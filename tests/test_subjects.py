"""Parties and stored value: the two subject kinds the question catalog needs that are not pages.

A subject the check cannot type would leave its questions never owed and the ledger looking clean,
so a missing fact is an error, never a silent skip."""
import json

import pytest

from conftest import check, findings, run

PAGE = "03-context-and-scope.md"
HEAD = """---
id: context-and-scope
type: index
title: Context and scope
authored: authored
---

# Context and scope

"""
PARTY = """## Outside parties

### PTY-01 Payco

- **Relationship:** supplier
- **Agreements:** the card processing contract, SRC-01

"""
STORED = """## Value held for customers

### SV-01 Gift cards

- **Holder:** [[shop-building-blocks|Shop]]
- **Owner:** the finance team
"""


def write(mini, body):
    (mini / PAGE).write_text(HEAD + body, encoding="utf-8")


def primary(out):
    return sorted(f for f in findings(out) if f[0] != "W402")


def test_a_typed_party_and_stored_value_are_clean(mini):
    write(mini, PARTY + STORED)
    code, out = check(mini)
    assert code == 0, out
    assert primary(out) == []


def test_a_party_with_no_relationship_is_e808(mini):
    write(mini, PARTY.replace("- **Relationship:** supplier\n", "") + STORED)
    code, out = check(mini)
    assert code == 1
    assert primary(out) == [("E808", PAGE)]
    assert "PTY-01 is a party with no **Relationship:** bullet." in out


def test_a_stored_value_with_no_owner_is_e808(mini):
    write(mini, PARTY + STORED.replace("- **Owner:** the finance team\n", ""))
    _, out = check(mini)
    assert primary(out) == [("E808", PAGE)]
    assert "SV-01 is a stored value with no **Owner:** bullet." in out


def test_a_relationship_outside_the_list_is_e105(mini):
    write(mini, PARTY.replace("supplier", "friend") + STORED)
    _, out = check(mini)
    assert primary(out) == [("E105", PAGE)]
    assert "partner, supplier, regulator, customer group" in out


def test_a_party_with_no_agreements_is_e808(mini):
    write(mini, PARTY.replace("- **Agreements:** the card processing contract, SRC-01\n", "") + STORED)
    _, out = check(mini)
    assert primary(out) == [("E808", PAGE)]
    assert "PTY-01 is a party with no **Agreements:** bullet." in out


def test_a_stored_value_with_no_holder_is_e808(mini):
    write(mini, PARTY + STORED.replace("- **Holder:** [[shop-building-blocks|Shop]]\n", ""))
    _, out = check(mini)
    assert primary(out) == [("E808", PAGE)]
    assert "SV-01 is a stored value with no **Holder:** bullet." in out


def test_an_empty_value_is_a_missing_fact(mini):
    write(mini, PARTY + STORED.replace("the finance team", ""))
    _, out = check(mini)
    assert ("E808", PAGE) in primary(out)


@pytest.mark.parametrize("heading", ["### PTY-1 Payco", "### Pty-01 Payco", "#### PTY-01 Payco", "### PTY-01: Payco",
                                     "## PTY-01 Payco", "### SV-1 Payco", "### sv-01 Payco"])
def test_a_mistyped_subject_heading_is_e810_never_dropped(mini, heading):
    write(mini, "## Outside parties\n\n" + heading + "\n\n- **Relationship:** supplier\n- **Agreements:** none known\n")
    code, out = check(mini)
    assert code == 1
    assert primary(out) == [("E810", PAGE)]
    assert "### PTY-nn <name>" in out or "### SV-nn <name>" in out


def test_an_ordinary_heading_that_starts_with_sv_is_not_a_subject(mini):
    write(mini, PARTY + STORED + "\n## SVG icons\n")
    assert primary(check(mini)[1]) == []


def test_a_subject_off_its_page_warns_w811_and_still_loads(mini):
    other = "04-concerns.md"
    write(mini, STORED)
    (mini / other).write_text(HEAD.replace("context-and-scope", "other-page").replace("Context and scope", "Other") + PARTY, encoding="utf-8")
    code, out = check(mini)
    assert ("W811", other) in primary(out)
    assert "PTY-01 is defined on" in out
    run_code, got = run("query", "get", "PTY-01", "--vault", str(mini), "--json")
    assert run_code == 0 and json.loads(got)["kind"] == "party"


def test_relationship_is_read_in_any_case(mini):
    write(mini, PARTY.replace("supplier", "Customer Group") + STORED)
    assert primary(check(mini)[1]) == []


def test_a_label_in_another_case_is_still_the_label(mini):
    write(mini, PARTY.replace("**Relationship:**", "**relationship:**") + STORED)
    assert primary(check(mini)[1]) == []


def test_two_headings_for_one_party_is_e208(mini):
    write(mini, PARTY + PARTY.replace("## Outside parties\n\n", "") + STORED)
    assert primary(check(mini)[1]) == [("E208", PAGE)]


def test_query_get_knows_the_new_kinds(mini):
    write(mini, PARTY + STORED)
    code, out = run("query", "get", "PTY-01", "--vault", str(mini), "--json")
    assert code == 0, out
    answer = json.loads(out)
    assert answer["kind"] == "party" and answer["link"] == "[[03-context-and-scope#PTY-01 Payco|PTY-01]]"
    code, out = run("query", "get", "SV-01", "--vault", str(mini), "--json")
    assert json.loads(out)["kind"] == "stored-value"


def test_the_fixture_types_its_parties_and_its_loyalty_points():
    from conftest import REPO
    from planner import cli
    vault = cli.load_vault(REPO / "examples" / "unified-booking")
    assert [(p.id, p.fact("Relationship")) for p in vault.parties] == [("PTY-01", "supplier"), ("PTY-02", "supplier")]
    assert [s.id for s in vault.stored_values] == ["SV-01"]
    assert {i.page.path for i in vault.parties + vault.stored_values} == {PAGE}
