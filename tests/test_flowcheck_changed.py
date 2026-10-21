"""The flow check scoped by an impact walk: what a change touches, the recorded results it reuses, and
`check-slice --changed` / `--all` on a real git repo. Fixture: tests/fixtures/flowcheck/30-impact-walk, three slices
(SLC-001 holds an item; SLC-002 pays for it and SLC-003 looks up the stock, both after SLC-001)."""
import json
import shutil
import subprocess

import pytest

from conftest import REPO, run

from vela import flowcheck
from vela.flowcheck import changed, impact, readers, record

FIXTURES = REPO / "tests" / "fixtures" / "flowcheck"
WALK = "30-impact-walk"
TODAY = "2026-10-14"
BILLING = "05-building-blocks/billing-building-blocks.md"
INVENTORY = "05-building-blocks/inventory-building-blocks.md"
HOLD_FLOW = "06-runtime/flows/FLO-501-place-a-hold.md"
STOCK_FLOW = "06-runtime/flows/FLO-503-look-up-the-stock.md"


def files_of(case=WALK):
    root = FIXTURES / case
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted(root.rglob("*")) if p.is_file()}


def walk_after(edit, case=WALK):
    """impact.walk from the fixture to the fixture after `edit(files)`."""
    before = files_of(case)
    after = dict(before)
    edit(after)
    old, new = readers.read_vault(before), readers.read_vault(after)
    return impact.walk(old, new, impact.changes(old, new))


def replace(files, path, old, new):
    assert old in files[path], (path, old)
    files[path] = files[path].replace(old, new, 1)


# --- the walk, one change kind at a time ------------------------------------------------------------------------------

def test_a_changed_contract_reaches_the_flows_calling_it_and_their_slices_only():
    walk = walk_after(lambda f: replace(f, BILLING, "| declined |  | 402 |", "| declined |  | 403 |"))
    assert walk.affected == {"SLC-002": ["Take the payment changed → A customer pays for the held item → SLC-002 Pay for it"]}
    assert walk.everything == "" and walk.untouched == []


def test_a_changed_entity_reaches_every_flow_that_sets_it_starts_from_it_or_calls_a_contract_that_sets_it():
    walk = walk_after(lambda f: replace(f, "entities/hold.md", "final: [none, released, captured]", "final: [none, released]"))
    assert sorted(walk.affected) == ["SLC-001", "SLC-002"]
    assert walk.affected["SLC-001"] == ["Hold changed → A customer holds an item → SLC-001 Hold an item"]
    assert walk.affected["SLC-002"] == ["Hold changed → A customer pays for the held item → SLC-002 Pay for it"]


def test_a_shared_entity_says_its_paired_journeys():
    walk = walk_after(lambda f: replace(f, "entities/hold.md", "shared: false", "shared: true"))
    assert "Hold changed (shared: its paired journeys)" in walk.affected["SLC-002"][0]


def test_a_changed_event_reaches_the_flows_publishing_it_and_calling_what_emits_it():
    walk = walk_after(lambda f: replace(f, "library/specs/registration.asyncapi.yaml", "exactly-once", "at-least-once"), case="04-chain-correct")
    assert list(walk.affected.values()) == [["registration created changed → A customer registers and is billed → Release one: pilot"]]


def test_a_changed_flow_reaches_its_slices():
    walk = walk_after(lambda f: replace(f, STOCK_FLOW, "END out_of_stock", "END sold_out"))
    assert walk.affected == {"SLC-003": ["A customer looks up the stock changed → SLC-003 Look up the stock"]}


def test_prose_the_checker_never_reads_reaches_nothing():
    walk = walk_after(lambda f: replace(f, STOCK_FLOW, "before holding it.", "before holding it, on any device."))
    assert walk.affected == {} and walk.untouched == [] and walk.everything == ""
    walk = walk_after(lambda f: replace(f, INVENTORY, "while the customer pays.", "while the customer pays by card."))
    assert walk.affected == {}


