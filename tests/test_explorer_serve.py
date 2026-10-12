"""`planner explore --serve`: the helper behind Ask Claude. A fake `claude` on PATH stands in for the model, so
no test here spends anything. They check what the helper promises: it listens on loopback only, it refuses a request
from another origin, it gives Claude read-only tools in the vault, it streams the answer and ends with cost and
session, a follow-up resumes that session, and every way a question can fail reaches the page as a visible error."""
import http.client
import json
import os
import pathlib
import shutil
import socket
import threading

import pytest

from conftest import REPO
from planner.explorer import serve

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


def request(server, method, path, body=None, host=None, origin="same"):
    conn = http.client.HTTPConnection(serve.LOOPBACK, server.server_port, timeout=15)
    headers = {"Host": host or f"{serve.LOOPBACK}:{server.server_port}"}
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
    server, _, _ = helper
    assert server.server_address[0] == serve.LOOPBACK
    assert server.url.startswith(f"http://{serve.LOOPBACK}:")
    # a socket to the machine's own non-loopback address finds nothing listening
    outward = socket.gethostbyname(socket.gethostname())
    if outward != serve.LOOPBACK:
        with pytest.raises(OSError), socket.create_connection((outward, server.server_port), timeout=2):
            pass


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
    assert value_after(argv, "--allowedTools") == "Read,Grep,Glob" and value_after(argv, "--tools") == "Read,Grep,Glob"
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
    from planner import cli
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
    assert (vault / ".planner" / "explorer.html").is_file()


def test_a_port_out_of_range_is_a_tool_error(tmp_path):
    import io
    from planner import cli
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    out = io.StringIO()
    assert cli.main(["explore", str(vault), "--serve", "--port", "70000"], out=out) == 2
    assert "not a port number" in out.getvalue()


def test_only_ask_js_freshness_js_and_layout_js_can_reach_the_network_and_each_checks_for_a_file_first():
    """The page's offline promise: no module but ask.js, freshness.js and layout.js names a network call, ask.js decides on
    file: before it looks for the helper, freshness.js asks only its own origin's /freshness, and only when served, and
    layout.js asks /pins only when the page was served and its reader is not a reader (a file saves to the browser)."""
    scripts = REPO / "plugin/lib/planner/explorer/assets/js"
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
