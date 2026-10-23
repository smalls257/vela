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
    """The page-type table lives in the CLI (`vela voice examples --key`); the skill carries no copy."""
    from vela import voiceplan
    return dict(voiceplan.PAGE_VOICE)


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
    assert "Replaces the paragraph above" not in voice and "## Replaced prose" not in voice  # a page never carries two openings; the file is the command's
    assert "more than about 20 prose paragraphs" not in voice and "`vela close drafts --json`" not in voice  # rule deletion: close owns the size question
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
    assert "Who said what, and every state, number, date and negation" in voice
    assert "Keep the state, not the record's word for it" in voice


def test_house_voice_explains_in_the_opening_and_keeps_items_short():
    """The user's 12 blind picks (2026-10-21): fuller openings for a reader who wasn't in the sessions, short items
    under them, the state said by its verb and never tagged on, and plain words even where the record says "gates"."""
    voice = text("skills/house-voice/SKILL.md")
    assert "someone on the team who wasn't in the sessions" in voice
    assert "The opening paragraph of a page does most of the explaining" in voice
    assert "Say a point's state with its verb, once" in voice and '"That isn\'t decided."' in voice
    assert "never vela's own, even where the record uses it" in voice
    assert "One open call holds up most of this page" in voice


def test_house_voice_protects_quoted_sentences_and_writes_capabilities_as_planned():
    """S51: the Heron rewrite broke 8 evidence quotes (E802). And capability prose said "the business can have" or
    "reads" for something not built; the user picked "will read"."""
    voice = text("skills/house-voice/SKILL.md")
    assert "a sentence another page quotes as evidence" in voice and "change the quote in the same edit" in voice
    assert "E802" not in voice  # rule deletion: `vela check` names the code
    assert "what the system will do" in voice and '"The Rider app will unlock' in voice and '"the business can have"' in voice


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
    template = REPO / "plugin" / "template"
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
    assert "`/vela:voice-seed`" not in voice and "public seed retires" not in voice  # rule deletion: `voice save` retires it


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


def test_the_page_type_table_is_the_clis_alone():
    """Rule deletion: the table and its copy are gone; a page with no file yet asks the command with `--key`."""
    voice = SKILL.read_text(encoding="utf-8")
    assert not SKILL.with_name("TYPES.md").exists()
    assert "TYPES.md" not in voice and "## Page types and voice types" not in voice and "| `goals` |" not in voice
    assert "`--key <page id or type>` for a page with no file yet" in voice


def test_merged_prose_is_copied_by_the_cli():
    voice = SKILL.read_text(encoding="utf-8")
    assert "`vela prose replace --page 05-building-blocks/till.md --line 12` (any line of the paragraph will do)" in voice
    assert "Never copy it by hand." in voice
    assert "byte for byte" not in voice and "with the page and the date" not in voice  # rule deletion: the command's doing


def test_the_moved_numbers_are_gone_from_the_rules():
    """Rules 2, 6 and 7 keep their judgment; their numbers live in `vela check` (W365) and `close drafts` only."""
    voice = SKILL.read_text(encoding="utf-8")
    for gone in ("at most about 80 words", "under 120 words", "about four", "limit of about 80 words",
                 "Split into PRs by page group", "whose frontmatter says `state: active`"):
        assert gone not in voice, gone
    assert "## Size" not in voice and "split them by section" not in voice  # rule deletion: `close drafts` asks it


def test_house_voice_names_only_commands_that_exist():
    import shlex
    from vela import cli
    parser = cli.build_parser()
    text = SKILL.read_text(encoding="utf-8")
    found = re.findall(r"`vela ((?:voice|prose|close|check) [^`]*)`", text)
    assert len(found) >= 2, found
    for call in found:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)



def test_the_voice_rule_covers_what_ifs():
    from conftest import REPO
    voice = (REPO / "plugin/skills/house-voice/SKILL.md").read_text(encoding="utf-8")
    assert "A what-if is framed as one" in voice and "never reports a new event" in voice


def test_house_voice_stays_lean():
    """Sensor against regrowth: the skill was 2,856 words before the voice and the rules were merged (now 2,462)."""
    assert len(SKILL.read_text(encoding="utf-8").split()) <= 2540
