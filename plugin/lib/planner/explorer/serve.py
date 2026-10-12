"""`planner explore --serve`: the explorer page on a small local server, with an "Ask Claude" endpoint behind it.

The page stays an offline file by default. Served, it can also ask a question of the vault: POST /ask runs Claude Code
headless (`claude -p`) in the vault with the read-only tools Read, Grep and Glob, and streams the answer back as
Server-Sent Events. Asking writes nothing to the vault. The one thing the helper writes is the layout: POST /pins
saves boxes the reader dragged to <vault>/.planner/explorer-pins.json (pins.py), and nothing else.

Three things this module exists to prevent:
- Silent Fallback: a missing `claude`, a non-zero exit, a timeout or an error result each reach the page as an
  `error` event that says why. No path ends in an empty answer that looks like a real one.
- Distributed Monolith across the network edge: the server binds the loopback address only, and a request whose Host or Origin
  is not the served origin is refused (DNS rebinding, cross-site POST). Anything else on the machine's network, or any
  other web page the reader has open, cannot spend their Claude quota or read their vault.
- Infected Core: the argv, the prompt, the stream parser and the origin rule are pure functions, tested without a
  socket or a process. Only `stream_answer` and `Handler` touch the OS.
"""
import http.server
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import threading
import webbrowser

from . import pins as pinning
from . import vault_files

# nosemgrep: prototype-no-hardcoded-server -- the policy itself: the helper listens on loopback and nowhere else, under these two names
LOOPBACK, LOCAL_NAME = "127.0.0.1", "localhost"
MODELS = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-5-5"}
DEFAULT_MODEL = "haiku"
MAX_QUESTION = 2000
MAX_BODY = 32 * 1024
MAX_CONTEXT_VALUE = 200
ASK_TIMEOUT = 180  # seconds a single question may run before claude is stopped
BUDGET_USD = 0.50  # one question's ceiling, so a runaway search cannot spend more
TOOLS = "Read,Grep,Glob"
CONTEXT_KEYS = ("view", "item", "item_title", "kind", "flow", "step")
SESSION_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

# The rules every answer follows. The page embeds the same text in "Copy as a Claude Code prompt", so a question
# pasted into a terminal is held to what a question asked from the page is.
RULES = ("Answer only from the vault's pages.",
         "Cite every claim: every bullet, every table row and every sentence that states a fact ends with the vault ID or the page path it comes from, written [[ID]] or [[path#heading]], for example [[FLO-002]] or [[releases/01-january.md#Scope]]. "
         "Write an ID only inside [[ ]], never bare, and cite requirement IDs such as [[CAP-001.FR1]] the same way. A claim you cannot cite from the vault is a claim you do not make. "
         "Put the citation after the claim, not around it: no |label inside [[ ]].",
         "When the vault does not answer, say so plainly in the first sentence. Do not guess and do not use outside knowledge.",
         "Be brief: a few sentences or a short list. The reader is mid-conversation. Write Markdown (bullets, a table when comparing), never raw HTML.",
         "Never create, edit or delete a file.")
SYSTEM_PROMPT = ("You are answering a question on a live call about one planning vault: Markdown pages in the current folder.\n"
                 "Search with Grep and Glob, read with Read. Ignore the .planner/ folder. You have read-only tools and no others.\n"
                 + "\n".join(f"- {rule}" for rule in RULES))


def claude_settings(home):
    """What a vault question loads: the vault's own settings, never the reader's global CLAUDE.md (it would steer
    every answer and cost tokens), and no read of the explorer page itself, a 3 MB single line that would drown a search."""
    claude_dir = pathlib.Path(home) / ".claude"
    return {"claudeMdExcludes": [str(claude_dir / "CLAUDE.md"), str(claude_dir / "**" / "*.md")],
            "permissions": {"deny": ["Read(./.planner/**)"]}}


def claude_argv(model_id, prompt, home, session_id=None):
    """The one `claude -p` call that answers a question. Read-only tools only, offered and allowed; no skills or MCP;
    a follow-up resumes the first answer's session so Claude keeps what it already read."""
    argv = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--model", model_id, "--allowedTools", TOOLS, "--tools", TOOLS, "--append-system-prompt", SYSTEM_PROMPT,
            "--disable-slash-commands", "--setting-sources", "project,local", "--strict-mcp-config",
            "--settings", json.dumps(claude_settings(home)), "--max-budget-usd", f"{BUDGET_USD:.2f}"]
    if session_id:
        argv += ["--resume", session_id]
    return argv + ["--", prompt]  # "--" so a question that starts with "-" is still the prompt


class FreshnessUnavailable(Exception):
    """The freshness check cannot run now (no role decides one); the message says why and reaches the page as a 503."""


