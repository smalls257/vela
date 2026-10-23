"""Does a session's name put a person in the shared plan? Pure.

The Violation this prevents is a Leaky Narrative at the one place the private session still shows: the id and title
of a session are committed, so "a person's name in a title" would carry a person's name into the plan's history while every word
of the session itself stays on one machine. The check runs at start, before anything is written, from the names the
plan really holds: page and item owners, the grill owners and joins in `.vela.yaml`, the lead's handle and display
names, and the person origins in this machine's private files. Team handles (`@org/team`) are not people.
"""
import re

from vela import grillowners, schema

TITLE_QUESTION = "The session's name is shared with the team. Can we call it by the topic, not the person?"
HANDLES = re.compile(schema.HANDLE)
CAPTURE_ORIGIN = re.compile(r"^- \[[\w-]+\] \((?P<origin>[^)]*)\) ", re.M)
FROM = "claude, from "
SHORT = 3  # a word of a display name shorter than this is too common to refuse a title over


def handles_in(value):
    """The person handles in a string, `@` dropped and lower-cased; a team handle (`@org/team`) is left out."""
    return {found[1:].lower() for found in HANDLES.findall(str(value or "")) if "/" not in found}


def people(vault, handle, names, origins):
    """The lower-case handles and display names this plan knows its people by."""
    found = set()
    for page in vault.pages:
        found |= handles_in(page.meta.get("owner"))
    for items in vault.items.values():
        for item in items:
            found |= handles_in(item.fact("Owner"))
    entries, _ = grillowners.read(vault.config)
    for entry in entries.values():
        found |= handles_in(entry.owner)
        for joined in entry.join:
            found |= handles_in(joined)
    found |= handles_in(handle) | {name.casefold() for name in names if name}
    return found | {origin.lstrip("@").casefold() for origin in origins if origin}


def origins_in(private_text):
    """The people a private file quotes: handles and capitalized names, `claude, from <name>` read as <name>. A role
    ("client", "the sponsor") and Claude itself are not people."""
    found = set()
    for match in CAPTURE_ORIGIN.finditer(private_text):
        origin = match["origin"].strip()
        origin = origin[len(FROM):].strip() if origin.lower().startswith(FROM) else origin
        if origin.startswith("@") and "/" not in origin or origin[:1].isupper():
            found.add(origin)
    return found


def name_words(person):
    """The words of a display name worth matching on their own (at least three letters). A handle is not split: its
    hyphen parts are ordinary words ("agent" in `@agent-lead`) and only the whole handle names a person."""
    return {word for word in person.split() if len(word) >= SHORT} if " " in person else set()


def named(title, people):
    """The title's words that name a person: a whole handle, or a word of a display name."""
    words = [word for word in re.split(r"[^a-z0-9]+", title.casefold()) if word]
    wholes = set(people)
    parts = set().union(*(name_words(person) for person in people)) if people else set()
    return [word for word in dict.fromkeys(words) if word in wholes or word in parts]
