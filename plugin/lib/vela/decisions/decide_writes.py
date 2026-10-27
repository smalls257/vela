"""What every decision writes and checks, whatever it decides (overhaul Task 16; grill's "File each decision as its branch closes"). Pure.

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
  (`consent.why_in_their_words`): Claude's recommendation accepted is not the lead's reason (Anchor). The notes stay
  on the lead's machine, so a Why, a Dissent or a receipt carries a person's words only when they are the lead's or
  that person said in this session they may be quoted (`consent.may_quote`); the rest stays in the private notes.
- **The Changes row cites the yes**, `| <ID> | <old state> | <new state> | [[<record>#^cNN]] |`, the row `close gate`
  reads for every change into or out of `decided`. The old state is read from the page, never typed.
- **The deciding capture is marked now** (`→ keep: [[<page>#<heading>|<ID>]] (<state>)`), the one exception to leaving
  marks to close, and so is every other capture the decision filed (the Why, the Dissent, the provider's
  standing, each override's reason), so close finds nothing of the decision left to place.
- **Dissent** is `<who>, <today>`, with `: "<their words>"` only when that person may be quoted (`receipts`), `who`
  being the capture's origin: someone disagreeing is recorded, and the item is still decided.
- **The Decision receipt** names the session, the capture of the yes and who said it (`receipts.decision_value`).
- **An Override** is written by the `override` kind's own grammar (`decisions.override.bullet_value`), parsed back with
  check's parser before it is returned; a standing rule needs `until`, an event rule takes none, so the rules a lead
  sets aside are split into one bullet of each.
- **Decided by ... on behalf of** is written whenever the yes isn't the owner's own (`stand_in_owners`): the lead's yes
  settles any item, with no refusal, no override and no warning.
- **Pending approval** in a reader copy: a reader's decision is a proposal that looks settled until an owner has seen
  it (`vela.pending`). Role is known to code, so the marker never depends on the model remembering it.
"""
import re
from dataclasses import dataclass

from vela import gates, override as overrides, privaterecord, receipts, said, say, schema as vault_schema
from vela.decisions import agenda, consent, options_line, override as override_kind, schema, textedit

HANDLE = re.compile(rf"^{vault_schema.HANDLE}$")
STATE_BULLET = re.compile(r"^- \*\*State:\*\*\s*(?P<state>\S*)")
FRONTMATTER_STATE = re.compile(r"^state:\s*(?P<state>.*?)\s*$")
# What the lead hears once when a gate rule that takes no end date (the stage, the options, the agenda's or the owner's
# yes) could be set aside: it holds at the moment of deciding, so an exception is a reason, not a period.
EVENT_WAIVER = "It's your call: I can decide it anyway and note your reason."
GATE_3 = "GATE-3"
# The one grill rule a decision a source states skips: a decision picks between options Shape wrote down, and the
# document records a choice already made. Every other reason (the stage, an open question, a contract's case table)
# still holds, because a stated decision can still be blocked or unfinished.
STATED_SKIPS = "GATE-2"
REOPENED = "reopened"
DECLINED = "declined"


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


def refusal(rule, plain, fix, override="the lead's override of that rule, with their reason, then decide again",
            audience=say.LEAD):
    return textedit.refusal(rule, plain, fix, override=override, audience=audience)


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
    """The lead's yes: there, a person's, not a bare "ok"."""
    if closegate_rule() in rules_set_aside(item) and not item.get("yes"):
        return []  # the lead's override of the quoted-yes rule is the record of going ahead; no yes to check
    if not item.get("yes"):
        return [refusal("decide-unfilled", "I still need your yes before I can write that down.",
                        "Give --yes: the capture holding the lead's yes.",
                        override=f"none: a decision needs a yes on record, or the lead's override of {closegate_rule()}")]
    found = consent.a_yes(item["yes"], record)
    return [found] if found else []


def closegate_rule():
    from vela import closegate
    return closegate.QUOTED_YES_RULE


def lead_unknown():
    return refusal("decide-lead-unknown", "I don't know your GitHub handle yet, so I can't put your words on record. "
                                          "What's the short name after the @?",
                   "Ask the lead once, run vela whoami --set <handle>, then decide again.",
                   override="none: whose words go on record is checked against the lead's handle")