def test_a_changed_slice_page_reaches_that_slice():
    walk = walk_after(lambda f: replace(f, "slices/SLC-003-stock.md", "- **After:** SLC-001\n", ""))
    assert walk.affected == {"SLC-003": ["SLC-003 Look up the stock changed"]}


def test_slices_after_a_slice_are_reached_only_when_its_flows_leave_different_states():
    walk = walk_after(lambda f: replace(f, HOLD_FLOW, "END held leaves hold=held", "END held"))
    assert walk.affected["SLC-001"] == ["A customer holds an item changed → SLC-001 Hold an item"]
    assert walk.affected["SLC-002"] == ["A customer holds an item now leaves different states → SLC-001 Hold an item, "
                                        "which SLC-002 Pay for it comes after"]
    assert "SLC-003" in walk.affected
    walk = walk_after(lambda f: replace(f, HOLD_FLOW, "END unavailable", "END none_left"))  # same leavings
    assert sorted(walk.affected) == ["SLC-001"]


def test_a_contract_that_only_moved_on_its_page_is_said_to_have_moved():
    walk = walk_after(lambda f: replace(f, BILLING, "## Contracts this app provides\n", "## Contracts this app provides\n\nA line.\n"))
    assert walk.affected == {"SLC-002": ["Take the payment moved on its page → A customer pays for the held item → SLC-002 Pay for it"]}


def test_a_renamed_app_reaches_the_flows_it_takes_part_in():
    walk = walk_after(lambda f: replace(f, BILLING, "title: Billing", "title: Payments"))
    assert walk.affected["SLC-002"] == ["Payments changed → A customer pays for the held item → SLC-002 Pay for it"]


def test_a_change_no_slice_reaches_is_listed_not_dropped():
    def add(f):
        f[BILLING] += ("\n### CON-505 Refund the payment\n\n- **Can time out:** no\n- **Retries:** none\n\n"
                       "| Case | When | Status | Answer | Emits | Sets |\n|---|---|---|---|---|---|\n| refunded |  | 200 | refunded |  |  |\n")
    walk = walk_after(add)
    assert walk.affected == {} and walk.untouched == ["Refund the payment (CON-505)"]


def test_the_walk_checks_every_slice_and_says_why_when_it_cannot_tell():
    walk = walk_after(lambda f: f.__setitem__("library/specs/broken.openapi.yaml", "paths: [unclosed"))
    assert sorted(walk.affected) == ["SLC-001", "SLC-002", "SLC-003"]
    assert walk.everything.startswith("library/specs/broken.openapi.yaml does not read the same as before")
    new = readers.read_vault(files_of())
    assert impact.walk(None, new, impact.Changes()).everything == "there is no earlier version to compare with"


# --- the record ---------------------------------------------------------------------------------------------------------

def test_a_record_round_trips_the_exploration_and_the_fingerprint_is_stable():
    catalog = readers.read_vault(files_of("04-chain-early-billing"))
    prepared = flowcheck.prepare(catalog, "FLO-004", TODAY)
    explored = flowcheck.explore_prepared(prepared)
    result = flowcheck.finish(catalog, prepared, explored, TODAY)
    kept = json.loads(record.dump_store({"format": 1, "slices": {"x": record.to_record(result, explored, "fp", TODAY)}}))
    again = record.explored_of(kept["slices"]["x"])
    assert again == explored
    assert flowcheck.finish(catalog, prepared, again, TODAY).format() == result.format()
    assert record.fingerprint(prepared, 10, 1.0, "v") == record.fingerprint(flowcheck.prepare(catalog, "FLO-004", TODAY), 10, 1.0, "v")
    assert record.fingerprint(prepared, 10, 1.0, "v") != record.fingerprint(prepared, 11, 1.0, "v")
    assert record.fingerprint(prepared, 10, 1.0, "v") != record.fingerprint(prepared, 10, 1.0, "w")


