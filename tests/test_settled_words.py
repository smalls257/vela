"""What the lead hears about settling: the close line, the waiting list, the PR title, the next step."""
from vela import prbody, progress, terms
from vela.decisions import ready, settled

RECORD = ("## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"
          "| solution-strategy | inkling | decided | [[r#^c18]] |\n| CON-003 | assumption | decided | [[r#^c46]] |\n"
          "| CON-003 | assumption | decided | [[r#^c46]] |\n| UNK-001 | open | resolved | [[r#^c50]] |\n")


def test_close_says_what_was_settled_in_words():
    assert settled.settled_ids(RECORD) == ["solution-strategy", "CON-003"]
    assert settled.sentence(["Solution strategy", "Job due"]) == ("You settled two things in this session: Solution "
                                                                   "strategy and Job due.")
    assert settled.sentence(["Job due"]) == "You settled one thing in this session: Job due."
    assert settled.sentence([]) == ""


def test_the_waiting_list_says_settle_not_a_short_grill():
    assert ready.sentence(["Stock level"]) == "One item you said yes to is waiting to be settled: Stock level."
    assert "grill" not in ready.sentence(["Stock level", "Job due"])


def test_the_pr_title_counts_the_decisions_a_session_settled():
    assert prbody.title("2026-10-26", ["shape"], "Options: booking jobs", decided=1) == \
        "2026-10-26 Options and one decision: booking jobs"
    assert prbody.title("2026-10-26", ["shape"], "Options: booking jobs", decided=3) == \
        "2026-10-26 Options and three decisions: booking jobs"
    assert prbody.title("2026-10-26", ["shape"], "Options: booking jobs") == "2026-10-26 Options: booking jobs"
    assert prbody.title("2026-10-26", ["grill"], "Decisions: jobs", decided=3) == "2026-10-26 Decisions: jobs"


def test_a_grill_is_for_testing():
    assert terms.define("grill") == ("A grill is a working session where Vela tests part of the plan with hard "
                                     "questions, one at a time, until it holds up.")
