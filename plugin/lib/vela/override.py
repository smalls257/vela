"""The user's word over a rule. Pure: no disk, clock or network.

The person running a skill may override any rule in it. The shape here exists to stop
two failures. A Silent Fallback: an override nobody can see, so a red check goes green
and the reviewer never learns why. And a typo that silently overrides nothing, so the
user believes a rule was set aside when the check still enforces it. So an override is
never refused and never invisible: a well-formed one turns the error it names into a
warning that quotes it, and a malformed one is an error of its own.

A third failure is time. An override of a standing rule (schema.STANDING_RULES: an open
unknown still blocking, a case table still missing) with no end would cover the rule
forever, so a red check stays green long after the lead's reason stopped holding: a Silent
Fallback with a signature on it. So it carries `until`, the day it ends (Anchor: the lead's
words and the date sit on the page). Past that day it covers nothing and check says E398;
the lead renews it or the rule bites again. An event rule (GATE-1, 2, 3, 5) was met or not at
the moment of deciding, so its override has nothing to end. An old bullet with no `until`
still parses and still covers, and when a refusal asks for a date, suggest_until offers one;
nothing here ever writes it. Dates come in as arguments: the core reads no clock.

Grammar, as CONVENTIONS.md gives it under "Overrides":

    - **Override:** <rule>[, <rule>...] by @handle on YYYY-MM-DD[ until YYYY-MM-DD]: <reason>
    - **Decided by:** @handle, on behalf of @owner [@owner...]
    - **Confirmed by:** @handle on YYYY-MM-DD

A <rule> is a name in schema.OVERRIDE_RULES, or a skill rule check cannot see, quoted:
"Shape offers 2 or 3 options". The flow check's quoted rules carry their end inside the
quotes ("F8 CON-020 declined until 2026-10-01"), and flowcheck.verdicts says their E398.
"""
import datetime
import difflib
import re
from dataclasses import dataclass

from vela import allocation, ledger, releases, schema
from vela.model import Finding, meta_line
from vela.parse import Bullet

QUOTED_RULE = r'"[^"\n]+"'
RULE_TOKEN = rf'{QUOTED_RULE}|[A-Za-z0-9-]+'
OVERRIDE_RE = re.compile(
    rf'^(?P<rules>(?:{RULE_TOKEN})(?:, (?:{RULE_TOKEN}))*) by (?P<by>{schema.HANDLE}) on (?P<date>\d{{4}}-\d{{2}}-\d{{2}})'
    rf'(?: until (?P<until>\d{{4}}-\d{{2}}-\d{{2}}))?: (?P<reason>\S.*)$')
# The end a flow-check rule carries inside its quotes.
QUOTED_UNTIL_RE = re.compile(r'^"F\d+ .* until (\d{4}-\d{2}-\d{2})"$')
# A bare handle is the owner's own decision (what a proposal's review writes); "on behalf of" is someone else deciding for them.
DECIDED_BY_RE = re.compile(rf'^(?P<by>{schema.HANDLE})(?:, on behalf of (?P<owners>{schema.HANDLE}(?: {schema.HANDLE})*))?$')
CONFIRMED_BY_RE = re.compile(rf'^(?P<by>{schema.HANDLE}) on (?P<date>\d{{4}}-\d{{2}}-\d{{2}})$')
RULE_SPLIT = re.compile(rf'{QUOTED_RULE}|[^,]+')

GRAMMAR = "<rule>, <rule> by @handle on YYYY-MM-DD until YYYY-MM-DD: <reason>"
DECIDED_BY_GRAMMAR = "@handle, on behalf of @owner (or just @owner for the owner's own decision)"
CONFIRMED_BY_GRAMMAR = "@owner on YYYY-MM-DD"
NEAR_MISS = 0.75  # a label this close to one of ours is a typo, never prose


