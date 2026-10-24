"""The renders say what the JSON says, in plain words, safely, and small."""
import json
import re

import pytest

from companion_vault import grill_session, run_companion
from vela import companionrender, companionsvg, say


@pytest.fixture
def data(tmp_path):
    root = grill_session(tmp_path)
    code, out = run_companion(root, "session", "--json")
    assert code == 0, out
    return root, json.loads(out)


def visible(html_text):
    body = re.sub(r"<style.*?</style>|<svg.*?</svg>", " ", html_text, flags=re.S)
    return re.sub(r"<[^>]+>", " ", body)


def test_the_markdown_has_no_html_tables_or_mermaid(data):
    _, got = data
    md = companionrender.markdown(got)
    assert "<" not in md and not re.search(r"^\|", md, re.M) and "```mermaid" not in md
    assert "Hold, pay, confirm" in md and "decided today" in md and "Pricing runtime" in md


def test_lead_text_names_things_and_holds_no_ids_or_paths(data):
    root, got = data
    for text in (companionrender.markdown(got), visible(companionrender.html(got, "")), companionrender.band(got)):
        assert say.leak_in(text) is None, say.leak_in(text)


def test_the_band_fits_a_narrow_window_and_names_the_command(data):
    _, got = data
    line = companionrender.band(got)
    assert len(line) <= companionrender.BAND_WIDTH and line.endswith("/vela-companion to open")
    assert "2 decided" in line and "1 open" in line


def test_the_html_stands_alone_and_stays_small(data):
    _, got = data
    page = companionrender.html(got, ":root { --room: #0d1317; }")
    assert "<script" not in page and "http://" not in page and "https://" not in page
    assert len(page.encode("utf-8")) < 200_000
    assert "as of 10:41" in page and "capture 14" in page and "dashboard.html in this folder" in page


def test_vault_text_is_escaped_everywhere():
    steps = [{"n": 1, "from": "<img src=x onerror=alert(1)>", "to": "Booking", "text": "</svg><script>x</script>"}]
    svg = companionsvg.sequence(steps, "<b>flow</b>")
    assert "<script" not in svg and "<img" not in svg and "<b>" not in svg
    assert "&lt;img" in svg and "&lt;script&gt;" in svg and "&lt;b&gt;" in svg


def test_a_long_flow_stays_under_the_svg_limit():
    steps = [{"n": n, "from": f"App {n % 7}", "to": f"App {(n + 1) % 7}", "text": "w" * 300} for n in range(1, 200)]
    assert len(companionsvg.sequence(steps, "Long")) < companionsvg.MAX_CHARS


def test_the_written_files_match_the_renders(data):
    root, got = data
    folder = root / ".vela" / "companion"
    assert (folder / "session.md").read_text(encoding="utf-8") == companionrender.markdown(got)


def test_an_unreadable_session_says_so_in_every_form(tmp_path):
    from vela import companionsession
    got = companionsession.unreadable({"id": "x", "title": "Grill: x", "modes": ["grill"], "date": "2026-10-24"},
                                      "missing", "2026-10-24", "10:00")
    for text in (companionrender.markdown(got), visible(companionrender.html(got, ""))):
        assert "I can't read this session's notes on this machine." in text and "Decided" not in text
