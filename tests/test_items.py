from conftest import check, edit, findings

SHOP = "05-building-blocks/shop-building-blocks.md"
STOCK = "05-building-blocks/stock-building-blocks.md"
UNK = "11-unknowns-and-risks.md"
GOALS = "01-goals.md"


def codes(out):
    """Findings without W402. A changed source page rightly makes its generated
    blocks stale, so W402 is an echo here, not the finding under test."""
    return sorted(f for f in findings(out) if f[0] != "W402")


# unknowns and risks

def test_unknown_with_no_owner(mini):
    edit(mini / UNK, "- **Owner:** @mini-qa\n", "")
    _, out = check(mini)
    assert codes(out) == [("E302", UNK)]


def test_unknown_owner_must_be_a_handle(mini):
    edit(mini / UNK, "- **Owner:** @mini-qa\n", "- **Owner:** QA lead\n")
    _, out = check(mini)
    assert codes(out) == [("E302", UNK)]


def test_open_unknown_with_no_ask_by(mini):
    edit(mini / UNK, "- **Ask by:** 2026-02-01\n", "")
    _, out = check(mini)
    assert codes(out) == [("E302", UNK)]


def test_unknown_with_no_blocks(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "")
    _, out = check(mini)
    assert codes(out) == [("E302", UNK)]


def test_blocks_in_words_only(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** the till rollout\n")
    _, out = check(mini)
    assert codes(out) == [("E302", UNK)]


def test_resolved_unknown_needs_outcome(mini):
    edit(mini / UNK, "- **Outcome:** Yes, one VAT line per receipt.\n", "")
    _, out = check(mini)
    assert codes(out) == [("E302", UNK)]


def test_bad_ask_by_date(mini):
    edit(mini / UNK, "- **Ask by:** 2026-02-01", "- **Ask by:** 1 Feb 2026")
    _, out = check(mini)
    assert ("E106", UNK) in codes(out)


def test_overdue_unknown_is_a_warning(mini):
    code, out = check(mini, today="2026-02-02")
    assert code == 0
    assert codes(out) == [("W705", UNK)]
    assert "@mini-qa" in out


def test_unknown_state_enum(mini):
    edit(mini / UNK, "- **State:** resolved\n", "- **State:** done\n")
    _, out = check(mini)
    assert ("E105", UNK) in codes(out)


def test_risk_with_no_owner(mini):
    edit(mini / UNK, "- **Owner:** @mini/till-team\n", "")
    _, out = check(mini)
    assert ("E302", UNK) in codes(out)


# contracts

def test_contract_missing_a_required_fact(mini):
    edit(mini / SHOP, "- **Change policy:** versioned.\n", "")
    _, out = check(mini)
    assert codes(out) == [("E320", SHOP)]


def test_consumers_in_words(mini):
    edit(mini / STOCK, "- **Consumers:** [[shop-building-blocks|Shop]]", "- **Consumers:** the shop")
    _, out = check(mini)
    assert ("E311", STOCK) in codes(out)


def test_consumers_none_is_allowed(mini):
    edit(mini / STOCK, "- **Consumers:** [[shop-building-blocks|Shop]]", "- **Consumers:** none")
    _, out = check(mini)
    assert all(c != "E311" for c, _ in codes(out))


def test_decided_contract_without_tested_by(mini):
    edit(mini / SHOP, "- **Tested by:** consumer tests in the till pipeline.\n", "")
    _, out = check(mini)
    assert codes(out) == [("E318", SHOP)]


def test_contract_change_enum(mini):
    edit(mini / SHOP, "- **Change:** new\n", "- **Change:** brand new\n")
    _, out = check(mini)
    assert codes(out) == [("E105", SHOP)]


# certainty

def test_fact_without_source(mini):
    edit(mini / STOCK, "- **Source:** SRC-01\n", "")
    _, out = check(mini)
    assert codes(out) == [("E304", STOCK)]


def test_fact_page_without_sources(mini):
    edit(mini / STOCK, "sources: [SRC-01]\n", "")
    _, out = check(mini)
    assert codes(out) == [("E304", STOCK)]


def test_decided_without_decision_bullet(mini):
    edit(mini / GOALS, "- **Decision:** [[2026-01-10-shop-api]]\n", "")
    _, out = check(mini)
    assert codes(out) == [("E303", GOALS)]


def test_decided_by_a_session_that_is_not_a_grill(mini):
    edit(mini / "sessions/2026-01-10-shop-api.md", "modes: [grill]", "modes: [shape]")
    _, out = check(mini)
    assert [c for c, _ in codes(out)] == ["E303", "E303", "E303"]


def test_requirements_session_cannot_decide(mini):
    edit(mini / GOALS, "- **Decision:** [[2026-01-10-shop-api]]", "- **Decision:** [[2026-01-05-till-needs]]")
    _, out = check(mini)
    assert codes(out) == [("E317", GOALS)]


def test_gate_four_blocked_item_cannot_be_decided(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** [[shop-building-blocks#CON-001 Sale API|CON-001]]\n")
    _, out = check(mini)
    assert codes(out) == [("E316", SHOP)]
    assert "open unknown UNK-001 blocks it" in out


def test_gate_four_on_a_page(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** [[01-goals|Goals]]\n")
    _, out = check(mini)
    assert ("E316", GOALS) in codes(out)


# stage

def test_new_app_needs_a_stage(mini):
    edit(mini / SHOP, "stage: contracts\n", "")
    _, out = check(mini)
    assert ("E319", SHOP) in codes(out)


def test_unchanged_app_takes_no_stage(mini):
    edit(mini / STOCK, "change: unchanged\n", "change: unchanged\nstage: baseline\n")
    _, out = check(mini)
    assert codes(out) == [("E319", STOCK)]


# fact tables

def test_goal_row_state(mini):
    edit(mini / GOALS, "| One till sells every product | decided |", "| One till sells every product | agreed |")
    _, out = check(mini)
    assert codes(out) == [("E306", GOALS)]


def test_source_row_kind(mini):
    edit(mini / "sources.md", "| exists |", "| rumour |")
    _, out = check(mini)
    assert codes(out) == [("E306", "sources.md")]


def test_duplicate_item_heading(mini):
    edit(mini / STOCK, "### CON-002 Stock level", "### CON-001 Stock level")
    _, out = check(mini)
    assert ("E208", SHOP) in codes(out) or ("E208", STOCK) in codes(out)


def test_label_case_does_not_matter(mini):
    edit(mini / SHOP, "- **Tested by:** consumer tests", "- **Tested By:** consumer tests")
    code, out = check(mini)
    assert code == 0, out