@dataclass(frozen=True)
class Override:
    line: int
    text: str
    rules: tuple  # rule names as written; empty when malformed
    by: str
    date: str
    reason: str
    problem: str  # "" when well formed
    until: object = None  # "YYYY-MM-DD", the last day it covers, or None when the bullet names no end

    @property
    def codes(self):
        """The check codes this override turns into warnings."""
        return {code for rule in self.rules for code in schema.OVERRIDE_RULES.get(rule, ())}

    def describe(self):
        until = f" until {self.until}" if self.until else ""
        return f"{', '.join(self.rules)} by {self.by} on {self.date}{until}: {self.reason}"

    def as_dict(self):
        if self.problem:
            return {"line": self.line, "text": self.text, "malformed": True, "problem": self.problem}
        out = {"line": self.line, "rules": list(self.rules), "by": self.by, "date": self.date, "reason": self.reason}
        if self.until:
            out["until"] = self.until
        return out


@dataclass(frozen=True)
class OnBehalf:
    """A Decided by bullet and whether a Confirmed by bullet clears it."""
    line: int
    by: str
    owners: tuple
    confirmed_by: str  # "" until confirmed
    confirmed_on: str

    def as_dict(self):
        return {"line": self.line, "by": self.by, "on_behalf_of": list(self.owners), "confirmed": bool(self.confirmed_by)}


def _is_date(value):
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


# Rules an old vault may still name: deciding is no longer limited to a grill, so there is nothing left to override.
RETIRED_RULES = ("grill", "E317", "W317")


def _rule_problem(names):
    unknown = [n for n in names if not n.startswith('"') and n not in schema.OVERRIDE_RULES]
    if not unknown:
        return ""
    retired = [n for n in unknown if n in RETIRED_RULES]
    if retired:
        return (f"names {', '.join(repr(n) for n in retired)}, and that rule is gone "
                "(delete this bullet)")
    hints = []
    for name in unknown:
        near = [k for k in schema.OVERRIDE_RULES if k.lower() == name.lower()] or \
            difflib.get_close_matches(name, schema.OVERRIDE_RULES, n=1, cutoff=0.6)
        hints.append(f"'{name}'" + (f" (did you mean {near[0]}?)" if near else ""))
    return (f"names {', '.join(hints)}, which is not a rule an override can name. "
            f"Use {', '.join(schema.OVERRIDE_RULES)}, or quote a skill rule check cannot see")


def _shape_problem(value):
    """Why a value that fails the grammar fails it, in the order a reader would fix it."""
    if not value:
        return "is empty"
    if re.match(r"by\s", value):
        return "names no rule before 'by'"
    if not re.search(rf" by {schema.HANDLE}", value):
        return "names no @handle after 'by'"
    if not re.search(r" on \d{4}-\d{2}-\d{2}", value):
        return "has no 'on YYYY-MM-DD' date"
    if re.search(r" on \d{4}-\d{2}-\d{2} until(?! \d{4}-\d{2}-\d{2}:)", value):
        return "has an end date that is not 'until YYYY-MM-DD' before the colon"
    if not re.search(r" on \d{4}-\d{2}-\d{2}(?: until \d{4}-\d{2}-\d{2})?: \S", value):
        return "gives no reason after the date"
    head = value.split(" by @", 1)[0]
    if not re.fullmatch(rf'(?:{RULE_TOKEN})(?:, (?:{RULE_TOKEN}))*', head):
        return "has a rule list that is not names separated by ', '"
    return "does not follow the grammar"


def parse_override(bullet):
    value = bullet.value.strip()
    match = OVERRIDE_RE.match(value)
    if not match:
        return Override(bullet.line, value, (), "", "", "", _shape_problem(value))
    names = tuple(m.group(0).strip() for m in RULE_SPLIT.finditer(match["rules"]))
    until = match["until"]
    problem = _rule_problem(names)
    if not problem and not _is_date(match["date"]):
        problem = f"has date {match['date']}, which is not a real date"
    if not problem and until and not _is_date(until):
        problem = f"has end date {until}, which is not a real date"
    if not problem and until and until < match["date"]:
        problem = f"ends on {until}, before the day it was written ({match['date']})"
    if problem:
        return Override(bullet.line, value, (), "", "", "", problem)
    return Override(bullet.line, value, names, match["by"], match["date"], match["reason"].strip(), "", until or None)


def parse(value, line=0):
    """One Override bullet's value read: rules, by, date, until (or None) and reason, or the problem."""
    return parse_override(Bullet(schema.OVERRIDE_LABEL, value, line, (), "", False))


