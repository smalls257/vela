"""Golden tests for the flow checker (design 19, amended by its review): one small vault per seeded issue under
tests/fixtures/flowcheck/<case>/, and the exact finding expected. Numbers follow the design's list (1 to 12) and the
review's (13 to 29)."""
import pathlib
import time

import pytest

from conftest import REPO, run

from planner import flowcheck
from planner.flowcheck import build, explore, readers, semantics

FIXTURES = REPO / "tests" / "fixtures" / "flowcheck"
TODAY = "2026-10-13"


def files_of(case):
    root = FIXTURES / case
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted(root.rglob("*")) if p.is_file()}


def flow_path(case):
    found = sorted((FIXTURES / case / "06-runtime" / "flows").glob("*.md"))
    return found[0].relative_to(FIXTURES / case).as_posix()


def at(case, text, nth=1):
    """'<flow path>:<line>' of the nth line of the case's flow page that contains `text`."""
    path = flow_path(case)
    lines = (FIXTURES / case / path).read_text(encoding="utf-8").split("\n")
    hits = [n for n, line in enumerate(lines, 1) if text in line]
    return f"{path}:{hits[nth - 1]}"


def check(case, target=None, **budget):
    target = target or pathlib.Path(flow_path(case)).name[:7]
    return flowcheck.check_slice(files_of(case), target, TODAY, **budget)


def found(result, *codes):
    return [(f.code, f.where) for f in result.findings if not codes or f.code in codes]


def errors(result):
    return [f.code for f in result.findings if f.severity == "error"]


def one(result, code):
    hits = [f for f in result.findings if f.code == code]
    assert len(hits) == 1, [f.format() for f in result.findings]
    return hits[0]


# --- the design's golden tests --------------------------------------------------------------------------------------

def test_01_a_409_nobody_handles_is_f1():
    case = "01-unhandled-409"
    result = check(case)
    f1 = one(result, "F1")
    assert (f1.where, f1.case, f1.call_line, f1.items) == (at(case, "CON-010"), "unavailable", at(case, "CON-010"), ("CON-010",))
    assert f1.summary == ('No branch for unavailable: Shop does not say what happens when Inventory answers unavailable (409) '
                          'on "Place a hold".')
    assert errors(result) == ["F1"] and result.status == "fails"


def test_02_a_branch_on_an_undeclared_case_is_f2():
    case = "02-invented-case"
    result = check(case)
    f2 = one(result, "F2")
    assert (f2.where, f2.case) == (at(case, "else sold_out"), "sold_out")
    assert f2.summary == 'Shop branches on sold_out, which "Place a hold" does not answer with here (it can answer: placed, unavailable).'
    assert errors(result) == ["F2"]


def test_03_an_event_with_no_subscriber_is_f3():
    case = "03-event-nobody"
    result = check(case)
    f3 = one(result, "F3")
    assert (f3.where, f3.case, f3.items) == (at(case, "CON-020"), "paid", ("CON-020", "EVT-020"))
    assert f3.summary == '"payment taken", published when "Take the payment" answers paid, has no subscriber at all.'
    assert errors(result) == ["F3"]


def test_04_register_then_bill_passes_when_the_order_is_saved_first():
    result = check("04-chain-correct")
    assert result.status == "passes", result.format()
    assert errors(result) == []


def test_04_billing_before_the_order_is_saved_is_f8_not_f7():
    """Design 19 labels this F7; by its own definitions every thread ends, so it is F8 (review 1.3)."""
    case = "04-chain-early-billing"
    result = check(case)
    f8 = one(result, "F8")
    assert f8.where == at(case, "END refused")  # the last transition: Billing giving up
    assert f8.summary == ("Order 1 is left pending, which is not one of its final states (completed, rejected), and no END says "
                          "the journey leaves it so.")
    assert f8.trace == (
        'Order service asks Registration to register the customer, and Registration answers created (201); Registration publishes "registration created".',
        'Billing receives "registration created".',
        "Billing asks Order service to complete the order, and is refused: not found (409).",
        'Billing\'s handling of "registration created" ends refused; it tries again (attempt 2 of 2).',
        "Billing asks Order service to complete the order, and is refused: not found (409).",
        "Order service sets Order 1 to pending.",
        "The journey ends: registered.",
        'Billing\'s handling of "registration created" ends refused, and Billing has no retries left.',
    )
    assert f8.owners == ("Billing", "Order service")
    assert f8.items == ("CON-030", "EVT-003", "CON-041", "ENT-004")
    assert errors(result) == ["F8"]


