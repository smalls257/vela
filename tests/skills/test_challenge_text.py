"""What the challenge skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shlex
import shutil

import yaml
from conftest import REPO, run
from vela import cli
from vela.commands import close_stage


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


PLUGIN = REPO / "plugin"


SKILL = PLUGIN / "skills" / "challenge" / "SKILL.md"


def skill_text_challenge():
    return SKILL.read_text(encoding="utf-8")


def read_override(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_answer.py: Answering a challenge: START opens an answer session on the challenge's own branch, a
# Grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_challenge_sends_the_lead_to_the_answer_path():
    challenge = read("plugin", "skills", "challenge", "SKILL.md")
    assert "Run `/vela:grill` and name this PR or <ID>" in challenge
    assert "opens an answer session on this branch" in challenge


def test_challenge_accepts_reopened_to_decided_for_an_epic():
    assert "| EPC-nnn | reopened | decided |" in read("plugin", "skills", "challenge", "SKILL.md")


# --- From tests/test_challenge.py: /vela:challenge: a senior's challenge after handoff becomes an open unknown they
# own, which blocks the item, and a Dissent line on it.


def test_challenge_is_the_leads_to_start():
    meta = yaml.safe_load(skill_text_challenge().split("---\n", 2)[1])
    assert meta["name"] == "challenge" and meta["disable-model-invocation"] is True


def test_challenge_never_changes_the_item_and_never_decides():
    text = skill_text_challenge()
    assert "Never touch the item's `state:`, `**State:**`, wording, criteria or any other line." in text
    assert "Never change the challenged item's state or text. Only the `**Dissent:**` line is added." in text
    assert "Never decide, resolve, reopen or set back anything. Only a grill decides" in text
    assert "never argue the item's side" in text


def test_challenge_resolves_the_id_and_shows_what_changed_since_handoff():
    text = skill_text_challenge()
    assert "sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela query get <ID> --json" in text
    assert "If it says `not_found`, stop" in text and "Do not guess another ID." in text
    assert "sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela handoff verify <APP-id> --for-lead" in text
    assert "Never cite an ID that `vela query get` reports `not_found`." in text


def test_challenge_writes_an_unknown_the_senior_owns():
    text = skill_text_challenge()
    assert "- **Owner:** @<team lead's handle> (<their role>)" in text
    assert "- **Blocks:** [[<page>#<heading>|<ID>]]" in text
    assert "- **Dissent:** <team lead's handle>, <today>: <the reason in a few words>" in text
    assert "Never name anyone but the team lead as the open question's owner." in text
    assert "vela next-id UNK" in text and "counts `main` and every open session branch" in text  # the command counts; the skill does not


def test_challenge_asks_the_solution_lead_in_a_pr():
    text = skill_text_challenge()
    assert "The reviewer is the solution lead: the `owner:` of `01-goals.md`." in text
    assert "a contract to `assumption`, an epic to `reopened`" in text
    assert "Never say a PR exists unless `gh` printed its URL." in text  # the hard stop stays pinned


# What the skill writes, applied to a copy of the fixture: the check turns red with E316 and
# the senior's handoff verify names the change. The contract itself is untouched.


def test_the_pr_says_the_red_check_is_deliberate_and_blocks_the_merge():
    text = skill_text_challenge()
    assert "E316 is deliberate." in text
    assert "blocks the merge wherever vela-check is a required check" in text
    assert "either by resolving `UNK-nnn` with a grill or by setting the item back" in text
    conv = (REPO / "plugin" / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "deliberate" in conv and "blocks the merge" in conv


def test_handoff_verify_exit_2_has_two_cases_and_the_skill_shows_the_message():
    text = skill_text_challenge()
    assert "read the tool's message to tell them apart; it's for you, not the team lead" in text
    assert 'If it says "doesn\'t exist", there is no manifest' in text  # the words the CLI prints, pinned below
    assert "could not be read, and go on without claiming anything" in text


def test_the_next_unknown_number_is_highest_plus_one_and_the_session_id_names_the_item():
    text = skill_text_challenge()
    assert "use exactly what it prints" in text and "a number is never handed out twice" in text
    assert "highest `UNK-nnn` in use plus one" not in text  # a dead hand method: vela next-id does it
    assert "at the end of `## Unknowns`, before `## Risks`" in text.replace("Add the entry at", "at")
    assert "`<date>-challenge-<id-lowercased>`" in text
    assert "E316 fires once per item" in text


# --- From tests/test_next_id.py: vela next-id: a number an open session branch already holds is never handed out
# again (UNK-026 twice, heron run).


def test_challenge_numbers_new_unknowns_with_the_command_not_by_eye():
    from conftest import REPO
    assert "vela next-id UNK" in (REPO / "plugin" / "skills/challenge/SKILL.md").read_text(encoding="utf-8")


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_challenge_knows_the_decided_by_bullet():
    challenge = read_override("skills", "challenge", "SKILL.md")
    assert "on behalf of @owner" in challenge and "`decided_by`" in challenge


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_challenge_refuses_in_a_reader_copy_naming_the_owner():
    assert "Only the owner can record a challenge here." in text("skills/challenge/SKILL.md") and "published.json" in text("skills/challenge/SKILL.md")


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S36 to S47


def test_a_challenge_promises_a_red_check_only_for_a_decided_item():
    challenge = text("skills/challenge/SKILL.md")
    assert "Never promise a red check for an item that is not `decided`." in challenge


# --- Overhaul Task 22h: the rewrite onto session start, close stage and the team lead's words.

def test_challenge_names_only_commands_that_exist():
    parser = cli.build_parser()
    calls = re.findall(r"`vela ((?:session|close|record|whoami|next-id|role|query|handoff) [^`]*)`", skill_text_challenge())
    # named in prose, not run as written: why the skill doesn't run them, and whose output a line means
    named_not_run = {"close finish", "close push", "query get", "handoff verify"}
    calls = [c for c in calls if c not in named_not_run]
    assert len(calls) >= 4, calls
    for call in calls:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_the_session_opens_with_session_start_and_files_with_close_stage():
    text = skill_text_challenge()
    assert "`vela session start --mode challenge --topic <ID> --for-lead`" in text
    assert "`vela close stage --session <id> --close --paths-from-render`" in text
    # rule deletion: staging by exact path is the command's now, with its reason in its docstring
    assert "Never use `git add -A`" not in text and "Stage every file `vela render` reported" not in text
    assert "git add -A" in close_stage.__doc__ and "allow-list" in close_stage.__doc__
    # the close commands' gate counts the deliberate red check as an error, so the skill says why it files itself
    assert "`vela close finish` and `vela close push` stop on the deliberate red check" in text


def test_nothing_is_sent_without_the_team_leads_yes():
    text = skill_text_challenge()
    assert 'I\'ll send this challenge for review to <the solution lead\'s name>. OK?' in text
    assert '--mark "drop: the yes to send this for review"' in text
    assert text.index("OK?") < text.index("git push -u origin session/<id>") < text.index("gh pr create")


def test_handoff_verify_says_doesnt_exist_when_there_is_no_manifest(tmp_path, capsys):
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    code, out = run("handoff", "verify", "APP-pricing", "--vault", str(vault))
    said = out + capsys.readouterr().err
    assert code == 2 and "doesn't exist" in said, said


def test_the_team_lead_hears_names_not_codes():
    text = skill_text_challenge()
    meta = yaml.safe_load(text.split("---\n", 2)[1])
    assert len(meta["description"]) <= 250
    assert "senior" not in text.lower() and "Grill" not in text and "vault" not in text.split("## 1.", 1)[1]
    assert "Here's what changed since you took the app on." in text
    assert "There's no record of what you accepted at handover" in text
    assert "I'd challenge only the contract." in text
    assert "|<short name>]])`" in text  # the Dissent link reads as the question's name, not its number
    assert "I've added the open question 'Hold expiry under load'" in text  # the worked read-back, by name