# ------------------------------------------------------------------ end dates

def is_standing(rule):
    """Whether the rule guards a condition that stays true, so an override of it needs the date it ends. A quoted
    rule is standing when it is one of schema.STANDING_QUOTED or a flow-check finding ("F<n> ...")."""
    if rule.startswith('"'):
        return rule in schema.STANDING_QUOTED or bool(re.match(r'^"F\d+ ', rule))
    return rule in schema.STANDING_RULES


def ends(ov):
    """The last day a standing override covers, "YYYY-MM-DD", or None when it names no end: its own `until`,
    else the earliest end a flow-check rule carries inside its quotes. An event override never ends."""
    if not any(is_standing(rule) for rule in ov.rules):
        return None
    if ov.until:
        return ov.until
    inner = [m.group(1) for m in map(QUOTED_UNTIL_RE.match, ov.rules) if m]
    return min(inner) if inner else None


def covers(ov, today):
    """Whether the override sets its rules aside on `today` ("YYYY-MM-DD" or a date): well formed, and not past its
    end. A past end covers nothing, so the rule bites again rather than staying quietly green."""
    if ov.problem:
        return False
    end = ends(ov)
    return end is None or str(today) <= end


def expired(ov, today):
    """Whether a well-formed standing override's own `until` has passed. The flow check's in-quote ends are
    flowcheck.verdicts' to report, so E398 is said once."""
    return bool(not ov.problem and ov.until and any(is_standing(r) for r in ov.rules) and ov.until < str(today))


_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _feeds(vault, release, item_id):
    """Whether the item is part of what the release delivers: a requirement it lists, the capability one belongs to,
    or an app or contract that carries a share of it."""
    requirements = {row.requirement for row in release.rows if row.requirement}
    if item_id in requirements or any(r.split(".")[0] == item_id for r in requirements):
        return True
    apps, contracts = releases.reach(vault, release)
    return item_id in apps or item_id in contracts


def suggest_until(item_id, vault, today):
    """The end date a refusal offers for a standing override on `item_id`: the soonest release `**Target**`, on or
    after today, of a release the item feeds, else SUGGEST_UNTIL_DAYS from today. Offered, never written: the lead
    picks the date."""
    today = str(today)
    targets = []
    for release in releases.releases(vault):
        found = _ISO.search(release.target or "")
        if found and _is_date(found.group(0)) and found.group(0) >= today and _feeds(vault, release, item_id):
            targets.append(found.group(0))
    if targets:
        return min(targets)
    return (datetime.date.fromisoformat(today) + datetime.timedelta(days=schema.SUGGEST_UNTIL_DAYS)).isoformat()


# ------------------------------------------------------------------ scopes

def scope_bullets(page, item_id, label):
    """Bullets with this label under one item heading, or at page level when item_id is ""."""
    return [b for b in page.bullets if b.label == label and b.item == item_id and not b.generated]


def overrides(page, item_id=""):
    return [parse_override(b) for b in scope_bullets(page, item_id, schema.OVERRIDE_LABEL)]


def valid_overrides(page, item_id=""):
    return [o for o in overrides(page, item_id) if not o.problem]


def on_behalf(page, item_id=""):
    """The first well-formed Decided by in the scope, with its confirmation, or None."""
    confirmations = [CONFIRMED_BY_RE.match(b.value.strip()) for b in scope_bullets(page, item_id, schema.CONFIRMED_BY_LABEL)]
    for bullet in scope_bullets(page, item_id, schema.DECIDED_BY_LABEL):
        match = DECIDED_BY_RE.match(bullet.value.strip())
        if not match or not match["owners"]:
            continue
        # The person who decided cannot confirm for the owner, or the warning clears itself.
        ok = [c for c in confirmations if c and _is_date(c["date"]) and c["by"] != match["by"]]
        return OnBehalf(bullet.line, match["by"], tuple(match["owners"].split()),
                        ok[0]["by"] if ok else "", ok[0]["date"] if ok else "")
    return None


