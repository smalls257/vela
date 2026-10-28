"""The gate hooks' decisions: what counts as bypassing the hooks, which tests a change needs, and when Stop blocks."""
import importlib.util
import pathlib

import pytest
import yaml

from conftest import REPO

spec = importlib.util.spec_from_file_location("gates", REPO / ".claude" / "hooks" / "gates.py")
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


@pytest.mark.parametrize("command", [
    "git push --no-verify origin main", "git commit -n -m wip", "git commit -am x --no-verify",
    "cd vault && git -c core.hooksPath=/dev/null push", "git config core.hooksPath .", "rm -rf .githooks",
    "chmod -x .githooks/pre-push",
])
def test_commands_that_skip_the_hooks_are_named(command):
    assert gates.bypass_reason(command)


@pytest.mark.parametrize("command", ["git push origin main", "git log -n 5", "git commit -m 'no -n here'",
                                     "python3 -m pytest -q", "ls .githooks"])
def test_ordinary_commands_pass(command):
    assert gates.bypass_reason(command) is None


def test_a_changed_vela_module_needs_its_test_file_and_cli_needs_none():
    changed = ["plugin/lib/vela/releases.py", "plugin/lib/vela/cli.py", "tests/test_search.py", "README.md"]
    assert gates.tests_for(changed) == ["tests/test_releases.py", "tests/test_search.py"]


def test_stop_blocks_once_then_tells_the_user_instead_of_looping():
    assert gates.stop_decision([], already_continuing=False) is None
    assert gates.stop_decision(["x"], already_continuing=False)["decision"] == "block"
    assert "decision" not in gates.stop_decision(["x"], already_continuing=True)


@pytest.mark.parametrize("command", ["git push -n origin main", "git merge -n feature"])
def test_dash_n_skips_hooks_only_on_commit(command):
    assert gates.bypass_reason(command) is None


@pytest.mark.parametrize("command", [
    "python3 -m pytest -q -n auto tests/test_gates.py\ngit commit -m 'x'",
    "git commit -m x\npython3 -m pytest -n 4",
    "git add a.py && git commit -m x && python3 -m pytest -n auto",
    "git commit -m \"$(cat <<'EOF'\nfix the -n parse\nEOF\n)\"\npython3 -m pytest -n auto",
    "git commit -m -n",            # git takes "-n" as the message
    "git commit -F msg.txt -- -n",  # after --, a pathspec
])
def test_dash_n_outside_git_commit_options_passes(command):
    assert gates.bypass_reason(command) is None


@pytest.mark.parametrize("command", [
    "git commit -m x -n", "git commit -nm x", "git commit -am x -n", "git -C repo commit -n -m x",
    "python3 -m pytest -n auto\ngit commit -n -m x", "git commit \\\n  -n -m x", "ls\ngit push --no-verify",
])
def test_dash_n_on_git_commit_still_skips_the_hooks(command):
    assert gates.bypass_reason(command) == "skips the git hooks"


@pytest.mark.parametrize("command", ["git config core.hooksPath .githooks", "git config --get core.hooksPath"])
def test_turning_the_hooks_on_or_reading_the_setting_passes(command):
    assert gates.bypass_reason(command) is None


@pytest.mark.parametrize("command", ["git config --unset core.hooksPath", "git config core.hooksPath /tmp/none"])
def test_turning_the_hooks_off_is_named(command):
    assert gates.bypass_reason(command)


def test_the_setting_named_inside_a_commit_message_is_not_a_change():
    assert gates.bypass_reason("git commit -m 'core.hooksPath to .githooks turns the hooks on'") is None


IGNORE = (REPO / ".semgrepignore").read_text().splitlines()


@pytest.mark.parametrize("path", ["plugin/lib/vela/assets/d3.min.js", "plugin/lib/yaml/__init__.py",
                                  ".semgrep/assets.js",
                                  "plugin/lib/vela/__pycache__/x.py"])
def test_files_semgrepignore_names_are_not_scanned_even_when_named(path):
    # Naming a file on semgrep's command line scans it despite .semgrepignore; a generated page then pasted
    # whole base64 lines into the Stop hook's feedback and pushed a session past its context window.
    assert gates.semgrep_ignores(path, IGNORE)


