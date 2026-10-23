"""The grammar of a receipt (`- **Decision:**`) and a Dissent, and the one way a handle is written. Pure.

The Violation this exists to prevent is a Distributed Monolith in the line grammar: the writer, the split and the
check each re-spelled `[[id]] c07, @maria: "words"`, so changing one spelling meant editing every reader. Every writer
and reader of those two lines goes through here, and every handle goes through `handle_ref`.

A receipt names the session and the capture the yes came from, then who said it, then (only with that person's own
yes to being quoted) their words:

    [[2026-10-22-booking-api]] c07, @maria: "Yes, one booking API for the web and the kiosks."
    [[2026-10-22-booking-api]] c09, @cto-ana
    [[2026-10-22-booking-api]] c09, @maria, as SRC-04 states: "..."
    [[2026-10-22-booking-api]]                       (an override: the bare link)

A Dissent is `@raj, 2026-10-22`, with `: "words"` and `(see [[record]])` only with Raj's own yes. A Dissent written
before the quotes were required (`@raj, 2026-01-10: too slow`) still parses.
"""
import re
from dataclasses import dataclass

from vela import privaterecord
from vela.decisions import textedit

_HANDLE = r"@?[A-Za-z0-9][\w./-]*"
_DECISION = re.compile(
    r"^\[\[(?P<record>[^\]#|]+)\]\]"
    r"(?: (?P<ref>(?:\d+\.)?c\d+))?"
    rf"(?:, (?P<who>{_HANDLE}))?"
    r"(?:, as (?P<stated>\S+) states)?"
    r'(?:: "(?P<words>.*)")?$')
_DISSENT = re.compile(
    rf"^(?P<who>{_HANDLE}), (?P<date>\d{{4}}-\d{{2}}-\d{{2}})"
    r"(?:: (?P<words>.+?))?"
    r"(?: \(see \[\[(?P<see>[^\]]+)\]\]\))?$")


@dataclass(frozen=True)
class Receipt:
    record: str
    ref: object  # privaterecord.Ref, or None for an override's bare link
    who: str  # "@maria", or "" when the line names no one
    stated_in: object  # "SRC-04", or None
    words: object  # the words as the page holds them, or None


@dataclass(frozen=True)
class Dissent:
    who: str
    date: str
    words: object  # the words, quotes removed, or None
    see: str  # the record the words were taken from, or ""


def handle_ref(handle):
    """`@maria` for `maria` or `@maria`; "" stays "". Every writer of a handle on a committed line goes through this,
    because whoami gives a bare login and a capture's origin may carry the @."""
    handle = (handle or "").strip()
    return handle if not handle or handle.startswith("@") else f"@{handle}"


def decision_value(record_id, ref, who="", words=None, stated_in=None):
    """The value after `- **Decision:**`. `ref` is a `privaterecord.Ref`, None for an override's bare link."""
    value = f"[[{record_id}]]"
    if ref is not None:
        value += f" {ref.text}"
    if who:
        value += f", {handle_ref(who)}"
    if stated_in:
        value += f", as {stated_in} states"
    if words:
        value += f': "{textedit.inline(words)}"'
    return value


def parse_decision(value):
    """A `Receipt`, or None when the value is not a receipt."""
    found = _DECISION.match(value.strip())
    if not found:
        return None
    ref = privaterecord.parse_ref(found["ref"]) if found["ref"] else None
    return Receipt(found["record"], ref, handle_ref(found["who"] or ""), found["stated"], found["words"])


def dissent_value(who, date, words=None, see=""):
    """The value after `- **Dissent:**`: `@raj, 2026-10-22`, with the words only when the caller has the speaker's
    own yes to pass them in."""
    value = f"{handle_ref(who)}, {date}"
    if words:
        value += f': "{textedit.inline(words)}"'
    if see:
        value += f" (see [[{see}]])"
    return value


def parse_dissent(value):
    """A `Dissent`, or None when the value is not `<who>, <date>` with optional words."""
    found = _DISSENT.match(value.strip())
    if not found:
        return None
    words = found["words"]
    if words and len(words) >= 2 and words[0] == words[-1] == '"':
        words = words[1:-1]
    return Dissent(handle_ref(found["who"]), found["date"], words, found["see"] or "")