def summary(page, item_id=""):
    """What query get returns about overrides for one item or page."""
    behalf = on_behalf(page, item_id)
    confirmed = scope_bullets(page, item_id, schema.CONFIRMED_BY_LABEL)
    match = CONFIRMED_BY_RE.match(confirmed[0].value.strip()) if confirmed else None
    return {
        "override": [o.as_dict() for o in overrides(page, item_id)],
        "decided_by": behalf.as_dict() if behalf else None,
        "confirmed_by": {"by": match["by"], "date": match["date"]} if match else None,
    }


def decisions(page):
    """[(valid overrides, on-behalf decision or None)] for each scope on the page that holds
    an override or a Decided by: the page level first, then each item in page order.
    Viewer and export read this, so neither grows a second parser."""
    ids = []
    for bullet in page.bullets:
        if bullet.label in schema.OVERRIDE_LABELS and not bullet.generated and bullet.item not in ids:
            ids.append(bullet.item)
    ids.sort(key=lambda i: (i != "",))
    scopes = [(valid_overrides(page, i), on_behalf(page, i)) for i in ids]
    return [(found, behalf) for found, behalf in scopes if found or behalf]


def _scopes(vault):
    """{(path, item id or ""): page} for every page and item heading that holds one of our bullets."""
    out = {}
    for page in vault.pages:
        for bullet in page.bullets:
            if bullet.label in schema.OVERRIDE_LABELS and not bullet.generated:
                out[(page.path, bullet.item)] = page
    return out


def unit_lines(vault, page, item_id):
    """The lines where check reports on the units a scope covers: an item's heading, or a page's state line, its goal
    rows, its allocation rows and its releases. Contracts under the page's headings are their own scope."""
    if item_id:
        item = vault.item(item_id)
        return {item.line} if item is not None and item.page is page else set()
    lines = {meta_line(page, "state")} if "state" in page.meta else set()
    for table in page.tables:
        if not table.generated and tuple(table.header)[:4] == schema.GOALS_HEADER:
            lines.update(table.row_lines)
    lines.update(row.line for row in allocation.rows(vault) if row.app is page)
    if page.id == releases.PAGE_ID:
        lines.update(release.line for release in releases.releases(vault))
    if page.id == ledger.PAGE_ID:
        lines.update(ledger.lines(page))  # a page-level override here may name a ledger code such as E805
        if not ledger.heading_line(page):
            lines.add(1)  # E805 reports at the top of a page that lacks the heading
    return lines


# ------------------------------------------------------------------ findings

def _f(page, line, code, message, fix):
    return Finding(page.path, line, code, message, fix)


def label_findings(vault):
    """E321 and E322 for a label that is nearly one of ours: a typo must never pass as prose."""
    ours = {label.lower(): label for label in schema.OVERRIDE_LABELS + (schema.PENDING_LABEL,)}
    known = {label.lower() for label in schema.CONTRACT_REQUIRED + schema.CONTRACT_OPTIONAL + schema.UNKNOWN_REQUIRED
             + schema.UNKNOWN_OPEN_REQUIRED + schema.UNKNOWN_RESOLVED_REQUIRED + schema.UNKNOWN_OPTIONAL
             + schema.RISK_REQUIRED + schema.RISK_OPTIONAL + schema.PAGE_LABELS + schema.SUBJECT_LABELS
             + schema.READING_LABELS}
    for page in vault.pages:
        for bullet in page.bullets:
            label = bullet.label.lower()
            if bullet.generated or label in known:
                continue
            near = difflib.get_close_matches(label, ours, n=1, cutoff=NEAR_MISS)
            if near:
                meant = ours[near[0]]
                code = "E321" if meant == schema.OVERRIDE_LABEL else "E322"
                yield _f(page, bullet.line, code, f"**{bullet.label}:** looks like **{meant}:**, so it records nothing.",
                         f"Write the label as **{meant}:**.")


