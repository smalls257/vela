"""The two side columns' room: one EdgeSize (panelsize.js) serves the right-hand panel and the left-hand sections bar,
so both hide, drag and remember the same way. The browser checks the behavior (the selftest's panel and sections bar
lines); this checks the page carries it, and that the sidebar's old copy of the hide logic is gone from nav.js."""
from conftest import REPO
from test_explorer import booking  # noqa: F401  (a fixture)

JS = REPO / "plugin" / "lib" / "vela" / "explorer" / "assets" / "js"


def test_the_page_carries_one_edge_factory_for_both_columns(booking):  # noqa: F811
    page, _ = booking
    assert page.count("function EdgeSize(") == 1
    assert 'id="side-grip" role="separator"' in page and 'aria-controls="side" tabindex="0"' in page
    assert 'grip: $("#side-grip")' in page and 'grip: $("#panel-grip")' in page
    assert 'widthKey: "explorer.side.width"' in page and 'hiddenKey: "explorer.side"' in page


def test_nav_no_longer_keeps_its_own_hidden_flag():
    nav = (JS / "nav.js").read_text(encoding="utf-8")
    assert "SIDE_KEY" not in nav and "side-hidden" not in nav and "#side-toggle" not in nav


def test_the_selftest_checks_the_sections_bar():
    selftest = (JS / "selftest.js").read_text(encoding="utf-8")
    assert "async function sideRoom()" in selftest and "await sideRoom();" in selftest
