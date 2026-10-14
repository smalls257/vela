"""The senior's handoff manifest, and the check against it. Pure: the CLI passes the
commit and the date, and reads and writes the file.

A manifest is an app's handoff list: every ID the senior takes on, with its state and a content hash.
`verify` compares the vault now with the manifest, so a change to anything the
senior accepted shows up the moment anyone runs it, not when their build breaks.
"""
import hashlib
import re
from dataclasses import dataclass

from vela import allocation, model, parse, progress, releases, schema, slices, trace
from vela.parse import split_row

# Lines a hash ignores: they change when a page is reread, handed off, or an owner confirms a decision
# made on their behalf, not when its content does.
VOLATILE = re.compile(r"^(last_verified|verified_by|handed_off):|^- \*\*[Cc]onfirmed [Bb]y:\*\*")
KIND_ORDER = ("app", "runtime", "provides", "consumes", "requirement", "epic", "slice", "release", "unknown")
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
    left: frozenset = frozenset()  # ids in `changed` that are still in the vault but no longer in the handoff list

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
    """The item's section, and its "#### <ID>" block under the page's History, so a change to its decision or
    override is charged to the item, not to the page."""
    lines = item.page.text.split("\n")
    skip = block_lines(item.page)
    spans = [range(item.line, section_end(item.page, item))]
    history = parse.history_items(item.page).get(item.id)
    if history:
        spans.append(range(*history))
    return [lines[n - 1] for span in spans for n in span if n not in skip and not VOLATILE.match(lines[n - 1])]


def page_text(vault, page):
    """The page without generated blocks, volatile frontmatter lines, or its items' sections."""
    lines = page.text.split("\n")
    skip = block_lines(page)
    for found in vault.items.values():
        for item in found:
            if item.page is page:
                skip.update(range(item.line, section_end(page, item)))
    for first, end in parse.history_items(page).values():
        skip.update(range(first, end))
    return [line for n, line in enumerate(lines, start=1) if n not in skip and not VOLATILE.match(line)]


def text(value):
    return value.strip() if isinstance(value, str) else ""


def page_entry(vault, page, kind):
    return Entry(page.id, kind, page.path, text(page.meta.get("state")), digest(page_text(vault, page)))


def item_entry(item, kind):
    return Entry(item.id, kind, item.page.path, item.fact("State"), digest(item_text(item)))


TRACER_ID = "TRACER-1"


def tracer_entry(vault):
    """Release one's Tracer and Not in the tracer bullets as one entry, or None when there are no releases. The
    tracer names the thin path every app builds its first story from, so a change to it must reach the senior
    who accepted the slice. The hash reads only those bullets: other edits to the release page are not the tracer."""
    first = releases.first_release(vault)
    if first is None:
        return None
    page = releases.page(vault)
    lines = page.text.split("\n")
    numbers = ([first.tracer_line] if first.tracer_line else []) + [left.line for left in first.not_in_tracer]
    return Entry(TRACER_ID, "release", page.path, "", digest([lines[n - 1] for n in sorted(numbers)]))


MOVES = re.compile(r"^- \*\*(Status|Journey|Journey due):\*\*")


def slice_entry(vault, page, found=None):
    """A slice page the app takes part in. The hash reads what the senior builds against (its flows, After, the joins
    its flows cross with both sides, how it ships switched off, what done is, what is left out, its overrides) and
    leaves out where it stands: Status, Journey, Journey due and History move as the teams move it, and the senior's
    own move must not read as a change to accept. The joins are read from the flows (slices.read_slices), so a join
    that changes in a flow changes the slice's hash even though the slice page did not change."""
    lines = page.text.split("\n")
    end = next((h.line for h in page.headings if h.level == 2 and h.text.strip().lower() == schema.HISTORY_HEADING.lower()),
               len(lines) + 1)
    kept = [line for n, line in enumerate(lines[:end - 1], 1) if not MOVES.match(line) and not VOLATILE.match(line)
            and n not in block_lines(page)]
    found = found if found is not None else next((s for s in slices.read_slices(vault) if s.path == page.path), None)
    kept += [f"join {contract} {sender} -> {receiver}" for contract, sender, receiver in (found.sides if found else ())]
    return Entry(page.id, "slice", page.path, "", digest(kept))


def app_slices(vault, app):
    """Slice entries for each slice the app takes part in, in slice order. Empty while slices are on the releases page,
    where the tracer entry carries the one slice there is."""
    if not slices.on_pages(vault):
        return []
    by_path = {p.path: p for p in slices.pages(vault)}
    return [slice_entry(vault, by_path[s.path], s) for s in slices.for_app(vault, slices.read_slices(vault), app)]


