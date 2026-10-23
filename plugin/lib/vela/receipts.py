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

from vela import closegate, override, privaterecord, questions
from vela.decisions import textedit
from vela.model import Finding

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


# ---- the check (E315) --------------------------------------------------------------------------------------------


def _predates_receipts(vault, bullet):
    """Whether the bullet links a record from before receipts were required, so its line is left as it was: a stub
    dated earlier than `records_split`, or a record still committed whole (a plan that has not split; W720 nags it).
    A stub with no `records_split` key is not exempt."""
    if not bullet.links:
        return False
    record = vault.page(bullet.links[0].target)
    if record is None or record.type != "session":
        return False
    if questions.holds_its_words(record):
        return True
    split = vault.config.get("records_split")
    return bool(split) and bool(record.meta.get("date")) and str(record.meta["date"]) < str(split)


def _bare_link_is_overridden(page, bullet):
    return any(closegate.QUOTED_YES_RULE in o.rules for o in override.valid_overrides(page, bullet.item))


def _decision_problem(page, bullet):
    receipt = parse_decision(bullet.value)
    if receipt is None:
        return ("is not a receipt. Write [[<session>]] c07, @who, naming the session, the capture and who said yes.")
    if (receipt.ref is None or not receipt.who) and not _bare_link_is_overridden(page, bullet):
        return ("has no capture or no one who said yes. Write [[<session>]] c07, @who, or record an override of "
                f"{closegate.QUOTED_YES_RULE}.")
    return None


def receipt_rules(vault, today):
    """E315: every `**Decision:**` and `**Dissent:**` bullet is in the receipt form, once per line. The Violation this
    prevents is a Silent Fallback in the record: a free-text "Decision: the team agreed" reads like a yes that someone
    gave. `vela check` judges the form only, because it does not know who the lead is; the close gate adds the lead
    clause."""
    for page in vault.pages:
        seen = set()
        for bullet in page.bullets:
            if bullet.label not in ("Decision", "Dissent") or bullet.generated or bullet.line in seen:
                continue
            seen.add(bullet.line)
            if _predates_receipts(vault, bullet):
                continue
            if bullet.label == "Decision":
                problem = _decision_problem(page, bullet)
            else:
                problem = None if parse_dissent(bullet.value) else (
                    "is not a Dissent. Write @who, <date>, with the words only when they said yes to being quoted.")
            if problem:
                yield Finding(page.path, bullet.line, "E315", f"The {bullet.label} line {problem}",
                              "Use the receipt form in CONVENTIONS (Page level).")
