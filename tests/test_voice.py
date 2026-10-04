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


def test_house_voice_reads_only_active_examples():
    voice = SKILL.read_text(encoding="utf-8")
    assert "Read every example of that type whose frontmatter says `state: active`, in file-name order" in voice
    assert "Skip every `state: retired` example." in voice
    assert "If the type has fewer than two active examples" in voice
    assert "`/planner:voice-seed`" in voice


def test_voice_seed_stores_the_owner_words_and_never_rewrites_them():
    seed = SEED_SKILL.read_text(encoding="utf-8")
    assert "It never rewrites them." in seed
    assert "Never rewrite, shorten, correct or paraphrase the owner's words." in seed
    assert "Did you write this yourself?" in seed and "wait for an explicit yes to each" in seed
    assert "Store an accepted passage as it was pasted." in seed
    assert "Never write under `voice/corpus/`." in seed


def test_voice_seed_retires_the_seed_only_once_the_owner_has_two():
    seed = SEED_SKILL.read_text(encoding="utf-8")
    assert "A type the owner gave at least 2 passages" in seed
    assert "Set `state: retired` on every `source: public-seed` example of that type" in seed
    assert "Never delete a seed example" in seed
    assert "A type with fewer than 2 owner passages keeps its seed." in seed
    assert f"A type holds at most {schema.VOICE_ACTIVE_MAX}." in seed


def test_voice_seed_commits_by_path_and_never_claims_a_pr():
    seed = SEED_SKILL.read_text(encoding="utf-8")
    assert "Never use `git add -A`." in seed
    assert "Never say a PR exists unless `gh` printed its URL." in seed
    assert "gh api user -q .login" in seed


def test_the_example_voice_seed_writes_has_only_documented_fields():
    seed = SEED_SKILL.read_text(encoding="utf-8")
    block = seed.split("## 4. Write the examples", 1)[1].split("```\n", 2)[1]
    filled = (block.replace("<type>", "decision").replace("NNN", "004").replace("<handle>", "hl-solution-lead")
              .replace("<where it comes from>", "design review").replace("<today>", "2026-11-20"))
    meta = yaml.safe_load(filled.split("---\n")[1])
    assert str(meta["added"]) == "2026-11-20"  # YAML reads an unquoted date as a date
    assert {k: v for k, v in meta.items() if k != "added"} == {
        "id": "VX-decision-004", "voice_type": "decision", "source": "owner", "author": "@hl-solution-lead",
        "from": "design review", "state": "active"}
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    for key in meta:
        assert f"`{key}`" in conventions, key
