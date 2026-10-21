"""What the ask skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

import yaml
from conftest import REPO
from test_skill_commands_exist import calls, is_a_mention, parse_error
from vela import cli

PLUGIN = REPO / "plugin"


ASK = PLUGIN / "skills" / "ask" / "SKILL.md"


VELA_TOOL = "Bash(python3 *scripts/vela *)"  # the one loose pattern, ruled in design session 15


# The voice load line: the owner's VOICE.md, then the plugin's conversation voice, in that order on one line.
VOICE_LINE = re.compile(r"^.*`voice/VOICE\.md`.*references/CONVERSATION-VOICE\.md.*$", re.M)


def ask_meta():
    return yaml.safe_load(ASK.read_text(encoding="utf-8").split("---\n", 2)[1])


def read(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_ask_query.py: /ask resolves every ID through vela query before citing it, and never cites a
# not_found.


def test_ask_runs_vela_by_the_one_loose_pattern_and_stays_read_only_by_disallowed_tools():
    allowed = ask_meta()["allowed-tools"]
    assert VELA_TOOL in allowed and allowed.count("scripts/vela") == 1
    assert "Write" not in allowed.split() and "Edit" not in allowed.split()
    assert ask_meta()["disallowed-tools"] == "Write Edit NotebookEdit"


def test_ask_resolves_every_id_before_citing_it():
    ask = ASK.read_text(encoding="utf-8")
    assert "Before you cite any ID, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela query get <ID> --json`." in ask
    assert "The ID stays behind the scenes." in ask
    assert "If the answer is `not_found`, never cite that ID" in ask
    assert "`Not recorded: <ID> is not in this vault.`" in ask
    assert "vela query find <words> --json" in ask and "vela query refs <ID> --json" in ask
    assert "`vela query` only reads." in ask
    assert "If `vela query` exits 2" in ask and "never treat that as `not_found`" in ask
    assert "say in one plain sentence that you couldn't check the items in this answer" in ask  # never raw tool text


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_ask_reports_an_override_and_an_unconfirmed_decision():
    ask = read("skills", "ask", "SKILL.md")
    assert '"(decided by override: <rule>, by @x)"' in ask and '"(decided by @x without the owner present, not yet confirmed)"' in ask


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S36 to S47


def test_ask_cannot_cat_any_file():
    meta = text("skills/ask/SKILL.md").split("---\n", 2)[1]
    assert "Bash(cat" not in meta


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# /ask (V1-15)


def test_ask_answers_from_opened_sections_and_marks_what_is_missing():
    ask = text("skills/ask/SKILL.md")
    assert "Never search or Read a file under `voice/` or `.inbox/`, other than `voice/VOICE.md` for how to talk." in ask
    assert "Cite nothing you did not open in this answer." in ask
    assert "`Not recorded:`" in ask and "`Not decided:`" in ask
    assert "Never create, edit or delete a file." in ask
    assert "Sources:" in ask


def test_ask_fix_round_bash_read_only_and_every_claim_sourced():
    ask = text("skills/ask/SKILL.md")
    assert "Never redirect output (`>`, `>>`)." in ask
    for banned in ("`tee`", "`sed -i`", "`git commit`", "`git checkout`", "`git log --output`", "`vela render`"):
        assert banned in ask
    assert "writes a file or changes git state" in ask
    assert "Every claim rests on a page in the `Sources:` list or is labeled `Not from the vault:`. There is no third choice." in ask
    assert "Name each thing in the sentence by its plain name, not its ID." in ask  # the lead reads names; IDs sit in Sources
    assert "Assert nothing you did not open and read. A Grep snippet alone does not count." in ask
    assert "Search and Read `sessions/` only if the question asks about a session or what was said." in ask
    assert "When `state` is `current`, say nothing about freshness." in ask  # a lead who asks a question does not read a commit hash first


# --- Task 22k: the overhaul rewrite. ask was the main source of raw IDs the lead read in the mid-point run
# (/tmp/compare/diagnosis.md section 3): its Sources list required an ID per line. Now it names pages by heading.


def test_ask_has_no_bang_injection_and_runs_freshness_as_a_normal_step():
    ask = text("skills/ask/SKILL.md")
    assert not re.search(r"^!", ask, re.M)  # Cowork doesn't run `!` lines (P19)
    assert "How fresh this clone is" not in ask
    steps = ask.split("## Steps", 1)[1]
    assert steps.index("vela freshness --json") < steps.index("vela query search")
    assert "This answer comes from a copy that is 4 changes behind the latest plan (last updated October 10)." in ask
    assert "Never say a branch, a commit or the command's message." in ask
    for gone in ("Bash(git log *)", "Bash(git rev-list *)", "Bash(date *)"):
        assert gone not in ask_meta()["allowed-tools"], gone


def test_ask_loads_the_voice_before_it_says_anything():
    body = text("skills/ask/SKILL.md").split("---\n", 2)[2]
    line = VOICE_LINE.search(body).group(0)  # VOICE.md first, then the conversation voice
    assert body.index(line) < body.index("## Steps") < body.index("vela freshness")


def test_ask_names_sources_by_page_heading_with_the_id_only_on_request():
    ask = text("skills/ask/SKILL.md")
    shape = ask.split("## Answer shape", 1)[1]
    assert "- <page title> · <section heading> · <state in words>" in shape
    assert "<ID>" not in shape and "<path>" not in shape
    assert "`- Unknowns and risks · Handoff date and form · open`" in shape
    assert "When the asker asked for IDs, tag it: `- Unknowns and risks · Handoff date and form · open · UNK-051`." in shape
    assert "An ID goes in only when the asker named the item by its ID or asks for IDs" in ask


def test_ask_shows_the_inline_parenthetical_it_must_not_write_and_its_right_form():
    names = text("skills/ask/SKILL.md").split("## Names, not IDs", 1)[1].split("\n## ", 1)[0]
    assert 'Don\'t write: "The handoff date is still open (UNK-051, due October 21)."' in names
    assert 'Write: "Nobody has settled the handoff date and form yet. Sam is to answer it by October 21."' in names


def test_ask_flags_read_in_words():
    ask = text("skills/ask/SKILL.md")
    for flag in ('"(just an idea)"', '"(not decided yet)"', "(nobody has looked at data protection for the dock app yet)",
                 "(the dock app's team lead hasn't confirmed it)",
                 "It came up in the October 12 desks session but nobody has filed it."):
        assert flag in ask, flag
    for old in ("unexamined: nobody", "assumed: not confirmed", "the <app> senior", "An unpromoted capture"):
        assert old not in ask, old


def test_ask_description_is_short_and_has_no_angle_brackets():
    description = ask_meta()["description"]
    assert len(description) <= 250 and "<" not in description and ">" not in description


def test_ask_names_only_commands_that_exist():
    parser = cli.build_parser()
    found = list(calls(ASK))
    assert len(found) >= 5, found
    for line, written, argv in found:
        assert is_a_mention(parser, argv) or parse_error(parser, argv) is None, (line, written)