def test_a_corrupt_or_foreign_store_is_ignored_with_a_warning():
    store, warning = record.read_store("{not json")
    assert store == {"format": 1, "slices": {}} and "is not JSON" in warning and "checked afresh" in warning
    store, warning = record.read_store('{"format": 99, "slices": {}}')
    assert store["slices"] == {} and "not a flow-check record" in warning
    assert record.read_store(None) == ({"format": 1, "slices": {}}, "")
    with pytest.raises(ValueError, match="does not read"):
        record.explored_of({"explored": {"findings": [{"nonsense": 1}]}})


def test_the_record_keeps_not_fully_checked_as_itself_and_its_budget():
    catalog = readers.read_vault(files_of())
    prepared = flowcheck.prepare(catalog, "SLC-002", TODAY)
    explored = flowcheck.explore_prepared(prepared, max_states=1)
    result = flowcheck.finish(catalog, prepared, explored, TODAY)
    kept = record.to_record(result, explored, "fp", TODAY, (1, 10.0))
    assert kept["status"] == "not fully checked" and kept["checked"] == TODAY and kept["openTitles"] == ["not fully checked"]
    assert kept["budget"] == [1, 10.0]  # a reader judges whether it still holds with the budget it was explored with


# --- check_slices: walk plus record -------------------------------------------------------------------------------------

def statuses(report):
    return [(line.key, bool(line.reused), line.why) for line in report.lines]


def test_first_run_checks_everything_and_the_second_reuses_everything():
    catalog = readers.read_vault(files_of())
    first = changed.check_slices(catalog, TODAY, {}, impact.Walk())
    assert [(k, r) for k, r, _ in statuses(first)] == [("SLC-001", False), ("SLC-002", False), ("SLC-003", False)]
    assert {w for _, _, w in statuses(first)} == {"Checked because it has no recorded result yet."}
    second = changed.check_slices(catalog, TODAY, first.store, impact.Walk())
    assert [r for _, r, _ in statuses(second)] == [True, True, True] and second.exit_code == 0
    assert second.format().split("\n")[0] == ("vela check-slice --changed: checked 0 of 3 slices. The other 3 are unchanged "
                                              "since their last check.")
    assert second.lines[0].words() == f"SLC-001 Hold an item: unchanged since {TODAY}, passes."


def test_only_the_slices_the_walk_reaches_are_checked():
    before = files_of()
    store = changed.check_slices(readers.read_vault(before), TODAY, {}, impact.Walk()).store
    after = dict(before)
    replace(after, BILLING, "| declined |  | 402 |", "| declined |  | 403 |")
    old, new = readers.read_vault(before), readers.read_vault(after)
    report = changed.check_slices(new, TODAY, store, impact.walk(old, new, impact.changes(old, new)))
    assert [(k, r) for k, r, _ in statuses(report)] == [("SLC-001", True), ("SLC-002", False), ("SLC-003", True)]
    assert report.lines[1].words() == ("SLC-002 Pay for it: passes. Checked because Take the payment changed → A customer pays "
                                       "for the held item → SLC-002 Pay for it.")
    assert report.format().split("\n")[0] == ("vela check-slice --changed: checked 1 of 3 slices. The other 2 are unchanged "
                                              "since their last check.")


def test_a_fingerprint_that_moved_where_the_walk_saw_nothing_is_checked_and_said():
    """The record is a sensor on the walk: a change it did not trace is checked, never served stale."""
    before = files_of()
    store = changed.check_slices(readers.read_vault(before), TODAY, {}, impact.Walk()).store
    after = dict(before)
    replace(after, BILLING, "| declined |  | 402 |", "| declined |  | 403 |")
    report = changed.check_slices(readers.read_vault(after), TODAY, store, impact.Walk())
    assert statuses(report)[1] == ("SLC-002", False, "Checked because what it reads changed in a way the impact walk did not trace.")


def test_a_reached_slice_whose_model_did_not_move_reuses_its_exploration_and_says_so():
    catalog = readers.read_vault(files_of())
    store = changed.check_slices(catalog, TODAY, {}, impact.Walk()).store
    walk = impact.Walk({"SLC-003": ["Check the stock changed → A customer looks up the stock → SLC-003 Look up the stock"]})
    line = changed.check_slices(catalog, TODAY, store, walk).lines[2]
    assert line.reused == TODAY
    assert line.why.endswith("but the model it checks is the one last explored, so that exploration is reused.")


