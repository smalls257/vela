"""`vela explore --serve`: the helper behind Ask Claude. A fake `claude` on PATH stands in for the model, so
no test here spends anything. They check what the helper promises: it listens on loopback only, it refuses a request
from another origin, it gives Claude read-only tools in the vault, it streams the answer and ends with cost and
session, a follow-up resumes that session, and every way a question can fail reaches the page as a visible error."""
import http.client
import json
import os
import pathlib
import re
import shutil
import socket
import threading

import pytest

from conftest import REPO
from vela.explorer import serve

STUB = REPO / "tests" / "explorer_stub"
SNAPSHOT = REPO / "tests/sim/snapshots/trading-coach/after-capture-boundary"


@pytest.fixture
def stub_log(tmp_path, monkeypatch):
    log = tmp_path / "claude-calls.jsonl"
    monkeypatch.setenv("PATH", f"{STUB}:" + os.environ["PATH"])
    monkeypatch.setenv("EXPLORE_STUB_LOG", str(log))
    return log


@pytest.fixture
def helper(tmp_path, stub_log):
    vault = tmp_path / "vault"
    vault.mkdir()
    page = tmp_path / "page.html"
    page.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    lines = []
    server = serve.Server(vault, page, 0, "haiku", 3, lines.append)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, vault, lines
    server.shutdown()
    server.server_close()
    thread.join(5)


def request(server, method, path, body=None, host=None, origin="same", key="own", headers=None):
    """`key` is the cookie the browser holds after opening the printed link: "own" sends the right one, None sends none."""
    conn = http.client.HTTPConnection(serve.LOOPBACK, server.server_port, timeout=15)
    headers = {"Host": host or f"{serve.LOOPBACK}:{server.server_port}", **(headers or {})}
    if key:
        headers["Cookie"] = f"{serve.cookie_name(server.server_port)}={server.key if key == 'own' else key}"
    if origin == "same":
        headers["Origin"] = f"http://{serve.LOOPBACK}:{server.server_port}"
    elif origin:
        headers["Origin"] = origin
    if body is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    return conn.getresponse()


def ask(server, question="What does the demo deliver?", **extra):
    response = request(server, "POST", "/ask", {"question": question, **extra})
    assert response.status == 200, response.read()
    return [json.loads(chunk[len("data: "):]) for chunk in response.read().decode("utf-8").split("\n\n") if chunk]


def calls(log):
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def value_after(argv, flag):
    return argv[argv.index(flag) + 1]


def test_the_server_binds_loopback_only(helper):
    """A socket bound to 127.0.0.1 accepts nothing from another machine, so the bind address is the guarantee.
    No name lookups: resolving the host name made the old test error or pass vacuously on some machines."""
    server, _, _ = helper
    assert server.server_address[0] == "127.0.0.1"
    assert serve.LOOPBACK == "127.0.0.1"
    assert server.url.startswith("http://127.0.0.1:")
    assert request(server, "GET", "/health", origin=None).status == 200

def test_health_names_the_vault_and_the_default_model(helper):
    server, vault, _ = helper
    response = request(server, "GET", "/health")
    body = json.loads(response.read())
    assert response.status == 200 and body["ok"] is True and body["vault"] == vault.name
    assert body["model"] == "haiku" and body["claude"] is True and body["models"] == serve.MODELS


def test_the_page_is_served_at_the_root(helper):
    server, _, _ = helper
    response = request(server, "GET", "/", origin=None)
    assert response.status == 200 and b"<title>x</title>" in response.read()


