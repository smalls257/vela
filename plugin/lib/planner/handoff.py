"""The senior's handoff manifest, and the check against it. Pure: the CLI passes the
commit and the date, and reads and writes the file.

A manifest lists every ID in an app's slice with its state and a content hash.
`verify` compares the vault now with the manifest, so a change to anything the
senior accepted shows up the moment anyone runs it, not when their build breaks.
"""
import hashlib
import re
from dataclasses import dataclass

from planner import model, progress, trace
from planner.parse import split_row

# Lines a hash ignores: they change when a page is reread, handed off, or an owner confirms a decision
# made on their behalf, not when its content does.
VOLATILE = re.compile(r"^(last_verified|verified_by|handed_off):|^- \*\*[Cc]onfirmed [Bb]y:\*\*")
KIND_ORDER = ("app", "runtime", "provides", "consumes", "epic", "unknown")
HEADER = ("ID", "Kind", "Page", "State", "Hash")
FACT = re.compile(r"^- \*\*(App|Commit|Written|Items):\*\* (.+)$")


class ManifestError(ValueError):
    """The manifest file cannot be read as one."""


@dataclass(frozen=True)
class Entry:
    id: str
    kind: str  # one of KIND_ORDER
    page: str  # vault-relative path
    state: str
    hash: str  # first 12 hex digits of SHA-256 over the item's own text


@dataclass(frozen=True)
class Diff:
    changed: tuple  # (old Entry, new Entry)
    added: tuple  # new Entry
    removed: tuple  # old Entry
    left: frozenset = frozenset()  # ids in `changed` that are still in the vault but no longer in the slice

    @property
    def breaks_acceptance(self):
        """Something the senior accepted changed or went away. A new item alone does not count."""
        return bool(self.changed or self.removed)


def digest(lines):
    kept = [line.rstrip() for line in lines]
    while kept and not kept[0]:
        kept.pop(0)
    while kept and not kept[-1]:
        kept.pop()
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()[:12]


def block_lines(page):
    """1-based line numbers inside generated blocks, markers included."""
    skip = set()
    for block in page.blocks:
        skip.update(range(block.start, block.end + 1))
    return skip


def section_end(page, item):
    """The line after an item's section: the next heading at level 3 or above, or the end."""
    later = [h.line for h in page.headings if h.line > item.line and h.level <= 3]
    return later[0] if later else len(page.text.split("\n")) + 1


def item_text(item):
    lines = item.page.text.split("\n")
    skip = block_lines(item.page)
    return [lines[n - 1] for n in range(item.line, section_end(item.page, item))
            if n not in skip and not VOLATILE.match(lines[n - 1])]


def page_text(vault, page):
    """The page without generated blocks, volatile frontmatter lines, or its items' sections."""
    lines = page.text.split("\n")
    skip = block_lines(page)
    for found in vault.items.values():
        for item in found:
            if item.page is page:
                skip.update(range(item.line, section_end(page, item)))
    return [line for n, line in enumerate(lines, start=1) if n not in skip and not VOLATILE.match(line)]


def text(value):
    return value.strip() if isinstance(value, str) else ""


def page_entry(vault, page, kind):
    return Entry(page.id, kind, page.path, text(page.meta.get("state")), digest(page_text(vault, page)))


def item_entry(item, kind):
    return Entry(item.id, kind, item.page.path, item.fact("State"), digest(item_text(item)))


def slice_of(vault, app):
    """Every entry in the app's slice: the app page, its runtime page, contracts provided and
    consumed, epics whose `apps` lists it, and open unknowns that block any of those."""
    entries = [page_entry(vault, app, "app")]
    runtime = progress.runtime_page(vault, app)
    if runtime is not None:
        entries.append(page_entry(vault, runtime, "runtime"))
    # A contract kept on this page for an external provider is one the app consumes.
    entries += [item_entry(c, "consumes" if c.fact("Provider") else "provides") for c in progress.provided(vault, app)]
    entries += [item_entry(c, "consumes") for c in progress.consumed(vault, app)]
    entries += [page_entry(vault, e, "epic") for e in trace.epics(vault) if app.id in trace.listed(e, "apps")]
    ids = {e.id for e in entries}
    blocking = {u.id: u for u in model.blocking_unknowns(vault, app)}
    for unit_id, unknowns in model.blockers(vault).items():
        if unit_id in ids:
            blocking.update({u.id: u for u in unknowns})
    entries += [item_entry(u, "unknown") for u in blocking.values()]
    unique = {e.id: e for e in entries}
    return sorted(unique.values(), key=lambda e: (KIND_ORDER.index(e.kind), e.id))


