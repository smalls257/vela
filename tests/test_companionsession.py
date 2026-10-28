"""The companion's session panel, read from a session record's Changes rows."""
from vela import closegate, companionsession

RECORD = ("## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"
          "| UNK-009 | open | decided | [[r#^c11]] |\n")


def test_an_item_decided_with_a_marked_row_is_listed():
    got = companionsession.decided_rows(closegate.change_rows(RECORD), {})
    assert [d["id"] for d in got] == ["UNK-009"] and got[0]["capture"] == 11
