"""What every decision writes and checks, whatever it decides (overhaul Task 16; grill section 4). Pure.

The Violation this exists to prevent is a Distributed Monolith across the target kinds. Grill section 4 is nine writes
per decision, and seven of them are the same whether the target is a page, a contract, a requirement, an epic, a
release, a slice or an allocation row: the lead's yes checked, the Decision bullet, the Why copied verbatim, the
Dissent, the Override and Decided by bullets, the Pending approval marker in a reader copy, the `## Changes` row, the
mark on the capture and the agenda line. Written once here, each target kind (`decide_<kind>.py`) holds only what is
its own: where its state lives and what else it needs before it is decided. A fix to the Changes row's grammar then
lands for every kind at once, and `close gate`, which reads that row, agrees with every kind by construction.

Why each write, and why it is code's:

- **The Why is copied verbatim** from the lead's capture (`textedit.inline` escapes only what would break the bullet;
  `textedit.unescape` gives the words back exactly), so it can't be tidied, and it must be a person's words
  (`consent.why_in_their_words`): Claude's recommendation accepted is not the lead's reason (Anchor).
- **The Changes row cites the yes**, `| <ID> | <old state> | <new state> | [[<record>#^cNN]] |`, the row `close gate`
  reads for every change into or out of `decided`. The old state is read from the page, never typed.
- **The deciding capture is marked now** (`→ keep: [[<page>#<heading>|<ID>]] (<state>)`), the one exception to leaving
  marks to close, so close finds the decision already filed.
- **Dissent** is `<who>, <today>: <their words>`, `who` being the capture's origin: someone disagreeing is recorded,
  and the item is still decided.
- **An Override** is written by the `override` kind's own grammar (`decisions.override.bullet_value`), parsed back with
  check's parser before it is returned; a standing rule needs `until`, an event rule takes none, so the rules a lead
  sets aside are split into one bullet of each.
- **Decided by ... on behalf of** goes with a GATE-5 override, as CONVENTIONS "Overrides" says: that is how GATE-5
  passes with the owner away, and the check keeps warning until the owner confirms.
- **Pending approval** in a reader copy: a reader's decision is a proposal that looks settled until an owner has seen
  it (`vela.pending`). Role is known to code, so the marker never depends on the model remembering it.
"""
import re
from dataclasses import dataclass

from vela import gates, override as overrides, schema as vault_schema
from vela.decisions import agenda, consent, override as override_kind, schema, textedit

HANDLE = re.compile(rf"^{vault_schema.HANDLE}$")
STATE_BULLET = re.compile(r"^- \*\*State:\*\*\s*(?P<state>\S*)")
FRONTMATTER_STATE = re.compile(r"^state:\s*(?P<state>.*?)\s*$")
GATE_5 = "GATE-5"
GATE_3 = "GATE-3"
REOPENED = "reopened"


@dataclass(frozen=True)
class Target:
    """What a kind found for an ID: where it lives, what it is called and where it stands now.

    `history` is "" for a page-level item (its bullets go directly under `## History`) or the ID whose `#### <ID>` they
    go under; `anchor` the heading the capture's keep mark links; `override_on` the ID an Override bullet is written
    for; `gate` the ID `gates.verdict` judges, "" when the gate has no view of the target (a release, a row)."""
    kind: str
    id: str
    path: str
    name: str
    state: str
    history: str
    anchor: str
    override_on: str
    gate: str = ""


def refusal(rule, plain, fix, override="the lead's override of that rule, with their reason, then decide again"):
    return textedit.refusal(rule, plain, fix, override=override)


# --- reading and setting a state ------------------------------------------------------------------------------------

def item_block(lines, ident):
    """(start, end) of `### <ident> ...` and what sits under it, or None."""
    pattern = re.compile(rf"^#{{2,3}} {re.escape(ident)}(?: |$)")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        return None
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    return start, textedit.section_end(lines, start, level)


def bullet_state(lines):
    for line in lines:
        found = STATE_BULLET.match(line)
        if found:
            return found["state"]
    return ""


def set_bullet_state(lines, start, end, state):
    """`lines` with the first `- **State:**` bullet in [start, end) set to `state`; None when there is none."""
    for index in range(start, end):
        if STATE_BULLET.match(lines[index]):
            out = list(lines)
            out[index] = f"- **State:** {state}"
            return out
    return None


