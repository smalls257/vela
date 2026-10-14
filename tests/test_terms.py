"""The kept working words (slice, tracer, grill) have one definition each, and the dashboard gets the same text."""
import pytest

from planner import terms


def test_each_kept_word_has_a_one_line_definition():
    assert set(terms.TERMS) == {"slice", "tracer", "grill"}
    for word, text in terms.TERMS.items():
        assert "\n" not in text and text.endswith(".") and len(text) < 200, word


def test_an_unknown_word_raises_rather_than_showing_a_blank():
    with pytest.raises(KeyError):
        terms.define("lamp")


def test_core_js_reads_definitions_from_the_data_and_throws_on_a_missing_one():
    from pathlib import Path
    core = (Path(terms.__file__).parent / "explorer/assets/js/core.js").read_text()
    assert "function termEl(" in core and "D.terms" in core and "throw new Error" in core
