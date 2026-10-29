"""Which `**Decision:**` receipt on a page counts as the lead's yes on this branch. Pure.

The Violation this exists to prevent is a Silent Fallback in the record: a hand-set `decided` with a receipt someone
wrote by hand looks exactly like a settle. So a receipt counts only when it names a person (Claude's summary never
does), was written since the branch point (an older one is a past decision), and cites a session that gave the yes on
this branch: this one, any part, or an earlier one opened here that closed and isn't merged yet. That earlier session's
close already asked for its yes; asking again at the next close re-asked every decision on the branch (fix ledger
E156). A receipt citing a session the plan doesn't have, or one already merged at the branch point, is not a yes here.

`receipts` owns the line's grammar; this owns what a parsed line is worth. `vault` and `before` are model.Vault
values, `before` the vault at the branch point or None in a reader copy (no git, so nothing is old).
"""


def decision_bullets(vault, item):
    """[(page, bullet)] for the item's (or the page's) `**Decision:**` line."""
    found = vault.item(item)
    if found is not None:
        return _item_decisions(found)
    pages = vault.by_id.get(item) or []
    return _page_decisions(pages[0]) if pages else []


def _item_decisions(item):
    """An item's Decision bullets, a repeated one included, in page order."""
    every = [item.facts.get("Decision")] + [b for kept, b in item.repeats if b.label == "Decision"]
    return [(item.page, b) for b in sorted(filter(None, every), key=lambda b: b.line)]


def _page_decisions(page):
    """A page's own Decision bullets: not an item's, not a generated block's."""
    return [(page, b) for b in page.bullets if b.label == "Decision" and not b.item and not b.generated]


def newest_receipt(vault, item_id):
    """(bullet, receipt) for the item's or page's newest `**Decision:**` bullet, or (None, None). A reopened item keeps
    its old bullet, so the newest one is the decision that counts."""
    from vela import receipts  # here, not at the top: receipts imports questions, which leads back to closegate
    for _, bullet in reversed(decision_bullets(vault, item_id)):
        found = receipts.parse_decision(bullet.value)
        if found is not None:
            return bullet, found
    return None, None


def receipt_of(vault, item_id):
    """The parsed newest `**Decision:**` bullet of an item or page, or None."""
    return newest_receipt(vault, item_id)[1]


def branch_yes(vault, before, item_id, record_name):
    """(bullet, receipt) when the item's newest receipt is the lead's yes on this branch, else None."""
    bullet, receipt = newest_receipt(vault, item_id)
    if not (names_a_person(receipt) and is_new_since(vault, before, item_id, bullet)):
        return None
    return (bullet, receipt) if receipt.record == record_name or opened_on_this_branch(vault, before, receipt.record) else None


def names_a_person(receipt):
    """A receipt is a yes when it names a person; a bare link names no one, and Claude's own summary is never one."""
    if receipt is None or not receipt.who.lstrip("@"):  # a bare `[[record]]` link names no one
        return False
    return not receipt.who.lstrip("@").lower().startswith("claude")


def is_new_since(vault, before, item_id, bullet):
    """Whether `bullet` was written after the branch point."""
    if before is None:
        return True
    page = next((pg for pg, b in decision_bullets(vault, item_id) if b is bullet), None)
    old = before.page(page.name) if page is not None else None
    return old is None or ("Decision", bullet.value) not in {(b.label, b.value) for b in old.bullets}


def opened_on_this_branch(vault, before, record):
    """Whether `record` is a session the plan has that wasn't there at the branch point."""
    return bool(record) and vault.page(record) is not None and (before is None or before.page(record) is None)
