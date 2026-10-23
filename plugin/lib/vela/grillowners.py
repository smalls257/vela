"""Who runs a grill, and who is asked to join it: the `grills:` block in `.vela.yaml`. Pure.

The Violation this exists to prevent is a Leaky Narrative on the lead's side: if "who runs the grill on the token
lifetime" lived in a hand-typed line on a page, in a spot that depends on whether the item is a heading, a table row
or a whole page, every reader of it would have to know the three shapes, and a typo would quietly hand a grill to
nobody. One block keyed by ID covers an item of any shape, `vela grill owner` is the only writer, and the reader
here says what it could not read instead of dropping it (Silent Fallback).

    grills:
      "CON-022":
        owner: "@agent-lead"
        join: ["@sam-hadley"]

A grill with no entry belongs to the item's own owner. `owner` replaces that; `join` lists the people asked to take
part, and they see the grill under their own filter. Handles are written with their @.
"""
import re

import yaml

from vela import schema

KEY = "grills"
HANDLE_RE = re.compile(rf"^{schema.HANDLE}$")
TOP_LEVEL = re.compile(r"^[^\s#]")


def handle_problem(value):
    """The sentence saying why `value` is not a handle, or "" when it is one (written with or without the @)."""
    text = str(value).strip()
    text = text if text.startswith("@") else "@" + text
    return "" if HANDLE_RE.match(text) else f"'{value}' is not a handle."


def handle(value):
    text = str(value).strip()
    return text if text.startswith("@") else "@" + text


class Entry:
    """One item's grill owner and the people asked to join. Either may be empty."""

    def __init__(self, owner="", join=()):
        self.owner, self.join = owner, tuple(join)

    def __eq__(self, other):
        return isinstance(other, Entry) and (self.owner, self.join) == (other.owner, other.join)

    def __repr__(self):
        return f"Entry({self.owner!r}, {self.join!r})"


def read(config):
    """({ID: Entry}, problems) from the parsed `.vela.yaml`. An entry that is not readable is left out and named."""
    block = (config or {}).get(KEY)
    if block is None:
        return {}, []
    if not isinstance(block, dict):
        return {}, [f"The {KEY} in the plan's settings should list an ID, then its owner and who is asked to join."]
    found, problems = {}, []
    for ident, body in block.items():
        entry, why = _entry(body)
        if why:
            problems.append(f"The grill on {ident}: {why}")
        else:
            found[str(ident)] = entry
    return found, problems


def _entry(body):
    if not isinstance(body, dict) or not set(body) <= {"owner", "join"}:
        return None, "write `owner:` and `join:` and nothing else."
    owner = body.get("owner") or ""
    joins = body.get("join") or []
    if not isinstance(joins, list):
        return None, "`join:` is a list of handles."
    for value in ([owner] if owner else []) + list(joins):
        why = handle_problem(value)
        if why:
            return None, why
    return Entry(handle(owner) if owner else "", [handle(j) for j in joins]), ""


def with_entry(text, ident, entry):
    """`.vela.yaml` text with `ident`'s entry set to `entry` (removed when the entry is empty), every other line kept."""
    current = yaml.safe_load(text) or {}
    block = current.get(KEY) if isinstance(current.get(KEY), dict) else {}
    entries = {str(k): v for k, v in block.items()}
    if entry.owner or entry.join:
        entries[ident] = {"owner": entry.owner, "join": list(entry.join)}
    else:
        entries.pop(ident, None)
    return replace_block(text, render(entries))


def render(entries):
    """The `grills:` block for {ID: {"owner", "join"}}, in ID order; "" when there are none."""
    lines = []
    for ident in sorted(entries):
        body = entries[ident]
        lines.append(f'  "{ident}":')
        if body.get("owner"):
            lines.append(f'    owner: "{body["owner"]}"')
        if body.get("join"):
            lines.append("    join: [" + ", ".join(f'"{j}"' for j in body["join"]) + "]")
    return f"{KEY}:\n" + "\n".join(lines) + "\n" if lines else ""


def replace_block(text, block):
    """`text` with its top-level `grills:` block replaced by `block` (dropped when empty, added at the end when absent)."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if re.match(rf"^{KEY}\s*:", line)), None)
    if start is None:
        body = text if text.endswith("\n") or not text else text + "\n"
        return body + block
    end = start + 1
    while end < len(lines) and not (TOP_LEVEL.match(lines[end]) and lines[end].strip()):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1  # blank lines after the block belong to what follows
    return "\n".join(lines[:start] + (block.rstrip("\n").split("\n") if block else []) + lines[end:])
