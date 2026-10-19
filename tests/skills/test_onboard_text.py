"""What the onboard skill says, pinned in one place. The rules live in code (`vela onboard`); the skill only talks.

The Violations these guard against: a Paper Tiger (a skill that asks nothing and hands everyone the same path), an
invented fact (a skill that adds modules or people the plan doesn't hold) and a Leaky Narrative (a skill that shows
the lead an id or a file format). Each is held by a sentence the skill must keep.
"""
import re

import yaml
from conftest import REPO
from vela import cli, onboarding

SKILL = REPO / "plugin" / "skills" / "onboard" / "SKILL.md"
VOICE_LINE = re.compile(r"^.*`voice/VOICE\.md`.*references/CONVERSATION-VOICE\.md.*$", re.M)


def parts():
    _, head, body = SKILL.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(head), body


def test_the_skill_loads_the_voice_before_it_says_anything():
    _, body = parts()
    assert body.index(VOICE_LINE.search(body).group(0)) < body.index("## Steps")


def test_only_the_person_starts_it_and_it_can_only_run_vela_and_open_a_page():
    meta, _ = parts()
    assert meta["name"] == "onboard" and meta["disable-model-invocation"] is True
    assert meta["allowed-tools"] == "Read Bash(python3 *scripts/vela *) Bash(uname *) Bash(open *) Bash(xdg-open *)"
    assert "Write" not in meta["allowed-tools"] and "Edit" not in meta["allowed-tools"]
    assert len(meta["description"]) <= 250 and "<" not in meta["description"] and ">" not in meta["description"]


def test_it_is_short_because_the_rules_are_in_code():
    _, body = parts()
    assert len(body.strip().splitlines()) < 45
    assert "Everything you say comes from what `vela onboard` prints" in body


def test_it_asks_the_role_what_they_need_and_whether_they_want_diagrams_or_explanations():
    _, body = parts()
    assert "Which is closest: exec sponsor, product owner, engineer, QA lead, delivery manager or solution lead?" in body
    assert "`roleSource`" in body and "keep it with `vela whoami --role <role>`" in body and "Never ask twice." in body
    assert "What would help most before you talk to people" in body
    assert "diagrams, explanations or both" in body
    assert body.count("one question") >= 2, "one question at a time, with a recommendation"


def test_it_builds_the_path_only_from_the_plans_modules_and_reads_it_back_before_writing():
    _, body = parts()
    assert "Choose from the plan's modules and nothing else." in body and "vela onboard modules --json" in body
    assert "wait for a yes" in body and "Never invent a module or a fact" in body
    for name in ("Goal", "Approach", "Where things stand", "Where you fit", "Who to talk to"):
        assert name.casefold() in onboarding.BY_NAME and name in body


def test_it_writes_through_the_command_and_names_the_leads_hide_as_the_leads_call():
    _, body = parts()
    assert "vela onboard path set --role <role> --modules" in body and "--bring-back" in body
    assert "The only thing you write is `vela onboard path set` or `clear`." in body
    assert "the lead hid it" in body and "it is recorded" in body
    assert "ask for their GitHub handle once and run `vela whoami --set <handle>`" in body


def test_it_never_assigns_work_never_quizzes_and_never_shows_a_code():
    _, body = parts()
    assert "never assign work or a first task, and you never quiz them" in body
    assert "Names, never IDs or module codes." in body
    assert "Never add a fact, an owner, a date or a reason" in body


def test_it_works_where_there_are_no_hooks_and_no_git():
    _, body = parts()
    assert "`START.md`, \"Where vela runs from\"" in body and "Cowork" in body
    assert "Nothing here uses git, so it works in a reader copy too." in body
    assert "`uname`" in body and "`open <file>`" in body and "`xdg-open <file>`" in body and "Never say it is open unless the command succeeded." in body


def test_every_command_it_names_is_one_the_parser_has_and_the_rest_is_held_by_the_registry_tests():
    _, body = parts()
    parser = cli.build_parser()
    for verb in ("show --role eng", "modules", "check", "path set --role eng --modules Goal", "path clear"):
        argv = ["onboard", *verb.split()]
        assert parser.parse_args(argv).func, verb
    for named in ("`vela onboard show --role <role> --for-lead`", "`vela onboard modules --json`", "`vela onboard path set --role <role> --modules", "`vela onboard path clear`"):
        assert named in body, named


def test_a_step_runs_the_check_on_the_leads_page_and_says_its_mistakes_in_one_sentence():
    _, body = parts()
    steps = body.split("## Steps")[1].split("## Rules")[0]
    step = next(line for line in steps.splitlines() if "`vela onboard check`" in line)
    assert step.lstrip().startswith("2.") and "one sentence" in step and "the lead's page to fix" in step
    assert body.count("`vela onboard check`") == 1, "one place says it, in the steps"
