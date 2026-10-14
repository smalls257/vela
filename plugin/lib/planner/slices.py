"""Slices: the unit of done. Which flows each slice proves, what it comes after, which joins it crosses and where it
stands. Pure: a vault in, slices out.

This is the one place that reads a slice. check-slice, check's slice rules, the handoff, planner next and the dashboard
all ask it, and nothing else reads the bullets behind it: a Shield against the Distributed Monolith in which every
caller parses slice pages (or the releases page) its own way, and one reader's idea of "the tracer" drifts from another's.

A slice lives on its own page, `slices/SLC-nnn-<slug>.md`, with `**Status:**`, `**Flows:**`, `**After:**`, `**Joins:**`
and the rest as bullets under the title. A vault with no slice pages yet is read the old way, so nothing breaks while a
lead moves over: release one's `**Tracer:**` flows are the tracer slice, and a later release's `**Flows:**` bullet names
its own, each after the one before. `planner check` says, once, that the vault is still on the old way (W399): the
fallback is never silent.
"""
import re
from dataclasses import dataclass, field, replace

from planner import releases, schema

STATUSES = schema.SLICE_STATUSES
PAGE_TYPE = "slice"
SLICE_ID = re.compile(r"\bSLC-\d{3}\b")
CONTRACT_ID = re.compile(r"\bCON-\d{3}\b")
JOURNEY = re.compile(rf"^passed (?P<date>\d{{4}}-\d{{2}}-\d{{2}}) by (?P<by>{schema.HANDLE}), (?P<evidence>\S.*)$")
NOT_IN_HEADING = "not in this slice"


@dataclass(frozen=True)
class Journey:
    """The hand-written record that the slice's journey ran green: `passed <date> by @who, <evidence link>`."""
    date: str
    by: str
    evidence: str
    line: int
    problem: str = ""  # why the line does not read; "" when it does


@dataclass(frozen=True)
class Slice:
    id: str  # SLC-nnn on a slice page; "" for a slice still read from the releases page
    name: str  # the page's title, or the release heading ("Release one: pilot")
    flows: tuple  # flow ids, in the order written
    path: str  # the page that names the flows
    line: int  # the bullet that names them (the title when there is none)
    order: int  # 0 for the first slice; slices come in After order, ties by ID
    after: tuple = ()  # keys of the slices it comes after; a release's slice comes after the release before it
    joins: tuple = ()  # contract ids it crosses, in the order written
    sides: tuple = ()  # (contract id, sender, receiver) as the Joins bullet names them in brackets
    status: str = ""  # one of STATUSES, or "" until a grill plans it (or for a slice read from the releases page)
    status_raw: str = ""  # as written, so a misspelt status is reported, never read as "not planned yet"
    journey: Journey = None
    owner: str = ""
    ships_off: str = ""
    done_when: str = ""
    milestone: str = ""  # the slice page's own Milestone bullet, as written
    not_in: tuple = ()  # releases.Left: what is left out of it, and why
    flows_none: str = ""  # the reason, when Flows says `none, <reason>`
    from_page: bool = False
    lines: dict = field(default_factory=dict, compare=False, hash=False)  # label -> line of its bullet

    @property
    def key(self):
        """What After names: the slice's ID, or its release heading while it has no page."""
        return self.id or self.name

    @property
    def label(self):
        return f"{self.id} {self.name}" if self.id else self.name

    def at_least(self, status):
        return rank(self.status) >= rank(status)


def rank(status):
    """Where a status sits on the way to on: -1 for "not planned yet" and anything unreadable."""
    return STATUSES.index(status) if status in STATUSES else -1


def pages(vault):
    """The vault's slice pages, by ID."""
    return sorted(vault.of_type(PAGE_TYPE), key=lambda p: p.id)


def on_pages(vault):
    """True once any slice has a page: from then on the releases page names no slices."""
    return bool(pages(vault))


def read_slices(vault):
    """Every slice in the vault, in order: from slice pages when there are any, else from the releases page."""
    found = pages(vault)
    if found:
        return _in_order([read_page(p) for p in found])
    return _from_releases(vault)


