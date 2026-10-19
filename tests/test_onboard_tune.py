"""The lead's onboarding page: parsed into a tuning, every mistake named, nothing dropped quietly.

The Violation these guard against is the Silent Fallback: "Hide: Contrcts" that hides nothing while the lead believes the
page works. So every name is checked against the fixed vocabulary and every mistake comes back with the fix.
"""
import re

from conftest import REPO
from vela import onboardtune, say

CONVENTIONS = (REPO / "plugin" / "vault" / "CONVENTIONS.md").read_text(encoding="utf-8")


EXAMPLE = """# Onboarding

Words of the lead's own, outside any role, are left alone.

## Engineering
- Stress: Contracts, Journeys
- Play down: Open questions
- Hide: Apps
- Note: Read the contract for the pilot first.

## Managers
- Hide: Dates
"""


def test_the_page_reads_into_a_tuning_per_role():
    tuning = onboardtune.parse(EXAMPLE)
    assert tuning.problems == ()
    assert tuning.for_audience("eng") == onboardtune.RoleTuning(("contracts", "journeys"), ("open-questions",), ("apps",), "Read the contract for the pilot first.")
    assert tuning.for_audience("mgr").hide == ("dates",) and tuning.for_audience("exec") is None


def test_the_example_in_conventions_is_the_example_the_parser_reads():
    block = re.search(r"```markdown\n(## Engineering\n.*?)```", CONVENTIONS, re.S).group(1)
    tuning = onboardtune.parse(block)
    assert tuning.problems == () and tuning.for_audience("eng").hide == ("handoff",)


def problems(text):
    return onboardtune.parse(text).problems


def test_a_typo_is_a_problem_with_the_name_it_was_near_never_a_dropped_line():
    found = problems("## Engineering\n- Hide: Contrcts\n")
    assert len(found) == 1 and found[0].line == 2 and "'Contrcts' is not a module" in found[0].text and "Did you mean 'Contracts'?" in found[0].fix
    assert onboardtune.parse("## Engineering\n- Hide: Contrcts\n").for_audience("eng").hide == ()


def test_each_mistake_is_named_and_the_rest_of_the_page_still_applies():
    text = ("## Engineering\n- Stress: Goal\n- Hide: Risks\n- Stress: Contracts\n- Note: first\n- Note: second\n"
            "## Exec\n- Note: see UNK-004\n## Sales\n- Hide: Dates\n## Product\n- Hide: Dates\n- Play down: Dates\n")
    said = [p.text for p in problems(text)]
    assert any("'Goal' is one of the five parts" in t for t in said)
    assert any("'Risks' is not one of the Engineering modules" in t for t in said)
    assert any("a second note" in t for t in said)
    assert any("holds a code" in t for t in said)
    assert any("'Sales' is not a role" in t for t in said)
    assert any("'Dates' is listed twice for Product" in t for t in said)
    tuning = onboardtune.parse(text)
    assert tuning.for_audience("eng").stress == ("contracts",) and tuning.for_audience("eng").note == "first"
    assert tuning.for_audience("product").hide == ("dates",)


def test_bullets_in_a_fence_or_outside_a_role_section_are_the_leads_own_words():
    text = "- Hide: Dates\n\n```\n## Engineering\n- Hide: Apps\n```\n\n## Exec\n- Owner: someone\n"
    tuning = onboardtune.parse(text)
    assert tuning.problems == () and tuning.for_audience("exec") == onboardtune.RoleTuning()


def test_problems_are_said_plainly_with_no_command_or_file_name():
    for line in onboardtune.problems_text(onboardtune.parse("## Sales\n## Engineering\n- Hide: Contrcts\n")):
        assert line.startswith("The onboarding page, line ") and not say.leak_in(line), line




def test_a_page_saved_on_windows_with_a_byte_order_mark_and_crlf_reads_the_same_as_any_other():
    plain = onboardtune.parse(EXAMPLE)
    windows = onboardtune.parse("\ufeff" + EXAMPLE.replace("\n", "\r\n"))
    assert windows == plain and windows.problems == () and windows.for_audience("eng").note == "Read the contract for the pilot first."


def test_a_role_heading_is_read_in_any_letter_case_and_with_trailing_hashes():
    tuning = onboardtune.parse("## engineering ##\n- hide: apps\n## QA\n- STRESS: Contracts\n")
    assert tuning.problems == () and tuning.for_audience("eng").hide == ("apps",) and tuning.for_audience("qa").stress == ("contracts",)


def test_a_second_section_for_a_role_is_reported_and_the_first_stands():
    tuning = onboardtune.parse("## Engineering\n- Hide: Apps\n## engineering\n- Hide: Dates\n- Note: later\n")
    assert [(p.line, p.text) for p in tuning.problems] == [(3, "Engineering is listed twice")]
    assert tuning.for_audience("eng") == onboardtune.RoleTuning((), (), ("apps",), "")


def test_a_line_that_names_no_module_is_a_problem_not_a_quiet_nothing():
    for line in ("- Hide:", "- Stress: ,"):
        found = problems("## Engineering\n" + line + "\n")
        assert len(found) == 1 and found[0].line == 2 and "names no module" in found[0].text and found[0].fix