def test_a_reused_failing_slice_still_fails_and_overrides_are_applied_fresh():
    files = files_of()
    replace(files, BILLING, "| declined |  | 402 | declined |  |  |\n", "| declined |  | 402 | declined |  |  |\n| held_back |  | 409 | held back |  |  |\n")
    catalog = readers.read_vault(files)
    first = changed.check_slices(catalog, TODAY, {}, impact.Walk())
    assert first.exit_code == 1
    again = changed.check_slices(catalog, TODAY, first.store, impact.Walk())
    assert again.lines[1].reused and again.exit_code == 1
    assert again.lines[1].words().startswith(f"SLC-002 Pay for it: unchanged since {TODAY}, fails, 1 open finding (an answer nobody handles)")
    flow = "06-runtime/flows/FLO-502-pay.md"
    files[flow] += '\n## History\n\n- **Override:** "F1 CON-503 held_back until 2026-12-01" by @lead on 2026-10-14: next sprint\n'
    covered = changed.check_slices(readers.read_vault(files), TODAY, first.store, impact.Walk())
    assert covered.lines[1].reused and covered.lines[1].passes and covered.exit_code == 0
    expired = changed.check_slices(readers.read_vault(files), "2026-12-02", first.store, impact.Walk())
    assert expired.exit_code == 1


def test_another_checker_version_or_budget_reuses_nothing():
    catalog = readers.read_vault(files_of())
    store = changed.check_slices(catalog, TODAY, {}, impact.Walk(), version="a").store
    assert not any(line.reused for line in changed.check_slices(catalog, TODAY, store, impact.Walk(), version="b").lines)
    assert not any(line.reused for line in changed.check_slices(catalog, TODAY, store, impact.Walk(), version="a", max_states=7).lines)


def test_all_explores_every_slice_and_reuses_nothing():
    catalog = readers.read_vault(files_of())
    store = changed.check_slices(catalog, TODAY, {}, impact.Walk()).store
    report = changed.check_slices(catalog, TODAY, store, everything=True)
    assert not any(line.reused for line in report.lines)
    assert report.format("--all").split("\n")[0] == "vela check-slice --all: checked 3 of 3 slices, every one, because --all asks for every one."


def test_an_unreadable_record_of_one_slice_is_checked_afresh_with_a_warning():
    catalog = readers.read_vault(files_of())
    store = changed.check_slices(catalog, TODAY, {}, impact.Walk()).store
    store["slices"]["SLC-001"]["explored"] = {"findings": "nope"}
    report = changed.check_slices(catalog, TODAY, store, impact.Walk())
    assert not report.lines[0].reused and report.lines[0].why == "Its record did not read."
    assert report.warnings and "SLC-001 Hold an item does not read" in report.warnings[0]


# --- the CLI on a git repo ----------------------------------------------------------------------------------------------

