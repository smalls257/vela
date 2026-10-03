import hashlib
import json
import re
import shutil

from conftest import REPO, edit, run

FIXTURE = REPO / "examples" / "unified-booking"
ASSETS = REPO / "plugin" / "lib" / "planner" / "assets"
ASSET_SHA256 = {
    "marked.min.js": "15fabce5b65898b32b03f5ed25e9f891a729ad4c0d6d877110a7744aa847a894",
    "mermaid.min.js": "61b335a46df05a7ce1c98378f60e5f3e77a7fb608a1056997e8a649304a936d6",
}


def build(vault, out):
    return run("view", "--vault", str(vault), "--out", str(out), "--date", "2026-11-20",
               "--commit", "abc1234", "--repo-url", "https://github.example/harbourline/unified-booking")


def bundle(html):
    raw = re.search(r'<script id="vault" type="application/json">(.*?)</script>', html, re.S).group(1)
    return json.loads(raw.replace("<\\/", "</"))


def test_assets_are_the_pinned_versions():
    for name, digest in ASSET_SHA256.items():
        assert hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() == digest, name


def test_viewer_builds_offline_from_the_fixture(tmp_path):
    out = tmp_path / "viewer.html"
    code, text = build(FIXTURE, out)
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]*\bsrc\s*=", html)
    assert not re.search(r"<link[^>]*\bhref\s*=", html)
    assert "fonts.googleapis" not in html
    data = bundle(html)
    paths = [p["path"] for p in data["pages"]]
    assert not [p for p in paths if p.startswith(("sessions/", "voice/", ".claude/"))]
    assert data["start"] == "01-goals" and "01-goals.md" in paths
    assert data["stamp"] == {"commit": "abc1234", "date": "2026-11-20",
                             "repo": "https://github.example/harbourline/unified-booking"}
    assert "Built from ${DATA.stamp.commit} on ${DATA.stamp.date}. Newer versions: ${DATA.stamp.repo}" in html


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
    assert "Working draft: not agreed yet" in html


def test_diagram_failure_shows_a_visible_box():
    html_source = (REPO / "plugin" / "lib" / "planner" / "viewer.py").read_text(encoding="utf-8")
    assert "box.className = 'diagram-error'" in html_source
    assert "Diagram not drawn: " in html_source


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
