"""A contract's case table: every way the provider can answer, one row each. Pure: text in, cases and problems out.

The table is what a flow checker, a stub and a boundary test read, so it is structure, never prose. It exists to
stop a Paper Tiger: a contract that is "decided" while nobody has said what happens when the call goes wrong.
This module only reads it. `rules.case_table_rules` turns the problems into warnings.
"""
import re
from dataclasses import dataclass

HEADER = ("Case", "When", "Status", "Answer", "Emits", "Sets")
CASE_KEY = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
STATUS = re.compile(r"^(?:\d{3}|ok|error)$")
EVENT_ID = re.compile(r"^EVT-\d{3}$")
BLANK = ("", "-", "—", "–")
_NAME = r"[a-z][a-z0-9_.]*"
_VALUE = r"[A-Za-z0-9_.-]+"
_CLAUSE = rf"{_NAME} (?:is|is not) {_VALUE}|{_NAME} in \[{_VALUE}(?:, ?{_VALUE})*\]"
WHEN = re.compile(rf"^(?:{_CLAUSE})(?: and (?:{_CLAUSE}))*$")
_STATE = r"[A-Za-z0-9_-]+"
_PAIR = rf"{_STATE}\s*(?:→|->)\s*{_STATE}"
# `order: new→held`, `order: held`, or a change that depends on where it starts: `stock: one→zero, zero→minus_one`.
SETS_ENTRY = re.compile(rf"^(?P<entity>[^:;]+?):\s*(?:(?P<pairs>{_PAIR}(?:\s*,\s*{_PAIR})*)|(?P<state>{_STATE}))$")
PAIR = re.compile(rf"^(?P<frm>{_STATE})\s*(?:→|->)\s*(?P<to>{_STATE})$")
_KEY = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
# How many times the caller tries again, and after which answers: `2 after timeout, unavailable`. Which answers are
# retried is required (design 19, revision 2, item 7): retrying a refusal is a bug, so nothing is assumed retried.
RETRIES = re.compile(rf"^(?:none|(?P<count>\d+) after (?P<keys>{_KEY}(?:, ?{_KEY})*))$")
YES_NO = ("yes", "no")
ENTITY_HEADING = re.compile(r"^ENT-\d{3}\b")
EVENT_HEADING = re.compile(r"^EVT-\d{3}\b")


@dataclass(frozen=True)
class Case:
    key: str
    when: str
    status: str
    answer: str
    emits: tuple
    sets: tuple  # (entity, from or "", to) for each state change
    line: int

    @property
    def is_error(self):
        return self.status == "error" or (self.status.isdigit() and int(self.status) >= 400)


@dataclass(frozen=True)
class Problem:
    line: int
    code: str  # "malformed" or "duplicate"
    message: str
    fix: str


@dataclass(frozen=True)
class CaseTable:
    line: int  # the header row
    cases: tuple
    problems: tuple


def section_end(page, item):
    later = [h.line for h in page.headings if h.line > item.line and h.level <= 3]
    return later[0] if later else len(page.text.split("\n")) + 1


def case_table(page, item):
    """The contract's case table, or None when its section holds no table headed Case."""
    end = section_end(page, item)
    for table in page.tables:
        if table.generated or not (item.line < table.line < end):
            continue
        if table.header and table.header[0].strip().lower() == "case":
            return _read(item.id, table)
    return None


def _read(contract_id, table):
    problems, cases, seen = [], [], {}
    if tuple(h.strip().lower() for h in table.header) != tuple(h.lower() for h in HEADER):
        problems.append(Problem(table.line, "malformed", f"{contract_id}'s case table has the columns {' | '.join(table.header)}.",
                                "Use exactly: | " + " | ".join(HEADER) + " |."))
        return CaseTable(table.line, (), tuple(problems))
    for row, line in zip(table.rows, table.row_lines):
        parsed = _row(contract_id, row, line)
        if isinstance(parsed, Problem):
            problems.append(parsed)
            continue
        if parsed.key in seen:
            problems.append(Problem(line, "duplicate", f"{contract_id} has two cases called {parsed.key} (lines {seen[parsed.key]} and {line}).",
                                    "Give each case its own key, or merge the rows."))
            continue
        seen[parsed.key] = line
        cases.append(parsed)
    return CaseTable(table.line, tuple(cases), tuple(problems))


def _bad(contract_id, line, what, fix):
    return Problem(line, "malformed", f"A case row of {contract_id} has {what}.", fix)


