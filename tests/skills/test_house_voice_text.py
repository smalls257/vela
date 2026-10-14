"""What the house-voice skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO
from vela import parse, schema


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def words(count, start=0):
    """Distinct words, so a long paragraph is not also a repeated phrase."""
    return " ".join(f"item{n}" for n in range(start, start + count)) + ". "


LINT = REPO / "plugin" / "references" / "lint-words.txt"


PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


VOICE_TYPES = ("diagnosis", "decision", "how-it-works")


MAP_VALUES = VOICE_TYPES + ("structured",)


SKILL = REPO / "plugin" / "skills" / "house-voice" / "SKILL.md"


def voice_map():
    text = SKILL.read_text(encoding="utf-8")
    section = text.split("## Page types and voice types", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| `([a-z0-9-]+)` \| ([a-z-]+) \|$", section, re.M)
    return dict(rows)


# --- From tests/test_cases.py: A contract's case table: the parser reads it, `vela check` warns when it is missing or
# cannot be trusted.


def test_house_voice_knows_the_case_table():
    from conftest import skill_text
    assert "case table" in skill_text("house-voice")


# --- From tests/test_final_wave.py: The last fix wave: the root README describes v2, and close, START, CONVENTIONS
# and the plugin manifest say what the code and the workflow actually do.

# M5: house-voice's no-examples line has a place in the PR body


def test_house_voice_says_when_it_drafted_without_examples():
    assert "No examples for <type>: drafted without examples" in read("plugin", "skills", "house-voice", "SKILL.md")


# --- From tests/test_readload.py: The second five reading-load warnings (design session 16): a paragraph, a table
# cell, a stock phrase, a template opening and an abbreviation that costs the reader more than a careful writer would.

# ------------------------------------------------------------------------------------------------ the lint word list (16-D2)


def test_house_voice_never_names_a_listed_word():
    """Naming a word in a prompt raises its odds, so the list lives in the lint and the reviewer, and the drafter never
    sees it."""
    from vela import reading
    words = reading.lint_words(LINT.read_text(encoding="utf-8"))
    relative = "skills/house-voice/SKILL.md"
    text = (REPO / "plugin" / relative).read_text(encoding="utf-8")
    for word in words:
        assert not reading.lint_pattern(word).search(text.replace("lint-words.txt", "")), f"{relative} names '{word}'"


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# house voice (V1-09): close now drafts prose through it, and only through it.


def test_house_voice_rules():
    voice = text("skills/house-voice/SKILL.md")
    assert "in file-name order" in voice
    assert "Never read `voice/corpus/`." in voice
    assert "Replaces the paragraph above" not in voice and "## Replaced prose" in voice  # a page never carries two openings
    assert "more than about 20 prose paragraphs" in voice
    assert "acceptance criteria, and the `- Trace:` line under each;" in voice and "`**Decision:**` and `**Dissent:**` lines;" in voice


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_house_voice_carries_the_plain_spoken_rules():
    """Design session 17: the writer persona, natural negatives, the true state once, about four things at once,
    no narrating the record, who said what kept, and the unknowns opening as the list-page example."""
    voice = text("skills/house-voice/SKILL.md")
    assert "senior technical writer explaining the system to a colleague" in voice
    assert "don't twist them into positives" in voice
    assert "Never make it sound more certain than the record" in voice
    assert "hold about four new things at once" in voice
    assert "not about the record" in voice and "## History" in voice
    assert "Who said what, and every state word" in voice
    assert "One open call holds up most of this page" in voice


def test_house_voice_protects_quoted_sentences_and_writes_capabilities_as_planned():
    """S51: the Heron rewrite broke 8 evidence quotes (E802). And capability prose said "the business can have" or
    "reads" for something not built; the user picked "will read"."""
    voice = text("skills/house-voice/SKILL.md")
    assert "a sentence another page quotes as evidence" in voice and "change the quote in the same edit" in voice and "E802" in voice
    assert "what the system will do" in voice and '"The Desktop agent will read' in voice and '"the business can have"' in voice


# --- From tests/test_voice.py: House-voice examples: license and attribution, copies in step, and the page-type map.


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


def test_house_voice_reads_only_active_examples():
    voice = SKILL.read_text(encoding="utf-8")
    assert "Read every example of that type whose frontmatter says `state: active`, in file-name order" in voice
    assert "Skip every `state: retired` example." in voice
    assert "If the type has fewer than two active examples" in voice
    assert "`/vela:voice-seed`" in voice


# fix round 1: write mechanism, risky lines, privacy, count and cap rules, quoting, final check.


def test_house_voice_reads_the_local_folder_too():
    voice = SKILL.read_text(encoding="utf-8")
    assert "`voice/local/<voice type>/*.md`" in voice
    assert "local `owner` and `owner-edit` examples first, then `voice/examples/`, then any other local example" in voice
    assert "fewer than two active examples across both folders" in voice


# fix round 2: local examples never change committed files; the verbatim check is a tool comparison.


def test_house_voice_reads_local_owner_examples_first():
    voice = SKILL.read_text(encoding="utf-8")
    assert "local `owner` and `owner-edit` examples first" in voice
