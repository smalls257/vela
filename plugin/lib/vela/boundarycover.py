"""Which requirements each proposed cut carries whole, splits across apps, or leaves with no app. Pure.

Boundary offers the ways to cut a decided direction into apps and tests each against the functional
requirements (boundary skill, section 2). The test is a count: for every requirement, how many of the cut's apps say
they carry it. One app: carried whole. Two or more: split, and the crossing needs a contract, which is a cost the
lead weighs. None: nobody builds it, also a cost. Done by hand, the model miscounted and the lead heard a tally that
did not match the pages; the trade-offs between cuts stay judgment, the count is code.

The Violation this shape prevents is the Leaky Narrative: the skill used to walk the model through every capability
page and every app's share in prose, and the IDs it counted with reached the lead. Here the skill hands over one cut
file and gets back the three lists per cut, with every requirement said by its name in `--for-lead`.

The cut file (JSON, version 1). Apps of a cut do not have pages yet, so a new app is named in words; an app that
already has a page is named by its ID and said by its page's title:

    {"version": 1,
     "cuts": [
       {"name": "One desktop agent",
        "apps": [
          {"name": "Desktop agent", "change": "new", "carries": ["CAP-001", "CAP-002.FR1"]},
          {"app": "APP-consent-and-identity", "change": "integrated", "carries": ["CAP-005.FR1"]}]}]}

- `carries` lists capabilities (`CAP-001`: every requirement under it) and single requirements (`CAP-001.FR2`).
- `change` is optional; when given it is one of new, changed, integrated, unchanged, retired.
- Cut and app names are said to the lead, so they are words, never IDs, and no name appears twice.

No disk, git or clock: the caller reads the file and the vault and passes in the text, the requirement names and the
existing apps' names.
"""
import json
import re
from dataclasses import dataclass

from vela import say

CUT_VERSION = 1
CHANGES = ("new", "changed", "integrated", "unchanged", "retired")
CAPABILITY = re.compile(r"^CAP-\d{3}$")
REQUIREMENT = re.compile(r"^CAP-\d{3}\.FR\d+$")
FIX = "Correct the cut file and run vela boundary cover again; vela boundary cover --help shows its shape."


class CutError(Exception):
    """The cut file does not validate. `plain` says why in words a lead can hear; `fix` is what the model does."""

    def __init__(self, plain, fix=FIX):
        self.plain, self.fix = plain, fix
        super().__init__(plain)


@dataclass(frozen=True)
class AppShare:
    name: str  # what the lead hears
    app: str  # the existing app's ID, or "" for an app the cut proposes
    change: str
    carries: frozenset  # requirement IDs


@dataclass(frozen=True)
class Cut:
    name: str
    apps: tuple


@dataclass(frozen=True)
class Coverage:
    cut: Cut
    whole: tuple  # ((requirement, app name), ...)
    split: tuple  # ((requirement, (app name, ...)), ...)
    uncarried: tuple  # (requirement, ...)

    def as_json(self, names):
        return {"name": self.cut.name,
                "apps": [{"name": a.name, "app": a.app, "change": a.change, "carries": sorted(a.carries)}
                         for a in self.cut.apps],
                "whole": [{"requirement": r, "name": names.get(r, ""), "app": app} for r, app in self.whole],
                "split": [{"requirement": r, "name": names.get(r, ""), "apps": list(apps)} for r, apps in self.split],
                "uncarried": [r for r in self.uncarried]}


