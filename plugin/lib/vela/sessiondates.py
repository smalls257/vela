"""A session record as plain words: its date. The dashboard (`vela explore`) and the reading copy (`vela view`) leave session
records out (the owner's call: a reader of the plan does not need the log of how it was written). Where a page links a session
only to say when something happened, the reader keeps the date; the link and the record's name go.

The Violation this prevents is a Leaky Narrative: a reader who sees "2026-10-19-first-release-boundary" in a Source line is
shown the vault's filing system instead of the fact it was settled on October 19. Pure: it takes the vault and the text.
"""
import re

from vela import say
from vela.parse import WIKILINK, parse_link

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NO_DATE = "an earlier date"


def session_date(page):
    """A session's date: its `date:` line, else the date its ID starts with ("2026-10-19-release-plan"), else ""."""
    found = str(page.meta.get("date") or "") or page.name[:10]
    return found if DATE.match(found) else ""


def session_of(vault, link, from_page):
    """The session record a wikilink points at, or None."""
    target = vault.resolve(link, from_page)
    return target if target is not None and target.type == "session" else None


def without_sessions(vault, text, from_page=None):
    """`text` with each wikilink to a session record, and each session ID written bare (a search snippet has had its
    brackets taken off), replaced by that session's date in words."""
    def date_of(match):
        found = session_of(vault, parse_link(match.group(1), 0), from_page)
        return match.group(0) if found is None else say.date_words(session_date(found)) or NO_DATE
    text = WIKILINK.sub(date_of, text)
    by_name = {p.name: p for p in vault.sessions}
    if not by_name:
        return text
    bare = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(n) for n in sorted(by_name, key=len, reverse=True)) + r")(?![\w-])")
    return bare.sub(lambda m: say.date_words(session_date(by_name[m.group(0)])) or NO_DATE, text)


def session_names(vault):
    return {p.name for p in vault.sessions}