def test_ask_streams_text_then_ends_with_cost_and_session(helper):
    server, _, _ = helper
    events = ask(server)
    kinds = [e["type"] for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done" and "delta" in kinds and "tool" in kinds
    text = "".join(e["text"] for e in events if e["type"] == "delta")
    assert text == "The demo delivers [[REQ-001]] and the page [[releases/01-january.md#Scope]], not [[ZZZ-999]]."  # once, not twice
    done = events[-1]
    assert done["cost"] == pytest.approx(0.0123) and done["session_id"].startswith("stub-") and done["model"] == serve.MODELS["haiku"]
    assert next(e for e in events if e["type"] == "tool") == {"type": "tool", "name": "Grep", "target": "demo"}


def test_a_follow_up_resumes_the_first_session(helper, stub_log):
    server, _, _ = helper
    first = ask(server)[-1]["session_id"]
    second = ask(server, "And after that?", conversation_id=first)
    assert second[-1]["session_id"] == first
    one, two = calls(stub_log)
    assert "--resume" not in one["argv"] and value_after(two["argv"], "--resume") == first


def test_claude_gets_read_only_tools_the_vault_as_cwd_and_the_citation_rule(helper, stub_log):
    server, vault, _ = helper
    ask(server, context={"view": "Flows", "item": "FLO-002", "flow": "FLO-002", "step": 2, "stray": "dropped"})
    (call,) = calls(stub_log)
    argv = call["argv"]
    assert value_after(argv, "--tools") == "Read,Grep,Glob" and "--allowedTools" not in argv  # no bare tool name pre-approves a path outside the vault
    assert pathlib.Path(call["cwd"]).resolve() == vault.resolve()
    assert value_after(argv, "--model") == serve.MODELS["haiku"] and "--disable-slash-commands" in argv
    system = value_after(argv, "--append-system-prompt")
    assert "[[ID]]" in system and "Never create, edit or delete" in system and "does not answer" in system
    # the smoke test returned requirement IDs as bare text: the rule asks for a citation on every bullet, row and claim
    assert "every bullet, every table row" in system and "never bare" in system and "[[CAP-001.FR1]]" in system and "never raw HTML" in system
    prompt = argv[argv.index("--") + 1]
    assert "flow FLO-002 step 2" in prompt and prompt.endswith("What does the demo deliver?") and "stray" not in prompt


def test_the_page_can_ask_for_sonnet_and_only_the_two_models(helper, stub_log):
    server, _, _ = helper
    assert ask(server, model="sonnet")[-1]["model"] == serve.MODELS["sonnet"]
    assert value_after(calls(stub_log)[0]["argv"], "--model") == "claude-sonnet-5-5"
    response = request(server, "POST", "/ask", {"question": "x", "model": "opus"})
    assert response.status == 400 and "model must be one of" in json.loads(response.read())["error"]


@pytest.mark.parametrize("origin, host", [("http://evil.example", None), ("http://localhost:1", None), (None, "evil.example")])
def test_a_request_from_another_origin_or_host_is_refused_and_claude_never_runs(helper, stub_log, origin, host):
    server, _, _ = helper
    response = request(server, "POST", "/ask", {"question": "x"}, host=host, origin=origin or "same")
    assert response.status == 403 and not stub_log.exists()
    assert request(server, "GET", "/health", host=host or None, origin=origin or None).status == 403


def test_a_post_with_no_origin_is_refused(helper, stub_log):
    server, _, _ = helper
    assert request(server, "POST", "/ask", {"question": "x"}, origin=None).status == 403 and not stub_log.exists()


def test_localhost_by_name_is_the_same_origin(helper):
    server, _, _ = helper
    host = f"{serve.LOCAL_NAME}:{server.server_port}"
    response = request(server, "POST", "/ask", {"question": "x"}, host=host, origin=f"http://{host}")
    assert response.status == 200 and b'"type": "done"' in response.read()


def test_question_length_and_shape_are_capped(helper, stub_log):
    server, _, _ = helper
    for body in ({"question": "q" * (serve.MAX_QUESTION + 1)}, {"question": "  "}, {"question": 7}, {"question": "x", "conversation_id": "--model"}):
        response = request(server, "POST", "/ask", body)
        assert response.status == 400, body
        assert json.loads(response.read())["error"]
    assert not stub_log.exists()


def test_a_missing_claude_is_a_visible_error(helper, monkeypatch):
    server, _, _ = helper
    monkeypatch.setenv("PATH", "/nonexistent")
    events = ask(server)
    assert events[-1]["type"] == "error" and "claude is not on PATH" in events[-1]["message"]


def test_a_non_zero_exit_is_a_visible_error_with_the_reason(helper, monkeypatch):
    server, _, _ = helper
    monkeypatch.setenv("EXPLORE_STUB_MODE", "fail")
    last = ask(server)[-1]
    assert last["type"] == "error" and "status 3" in last["message"] and "authentication failed" in last["message"]


def test_a_timeout_is_a_visible_error_and_stops_claude(helper, monkeypatch):
    server, _, _ = helper
    monkeypatch.setenv("EXPLORE_STUB_MODE", "hang")
    last = ask(server)[-1]
    assert last["type"] == "error" and "longer than 3 s" in last["message"]


def test_an_error_result_and_a_missing_result_are_visible_errors(helper, monkeypatch):
    server, _, _ = helper
    monkeypatch.setenv("EXPLORE_STUB_MODE", "error")
    assert "Reached maximum budget" in ask(server)[-1]["message"]
    monkeypatch.setenv("EXPLORE_STUB_MODE", "silent")
    assert "no result event" in ask(server)[-1]["message"]


REPORT = {"role": "reader", "state": "newer", "checked_at": "2026-10-18T09:12:00", "have": {"commit": "9f3c2ab", "date": "2026-10-11"},
          "latest": {"commit": "4d1e8a0", "date": "2026-10-20"}, "behind": None, "ahead": None, "uncommitted": None, "message": "A newer copy was published."}


def test_freshness_returns_the_report_the_cli_would_print(helper):
    server, _, _ = helper
    server.freshness = lambda: REPORT
    response = request(server, "GET", "/freshness")
    assert response.status == 200 and response.getheader("Cache-Control") == "no-store" and json.loads(response.read()) == REPORT


def test_freshness_that_cannot_run_is_a_503_with_the_reason_and_is_logged(helper):
    server, _, lines = helper

    def cannot():
        raise serve.FreshnessUnavailable("cannot check freshness: this folder is neither a vault repo nor a published copy")
    server.freshness = cannot
    response = request(server, "GET", "/freshness")
    assert response.status == 503 and "neither a vault repo" in json.loads(response.read())["error"]
    assert any("freshness:" in line for line in lines)


def test_a_helper_started_without_a_freshness_check_says_so(helper):
    server, _, _ = helper
    response = request(server, "GET", "/freshness")
    assert response.status == 404 and "without a freshness check" in json.loads(response.read())["error"]


def test_freshness_is_refused_to_another_origin_like_every_route(helper):
    server, _, _ = helper
    server.freshness = lambda: REPORT
    assert request(server, "GET", "/freshness", host="evil.example").status == 403
    assert request(server, "GET", "/freshness", origin="http://evil.example").status == 403


def test_each_ask_is_logged_with_its_outcome(helper):
    server, _, lines = helper
    ask(server)
    assert any(line.startswith("ask haiku") for line in lines) and any("-> done" in line and "$0.0123" in line for line in lines)


def test_the_cli_serves_a_built_vault_and_stops_on_ctrl_c(tmp_path, monkeypatch):
    import io
    from vela import cli
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    seen = {}

    def serve_once(self_server=None):
        seen["called"] = True
        raise KeyboardInterrupt
    monkeypatch.setattr(serve.Server, "serve_forever", lambda self, *a: serve_once())
    out = io.StringIO()
    assert cli.main(["explore", str(vault), "--today", "2026-10-10", "--serve", "--no-open", "--model", "sonnet"], out=out) == 0
    text = out.getvalue()
    assert seen and f"serving http://{serve.LOOPBACK}:" in text and "claude-sonnet-5-5" in text and text.rstrip().endswith("stopped")
    assert (vault / "dashboard.html").is_file()


def test_a_port_out_of_range_is_a_tool_error(tmp_path):
    import io
    from vela import cli
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    out = io.StringIO()
    assert cli.main(["explore", str(vault), "--serve", "--port", "70000"], out=out) == 2
    assert "not a port number" in out.getvalue()


def test_only_ask_js_freshness_js_and_layout_js_can_reach_the_network_and_each_checks_for_a_file_first():
    """The page's offline promise: no module but ask.js, freshness.js and layout.js names a network call, ask.js decides on
    file: before it looks for the helper, freshness.js asks only its own origin's /freshness, and only when served, and
    layout.js asks /pins only when the page was served and its reader is not a reader (a file saves to the browser)."""
    scripts = REPO / "plugin/lib/vela/explorer/assets/js"
    network = ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon")
    for script in scripts.glob("*.js"):
        text = script.read_text(encoding="utf-8")
        if script.name == "ask.js":
            assert text.index('loc.protocol === "file:"') < text.index('fetchFn("/health")')
            assert 'fetchFn("/ask"' in text and "XMLHttpRequest" not in text
        elif script.name == "freshness.js":
            assert text.index("if (!served() ||") < text.index('fetchFn("/freshness")')
            assert 'location.protocol === "http:" || location.protocol === "https:"' in text
            assert text.count("fetchFn(") == 1 and "XMLHttpRequest" not in text and "://" not in text.replace('"http:"', "").replace('"https:"', "")
        elif script.name == "layout.js":
            assert 'const canSave = () => typeof Ask !== "undefined" && Ask.served() && D.role !== "reader";' in text
            assert text.index("if (!canSave()) return;") < text.index('net.fetch("/pins")')
            assert "if (canSave()) { await saveToVault(said);" in text and "    if (canSave()) {\n      base = clone(built);" in text
            assert text.count("net.fetch(") == 2 and "XMLHttpRequest" not in text and "://" not in text.replace('"http:"', "").replace('"https:"', "")
        elif script.name != "selftest.js":  # the self-test wraps fetch to prove none is made
            assert not [word for word in network if word in text], script.name


# ------------------------------------------------------------------ a received vault is hostile input

def test_ask_does_not_load_the_vaults_own_settings_and_turns_hooks_off(helper, stub_log):
    """E19. A vault arriving by zip or proposal can carry .claude/settings.json with a SessionStart hook. claude -p shows no
    trust dialog, so loading project settings would run it as the reader."""
    server, vault, _ = helper
    (vault / ".claude").mkdir()
    (vault / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "touch PWNED"}]}]}}), encoding="utf-8")
    ask(server)
    (call,) = calls(stub_log)
    argv = call["argv"]
    assert value_after(argv, "--setting-sources") == "user"
    settings = json.loads(value_after(argv, "--settings"))
    assert settings["disableAllHooks"] is True
    assert not (vault / "PWNED").exists()


