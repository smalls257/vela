"""The "How vela thinks" site under docs/method/. The Violation these tests hold off is the one-page wall: the old
METHOD.html was 18,600 words with no way in. So: a page opens with a count and holds four to seven sections (the
builder refuses otherwise), the home offers four to seven places to start, the committed pages match their Markdown
source, every link and image lands on a real file, and the whole site stays well under the old page."""
import pathlib
import re
import sys

import pytest

from conftest import REPO

DOCS = REPO / "docs"
SITE = DOCS / "method"
sys.path.insert(0, str(DOCS))
import render_method  # noqa: E402

WORD_CEILING = 12_000  # the old single page was 18,600


@pytest.fixture(scope="module")
def built():
    return render_method.build_all()


def test_committed_pages_match_their_markdown(built):
    stale = [name for name, text in built.items() if (SITE / f"{name}.html").read_text(encoding="utf-8") != text]
    assert not stale, f"run python3 docs/render_method.py: {stale}"


def test_home_offers_four_to_seven_places_to_start(built):
    entries = built["index"].count('class="entry"')
    assert render_method.MIN_SECTIONS <= entries <= render_method.MAX_SECTIONS


def test_every_topic_opens_with_a_count_of_its_sections(built):
    for name in render_method.ORDER:
        sections = built[name].count("<section id=")
        assert render_method.MIN_SECTIONS <= sections <= render_method.MAX_SECTIONS, name
        assert f"{render_method.NUMBER_WORDS[sections]} things below." in built[name], name


def test_the_site_is_well_under_the_old_single_page(built):
    assert sum(render_method.visible_words(text) for text in built.values()) < WORD_CEILING


def test_a_page_with_eight_sections_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(render_method, "SRC", tmp_path)
    (tmp_path / "refs.md").write_text("", encoding="utf-8")
    body = "\n".join(f"## S{i}\ntext\n" for i in range(8))
    (tmp_path / "wall.md").write_text(f"---\ntitle: Wall\nlede: x\n---\n{body}", encoding="utf-8")
    with pytest.raises(render_method.PageError, match="8 sections"):
        render_method.build_page("wall", {}, {})


def test_every_link_and_image_lands_on_a_real_file(built):
    missing = []
    for name, text in built.items():
        for target in re.findall(r'(?:href|src)="([^"#:]+)(?:#[^"]*)?"', text):
            base = DOCS / "site" if target == "../index.html" else SITE  # the home page sits one level up once published
            home = base / "index.html" if base != SITE else SITE / target
            if not home.resolve().exists():
                missing.append(f"{name}.html -> {target}")
    assert not missing, missing


def test_a_page_never_loads_anything_from_the_network(built):
    for name, text in built.items():
        assert not re.search(r'(?:src|href)="https?://', text.replace('<a href="https://', "")), name
    assert "http" not in (SITE / "method.css").read_text(encoding="utf-8").replace("https://github.com", "")


def test_every_page_carries_the_theme_toggle_and_the_shared_storage_key(built):
    """The choice must carry between the landing page and the method pages, so one key and one button everywhere."""
    pages = dict(built)
    pages["landing"] = (DOCS / "site" / "index.html").read_text(encoding="utf-8")
    for name, text in pages.items():
        assert 'id="theme-toggle"' in text, name
        assert text.count('"vela-theme"') == 2, name  # read before first paint, written on click
        assert text.index("localStorage.getItem") < text.index("<body"), f"{name}: the saved theme must apply before first paint"
        assert "Switch to " in text, name
    assert render_method.THEME_HEAD in pages["landing"] and render_method.THEME_BUTTON in pages["landing"]