def read_page(page):
    """One slice page's facts. Records what is written; the rules judge it."""
    def bullet(label):
        found = page.page_bullets(label)
        return found[0] if found else None

    lines = {}
    values = {}
    for label in schema.SLICE_LABELS:
        b = bullet(label)
        if b is not None:
            lines[label], values[label] = b.line, b.value.strip()
    flows, flows_none = (), ""
    if "Flows" in values:
        # Every flow ID on the line counts, linked or bare, so a typo is reported (W393) rather than read as words.
        _, _, flows_none = releases.read_tracer(values["Flows"])
        flows = () if flows_none else _ids(releases.FLOW_ID, values["Flows"])
    status_raw = values.get("Status", "")
    status = " ".join(status_raw.lower().split())
    journey = read_journey(values["Journey"], lines["Journey"]) if "Journey" in values else None
    title = str(page.meta.get("title") or page.id)
    return Slice(page.id, title, tuple(flows), page.path, lines.get("Flows", 1), 0,
                 after=_ids(SLICE_ID, values.get("After", "")), joins=_ids(CONTRACT_ID, values.get("Joins", "")),
                 sides=tuple(read_sides(values.get("Joins", ""))),
                 status=status if status in STATUSES else "", status_raw=status_raw, journey=journey,
                 owner=values.get("Owner", ""), ships_off=values.get("Ships switched off", ""),
                 done_when=values.get("Done when", ""), milestone=values.get("Milestone", ""),
                 not_in=tuple(_not_in(page)), flows_none=flows_none, from_page=True, lines=lines)


def read_journey(value, line):
    m = JOURNEY.match(value.strip())
    if not m:
        return Journey("", "", "", line, "is not 'passed YYYY-MM-DD by @who, <where the run's result is>'")
    return Journey(m["date"], m["by"], m["evidence"].strip(), line)


def _ids(pattern, value):
    return tuple(dict.fromkeys(pattern.findall(value)))


def _not_in(page):
    """The plain bullets under `## Not in this slice`, read like Not in the tracer: what, the IDs it names, why."""
    lines = page.text.split("\n")
    inside = False
    for n, line in enumerate(lines, 1):
        if line.startswith("#"):
            inside = line.lstrip("#").strip().lower() == NOT_IN_HEADING
            continue
        if inside and re.match(r"^[-*] (?!\*\*)", line):
            yield releases.read_left(line[2:], n)


def _from_releases(vault):
    """The old way: release one's Tracer flows, then each later release's Flows, each after the one before."""
    found = releases.releases(vault)
    page = releases.page(vault)
    out = []
    for n, release in enumerate(found):
        if n == 0 and release.tracer_flows:
            flows, line, not_in = release.tracer_flows, release.tracer_line, tuple(release.not_in_tracer)
        elif release.flows:
            flows, line, not_in = release.flows, release.flows_line, ()
        else:
            continue
        after = (out[-1].key,) if out else ()
        out.append(Slice("", release.name, tuple(flows), page.path if page else "", line, len(out), after=after,
                         not_in=not_in, milestone=release.name))
    return out


def _in_order(found):
    """After order, ties by ID: a slice comes once everything it names in After has come. Slices caught in a circle
    (E394) or after a slice that does not exist keep their ID order at the end, so nothing drops out of view."""
    by_key = {s.key: s for s in found}
    placed, out = set(), []
    pending = sorted(found, key=lambda s: s.id)
    progress = True
    while pending and progress:
        progress = False
        for s in list(pending):
            if all(a in placed or a not in by_key for a in s.after):
                out.append(s)
                placed.add(s.key)
                pending.remove(s)
                progress = True
                break
    out += pending
    return [replace(s, order=n) for n, s in enumerate(out)]


def tracer(found):
    """The tracer: the first slice, built first and kept. None when the vault names no slice."""
    return found[0] if found else None


def upstream(found, chosen):
    """The keys of `chosen` and every slice it comes after, all the way back."""
    by_key = {s.key: s for s in found}
    seen, todo = set(), [chosen.key]
    while todo:
        key = todo.pop()
        if key in seen:
            continue
        seen.add(key)
        if key in by_key:
            todo += list(by_key[key].after)
    return seen


