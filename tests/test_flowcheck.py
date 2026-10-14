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
    assert result.findings == []  # Inventory answers from its contract and calls nobody, so no F12 (revision 2, item 8)


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
    assert 'Booking is canceled, and "Confirm the booking" answering confirmed gives it nowhere to go from there.' in summaries


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
    assert f13.summary == "FLO-232 starts from Hold paid, and no flow in this or an earlier slice ends leaving it paid."
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


def copy_fixture(tmp_path, case):
    """A copy to run the CLI on: check-slice records its result under the vault's .planner/."""
    import shutil
    target = tmp_path / case
    shutil.copytree(FIXTURES / case, target)
    return target


def test_the_cli_exits_0_on_a_pass_1_on_findings_and_prints_plain_words(tmp_path):
    clean, early = copy_fixture(tmp_path, "12-clean-tracer"), copy_fixture(tmp_path, "04-chain-early-billing")
    code, out = run("check-slice", "Release one", "--vault", str(clean))
    assert code == 0 and "passes" in out.splitlines()[0]
    code, out = run("check-slice", "FLO-004", "--vault", str(early))
    assert code == 1 and "F8 Not final" in out and "Billing has no retries left" in out
    code, out = run("check-slice", "Release one", "--vault", str(clean), "--max-states", "5")
    assert code == 1 and "not fully checked" in out


# --- design 19 revision 2: one fixture per changed item ---------------------------------------------------------------

def test_r2_01_a_timed_out_call_may_have_been_answered_events_included():
    """Item 1: an undrawn provider that timed out either did nothing or applied a case, its events included."""
    case = "r2-01-timeout-published-anyway"
    result = check(case)
    # One finding: the same rule broken by the same answers, whether the parcel ships before or after the cancel.
    assert errors(result) == ["F9"]
    first = result.findings[0]
    assert first.trace[0] == ('Shop asks Payments to take the payment, and the call times out, though Payments had in fact '
                              'answered paid and published "payment taken".')
    assert first.trace[-1] == "Warehouse sets Parcel 1 to shipped."
    assert set(first.owners) == {"Shop", "Warehouse"}


def test_r2_04_a_when_column_keeps_a_case_to_the_states_it_names():
    """Item 4: with the When, already_gone is no answer to a held booking; without it the booking can be left held."""
    case = "r2-04-when"
    assert check(case).status == "passes"
    files = files_of(case)
    page = "05-building-blocks/booking-building-blocks.md"
    files[page] = files[page].replace("| already_gone | booking is not held and booking is not paid |", "| already_gone | |")
    f8 = one(flowcheck.check_slice(files, "FLO-304", TODAY), "F8")
    assert f8.summary.startswith("Booking 1 is left held")


def test_an_unreadable_bullet_on_a_contract_with_a_when_column_is_f10_not_a_crash():
    """Ledger C47: a problem tied to an item made the builder unpack a When clause (three parts) as a Sets pair (two)."""
    files = files_of("r2-04-when")
    page = "05-building-blocks/booking-building-blocks.md"
    files[page] = files[page].replace("- **Retries:** none", "- **Retries:** often", 1)
    result = flowcheck.check_slice(files, "FLO-304", TODAY)
    assert result.status == "not fully checked" and "F10" in [f.code for f in result.findings]


def test_r2_05_a_change_with_no_row_for_the_current_state_is_illegal():
    """Item 5: `ticket: open→closed` moves an open ticket only; closing a closed one has nowhere to go."""
    f5 = one(check("r2-05-no-row-for-the-state"), "F5")
    assert f5.summary == 'Ticket 1 is closed, and "Close the ticket" answering closed gives it nowhere to go from there.'
    assert f5.owners == ("Agent desk", "Helpdesk")


