"""The `override` apply kind: the lead setting a rule aside, written on the item in their own words (plan 4.4;
CONVENTIONS "Overrides"; close's "Find the session and mark the captures", grill's "The gate and the agenda", epics' E805 route). Pure.

    - **Override:** <rule>[, <rule>] by @handle on YYYY-MM-DD[ until YYYY-MM-DD]: <the lead's words>

The Violation this exists to prevent is a Silent Fallback with a signature on it. An override is how the lead goes
ahead past any rule (they may override anything; it is never refused for being an override), so what it must never be
is invisible or endless:

- **The reason is the lead's words, verbatim**, copied by code from the capture the item names: a reason the model
  paraphrased is the model's reason. So the capture must be a person's, not Claude's (`consent.why_in_their_words`).
  Words that are also the page's syntax are escaped so the bullet holds (`textedit.inline`); `words_of` reads them
  back unchanged.
- **`by` is the capture's origin handle** and **`on` is today**: who chose, and when, are facts the record already
  holds, so nobody is asked for them.
- **A standing rule needs `until`** (`override.is_standing`: GATE-4, E303, E304, E316, E318, E805, the case
  table, a flow-check finding): it guards a condition that stays true until someone acts, so without an end it would
  cover the rule long after the lead's reason stopped holding. A missing date is refused with the date to offer
  (`override.suggest_until`: the next release target the item feeds, else 30 days on), which the lead agrees to
  before it is written. An event rule (GATE-1, 2, 3, 5) was met or not at the moment of deciding and takes no `until`.
- **The rule names a rule**: a name in `schema.OVERRIDE_RULES`, or a skill rule in double quotes. A name that exists
  nowhere would override nothing while the lead believes it did; and a wish that sets no rule aside is a Notes line,
  not an override.
- **Where it sits**: under `## History`, in `#### <ID>` for an item with a heading, directly under `## History` for a
  page, which is where CONVENTIONS puts every override and where check reads it.

The bullet written is parsed back with the check's own parser (`vela.override.parse`) before it is returned, so a
bullet check would call malformed (E321) is never written.
"""
import re

from vela import override as overrides, say, schema as vault_schema
from vela.decisions import consent, schema, textedit

HANDLE = re.compile(rf"^{vault_schema.HANDLE}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SCHEMA = schema.KindSchema(
    fields={"on": "the item's ID (or a page's ID) the rule is set aside for",
            "rules": "the rules set aside: names such as GATE-4 or E805, or a quoted skill rule \"...\"",
            "reason": "the capture holding the lead's reason, in their words (\"^c35\")",
            "until": "YYYY-MM-DD, the last day it covers; required for a standing rule, left out for an event rule"},
    judgment=("reason", "until"), required=("on", "rules", "reason"),
    example={"on": "CON-003", "rules": ["GATE-4"], "reason": "^c35", "until": "2026-11-30"})


def words_of(reason):
    """The lead's words as captured, from a written reason."""
    return textedit.unescape(reason)


def rule_problem(rule):
    rule = str(rule)
    if rule in vault_schema.OVERRIDE_RULES or re.fullmatch(r'"[^"\n]+"', rule):
        return None
    return rule


def validate(item, vault, record):
    found = textedit.context_refusals(vault)
    rules = [str(r) for r in item["rules"]] if isinstance(item["rules"], list) else [str(item["rules"])]
    bad = [r for r in rules if rule_problem(r)]
    if bad or not rules:
        found.append(textedit.refusal("override-rule", "I couldn't tell which rule you're setting aside, so I wrote "
                                                       "nothing.",
                                      f"{', '.join(bad) or 'no rule'}: a rule is one of "
                                      f"{', '.join(vault_schema.OVERRIDE_RULES)}, or a skill rule in double quotes.",
                                      override="none: name the rule; a wish that sets none aside is a Notes line"))
    if textedit.find(vault, str(item["on"])) is None:
        found.append(textedit.refusal("override-item", "I can't find the item that override is for.",
                                      f"{item['on']} is no item or page ID in this vault."))
    why = consent.why_in_their_words(item["reason"], record, getattr(vault, "lead", None))
    if why is not None:
        return found + [why]
    capture = record.capture(item["reason"])
    if not HANDLE.match(capture.origin.strip()):
        found.append(textedit.refusal("override-by", "I need your handle on the reason, so the override says who "
                                                     "chose it.",
                                      f"^c{capture.n} has origin {capture.origin!r}; capture the lead's reason with "
                                      "their handle as origin (vela whoami).",
                                      override="none: an override names who chose it"))
    today = textedit.today(vault)
    standing = any(overrides.is_standing(r) for r in rules)
    until = item.get("until")
    if standing and not until and today:
        date = overrides.suggest_until(str(item["on"]), vault.model, today)
        found.append(textedit.refusal("override-until", "Setting that aside needs an end date, so it can't cover the "
                                                        f"rule forever. Shall I say until {_said(date)}?",
                                      f"Standing rule: ask the lead for the last day it covers; offer {date} (the next "
                                      "release the item feeds, else 30 days on), then set until.",
                                      override="none for the date itself: a standing override always ends; the lead "
                                               "picks the day"))
    elif until and not standing:
        found.append(textedit.refusal("override-until-event", "That check was met or not when you decided, so it has "
                                                              "nothing to end.",
                                      "Leave until out for GATE-1, GATE-2, GATE-3, GATE-5 and other event rules."))
    elif until and (not DATE.match(str(until)) or (today and str(until) < today)):
        found.append(textedit.refusal("override-until-date", "That end date isn't one I can use.",
                                      f"until {until!r} must be a YYYY-MM-DD date, today or later."))
    return found


def _said(date):
    """The end date as the lead hears it, without a year: 'December 1'."""
    import datetime
    return say.date_words(date, today=datetime.date.fromisoformat(date))


def bullet_value(item, vault, record):
    capture = record.capture(item["reason"])
    rules = item["rules"] if isinstance(item["rules"], list) else [item["rules"]]
    until = f" until {item['until']}" if item.get("until") else ""
    return (f"{', '.join(map(str, rules))} by {capture.origin.strip()} on {textedit.today(vault)}{until}: "
            f"{textedit.inline(capture.quote)}")


def apply(item, vault, record):
    from vela.decisions import Refused  # the core's whole-file refusal, raised on a vela bug only
    value = bullet_value(item, vault, record)
    parsed = overrides.parse(value)
    if parsed.problem:
        raise Refused([textedit.refusal("override-grammar", "Something went wrong on my side, so I wrote nothing.",
                                        f"vela bug: the override bullet would not parse ({parsed.problem}): {value}")])
    path, heading = textedit.find(vault, str(item["on"]))
    page = textedit.add_history(vault.text(path), f"- **Override:** {value}", str(item["on"]) if heading else "")
    return [schema.Write(path, page)]
