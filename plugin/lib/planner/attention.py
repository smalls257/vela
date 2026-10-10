"""What needs the lead, as one light per app, contract and flow. Pure: the caller passes the date.

The explorer's map, the gallery's cockpit and transit maps, and later the viewer and the digest all colour the
same things by the same rule, so this is the rule. It follows the early-warning scores used on hospital wards:
a subject's light is its single worst sign, never an average, because one overdue answer matters however calm
the rest is. Levels, most urgent first:

  warning     an open question holding it is past its ask-by date
  caution     not decided yet, or held by an open question
  unexamined  no state recorded, or a concern cell nobody has looked at: dark has to be earned
  override    a rule was set aside by the lead, which is visible but not an alarm
  dark        settled, and nothing holds it

`urgency` (0 to 1) says how hard a lit subject should glow: 1 is overdue, falling as the ask-by date moves away.
Every light carries its reasons, in words, so a page can say why something is lit.
"""
import datetime
from dataclasses import dataclass, field

from planner import model, override, progress, trace

LEVELS = ("warning", "caution", "unexamined", "override", "dark")
SETTLED = ("decided", "fact")
DUE_SOON_DAYS = 7


@dataclass
class Light:
    level: str = "dark"
    urgency: float = 0.0
    reasons: list = field(default_factory=list)  # {"kind", "text", and "unknown" when a question is behind it}

    def raise_to(self, level, urgency):
        if LEVELS.index(level) < LEVELS.index(self.level):
            self.level = level
        self.urgency = round(max(self.urgency, urgency), 2)

    def as_dict(self):
        return {"level": self.level, "urgency": self.urgency, "reasons": list(self.reasons)}


def days_until(as_of, date):
    return (datetime.date.fromisoformat(date) - datetime.date.fromisoformat(as_of)).days


def hold(light, unknown, as_of, via=""):
    ask = unknown.fact("Ask by")
    through = f" through {via}" if via else ""
    who = unknown.fact("Ask") or unknown.fact("Owner").split(" ")[0]
    light.reasons.append({"kind": "held", "unknown": unknown.id, "ask": who,
                          "text": f"{unknown.id} {unknown.heading.split(' ', 1)[-1]} holds it{through}; ask {who} by {ask or 'no date'}"})
    if not progress.is_date(ask):
        light.raise_to("caution", 0.45)
        return
    left = days_until(as_of, ask)
    if left < 0:
        light.raise_to("warning", 1.0)
    else:
        soon = left <= DUE_SOON_DAYS
        light.raise_to("caution", max(0.25, 1 - left / 30) if soon else min(0.5, max(0.25, 1 - left / 30)))


def settle(light, state, unexamined=(), overrides=()):
    if not state:
        light.reasons.append({"kind": "unexamined", "text": "no state recorded"})
        light.raise_to("unexamined", 0.5)
    elif state not in SETTLED:
        light.reasons.append({"kind": "state", "text": f"still at {state}"})
        light.raise_to("caution", 0.4)
    for concern in unexamined:
        light.reasons.append({"kind": "unexamined", "text": f"{concern} never examined"})
        light.raise_to("unexamined", 0.5)
    for o in overrides:
        light.reasons.append({"kind": "override", "text": f"override of {', '.join(o.rules)} by {o.by}"})
        light.raise_to("override", 0.15)


def lights(vault, as_of):
    """{subject id: Light} for every app page, contract and flow, and "above": open questions that hold
    something not on a map (the strategy, a goal, another question), so a page can show them instead of
    dropping them."""
    blockers = model.blockers(vault)
    out = {}
    epics = trace.epics(vault)
    for app in vault.apps:
        light = out.setdefault(app.id, Light())
        for unknown in model.blocking_unknowns(vault, app):
            hold(light, unknown, as_of)
        for item_id in {i.id for items in vault.items.values() for i in items if i.page is app}:
            for unknown in blockers.get(item_id, []):
                hold(light, unknown, as_of, via=item_id)
        for epic in epics:
            if app.id in trace.listed(epic, "apps"):
                for unknown in blockers.get(epic.id, []):
                    hold(light, unknown, as_of, via=epic.id)
        cells = [c for c in vault.cells if c.app.lower() == app.name.lower() and c.state == "unexamined"]
        settle(light, str(app.meta.get("state") or ""), [c.concern.id for c in cells], override.valid_overrides(app))
    for contract in vault.contracts:
        light = out.setdefault(contract.id, Light())
        for unknown in blockers.get(contract.id, []):
            hold(light, unknown, as_of)
        for epic in epics:
            if contract.id in trace.listed(epic, "delivers") + trace.listed(epic, "consumes"):
                for unknown in blockers.get(epic.id, []):
                    hold(light, unknown, as_of, via=epic.id)
        settle(light, contract.fact("State"), (), override.valid_overrides(contract.page, contract.id))
    stale = stale_by_page(vault)
    for flow in vault.of_type("flow"):
        light = out.setdefault(flow.id, Light())
        for unknown in blockers.get(flow.id, []):
            hold(light, unknown, as_of)
        for line, unknown_id in stale.get(flow.path, []):
            light.reasons.append({"kind": "stale", "unknown": unknown_id,
                                  "text": f"line {line} reads {unknown_id} as open; the record says resolved"})
            light.raise_to("caution", 0.35)
        settle(light, str(flow.meta.get("state") or ""))
    shown = {r["unknown"] for light in out.values() for r in light.reasons if r.get("unknown")}
    above = []
    for unit_id, unknowns in blockers.items():
        for unknown in unknowns:
            if unknown.id not in shown and unit_id not in out:
                above.append({"unknown": unknown.id, "holds": unit_id, "ask_by": unknown.fact("Ask by")})
    return out, sorted(above, key=lambda a: (a["ask_by"] or "9999", a["unknown"]))


def stale_by_page(vault):
    """{page path: [(line, unknown id)]} from W334, the sentences that call an answered question open."""
    from planner import rules
    out = {}
    for finding in rules.stale_mention_rules(vault, None):
        unknown_id = next((w for w in finding.message.replace(",", " ").split() if w.startswith("UNK-")), "")
        out.setdefault(finding.path, []).append((finding.line, unknown_id))
    return out


def ranked(found):
    """Lit subjects, most urgent first: by level, then urgency, then ID."""
    lit = [(subject, light) for subject, light in found.items() if light.level != "dark"]
    return sorted(lit, key=lambda p: (LEVELS.index(p[1].level), -p[1].urgency, p[0]))
