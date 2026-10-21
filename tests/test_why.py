"""A decided item keeps the lead's own reasons: the Grill asks for them, and the check names the item that has none."""
from conftest import check, edit, findings, REPO, run

SHOP = "05-building-blocks/shop-building-blocks.md"
WHY = "- **Why:** The till needs one place to ask for a sale.\n"


def whys(out):
    return [(code, path) for code, path in findings(out, keep_open=True) if code == "W390"]


def test_the_vault_whose_decisions_keep_their_why_is_quiet(mini):
    assert whys(check(mini)[1]) == []


def test_a_decided_contract_with_no_why_warns(mini):
    text = (mini / SHOP).read_text(encoding="utf-8")
    contract = text.index("### CON-001")
    (mini / SHOP).write_text(text[:contract] + text[contract:].replace(WHY, "", 1), encoding="utf-8")
    code, out = check(mini)
    assert code == 0  # a warning, never an error
    assert whys(out) == [("W390", SHOP)] and "(CON-001) is marked decided, but the reason isn't written down" in out


def test_a_decided_page_with_no_why_warns_once_however_many_rows_it_decides(mini):
    edit(mini / "01-goals.md", WHY, "")
    _, out = check(mini)
    assert whys(out) == [("W390", "01-goals.md")]


def test_a_why_under_the_items_history_entry_counts(mini):
    text = (mini / SHOP).read_text(encoding="utf-8")
    contract = text.index("### CON-001")
    text = text[:contract] + text[contract:].replace(WHY, "", 1)
    (mini / SHOP).write_text(text.rstrip("\n") + "\n\n## History\n\n#### CON-001 Sale API\n\n" + WHY, encoding="utf-8")
    _, out = check(mini)
    assert whys(out) == []


def test_a_decision_record_is_the_why_itself_and_needs_none(mini):
    (mini / "09-decisions").mkdir(exist_ok=True)
    (mini / "09-decisions" / "ADR-0001-one-till.md").write_text(
        "---\nid: ADR-0001\ntype: decision\ntitle: One till\nstate: decided\nowner: \"@mini-lead\"\nauthored: authored\n---\n\n# One till\n\n"
        "- **Decision:** [[2026-01-10-shop-api]]\n", encoding="utf-8")
    _, out = check(mini)
    assert whys(out) == []


def test_the_example_shows_the_warning_where_it_has_no_reason_to_give():
    code, out = run("check", "--vault", str(REPO / "examples" / "unified-booking"), "--today", "2026-11-20")
    assert code == 0 and ("W390", "05-building-blocks/booking-building-blocks.md") in whys(out)


def test_a_fixture_decision_takes_its_why_from_its_own_options_considered():
    text = (REPO / "tests" / "fixtures" / "team-skills" / "heron" / "04-solution-strategy.md").read_text(encoding="utf-8")
    assert "- **Why:** The cloud-written digest was rejected because it rules out a February 2, 2027 pilot" in text