def test_ask_is_confined_to_the_vault_when_claude_can_be(helper, stub_log):
    """E24. The file tools stay in the folder: --restricted where this claude has it, never a bare Read/Grep/Glob allow rule."""
    server, _, _ = helper
    ask(server)
    (call,) = calls(stub_log)
    assert "--restricted" in call["argv"]
    assert "--allowedTools" not in call["argv"]
    assert json.loads(request(server, "GET", "/health").read())["confined"] is True
    older = serve.claude_argv("m", "q", "/h")
    assert "--restricted" not in older and "--allowedTools" not in older and value_after(older, "--setting-sources") == "user"


def test_the_settings_deny_the_exact_explorer_page_the_helper_writes():
    """E25. dashboard.html is what `vela explore` writes at the vault root, and the docstring promised no read of it."""
    from vela import publish
    deny = serve.claude_settings("/h")["permissions"]["deny"]
    assert f"Read(./{publish.DASHBOARD_PATH})" in deny and f"Read(./**/{publish.DASHBOARD_PATH})" in deny and "Read(./.vela/**)" in deny


def test_a_request_without_the_key_is_refused_even_with_the_right_host_and_origin(helper, stub_log):
    """E26. Host and Origin are headers any local program can set; the key is what only the opened link carries."""
    server, _, _ = helper
    for key in (None, "wrong-key"):
        assert request(server, "POST", "/ask", {"question": "x"}, key=key).status == 403
        assert request(server, "POST", "/pins", {"pins": {}}, key=key).status == 403
        assert request(server, "GET", "/freshness", key=key).status == 403
        assert request(server, "GET", "/", key=key, origin=None).status == 403
    assert not stub_log.exists()