def cycles(found):
    """Each group of slices that come after each other in a circle, once, as sorted keys. A slice in one can never
    start, because each waits on another."""
    by_key = {s.key: s for s in found}
    out, done = [], set()
    for key in sorted(by_key):
        if key in done:
            continue
        circle = sorted(k for k in upstream(found, by_key[key]) if k in by_key and key in upstream(found, by_key[k]))
        if key in by_key[key].after or len(circle) > 1:
            out.append(tuple(circle))
            done.update(circle)
    return out


def milestones(vault):
    """{slice id: [release]} for each release whose `**Slices:**` bullet names the slice: the dated checkpoints it is
    part of. Nothing waits for one; a slice switches on when its journey passes."""
    out = {}
    for release in releases.releases(vault):
        for sid in release.slices:
            out.setdefault(sid, []).append(release)
    return out


SIDES = re.compile(r"(CON-\d{3})[^()]*?\(([^()]+?)\s*(?:→|->)\s*([^()]+?)\)")


def read_sides(value):
    """(contract id, sender, receiver) for each join written `<contract> (<sender> → <receiver>)`."""
    for m in SIDES.finditer(value):
        yield m.group(1), _plain(m.group(2)), _plain(m.group(3))


def _plain(text):
    """A side as words: a link reads as its label."""
    return " ".join(re.sub(r"\[\[[^\]|]*\|([^\]]+)\]\]|\[\[([^\]]+)\]\]", lambda m: m.group(1) or m.group(2), text).split())


def names(app):
    """The words a slice page may call an app by: its title or its slug, ignoring case."""
    return {str(app.meta.get("title") or "").lower(), app.id.removeprefix("APP-").replace("-", " ").lower()} - {""}


def _calls(side, app):
    """A side names the app when its words are the app's name or a part of it ("Kiosks" for "Port kiosks")."""
    words = set(side.lower().split())
    return bool(words) and any(words <= set(n.split()) or set(n.split()) <= words for n in names(app))


def for_app(vault, found, app):
    """The slices an app takes part in: a flow of the slice has a step to or from it, a join names it on one side,
    or the slice joins a contract it provides. Consuming a joined contract is not enough: three channels consume one
    booking API, and only the channel a slice moves takes part in it."""
    from planner import flows, progress
    provided = {c.id for c in progress.provided(vault, app) if not c.fact("Provider")}
    out = []
    for s in found:
        apps, _ = flows.passes_through(vault, s.flows)
        sided = any(_calls(sender, app) or _calls(receiver, app) for _, sender, receiver in s.sides)
        if app.id in apps or sided or provided & set(s.joins):
            out.append(s)
    return out


# What moves a slice on from each status, in words for `planner next`. Vela plans and records; the teams run things.
NEXT = {
    "": "is not planned yet: draw its flows, write their case tables and run planner check-slice {id} until it passes "
        "(or each finding has an override with an end date), then plan it in a Grill",
    "planned": "is planned: hand its apps over so each team accepts its part, then set it to building",
    "building": "is building: run its journey in the shared environment and record the result as "
                "'- **Journey:** passed YYYY-MM-DD by @who, <link>'",
    "journey passes": "passed its journey: deploy it switched off ({ships}), then set it to live but off",
    "live but off": "is live but off: the business owner decides when to switch it on, and History records who and when",
}


def next_step(found):
    """The next move for the first slice, in slice order, that is not on and whose After slices have all passed their
    journey; failing that, the first that is not on. "" when every slice is on, or there are none."""
    by_key = {s.key: s for s in found}
    waiting = [s for s in found if s.status != "on"]
    ready = [s for s in waiting if all(by_key[a].at_least("journey passes") for a in s.after if a in by_key)]
    chosen = (ready or waiting or [None])[0]
    if chosen is None:
        return ""
    ships = chosen.ships_off or "how it ships switched off is not written yet"
    return f"{chosen.label} {NEXT[chosen.status].format(id=chosen.id or chosen.name, ships=ships)}."