def test_r2_08_drawn_handling_can_answer_from_its_contract():
    """Item 8: the marker lets drawn handling decide on the request's content; held only ever follows a reserved seat,
    so the invariant holds, both answers are reachable, and a provider outside the vault gets no F12."""
    case = "r2-08-answers-from-contract"
    result = check(case)
    assert result.status == "passes" and result.findings == [], result.format()
    catalog = readers.read_vault(files_of(case))
    program, _ = build.build(catalog, ("FLO-308",), TODAY)
    graph = explore.explore(semantics.Semantics(program, (0,)), 1000, 10, flowcheck.frozen_clock)
    table = program.contracts["CON-380"]
    answered = {table.cases[label[6]].key for label in graph.label
                if label and label[0] == "reply" and len(label) > 6 and label[6] >= 0}
    assert answered == {"held", "sold_out"}


def test_r2_08_answers_from_contract_outside_drawn_handling_is_unreadable():
    files = files_of("r2-08-answers-from-contract")
    page = flow_path("r2-08-answers-from-contract")
    files[page] = files[page].replace("alt held\n", "alt held\n    Note over W: ANSWERS FROM CONTRACT\n")
    assert flowcheck.check_slice(files, "FLO-308", TODAY).status == "not fully checked"


def test_r2_10_a_timer_that_wins_the_race_leaves_the_late_event_nowhere_to_go():
    """Item 10: the AWAIT and the timer race, the winner cancels the other, and the payment confirmation that comes
    after the hold was released is a message nothing will take."""
    f6 = one(check("r2-10-timer-race"), "F6")
    assert f6.summary == ('"payment confirmed" is still on its way to Shop, and nothing will take it. '
                          "From step 4 on it could no longer finish.")
    assert f6.trace[2:4] == ("Shop starts the pay window timer (15m).", "The pay window timer fires.")
    assert f6.owners == ("Shop", "Billing")


def test_r2_10_an_await_branch_on_a_timer_it_never_armed_is_a_finding():
    files = files_of("r2-10-timer-race")
    page = flow_path("r2-10-timer-race")
    files[page] = files[page].replace("else pay_window", "else hold_window")
    assert "F2" in [f.code for f in flowcheck.check_slice(files, "FLO-310", TODAY).findings]


def test_r2_13_an_invariant_with_or_and_parentheses():
    f9 = one(check("r2-13-or-invariant"), "F9")
    assert f9.summary == 'The invariant "not (order=shipped and (payment=none or payment=refunded))" of Order no longer holds.'
    assert readers.parse_invariant("a=x or b=y and c=z")[0] == ("or", ("is", "a", "x"), ("and", ("is", "b", "y"), ("is", "c", "z")))


def test_r2_18_unquoted_yaml_booleans_and_an_on_retry_key_are_refused():
    """Item 18: YAML reads off as false and on: as true; the reader says so instead of reading them."""
    result = check("r2-18-yaml-trap")
    summaries = [f.summary for f in result.findings if f.code == "F10"]
    assert any("x-vela-retries says on:" in s for s in summaries)
    assert any("quote such a state" in s for s in summaries)
    assert result.status.endswith("not fully checked") and result.states == 0


def test_c40_a_timeout_part_way_through_drawn_handling_leaves_what_the_provider_had_done():
    """Ledger C40: Store sets the hold, then Shop's call times out before Store charges the card. Store stops there, the
    hold stays held, and Shop cancels. Before part-way timeouts were modeled this slice showed only the late answer."""
    case = "r2-40-timeout-part-way"
    result = check(case)
    f8 = one(result, "F8")
    assert f8.summary.startswith("Hold 1 is left held, which is not one of its final states")
    assert f8.trace == ("Shop asks Store to take the order.",
                        "Store sets Hold 1 to held.",
                        'Shop times out waiting for Store part-way through "Take the order": Store stops there, and what '
                        "it has done so far stands.",
                        "Shop sets Order 1 to canceled.",
                        "The journey ends: canceled.")
    assert (f8.call_line, f8.case) == (at(case, "CON-401"), "timeout")
    assert f8.owners == ("Shop", "Store")
    assert sorted(errors(result)) == ["F8", "F9"]


