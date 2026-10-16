"""Slices: the unit of done. Which flows each slice proves, what it comes after, which joins it crosses and where it
stands. Pure: a vault in, slices out.

This is the one place that reads a slice. check-slice, check's slice rules, the handoff, vela next and the dashboard
all ask it, and nothing else reads the bullets behind it: a Shield against the Distributed Monolith in which every
caller parses slice pages (or the releases page) its own way, and one reader's idea of "the tracer" drifts from another's.

A slice lives on its own page, `slices/SLC-nnn-<slug>.md`, with `**Status:**`, `**Flows:**`, `**After:**` and the rest
as bullets under the title. The joins it crosses are not written on the page: they are read from its flows' steps
(`flows.steps`), which already name each contract with its sender and receiver, so a hand-written list cannot drift from
the flows. A page that still has the old `**Joins:**` bullet is told so by check (W405), never quietly obeyed. A vault with no slice pages yet is read the old way, so nothing breaks while a
lead moves over: release one's `**Tracer:**` flows are the tracer slice, and a later release's `**Flows:**` bullet names
its own, each after the one before. `vela check` says, once, that the vault is still on the old way (W399): the
fallback is never silent.
"""
import re
from dataclasses import dataclass, field, replace

from vela import releases, schema

STATUSES = schema.SLICE_STATUSES
PAGE_TYPE = "slice"
SLICE_ID = re.compile(r"\bSLC-\d{3}\b")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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
    joins: tuple = ()  # contract ids its flows' steps cross, in flow and step order
    sides: tuple = ()  # (contract id, sender, receiver) for each join, as the first step that crosses it names its ends
    status: str = ""  # one of STATUSES, or "" until a grill plans it (or for a slice read from the releases page)
    status_raw: str = ""  # as written, so a misspelled status is reported, never read as "not planned yet"
    journey: Journey = None
    journey_due: str = ""  # the Journey due bullet as written: the date the team expects the journey to run
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
    read = _in_order([read_page(p) for p in found]) if found else _from_releases(vault)
    return _with_joins(vault, read)


def read_page(page):
    """One slice page's facts. Records what is written; the rules judge it."""
    def bullet(label):
        found = page.page_bullets(label)
        return found[0] if found else None

    lines = {}
    values = {}
    for label in schema.SLICE_LABELS + schema.RETIRED_SLICE_LABELS:
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
                 after=_ids(SLICE_ID, values.get("After", "")),
                 status=status if status in STATUSES else "", status_raw=status_raw, journey=journey,
                 journey_due=values.get("Journey due", ""),
                 owner=values.get("Owner", ""), ships_off=values.get("Ships switched off", ""),
                 done_when=values.get("Done when", ""), milestone=values.get("Milestone", ""),
                 not_in=tuple(_not_in(page)), flows_none=flows_none, from_page=True, lines=lines)


def read_journey(value, line):
    m = JOURNEY.match(value.strip())
    if not m:
        return Journey("", "", "", line, "is not 'passed YYYY-MM-DD by @who, <where the run's result is>'")
    return Journey(m["date"], m["by"], m["evidence"].strip(), line)


def _with_joins(vault, found):
    """Each slice with the joins its flows cross, read from the flows' steps: one read of the steps for all slices."""
    from vela import flows  # flows reads the vault's pages; slices is imported by modules flows does not need
    contract_ids = {c.id for c in vault.contracts}
    by_flow = {}
    for step in flows.steps(vault):
        by_flow.setdefault(step.page.id, []).append(step)
    out = []
    for s in found:
        sides = {}
        for fid in s.flows:
            for step in by_flow.get(fid, ()):
                for contract in step.contracts:
                    if contract.id in contract_ids and contract.id not in sides:
                        sender, receiver = (_plain(step.pair[0]), _plain(step.pair[1])) if step.pair else ("", "")
                        sides[contract.id] = (contract.id, sender, receiver)
        out.append(replace(s, joins=tuple(sides), sides=tuple(sides.values())))
    return out


def journey_overdue(s, today):
    """True when the slice's Journey due date has passed and no readable Journey line records the run: the team said
    when it would run, and nothing says it did. A due date that does not read is check's to report (W400), not a guess."""
    return bool(DATE.match(s.journey_due)) and s.journey_due < today and (s.journey is None or bool(s.journey.problem))


def journey_overdue_says(s):
    """The plain words a reader sees for an overdue journey, after the slice's name: on the dashboard and in check.
    The date in words, not ISO; what to do is check's Fix line, so it isn't said twice here."""
    from vela import say
    recorded = ("the result on the slice page can't be read; check its Journey line" if s.journey is not None
                else "nothing says how it went")
    return f"someone was due to try its journey by {say.date_words(s.journey_due)}, and {recorded}"


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


def roots(found):
    """The slices that come after nothing, in slice order: the tracer, when there is exactly one."""
    return [s for s in found if not s.after]


def tracer(found):
    """The tracer: the one slice with no After, built first and kept. Every other slice comes after it, or after one
    that does. When two or more name no After, the first by ID stands in and check says so (W406); when none does (a
    circle, E394), there is no tracer. None when the vault names no slice."""
    first = roots(found)
    return first[0] if first else None


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


def _plain(text):
    """A side as words: a link reads as its label."""
    return " ".join(re.sub(r"\[\[[^\]|]*\|([^\]]+)\]\]|\[\[([^\]]+)\]\]", lambda m: m.group(1) or m.group(2), text).split())


def taking_part(vault, found):
    """{slice key: [app id]}: the apps each slice takes part in, in vault order. An app takes part when a flow of the
    slice has a step to or from it, or the slice joins a contract it provides. Consuming a joined contract is not
    enough: three channels consume one booking API, and only the channel a slice moves takes part in it. The one rule
    behind the handoff, the dashboard's team filter and vela next."""
    from vela import flows, progress
    provided = {app.id: {c.id for c in progress.provided(vault, app) if not c.fact("Provider")} for app in vault.apps}
    out = {}
    for s in found:
        apps, _ = flows.passes_through(vault, s.flows)
        out[s.key] = [app.id for app in vault.apps if app.id in apps or provided[app.id] & set(s.joins)]
    return out


def for_app(vault, found, app):
    """The slices an app takes part in (taking_part), in slice order."""
    part = taking_part(vault, found)
    return [s for s in found if app.id in part[s.key]]


# What moves a slice on from each status, in words for `vela next`. Vela plans and records; the teams run things.
NEXT = {
    "": "is not planned yet: draw its flows, write their case tables and run the flow check on it until it passes "
        "(or each finding has an exception with an end date), then plan it in a grill",
    "planned": "is planned: hand its apps over so each team accepts its part, then set it to building",
    "building": "is building: run its journey in the shared environment and record the result on its page",
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
