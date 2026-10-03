"""House-voice examples: licence and attribution, copies in step, and the page-type map."""
import re

import pytest
import yaml

from conftest import REPO
from planner import parse, schema

EXAMPLES = REPO / "template" / "voice" / "examples"
FILES = sorted(EXAMPLES.glob("*/*.md"))
VOICE_TYPES = ("diagnosis", "decision", "how-it-works")
MAP_VALUES = VOICE_TYPES + ("structured",)
SKILL = REPO / "plugin" / "skills" / "house-voice" / "SKILL.md"


def split(path):
    text = path.read_text(encoding="utf-8")
    _, head, body = text.split("---\n", 2)
    return yaml.safe_load(head), body


def test_two_or_three_examples_per_voice_type():
    for voice_type in VOICE_TYPES:
        count = len(list((EXAMPLES / voice_type).glob("*.md")))
        assert 2 <= count <= 3, f"{voice_type} has {count} examples"
    assert sorted(p.name for p in EXAMPLES.iterdir()) == sorted(VOICE_TYPES)


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_every_example_carries_licence_and_attribution(path):
    meta, body = split(path)
    assert meta["id"] == path.stem
    assert meta["voice_type"] == path.parent.name
    assert meta["source"] == "public-seed"
    assert meta["licence"] == "CC BY 3.0"
    assert meta["licence_url"] == "https://creativecommons.org/licenses/by/3.0/"
    assert meta["author"] and meta["chapter"].startswith("Chapter ")
    assert meta["work"].startswith("The Architecture of Open Source Applications, Volume ")
    assert re.match(r"^https://aosabook\.org/en/v[12]/[a-z]+\.html$", meta["url"])
    assert meta["changes"].startswith("none")
    words = len(body.split())
    assert 80 <= words <= 300, f"{path.name} has {words} words"
    assert "[[" not in body


def test_only_public_seed_text_is_committed():
    """Evans, Luu and Fowler stay in the gitignored voice/corpus/. Nothing committed names them as a source."""
    for root in (REPO / "template", REPO / "examples" / "unified-booking", REPO / "plugin"):
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"\b(Evans|Luu|Fowler)\b", text), f"{path} names a corpus author"
        assert not list(root.rglob("corpus/*")), f"{root} holds corpus files"


def test_fixture_examples_equal_the_template():
    fixture = REPO / "examples" / "unified-booking" / "voice" / "examples"
    got = sorted(p.relative_to(fixture).as_posix() for p in fixture.glob("*/*.md"))
    assert got == sorted(p.relative_to(EXAMPLES).as_posix() for p in FILES)
    for path in FILES:
        assert (fixture / path.relative_to(EXAMPLES)).read_bytes() == path.read_bytes()


def voice_map():
    text = SKILL.read_text(encoding="utf-8")
    section = text.split("## Page types and voice types", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| `([a-z0-9-]+)` \| ([a-z-]+) \|$", section, re.M)
    return dict(rows)


def test_voice_map_values():
    mapping = voice_map()
    assert mapping, "the house-voice skill has no page-type table"
    for key, value in mapping.items():
        assert value in MAP_VALUES, f"{key} maps to {value}"


def test_every_page_type_has_a_voice_type():
    mapping = voice_map()
    for page_type in schema.PAGE_TYPES:
        assert page_type in mapping, f"page type {page_type} has neither a voice type nor structured"


def test_every_template_page_resolves_to_a_voice_type():
    mapping = voice_map()
    template = REPO / "template"
    for path in template.rglob("*.md"):
        rel = path.relative_to(template)
        if rel.parts[0] in ("voice", ".github") or rel.name in schema.SKIP_FILES:
            continue
        page = parse.parse_page(rel.as_posix(), path.read_text(encoding="utf-8"))
        assert page.id in mapping or page.type in mapping, f"{rel} ({page.id}, {page.type}) has no voice type"