def test_c40_a_provider_that_carries_on_after_its_caller_moved_on_races_the_callers_lookup():
    """Shop looks the order up after a timeout, finds nothing yet, and cancels; Store, still going, then takes the card.
    Only a provider that carries on alone finds it: before it acts and after it answers, the lookup agrees."""
    case = "r2-40-timeout-late-answer"
    f9 = one(check(case), "F9")
    assert f9.summary == 'The invariant "not (order=canceled and hold=captured)" of Order no longer holds.'
    assert f9.trace[2] == 'Shop times out waiting for Store part-way through "Take the order": Store carries on with it alone.'
    assert f9.trace[3:] == ("Shop asks Store to look up the order, and is refused: not found (404).",
                            "Shop sets Order 1 to canceled.", "Store sets Hold 1 to captured.")


def test_c40_a_provider_that_changes_state_in_one_step_passes_however_the_timeout_falls():
    result = check("r2-40-timeout-part-way-one-step")
    assert result.status == "passes", result.format()
    assert errors(result) == []


def test_c40_an_answer_that_goes_nowhere_ends_the_provider_and_retries_reenter_its_handling():
    """The semantics directly: a part-way timeout that is retried enters the drawn handling again; an answer to a caller
    that moved on ends the provider's thread, and the slice can still finish."""
    files = files_of("r2-40-timeout-part-way-one-step")
    page = "05-building-blocks/store-building-blocks.md"
    files[page] = files[page].replace("- **Can time out:** yes\n- **Retries:** none", "- **Can time out:** yes\n- **Retries:** 1 after timeout", 1)
    flow = flow_path("r2-40-timeout-part-way-one-step")
    files[flow] = files[flow].replace("else refused, timeout", "else refused, gave_up")
    catalog = readers.read_vault(files)
    program, _ = build.build(catalog, ("FLO-402",), TODAY)
    sem = semantics.Semantics(program, (0,))
    graph = explore.explore(sem, 10_000, 10, flowcheck.frozen_clock)
    kinds = {label[0] for label in graph.label if label}
    assert {"ptmo", "pcarry", "late"} <= kinds
    assert any(label[0] == "ptmo" and label[5] == 1 for label in graph.label if label)  # tried again
    assert any(label[0] == "ptmo" and label[5] == 2 for label in graph.label if label)  # gave up after the last
    assert graph.complete and any(sem.finished(s) for s in graph.states)


# --- limits said out loud, and three journeys on request (ledger C39) -------------------------------------------------

def _three_orders_two_items():
    """06 with two items in stock: two orders can never oversell, three can."""
    files = files_of("06-two-orders-last-item")
    files["entities/stock.md"] = (files["entities/stock.md"].replace("initial: one\nfinal: [one, zero]", "initial: two\nfinal: [two, one, zero]")
                                  .replace("| one | zero | CON-021 reserved |", "| two | one | CON-021 reserved |\n| one | zero | CON-021 reserved |"))
    page = "05-building-blocks/inventory-building-blocks.md"
    files[page] = (files[page].replace("| in_stock | stock is one |", "| in_stock | stock in [two, one] |")
                   .replace("stock: one→zero, zero→minus_one", "stock: two→one, one→zero, zero→minus_one"))
    return files


def test_a_result_over_a_shared_entity_says_it_ran_pairs_not_triples():
    result = check("06-two-orders-last-item")
    assert result.limits == ["Stock is shared, so the flows that touch it ran two journeys at once, not three "
                             "(--journeys 3 tries three)."]
    assert "Limit: Stock is shared" in result.format().split("\n")[1]


def test_three_journeys_on_request_find_the_race_two_cannot():
    files = _three_orders_two_items()
    pairs = flowcheck.check_slice(files, "FLO-006", TODAY)
    assert pairs.status == "passes", pairs.format()
    triples = flowcheck.check_slice(files, "FLO-006", TODAY, journeys=3)
    f9 = one(triples, "F9")
    assert f9.summary == 'The invariant "not stock=minus_one" of Stock no longer holds.'
    assert {line.split(":")[0] for line in f9.trace} == {"Journey 1", "Journey 2", "Journey 3"}
    assert [r[0] for r in triples.runs] == [("FLO-006", "FLO-006"), ("FLO-006", "FLO-006", "FLO-006")]
    assert triples.limits == ["Stock is shared, so the flows that touch it ran two and three journeys at once, never four."]