def parse_cut(text, requirements, apps):
    """[Cut] from the cut file's text. `requirements` is {requirement ID: name}, `apps` {existing app ID: name}.
    Raises CutError with a plain reason on the first thing that does not validate."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise CutError(f"The cut file is not JSON ({exc}).") from exc
    if not isinstance(data, dict) or data.get("version") != CUT_VERSION:
        found = data.get("version") if isinstance(data, dict) else None
        raise CutError(f"The cut file is version {found}; vela reads cut files of version {CUT_VERSION}.")
    cuts = data.get("cuts")
    if not isinstance(cuts, list) or not cuts:
        raise CutError('The cut file must list at least one cut under "cuts".')
    found = [_cut(entry, n, requirements, apps) for n, entry in enumerate(cuts, 1)]
    _unique([c.name for c in found], "A cut")
    return found


def _cut(entry, n, requirements, apps):
    if not isinstance(entry, dict):
        raise CutError(f"Cut {n} in the file is not an object with a name and apps.")
    name = _words(entry.get("name"), f"Cut {n}")
    shares = entry.get("apps")
    if not isinstance(shares, list) or not shares:
        raise CutError(f'The cut "{name}" names no apps.')
    out = tuple(_share(share, name, requirements, apps) for share in shares)
    _unique([a.name for a in out], f'In the cut "{name}", an app')
    return Cut(name, out)


def _share(entry, cut, requirements, apps):
    if not isinstance(entry, dict):
        raise CutError(f'An app in the cut "{cut}" is not an object with a name and what it carries.')
    ident = entry.get("app") or ""
    if not isinstance(ident, str):
        raise CutError(f'An app in the cut "{cut}" gives "app" as something other than an app ID.')
    if ident:
        if ident not in apps:
            raise CutError(f'The cut "{cut}" names {ident}, and the vault has no app page with that ID. '
                           'Name an app the vault does not have yet by "name", in words.')
        name = apps[ident]
    else:
        name = _words(entry.get("name"), f'An app in the cut "{cut}"')
    change = entry.get("change") or ""
    if change and change not in CHANGES:
        raise CutError(f'The app "{name}" in the cut "{cut}" has change "{change}"; it must be one of '
                       f"{', '.join(CHANGES)}.")
    carries = entry.get("carries", [])
    if not isinstance(carries, list) or not all(isinstance(c, str) for c in carries):
        raise CutError(f'What the app "{name}" in the cut "{cut}" carries must be a list of capability or '
                       "requirement IDs.")
    return AppShare(name, ident, change, frozenset(r for c in carries for r in _expand(c.strip(), requirements)))


def _expand(ident, requirements):
    """The requirement IDs one `carries` entry stands for."""
    if REQUIREMENT.match(ident) and ident in requirements:
        return [ident]
    if CAPABILITY.match(ident):
        under = [r for r in requirements if r.split(".")[0] == ident]
        if under:
            return under
    raise CutError(f"The cut file names {ident}, and the vault has no capability or requirement with that ID.")


def _words(value, who):
    if not isinstance(value, str) or not value.strip():
        raise CutError(f"{who} has no name.")
    if say.leak_in(value):
        raise CutError(f'{who} is called "{value}". Names are said to the lead, so give it a name in words, '
                       "with no ID in it.")
    return value.strip()


def _unique(names, who):
    seen = set()
    for name in names:
        if name.lower() in seen:
            raise CutError(f'{who} called "{name}" appears twice; give each its own name.')
        seen.add(name.lower())


def cover(cuts, requirement_ids):
    """[Coverage] per cut, each list in `requirement_ids` order; a split names its apps in the cut's order."""
    out = []
    for cut in cuts:
        whole, split, uncarried = [], [], []
        for req in requirement_ids:
            holders = tuple(a.name for a in cut.apps if req in a.carries)
            if not holders:
                uncarried.append(req)
            elif len(holders) == 1:
                whole.append((req, holders[0]))
            else:
                split.append((req, holders))
        out.append(Coverage(cut, tuple(whole), tuple(split), tuple(uncarried)))
    return out


def summary(coverage):
    return (f"{coverage.cut.name}: {len(coverage.whole)} whole, {len(coverage.split)} split, "
            f"{len(coverage.uncarried)} carried by no app.")


def summary_words(coverage):
    """One cut's count the way the lead hears it: whole first, then the costs, each count in words."""
    total = len(coverage.whole) + len(coverage.split) + len(coverage.uncarried)
    costs = []
    if coverage.split:
        costs.append(f"splits {say.count_words(len(coverage.split))} across apps (each needs a contract)")
    if coverage.uncarried:
        costs.append(f"leaves {say.count_words(len(coverage.uncarried))} with no app")
    head = f"{coverage.cut.name} carries {say.count_words(len(coverage.whole))} of {say.count_words(total)} " \
           f"requirements whole"
    if not costs:
        return f"{head}."
    return f"{head} and {costs[0]}." if len(costs) == 1 else f"{head}, {costs[0]}, and {costs[1]}."


def lines(coverages, names):
    """say.Lines: first one summary line per cut so the cuts read side by side (the answer, voice audit row 212);
    then per cut the costs (split, then carried by no app) and what one app carries whole, which the lead hears
    after about four things only when they want them. `text` keeps the IDs for files; `plain` says each requirement
    by its name."""
    out = [say.Line("Side by side:", plain="")]
    out += [say.Line(f"- {summary(c)}", summary_words(c)) for c in coverages]
    for c in coverages:
        out.append(say.Line(f"Cut: {c.cut.name} ({', '.join(a.name for a in c.cut.apps)})"))
        for req, apps in c.split:
            out.append(say.Line(f"  split, needs a contract: {req} {names[req]}, across {_and(apps)}",
                                f"  split across {_and(apps)}, so it needs a contract: {names[req]}"))
        for req in c.uncarried:
            out.append(say.Line(f"  carried by no app: {req} {names[req]}", f"  carried by no app: {names[req]}"))
        for req, app in c.whole:
            out.append(say.Line(f"  whole: {req} {names[req]}, by {app}", f"  carried whole by {app}: {names[req]}"))
    return out


def _and(names):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
