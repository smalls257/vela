"""One team's epics frontier: the traceability gaps that are its work, the counts the epics skill paces by, and whether
its first epic sits on the tracer (CLI/skill overhaul, Task 21e). Pure: a built vault in, a Frontier out.

Why it is code: the epics skill read the `traceability` block on `13-epics/13-epics.md` by eye, picked out one team's
rows, counted epics and criteria for pacing, and compared the first epic's `flows:` with release one's tracer. Each step
is a lookup, and a model doing a lookup by eye gets the team wrong or the count wrong (Paper Tiger: the frontier said
"done" while another team's gap was mistaken for this one's). So this module answers, and the skill keeps the judgment:
which cuts to offer, and what comes first when the first epic is not on the tracer (that is not a fault).

The Violation its shape prevents is a Distributed Monolith: the gaps come from `trace.report`, the one computation the
check and the render already share, and a team's share of them is `rules.scope_to_app`, the same filter
`vela check --gate epics --app` applies. Nothing here re-derives a gap, so the frontier and the gate never disagree.

- A team is an `owner:` handle on app pages (the epics skill, section 2), and also the `owner:` of an epic.
- Its epics are the ones it owns, and the ones that list one of its apps.
- Only T1, T2, T4 and T6 are the epics frontier. T7 (a requirement no app carries) belongs to allocate, not to a team.
- A gap no team's filter keeps (a capability no allocation row carries, say) is in nobody's frontier, as it is in no
  `--app` gate. It is listed as `unowned` on every team's frontier, so narrowing to a team never makes it vanish
  (Silent Fallback: a gap dropped by the filter would read as "this team is done").
- The tracer is `slices.tracer`: the tracer slice's flows, or release one's `**Tracer:**` flows while the vault has no
  slice pages. The first epic is the team's lowest-numbered one; it is on the tracer when its `flows:` names one of them.
"""
from dataclasses import dataclass

from vela import criteria, rules, slices, trace

FRONTIER_RULES = ("T1", "T2", "T4", "T6")
# What each rule means, in the lead's words, for the pacing line ("2 capabilities nobody delivers").
RULE_WORDS = {"T1": "capabilities nobody delivers", "T2": "contracts no epic builds",
              "T4": "concern cells with work and no marked criterion", "T6": "epics that deliver nothing"}


class UnknownTeam(ValueError):
    """No app page and no epic names this handle as its owner. `known` lists the handles that do."""

    def __init__(self, team, known):
        self.team, self.known = team, tuple(known)
        super().__init__(f"no app page or epic is owned by {team}")


@dataclass(frozen=True)
class Tracer:
    state: str  # "on", "off", "no-tracer" (the vault names no tracer flows) or "no-epic" (the team has none yet)
    epic: str = ""  # the team's first epic
    epic_title: str = ""
    epic_flows: tuple = ()
    tracer_name: str = ""  # the tracer slice, or release one's heading
    tracer_flows: tuple = ()
    on_tracer: tuple = ()  # the first epic's flows that are tracer flows


@dataclass(frozen=True)
class Frontier:
    team: str
    apps: tuple  # (id, title) of the team's apps
    epics: tuple  # (id, title) of the team's epics, by ID
    criteria: int  # criteria on those epics, struck ones left out
    gaps: tuple  # trace.Gap, T1/T2/T4/T6 only, the team's share
    tracer: Tracer
    unowned: tuple = ()  # trace.Gap no team's share holds

    def count(self, rule):
        return sum(1 for g in self.gaps if g.rule == rule)


def handle(value):
    """'"@Sim-Lead"' and 'sim-lead' both read as '@sim-lead'."""
    text = str(value or "").strip().strip("\"'").strip().lower()
    return text if not text or text.startswith("@") else f"@{text}"


def title(page):
    value = page.meta.get("title")
    return str(value).strip() if value else page.id


def teams(vault):
    """Every handle that owns an app page or an epic, in order."""
    found = {handle(p.meta.get("owner")) for p in list(vault.apps) + trace.epics(vault)}
    return sorted(h for h in found if h)


def team_apps(vault, team):
    return [a for a in sorted(vault.apps, key=lambda p: p.id) if handle(a.meta.get("owner")) == team]


def team_epics(vault, team, apps):
    ids = {a.id for a in apps}
    return [e for e in trace.epics(vault)
            if handle(e.meta.get("owner")) == team or ids & set(trace.listed(e, "apps"))]


def frontier_gaps(vault):
    return [g for g in trace.report(vault).gaps if g.rule in FRONTIER_RULES]


def keeper(vault, apps, epics):
    """Whether a gap is the team's: what `--gate epics --app` keeps for any of its apps, plus its own epics."""
    filters = [rules.scope_to_app(vault, app)[0] for app in apps]
    mine = {e.id for e in epics}
    return lambda g: g.subject in mine or any(keep(g) for keep in filters)


def unowned(vault, gaps):
    keepers = []
    for team in teams(vault):
        apps = team_apps(vault, team)
        keepers.append(keeper(vault, apps, team_epics(vault, team, apps)))
    return tuple(g for g in gaps if not any(keep(g) for keep in keepers))


def tracer_of(vault, epics):
    found = slices.tracer(slices.read_slices(vault))
    flows = tuple(found.flows) if found is not None else ()
    if not epics:
        return Tracer("no-epic", tracer_name=found.name if found else "", tracer_flows=flows)
    first = epics[0]
    epic_flows = tuple(trace.listed(first, "flows"))
    base = dict(epic=first.id, epic_title=title(first), epic_flows=epic_flows,
                tracer_name=found.name if found else "", tracer_flows=flows)
    if not flows:
        return Tracer("no-tracer", **base)
    on = tuple(f for f in epic_flows if f in flows)
    return Tracer("on" if on else "off", on_tracer=on, **base)


def frontier(vault, team):
    """The team's frontier. Raises UnknownTeam when nothing in the vault is owned by `team`."""
    team = handle(team)
    apps = team_apps(vault, team)
    epics = team_epics(vault, team, apps)
    if not apps and not epics:
        raise UnknownTeam(team, teams(vault))
    count = sum(1 for e in epics for c in criteria.read(e) if not c.struck)
    gaps = frontier_gaps(vault)
    mine = keeper(vault, apps, epics)
    return Frontier(team, tuple((a.id, title(a)) for a in apps), tuple((e.id, title(e)) for e in epics), count,
                    tuple(g for g in gaps if mine(g)), tracer_of(vault, epics), unowned(vault, gaps))
