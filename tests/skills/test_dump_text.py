"""What the dump skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex

from conftest import REPO
from vela import cli

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ the checkpoints replace the sweeps


def test_dump_runs_the_checkpoint_after_the_pre_mortem_and_the_sweep_is_gone():
    dump = text("skills/dump/SKILL.md")
    assert "references/REVIEW.md" in dump and '"after the pre-mortem"' in dump
    assert "concern sweep" not in dump
    assert "nobody has named yet" not in dump
    assert "to fetch:" in dump


def test_dump_leaves_the_checks_every_area_makes_to_the_agent():
    body = text("skills/dump/SKILL.md")
    assert "Add to that focus" not in body and "who gains and who loses" not in body
    assert "service levels" not in body


def test_round_two_fixes_in_dump():
    dump = text("skills/dump/SKILL.md")
    assert "is not a verdict on any idea" in dump
    assert "Never present the checkpoint's digest as a verdict" in dump
    assert 'type at close: PTY' in dump and 'type at close: SV' in dump
    assert "any contract or document the captures themselves name" in dump


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_dump_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/dump/SKILL.md"), "dump must stay the lead's to start"


def test_dump_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/dump/SKILL.md")
    assert "Closing a session" in body, "dump must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_dump_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/dump/SKILL.md")


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# Session start, dump and close (V1-08). Each assertion pins a rule whose loss would be silent.


def test_dump_writes_captures_only():
    dump = text("skills/dump/SKILL.md")
    assert "Never edit a page outside `sessions/` during a dump." in dump
    assert "pre-mortem" in dump
    assert "Do not run close yourself." not in dump


# --- From tests/test_v3_final_fixes.py: The v3 final fix wave.

# ------------------------------------------------------------------ 2. a yes to an existence question is one flow


def test_dump_captures_a_yes_as_one_capture_that_starts_with_the_copy_id():
    dump = text("skills/dump/SKILL.md")
    assert "`- [thought] (<name>) Q-FIN-01@INI-001: yes, <what>. type at close: SV`" in dump


# --- From tests/test_vault_title.py: S49: the first session asks for the initiative's short name once, and vela check
# warns (W718) while the vault still carries the title the template ships.


def test_dump_asks_once_for_the_initiatives_short_name():
    text = (PLUGIN / "skills" / "dump" / "SKILL.md").read_text(encoding="utf-8")
    assert "asks once for the initiative's short name" in text


# --- Overhaul Task 22g: `vela record add` numbers the captures; the conversation stays the skill's. No `vela checkpoint`
# exists yet, so "checkpoint after about every ten" stays as written (no rule-deletion assert for it).


DUMP = text("skills/dump/SKILL.md")


def test_dump_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = re.findall(r"scripts/vela ([a-z][^`]*)`", DUMP) + re.findall(r"`vela ([a-z][^`]*)`", DUMP)
    assert calls, "dump names no vela call"
    for call in calls:
        argv = shlex.split(re.sub(r"<[^<>]*>", "X", call))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_capture_numbering_is_the_commands_not_the_models():
    assert "record add --origin" in DUMP and "never number one yourself" in DUMP
    assert not re.search(r"\^c(?:NN|\d)", DUMP)  # no hand arithmetic over ^cNN


def test_dump_says_a_yes_to_the_lead_in_words():
    assert "Noted: the plan holds money or points on customers' behalf." in DUMP
    assert "noted, there is stored value" not in DUMP


# The topic map rides on `vela record add` (probe batch A, 2026-10-16: sessions never ran `vela map next` and barely
# ran `vela map add`, so skill prose about the map changed nothing). One line says it; batch A's multi-step map prose
# coming back fails the rule-deletion test, since steps the sessions skipped only look like steering.
RECORD_MAP_LINE = ("then ask the question its `next:` line suggests, in the voice; while the lead is mid-account, let "
                   "them finish")
OLD_MAP_PROSE = ("vela map add", "vela map next", "vela map open", "vela map close", "vela map show",
                 "## The running map", "Tag as you go", "Park, don't interrupt", "Pick the next question from the map",
                 "Who has a say.", "A clash, side by side.", "A gap, named.", "Confirm in batches.",
                 "The read-back settles everything.")


def test_dump_says_the_record_map_line_once():
    body = DUMP
    assert body.count(RECORD_MAP_LINE) == 1
    assert "`--kind`" in body and '`--group "<group>"`' in body


def test_dump_has_no_multi_step_map_prose():
    body = DUMP
    for phrase in OLD_MAP_PROSE:
        assert phrase not in body, phrase
