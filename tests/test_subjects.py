"""Parties and stored value: the two subject kinds the question catalogue needs that are not pages.

A subject the check cannot type would leave its questions never owed and the ledger looking clean,
so a missing fact is an error, never a silent skip."""
import json

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


def test_relationship_is_read_in_any_case(mini):
    write(mini, PARTY.replace("supplier", "Customer Group") + STORED)
    assert primary(check(mini)[1]) == []


def test_a_label_in_another_case_is_still_the_label(mini):
    write(mini, PARTY.replace("**Relationship:**", "**relationship:**") + STORED)
    assert primary(check(mini)[1]) == []


def test_two_headings_for_one_party_is_e208(mini):
    write(mini, PARTY + PARTY.replace("## Outside parties\n\n", "") + STORED)
    assert ("E208", PAGE) in primary(check(mini)[1])


def test_query_get_knows_the_new_kinds(mini):
    write(mini, PARTY + STORED)
    code, out = run("query", "get", "PTY-01", "--vault", str(mini), "--json")
    assert code == 0, out
    answer = json.loads(out)
    assert answer["kind"] == "party" and answer["link"] == f"[[03-context-and-scope#PTY-01 Payco|PTY-01]]"
    code, out = run("query", "get", "SV-01", "--vault", str(mini), "--json")
    assert json.loads(out)["kind"] == "stored-value"


def test_the_fixture_types_its_parties_and_its_loyalty_points():
    from conftest import REPO
    from planner import cli
    vault = cli.load_vault(REPO / "examples" / "unified-booking")
    assert [(p.id, p.fact("Relationship")) for p in vault.parties] == [("PTY-01", "supplier"), ("PTY-02", "supplier")]
    assert [s.id for s in vault.stored_values] == ["SV-01"]
    assert {i.page.path for i in vault.parties + vault.stored_values} == {PAGE}