def set_item_state(text, ident, state):
    lines = text.rstrip("\n").split("\n")
    start, end = item_block(lines, ident)
    return "\n".join(set_bullet_state(lines, start, end, state)) + "\n"


def frontmatter_state(text):
    return str(textedit.meta_of(text).get("state") or "").strip()


def set_frontmatter_state(text, state):
    lines = text.split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    for index in range(1, end):
        if FRONTMATTER_STATE.match(lines[index]):
            lines[index] = f"state: {state}"
            return "\n".join(lines)
    return "\n".join(lines[:end] + [f"state: {state}"] + lines[end:])


def item_target(view, ident, kind):
    """A Target for a `### <ID> <name>` item with a `**State:**` bullet (a contract, a requirement)."""
    found = textedit.find(view, ident)
    if found is None or found[1] is None:
        return None
    path, heading = found
    lines = view.text(path).split("\n")
    start, end = item_block(lines, ident)
    return Target(kind, ident, path, textedit.name_of(view, ident), bullet_state(lines[start:end]), ident, heading,
                  ident, ident)


def page_target(view, ident, kind):
    """A Target for a page whose frontmatter `id` is `ident`."""
    found = textedit.find(view, ident)
    if found is None or found[1] is not None:
        return None
    path = found[0]
    text = view.text(path)
    return Target(kind, ident, path, textedit.name_of(view, ident), frontmatter_state(text), "",
                  textedit.title_heading(text), ident, ident)


# --- what the record must hold --------------------------------------------------------------------------------------

def rules_set_aside(item):
    return {str(rule) for group in (item.get("overrides") or []) for rule in (group.get("rules") or [])}


def yes_refusals(item, record):
    """The lead's yes to the read-back: there, a person's, not a bare "ok", after the read-back."""
    missing = [name for name in ("readback", "yes") if not item.get(name)]
    if missing:
        return [refusal("decide-unfilled", "I still need your yes to the read-back before I can write that down.",
                        f"Give {' and '.join('--' + m for m in missing)}: the read-back capture and the lead's yes "
                        "after it.", override="none: a decision needs a yes on record, or the lead's override of "
                                              f"{closegate_rule()}")]
    found = consent.a_yes(item["yes"], record, readback=item["readback"])
    return [found] if found else []


def closegate_rule():
    from vela import closegate
    return closegate.QUOTED_YES_RULE


def words_refusals(item, record):
    """The Why must be the lead's words; a Dissent someone's (a person's) words."""
    found = []
    if item.get("why"):
        why = consent.why_in_their_words(item["why"], record)
        if why is not None:
            found.append(why)
    if item.get("dissent"):
        missing = consent.exists(item["dissent"], record)
        capture = record.capture(item["dissent"])
        if missing is not None:
            found.append(missing)
        elif not capture.is_person:
            found.append(refusal("decide-dissent-not-theirs", "A disagreement goes down in the words of whoever "
                                                              "disagrees, not mine.",
                                 f"Capture the dissent in the dissenter's words with them as origin (^c{capture.n} is "
                                 f"Claude's, origin {capture.origin!r}).", override="leave the dissent out"))
    return found


def override_items(item, target):
    """The `override` kind's items for this decision: one per group the lead set aside, `on` the target."""
    out = []
    for group in item.get("overrides") or []:
        rules = [str(r) for r in (group.get("rules") or [])]
        one = {"on": target.override_on, "rules": rules, "reason": group.get("reason")}
        if group.get("until"):
            one["until"] = group["until"]
        out.append(one)
    return out


def override_refusals(item, view, record, target):
    found = []
    for one in override_items(item, target):
        if not one.get("reason"):
            found.append(refusal("decide-override-reason", "Setting a rule aside needs your reason, in your words.",
                                 "Give --reason-from: the capture holding the lead's reason.",
                                 override="none: an override always carries the lead's reason"))
            continue
        found += override_kind.validate(one, view, record)
    owners = item.get("on_behalf_of")
    if owners:
        bad = [o for o in str(owners).split() if not HANDLE.match(o)]
        if bad:
            found.append(refusal("decide-on-behalf-handle", "I need the owner's handle to say whose decision this was.",
                                 f"--on-behalf takes handles such as @owner; {', '.join(bad)} is not one.",
                                 override="none: name the owner by handle"))
        if GATE_5 not in rules_set_aside(item):
            found.append(refusal("decide-on-behalf-needs-gate-5",
                                 "Deciding for an owner who isn't here goes on record as your choice, with your reason.",
                                 "Add --override GATE-5 --reason-from <the lead's reason>: deciding on the owner's "
                                 "behalf is how GATE-5 passes with them away (CONVENTIONS \"Overrides\").",
                                 override="none: the GATE-5 override is the record of it"))
    return found + by_refusals(item)


