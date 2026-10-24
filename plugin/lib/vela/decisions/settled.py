"""What a session settled, said in the lead's words. Pure.

The Violation this exists to prevent is a Black Box at close: a lead who settled things in a session heard nothing of
it, and had to open a page to learn what was decided (Sensor). `vela decide` writes a `## Changes` row into `decided`
for every settle, so the record already holds the answer; this reads it.
"""
from vela import closegate, say

DECIDED = closegate.CONSENT_STATE


def settled_ids(record_text):
    """IDs with a `## Changes` row into `decided` in this record, first-seen order, once each."""
    found = []
    for row in closegate.change_rows(record_text):
        if row.after == DECIDED and row.item not in found:
            found.append(row.item)
    return found


def sentence(names):
    """'You settled two things in this session: Solution strategy and Job due.'; "" for none."""
    if not names:
        return ""
    count = "one thing" if len(names) == 1 else f"{say.count_words(len(names))} things"
    return f"You settled {count} in this session: {say.names_said(names)}."
