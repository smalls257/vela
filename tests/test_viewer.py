import hashlib
import http.server
import json
import re
import shutil
import subprocess
import threading
from html.parser import HTMLParser

import pytest

import pathlib

from conftest import MINI, REPO, edit, run

FIXTURE = REPO / "examples" / "unified-booking"
ASSETS = REPO / "plugin" / "lib" / "planner" / "assets"
ASSET_SHA256 = {
    "marked.min.js": "15fabce5b65898b32b03f5ed25e9f891a729ad4c0d6d877110a7744aa847a894",
    "mermaid.min.js": "61b335a46df05a7ce1c98378f60e5f3e77a7fb608a1056997e8a649304a936d6",
}


def build(vault, out):
    return run("view", "--vault", str(vault), "--out", str(out), "--date", "2026-11-20",
               "--commit", "abc1234", "--repo-url", "https://github.example/harborline/unified-booking")


def bundle(html):
    raw = re.search(r'<script id="vault" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert "<" not in raw and ">" not in raw and "&" not in raw
    return json.loads(raw)


def test_assets_are_the_pinned_versions():
    for name, digest in ASSET_SHA256.items():
        assert hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() == digest, name


def test_viewer_builds_offline_from_the_fixture(tmp_path):
    out = tmp_path / "viewer.html"
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)  # a copy outside any repo, so the stamp does not depend on this checkout's status
    code, text = build(vault, out)
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]*\bsrc\s*=", html)
    assert not re.search(r"<link[^>]*\bhref\s*=", html)
    assert "fonts.googleapis" not in html
    data = bundle(html)
    paths = [p["path"] for p in data["pages"]]
    assert not [p for p in paths if p.startswith(("sessions/", "voice/", ".claude/"))]
    assert data["start"] == "01-goals" and "01-goals.md" in paths
    # the stamp repeats what check says of the vault; the example leaves open on purpose its decided items' Why (W390) and
    # the flow check of slices whose flows predate the strict form (W391)
    checked = run("check", "--vault", str(vault), "--today", "2026-11-20")[1]
    counts = re.search(r"planner check: (\d+) errors, (\d+) warnings", checked)
    assert counts, checked
    assert data["stamp"] == {"commit": "abc1234", "date": "2026-11-20",
                             "repo": "https://github.example/harborline/unified-booking",
                             "errors": 0, "warnings": int(counts.group(2))}
    assert data["stamp"]["warnings"] == len(re.findall(r" W39[01] ", checked)) > 0
    assert "Built from ${DATA.stamp.commit} on ${DATA.stamp.date}. Newer versions: ${DATA.stamp.repo}" in html


