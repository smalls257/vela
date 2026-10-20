"""Ready to decide: a yes the lead gave in a session that cannot decide, kept so the next grill opens with it.

The Violation this exists to prevent is a Silent Fallback of consent. Shape, boundary, releases and the other
building sessions save a picked option at `assumption` (MODES: only a grill sets `decided`), so a lead's plain yes
there was recorded and then forgotten: the full3 run lost three decisions this way (D4, D7, D8), each with a yes on
record and no grill ever offered. The rule is in code, not in each skill: `vela decide` run in such a session
refuses, tells the model to offer the lead a short grill on that item, and writes one line under `## Ready to decide`
in the session record. `vela session brief` reads those lines across the records and lists every item still not
decided, so the grill that follows starts with them.

    ## Ready to decide

    - CON-003: the lead said yes in 2026-10-20-shape-booking (^c31)

The line is a pointer, not a decision: the grill still reads the final wording back and gets its own yes.

Two writers fill it. `vela decide` does when the model runs it. But the rule "run `vela decide` on a plain yes" sat in
the skills and was skipped (E81: ~20 yeses in two paid runs, none listed), so `vela apply` of a `marks` file also
does, with no model step: a keep at `assumption` whose capture is the lead's own plain yes (`from_keep`). The mark
already names the item and its state, so the yes is tied to the item mechanically.
"""
import re

from vela import say
from vela.decisions import consent, textedit

HEADING = "Ready to decide"
CANNOT_DECIDE = frozenset({"dump", "discover", "shape", "boundary", "requirements", "allocate", "releases"})
LINE = re.compile(r"^- (?P<id>\S+): the lead said yes in (?P<session>\S+)(?: \((?P<yes>\^c\d+)\))?\s*$")
YES_OPENERS = ("yes", "yeah", "yep", "yup", "agreed", "absolutely", "correct", "go ahead", "that's right",
               "thats right", "sounds good", "do it")
KEPT_AT = "assumption"
MODES = re.compile(r"^modes:\s*\[(?P<modes>[^\]]*)\]", re.M)


def modes_of(record_text):
    found = MODES.search(record_text)
    return [m.strip() for m in found["modes"].split(",") if m.strip()] if found else []


def can_decide(record_text):
    """False when every mode of the session is one that never sets `decided`; a session with no modes, or any mode
    outside that list (grill, answer, epics inside a grill part), is left to the gate."""
    modes = modes_of(record_text)
    return not modes or any(m not in CANNOT_DECIDE for m in modes)


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


def waiting(record_texts, is_decided):
    """[{id, session}] across records, each item once, leaving out any `is_decided(id)` says is decided now."""
    seen, found = set(), []
    for text in record_texts:
        for entry in entries(text):
            if entry["id"] in seen or is_decided(entry["id"]):
                continue
            seen.add(entry["id"])
            found.append({"id": entry["id"], "session": entry["session"]})
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
    `assumption` in a session that can't decide; else unchanged."""
    if state != KEPT_AT or can_decide(record_text) or not leads_own_yes(capture, lead):
        return record_text
    return mark(record_text, ident, record_id, f"^c{capture.n}")


def sentence(names):
    """What close tells the lead about their yeses still waiting for a grill, in their words (no IDs); "" when none."""
    if not names:
        return ""
    if len(names) == 1:
        return f"One item you said yes to is ready for a short grill: {names[0]}."
    return f"{say.count_words(len(names), capital=True)} items you said yes to are ready for a short grill: {say.names_said(names)}."