def test_05_a_hold_never_released_after_a_decline_is_f8():
    case = "05-hold-never-released"
    result = check(case)
    f8 = one(result, "F8")
    assert f8.where == at(case, "END declined")
    assert f8.trace == ("Shop asks Inventory to place a hold, and Inventory answers placed (200); Hold 1 is now held.",
                        "Shop asks Tidepay to take the payment, and is refused: declined (402).",
                        "The journey ends: declined.")
    assert f8.summary.startswith("Hold 1 is left held, which is not one of its final states (released, captured)")
    assert (f8.call_line, f8.case) == (at(case, "CON-020"), "declined")
    assert errors(result) == ["F8"]


def test_06_two_orders_take_the_last_item_with_shared_stock_is_f9():
    case = "06-two-orders-last-item"
    result = check(case)
    f9 = one(result, "F9")
    assert f9.summary == 'The invariant "not stock=minus_one" of Stock no longer holds.'
    assert f9.trace == (
        "Journey 1: Shop asks Inventory to check the stock, and Inventory answers in stock (200).",
        "Journey 2: Shop asks Inventory to check the stock, and Inventory answers in stock (200).",
        "Journey 2: Shop asks Inventory to reserve the item, and Inventory answers reserved (200); Stock is now zero.",
        "Journey 1: Shop asks Inventory to reserve the item, and Inventory answers reserved (200); Stock is now minus one.",
    )
    assert errors(result) == ["F9"]
    assert result.runs == [(("FLO-006", "FLO-006"), result.states, result.transitions, True)]


def test_07_an_at_least_once_event_charged_twice_is_f9():
    result = check("07-duplicate-billing")
    f9 = one(result, "F9")
    assert f9.trace == (
        'Shop publishes "order placed" for Billing.',
        'Billing receives "order placed", and a duplicate is still on its way.',
        "Billing asks Cardco to charge the card, and Cardco answers charged (200); Payment 1 is now charged.",
        'Billing receives "order placed" a second time.',
        "Billing asks Cardco to charge the card, and Cardco answers charged (200); Payment 1 is now charged twice.",
    )
    assert errors(result) == ["F9"]


def test_08_an_awaited_may_be_lost_event_with_no_timer_is_f6():
    case = "08-lost-event-no-timer"
    result = check(case)
    f6 = one(result, "F6")
    assert f6.summary == ('Shop is still waiting for "invoice ready", which can no longer come. '
                          "From step 4 on it could no longer finish.")
    assert f6.trace[3] == '"invoice ready" is lost on its way to Shop.'
    assert f6.owners[:2] == ("Billing", "Shop")
    assert errors(result) == ["F6"]


def test_09_retries_with_no_gave_up_branch_is_f1_and_with_one_passes():
    case = "09-retries-no-gave-up"
    f1 = one(check(case), "F1")
    assert (f1.where, f1.case) == (at(case, "CON-060"), "gave_up")
    assert f1.summary == ('No branch for gave_up: Shop does not say what happens when every one of its 3 attempts fails on '
                          '"Take the payment".')
    assert check("09-retries-with-gave-up").status == "passes"


def test_10_an_unreadable_line_and_a_missing_delivery_are_f10_and_not_fully_checked():
    case = "10-unreadable-and-undeclared"
    result = check(case)
    assert found(result) == [("F10", at(case, "loop every morning")), ("F10", at(case, "EVT-010"))]
    assert result.findings[1].summary.startswith("EVT-010 has no delivery")
    assert result.status == "not fully checked"
    assert result.states == 0  # a model with a hole in it is not explored


def test_11_a_budget_too_small_is_f11_never_a_pass():
    result = check("12-clean-tracer", "Release one", max_states=5)
    assert errors(result) == ["F11"]
    assert result.status == "not fully checked"
    assert "budget of 5 states ran out" in one(result, "F11").summary


def test_12_a_clean_three_app_tracer_passes_fast():
    started = time.perf_counter()
    result = flowcheck.check_slice(files_of("12-clean-tracer"), "Release one", TODAY, clock=time.perf_counter)
    assert result.status == "passes", result.format()
    assert result.name == "Release one: pilot" and result.flows == ("FLO-012",)
    assert time.perf_counter() - started < 1.0
    assert {f.code for f in result.findings} <= {"F12"}  # Inventory answers from its contract: a warning, not a failure


# --- the review's golden tests --------------------------------------------------------------------------------------

