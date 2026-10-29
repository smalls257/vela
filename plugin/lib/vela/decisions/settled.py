"""What a session settled, said in the lead's words. Pure.

The Violation this exists to prevent is a Black Box at close: a lead who settled things in a session heard nothing of
it, and had to open a page to learn what was decided (Sensor). `vela decide` writes a `## Changes` row into `decided`
for every settle, so the record already holds the answer; a settle whose row is in another part's notes (another
machine) is still on the page as a Decision receipt naming this session, so that is read too.
"""
from vela import closegate, receiptyes, say

DECIDED = closegate.CONSENT_STATE


def settled_ids(record_text, vault=None, record_id=""):
    """IDs this session settled, once each, first-seen order: the `## Changes` rows into `decided` in this record,
    then every decided item or page whose Decision receipt names `record_id` (a settle recorded in other notes)."""
    found = []
    for row in closegate.change_rows(record_text):
        if row.after == DECIDED and row.item not in found:
            found.append(row.item)
    if vault is not None and record_id:
        for item, state in sorted(closegate.states(vault).items()):
            receipt = receiptyes.receipt_of(vault, item) if state == DECIDED else None
            if receipt is not None and receipt.record == record_id and item not in found:
                found.append(item)
    return found


def sentence(names):
    """'You settled two things in this session: Solution strategy and Job due.'; "" for none."""
    if not names:
        return ""
    count = "one thing" if len(names) == 1 else f"{say.count_words(len(names))} things"
    return f"You settled {count} in this session: {say.names_said(names)}."