@pytest.mark.parametrize("path", ["tests/fixtures/explorer/build.py", "plugin/lib/vela/explorer/assets/js/core.js",
                                  "tests/sim/test_x.py", "plugin/lib/vela/assets/app.js"])
def test_hand_written_files_are_scanned(path):
    assert not gates.semgrep_ignores(path, IGNORE)


def rule_paths():
    """(rule file, rule id, glob) for every path a semgrep rule includes or excludes."""
    for rules_file in sorted((REPO / ".semgrep").glob("*.yaml")):
        for rule in yaml.safe_load(rules_file.read_text(encoding="utf-8"))["rules"]:
            for glob in sum((rule.get("paths") or {}).values(), []):
                yield rules_file.name, rule["id"], glob


@pytest.mark.parametrize("file,rule,glob", list(rule_paths()))
def test_every_path_a_semgrep_rule_names_still_exists(file, rule, glob):
    # A rule whose path matches nothing passes every scan, so a move that leaves it watching an empty place is
    # invisible unless something checks. The part of the glob before its first wildcard must exist.
    fixed = []
    for part in pathlib.PurePosixPath(glob.lstrip("/")).parts:
        if any(c in part for c in "*?["):
            break
        fixed.append(part)
    assert REPO.joinpath(*fixed).exists(), f"{file}: {rule} names {glob}, which is not in the repo"


def test_the_asset_slot_rule_watches_the_explorer_where_it_lives_now():
    # The explorer's page code lives in the plugin; the rule that keeps its JS to slot ids
    # has to follow it, or it passes by scanning nothing.
    globs = [g for _, rule, g in rule_paths() if rule == "asset-by-slot-id"]
    assert "/plugin/lib/vela/explorer/**" in globs
    assert (REPO / "plugin/lib/vela/explorer/assets/js/assets.js").is_file()


# ================================================================== grill gate verdicts (overhaul Task 13)
# `plugin/lib/vela/gates.py` shares this file's name with the hooks module above, and the Stop hook maps each vela
# module to tests/test_<module>.py, so its tests live here. The grill skill used to search the unknowns page for
# `**Blocks:**` itself while E316 does the same search in code: one rule in two places (Distributed Monolith). These pin
# the one place that now computes the stage, preferred-option, open-question, case-table and flow-check conditions per
# item, and that the plain `--gate decide` output the skills already read did not move.
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402

from conftest import edit, run  # noqa: E402
from vela import cli, say  # noqa: E402
from vela import gates as grill  # noqa: E402
from vela.flowcheck import standing  # noqa: E402

FIXTURE = REPO / "examples" / "unified-booking"
BOOKING = "05-building-blocks/booking-building-blocks.md"
UNKNOWNS = "11-unknowns-and-risks.md"
SLICE = "slices/SLC-001-website-books-through-booking.md"
TODAY = "2026-11-20"

CON_001_STATE = "- **State:** decided\n- **Decision:** [[2026-08-26-kiosks-and-rollout]]\n"
CON_002_STATE = "- **State:** decided\n- **Decision:** [[2026-11-03-events]]\n"
OPEN = "- **State:** assumption\n- **Options considered:** versioned API picked; one shared schema rejected (kiosks update twice a year)\n"
BUS_DOWN = ("| bus_down | | error | the event bus is down: the Event publisher keeps the events and publishes them in order "
            "when it returns, so none are lost | | |\n")
UNKNOWN = """
### UNK-099 Who owns booking holds

- **Question:** Who decides how long a hold lasts before the seat goes back on sale?
- **Owner:** @hl-booking-senior (Booking senior)
- **Opened:** 2026-11-19 Grill
- **Ask by:** 2026-11-30
- **State:** open
- **Blocks:** [[booking-building-blocks|Booking]]
"""


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    edit(dest / BOOKING, CON_001_STATE, OPEN)
    edit(dest / BOOKING, CON_002_STATE, OPEN)
    return dest


def block_booking(vault):
    text = (vault / UNKNOWNS).read_text(encoding="utf-8")
    (vault / UNKNOWNS).write_text(text.replace("\n### UNK-001 ", UNKNOWN + "\n### UNK-001 ", 1), encoding="utf-8")


def judge(vault, item, record=None, today=TODAY, flows=None):
    return grill.verdict(cli.load_vault(vault), record, item, today, flows=flows)


def rules_of(found):
    return [r.rule for r in found.reasons]