def words_refusals(item, view, record):
    """The Why must be words that may go on a page; a Dissent a person's (its words go out only with theirs)."""
    lead = getattr(view, "lead", None)
    if lead is None:
        return [lead_unknown()]
    found = []
    if item.get("why"):
        why = consent.why_in_their_words(item["why"], record, lead)
        if why is not None:
            found.append(why)
    if item.get("options_none"):
        missing = consent.exists(item["options_none"], record)
        if missing is not None:
            found.append(missing)
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
    return found + speaker_refusals(item, record, lead)


def speaker_refusals(item, record, lead):
    """A yes or dissent from someone whose origin is a display name ("Raj Patel") can't go on a page as `@who`: E315
    would fail it later, when the fix is no longer at hand. Stop here, with the capture to fix."""
    out = []
    for name in ("yes", "dissent"):
        ref = item.get(name)
        if not ref or consent.exists(ref, record) is not None:
            continue
        capture = record.capture(ref)
        who = speaker(capture, lead)
        if capture.is_person and not receipts.is_handle(who):
            out.append(refusal("decide-speaker-not-handle", f"I don't have a handle for {who}, so I can't name them "
                                                            "on the record.",
                               f"Re-capture ^c{capture.n} with their handle (like @raj) as origin, or ask them for it, "
                               "then decide again.", override="leave the dissent out" if name == "dissent" else
                               "none: the receipt has to name who said yes"))
    return out


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
            found.append(refusal("decide-override-reason", "Why set it aside? In your words, so I can note it.",
                                 "Give --reason-from: the capture holding the lead's reason.",
                                 override="none: an override always carries the lead's reason"))
            continue
        found += override_kind.validate(one, view, record)
    return found + by_refusals(item)


def by_refusals(item):
    if HANDLE.match(str(item.get("by") or "")):
        return []
    return [refusal("decide-by", "I need your handle to say who decided.",
                    f"by {item.get('by')!r} is not a handle; run vela whoami, or capture the yes with the lead's handle "
                    "as origin.", override="none: a decision names who made it", audience=say.MODEL)]


OWNER_HANDLES = re.compile(r"@[\w][\w./-]*")


def owners_of(view, target):
    """The handles on the target's `**Owner:**` bullet (an item) or `owner:` field (a page); () when it names none."""
    found = view.model.item(target.id)
    if found is not None:
        text = found.fact("Owner")
    else:
        pages = view.model.by_id.get(target.id) or []
        text = str(pages[0].meta.get("owner") or "") if pages else ""
    return tuple(OWNER_HANDLES.findall(text))


def stand_in_owners(item, view, record, target):
    """The owners' handles when the lead's yes settles an item someone else owns, else (): the lead's yes settles any
    item, so nothing is refused, but a decision that isn't the owner's own is never filed as if it were (Silent
    Fallback of consent otherwise). It is written as `Decided by ... on behalf of`, which the owner can confirm or
    challenge later."""
    owners = owners_of(view, target)
    if not owners or item.get("reopen") or not item.get("yes") or consent.exists(item["yes"], record) is not None:
        return ()
    who = speaker(record.capture(item["yes"]), getattr(view, "lead", None))
    if any(consent.same_handle(who, owner) for owner in owners):
        return ()
    return owners


def gate_refusals(item, view, record, target):
    """The grill gate's verdict on the target, each reason the lead didn't set aside refused. A flow check that did
    not pass is never set aside here: its findings are covered by the dated overrides the checker itself reads
    (`vela conventions "Flow check"`), which its standing already applies, and "not fully checked" has none."""
    out = []
    if not target.gate:
        return out
    found = gates.verdict(view.model, record.text, target.gate, textedit.today(view), getattr(view, "flows", None))
    named = rules_set_aside(item)
    for reason in found.reasons:
        route = gates.ROUTE_NAMES.get(reason.rule)
        if route is not None and route in named:
            continue
        if (item.get("stated_in") or options_given(item)) and reason.rule == STATED_SKIPS:
            continue  # a source states it, the pick is written with it, or the lead said there was only this one
        override = found.route if route is not None else \
            "none from decide: settle each finding, or the dated flow-check override the checker reads"
        # The gate's fix is my recommendation to the lead; an event rule is set aside with a reason and no end date.
        waiver = None if route is None or overrides.is_standing(route) else EVENT_WAIVER
        out.append(textedit.refusal(reason.rule, reason.plain, reason.fix, override=override, recommend=reason.fix,
                                    waiver=waiver))
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