def handoff_list(vault, app):
    """Every entry in the app's handoff list: the app page, its runtime page, contracts provided and
    consumed, the slices it takes part in (or release one's tracer, while slices are on the releases page), the
    functional requirements its allocation rows carry, epics whose `apps` lists it, and open unknowns that block any
    of those."""
    entries = [page_entry(vault, app, "app")]
    runtime = progress.runtime_page(vault, app)
    if runtime is not None:
        entries.append(page_entry(vault, runtime, "runtime"))
    # A contract kept on this page for an external provider is one the app consumes.
    entries += [item_entry(c, "consumes" if c.fact("Provider") else "provides") for c in progress.provided(vault, app)]
    entries += [item_entry(c, "consumes") for c in progress.consumed(vault, app)]
    # The design answers for each requirement's acceptance criteria, which live on the capability page,
    # so a criterion edited after handoff must show up in handoff verify.
    carried = {r.requirement for r in allocation.rows(vault) if r.app is app and r.requirement}
    entries += [item_entry(r, "requirement") for r in allocation.requirements(vault) if r.id in carried]
    entries += [page_entry(vault, e, "epic") for e in trace.epics(vault) if app.id in trace.listed(e, "apps")]
    taking_part = app_slices(vault, app)
    entries += taking_part
    tracer = None if taking_part or slices.on_pages(vault) else tracer_entry(vault)
    if tracer is not None:
        entries.append(tracer)
    ids = {e.id for e in entries}
    blocking = {u.id: u for u in model.blocking_unknowns(vault, app)}
    for unit_id, unknowns in model.blockers(vault).items():
        if unit_id in ids:
            blocking.update({u.id: u for u in unknowns})
    entries += [item_entry(u, "unknown") for u in blocking.values()]
    unique = {e.id: e for e in entries}
    return sorted(unique.values(), key=lambda e: (KIND_ORDER.index(e.kind), e.id))


NOT_FIRM_HEADING = "## Not settled at handoff"
# What each kind of row is, in a reader's words. The table keeps the short kinds: read() parses them.
KIND_WORDS = {"app": "app", "runtime": "how it runs", "provides": "interface it offers", "consumes": "interface it uses",
              "requirement": "requirement", "epic": "epic", "slice": "slice", "release": "release", "unknown": "open question"}


CHECKS_HEADING = "## Flow checks when written"


def check_lines(taking_part, standings):
    """One bullet per slice the app takes part in, saying where its recorded flow check stood (`standing.Standing`):
    passed, its findings, not fully checked, or not checked since a date, never a pass the record does not hold."""
    return [f"- {s.label}: {standings[s.key].line()}" for s in taking_part if s.key in standings]


def write(app_id, entries, commit, today, not_firm=(), title="", checks=()):
    """The manifest file's text. `not_firm` is the sentences handoffwarn found, so the senior's copy says what was never
    decided; `checks` is `check_lines`, so it says how far each slice's logic was proved. Neither is part of a hash."""
    rows = [f"| {e.id} | {e.kind} | {e.page} | {e.state or '-'} | {e.hash} |" for e in entries]
    tail = ["", CHECKS_HEADING, "", "Where each slice's flow check stood, as recorded by vela check-slice:", "", *checks] if checks else []
    tail += ["", NOT_FIRM_HEADING, "", "The app's team accepts it knowing these are still open:", "", *not_firm, ""] if not_firm else [""]
    return "\n".join([
        f"# Handoff record: {title or app_id}", "",
        f"- **App:** {app_id}", f"- **Commit:** {commit}", f"- **Written:** {today}", f"- **Items:** {len(entries)}", "",
        f"Made by `vela handoff {app_id}`; don't edit it by hand. To see what changed since the app's team accepted it, "
        f"run `vela handoff verify {app_id}`. The Hash column is a fingerprint of each item's text, used to spot changes.", "",
        "| " + " | ".join(HEADER) + " |", "|---|---|---|---|---|", *rows, *tail])


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
    if old.kind == "release":
        return tracer_entry(vault)
    if old.kind == "slice":
        found = [p for p in slices.pages(vault) if p.id == old.id]
        return slice_entry(vault, found[0]) if found else None
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


def describe(old, new, left=False, name=""):
    """One changed item, by name when the caller knows it; the ID stays as a tag."""
    parts = []
    if old.state != new.state:
        parts.append(f"state {old.state or 'none'} -> {new.state or 'none'}")
    if old.kind != new.kind:
        parts.append(f"was {KIND_WORDS.get(old.kind, old.kind)}, now {KIND_WORDS.get(new.kind, new.kind)}")
    if old.page != new.page:
        parts.append(f"moved from {old.page} to {new.page}")
    if old.hash != new.hash:
        parts.append("its wording changed")
    if left:
        parts.append("no longer in this app's handoff list")
    subject = f"{name} ({new.id})" if name and name != new.id else new.id
    return f"changed: {KIND_WORDS.get(new.kind, new.kind)} {subject}: " + ", ".join(parts)
