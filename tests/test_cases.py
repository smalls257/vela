"""A contract's case table: the parser reads it, `vela check` warns when it is missing or cannot be trusted."""
import re

import pytest

from conftest import edit, check, findings
from vela import cases, model, parse

SHOP = "05-building-blocks/shop-building-blocks.md"
HEADER = "| Case | When | Status | Answer | Emits | Sets |\n|---|---|---|---|---|---|\n"


def table_of(rows, contract="CON-001"):
    page = parse.parse_page("x.md", f"---\nid: x\n---\n\n### {contract} Thing\n\n- **State:** assumption\n\n{HEADER}{rows}\n")
    vault = model.build([page], {})
    return cases.case_table(page, vault.item(contract))


def codes(out):
    return [code for code, _ in findings(out)]


def test_a_well_formed_table_reads_into_cases():
    table = table_of("| reserved | stock is available | 201 | held | EVT-004 | order: new→held; stock: low |\n"
                     "| out_of_stock | stock is not available and kind in [a, b] | 409 | refused | | |\n")
    assert table.problems == ()
    first, second = table.cases
    assert first.emits == ("EVT-004",)
    assert first.sets == (("order", "new", "held"), ("stock", "", "low"))
    assert not first.is_error and second.is_error


@pytest.mark.parametrize("row", [
    "| Reserved | | 201 | held | | |",                       # not snake_case
    "| ok_case | whenever | 201 | held | | |",               # a When outside the grammar
    "| ok_case | | 2xx | held | | |",                        # status
    "| ok_case | | 201 | held | EVT-4 | |",                  # emits
    "| ok_case | | 201 | held | | order held |",             # sets
    "| ok_case | | 201 | held |",                            # a dropped column
])
def test_a_malformed_row_is_a_problem_and_never_a_case(row):
    table = table_of(row + "\n")
    assert table.cases == () and [p.code for p in table.problems] == ["malformed"]


def test_a_change_that_depends_on_where_it_starts_reads_as_one_row_per_start():
    """Revision 2, item 5: stock running out needs 'one less', which an absolute state cannot say."""
    table = table_of("| reserved | | 200 | held | | stock: one→zero, zero→minus_one; order: new->held |\n")
    assert table.problems == ()
    assert table.cases[0].sets == (("stock", "one", "zero"), ("stock", "zero", "minus_one"), ("order", "new", "held"))
    twice = table_of("| reserved | | 200 | held | | stock: one→zero, one→minus_one |\n")
    assert twice.cases == () and "two changes of stock from one" in twice.problems[0].message


@pytest.mark.parametrize("value, parsed", [("none", (0, ())), ("2 after timeout, unavailable", (2, ("timeout", "unavailable"))),
                                           ("3", None), ("2 on timeout", None)])
def test_retries_say_how_many_and_after_which_answers(value, parsed):
    """Revision 2, item 7: which answers are retried is required; a bare count is not readable."""
    assert cases.retries(value) == parsed


def test_a_repeated_key_is_a_duplicate():
    table = table_of("| a_case | | 200 | one | | |\n| a_case | | 404 | two | | |\n")
    assert [c.status for c in table.cases] == ["200"]
    assert [p.code for p in table.problems] == ["duplicate"]


def test_a_contract_with_no_table_has_none():
    page = parse.parse_page("x.md", "---\nid: x\n---\n\n### CON-001 Thing\n\n- **State:** assumption\n")
    assert cases.case_table(page, model.build([page], {}).item("CON-001")) is None


def test_the_vault_with_tables_is_quiet(mini):
    _, out = check(mini)
    assert codes(out) == []


def test_w380_a_contract_without_a_table(mini):
    text = (mini / SHOP).read_text(encoding="utf-8")
    (mini / SHOP).write_text(re.sub(r"\n\| Case .*?\n\n", "\n\n", text, flags=re.S), encoding="utf-8")
    _, out = check(mini)
    assert codes(out) == ["W380"]


def test_w381_a_row_it_cannot_read(mini):
    edit(mini / SHOP, "| sold | | 200 |", "| Sold | | 200 |")
    _, out = check(mini)
    assert codes(out) == ["W381"]


def test_w382_a_repeated_case_key(mini):
    edit(mini / SHOP, "| basket_refused |", "| sold |")
    _, out = check(mini)
    assert sorted(codes(out)) == ["W382", "W385"]  # the refusal is gone with the duplicate, so the error case is missing too


def test_w383_an_event_nobody_names(mini):
    edit(mini / SHOP, "| sold | | 200 | the receipt | | |", "| sold | | 200 | the receipt | EVT-009 | |")
    _, out = check(mini)
    assert codes(out) == ["W383"]


def test_a_named_event_and_entity_are_known(mini):
    edit(mini / SHOP, "| sold | | 200 | the receipt | | |", "| sold | | 200 | the receipt | EVT-009 | basket: open→paid |")
    edit(mini / SHOP, "## Contracts this app consumes", "### EVT-009 Sale made\n\n### ENT-001 Basket\n\n## Contracts this app consumes")
    _, out = check(mini)
    assert codes(out) == []


def test_w384_an_entity_nobody_names(mini):
    edit(mini / SHOP, "| sold | | 200 | the receipt | | |", "| sold | | 200 | the receipt | | basket: open→paid |")
    _, out = check(mini)
    assert codes(out) == ["W384"]


def test_w385_a_decided_contract_with_no_error_case(mini):
    edit(mini / SHOP, "| basket_refused | | 422 | the basket is empty or holds an unknown product | | |\n", "")
    _, out = check(mini)
    assert codes(out) == ["W385"]


def test_w381_a_timeout_or_retries_line_it_cannot_read(mini):
    edit(mini / SHOP, "- **State:** decided\n", "- **State:** decided\n- **Can time out:** sometimes\n- **Retries:** 3\n"
                                            "- **Idempotent:** maybe\n")
    _, out = check(mini)
    assert codes(out) == ["W381", "W381", "W381"]
    assert "after which answers" in out


def test_retries_with_their_answers_and_an_idempotent_bullet_are_quiet(mini):
    edit(mini / SHOP, "- **State:** decided\n", "- **State:** decided\n- **Can time out:** yes\n- **Retries:** 2 after timeout\n"
                                            "- **Idempotent:** yes\n")
    _, out = check(mini)
    assert codes(out) == []


def test_the_skills_put_the_case_table_where_it_is_written_and_decided():
    from conftest import skill_text
    assert "case table" in skill_text("boundary") and "one question per open case" in skill_text("boundary")
    assert "not decided without its case table" in skill_text("grill")
    assert "case table" in skill_text("house-voice")