def by_refusals(item):
    if HANDLE.match(str(item.get("by") or "")):
        return []
    return [refusal("decide-by", "I need your handle to say who decided.",
                    f"by {item.get('by')!r} is not a handle; run vela whoami, or capture the yes with the lead's handle "
                    "as origin.", override="none: a decision names who made it")]


def gate_refusals(item, view, record, target):
    """The grill gate's verdict on the target, each reason the lead didn't set aside refused. A flow check that did
    not pass is never set aside here: its findings are covered by the dated overrides the checker itself reads
    (`vela conventions "Flow check"`), which its standing already applies, and "not fully checked" has none."""
    if not target.gate:
        return []
    found = gates.verdict(view.model, record.text, target.gate, textedit.today(view), getattr(view, "flows", None))
    named = rules_set_aside(item)
    out = []
    for reason in found.reasons:
        route = gates.ROUTE_NAMES.get(reason.rule)
        if route is not None and route in named:
            continue
        override = found.route if route is not None else \
            "none from decide: settle each finding, or the dated flow-check override the checker reads"
        out.append(textedit.refusal(reason.rule, reason.plain, reason.fix, override=override))
    return out


# --- the writes -----------------------------------------------------------------------------------------------------

def _override_bullets(item, view, record, target):
    """One bullet per override group, its words checked by check's own parser."""
    from vela.decisions import Refused
    out = []
    for one in override_items(item, target):
        value = override_kind.bullet_value(one, view, record)
        parsed = overrides.parse(value)
        if parsed.problem:
            raise Refused([refusal("override-grammar", "Something went wrong on my side, so I wrote nothing.",
                                   f"vela bug: the override bullet would not parse ({parsed.problem}): {value}",
                                   override="none: this is a fault in vela")])
        out.append(f"- **Override:** {value}")
    return out


def history_bullets(item, view, record, target, decision=True):
    """The bullets a decision adds under `## History`, in CONVENTIONS' order."""
    today = textedit.today(view)
    out = [f"- **Decision:** [[{record.id}]]"] if decision else []
    if item.get("why"):
        out.append(f"- **Why:** {textedit.inline(record.capture(item['why']).quote)}")
    if item.get("dissent"):
        capture = record.capture(item["dissent"])
        out.append(f"- **Dissent:** {capture.origin.strip()}, {today}: {textedit.inline(capture.quote)}")
    out += _override_bullets(item, view, record, target)
    if item.get("on_behalf_of"):
        out.append(f"- **Decided by:** {item['by']}, on behalf of {item['on_behalf_of']}")
    if item.get("reader"):
        out.append(f"- **Pending approval:** {item['by']}, {today}")
    return out


def add_history(text, bullets, target):
    for bullet in bullets:
        text = textedit.add_history(text, bullet, target.history)
    return text


def record_after(item, view, record, target, before, after, cite):
    """The record with the Changes row, the cited capture's keep mark and the agenda line."""
    text = textedit.record_text(record, view)
    text = textedit.add_change(text, textedit.cell(target.id), before or "-", after,
                               textedit.capture_link(record.id, cite))
    mark = textedit.keep_mark(textedit.basename(target.path), target.anchor, target.id, after if after != "-" else
                              "open")
    text = textedit.mark_if_unmarked(text, cite, mark)
    line = agenda.entries(text).get(target.id)
    if line is not None:
        status = "decided" if item.get("reopen") is not True else "open"
        held = tuple(line["override"].split(", ")) if line["override"] else ()
        text = agenda.set_line(text, target.id, agenda.format_line(target.id, line["yes"] == "yes", status, held))
    return text


def writes(target, page_text, record_text_after, view, record):
    out = [schema.Write(target.path, page_text)] if page_text != view.text(target.path) else []
    return out + textedit.record_writes(record, view, record_text_after)
