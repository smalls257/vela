"""The words a reader sees for the vault's own state, stage and cell values, in generated page text.

The vault keeps short machine values (`assumption`, `boundaries`, `unexamined`) because the checker and the skills
type and compare them. A product owner reading a generated table does not know them, so `planner render` shows these
words instead (wording audit, 2026-10-14). One table, so every generated block says the same thing. A value with no
entry is shown as it is: the checker reports a bad value elsewhere, and hiding it here would make it look settled.
"""

STATE_WORDS = {
    "inkling": "early idea",
    "assumption": "assumed",
    "fact": "confirmed",
    "decided": "decided",
    "draft": "draft",
    "open": "open",
    "resolved": "answered",
    "mitigated": "mitigated",
    "accepted": "accepted",
    "closed": "closed",
    "confirmed": "confirmed",
    "unchanged": "unchanged",
    "retired": "retired",
}

# `stage` means "in this stage now" (CONVENTIONS, "Areas and stages"); each word says where the app has got to.
STAGE_WORDS = {
    "baseline": "named in scope",
    "target": "researched",
    "boundaries": "boundaries drawn",
    "contracts": "agreeing contracts",
    "handoff": "ready to hand over",
    "epics": "writing epics",
}

CELL_WORDS = {
    "addressed": "covered",
    "unchanged": "unchanged",
    "n/a": "doesn't apply",
    "unknown": "waiting on an open question",
    "unexamined": "not looked at yet",
}


def state_word(value):
    return STATE_WORDS.get(str(value).strip(), str(value).strip())


def stage_word(value):
    return STAGE_WORDS.get(str(value).strip(), str(value).strip())


def cell_word(value):
    text = str(value).strip()
    if text.startswith("unexamined ("):  # "unexamined (no row)": the concern page has no line for this app at all
        return CELL_WORDS["unexamined"] + " (no line for this app)"
    return CELL_WORDS.get(text, text)