def test_13_a_timed_out_call_may_have_taken_the_payment():
    f8 = one(check("13-timeout-no-reconcile"), "F8")
    assert f8.trace == ("Shop asks Tidepay to take the payment, and the call times out, though Tidepay had in fact answered "
                        "paid; Charge 1 is now taken.", "The journey ends: payment failed.")
    assert (f8.case, f8.call_line) == ("timeout", at("13-timeout-no-reconcile", "CON-020"))
    assert check("13-timeout-reconciled").status == "passes"


def test_14_retrying_a_charge_on_timeout_charges_twice_unless_idempotent():
    f9 = one(check("14-retry-double-charge"), "F9")
    assert f9.trace == ("Shop asks Tidepay to take the payment, and the call times out, though Tidepay had in fact answered "
                        "paid; Shop tries again (attempt 2 of 2); Charge 1 is now taken.",
                        "Shop asks Tidepay to take the payment, and Tidepay answers paid (200); Charge 1 is now taken twice.")
    assert check("14-retry-idempotent").status == "passes"


def test_15_a_late_duplicate_after_quiescence_is_f8():
    f8 = one(check("15-late-duplicate"), "F8")
    assert f8.summary.startswith("Ticket 1 is left open")
    assert 'Ticket service receives "close requested" a second time.' in f8.trace
    assert f8.trace[-2] == "Ticket service asks Helpdesk to toggle the ticket, and Helpdesk answers toggled (200); Ticket 1 is now open."


def test_17_an_awaited_lost_event_with_a_timer_passes():
    assert check("17-lost-event-with-timer").status == "passes"


def test_18_a_webhook_that_may_never_come_needs_the_hold_expiry_timer():
    f8 = one(check("18-webhook-no-timer"), "F8")
    assert f8.trace[-1] == '"Report the payment" is lost on its way to Shop.'
    assert f8.where == at("18-webhook-no-timer", "END waiting")
    assert check("18-webhook-with-timer").status == "passes"


def test_19_an_unclosed_handler_and_a_branch_on_a_handler_outcome_are_f10():
    result = check("19-handler-not-closed")
    assert found(result) == [("F10", at("19-handler-not-closed", "par Mailer"))]
    assert result.findings[0].summary == "The par block opened here is never closed with end."
    result = check("19-branch-on-handler-outcome")
    assert found(result) == [("F10", at("19-branch-on-handler-outcome", "alt handled"))]


def test_20_a_drawn_provider_answers_per_its_drawing_and_an_undrawn_one_is_f12():
    """Drawn: Booking answers held only after the ferry reserved, so the invariant holds. Not drawn: Booking may
    answer held from its contract with no seat reserved; F12 says why the model knows no better."""
    assert check("20-provider-drawn").status == "passes"
    result = check("20-provider-not-drawn")
    assert [f.code for f in result.findings] == ["F12", "F9"]


def test_21_confirm_and_cancel_on_one_shared_booking_race():
    result = check("21-shared-race", "Release one")
    assert [r[0] for r in result.runs] == [("FLO-211", "FLO-211"), ("FLO-211", "FLO-212"), ("FLO-212", "FLO-212")]
    summaries = [f.summary for f in result.findings if f.code == "F5"]
    assert 'Booking is cancelled, and "Confirm the booking" answering confirmed gives it nowhere to go from there.' in summaries


def test_21_symmetry_halves_the_same_flow_pair_and_finds_the_same():
    catalog = readers.read_vault(files_of("06-two-orders-last-item"))
    program, _ = build.build(catalog, ("FLO-006",), TODAY)
    graphs = {}
    for name, reductions in (("with", semantics.ALL_REDUCTIONS), ("without", {semantics.LOCAL_STEPS})):
        sem = semantics.Semantics(program, (0, 0), reductions)
        graphs[name] = explore.explore(sem, 10_000, 10, flowcheck.frozen_clock)
    assert graphs["with"].complete and graphs["without"].complete
    assert len(graphs["with"].states) < 0.75 * len(graphs["without"].states)
    with_symmetry = check("06-two-orders-last-item")
    without = flowcheck.check_slice(files_of("06-two-orders-last-item"), "FLO-006", TODAY, reductions={semantics.LOCAL_STEPS})
    assert [(f.code, f.summary) for f in with_symmetry.findings] == [(f.code, f.summary) for f in without.findings]


def test_22_given_sets_where_a_mid_lifecycle_flow_starts():
    assert check("22-given").status == "passes"
    f5 = one(check("22-no-given"), "F5")
    assert f5.summary.endswith("The flow has no GIVEN, so Booking starts at its initial state, new; did you mean GIVEN booking confirmed?")


