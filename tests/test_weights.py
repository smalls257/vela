"""Every finding code has one weight; only reading polish goes quiet; no error is ever quiet or left to close."""
import pytest

from vela import schema

POLISH = ["W353", "W360", "W361", "W362", "W363", "W364", "W365", "W366", "W367", "W368", "W369",
          "W371", "W372", "W373"]


def test_every_code_has_exactly_one_weight():
    assert set(schema.WEIGHT) == set(schema.CODES)
    for code, weight in schema.WEIGHT.items():
        assert weight in schema.WEIGHTS or (weight.startswith("scale:") and weight[6:] in schema.NEEDS), code


def test_no_error_is_quiet_or_fixed_by_close():
    assert [c for c, w in schema.WEIGHT.items() if c.startswith("E") and w != "decision"] == []


def test_the_quiet_set_is_the_reading_load():
    assert sorted(c for c, w in schema.WEIGHT.items() if w == "polish") == POLISH


def test_auto_and_scale_are_the_named_few():
    assert sorted(c for c, w in schema.WEIGHT.items() if w == "auto") == ["W326", "W358", "W402", "W408"]
    assert {c: w for c, w in schema.WEIGHT.items() if w.startswith("scale:")} == {"W352": "scale:DOMAIN_FIELD"}


@pytest.mark.parametrize("code", ["W370", "W720", "W327", "W604", "W388", "E361", "W345", "W705", "W389", "W334",
                                  "W380", "W385", "W390", "W391", "W324", "W807"])
def test_what_can_change_a_decision_is_said(code):
    assert schema.WEIGHT[code] == "decision"