def grammar_findings(vault):
    for page in vault.pages:
        for bullet in page.bullets:
            if bullet.generated:
                continue
            value = bullet.value.strip()
            if bullet.label == schema.OVERRIDE_LABEL:
                found = parse_override(bullet)
                if found.problem:
                    yield _f(page, bullet.line, "E321", f"This **Override:** {found.problem}, so it overrides nothing.",
                             f"Write - **Override:** {GRAMMAR}, for example GATE-4 by @hl-solution-lead on 2026-11-20: <why>.")
            elif bullet.label == schema.DECIDED_BY_LABEL and not DECIDED_BY_RE.match(value):
                yield _f(page, bullet.line, "E322", f"**Decided by:** '{value}' does not say who decided on whose behalf.",
                         f"Write - **Decided by:** {DECIDED_BY_GRAMMAR}.")
            elif bullet.label == schema.CONFIRMED_BY_LABEL:
                match = CONFIRMED_BY_RE.match(value)
                if not match or not _is_date(match["date"]):
                    yield _f(page, bullet.line, "E322", f"**Confirmed by:** '{value}' does not say who confirmed it and when.",
                             f"Write - **Confirmed by:** {CONFIRMED_BY_GRAMMAR}.")


def testable(rule, gate):
    """Whether this run of check could see the rule broken: a gate-only code only under its gate."""
    codes = schema.OVERRIDE_RULES.get(rule, ())
    return bool(codes) and all(schema.GATE_ONLY_CODES.get(code) in (None, gate) for code in codes)


def apply(vault, findings, today, gate=None):
    """The findings with every overridden error turned into its warning, plus W323 for an
    override that sets aside a rule the item does not break, W324 for an on-behalf decision
    the owner has not confirmed, E398 for a standing override past its `until` (which covers
    nothing, so the error it named stays an error), and E321/E322 for bullets that cannot be
    read. `gate` is the gate check ran under, so an override of a gate-only code is idle only
    when its gate ran. `today` is "YYYY-MM-DD", passed in."""
    scopes = _scopes(vault)
    by_line = {}
    for (path, item_id), page in scopes.items():
        for line in unit_lines(vault, page, item_id):
            by_line[(path, line)] = (page, item_id)
    fired = {}  # (path, item id) -> codes that fired in that scope
    out = []
    for finding in findings:
        scope = by_line.get((finding.path, finding.line))
        if scope is None or finding.code not in schema.OVERRIDE_CODES:
            out.append(finding)
            continue
        page, item_id = scope
        fired.setdefault((page.path, item_id), set()).add(finding.code)
        cover = [o for o in valid_overrides(page, item_id) if finding.code in o.codes and covers(o, today)]
        if not cover:
            out.append(finding)
            continue
        said = "; ".join(o.describe() for o in cover)
        fix = finding.fix.replace(schema.E805_OVERRIDE_HINT, "").strip()
        out.append(Finding(finding.path, finding.line, schema.OVERRIDE_CODES[finding.code],
                           f"{finding.message} Accepted as an exception: {said}.",
                           f"It doesn't block. To clear the exception, fix the cause: {fix}"))
    for (path, item_id), page in sorted(scopes.items(), key=lambda kv: kv[0]):
        seen = fired.get((path, item_id), set())
        where = item_id or page.id or page.name
        for found in valid_overrides(page, item_id):
            if expired(found, today):
                standing = [r for r in found.rules if is_standing(r)]
                out.append(_f(page, found.line, "E398",
                              f"The override of {', '.join(standing)} on {vault.named(where)} ended on {found.until}, "
                              "so it covers nothing and the rule it set aside applies again.",
                              "Fix the cause and delete the override, or renew it: write a new until date and why it moved."))
                continue
            idle = [r for r in found.rules if testable(r, gate) and not set(schema.OVERRIDE_RULES[r]) & seen]
            if idle:
                out.append(_f(page, found.line, "W323",
                              f"Override not needed: {where} does not break {', '.join(idle)}, so the override sets nothing aside.",
                              "Remove the rule from the bullet, or the bullet. The session record keeps the history."))
        behalf = on_behalf(page, item_id)
        if behalf and not behalf.confirmed_by:
            owners = " ".join(behalf.owners)
            out.append(_f(page, behalf.line, "W324",
                          f"{behalf.by} decided {vault.named(where)} on {owners}'s behalf, and {owners} hasn't confirmed it yet.",
                          f"Ask {owners} to confirm (add - **Confirmed by:** {CONFIRMED_BY_GRAMMAR}), "
                          f"or to challenge it with /vela:challenge if they disagree."))
    out.extend(grammar_findings(vault))
    out.extend(label_findings(vault))
    return out
