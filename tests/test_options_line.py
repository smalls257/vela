"""The one writer of the Options considered line: its three forms, read back by the dashboard's parser."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "plugin" / "lib"))

from vela.decisions import options_line  # noqa: E402
from vela.explorer import asks_data  # noqa: E402


def test_a_reason_with_a_semicolon_does_not_read_back_as_another_option():
    line = options_line.picked("Rent", [("Buy", "too dear; and slow"), ("Lease", options_line.DECLINED_REASON)])
    picked, rejected = asks_data.parse_options(line.split("** ", 1)[1])
    assert picked["label"] == "Rent"
    assert [r["label"] for r in rejected] == ["Buy", "Lease"]
    assert rejected[0]["reason"] == "too dear, and slow"


def test_only_this_one_carries_the_words_only_when_given():
    assert options_line.only_this_one("[[S]] c14", "just the one") == \
        "- **Options considered:** only this one: just the one ([[S]] c14)"
    assert options_line.only_this_one("[[S]] c14") == "- **Options considered:** only this one ([[S]] c14)"
