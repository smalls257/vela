"""Onboarding speaks the plan's voice: the checks every page and read-back already pass, held to what onboarding says.

Names not codes, answer first, about four things at a time, natural negatives, American spelling, and the kept terms
defined on first use (the page's own selftest holds the last one to each role's path; here the data is held to it).
The Violation these guard against is a Leaky Narrative: text written once in code and never read by the checks that
read every other sentence the lead hears.
"""
import re

import pytest

from conftest import REPO
from test_onboard_modules import VAULTS, data, words
from vela import onboardmodules, say, spelling, terms

PLUGIN = REPO / "plugin"
# What this feature writes: its code, its page's script, its skill and the conventions section it adds.
SOURCES = [PLUGIN / "lib" / "vela" / name for name in ("onboarding.py", "onboardmodules.py", "onboardtune.py", "onboardpath.py")] + [
    PLUGIN / "lib" / "vela" / "commands" / "onboard.py", PLUGIN / "lib" / "vela" / "explorer" / "onboard_data.py",
    PLUGIN / "lib" / "vela" / "explorer" / "assets" / "js" / "onboard.js", PLUGIN / "skills" / "onboard" / "SKILL.md"]
FORCED_NEGATIVE = re.compile(r"\b(?:sends|shows|holds|lists|says|has|makes|gives|needs|names|carries) nothing\b", re.I)


def conventions_section():
    text = (PLUGIN / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    return text.split("\n## Onboarding\n", 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_what_this_feature_writes_is_in_american_spelling(path):
    assert not spelling.british_words(path.read_text(encoding="utf-8")), (path.name, spelling.british_words(path.read_text(encoding="utf-8")))


def test_the_conventions_section_is_in_american_spelling_and_shows_no_id_to_a_lead():
    section = conventions_section()
    assert not spelling.british_words(section)
    assert say.leak_in(re.sub(r"`[^`]*`", "", re.sub(r"```.*?```", "", section, flags=re.S))) is None


@pytest.mark.parametrize("name", sorted(VAULTS))
def test_a_negative_is_said_the_natural_way_never_as_a_verb_that_sends_nothing(name):
    for module in onboardmodules.build_all(data(name)).values():
        assert not FORCED_NEGATIVE.search(words(module)), (name, module["id"], words(module)[:200])
    assert not FORCED_NEGATIVE.search((PLUGIN / "skills" / "onboard" / "SKILL.md").read_text(encoding="utf-8"))
    assert not FORCED_NEGATIVE.search(conventions_section())


@pytest.mark.parametrize("name", sorted(VAULTS))
def test_the_answer_comes_first_as_one_short_sentence_and_the_gist_depth_shows_about_four_things(name):
    for module in onboardmodules.build_all(data(name)).values():
        gist = module["gist"]
        assert len(gist.split()) <= 40 and gist.endswith((".", "!", "?", "…")), (name, module["id"], gist)
    assert onboardmodules.DEPTHS["gist"]["items"] <= 4 and onboardmodules.DEPTHS["normal"]["items"] <= 6


def test_the_commands_lines_for_the_lead_stop_at_four_then_offer_the_rest():
    assert say.LEAD_LIMIT == 4


@pytest.mark.parametrize("name", sorted(VAULTS))
def test_the_kept_terms_a_module_uses_are_the_three_words_vela_keeps_and_are_defined(name):
    modules = onboardmodules.build_all(data(name))
    for module in modules.values():
        for term in module["terms"]:
            assert term in terms.TERMS and terms.define(term)
        if re.search(r"\bslices?\b", words(module), re.I) and module["items"]:
            assert "slice" in module["terms"] or module["id"] in ("goal", "standing", "people", "fit", "needs-you", "dates", "journeys", "capabilities", "progress", "handoff"), (name, module["id"])


def test_a_module_that_names_a_grill_never_appears_because_the_grill_is_not_part_of_the_path():
    for name in VAULTS:
        for module in onboardmodules.build_all(data(name)).values():
            assert "grill" not in module["terms"]
