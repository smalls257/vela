"""Releases: each lists the requirements it delivers; the state after each is computed from them."""
import shutil
import sys

from conftest import REPO, run

sys.path.insert(0, str(REPO / "plugin" / "lib"))
from vela import cli, releases  # noqa: E402

FIXTURE = REPO / "examples" / "unified-booking"
CAP = "capabilities/CAP-014-hold-a-seat.md"
APP = "05-building-blocks/booking-building-blocks.md"
FR = ("\n## Functional requirements\n\n### CAP-014.FR1 Hold a seat while paying\n\n"
      "A customer's seat is held while they pay, and released if they do not.\n\n"
      "- **State:** assumption\n- **Source:** SRC-04\n\n- The hold ends after ten minutes.\n- The customer sees the time left.\n")
ROW = ("\n## Requirements allocated\n\n| Requirement | Share | Through | State |\n|---|---|---|---|\n"
       "| [[CAP-014-hold-a-seat#CAP-014.FR1 Hold a seat while paying\\|CAP-014.FR1]] | holds the seat | CON-001 | assumption |\n")
LINK = "[[CAP-014-hold-a-seat#CAP-014.FR1 Hold a seat while paying\\|CAP-014.FR1]]"


def vault_with(tmp_path, body):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    for rel, add in ((CAP, FR), (APP, ROW)):
        f = vault / rel
        f.write_text(f.read_text(encoding="utf-8").rstrip("\n") + "\n" + add, encoding="utf-8")
    (vault / "04b-releases.md").write_text(
        "---\nid: releases\ntype: initiative-section\ntitle: Releases\narc42: \"§4\"\nstate: assumption\n"
        "owner: \"@hl-solution-lead\"\nauthored: mixed\n---\n\n# Releases\n\nTwo releases.\n\n" + body, encoding="utf-8")
    return vault


def release(name, rows, state="assumption"):
    table = "".join(f"| {r} |\n" for r in rows)
    return f"## {name}\n\n- **Target:** 2027-01-15\n- **State:** {state}\n\n| Delivers | Criteria | Note |\n|---|---|---|\n{table}\n"


def check(vault):
    return run("check", "--vault", str(vault), "--today", "2026-11-20")[1]


def test_a_requirement_split_across_two_releases_is_clean(tmp_path):
    vault = vault_with(tmp_path, release("Release one", [f"{LINK} | AC1 | AC2 later"]) + release("Release two", [f"{LINK} | AC2 | "]))
    out = check(vault)
    assert not any(c in out for c in ("E340", "E341", "E342", "W343")), out


def test_rows_must_name_real_requirements_and_criteria(tmp_path):
    vault = vault_with(tmp_path, release("Release one", [f"{LINK} | AC3 | ", "CAP-099.FR9 | all | "], state="soon"))
    out = check(vault)
    assert "E340" in out and "E341" in out and "E342" in out, out


def test_a_requirement_no_release_delivers_warns(tmp_path):
    vault = vault_with(tmp_path, release("Release one", []))
    assert "W343" in check(vault)


def test_after_a_release_its_apps_change_and_its_contracts_exist(tmp_path):
    vault = vault_with(tmp_path, release("Release one", [f"{LINK} | all | "]))
    shots = releases.snapshots(cli.load_vault(vault))
    assert [s["name"] for s in shots] == ["Today", "Release one"]
    booking_today = shots[0]["apps"]["APP-booking"]
    assert shots[1]["apps"]["APP-booking"] == ("new" if booking_today == "absent" else "changes")
    assert shots[1]["delivers"] == ["CAP-014.FR1"]
    assert shots[1]["contracts"]["CON-001"] in ("exists", "new")