def test_journeys_other_than_two_or_three_are_refused():
    catalog = readers.read_vault(files_of("06-two-orders-last-item"))
    program, _ = build.build(catalog, ("FLO-006",), TODAY)
    with pytest.raises(ValueError, match="journeys must be 2 or 3"):
        flowcheck.plan_runs(program, 4)


def test_a_slice_with_a_timer_says_it_takes_timers_to_fire():
    assert "A timer is taken to fire in the end: an order of events in which a timer never fires is not explored." in \
        check("r2-10-timer-race").limits


def test_a_plain_slice_states_no_limits():
    assert check("12-clean-tracer").limits == []


def test_a_budget_stop_names_the_run_it_stopped_in_and_the_runs_it_skipped():
    """The write-up's §5: a budget stop used to end the slice without a word about the runs after it."""
    result = check("21-shared-race", "Release one", max_states=3)
    f11 = one(result, "F11")
    assert "while checking FLO-211 and FLO-212 together." in f11.summary
    assert [r[3] for r in result.runs] == [True, False]
    assert result.skipped == [("FLO-212", "FLO-212")]
    assert result.limits[-1] == "Not explored, because the budget ran out first: FLO-212 twice."
    assert result.status.endswith("not fully checked")


# --- noise: warnings that fire only on a real gap ---------------------------------------------------------------------

def test_f12_is_quiet_when_everything_the_provider_calls_is_drawn_in_the_slice():
    """Heron's false alarm: Consent and identity answered the consent check from its contract, though the Microsoft
    sign-in it calls was drawn in Record consent's handling, in the same slice. Here Store answers the lookup from its
    contract, and the card charge it calls is drawn in Take the order's handling."""
    case = "r2-40-timeout-late-answer"
    assert "F12" not in [f.code for f in check(case).findings]


def test_f12_still_fires_for_a_call_the_slice_never_draws_and_names_it():
    files = files_of("r2-40-timeout-late-answer")
    page = "05-building-blocks/store-building-blocks.md"
    files[page] += ("\n### CON-404 Ask the fraud desk\n\n- **Provider:** Fraudco\n- **Consumers:** [[store-building-blocks|Store]]\n"
                    "- **Can time out:** no\n- **Retries:** none\n\n| Case | When | Status | Answer | Emits | Sets |\n"
                    "|---|---|---|---|---|---|\n| clear |  | 200 | clear |  |  |\n")
    f12 = one(flowcheck.check_slice(files, "FLO-403", TODAY), "F12")
    assert f12.summary == ('Store answers "Look up the order" from its contract alone in this flow, and it calls "Ask the '
                           'fraud desk" itself, which no flow of this slice draws it calling; what it does with the answers '
                           "is not checked here.")
    assert f12.items == ("CON-403", "CON-404")


def test_f12_fires_for_a_flow_checked_alone_when_its_calls_are_drawn_only_in_another_flow():
    """The rule is per slice: checked on its own, the lookup flow has no drawing of the charge Store makes."""
    files = files_of("r2-40-timeout-late-answer")
    flow = flow_path("r2-40-timeout-late-answer")
    files[flow] = files[flow].replace("S->>T: CON-401 take the order\nT->>P: CON-402 charge the card\nalt charged\n    P-->>T: 200 charged\n"
                                      "    Note over T: SET hold captured\n    T-->>S: 200 taken\nelse declined\n    P-->>T: 402 declined\n"
                                      "    T-->>S: 402 refused\nend\n", "S->>T: CON-401 take the order\n")
    codes = [f.code for f in flowcheck.check_slice(files, "FLO-403", TODAY).findings]
    assert codes.count("F12") == 2  # both of Store's answers, Take the order and the lookup, now hide the charge


