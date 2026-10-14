"""What needs the lead, as one light per app, contract and flow. Pure: the caller passes the date.

The explorer's map, the gallery's cockpit and transit maps, and later the viewer and the digest all color the
same things by the same rule, so this is the rule. It follows the early-warning scores used on hospital wards:
a subject's light is its single worst sign, never an average, because one overdue answer matters however calm
the rest is. Levels, most urgent first:

  warning     an open question holding it is past its ask-by date, or a slice's journey is past its due date with
              nothing recorded
  caution     not decided yet, or held by an open question
  pending     decided by a reader and not yet reviewed by the owner: an unsettled claim that looks settled
  unexamined  no state recorded, or a concern cell nobody has looked at: dark has to be earned
  override    a rule was set aside by the lead, which is visible but not an alarm
  dark        settled, and nothing holds it

Pending ranks below the two that stop work (an overdue or open blocking question) and above the rest: those
block, this awaits review. A reader's `decided` must not read as the owner's, so it outranks `unexamined`,
`override` and a plain `decided` that is dark.

`urgency` (0 to 1) says how hard a lit subject should glow: 1 is overdue, falling as the ask-by date moves away.
Every light carries its reasons, in words, so a page can say why something is lit.
"""
import datetime
from dataclasses import dataclass, field

from vela import model, override, pending, progress, slices, trace

LEVELS = ("warning", "caution", "pending", "unexamined", "override", "dark")
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


def held_text(unknown, via, who, ask):
    through = " through " + " and ".join([", ".join(via[:-1]), via[-1]] if len(via) > 1 else via) if via else ""
    return f"{unknown.id} {unknown.heading.split(' ', 1)[-1]} holds it{through}; ask {who} by {ask or 'no date'}"


def hold(light, unknown, as_of, via=""):
    """One reason per question on a light. A question can reach a subject several ways (the app's page, and every
    item on that page, which the page block also reaches); listing each way repeated the question. A direct hold says
    it all, so it drops the routes; otherwise the one reason names every route. The level is the question's either way."""
    ask = unknown.fact("Ask by")
    who = unknown.fact("Ask") or unknown.fact("Owner").split(" ")[0]
    seen = next((r for r in light.reasons if r["kind"] == "held" and r.get("unknown") == unknown.id), None)
    if seen is not None:
        if not via:
            seen["via"] = []
        elif seen["via"] and via not in seen["via"]:
            seen["via"].append(via)
        seen["text"] = held_text(unknown, seen["via"], who, ask)
        return
    routes = [via] if via else []
    light.reasons.append({"kind": "held", "unknown": unknown.id, "ask": who, "via": routes, "text": held_text(unknown, routes, who, ask)})
    if not progress.is_date(ask):
        light.raise_to("caution", 0.45)
        return
    left = days_until(as_of, ask)
    if left < 0:
        light.raise_to("warning", 1.0)
    else:
        soon = left <= DUE_SOON_DAYS
        light.raise_to("caution", max(0.25, 1 - left / 30) if soon else min(0.5, max(0.25, 1 - left / 30)))


def question_light(unknown, as_of):
    """The light one open question gives whatever it holds: warning past its ask-by date, caution before.
    Views that draw the questions themselves (strips, markers, buds) color them by this."""
    light = Light()
    hold(light, unknown, as_of)
    return light


def await_review(light, marker):
    """Light a subject whose decision a reader made and no owner has reviewed. `marker` is a pending.Pending or None."""
    if marker is None:
        return
    light.reasons.append({"kind": "pending", "by": marker.by, "date": marker.date,
                          "text": f"pending approval: decided by {marker.by} on {marker.date}, not yet reviewed by the owner"})
    light.raise_to("pending", 0.4)


def settle(light, state, unexamined=(), overrides=(), marker=None):
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
    await_review(light, marker)


def lights(vault, as_of):
    """{subject id: Light} for every app page, contract and flow, each slice whose journey is overdue, and "above":
    open questions that hold something not on a map (the strategy, a goal, another question), so a page can show them
    instead of dropping them."""
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
        settle(light, str(app.meta.get("state") or ""), [str(c.concern.meta.get("title") or c.concern.id) for c in cells], override.valid_overrides(app),
               pending.pending_for(app))
    for contract in vault.contracts:
        light = out.setdefault(contract.id, Light())
        for unknown in blockers.get(contract.id, []):
            hold(light, unknown, as_of)
        for epic in epics:
            if contract.id in trace.listed(epic, "delivers") + trace.listed(epic, "consumes"):
                for unknown in blockers.get(epic.id, []):
                    hold(light, unknown, as_of, via=epic.id)
        settle(light, contract.fact("State"), (), override.valid_overrides(contract.page, contract.id),
               pending.pending_for(contract.page, contract.id))
    stale = stale_by_page(vault)
    for flow in vault.of_type("flow"):
        light = out.setdefault(flow.id, Light())
        for unknown in blockers.get(flow.id, []):
            hold(light, unknown, as_of)
        for line, unknown_id in stale.get(flow.path, []):
            light.reasons.append({"kind": "stale", "unknown": unknown_id,
                                  "text": f"line {line} reads {unknown_id} as open; the record says resolved"})
            light.raise_to("caution", 0.35)
        settle(light, str(flow.meta.get("state") or ""), marker=pending.pending_for(flow))
    for s in slices.read_slices(vault):  # a journey past its due date with nothing recorded needs the lead
        if s.id and slices.journey_overdue(s, as_of):
            light = out.setdefault(s.id, Light())
            light.reasons.append({"kind": "journey-due", "text": slices.journey_overdue_says(s)})
            light.raise_to("warning", 1.0)
    for marker in pending.items(vault):  # a reader's decision on any other page or item is lit too
        subject = marker.item or next((p.id for p in vault.pages if p.path == marker.path), "")
        if subject and subject not in out:
            await_review(out.setdefault(subject, Light()), marker)
    shown = {r["unknown"] for light in out.values() for r in light.reasons if r.get("unknown")}
    above = []
    for unit_id, unknowns in blockers.items():
        for unknown in unknowns:
            if unknown.id not in shown and unit_id not in out:
                above.append({"unknown": unknown.id, "holds": unit_id, "ask_by": unknown.fact("Ask by")})
    return out, sorted(above, key=lambda a: (a["ask_by"] or "9999", a["unknown"]))


def stale_by_page(vault):
    """{page path: [(line, unknown id)]} from W334, the sentences that call an answered question open."""
    from vela import rules
    out = {}
    for finding in rules.stale_mention_rules(vault, None):
        unknown_id = next((w for w in finding.message.replace(",", " ").split() if w.startswith("UNK-")), "")
        out.setdefault(finding.path, []).append((finding.line, unknown_id))
    return out


def ranked(found):
    """Lit subjects, most urgent first: by level, then urgency, then ID."""
    lit = [(subject, light) for subject, light in found.items() if light.level != "dark"]
    return sorted(lit, key=lambda p: (LEVELS.index(p[1].level), -p[1].urgency, p[0]))
