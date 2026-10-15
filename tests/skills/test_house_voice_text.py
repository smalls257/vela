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
TYPES = REPO / "plugin" / "skills" / "house-voice" / "TYPES.md"


def voice_map():
    """The page-type table, which moved to TYPES.md (Task 22i): read only when `voice examples --page` can't resolve."""
    text = TYPES.read_text(encoding="utf-8")
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
    assert "more than about 20 prose paragraphs" in voice and "`vela close drafts --json`" in voice
    assert "acceptance criteria, and the `- Trace:` line under each;" in voice and "`**Decision:**` and `**Dissent:**` lines;" in voice


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_house_voice_carries_the_plain_spoken_rules():
    """Design session 17: the writer persona, natural negatives, the true state once, about four things at once,
    no narrating the record, who said what kept, and the unknowns opening as the list-page example."""
    voice = text("skills/house-voice/SKILL.md")
    assert "senior technical writer explaining the system to a colleague" in voice
    assert "don't twist them into positives" in voice
    assert "Never make it sound more certain than the record" in voice
    assert "hold only a few new things at once" in voice
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


def test_house_voice_reads_the_examples_voice_examples_lists():
    voice = SKILL.read_text(encoding="utf-8")
    assert "run `vela voice examples --page <page> --json`" in voice
    assert "Read every example of that type it lists, in the order it lists them" in voice
    assert "active examples in file-name order" in voice
    assert "fewer than two active examples" in voice
    assert "`/vela:voice-seed`" in voice


# fix round 1: write mechanism, risky lines, privacy, count and cap rules, quoting, final check.


def test_house_voice_states_the_order_conversation_voice_relies_on():
    """CONVERSATION-VOICE reads the conversation examples by hand "in the order house-voice fixes"."""
    voice = SKILL.read_text(encoding="utf-8")
    assert "local `owner` and `owner-edit` examples first, then `voice/examples/`, then any other local example" in voice
    assert "fewer than two active examples across both folders" in voice


# fix round 2: local examples never change committed files; the verbatim check is a tool comparison.


def test_house_voice_reads_local_owner_examples_first():
    voice = SKILL.read_text(encoding="utf-8")
    assert "local `owner` and `owner-edit` examples first" in voice


# --- Task 22i: the table moved to TYPES.md, the order and the copy to the CLI, the thresholds to `check`.


def test_the_types_table_and_the_code_table_are_one_table():
    """`voice examples --page` reads `voiceplan.PAGE_VOICE`; TYPES.md is what the model reads when it can't. Two copies
    that drift send a draft to the wrong examples, so they are pinned equal."""
    from vela import voiceplan
    assert voice_map() == voiceplan.PAGE_VOICE


def test_house_voice_reads_types_only_when_the_command_cannot_resolve():
    voice = SKILL.read_text(encoding="utf-8")
    assert "## Page types and voice types" not in voice and "| `goals` |" not in voice
    assert "When the command can't resolve the page, read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/TYPES.md`" in voice
    assert "vela voice examples --type how-it-works --json` with that voice type" in TYPES.read_text(encoding="utf-8")


def test_merged_prose_is_copied_by_the_cli():
    voice = SKILL.read_text(encoding="utf-8")
    assert "`vela prose replace --page 05-building-blocks/till.md --line 12` with the page and any line of the paragraph" in voice
    assert "Never copy it by hand." in voice


def test_the_moved_numbers_are_gone_from_the_rules():
    """Rules 2, 6 and 7 keep their judgment; their numbers live in `vela check` (W365) and `close drafts` only."""
    voice = SKILL.read_text(encoding="utf-8")
    for gone in ("at most about 80 words", "under 120 words", "about four", "limit of about 80 words",
                 "Split into PRs by page group", "whose frontmatter says `state: active`"):
        assert gone not in voice, gone
    assert "Send them for review as one batch, or split them by section (apps, flows, the rest)?" in voice


def test_house_voice_names_only_commands_that_exist():
    import shlex
    from vela import cli
    parser = cli.build_parser()
    text = SKILL.read_text(encoding="utf-8") + TYPES.read_text(encoding="utf-8")
    found = re.findall(r"`vela ((?:voice|prose|close|check) [^`]*)`", text)
    assert len(found) >= 3, found
    for call in found:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)
