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


# fix round 1: GATE-4 reach, decided rows, malformed anchors and Decision links

def test_gate_four_page_link_reaches_items_on_the_page(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** [[shop-building-blocks|Shop]]\n")
    _, out = check(mini)
    assert ("E316", SHOP) in codes(out)
    assert "CON-001 is decided, but open unknown UNK-001 blocks it" in out


def test_gate_four_anchor_id_matches_in_any_case(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** [[shop-building-blocks#con-001 Sale API|CON-001]]\n")
    _, out = check(mini)
    assert ("E316", SHOP) in codes(out)  # E202 also fires: the anchor is not exact


def test_gate_four_page_link_reaches_decided_goal_rows(mini):
    edit(mini / GOALS, "state: decided\n", "state: assumption\n")
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** [[01-goals|Goals]]\n")
    _, out = check(mini)
    assert "G1 is decided, but open unknown UNK-001 blocks it" in out


def test_decided_goal_row_needs_a_grill(mini):
    edit(mini / GOALS, "state: decided\n", "state: assumption\n")
    edit(mini / GOALS, "- **Decision:** [[2026-01-10-shop-api]]\n", "")
    _, out = check(mini)
    assert codes(out) == [("E303", GOALS)]
    assert "G1" in out


def test_whitespace_only_anchor_is_not_a_crash(mini):
    edit(mini / UNK, "- **Blocks:** nothing\n", "- **Blocks:** [[shop-building-blocks# ]]\n")
    code, out = check(mini)
    assert code in (0, 1), out
    assert "internal error" not in out


def test_decision_linking_a_missing_session(mini):
    edit(mini / GOALS, "- **Decision:** [[2026-01-10-shop-api]]", "- **Decision:** [[2026-01-11-no-such-session]]")
    _, out = check(mini)
    assert ("E303", GOALS) in codes(out)


def test_decision_linking_a_page_that_is_not_a_session(mini):
    edit(mini / GOALS, "- **Decision:** [[2026-01-10-shop-api]]", "- **Decision:** [[shop-building-blocks]]")
    _, out = check(mini)
    assert ("E303", GOALS) in codes(out)


def test_grill_session_with_numeric_modes(mini):
    edit(mini / "sessions/2026-01-10-shop-api.md", "modes: [grill]", "modes: 5")
    code, out = check(mini)
    assert code == 1, out
    got = codes(out)
    assert ("E303", GOALS) in got
    assert ("E105", "sessions/2026-01-10-shop-api.md") in got


def test_an_epics_session_that_includes_grill_still_decides_and_passes(mini):
    edit(mini / "sessions/2026-01-10-shop-api.md", "modes: [grill]", "modes: [epics, shape, grill]")
    _, out = check(mini)
    assert codes(out) == []