def _with_unreached_case(files):
    page = "05-building-blocks/booking-building-blocks.md"
    files[page] = files[page].replace("| unavailable |  | 503 | unavailable |  |  |\n",
                                      "| unavailable |  | 503 | unavailable |  |  |\n| waitlisted |  | 202 | on the waiting list |  |  |\n", 1)
    return files


UNDRAWN_FLOW = ("---\nid: FLO-099\ntype: flow\ntitle: A traveler changes a seat\nstate: assumption\n---\n\n# A traveler changes a seat\n\n"
                "## Steps\n\n1. [[website-building-blocks|Website]] → [[booking-building-blocks|Booking]]: asks for a seat, over "
                "[[booking-building-blocks#CON-100 Hold a seat|Hold a seat]].\n")


def test_f4_still_fires_for_a_case_no_flow_reaches_when_every_flow_that_crosses_it_is_drawn():
    result = flowcheck.check_slice(_with_unreached_case(files_of("20-provider-drawn")), "FLO-020", TODAY)
    f4 = one(result, "F4")
    assert f4.summary == 'Case waitlisted of "Hold a seat" is reached by no flow.'


def test_f4_is_not_claimed_while_a_flow_that_crosses_the_contract_is_undrawn():
    """Heron's other false alarm: "transcripts alone" of Record consent, reached by no drawn flow, while the withdrawal
    flow, which crosses Record consent, had no diagram yet."""
    files = _with_unreached_case(files_of("20-provider-drawn"))
    files["06-runtime/flows/FLO-099-change-a-seat.md"] = UNDRAWN_FLOW
    assert "F4" not in [f.code for f in flowcheck.check_slice(files, "FLO-020", TODAY).findings]


def test_one_missing_branch_is_one_finding_not_an_unhandled_and_an_unused_case():
    assert [f.code for f in check("01-unhandled-409").findings] == ["F1"]


# --- slices, overrides and the check warning --------------------------------------------------------------------------

def test_a_later_release_names_its_slice_with_a_flows_bullet():
    from planner import model, parse, slices
    text = ("---\nid: releases\ntype: initiative-section\ntitle: Releases\n---\n\n# Releases\n\n## Release one: pilot\n\n"
            "- **State:** assumption\n- **Tracer:** [[FLO-001-a|FLO-001]], thin\n\n## Release two: more\n\n"
            "- **State:** assumption\n- **Flows:** [[FLO-002-b|FLO-002]], [[FLO-003-c|FLO-003]]\n\n## Release three\n\n"
            "- **State:** inkling\n")
    found = slices.read_slices(model.build([parse.parse_page("04b-releases.md", text)], {}))
    assert [(s.name, s.flows, s.order) for s in found] == [("Release one: pilot", ("FLO-001",), 0),
                                                          ("Release two: more", ("FLO-002", "FLO-003"), 1)]


def _with_override(case, rule, until):
    files = files_of(case)
    page = flow_path(case)
    files[page] += f'\n## History\n\n- **Override:** "{rule} until {until}" by @lead on 2026-10-13: the refund flow lands next sprint\n'
    return files


def test_an_override_covers_an_explored_finding_until_its_date_then_it_blocks_again():
    """Item 21: scoped to flow, code, item and case; past its date the finding is an error and says when it ended."""
    case = "05-hold-never-released"
    covered = flowcheck.check_slice(_with_override(case, "F8 CON-020 declined", "2026-12-01"), "FLO-005", TODAY)
    assert covered.status == "passes" and one(covered, "F8").severity == "covered"
    expired = flowcheck.check_slice(_with_override(case, "F8 CON-020 declined", "2026-10-01"), "FLO-005", TODAY)
    f8 = one(expired, "F8")
    assert f8.severity == "error"
    assert f8.summary.endswith("The override for it ended on 2026-10-01, so it blocks the slice again.")
    other_case = flowcheck.check_slice(_with_override(case, "F8 CON-020 paid", "2026-12-01"), "FLO-005", TODAY)
    assert one(other_case, "F8").severity == "error"