def test_the_printed_link_hands_the_key_to_the_browser_as_a_cookie_and_redirects(helper):
    server, _, _ = helper
    assert "?k=" + server.key in server.url
    response = request(server, "GET", f"/?k={server.key}", key=None, origin=None)
    assert response.status == 302 and response.getheader("Location") == "/"
    cookie = response.getheader("Set-Cookie")
    assert f"{serve.cookie_name(server.server_port)}={server.key}" in cookie and "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert request(server, "GET", "/?k=nope", key=None, origin=None).status == 403


@pytest.mark.parametrize("length, status", [("-1", 400), ("abc", 400), ("99999999", 413), (None, 411)])
def test_a_bad_content_length_gets_a_status_not_a_hung_thread(helper, length, status):
    """E28. read(-1) blocks until the client closes; int('abc') raised with only a traceback on stderr."""
    server, _, _ = helper
    conn = http.client.HTTPConnection(serve.LOOPBACK, server.server_port, timeout=5)
    conn.putrequest("POST", "/pins", skip_accept_encoding=True)
    conn.putheader("Host", f"{serve.LOOPBACK}:{server.server_port}")
    conn.putheader("Origin", f"http://{serve.LOOPBACK}:{server.server_port}")
    conn.putheader("Cookie", f"{serve.cookie_name(server.server_port)}={server.key}")
    if length is not None:
        conn.putheader("Content-Length", length)
    conn.endheaders()
    assert conn.getresponse().status == status


