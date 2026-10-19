"""The dashboard's controls ride on the diagram as menus, and three things are gone: sound, the ripple of Impact, and
the Animation switch. The browser side (menus switch views, the keys, closing, 800 px) is the page's own #selftest, run
by test_explorer_browser.py; these checks are the ones a grep can make, so a removed feature cannot creep back in."""
import pathlib
import re

import pytest

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "plugin" / "lib" / "vela" / "explorer" / "assets"
BUILD = ASSETS.parent / "build.py"
SOURCES = sorted(p for p in ASSETS.rglob("*") if p.suffix in {".js", ".css", ".html"} and not p.name.startswith("selftest"))  # the selftest names what must be gone


def hits(pattern):
    rx = re.compile(pattern)
    return [f"{p.relative_to(ASSETS)}:{n}" for p in SOURCES for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if rx.search(line)]


def test_no_sound_code_remains():
    assert not (ASSETS / "js" / "sound.js").exists()
    assert '"sound"' not in BUILD.read_text(encoding="utf-8")
    found = hits(r"AudioContext|createOscillator|\bSound\.|\bSound\b\s*=|sound-btn|id=\"sound\"|\bchime\b|Web Audio")
    assert not found, f"sound code is back: {found}"


def test_no_ripple_or_impact_mode_remains():
    found = hits(r"ripple|rippling|rp-on|rp-wave|data-ring|Nav\.ripple|Impact: what depends|FX\.(motion|MOTIONS|setMotion)|explorer\.motion")
    assert not found, f"the ripple or the Impact mode is back: {found}"


def test_the_animation_switch_is_gone_and_nothing_about_effects_is_remembered():
    assert 'id="fx"' not in (ASSETS / "shell.html").read_text(encoding="utf-8")
    fx = (ASSETS / "js" / "fx.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in fx and "Settings." not in fx and "explorer.effects" not in fx


def test_the_controls_are_menus_with_the_aria_a_menu_needs():
    menus = (ASSETS / "js" / "menus.js").read_text(encoding="utf-8")
    for needed in ('"aria-haspopup": "menu"', '"aria-expanded"', 'role: "menu"', "menuitemradio", "menuitemcheckbox", '"Escape"', '"ArrowDown"', '"Home"', "pointerdown"):
        assert needed in menus, f"menus.js lacks {needed}"
    assert "menus" in re.search(r"JS_MODULES = \((.*?)\)", BUILD.read_text(encoding="utf-8"), re.S).group(1)


@pytest.mark.parametrize("view", ["view-map.js", "view-flows.js", "view-asks.js", "slices.js", "view-decisions.js"])
def test_each_view_with_toggles_puts_them_on_its_diagram(view):
    source = (ASSETS / "js" / view).read_text(encoding="utf-8")
    assert "Menus.menu(" in source or "Menus.frame(" in source, f"{view} has no menu on its diagram"
    assert 'aria-label": "Lens"' not in source and 'aria-label": "Due within"' not in source