def git_in(vault, *args):
    subprocess.run(["git", "-C", str(vault), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True, timeout=60)


def test_stamp_says_when_the_vault_has_uncommitted_changes(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    git_in(vault, "init", "-q")
    git_in(vault, "add", "-A")
    git_in(vault, "commit", "-q", "-m", "x")
    out = tmp_path / "viewer.html"
    build(vault, out)
    assert bundle(out.read_text(encoding="utf-8"))["stamp"]["commit"] == "abc1234"
    edit(vault / "12-glossary.md", "title: Glossary\n", "title: Glossary edited\n")
    build(vault, out)
    assert bundle(out.read_text(encoding="utf-8"))["stamp"]["commit"] == "abc1234 with uncommitted changes"


def test_header_carries_the_check_counts_so_a_vault_with_errors_is_visible(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "03-context-and-scope.md", "state: decided\n", "state: bogus\n")
    out = tmp_path / "viewer.html"
    code, text = build(vault, out)
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    stamp = bundle(html)["stamp"]
    assert stamp["errors"] >= 1
    assert f"Check at build time: {stamp['errors']} errors" in text
    assert "Check at build time: ${DATA.stamp.errors} errors, ${DATA.stamp.warnings} warnings." in html


def test_every_link_and_anchor_resolves_in_the_bundle(tmp_path):
    out = tmp_path / "viewer.html"
    build(FIXTURE, out)
    data = bundle(out.read_text(encoding="utf-8"))
    pages = {p["name"].lower(): p for p in data["pages"]}
    excluded = set(data["excluded"])
    for page in data["pages"]:
        body = re.sub(r"```.*?```", "", page["body"], flags=re.S)
        body = re.sub(r"`[^`]*`", "", body)
        for inner in re.findall(r"\[\[([^\]]+?)\]\]", body):
            target, _, _ = inner.replace("\\|", "|").partition("|")
            name, _, anchor = target.partition("#")
            name = (name.strip() or page["name"]).lower()
            if name in excluded:
                continue
            assert name in pages, f"{page['path']}: [[{inner}]]"
            if anchor and not anchor.startswith("^"):
                assert anchor.strip() in pages[name]["headings"], f"{page['path']}: [[{inner}]]"


def test_page_below_decided_carries_the_draft_banner(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "03-context-and-scope.md", "state: decided\n", "state: assumption\n")
    out = tmp_path / "viewer.html"
    build(vault, out)
    html = out.read_text(encoding="utf-8")
    pages = {p["name"]: p for p in bundle(html)["pages"]}
    assert pages["03-context-and-scope"]["draft"] is True
    assert pages["01-goals"]["draft"] is False
    assert "${esc(p.state)}: not agreed yet" in html and "draft-banner" not in html  # a quiet line, not a yellow box


def pages_of(tmp_path, vault):
    out = tmp_path / "viewer.html"
    code, text = build(vault, out)
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    return html, {p["name"]: p for p in bundle(html)["pages"]}


def test_an_item_override_is_listed_and_no_page_gets_an_override_banner(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    html, pages = pages_of(tmp_path, vault)
    assert pages["pricing-building-blocks"]["overrides"] == [{
        "rules": "GATE-5", "by": "@hl-solution-lead", "date": "2026-07-28", "pending_for": "",
        "reason": pages["pricing-building-blocks"]["overrides"][0]["reason"]}]
    assert pages["pricing-building-blocks"]["overrides"][0]["reason"].startswith("the Revenue team was in its fare review")
    assert pages["01-goals"]["overrides"] == []
    assert "override-banner" not in html  # the Override bullet is in the folded History, not a box up top


def test_an_unconfirmed_on_behalf_decision_gets_one_status_line(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "05-building-blocks" / "pricing-building-blocks.md", "- **Confirmed by:** @hl-pricing-senior on 2026-08-12\n", "")
    html, pages = pages_of(tmp_path, vault)
    assert [o["pending_for"] for o in pages["pricing-building-blocks"]["overrides"]] == ["@harborline/revenue-team"]
    assert "decided on behalf of ${esc([...new Set(pending)].join(', '))}, not yet confirmed" in html


def test_every_override_on_a_page_gets_its_own_line_and_malformed_ones_get_none(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "01-goals.md", "# Unified Booking\n", "# Unified Booking\n\n- **Override:** grill by @a on 2026-11-20: first\n"
         "- **Override:** GATE-4 by @b on 2026-11-21: second\n- **Override:** nonsense\n")
    _, pages = pages_of(tmp_path, vault)
    assert [(o["rules"], o["reason"]) for o in pages["01-goals"]["overrides"]] == [("grill", "first"), ("GATE-4", "second")]


def test_the_override_banner_is_built_from_escaped_text_and_adds_no_script(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    html, _ = pages_of(tmp_path, vault)
    assert "innerHTML = (p.draft" in html and "esc([...new Set(pending)]" in html
    csp = re.search(r'Content-Security-Policy" content="([^"]*)"', html).group(1)
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert csp.count("sha256-") == len(scripts) == 3, "the banner is inside the existing APP script, so no new hash"



def test_voice_and_claude_folders_stay_out_of_the_bundle(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    (vault / "voice").mkdir(exist_ok=True)
    (vault / ".claude").mkdir(exist_ok=True)
    (vault / "voice" / "how-we-write.md").write_text("# Voice SECRET-VOICE\n", encoding="utf-8")
    (vault / ".claude" / "notes.md").write_text("# Notes SECRET-CLAUDE\n", encoding="utf-8")
    out = tmp_path / "viewer.html"
    code, text = build(vault, out)
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    assert "SECRET-VOICE" not in html and "SECRET-CLAUDE" not in html
    paths = [p["path"] for p in bundle(html)["pages"]]
    assert not [p for p in paths if p.startswith(("voice/", ".claude/", "sessions/"))]


HOSTILE = """---
id: hostile
type: initiative-section
title: Hostile
initiative: INI-900
state: decided
---
# Hostile

<img src=x onerror=alert(1)>

<script>alert(1)</script>

[x](javascript:alert(1)) and [y](data:text/html,boo) and [z](  JavaScript:alert(2)) and [e](&#106;avascript:alert(3))

![p](https://example.com/p.png)

[fine](https://example.com/ok) and [local](#hostile) and [[01-goals]]

`<b>kept</b>` stays as written.

```mermaid
graph TD
  A[Start]-->B[End<br/>line]
```
"""


def hostile_body(tmp_path):
    from conftest import MINI
    vault = tmp_path / "mini"
    shutil.copytree(MINI, vault)
    (vault / "12-hostile.md").write_text(HOSTILE, encoding="utf-8")
    out = tmp_path / "viewer.html"
    code, text = build(vault, out)
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    page = next(p for p in bundle(html)["pages"] if p["name"] == "12-hostile")
    return page["body"], html


def test_raw_html_in_a_page_is_escaped_not_rendered(tmp_path):
    body, html = hostile_body(tmp_path)
    assert "<img" not in body and "<script" not in body
    assert "&lt;img src=x onerror=alert(1)>" in body
    assert "&lt;script>alert(1)&lt;/script>" in body
    assert "<script>alert(1)" not in html


def test_unsafe_link_schemes_become_plain_text(tmp_path):
    body, _ = hostile_body(tmp_path)
    assert "](javascript" not in body.lower() and "](data:" not in body.lower() and "](  javascript" not in body.lower()
    assert "](&#106;" not in body
    assert "[fine](https://example.com/ok)" in body and "[local](#hostile)" in body


def test_images_never_fetch_from_the_network(tmp_path):
    body, _ = hostile_body(tmp_path)
    assert "![p](https://example.com/p.png)" not in body
    assert "p (https://example.com/p.png)" in body


def test_code_and_diagrams_are_left_as_written(tmp_path):
    body, _ = hostile_body(tmp_path)
    assert "`<b>kept</b>`" in body
    assert "B[End<br/>line]" in body
    assert "[[01-goals]]" in body


def test_generated_markers_survive_neutralizing():
    from planner import viewer
    marker = "<!-- generated:where-it-stands sha=0a1b2c3d: do not edit, run planner render -->"
    end = "<!-- /generated:where-it-stands -->"
    assert viewer.neutralize(f"{marker}\ntext <b>\n{end}") == f"{marker}\ntext &lt;b>\n{end}"
    assert viewer.neutralize("<!-- anything else -->") == "&lt;!-- anything else -->"


def test_broken_link_in_a_bundled_page_stops_the_build(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "README.md", "[[01-goals|Unified Booking: Goals]]", "[[01-gaols|Unified Booking: Goals]]")
    out = tmp_path / "viewer.html"
    code, text = build(vault, out)
    assert code == 1
    assert "01-gaols" in text
    assert not out.exists()


def test_missing_asset_is_a_tool_failure(tmp_path, monkeypatch):
    from planner import cli
    monkeypatch.setattr(cli, "ASSETS", tmp_path)
    code, text = build(FIXTURE, tmp_path / "viewer.html")
    assert code == 2
    assert "cannot work offline" in text


def test_embedded_json_has_no_raw_angle_brackets(tmp_path):
    vault = tmp_path / "mini"
    shutil.copytree(MINI, vault)
    (vault / "12-trap.md").write_text(PAGE.format(title="Trap", body="```\n<!--<script>\n```\n"), encoding="utf-8")
    out = tmp_path / "viewer.html"
    build(vault, out)
    html = out.read_text(encoding="utf-8")
    page = next(p for p in bundle(html)["pages"] if p["name"] == "12-trap")
    assert "<!--<script>" in page["body"]
    assert "<!--<script>" not in html


def test_built_file_carries_a_csp_whose_hashes_match_its_scripts(tmp_path):
    import base64
    out = tmp_path / "viewer.html"
    build(FIXTURE, out)
    html = out.read_text(encoding="utf-8")
    csp = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert html.index("Content-Security-Policy") < html.index("<script")
    for directive in ("default-src 'none'", "img-src data:", "connect-src 'none'", "frame-src 'none'",
                      "object-src 'none'", "base-uri 'none'", "form-action 'none'"):
        assert directive in csp
    assert "unsafe-eval" not in csp
    allowed = set(re.findall(r"'(sha256-[^']+)'", csp))
    inline = [m.group(1) for m in re.finditer(r"<script>(.*?)</script>", html, re.S)]
    assert len(inline) == 3  # marked, mermaid, the viewer
    actual = {"sha256-" + base64.b64encode(hashlib.sha256(src.encode("utf-8")).digest()).decode() for src in inline}
    assert actual == allowed


# The checks below run the real viewer in headless Chrome and audit the DOM it
# produced, with a local server that records every network request. They are the
# only tests that exercise marked, the sanitizer, mermaid and the CSP together.

CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",)
CHROME = next((p for p in CHROME_PATHS if pathlib.Path(p).exists()),
              shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chrome"))
needs_chrome = pytest.mark.skipif(CHROME is None, reason="headless Chrome is not installed, so the rendered DOM cannot be audited")

PAGE = """---
id: {title}
type: initiative-section
title: {title}
initiative: INI-900
state: decided
---
# {title}

{body}
"""


class Sensor(http.server.ThreadingHTTPServer):
    """A local server that records every request the viewer makes."""

    def __init__(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def handle_any(handler):
                self.requests.append(f"{handler.command} {handler.path}")
                handler.send_response(404)
                handler.end_headers()

            do_GET = do_HEAD = do_POST = do_OPTIONS = do_PUT = handle_any

            def log_message(handler, *args):
                pass

        self.requests = []
        super().__init__(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def base(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


def hostile_pages(base):
    img = f"<img src={base}/raw.png onerror=alert(1)>"
    return {
        "13-hostile-code": "\n\n".join([
            "\\`" + img + "`",
            "``" + img + "`",
            "`" + img + "``",
            "```a`b\n" + img + "\n```",
            "\t```\n" + img + "\n```",
            "\u00a0```\n" + img + "\n```",
            "- item\n  ```\n  " + img + "\n  ```",
            "- item\n\n      " + img,
            "[[01-goals|" + img + "]]",
            '\\`<div class="draft-banner gen diagram-error mermaid" id="props">claimed classes</div>`',
        ]),
        "14-hostile-comment": "```\n<!--<script>alert(1)</script>\n```\n\nafter the fence",
        "15-hostile-diagram": "\n\n".join([
            f"```mermaid\ngraph TD\n  A[\"<img src='{base}/m.png'>\"] --> B\n```",
            f'```mermaid\ngraph TD\n  A --> B\n  classDef x background-image:url({base}/class.png)\n  class A x\n  style B fill:#fff,background-image:url({base}/style.png)\n```',
        ]),
        "16-hostile-classic": "\n\n".join([
            "<script>alert(1)</script>", "<svg onload=alert(1)></svg>", f"<iframe src={base}/frame></iframe>",
            f"<style>body{{background:url({base}/s.png)}}</style>",
            '<a href="javascript:alert(1)" onclick="alert(2)">raw anchor</a>',
            "[x](javascript:alert(1)) [y](data:text/html,boo) [r][ref]", f"![p]({base}/p.png)",
            f"<img src={base}/plain.png>", "[ref]: javascript:alert(3)",
            "[slashes](//evil.test/x) [back](\\\\evil.test\\x)",
        ]),
        "17-broken-diagram": "```mermaid\nthis is not a diagram at all -->\n```",
        "18-hostile-directives": "\n\n".join([
            f'```mermaid\ngraph TD\n  A --> B\n%%{{init: {{"themeCSS": "background-image:url({base}/b1.png);"}}',
            f'```mermaid\n%%{{init: {{"htmlLabels": true, "flowchart": {{"htmlLabels": true}}}}\ngraph TD\n  A["x<img src=\\"{base}/b1b.png\\">"] --> B\n```',
            f'```mermaid\n%%{{init: {{"themeCSS": "g{{background:\\\\75rl({base}/b2.png)}}"}}}}%%\ngraph TD\n  A --> B\n```',
            f'```mermaid\n%%{{init: {{"themeCSS": "g{{background:image-set(\\"{base}/b2b.png\\" 1x)}}"}}}}%%\ngraph TD\n  A --> B\n```',
            f'```mermaid\n---\nconfig:\n  themeCSS: "g{{background:url({base}/fm.png)}}"\n---\ngraph TD\n  A --> B\n```',
        ]),
        "## Props": "A heading that is named after a viewer element.\n\n## Backlinks\n\nText.\n\n## Page\n\nText.\n",  # the reading view drops empty sections
    }


class Audit(HTMLParser):
    """Everything a hostile page could smuggle into the dumped DOM."""

    def __init__(self):
        super().__init__()
        self.tags, self.styles, self._style = [], [], False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self._style = tag == "style"

    def handle_endtag(self, tag):
        self._style = False

    def handle_data(self, data):
        if self._style:
            self.styles.append(data)


def audit(html):
    parser = Audit()
    parser.feed(html)
    return parser


def dump_dom(viewer_file, route):
    result = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=20000", "--dump-dom",
         f"file://{viewer_file}#/{route}"],
        capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr[-500:]
    return result.stdout


@pytest.fixture(scope="module")
def sensor():
    server = Sensor()
    yield server
    server.shutdown()


@pytest.fixture(scope="module")
def hostile_viewer(tmp_path_factory, sensor):
    tmp = tmp_path_factory.mktemp("hostile")
    vault = tmp / "mini"
    shutil.copytree(MINI, vault)
    for name, body in hostile_pages(sensor.base).items():
        title = name.lstrip("# ")
        file_name = f"{title.lower()}.md" if name.startswith("#") else f"{name}.md"
        (vault / file_name).write_text(PAGE.format(title=title, body=body), encoding="utf-8")
    out = tmp / "viewer.html"
    code, text = build(vault, out)
    assert code == 0, text
    return out


ROUTES = ["13-hostile-code", "14-hostile-comment", "15-hostile-diagram", "16-hostile-classic",
          "17-broken-diagram", "18-hostile-directives", "props"]


@needs_chrome
@pytest.mark.parametrize("route", ROUTES)
def test_hostile_page_renders_no_live_markup_and_makes_no_requests(hostile_viewer, sensor, route):
    built = audit(hostile_viewer.read_text(encoding="utf-8"))
    sensor.requests.clear()
    dom = audit(dump_dom(hostile_viewer, route))
    assert sensor.requests == [], f"the viewer fetched {sensor.requests}"
    names = [t for t, _ in dom.tags]
    for tag, attrs in dom.tags:
        assert not [a for a in attrs if a.startswith("on")], (tag, attrs)
        assert "src" not in attrs, (tag, attrs)
        for name, value in attrs.items():
            squeezed = re.sub(r"[\x00-\x20]", "", value or "").lower()
            assert not squeezed.startswith(("javascript:", "data:", "//", "\\")), (tag, name, value)
            if sensor.base in (value or ""):
                assert tag == "a" and name == "href", (tag, name, value)
    assert names.count("script") == [t for t, _ in built.tags].count("script")
    assert not {"img", "iframe", "image", "foreignobject", "object", "embed"} & set(names)
    assert not [css for css in dom.styles if sensor.base in css]
    assert [a for t, a in dom.tags if t == "a" and "data-name" in a], "the viewer did not render its page tree"


@needs_chrome
def test_hostile_code_page_shows_its_text_and_cannot_claim_viewer_classes(hostile_viewer):
    dom_text = dump_dom(hostile_viewer, "13-hostile-code")
    assert "&lt;img src=" in dom_text
    dom = audit(dom_text)
    assert "claimed classes" in dom_text
    claimed = [a for t, a in dom.tags if t == "div" and re.search(r"draft-banner|gen|diagram-error|mermaid", a.get("class", ""))]
    assert claimed == []
    assert [a.get("id") for t, a in dom.tags].count("props") == 1


@needs_chrome
def test_headings_named_like_viewer_elements_do_not_break_the_rail(hostile_viewer):
    dom = dump_dom(hostile_viewer, "props")
    assert '<h2 id="h-props">Props</h2>' in dom or 'id="h-backlinks"' in dom
    assert re.search(r'<ul id="backlinks">', dom) and re.search(r'<dl id="props">', dom)


@needs_chrome
def test_diagram_directives_are_refused_with_a_visible_box(hostile_viewer):
    dom_text = dump_dom(hostile_viewer, "18-hostile-directives")
    assert dom_text.count("diagram directives aren&#39;t allowed in the offline viewer") + \
        dom_text.count("diagram directives aren't allowed in the offline viewer") >= 5


@needs_chrome
def test_bad_route_falls_back_to_goals(hostile_viewer):
    for route in ("%E0%A4%A", "__proto__", "constructor"):
        dom = dump_dom(hostile_viewer, route)
        assert 'id="crumb">01-goals.md' in dom, route


@needs_chrome
def test_diagram_failure_shows_a_visible_box(hostile_viewer):
    dom = audit(dump_dom(hostile_viewer, "17-broken-diagram"))
    boxes = [a for t, a in dom.tags if t == "div" and "diagram-error" in a.get("class", "")]
    assert boxes, "a diagram that cannot be drawn must show a visible error box"


@needs_chrome
def test_fixture_viewer_draws_its_diagrams_and_generated_blocks_without_network(tmp_path, sensor):
    out = tmp_path / "viewer.html"
    build(FIXTURE, out)
    sensor.requests.clear()
    dom = audit(dump_dom(out, "booking-building-blocks"))
    assert sensor.requests == []
    classes = [a.get("class", "") for t, a in dom.tags if t == "div"]
    assert classes.count("mermaid") == 2
    assert not [c for c in classes if "diagram-error" in c]
    assert not [c for c in classes if c == "gen"], "generated blocks read as plain sections now, with no box"


GENERATED_ROUTES = {"05-building-blocks": "CON-007", "03-context-and-scope": "CON-006", "04a-capability-delta": "CAP-014",
                    "ferrymaster-building-blocks": "CON-006"}


@needs_chrome
@pytest.mark.parametrize("route", sorted(GENERATED_ROUTES))
def test_generated_diagrams_draw_under_the_csp_and_sanitizer(tmp_path, sensor, route):
    out = tmp_path / "viewer.html"
    build(FIXTURE, out)
    sensor.requests.clear()
    text = dump_dom(out, route)
    assert sensor.requests == []
    dom = audit(text)
    classes = [a.get("class", "") for t, a in dom.tags if t == "div"]
    assert classes.count("mermaid") >= 1, route
    assert not [c for c in classes if "diagram-error" in c], route
    assert "svg" in [t for t, _ in dom.tags]
    assert GENERATED_ROUTES[route] in text, f"{route} drew no {GENERATED_ROUTES[route]} label"


@needs_chrome
def test_override_banner_shows_the_text_in_the_browser_and_escapes_a_hostile_reason(tmp_path, sensor):
    vault = tmp_path / "mini"
    shutil.copytree(MINI, vault)
    hostile = "<script>alert(1)</script> <img src=" + sensor.base + "/x.png onerror=alert(2)>"
    body = (f"- **Override:** GATE-5 by @a on 2026-11-20: {hostile}\n- **Decided by:** @a, on behalf of @owner\n\nText.")
    (vault / "19-overridden.md").write_text(PAGE.format(title="19-overridden", body=body), encoding="utf-8")
    out = tmp_path / "viewer.html"
    code, text = build(vault, out)
    assert code == 0, text
    sensor.requests.clear()
    dom = dump_dom(out, "19-overridden")
    assert sensor.requests == []
    status = re.search(r'<div class="status-line">(decided on behalf.*?)</div>', dom, re.S).group(1)
    assert status == "decided on behalf of @owner, not yet confirmed"
    history = re.search(r"<details>(.*?)</details>", dom, re.S).group(1)
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &lt;img src=" in history
    tags = [t for t, _ in audit(dom).tags]
    assert "img" not in tags and tags.count("script") == 4