HELD_TIMEOUTS = []  # the stub hangs on purpose, so the held requests end by timing out; kept so the test can see them


def _drain(server):
    try:
        request(server, "POST", "/ask", {"question": "x"}).read()
    except TimeoutError as exc:
        HELD_TIMEOUTS.append(exc)


def test_a_third_question_is_told_to_wait_rather_than_spawning_another_claude(helper, stub_log, monkeypatch):
    """E40. Each /ask is a claude process with its own budget."""
    server, _, _ = helper
    monkeypatch.setenv("EXPLORE_STUB_MODE", "hang")
    server.ask_timeout = 20
    held = []
    for _ in range(serve.MAX_CONCURRENT_ASKS):
        thread = threading.Thread(target=lambda: _drain(server), daemon=True)
        thread.start()
        held.append(thread)
    for _ in range(400):
        if stub_log.exists() and len(calls(stub_log)) >= serve.MAX_CONCURRENT_ASKS:
            break
        threading.Event().wait(0.05)
    else:
        raise AssertionError("the first questions never started")
    assert request(server, "POST", "/ask", {"question": "x"}).status == 429
    assert len(calls(stub_log)) == serve.MAX_CONCURRENT_ASKS


def test_a_vault_holding_a_symbolic_link_is_not_served(tmp_path):
    """E24. A link inside the vault can name ~/.ssh/id_rsa; Ask follows it."""
    import io
    from vela import cli
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    (vault / "keys").symlink_to(tmp_path)
    out = io.StringIO()
    assert cli.main(["explore", str(vault), "--today", "2026-10-10", "--serve", "--no-open"], out=out) == 2
    assert "keys" in out.getvalue() and "symbolic link" in out.getvalue()