def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(FIXTURES / WALK, root)
    (root / ".gitignore").write_text(".vela/*\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "the plan")
    return root


def edit(root, path, old, new):
    target = root / path
    text = target.read_text(encoding="utf-8")
    assert old in text
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def changed_run(root, *extra):
    return run("check-slice", "--vault", str(root), "--today", TODAY, *extra)


def test_cli_changed_checks_all_once_then_only_what_a_change_reaches(repo):
    code, out = changed_run(repo, "--changed")
    assert code == 0 and out.startswith("vela check-slice --changed: checked 3 of 3 slices.")
    assert (repo / ".vela" / "flowcheck-cache.json").is_file()
    edit(repo, BILLING, "| declined |  | 402 |", "| declined |  | 403 |")
    code, out = changed_run(repo, "--changed")
    assert code == 0
    assert out.split("\n")[:4] == [
        "vela check-slice --changed: checked 1 of 3 slices. The other 2 are unchanged since their last check.",
        f"SLC-001 Hold an item: unchanged since {TODAY}, passes.",
        "SLC-002 Pay for it: passes. Checked because Take the payment changed → A customer pays for the held item → SLC-002 Pay for it.",
        f"SLC-003 Look up the stock: unchanged since {TODAY}, passes."]


def test_cli_changed_with_a_range_and_since_a_commit(repo):
    changed_run(repo, "--all")
    edit(repo, STOCK_FLOW, "END out_of_stock", "END sold_out")
    git(repo, "commit", "-qam", "rename an outcome")
    code, out = changed_run(repo, "--changed", "HEAD~1..HEAD")
    assert code == 0 and "SLC-003 Look up the stock: passes. Checked because A customer looks up the stock changed" in out
    edit(repo, STOCK_FLOW, "END sold_out", "END gone")
    code, out = changed_run(repo, "--since-commit", "HEAD~1")
    assert "checked 1 of 3 slices" in out.split("\n")[0]
    code, out = changed_run(repo, "--changed", "nonsense..HEAD")
    assert "every one, because the walk cannot tell what changed: git cannot say what changed" in out.split("\n")[0]


def test_cli_changed_outside_git_checks_every_slice_and_says_why(tmp_path):
    root = tmp_path / "plain"
    shutil.copytree(FIXTURES / WALK, root)
    code, out = changed_run(root, "--changed")
    assert code == 0 and out.split("\n")[0].startswith(
        "vela check-slice --changed: checked 3 of 3 slices, every one, because the walk cannot tell what changed: git cannot say")


def test_cli_a_corrupt_record_warns_and_checks_afresh(repo):
    changed_run(repo, "--changed")
    (repo / ".vela" / "flowcheck-cache.json").write_text("{half", encoding="utf-8")
    code, out = changed_run(repo, "--changed")
    assert code == 0 and "checked 3 of 3 slices" in out.split("\n")[0]
    assert "Warning: .vela/flowcheck-cache.json is not JSON" in out
    assert json.loads((repo / ".vela" / "flowcheck-cache.json").read_text(encoding="utf-8"))["format"] == 1


def test_cli_exits_1_on_an_open_finding_and_on_not_fully_checked(repo):
    edit(repo, BILLING, "| declined |  | 402 | declined |  |  |\n", "| declined |  | 402 | declined |  |  |\n| held_back |  | 409 | held back |  |  |\n")
    code, out = changed_run(repo, "--changed")
    assert code == 1 and "SLC-002 Pay for it: fails, 1 open finding (an answer nobody handles)." in out and "F1 An answer nobody handles" in out
    code, out = changed_run(repo, "--changed")
    assert code == 1  # reused, and still failing
    code, out = changed_run(repo, "--all", "--max-states", "1")
    assert code == 1 and "not fully checked (the budget ran out)" in out


def test_cli_a_single_check_is_recorded_for_the_next_changed(repo):
    code, _ = run("check-slice", "SLC-001", "--vault", str(repo), "--today", TODAY)
    assert code == 0
    kept = json.loads((repo / ".vela" / "flowcheck-cache.json").read_text(encoding="utf-8"))
    assert list(kept["slices"]) == ["SLC-001"] and kept["slices"]["SLC-001"]["status"] == "passes"
    code, out = changed_run(repo, "--changed")
    assert f"SLC-001 Hold an item: unchanged since {TODAY}, passes." in out


def test_cli_refuses_a_slice_with_changed_and_neither():
    assert run("check-slice", "SLC-001", "--changed", "--vault", str(FIXTURES / WALK))[0] == 2
    assert run("check-slice", "--vault", str(FIXTURES / WALK))[0] == 2
    assert run("check-slice", "--all", "--changed", "--vault", str(FIXTURES / WALK))[0] == 2


def test_cli_journeys_three_runs_triples(tmp_path):
    root = tmp_path / "v"
    shutil.copytree(FIXTURES / "06-two-orders-last-item", root)
    code, out = run("check-slice", "FLO-006", "--vault", str(root), "--journeys", "3")
    assert "Limit: Stock is shared, so the flows that touch it ran two and three journeys at once, never four." in out
