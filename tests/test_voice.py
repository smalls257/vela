"""House-voice examples: license and attribution, copies in step, and the page-type map."""
import re

import pytest
import yaml

from conftest import REPO
from vela import schema

EXAMPLES = REPO / "plugin" / "template" / "voice" / "examples"
FILES = sorted(EXAMPLES.glob("*/*.md"))
VOICE_TYPES = ("diagnosis", "decision", "how-it-works")


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
def test_every_example_carries_license_and_attribution(path):
    meta, body = split(path)
    assert meta["id"] == path.stem
    assert meta["voice_type"] == path.parent.name
    assert meta["source"] == "public-seed"
    assert meta["license"] == "CC BY 3.0"
    assert meta["license_url"] == "https://creativecommons.org/licenses/by/3.0/"
    assert meta["author"] and meta["chapter"].startswith("Chapter ")
    assert meta["work"].startswith("The Architecture of Open Source Applications, Volume ")
    assert re.match(r"^https://aosabook\.org/en/v[12]/[a-z]+\.html$", meta["url"])
    assert meta["changes"].startswith("none")
    words = len(body.split())
    assert 80 <= words <= 300, f"{path.name} has {words} words"
    assert "[[" not in body


def test_only_public_seed_text_is_committed():
    """Evans, Luu and Fowler stay in the gitignored voice/corpus/. Nothing committed names them as a source."""
    for root in (REPO / "plugin" / "template", REPO / "examples" / "unified-booking", REPO / "plugin"):
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


# v2: the owner's examples, retiring, and the cap of five.

SEED_SKILL = REPO / "plugin" / "skills" / "voice-seed" / "SKILL.md"


def test_template_examples_use_the_schema_values():
    for path in FILES:
        meta, _ = split(path)
        assert meta["voice_type"] in schema.VOICE_TYPES
        assert meta["source"] in schema.VOICE_SOURCES
        assert meta["state"] in schema.VOICE_STATES
    for voice_type in schema.VOICE_TYPES:
        active = [p for p in (EXAMPLES / voice_type).glob("*.md") if split(p)[0]["state"] == "active"]
        assert len(active) <= schema.VOICE_ACTIVE_MAX


# fix round 2: local examples never change committed files; the verbatim check is a tool comparison.

def test_conventions_never_let_a_local_example_retire_a_committed_seed():
    conventions = (REPO / "plugin" / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "A local example never retires a committed seed, so every clone keeps its seed." in conventions
    assert "reads local `owner` and `owner-edit` examples ahead of the committed ones" in conventions