# ------------------------------------------------------------ E17: the served page's Open-the-file links

def get(server, path):
    response = request(server, "GET", path, origin=None)
    return response.status, dict(response.getheaders()), response.read()


def test_e17_the_helper_serves_a_vault_file_as_text_and_nothing_outside_the_vault(helper, tmp_path):
    server, vault, _ = helper
    (vault / "docs").mkdir()
    (vault / "docs" / "Q&A #2.md").write_text("# hello\n", encoding="utf-8")
    (vault / "page.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    (vault / ".vela").mkdir()
    (vault / ".vela" / "explorer-pins.json").write_text("{}", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOPSECRET-4471", encoding="utf-8")
    (vault / "link.txt").symlink_to(tmp_path / "secret.txt")
    status, headers, body = get(server, "/vault-file/docs/Q%26A%20%232.md")
    assert (status, body) == (200, b"# hello\n") and headers["Content-Type"].startswith("text/plain")
    status, headers, _ = get(server, "/vault-file/page.html")
    assert status == 200 and headers["Content-Type"].startswith("text/plain") and headers["X-Content-Type-Options"] == "nosniff"
    for refused in ("/vault-file/.vela/explorer-pins.json", "/vault-file/../secret.txt", "/vault-file/%2e%2e/secret.txt",
                    "/vault-file/link.txt", "/vault-file/docs", "/vault-file/missing.md", "/vault-file/"):
        status, _, body = get(server, refused)
        assert status in (400, 403, 404), refused
        assert b"TOPSECRET-4471" not in body and json.loads(body)["error"], refused


def test_e17_a_vault_file_request_still_has_to_come_from_this_helper(helper):
    server, vault, _ = helper
    (vault / "a.md").write_text("x", encoding="utf-8")
    response = request(server, "GET", "/vault-file/a.md", host="evil.example:80", origin=None)
    assert response.status == 403


# ------------------------------------------------------------ E27: the same port on every run, so the browser's saved state is found

def test_e27_a_vault_gets_the_same_port_every_time_inside_the_private_range():
    port = serve.preferred_port("v-9f3c0a17d4e2b6")
    assert port == serve.preferred_port("v-9f3c0a17d4e2b6") and 49152 <= port <= 65151
    assert serve.preferred_port("v-0000000000000a") != serve.preferred_port("v-0000000000000b")


def test_e27_explore_serve_without_a_port_uses_the_vaults_port_or_says_why_it_did_not(tmp_path, stub_log):
    import subprocess
    import sys
    root = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, root)
    command = [sys.executable, str(REPO / "plugin" / "scripts" / "vela"), "explore", str(root), "--today", "2026-10-12", "--serve", "--no-open"]

    def started():
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        watchdog = threading.Timer(60, proc.kill)
        watchdog.start()
        try:
            lines = []
            for line in proc.stdout:
                lines.append(line)
                if "serving http://" in line:
                    return lines
            raise AssertionError("never said where it serves: " + "".join(lines))
        finally:
            watchdog.cancel()
            proc.terminate()
            proc.wait(10)
    first = started()
    port = int(re.search(r"serving http://127.0.0.1:(\d+)/", "".join(first)).group(1))
    assert port == serve.preferred_port(expected_id(root))
    assert port == int(re.search(r"serving http://127.0.0.1:(\d+)/", "".join(started())).group(1))
    with socket.socket() as taken:
        taken.bind((serve.LOOPBACK, port))
        taken.listen()
        lines = "".join(started())
    other = int(re.search(r"serving http://127.0.0.1:(\d+)/", lines).group(1))
    assert other != port and "port" in lines and "taken" in lines


def expected_id(root):
    from vela import cli
    from vela.explorer import build
    config = cli.load_config(root)
    return build.vault_id(str(config.get("initiative", "")), str(config.get("title", "")), config.get(build.VAULT_ID_KEY))