# ------------------------------------------------------------------ first callers

def test_an_open_question_is_listed_not_refused(ub):
    assert judge(ub, "CON-001").open_blockers == (), "without the unknown there is nothing to note"
    block_booking(ub)
    for item in ("CON-001", "CON-002"):
        found = judge(ub, item)
        assert found.ready and found.open_blockers == ("UNK-099",), (item, found)
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "decide", "--item", "CON-001", "--for-lead")
    assert code == 0 and "still has an open question under it" in out and "how long a hold lasts" in out, out
    assert "UNK-099" not in out and "Settling notes it as still open." in out, out


def test_a_requirement_needs_no_options(ub):
    page = ub / BOOKING
    page.write_text(page.read_text(encoding="utf-8").replace(OPEN, "- **State:** assumption\n"), encoding="utf-8")
    assert "GATE-2" not in rules_of(judge(ub, "CON-001")), "a contract at assumption settles without options"


def test_the_strategy_still_needs_options(ub):
    page = ub / "04-solution-strategy.md"
    text = page.read_text(encoding="utf-8")
    assert "id: solution-strategy" in text
    text = re.sub(r"(?m)^- \*\*Options considered:\*\*.*\n", "", text)
    text = re.sub(r"(?m)^state: .*$", "state: assumption", text, count=1)
    page.write_text(text, encoding="utf-8")
    assert "GATE-2" in rules_of(judge(ub, "solution-strategy"))


def test_contract_without_error_case_not_ready(ub):
    edit(ub / BOOKING, BUS_DOWN, "")
    found = judge(ub, "CON-002")
    assert not found.ready and rules_of(found) == ["case table"]
    assert "Booking state changed" in found.reasons[0].plain and "goes wrong" in found.reasons[0].plain
    assert found.fix == found.reasons[0].fix and "boundary session" in found.fix
    assert '"case table"' in found.route and "until" not in found.route, "no end date is suggested"


def test_contract_with_no_case_table_at_all_not_ready(ub):
    text = (ub / BOOKING).read_text(encoding="utf-8")
    start = text.index("| Case |", text.index("### CON-002"))
    end = text.index("## Contract kept here")
    (ub / BOOKING).write_text(text[:start] + text[end:], encoding="utf-8")
    found = judge(ub, "CON-002")
    assert not found.ready and rules_of(found) == ["case table"]
    assert "Nobody has written down" in found.reasons[0].plain


def test_not_fully_checked_can_be_set_aside(ub):
    passed = {"SLC-001": standing.Standing(standing.PASSED, "passed", "2026-11-19")}
    assert judge(ub, "SLC-001", flows=passed).ready
    partial = {"SLC-001": standing.Standing(standing.NOT_FULLY, "not fully checked", "2026-11-19")}
    found = judge(ub, "SLC-001", flows=partial)
    assert not found.ready and rules_of(found) == ["flow check"]
    assert "not fully checked" in found.reasons[0].plain
    assert '--override \'"flow check"\'' in found.route and "--reason-from ^cR" in found.route
    page = ub / SLICE
    page.write_text(page.read_text(encoding="utf-8") + "\n- **Override:** \"flow check\" by @hl-solution-lead "
                    "on 2026-11-19 until 2026-12-31: the budget ran out\n", encoding="utf-8")
    found = judge(ub, "SLC-001", flows=partial)
    assert found.ready and len(found.overridden) == 1, "the lead's word sets aside a check that did not finish"
    missing = judge(ub, "SLC-001", flows={})
    assert missing.ready, "an override on the slice covers a check that was not run, too"


def test_a_slice_never_checked_is_not_ready(ub):
    missing = judge(ub, "SLC-001")
    assert not missing.ready and "hasn't been run" in missing.reasons[0].plain, "no record is never a pass (R0)"


LEDGER_ROW_START = "| Q-DAT-02@APP-* |"


def drop_dat_02(vault):
    text = (vault / UNKNOWNS).read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(LEDGER_ROW_START)) + "\n"
    edit(vault / UNKNOWNS, row, "")


