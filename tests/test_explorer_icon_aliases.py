"""A vault written before the American spelling still says `icon: catalogue` or `icon: callcentre`.

Without the read-both alias those names would quietly drop to a keyword guess and a "not in the built-in set"
note; this file feeds the British names and expects the same glyph the American names draw, with no warning.
"""
import re
from pathlib import Path

from planner.explorer import icons_data

ICONS_JS = Path(icons_data.__file__).parent / "assets/js/icons.js"
GLYPH = re.compile(r"^\s{4}([a-z]+): \"M", re.M)


def test_the_british_icon_names_draw_the_american_glyph():
    assert icons_data.choose("Zephyr", asked="catalogue") == ("catalog", "icon: catalogue on its page")
    assert icons_data.choose("Zephyr", asked="callcentre") == ("callcenter", "icon: callcentre on its page")


def test_the_american_icon_names_are_the_built_in_ones():
    assert icons_data.choose("Zephyr", asked="catalog") == ("catalog", "icon: catalog on its page")
    assert icons_data.choose("Zephyr", asked="callcenter") == ("callcenter", "icon: callcenter on its page")
    glyphs = set(GLYPH.findall(ICONS_JS.read_text(encoding="utf-8")))
    assert set(icons_data.ICON_ALIASES.values()) <= glyphs
    assert not set(icons_data.ICON_ALIASES) & glyphs  # the old names live only in the alias table


def test_a_british_icon_name_is_not_reported_as_unknown():
    nodes = [{"key": "APP-a", "title": "Zephyr"}, {"key": "APP-b", "title": "Qwerty"}, {"key": "APP-c", "title": "Hum"}]
    meta = {"APP-a": {"icon": "catalogue"}, "APP-b": {"icon": "callcentre"}, "APP-c": {"icon": "rocket"}}
    icons, unknown = icons_data.for_map(nodes, {}, {}, meta)
    assert icons["APP-a"]["icon"] == "catalog" and icons["APP-b"]["icon"] == "callcenter"
    assert unknown == [("APP-c", "rocket")]