def write(app_id, entries, commit, today):
    """The manifest file's text."""
    rows = [f"| {e.id} | {e.kind} | {e.page} | {e.state or '-'} | {e.hash} |" for e in entries]
    return "\n".join([
        f"# Handoff manifest: {app_id}", "",
        f"- **App:** {app_id}", f"- **Commit:** {commit}", f"- **Written:** {today}", f"- **Items:** {len(entries)}", "",
        f"Written by `planner handoff {app_id}`. Do not edit it by hand. "
        f"`planner handoff verify {app_id}` lists what changed since the senior accepted this slice.", "",
        "| " + " | ".join(HEADER) + " |", "|---|---|---|---|---|", *rows, ""])


def read(text_value):
    """(facts dict with App, Commit and Written, [Entry]). Raises ManifestError."""
    facts, entries, in_table = {}, [], False
    for raw in text_value.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        fact = FACT.match(line)
        if fact:
            facts[fact.group(1)] = fact.group(2).strip()
        elif line.startswith("|"):
            cells = split_row(line)
            if cells == HEADER:
                in_table = True
            elif in_table and not set(line) <= set("|- "):
                if len(cells) != len(HEADER) or cells[1] not in KIND_ORDER or not re.match(r"^[0-9a-f]{12}$", cells[4]):
                    raise ManifestError(f"this row is not a manifest row: {line}")
                entries.append(Entry(cells[0], cells[1], cells[2], "" if cells[3] == "-" else cells[3], cells[4]))
    if not in_table:
        raise ManifestError("it has no ID | Kind | Page | State | Hash table")
    for label in ("App", "Commit", "Written", "Items"):
        if label not in facts:
            raise ManifestError(f"it has no '- **{label}:**' line")
    ids = [e.id for e in entries]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ManifestError(f"these IDs have more than one row: {', '.join(repeated)}")
    if not facts["Items"].isdigit() or int(facts["Items"]) != len(entries):
        raise ManifestError(f"its Items line says {facts['Items']} but the table has {len(entries)} rows, so a row was added or deleted by hand")
    return facts, entries


def check_manifest(app_id, facts, entries):
    """Refuse a manifest that is not the one for this app, or that has lost the app's own row."""
    if facts.get("App") != app_id:
        raise ManifestError(f"it records {facts.get('App')}, not {app_id}")
    if not any(e.id == app_id and e.kind == "app" for e in entries):
        raise ManifestError(f"it has no row for {app_id} itself, so a row was deleted by hand")


def same(old, new):
    return (old.hash, old.state, old.page, old.kind) == (new.hash, new.state, new.page, new.kind)


def lookup(vault, old):
    """The accepted ID as the whole vault holds it now, or None when the vault no longer has it."""
    found = vault.items.get(old.id)
    if found:
        return item_entry(found[0], old.kind)
    pages = vault.by_id.get(old.id)
    if pages:
        return page_entry(vault, pages[0], old.kind)
    return None


def verify(accepted, now, vault):
    """Compare the accepted entries with the slice now. An accepted ID that left the slice but
    is still in the vault is `changed` (the senior should reread it); only an ID the vault no
    longer holds is `removed`."""
    before = {e.id: e for e in accepted}
    after = {e.id: e for e in now}
    changed = [(before[i], after[i]) for i in sorted(before.keys() & after.keys()) if not same(before[i], after[i])]
    removed, left = [], set()
    for i in sorted(before.keys() - after.keys()):
        still = lookup(vault, before[i])
        if still is None:
            removed.append(before[i])
        else:
            changed.append((before[i], still))
            left.add(i)
    changed.sort(key=lambda pair: pair[0].id)
    added = tuple(after[i] for i in sorted(after.keys() - before.keys()))
    return Diff(tuple(changed), added, tuple(removed), frozenset(left))


def describe(old, new, left=False):
    parts = []
    if old.state != new.state:
        parts.append(f"state {old.state or '-'} -> {new.state or '-'}")
    if old.kind != new.kind:
        parts.append(f"kind {old.kind} -> {new.kind}")
    if old.page != new.page:
        parts.append(f"moved from {old.page} to {new.page}")
    if old.hash != new.hash:
        parts.append("text changed")
    if left:
        parts.append("no longer in this app's slice")
    return f"changed: {new.id} ({new.kind}, {new.page}): " + ", ".join(parts)
