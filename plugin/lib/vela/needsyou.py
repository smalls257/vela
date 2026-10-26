"""What needs a person, most urgent first: the data behind the explorer's Needs you block. Pure: no disk, clock or network.

The Violation this exists to prevent is a Leaky Narrative on the page. If the script had to know that an open question
is late when its ask-by date is before today, that a grill is the viewer's when they are its first-named owner, or that
an app counts as "just handed over" for two weeks, each rule would live where no vault test reaches it, and the page,
the badge and the sidebar would each carry their own copy. They are decided here, once. The page only asks who is
viewing, keeps the lines that are for that person, and draws them.

Who is viewing is the page's (it is a browser setting); this module therefore lists every line with the handles it is
for, in the order a person should meet them, and the page filters without reordering. Four kinds of line:

- question: an open question the person was asked, with its ask-by date (late, soon, later or undated)
- proposal: a decision a reader made, or one made on someone's behalf, that waits on the owner's yes
- handed: an app recently handed to the person
- grill: an item the person could settle or grill that is ready to decide, or that the lead already said yes to

A question the person owns but someone else was asked is not a line (it does not need them), but its date is the
person's next date, so it is listed under `dates` for the empty state to name.
"""
import datetime
import re

from vela import schema

SOON_DAYS = 7  # a question due within a week is "soon": long enough to plan around, short enough to still be urgent
HANDED_DAYS = 14  # an app handed over within two weeks is "just handed"; after that it is just theirs
READY_GROUPS = ("said-yes", "ready")  # a grill one answer away from ready is not yet the person's to run
ASKED_BY_LATE, ASKED_BY_SOON, ASKED_BY_LATER, ASKED_BY_NONE = "late", "soon", "later", "none"

# The order a person should meet them: overdue answers, then those due soon, then other people waiting on their yes,
# then what was just handed over, then grills that are ready, then questions with a later or no date.
TIERS = {"late": 0, "soon": 1, "proposal": 2, "handed": 3, "grill": 4, "later": 5, "none": 6}
HANDLE_RE = re.compile(schema.HANDLE)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _day(text):
    """The date a string is, or None. Malformed or impossible dates are not dates."""
    if not isinstance(text, str) or not DATE_RE.fullmatch(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _handles(*values):
    """Every handle named in the values, lower-cased and unique, in order. A name that is not a handle names nobody."""
    out = []
    for value in values:
        for found in HANDLE_RE.findall(str(value or "")):
            low = found.lower()
            if low not in out:
                out.append(low)
    return out


def question_standing(ask_by, today):
    """(standing, days until the date): late, soon, later or none. `days` is None without a date."""
    due, now = _day(ask_by), _day(today)
    if due is None or now is None:
        return ASKED_BY_NONE, None
    days = (due - now).days
    if days < 0:
        return ASKED_BY_LATE, days
    return (ASKED_BY_SOON if days <= SOON_DAYS else ASKED_BY_LATER), days


def question_lines(asks, today):
    """One line per open question, for the people it was asked of. `words` is the name the plan gives who is asked, so a
    page that knows only a role (no person) can still match "the product owner"."""
    out = []
    for ask in asks:
        if ask.get("state") != "open":
            continue
        who = ask.get("ask") or {}
        standing, days = question_standing(ask.get("askBy"), today)
        out.append({"kind": "question", "key": ask["id"], "for": _handles(who.get("key")), "words": str(who.get("name") or ""),
                    "date": ask.get("askBy") or "", "standing": standing, "days": days, "tier": TIERS[standing]})
    return out


def date_rows(asks, today):
    """The dates a person is waiting on: open questions they own with an answer due today or later, each with who was asked.
    The owner is the first handle in the Owner line; a later one in its parenthesis ("asking @x") is who to ask, not who owns it."""
    now = _day(today)
    out = []
    for ask in asks:
        due = _day(ask.get("askBy"))
        if ask.get("state") != "open" or due is None or now is None or due < now:
            continue
        who = ask.get("ask") or {}
        out.append({"key": ask["id"], "for": _handles(ask.get("ownerRaw"))[:1], "words": str(ask.get("ownerRaw") or ""),
                    "date": ask["askBy"], "askedName": str(who.get("name") or ""), "askedKey": str(who.get("key") or "")})
    return sorted(out, key=lambda r: (r["date"], r["key"]))


def proposal_lines(proposals):
    """Decisions waiting on an owner's yes. Each is {"key", "by", "date", "owners"}; a proposal with no owner is nobody's to answer."""
    out = []
    for p in proposals:
        owners = _handles(*p.get("owners", ()))
        if owners:
            out.append({"kind": "proposal", "key": p["key"], "for": owners, "words": "", "by": p.get("by") or "", "date": p.get("date") or "",
                        "standing": "waiting", "days": None, "tier": TIERS["proposal"]})
    return sorted(out, key=lambda r: (r["date"] or "9999-99-99", r["key"]))


def parse_handed_off(text):
    """(who, "YYYY-MM-DD") from an app's handed_off field ("<name or @handle>, <date>"), or None when it is not that."""
    if not schema.HANDED_OFF_RE.match(str(text or "")):
        return None
    who, _, date = str(text).rpartition(", ")
    return (who.strip(), date) if who.strip() and _day(date) else None


def handed_lines(handed, today):
    """Apps handed to a person within HANDED_DAYS, newest first. Each is {"key", "handed_off"}; a handoff in the future is not yet theirs.
    The field is written as a handle or as a name ("Booking senior"). A name names nobody the build can resolve, so it travels
    as `named` for the page to match against the people it knows by name."""
    now = _day(today)
    out = []
    for app in handed:
        found = parse_handed_off(app.get("handed_off"))
        if found is None or now is None:
            continue
        who, date = found
        age = (now - _day(date)).days
        if 0 <= age <= HANDED_DAYS:
            handles = _handles(who)
            out.append({"kind": "handed", "key": app["key"], "for": handles, "words": "", "named": "" if handles else who.casefold(), "date": date,
                        "standing": "new", "days": -age, "tier": TIERS["handed"]})
    return sorted(out, key=lambda r: (r["date"], r["key"]), reverse=True)


def grill_lines(grills):
    """Grills ready to decide, for their owners. Each row is a grills_data row: {"id", "key", "group", "owner"}."""
    out = []
    for g in grills:
        if g.get("group") in READY_GROUPS and g.get("owner"):
            out.append({"kind": "grill", "key": g.get("key") or "grill:" + g["id"], "grill": g["id"], "for": _handles(*g["owner"]), "words": "",
                        "date": "", "standing": g["group"], "days": None, "tier": TIERS["grill"]})
    return out


def extract(asks, grills, proposals, handed, today):
    """{"lines": [...], "dates": [...]}: every line for every person, most urgent first (tier, then date, then key).

    Lines keep their tier and the order within it, so the page filters to one person and never re-sorts."""
    lines = question_lines(asks, today) + proposal_lines(proposals) + handed_lines(handed, today) + grill_lines(grills)
    order = {id(line): i for i, line in enumerate(lines)}
    lines.sort(key=lambda line: (line["tier"], line["date"] if line["kind"] == "question" and line["date"] else "9999-99-99", order[id(line)]))
    return {"lines": lines, "dates": date_rows(asks, today)}