def speaker(capture, lead):
    """Who a committed line names: the lead's `whoami` handle when the capture is the lead's (its origin may be a
    display name, never to become `@Jo`), else the capture's origin without its `unverified` mark (the gate asks the
    lead to confirm that capture; the line names who said it, never the mark)."""
    if lead is not None and consent.from_the_lead(capture, lead[0], lead[1]) is None:
        return receipts.handle_ref(lead[0])
    return said.confirmed(capture.origin)


def receipt(item, view, record):
    """The value after `- **Decision:**`: the cited yes's session, capture and speaker, with their words when they may
    be quoted; the bare link for a decision made on an override of the quoted-yes rule."""
    if not item.get("yes"):
        return receipts.decision_value(record.id, None)
    capture = record.capture(item["yes"])
    words = capture.quote if consent.may_quote(capture, record, view.lead) else None
    return receipts.decision_value(record.id, privaterecord.Ref(record.part, int(capture.n)),
                                   speaker(capture, view.lead), words, item.get("stated_in"))


def history_bullets(item, view, record, target, decision=True):
    """The bullets a decision adds under `## History`, in CONVENTIONS' order."""
    today = textedit.today(view)
    out = [options_bullet(item, view, record)] if options_given(item) else []
    out += [f"- **Decision:** {receipt(item, view, record)}"] if decision else []
    if item.get("why"):
        out.append(f"- **Why:** {textedit.inline(record.capture(item['why']).quote)}")
    if item.get("dissent"):
        capture = record.capture(item["dissent"])
        words = capture.quote if consent.may_quote(capture, record, view.lead) else None
        see = record.id if words else ""
        out.append(f"- **Dissent:** {receipts.dissent_value(speaker(capture, view.lead), today, words, see=see)}")
    out += _override_bullets(item, view, record, target)
    owners = stand_in_owners(item, view, record, target)
    if owners:
        out.append(f"- **Decided by:** {item['by']}, on behalf of {' '.join(owners)}")
    if item.get("reader"):
        out.append(f"- **Pending approval:** {item['by']}, {today}")
    return out


# --- a settled pick's options (--picked, --rejected)

def pick_given(item):
    """--picked or --rejected is on the item."""
    return bool(item.get("picked") or item.get("rejected"))


def options_given(item):
    """The options come with the decision (a pick, or the lead's "only this one"), so GATE-2 has nothing to ask."""
    return pick_given(item) or bool(item.get("options_none"))


def options_specs(item):
    """The `<option>=<^cN or declined>` strings, the pick first."""
    return ([item["picked"]] if item.get("picked") else []) + list(item.get("rejected") or [])


def option_parts(spec):
    """(option, what follows the last '='), or (spec, "") when there is no '='."""
    name, _, rest = str(spec).rpartition("=")
    return (name.strip(), rest.strip()) if name else (str(spec).strip(), "")


def option_ref(spec):
    """The capture a spec cites, or "" for a declined reason."""
    rest = option_parts(spec)[1]
    return "" if rest == DECLINED else rest


def options_bullet(item, view, record):
    """The `**Options considered:**` line for this decision, in the form the lead's words call for (options_line).
    A reason goes on in words only when that person may be quoted; else the bullet points at the notes."""
    if item.get("options_none"):
        capture = record.capture(item["options_none"])
        cite = privaterecord.citation(record.id, record.part, int(capture.n))
        words = textedit.inline(capture.quote) if consent.may_quote(capture, record, view.lead) else None
        return options_line.only_this_one(cite, words)
    rejected = []
    for spec in item.get("rejected") or []:
        name, rest = option_parts(spec)
        if rest == DECLINED:
            why = options_line.DECLINED_REASON
        else:
            capture = record.capture(rest)
            why = (f'"{textedit.inline(capture.quote).replace(chr(34), chr(39))}"'
                   if consent.may_quote(capture, record, view.lead)
                   else f"the reason is in {textedit.capture_ref(record, rest)}")
        rejected.append((textedit.inline(name), why))
    return options_line.picked(textedit.inline(option_parts(item["picked"])[0]), rejected)


