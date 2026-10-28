"""The vocabulary the page checks read: which bullets belong to an item's history."""
from vela import schema


def test_decided_with_open_is_a_history_label():
    assert schema.DECIDED_WITH_OPEN_LABEL == "Decided with open"
    assert schema.DECIDED_WITH_OPEN_LABEL in schema.HISTORY_LABELS