def test_23_a_release_cut_leaves_a_state_the_next_release_must_start_from():
    files = files_of("23-release-cut")
    assert flowcheck.check_slice(files, "Release one", TODAY).status == "passes"
    result = flowcheck.check_slice(files, "Release two", TODAY)
    f13 = one(result, "F13")
    assert f13.summary == "FLO-232 starts from Hold paid, and no flow in this or an earlier release ends leaving it paid."
    assert errors(result) == ["F13"]


def test_24_an_event_consumed_only_outside_the_slice_is_a_warning():
    result = check("24-outside-subscriber")
    assert [f.code for f in result.findings] == ["F3w"] and result.status == "passes"


def test_25_grouped_branches_and_an_on_rule_cover_every_case_and_are_reachable():
    case = "25-grouped-and-on"
    assert check(case).status == "passes"
    catalog = readers.read_vault(files_of(case))
    program, _ = build.build(catalog, ("FLO-025",), TODAY)
    calls = {ins.data["contract"]: ins for ins in program.code if ins.kind == "call"}
    assert set(calls["CON-010"].data["branches"]) == {"placed", "unavailable", "blocked", "timeout"}
    assert set(calls["CON-020"].data["branches"]) == {"paid", "timeout"}
    sem = semantics.Semantics(program, (0,))
    graph = explore.explore(sem, 10_000, 10, flowcheck.frozen_clock)
    ends = {program.code[label[2]].where for label in graph.label if label and label[0] == "end"}
    uniform = {ins.where for ins in program.code if ins.kind == "end" and ins.data.get("uniform")}
    assert uniform and uniform <= ends


def test_26_a_budget_stop_reports_f11_alone_even_with_a_real_f6_ahead():
    result = check("08-lost-event-no-timer", max_states=2)
    assert errors(result) == ["F11"] and result.status == "not fully checked"


def test_27_one_lost_event_behind_many_unfinished_states_is_one_finding():
    result = check("27-frontier")
    assert [f.code for f in result.findings] == ["F6"]
    assert result.states > 50


def test_28_the_same_vault_gives_byte_identical_output():
    first = check("04-chain-early-billing").format()
    second = check("04-chain-early-billing").format()
    assert first == second


def test_29_a_hand_written_case_table_gives_the_openapi_twin_s_findings():
    def view(result):
        return [(f.code, f.summary, f.trace, f.items, f.owners, f.case) for f in result.findings]
    assert view(check("29-case-table-twin")) == view(check("04-chain-early-billing"))


# --- readers, overrides and the CLI ---------------------------------------------------------------------------------

def test_a_yaml_on_key_still_reads_as_the_retried_outcomes():
    catalog = readers.read_vault(files_of("04-chain-early-billing"))
    assert dict(catalog.events["EVT-003"].subscribers)["billing"].on == ("refused",)


def test_an_override_with_a_future_end_date_covers_f1_and_an_expired_one_does_not():
    files = files_of("01-unhandled-409")
    page = flow_path("01-unhandled-409")
    for until, severity in (("2026-12-01", "covered"), ("2026-10-01", "error")):
        changed = dict(files)
        changed[page] += f'\n- **Override:** "F1 CON-010 unavailable until {until}" by @lead on 2026-10-13: next sprint\n'
        f1 = one(flowcheck.check_slice(changed, "FLO-001", TODAY), "F1")
        assert f1.severity == severity
    covered = dict(files)
    covered[page] += '\n- **Override:** "F1 CON-010 unavailable until 2026-12-01" by @lead on 2026-10-13: next sprint\n'
    assert flowcheck.check_slice(covered, "FLO-001", TODAY).status == "passes"


def test_an_unknown_slice_names_the_releases():
    with pytest.raises(flowcheck.SliceNotFound, match="Release one: pilot"):
        check("12-clean-tracer", "Release nine")


def test_the_cli_exits_0_on_a_pass_1_on_findings_and_prints_plain_words():
    code, out = run("check-slice", "Release one", "--vault", str(FIXTURES / "12-clean-tracer"))
    assert code == 0 and "passes" in out.splitlines()[0]
    code, out = run("check-slice", "FLO-004", "--vault", str(FIXTURES / "04-chain-early-billing"))
    assert code == 1 and "F8 Not final" in out and "Billing has no retries left" in out
    code, out = run("check-slice", "Release one", "--vault", str(FIXTURES / "12-clean-tracer"), "--max-states", "5")
    assert code == 1 and "not fully checked" in out
