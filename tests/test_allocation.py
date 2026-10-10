"""Requirements in two levels: a capability's functional requirements, and each app's allocated share of them."""
import shutil

from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"
CAP = "capabilities/CAP-014-hold-a-seat.md"
APP = "05-building-blocks/booking-building-blocks.md"
FR = ("\n## Functional requirements\n\n### CAP-014.FR1 Hold a seat while paying\n\n"
      "A customer's seat is held while they pay, and released if they do not.\n\n"
      "- **State:** assumption\n- **Source:** SRC-04\n\n- The hold ends after ten minutes.\n")
ROW = ("\n## Requirements allocated\n\n| Requirement | Share | Through | State |\n|---|---|---|---|\n"
       "| [[CAP-014-hold-a-seat#CAP-014.FR1 Hold a seat while paying\\|CAP-014.FR1]] | {share} | {through} | {state} |\n")


def vault_with(tmp_path, row=None):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    cap = vault / CAP
    cap.write_text(cap.read_text(encoding="utf-8").rstrip("\n") + "\n" + FR, encoding="utf-8")
    if row:
        app = vault / APP
        app.write_text(app.read_text(encoding="utf-8").rstrip("\n") + "\n" + ROW.format(**row), encoding="utf-8")
    return vault


def check(vault, *extra):
    return run("check", "--vault", str(vault), "--today", "2026-11-20", *extra)


def test_a_requirement_nobody_carries_is_a_trace_gap_and_an_error_at_the_epics_gate(tmp_path):
    vault = vault_with(tmp_path)
    assert "W505" in check(vault)[1] and "CAP-014.FR1" in check(vault)[1]
    assert "E505" in check(vault, "--gate", "epics")[1]


def test_an_allocated_requirement_is_no_gap(tmp_path):
    vault = vault_with(tmp_path, {"share": "holds the seat for ten minutes", "through": "CON-001", "state": "assumption"})
    out = check(vault)[1]
    assert "W505" not in out and "E33" not in out, out


def test_rows_that_name_nothing_real_are_errors(tmp_path):
    vault = vault_with(tmp_path, {"share": "x", "through": "CON-999", "state": "maybe"})
    out = check(vault)[1]
    assert "E331" in out and "E332" in out
    vault2 = vault_with(tmp_path / "b", {"share": "x", "through": "—", "state": "assumption"})
    app = vault2 / APP
    app.write_text(app.read_text(encoding="utf-8").replace(
        "[[CAP-014-hold-a-seat#CAP-014.FR1 Hold a seat while paying\\|CAP-014.FR1]]", "CAP-099.FR9"), encoding="utf-8")
    assert "E330" in check(vault2)[1]


def test_the_allocation_block_shows_each_requirement_against_each_app(tmp_path):
    vault = vault_with(tmp_path, {"share": "holds the seat", "through": "CON-001", "state": "assumption"})
    run("render", "--vault", str(vault))
    page = (vault / "04a-capability-delta.md").read_text(encoding="utf-8")
    assert "**Allocation:** 1 requirements, 0 not allocated." in page
    assert "holds the seat (CON-001)" in page


def test_next_suggests_allocate_before_epics_while_a_requirement_is_unallocated(tmp_path):
    vault = vault_with(tmp_path)
    out = run("next", "--vault", str(vault), "--today", "2026-11-20")[1]
    assert "allocate CAP-014" in out, out
    carried = vault_with(tmp_path / "b", {"share": "holds the seat", "through": "CON-001", "state": "assumption"})
    assert "allocate" not in run("next", "--vault", str(carried), "--today", "2026-11-20")[1]