class BadRequest(Exception):
    """A request the page should not have sent; the message says what to change."""


def apply_pins(path, body):
    """Save a dragged layout to the pins file and return the saved pins, or raise BadRequest. The body is
    {"pins": {key: [col, row]}, "kinds": {key: "app" | "partner"}}. A page may move boxes the file already pins and
    order clusters ("grp:" keys); a key the file does not hold is refused, so the endpoint cannot grow the file.
    Boxes that would overlap, or a party above the apps, are refused with the reason, as the page's drop refuses them.
    Pure of sockets: the handler only carries the body in and the answer out."""
    try:
        req = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BadRequest(f"the body is not JSON: {exc}") from exc
    if not isinstance(req, dict) or not isinstance(req.get("pins"), dict):
        raise BadRequest('the body must be {"pins": {key: [column, row]}, "kinds": {key: "app" | "partner"}}')
    path = pathlib.Path(path)
    if not path.exists():
        raise BadRequest("this vault has no pins file to save into; run planner explore once without --out outside the vault")
    try:
        current = pinning.read_pins(path)
        pins = pinning.validate(req["pins"], set(current))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    kinds = req.get("kinds") if isinstance(req.get("kinds"), dict) else {}
    if not all(v in ("app", "partner") for v in kinds.values()):
        raise BadRequest('kinds must say "app" or "partner" for each key')
    merged = {**current, **pins}
    problem = pinning.check_move(merged, {k: v for k, v in kinds.items() if k in merged and pinning.is_node(k)})
    if problem:
        raise BadRequest(problem)
    pinning.write_pins(path, merged)
    return merged