def options_written(view, target):
    """Whether the item (or page) already carries an `**Options considered:**` bullet."""
    found = view.model.item(target.id)
    if found is not None:
        return vault_schema.OPTIONS_LABEL in found.facts
    pages = view.model.by_id.get(target.id) or []
    return bool(pages and pages[0].page_bullets(vault_schema.OPTIONS_LABEL))


def options_refusals(item, view, record, target):
    """A pick is whole: the option picked, at least one set aside, each citing a capture the record holds, and not
    written already. Each refusal names the way round it (the audience is the model)."""
    if item.get("options_none") and pick_given(item):
        return [refusal("decide-options-both", "An item has one answer to what else was on the table, not two.",
                        "Give --options-none (the only option) or --picked with --rejected, not both.",
                        override="none: one options line per item", audience=say.MODEL)]
    if not pick_given(item):
        return []
    gate_two = "the lead's override of GATE-2, with their reason, instead of --picked and --rejected"
    if not item.get("picked") or not item.get("rejected"):
        return [refusal("decide-options-one", "A pick needs something it was picked over before I can write it down.",
                        "Give both --picked \"<option>=^cP\" and --rejected \"<option>=^cR\" (or =declined) for each "
                        "option set aside; one option alone is not a choice.", override=gate_two, audience=say.MODEL)]
    found = []
    for spec in options_specs(item):
        name, rest = option_parts(spec)
        problem = None if rest == DECLINED else consent.exists(rest, record) if rest else True
        if problem is not None:
            found.append(refusal("decide-options-capture", "I can't find where that option was picked or set aside.",
                                 f"{spec!r}: use <option>=^cN with a capture in this record, or <option>=declined for "
                                 "a reason the lead declined to give.", override="none: drop --picked and --rejected",
                                 audience=say.MODEL))
    picked_ref = option_ref(item["picked"]) if item.get("picked") else ""
    if picked_ref and consent.exists(picked_ref, record) is None and not record.capture(picked_ref).is_person:
        found.append(refusal("decide-options-pick-not-theirs", "The pick has to be in the lead's own words, not mine.",
                             f"Capture where the lead picked it with them as origin (^c{record.capture(picked_ref).n} is "
                             "Claude's), then use that capture in --picked.",
                             override="none: drop --picked and --rejected", audience=say.MODEL))
    if options_written(view, target):
        found.append(refusal("decide-options-written", "That item already has its options written down, so I left "
                                                        "them as they are.",
                             "Drop --picked and --rejected; the bullet stays as written.",
                             override="none: the options are already on the page", audience=say.MODEL))
    return found


def add_history(text, bullets, target):
    for bullet in bullets:
        text = textedit.add_history(text, bullet, target.history)
    return text


def consumed(item):
    """Every capture the decision filed, the cited one first: each is kept on the item it went into, so close finds
    nothing of this decision left to place."""
    refs = [item.get(name) for name in ("yes", "why", "dissent", "provider", "options_none")]
    refs += [option_ref(spec) for spec in options_specs(item)]
    refs += [group.get(name) for group in item.get("groups") or [] for name in ("yes",)]
    refs += [group.get("reason") for group in item.get("overrides") or []]
    return list(dict.fromkeys(ref for ref in refs if ref))


def record_after(item, view, record, target, before, after, cite):
    """The record with the Changes row, a keep mark on every capture the decision filed (an earlier mode's mark is
    left as it is) and the agenda line."""
    text = textedit.record_text(record, view)
    text = textedit.add_change(text, textedit.cell(target.id), before or "-", after,
                               textedit.capture_link(record.id, cite))
    mark = textedit.keep_mark(textedit.basename(target.path), target.anchor, target.id, after)
    for ref in [cite] + consumed(item):
        text = textedit.mark_if_unmarked(text, ref, mark)
    line = agenda.entries(text).get(target.id)
    if line is not None:
        status = "decided" if item.get("reopen") is not True else "open"
        held = tuple(line["override"].split(", ")) if line["override"] else ()
        text = agenda.set_line(text, target.id, agenda.format_line(target.id, line["yes"] == "yes", status, held))
    return text


def writes(target, page_text, record_text_after, view, record):
    out = [schema.Write(target.path, page_text)] if page_text != view.text(target.path) else []
    return out + textedit.record_writes(record, view, record_text_after)
