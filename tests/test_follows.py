"""REG-05 is owed only after REG-01 is answered yes; a no keeps it off the ledger."""
import pytest

from conftest import edit
from sizing_vault import from_template
from vela import catalog, cli, questions

LEDGER = "11-unknowns-and-risks.md"


def owed_entries(root):
    return {c.entry.id for c in questions.owed(cli.load_vault(root))}


HEADER = "| Copy | State | Evidence | By | Date |\n|---|---|---|---|---|\n"  # unique; the bare separator is not


def with_row(root, state, evidence):
    edit(root / LEDGER, HEADER, HEADER + f"| Q-REG-01@INI-001 | {state} | {evidence} | @dana | 2026-10-23 |\n")


def test_a_new_plan_owes_reg01_and_not_reg05(tmp_path):
    found = owed_entries(from_template(tmp_path))
    assert "Q-REG-01" in found and "Q-REG-05" not in found


def test_reg05_is_owed_after_a_yes(tmp_path):
    root = from_template(tmp_path)
    with_row(root, "answered", "item: [[03-context-and-scope]]; source: SRC-01; answer: sold as a bundle with rail")
    assert "Q-REG-05" in owed_entries(root)


def test_reg05_stays_off_after_a_no(tmp_path):
    root = from_template(tmp_path)
    with_row(root, "not-applicable", "reason: nothing is sold with another party")
    assert "Q-REG-05" not in owed_entries(root)


@pytest.mark.parametrize("follows, said", [("Q-REG-99", "names no entry"), ("Q-OPS-01", "scope"),
                                           ("Q-REG-05", "itself")])
def test_a_follows_that_cannot_hold_is_refused_at_load(follows, said):
    data = catalog.load_yaml((cli.CATALOG).read_text(encoding="utf-8"))
    entry = next(e for e in data["entries"] if e["id"] == "Q-REG-05")
    entry["follows"] = follows
    with pytest.raises(catalog.CatalogError, match=said):
        catalog.parse_catalog(data)


def with_rows(root, *rows):
    edit(root / LEDGER, HEADER, HEADER + "".join(f"| {r} | @dana | 2026-10-23 |\n" for r in rows))


def w804(root):
    from conftest import run
    return [line for line in run("check", "--vault", str(root))[1].splitlines() if "W804" in line and "REG-05" in line]


@pytest.mark.parametrize("parent", ["unknown | unknown: [[11-unknowns-and-risks#UNK-001]]",
                                    "not-applicable | reason: nothing is sold with another party"])
def test_a_follow_up_row_waiting_on_its_parent_is_not_called_unmatched(tmp_path, parent):
    # The trigger matches; the row waits for Q-REG-01's answer. Telling the lead to remove it would delete a recorded answer.
    root = from_template(tmp_path)
    with_rows(root, f"Q-REG-01@INI-001 | {parent}",
              "Q-REG-05@INI-001 | not-applicable | reason: no product is shared across parties")
    assert w804(root) == []


def test_a_follow_up_row_is_still_called_out_when_its_trigger_stops_matching(tmp_path):
    root = from_template(tmp_path)
    with_rows(root, "Q-REG-05@INI-999 | not-applicable | reason: gone")
    assert w804(root), "an unmatched subject still draws the finding"