def clean_context(raw):
    """The page's context as a dict of short strings under known keys. It is the reader's own view, but it is
    still input from a socket: unknown keys are dropped and every value is capped."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise BadRequest("context must be an object")
    return {k: str(raw[k])[:MAX_CONTEXT_VALUE] for k in CONTEXT_KEYS if raw.get(k) not in (None, "")}


def context_line(context):
    if not context:
        return ""
    parts = []
    if "view" in context:
        parts.append(f"the {context['view']} view")
    if "item" in context:
        title = f" ({context['item_title']})" if "item_title" in context else ""
        parts.append(f"{context.get('kind', 'item')} {context['item']}{title}")
    if "flow" in context:
        parts.append(f"flow {context['flow']}" + (f" step {context['step']}" if "step" in context else ""))
    return "The reader is looking at " + ", ".join(parts) + ". Use it to read an ambiguous question, not as the only place to look.\n\n"


def parse_ask(body):
    """(question, context, session_id, model_key) from a POST /ask body, or BadRequest."""
    try:
        req = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BadRequest(f"the body is not JSON: {exc}") from exc
    if not isinstance(req, dict):
        raise BadRequest("the body must be a JSON object")
    question = req.get("question")
    if not isinstance(question, str) or not question.strip():
        raise BadRequest("question is required")
    if len(question) > MAX_QUESTION:
        raise BadRequest(f"the question is {len(question)} characters; the limit is {MAX_QUESTION}")
    session = req.get("conversation_id")
    if session is not None and not (isinstance(session, str) and SESSION_ID.match(session)):
        raise BadRequest("conversation_id is not a session id this helper issued")
    model = req.get("model") or None
    if model is not None and model not in MODELS:
        raise BadRequest(f"model must be one of {', '.join(MODELS)}")
    return question.strip(), clean_context(req.get("context")), session, model


def origin_allowed(host, origin, port):
    """True when the request is addressed to this server by a loopback name and, if the browser says where the
    request came from, it came from this same origin. A page on another site posting here sends its own Origin."""
    served = {f"{LOOPBACK}:{port}", f"{LOCAL_NAME}:{port}"}
    if host not in served:
        return False
    return origin is None or origin in {f"http://{h}" for h in served}


def tool_target(name, tool_input):
    """A short phrase for the page's progress line: what Claude is reading or searching, from the tool's own input."""
    if not isinstance(tool_input, dict):
        return ""
    return str(tool_input.get("file_path") or tool_input.get("pattern") or tool_input.get("path") or "")[:120]


def events_from(line, state):
    """The page-facing events one stream-json line carries. `state` remembers whether text has streamed, so that a
    whole assistant message is shown only when no partial deltas already carried it."""
    try:
        event = json.loads(line)
    except ValueError:
        return []  # claude -p prints nothing but JSON lines in this mode; a stray line carries no answer
    kind = event.get("type")
    if kind == "stream_event":
        inner = event.get("event") or {}
        if inner.get("type") == "content_block_start" and (inner.get("content_block") or {}).get("type") == "text" and state["text"]:
            state["streamed"] = True
            return [{"type": "delta", "text": "\n\n"}]
        delta = inner.get("delta") or {}
        if inner.get("type") == "content_block_delta" and delta.get("type") == "text_delta" and delta.get("text"):
            state["text"] += delta["text"]
            state["streamed"] = True
            return [{"type": "delta", "text": delta["text"]}]
        return []
    if kind == "assistant":
        out = []
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") == "text" and block.get("text") and not state["streamed"]:
                out.append({"type": "delta", "text": ("\n\n" if state["text"] else "") + block["text"]})
                state["text"] += block["text"]
            elif block.get("type") == "tool_use":
                out.append({"type": "tool", "name": block.get("name", ""), "target": tool_target(block.get("name"), block.get("input"))})
        state["streamed"] = False
        return out
    if kind == "result":
        state["result"] = event
    return []


def finish(state, model_key):
    """The closing events, from the result claude printed: done with cost and session, or the error it reported."""
    result = state.get("result")
    if result is None:
        return [{"type": "error", "message": "claude ended without an answer (no result event); run `claude -p` in the vault to see why"}]
    if result.get("is_error"):
        reason = result.get("result") or "; ".join(map(str, result.get("errors") or [])) or result.get("subtype", "unknown")
        return [{"type": "error", "message": f"claude reported an error: {reason}"}]
    out = []
    if not state["text"] and result.get("result"):
        out.append({"type": "delta", "text": result["result"]})
    out.append({"type": "done", "cost": result.get("total_cost_usd"), "session_id": result.get("session_id"),
                "model": MODELS[model_key]})
    return out


def stream_answer(vault, model_key, prompt, session_id, timeout=ASK_TIMEOUT, home=None):
    """Run claude and yield the page-facing events as they arrive, ending in `done` or `error`. The child gets a
    deadline: a timer kills it, and the reason reaches the page."""
    argv = claude_argv(MODELS[model_key], prompt, home or pathlib.Path.home(), session_id)
    if shutil.which(argv[0]) is None:
        yield {"type": "error", "message": "claude is not on PATH, so nothing can answer. Install Claude Code, or open the page as a file and use the copied prompt."}
        return
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
        proc = subprocess.Popen(argv, cwd=vault, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors, text=True, encoding="utf-8")
        timed_out = threading.Event()

        def stop():
            timed_out.set()
            proc.kill()
        timer = threading.Timer(timeout, stop)
        timer.start()
        state = {"text": "", "streamed": False, "result": None}
        try:
            yield {"type": "start", "model": MODELS[model_key]}
            for line in proc.stdout:
                yield from events_from(line, state)
            try:
                code = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:  # stdout closed but the process lingers: it is stopped below, and the reader told
                stop()
                code = proc.wait()
        finally:
            timer.cancel()
            if proc.poll() is None:
                proc.kill()  # the page went away or the stream broke: stop spending
            proc.wait()
            proc.stdout.close()
        if timed_out.is_set():
            yield {"type": "error", "message": f"claude took longer than {timeout} s and was stopped"}
            return
        if code != 0:
            errors.seek(0)
            tail = errors.read().strip()[-400:] or "no message on stderr"
            yield {"type": "error", "message": f"claude exited with status {code}: {tail}"}
            return
        yield from finish(state, model_key)


class Handler(http.server.BaseHTTPRequestHandler):
    """GET / is the page, GET /health says the helper is here, GET /freshness is `planner freshness --json` asked again
    now (the page polls it on load and on window focus), GET /pins is the saved layout, GET /vault-file/<path> is one of the vault's own files (read-only), POST /ask streams an answer and
    POST /pins saves a dragged layout."""

    def log_message(self, fmt, *args):
        self.server.log(f"{self.address_string()} {fmt % args}")

    def send_json(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def guarded(self):
        """False after answering 403, when the Host or Origin is not this server's own."""
        if origin_allowed(self.headers.get("Host"), self.headers.get("Origin"), self.server.server_port):
            return True
        self.send_json(403, {"error": "this helper answers only requests from its own page on this machine"})
        return False

    def do_GET(self):
        if not self.guarded():
            return
        if self.path == "/health":
            self.send_json(200, {"ok": True, "vault": self.server.vault.name, "model": self.server.default_model,
                                 "models": MODELS, "claude": shutil.which("claude") is not None, "maxQuestion": MAX_QUESTION})
        elif self.path == "/freshness":
            self.send_freshness()
        elif self.path == "/pins":
            self.send_pins()
        elif self.path.startswith(vault_files.PREFIX):
            self.send_vault_file()
        elif self.path in ("/", "/index.html"):
            data = self.server.page.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_json(404, {"error": f"nothing at {self.path}"})

    def send_vault_file(self):
        """The page's 'Open the file' links when served: a file inside the vault, as text, read-only (vault_files.py)."""
        try:
            target = vault_files.resolve(self.server.vault, self.path)
            data = target.read_bytes()
        except vault_files.Refused as exc:
            self.send_json(exc.status, {"error": str(exc)})
            return
        except OSError as exc:
            self.server.log(f"vault file {self.path}: {exc}")
            self.send_json(500, {"error": f"cannot read that file: {exc}"})
            return
        self.send_response(200)
        self.send_header("Content-Type", vault_files.content_type(target))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_pins(self):
        """The layout as saved now, so a reload after a save shows it though the page file still carries the old one."""
        if self.server.pins is None or not self.server.pins.exists():
            self.send_json(404, {"error": "this helper has no pins file"})
            return
        try:
            self.send_json(200, {"pins": pinning.read_pins(self.server.pins)})
        except ValueError as exc:
            self.server.log(f"pins: {exc}")
            self.send_json(500, {"error": str(exc)})

    def save_pins(self, body):
        if self.server.pins is None:
            self.send_json(404, {"error": "this helper was started without a pins file"})
            return
        try:
            with self.server.pins_lock:
                saved = apply_pins(self.server.pins, body)
        except BadRequest as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except OSError as exc:
            self.server.log(f"pins: cannot write {self.server.pins}: {exc}")
            self.send_json(500, {"error": f"cannot write the pins file: {exc}"})
            return
        self.server.log(f"layout saved to {pinning.PINS_FILE} ({len(saved)} keys)")
        self.send_json(200, {"saved": len(saved), "file": pinning.PINS_FILE, "pins": saved})

    def send_freshness(self):
        if self.server.freshness is None:
            self.send_json(404, {"error": "this helper was started without a freshness check"})
            return
        try:
            report = self.server.freshness()
        except FreshnessUnavailable as exc:
            self.server.log(f"freshness: {exc}")
            self.send_json(503, {"error": str(exc)})
            return
        self.send_json(200, report)

    def do_POST(self):
        # A browser always names the origin of a POST; a missing one is a script, not the page.
        if self.path not in ("/ask", "/pins"):
            self.send_json(404, {"error": f"nothing at {self.path}"})
            return
        if not self.guarded():
            return
        if self.headers.get("Origin") is None:
            self.send_json(403, {"error": "a POST must name its Origin"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self.send_json(413, {"error": f"the request is over {MAX_BODY} bytes"})
            return
        if self.path == "/pins":
            self.save_pins(self.rfile.read(length))
            return
        try:
            question, context, session, model = parse_ask(self.rfile.read(length))
        except BadRequest as exc:
            self.send_json(400, {"error": str(exc)})
            return
        self.stream(question, context, session, model or self.server.default_model)

    def stream(self, question, context, session, model):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        prompt = context_line(context) + question
        self.server.log(f"ask {model}{' (follow-up)' if session else ''}: {question[:80]!r}")
        events = stream_answer(self.server.vault, model, prompt, session, self.server.ask_timeout)
        for event in events:
            if event["type"] in ("done", "error"):
                self.server.log(f"  -> {event['type']}: " + (event.get("message") or f"${event.get('cost')} session {event.get('session_id')}"))
            try:
                self.wfile.write(b"data: " + json.dumps(event).encode("utf-8") + b"\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError) as exc:
                self.server.log(f"  -> the page went away mid-answer ({exc}); claude was stopped")
                events.close()  # stream_answer's finally stops the child
                return


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, vault, page, port, default_model, ask_timeout, log, freshness=None, pins=None):
        super().__init__((LOOPBACK, port), Handler)
        self.vault, self.page, self.default_model, self.ask_timeout, self.log = pathlib.Path(vault), pathlib.Path(page), default_model, ask_timeout, log
        self.freshness = freshness  # a callable returning the report dict, or None
        self.pins = pathlib.Path(pins) if pins else None  # the file POST /pins saves to
        self.pins_lock = threading.Lock()  # two saves at once must not interleave their writes

    @property
    def url(self):
        return f"http://{LOOPBACK}:{self.server_port}/"


def serve(vault, page, port, model, open_browser, log, ask_timeout=ASK_TIMEOUT, freshness=None, pins=None):
    """Serve until Ctrl-C. `open_browser` is the caller's choice: tests and remote shells say no."""
    server = Server(vault, page, port, model, ask_timeout, log, freshness, pins)
    if shutil.which("claude") is None:
        log("claude is not on PATH: the page will load, and Ask Claude will say so when asked")
    log(f"serving {server.url} (Ctrl-C stops it); questions run on {MODELS[model]} unless the page asks for sonnet")
    if open_browser and not webbrowser.open(server.url):
        log(f"no browser could be opened; open {server.url} yourself")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("stopped")
    finally:
        server.server_close()
