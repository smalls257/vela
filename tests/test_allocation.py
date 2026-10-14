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
    assert "**Who does what:** 1 requirement is firm enough to split between the apps (assumed or later); none is waiting for an app." in page
    assert "holds the seat (CON-001)" in page


def test_next_suggests_allocate_before_epics_while_a_requirement_is_unallocated(tmp_path):
    vault = vault_with(tmp_path)
    out = run("next", "--vault", str(vault), "--today", "2026-11-20")[1]
    assert out.startswith("planner next: for the whole plan: decide which app owns Hold a seat while paying (CAP-014.FR1)"), out
    carried = vault_with(tmp_path / "b", {"share": "holds the seat", "through": "CON-001", "state": "assumption"})
    assert "allocate" not in run("next", "--vault", str(carried), "--today", "2026-11-20")[1]


def add_row(vault, page, cells):
    path = vault / page
    text = path.read_text(encoding="utf-8")
    if "## Requirements allocated" not in text:
        text = text.rstrip("\n") + "\n\n## Requirements allocated\n\n| Requirement | Share | Through | State |\n|---|---|---|---|\n"
    path.write_text(text + "| " + " | ".join(cells) + " |\n", encoding="utf-8")


LINK = "[[CAP-014-hold-a-seat#CAP-014.FR1 Hold a seat while paying\\|CAP-014.FR1]]"


def test_a_decided_row_needs_a_grill_like_any_decided_item(tmp_path):
    vault = vault_with(tmp_path, {"share": "holds the seat", "through": "CON-001", "state": "decided"})
    assert "E303" not in check(vault)[1]  # Booking's Decision links the Grill that decided it
    app = vault / APP
    app.write_text("\n".join(l for l in app.read_text(encoding="utf-8").splitlines()
                              if not l.startswith("- **Decision:**")) + "\n", encoding="utf-8")
    out = check(vault)[1]
    assert "E303" in out and "CAP-014.FR1@APP-booking" in out, out


def test_an_inkling_row_is_a_guess_and_carries_nothing(tmp_path):
    vault = vault_with(tmp_path, {"share": "maybe holds it", "through": "—", "state": "inkling"})
    assert "W505" in check(vault)[1]


def test_a_fact_row_needs_its_page_sources(tmp_path):
    vault = vault_with(tmp_path, {"share": "holds the seat today", "through": "—", "state": "fact"})
    out = check(vault)[1]
    assert "E333" not in out and "W505" not in out, out  # Booking lists sources
    edit_page = vault / APP
    text = edit_page.read_text(encoding="utf-8")
    start = text.index("\nsources:")
    edit_page.write_text(text[:start] + text[text.index("\n", start + 1):], encoding="utf-8")
    assert "E333" in check(vault)[1]


def test_a_short_row_has_no_state(tmp_path):
    vault = vault_with(tmp_path)
    add_row(vault, APP, [LINK, "holds the seat"])
    assert "E332" in check(vault)[1]


def test_t7_warns_before_the_first_epic_because_allocation_comes_first(tmp_path):
    vault = vault_with(tmp_path)
    shutil.rmtree(vault / "13-epics")
    out = check(vault)[1]
    assert "W505" in out and "W501" not in out, out


def test_the_block_joins_two_shares_of_one_app_and_shows_each_app(tmp_path):
    vault = vault_with(tmp_path, {"share": "holds the seat", "through": "CON-001", "state": "assumption"})
    add_row(vault, APP, [LINK, "releases it after ten minutes", "—", "assumption"])
    add_row(vault, "05-building-blocks/website-building-blocks.md", [LINK, "shows the hold's countdown", "—", "assumption"])
    run("render", "--vault", str(vault))
    page = (vault / "04a-capability-delta.md").read_text(encoding="utf-8")
    assert "holds the seat (CON-001); releases it after ten minutes" in page
    assert "shows the hold's countdown" in page


def test_handoff_verify_sees_a_carried_requirement_change(tmp_path):
    vault = vault_with(tmp_path, {"share": "holds the seat", "through": "CON-001", "state": "assumption"})
    code, out = run("handoff", "APP-booking", "--vault", str(vault), "--today", "2026-11-20", "--replace")
    assert code == 0, out
    assert "CAP-014.FR1" in (vault / "handoffs" / "APP-booking.md").read_text(encoding="utf-8")
    cap = vault / CAP
    cap.write_text(cap.read_text(encoding="utf-8").replace("ten minutes", "fifteen minutes"), encoding="utf-8")
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(vault), "--today", "2026-11-20")
    assert code == 1 and "CAP-014.FR1" in out, out


def test_next_suggests_requirements_for_a_changing_capability_before_the_first_epic(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    shutil.rmtree(vault / "13-epics")
    out = run("next", "--vault", str(vault), "--today", "2026-11-20")[1]
    assert out.startswith("planner next: for the whole plan: write the requirements for ") and "(CAP-" in out, out