def test_an_override_cannot_cover_not_fully_checked_and_a_misspelled_one_is_said():
    result = flowcheck.check_slice(_with_override("10-unreadable-and-undeclared", "F10 EVT-010 delivery", "2026-12-01"),
                                   "FLO-010", TODAY)
    assert any("no override covers it" in f.summary for f in result.findings)
    result = flowcheck.check_slice(_with_override("01-unhandled-409", "F1 CON-010", "2026-12-01"), "FLO-001", TODAY)
    assert result.status == "fails, and is not fully checked"  # the F1 stands, and the typo is said
    assert any('is not "<code> <ID> <case> until YYYY-MM-DD"' in f.summary for f in result.findings)


def test_the_default_budget_is_200000_states_and_10_seconds_and_the_clock_is_frozen():
    import inspect
    defaults = inspect.signature(flowcheck.check_slice).parameters
    assert defaults["max_states"].default == 200_000 and defaults["max_seconds"].default == 10.0
    assert defaults["clock"].default is flowcheck.frozen_clock


def test_check_warns_w391_for_a_drawn_slice_with_open_findings_and_stays_quiet_on_a_pass():
    _, out = run("check", "--vault", str(FIXTURES / "05-hold-never-released"), "--today", TODAY)
    lines = [line for line in out.splitlines() if " W391 " in line]
    assert lines == ['04b-releases.md:13: W391 Release one: pilot fails: 1 open finding (not final). Fix: Run planner '
                     'check-slice "Release one: pilot" for the traces and owners, and fix or override each.']
    _, out = run("check", "--vault", str(FIXTURES / "12-clean-tracer"), "--today", TODAY)
    assert " W391 " not in out


def test_a_tracer_with_nothing_drawn_is_not_fully_checked_and_check_leaves_it_to_check_slice(tmp_path):
    import shutil
    vault = tmp_path / "v"
    shutil.copytree(FIXTURES / "12-clean-tracer", vault)
    flow = next((vault / "06-runtime" / "flows").glob("*.md"))
    flow.write_text(flow.read_text(encoding="utf-8").split("```mermaid")[0], encoding="utf-8")
    code, out = run("check-slice", "Release one", "--vault", str(vault))
    assert code == 1 and "not fully checked" in out.splitlines()[0]
    _, out = run("check", "--vault", str(vault), "--today", TODAY)
    assert " W391 " not in out


def test_the_conventions_worked_example_is_in_the_grammar_the_checker_reads():
    """CONVENTIONS shows the flow-step grammar with a worked example; every line of it must read, so the two never drift."""
    from planner.flowcheck import mermaid
    text = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    section = text.split("\n## Flow check\n", 1)[1].split("\n## ", 1)[0]
    block = section.split("```mermaid\n", 1)[1].split("```", 1)[0].split("\n")
    problems = []
    tokens = mermaid.tokenize(block, 1, "CONVENTIONS.md", "example", problems)
    assert problems == [] and len(tokens) > 20
    tree_problems = []
    mermaid.parse_tree(readers.Flow("FLO-000", "example", "CONVENTIONS.md", tuple(tokens), (), True), tree_problems)
    assert tree_problems == []
    for line in [row.split("|")[1].strip().strip("`") for row in section.split("\n") if row.startswith("| `")]:
        if "..." in line:
            continue
        assert mermaid._token(line, 1) is not None, line


def test_a_slice_named_in_full_is_found_even_when_a_longer_name_starts_the_same():
    from planner.flowcheck.tables import Catalog
    from planner.slices import Slice
    catalog = Catalog(slices=[Slice("", "Release one", ("FLO-001",), "", 1, 0), Slice("", "Release one b", ("FLO-002",), "", 2, 1)])
    assert flowcheck.resolve_slice(catalog, "Release one") == ("Release one", ("FLO-001",), 0)
    with pytest.raises(flowcheck.SliceNotFound, match="more than one"):
        flowcheck.resolve_slice(catalog, "Release o")