def test_w807_answered_in_record_is_skipped(ub):
    drop_dat_02(ub)
    everything = judge(ub, "CON-001")
    assert everything.ready, "an owed question is a question to ask, not a gate"
    assert sorted(everything.owed) == ["Q-DAT-02@APP-call-center", "Q-DAT-02@APP-kiosks", "Q-DAT-02@APP-website"]
    record = ("## Captures\n\n- [thought] (Head of Data) Q-DAT-02@APP-kiosks: kiosks keep no customer data ^c03\n"
              "- [decision] (Solution lead) decided with Q-DAT-02@APP-website open (W807) ^c04\n")
    assert sorted(judge(ub, "CON-001", record).owed) == ["Q-DAT-02@APP-call-center", "Q-DAT-02@APP-website"], \
        "an answer skips its copy; a decided-with-it-open note is not an answer"
    wildcard = "- [thought] (Head of Data) Q-DAT-02@APP-*: no channel keeps customer data ^c05\n"
    assert judge(ub, "CON-001", wildcard).owed == ()


def test_for_lead_reason_names_the_thing(ub):
    block_booking(ub)
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "decide", "--item", "CON-001",
                    "--item", "CON-007", "--for-lead")
    assert code == 1, out
    assert "Booking API" in out and "how long a hold lasts" in out, out
    assert not any(say.leak_in(line) for line in out.splitlines()), out


def test_json_carries_each_verdict_for_decide(ub):
    block_booking(ub)
    edit(ub / BOOKING, BUS_DOWN, "")
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "decide", "--item", "CON-001", "--item",
                    "CON-002", "--json")
    assert code == 1
    found = json.loads(out)
    assert found["ready"] is False
    item = next(i for i in found["items"] if i["id"] == "CON-001")
    assert {"id", "ready", "reasons", "fix", "override", "overridden", "owed", "open_blockers"} <= set(item)
    assert item["open_blockers"] == ["UNK-099"] and item["reasons"] == []
    broken = next(i for i in found["items"] if i["id"] == "CON-002")
    assert broken["reasons"][0]["rule"] == "case table" and "blocked_by" not in broken["reasons"][0]


def test_all_ready_exits_0(ub):
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "decide", "--item", "CON-001", "--for-lead")
    assert code == 0 and "Booking API" in out and "ready" in out, out


def test_already_decided_item_is_said_so(ub):
    found = judge(ub, "CON-007")
    assert not found.ready and rules_of(found) == ["GATE-2", "case table"], "it has no error case either"
    assert "already" in found.reasons[0].plain


def test_app_below_target_stage_fails_the_stage_condition(ub):
    # no source at all: the app's pages reach only baseline
    edit(ub / BOOKING, 'sources: ["Booking senior container review", "UNK-001 ledger latency measurement 2026-09-02", SRC-04, SRC-05]', "sources: []")
    found = judge(ub, "CON-001")
    assert not found.ready and "GATE-1" in rules_of(found)


def test_check_without_for_lead_unchanged(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    drop_dat_02(vault)
    run("render", "--vault", str(vault))
    code, out = run("check", "--vault", str(vault), "--today", TODAY, "--gate", "decide", "--item", "CON-001",
                    "--item", "ADR-0001")
    assert code == 0
    assert "Checking the open questions that hold up the items you'd decide. Items: " in out.splitlines()[0]
    assert len([line for line in out.splitlines() if " W807 " in line]) == 3
    assert run("check", "--vault", str(vault), "--gate", "decide", "--item", "CON-099", "--for-lead")[0] == 2
    assert run("check", "--vault", str(vault), "--json")[0] == 2, "--json goes with --gate decide --item"


# ------------------------------------------------------------------ --all: one call finds what is ready

def test_gate_all_lists_every_waiting_item_with_the_ready_ones_first(ub):
    ids = grill.candidates(cli.load_vault(ub))
    assert "CON-001" in ids and "CON-002" in ids
    edit(ub / BOOKING, BUS_DOWN, "")
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "decide", "--all", "--json")
    data = json.loads(out)["items"]
    assert {i["id"] for i in data} == set(ids)
    flags = [i["ready"] for i in data]
    assert flags == sorted(flags, reverse=True)  # ready first
    assert any(not f for f in flags)


def test_gate_all_refuses_a_named_item_and_a_non_decide_gate(ub):
    assert run("check", "--vault", str(ub), "--gate", "decide", "--all", "--item", "CON-001")[0] == 2
    assert run("check", "--vault", str(ub), "--gate", "shape", "--all")[0] == 2