def _row(contract_id, row, line):
    if len(row) != len(HEADER):
        return _bad(contract_id, line, f"{len(row)} columns instead of {len(HEADER)}", "Fill every column; leave one blank rather than dropping it.")
    key, when, status, answer, emits, sets = (c.strip() for c in row)
    if not CASE_KEY.match(key):
        return _bad(contract_id, line, f"the case key '{key}'", "Write the key in snake_case, such as out_of_stock.")
    if when not in BLANK and not WHEN.match(when):
        return _bad(contract_id, line, f"a When it cannot read ('{when}')",
                    "Write '<field> is <value>' or '<field> in [a, b]', joined by 'and', or leave it blank.")
    if not STATUS.match(status):
        return _bad(contract_id, line, f"the status '{status}'", "Use a three-digit code such as 409, or ok or error.")
    event_ids = () if emits in BLANK else tuple(p.strip() for p in emits.split(","))
    if any(not EVENT_ID.match(e) for e in event_ids):
        return _bad(contract_id, line, f"an Emits it cannot read ('{emits}')", "List event IDs such as EVT-003, separated by commas, or leave it blank.")
    changes = []
    for entry in () if sets in BLANK else [p.strip() for p in sets.split(";")]:
        match = SETS_ENTRY.match(entry)
        if not match:
            return _bad(contract_id, line, f"a Sets it cannot read ('{entry}')",
                        "Write '<entity>: <from>→<to>' (several as '<from>→<to>, <from>→<to>') or '<entity>: <state>', separated by ';'.")
        entity = match["entity"].strip()
        if match["state"]:
            changes.append((entity, "", match["state"]))
            continue
        starts = []
        for pair in (PAIR.match(p.strip()) for p in match["pairs"].split(",")):
            if pair["frm"] in starts:
                return _bad(contract_id, line, f"two changes of {entity} from {pair['frm']}", "Give each starting state one change.")
            starts.append(pair["frm"])
            changes.append((entity, pair["frm"], pair["to"]))
    return Case(key, "" if when in BLANK else when, status, answer, event_ids, tuple(changes), line)


def facts_problems(contract):
    """(line, message, fix) for a Can time out, Retries or Idempotent bullet whose value is not one the checker can read."""
    out = []
    for label, says in (("Can time out", "it can time out"), ("Idempotent", "it is idempotent")):
        bullet = contract.facts.get(label)
        if bullet and bullet.value.strip().lower() not in YES_NO:
            out.append((bullet.line, f"{contract.id} says {says}: '{bullet.value.strip()}'.", "Write yes or no."))
    bullet = contract.facts.get("Retries")
    if bullet and not RETRIES.match(bullet.value.strip().lower()):
        out.append((bullet.line, f"{contract.id} says its retries are '{bullet.value.strip()}'.",
                    "Write none, or how many times the caller tries again and after which answers: 2 after timeout, unavailable."))
    return out


def yes_no(contract, label):
    """True or False for a yes or no bullet; None when it is missing or unreadable (facts_problems says which)."""
    bullet = contract.facts.get(label)
    value = bullet.value.strip().lower() if bullet else ""
    return {"yes": True, "no": False}.get(value)


def retries(value):
    """(tries again, (retried case keys, ...)) from a Retries value; (0, ()) for none; None when unreadable."""
    match = RETRIES.match(value.strip().lower())
    if not match:
        return None
    if not match["count"]:
        return 0, ()
    return int(match["count"]), tuple(k.strip() for k in match["keys"].split(","))


def vault_events(vault):
    """Event IDs the vault names: a page whose id, or a level-3 heading whose first word, is EVT-nnn."""
    found = {p.id for p in vault.pages if EVENT_ID.match(p.id)}
    for page in vault.pages:
        found.update(h.text.split()[0] for h in page.headings if h.level == 3 and EVENT_HEADING.match(h.text))
    return found


def vault_entities(vault):
    """Entity IDs and lower-case names: a level-3 heading `### ENT-nnn <name>`, or a page whose id is ENT-nnn."""
    found = set()
    for page in vault.pages:
        if re.match(r"^ENT-\d{3}$", page.id):
            found.update((page.id, str(page.meta.get("title", "")).lower()))
        for h in page.headings:
            if h.level == 3 and ENTITY_HEADING.match(h.text):
                words = h.text.split(None, 1)
                found.update((words[0], words[1].lower() if len(words) > 1 else ""))
    found.discard("")
    return found
