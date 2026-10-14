"""The lead-side tracer guidance (S52, step 2): present in each skill, never a gate, the example in the plan's format, and no codes read to the lead.

    python3 -m pytest tests/test_tracer_skills.py
"""

from conftest import REPO


def test_the_tracer_is_the_slice_with_no_after():
    assert "The tracer is the one slice with no After, usually SLC-001" in (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")


def test_the_tracer_has_one_definition():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert conventions.count("a thin path through every app and contract it needs, built first and kept") == 1
