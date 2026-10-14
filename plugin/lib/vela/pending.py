"""Decisions a reader made that the owner has not yet reviewed. Pure: no disk, clock or network.

A reader has no git access, so a decision or override they record is a proposal that looks settled.
The Silent Fallback to prevent is that look: a `decided` page nobody with authority has seen. So the
item stays `decided` and carries a bullet beside its Override and Decided by:

    - **Pending approval:** @handle, YYYY-MM-DD

`vela check` lists every such item in one warning, never an error, so a reader's copy stays green
and an owner's main shows a review that skipped one. A malformed bullet is E322, because a typo must
not leave a reader's decision looking like an owner's.
"""
import datetime
import re
from dataclasses import dataclass

from vela import schema
from vela.model import Finding

PENDING_RE = re.compile(rf'^(?P<by>{schema.HANDLE}), (?P<date>\d{{4}}-\d{{2}}-\d{{2}})$')
GRAMMAR = "@handle, YYYY-MM-DD"
WARNING = "W327"


@dataclass(frozen=True)
class Pending:
    path: str
    line: int
    item: str  # the item ID, or "" for page level
    subject: str  # what to call it: the item ID, else the page's ID, else its file name
    by: str  # "" when malformed
    date: str
    problem: str  # "" when well formed

    def as_dict(self):
        if self.problem:
            return {"path": self.path, "line": self.line, "item": self.item, "malformed": True, "problem": self.problem}
        return {"path": self.path, "line": self.line, "item": self.item, "subject": self.subject,
                "by": self.by, "date": self.date}


def _is_date(value):
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _problem(value):
    if not re.match(schema.HANDLE, value):
        return "names no @handle first"
    match = PENDING_RE.match(value)
    if not match:
        return "has no ', YYYY-MM-DD' date after the handle"
    if not _is_date(match["date"]):
        return f"has date {match['date']}, which is not a real date"
    return ""


def parse_pending(page, bullet):
    value = bullet.value.strip()
    subject = bullet.item or page.id or page.name
    problem = _problem(value)
    if problem:
        return Pending(page.path, bullet.line, bullet.item, subject, "", "", problem)
    match = PENDING_RE.match(value)
    return Pending(page.path, bullet.line, bullet.item, subject, match["by"], match["date"], "")


def all_bullets(vault):
    """Every Pending approval bullet outside generated blocks, in page then line order, well formed or not."""
    return [parse_pending(page, bullet) for page in vault.pages for bullet in page.bullets
            if bullet.label == schema.PENDING_LABEL and not bullet.generated]


def items(vault):
    """The well-formed ones: what the explorer, propose and review read."""
    return [p for p in all_bullets(vault) if not p.problem]


def pending_for(page, item_id=""):
    """The well-formed marker on one item (or on the page when item_id is ""), or None."""
    for bullet in page.bullets:
        if bullet.label == schema.PENDING_LABEL and bullet.item == item_id and not bullet.generated:
            found = parse_pending(page, bullet)
            if not found.problem:
                return found
    return None


def findings(vault):
    found = all_bullets(vault)
    out = [Finding(p.path, p.line, "E322", f"**Pending approval:** on {p.subject} {p.problem}, so it marks nothing for review.",
                   f"Write - **Pending approval:** {GRAMMAR}.") for p in found if p.problem]
    good = [p for p in found if not p.problem]
    if good:
        first = good[0]
        listing = "; ".join(f"{p.subject} ({p.by}, {p.date})" for p in good)
        noun = "item" if len(good) == 1 else "items"
        out.append(Finding(first.path, first.line, WARNING, f"{len(good)} {noun} pending approval: {listing}.",
                           "The owner reviews each: accept (remove the bullet, record **Decided by:** and a credit), "
                           "reject (revert it), or edit it. Nothing here blocks a merge."))
    return out
