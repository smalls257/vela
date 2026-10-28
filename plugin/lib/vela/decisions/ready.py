"""Ready to decide: a yes the lead gave and didn't settle, kept so the next session opens with it.

The Violation this exists to prevent is a Silent Fallback of consent. A lead's plain yes to a pick used to be recorded
and then forgotten: the full3 run lost three decisions this way (D4, D7, D8), each with a yes on record and nothing
ever offering to settle it. Any session can settle now (`vela decide`), so the list holds what the lead said yes to and
chose not to settle yet (`vela decide --later`), or what a plain yes kept at `assumption` left behind. `vela session
brief` reads the lines across the records and lists every item still not decided, so the next session opens with them.

    ## Ready to decide

    - CON-003: the lead said yes in 2026-10-20-shape-booking (^c31)

The line is a pointer, not a decision: settling still takes the lead's own yes.

A group's yes in requirements, boundary or allocate can settle its lines at once (`vela decide <ID> --yes ^cM`).
Items the lead keeps not decided yet reach this list only through `vela decide --later` or a keep mark.

Two writers fill it. `vela decide --later` does when the lead declines the offer to settle. But the rule "run `vela
decide` on a plain yes" sat in the skills and was skipped (E81: ~20 yeses in two paid runs, none listed), so `vela
apply` of a `marks` file also does, with no model step: a keep at `assumption` whose capture is the lead's own plain
yes (`from_keep`). The mark already names the item and its state, so the yes is tied to the item mechanically.
"""
import re

from vela import privaterecord, say
from vela.decisions import consent, textedit

HEADING = privaterecord.READY_HEADING
LINE = privaterecord.READY_LINE
YES_OPENERS = ("yes", "yeah", "yep", "yup", "agreed", "absolutely", "correct", "go ahead", "that's right",
               "thats right", "sounds good", "do it")
KEPT_AT = "assumption"


def mark(record_text, ident, session, yes=None):
    """The record with `ident` listed under Ready to decide; unchanged when already there."""
    if ident in {m["id"] for m in entries(record_text)}:
        return record_text
    tail = f" ({yes})" if yes else ""
    return textedit.insert_block(record_text, HEADING, [f"- {ident}: the lead said yes in {session}{tail}"],
                                 before=("Captures", "Changes"))


def entries(record_text):
    """Every Ready-to-decide line in one record, as match groups."""
    found, inside = [], False
    for line in record_text.split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip() == HEADING
            continue
        match = LINE.match(line.strip()) if inside else None
        if match:
            found.append(match.groupdict())
    return found


def waiting(metas, is_decided):
    """[{id, session}] across the records' frontmatter (`ready:` in each stub), each item once, leaving out any
    `is_decided(id)` says is decided now. The session is the record's own id."""
    seen, found = set(), []
    for meta in metas:
        for ident in privaterecord.listed(meta, "ready"):
            if ident in seen or is_decided(ident):
                continue
            seen.add(ident)
            found.append({"id": ident, "session": str(meta.get("id", ""))})
    return found


def is_yes(words):
    """True when the lead's words open with a yes (START: a line is written after a yes; "ok", silence, "not sure" and
    "no" are not one). Opening, not containing: "Not sure, yes maybe" and "No, yes was last week" must not count."""
    said = re.sub(r"[^\w\s']", " ", words.lower()).split()
    text = " ".join(said)
    return any(text == w or text.startswith(w + " ") for w in YES_OPENERS)


def leads_own_yes(capture, lead):
    """True when `capture` is a plain yes the lead typed. `lead` is (handle, display names), or None when who the lead
    is isn't known, which lists nothing: a yes nobody can tie to the lead is no yes (consent.from_the_lead)."""
    if lead is None or not capture.is_person or capture.unverified:
        return False
    handle, names = lead
    said = consent.same_handle(capture.origin, handle) or capture.origin.strip().casefold() in {n.casefold() for n in names}
    return said and not capture.is_bare_non_yes and is_yes(capture.quote)


def from_keep(record_text, record_id, capture, ident, state, lead):
    """The record with `ident` listed as ready to decide when this keep is the lead's plain yes on an item left at
    `assumption`, in any session; else unchanged."""
    if state != KEPT_AT or not leads_own_yes(capture, lead):
        return record_text
    return mark(record_text, ident, record_id, f"^c{capture.n}")


def sentence(names):
    """What close tells the lead about their yeses still waiting to be settled, in their words (no IDs); "" when none."""
    if not names:
        return ""
    if len(names) == 1:
        return f"One item you said yes to is waiting to be settled: {names[0]}."
    return f"{say.count_words(len(names), capital=True)} items you said yes to are waiting to be settled: {say.names_said(names)}."
