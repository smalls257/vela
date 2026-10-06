"""The question catalogue as data. Pure: takes the parsed YAML, returns a Catalogue.

Code decides what a vault owes; the model only decides how to ask. So a trigger is a small
declarative condition this module reads, never Python it runs: no eval, no exec, no lookup of
an attribute by name. A trigger may test only the fields TRIGGER_FIELDS lists for its scope,
against values those fields can take, so a typo in the catalogue is an error at load, not a
question that silently never fires. A catalogue that cannot be read raises CatalogueError, and
the CLI exits 2: an empty catalogue would make every vault look as if it owed nothing.
"""
import re
from dataclasses import dataclass

from planner import schema

SCOPES = ("initiative", "app", "contract", "capability", "party", "stored-value")
SEVERITIES = ("high", "normal")
BLOCK_KINDS = ("app", "contract", "requirement", "capability", "decision", "epic")
CREATES = ("party", "stored-value")
REQUIRED = ("id", "area", "scope", "trigger", "question", "why", "severity")
OPTIONAL = ("blocks", "creates", "mentions")
ENTRY_ID_RE = re.compile(r"^Q-(?P<area>[A-Z]{3})-\d{2}$")
AREA_RE = re.compile(r"^[A-Z]{3}$")
WORD_RE = re.compile(r"^[a-z]+$")

# The fields a trigger may test, per scope, and the values each may take. None: any text.
TRIGGER_FIELDS = {
    "initiative": {},
    "app": {"change": schema.ENUMS["change@app-building-blocks"], "state": schema.STATE_ITEM,
            "stage": schema.ENUMS["stage"]},
    "contract": {"change": schema.CONTRACT_CHANGES, "state": schema.CONTRACT_STATES, "provider": ("external", "app")},
    "capability": {"change": schema.ENUMS["change@capability"], "state": schema.PAGE_TYPES["capability"]["states"],
                   "origin": schema.ENUMS["origin"], "domain": None},
    "party": {"relationship": schema.PARTY_RELATIONSHIPS},
    "stored-value": {},
}
CONDITION_RE = re.compile(r"^(?P<field>[a-z][a-z_]*)(?:: (?P<value>[^\[\],]+)| in \[(?P<values>[^\[\]]+)\])$")


class CatalogueError(ValueError):
    """The catalogue cannot be read. The message lists every problem found."""


@dataclass(frozen=True)
class Condition:
    field: str
    values: tuple  # lower-case; the condition holds when the subject's field is one of them


@dataclass(frozen=True)
class Trigger:
    text: str
    conditions: tuple  # of Condition, all must hold; empty for `exists`

    def matches(self, facts):
        """Whether a subject with these facts owes the entry. `facts` maps field -> lower-case text;
        a missing or non-text field never matches, so an untyped subject owes nothing it was not typed for."""
        return all(isinstance(facts.get(c.field), str) and facts[c.field] in c.values for c in self.conditions)


@dataclass(frozen=True)
class Entry:
    id: str
    area: str
    scope: str
    trigger: Trigger
    question: str
    why: str
    severity: str
    blocks: tuple  # of BLOCK_KINDS
    creates: str  # "" or one of CREATES: the subject kind a yes to this question creates
    mentions: tuple  # lower-case words that, untyped in a fact, suggest the subject this entry creates


@dataclass(frozen=True)
class Catalogue:
    version: int
    areas: tuple  # ((code, label), ...) in file order
    entries: tuple  # of Entry, sorted by id

    def entry(self, entry_id):
        return next((e for e in self.entries if e.id == entry_id), None)

    @property
    def area_codes(self):
        return tuple(code for code, _ in self.areas)

    def area_label(self, code):
        return dict(self.areas).get(code, code)


EMPTY = Catalogue(0, (), ())


def parse_trigger(text, scope):
    """A Trigger, or CatalogueError naming what is wrong with the text.

    Grammar: `exists`, or conditions joined by ` and `, each `field: value` or `field in [a, b]`.
    Values are lower-case words and may hold spaces, as in `new consumers`."""
    if not isinstance(text, str) or not text.strip():
        raise CatalogueError("trigger must be text, such as 'exists' or 'change in [new, changed]'")
    text = " ".join(text.split())
    if text == "exists":
        return Trigger(text, ())
    fields = TRIGGER_FIELDS.get(scope, {})
    conditions = []
    for part in text.split(" and "):
        match = CONDITION_RE.match(part)
        if not match:
            raise CatalogueError(f"trigger part '{part}' is not 'field: value' or 'field in [a, b]'")
        field = match["field"]
        if field not in fields:
            allowed = ", ".join(fields) or "none: use exists"
            raise CatalogueError(f"trigger field '{field}' is not one a {scope} subject has (fields: {allowed})")
        raw = [match["value"]] if match["value"] is not None else match["values"].split(",")
        values = tuple(v.strip().lower() for v in raw)
        if any(not v for v in values):
            raise CatalogueError(f"trigger part '{part}' has an empty value")
        allowed_values = fields[field]
        bad = [v for v in values if allowed_values is not None and v not in allowed_values]
        if bad:
            raise CatalogueError(f"trigger value {', '.join(repr(v) for v in bad)} is not one {field} can take "
                                 f"({', '.join(allowed_values)})")
        conditions.append(Condition(field, values))
    return Trigger(text, tuple(conditions))


def _text(entry, key, problems, where):
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{where}: '{key}' must be text")
        return ""
    return " ".join(value.split())


def _word_list(entry, key, allowed, problems, where):
    value = entry.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        problems.append(f"{where}: '{key}' must be a list of words")
        return ()
    out = tuple(v.strip().lower() for v in value)
    bad = [v for v in out if (allowed is not None and v not in allowed) or (allowed is None and not WORD_RE.match(v))]
    if bad:
        hint = f" (use: {', '.join(allowed)})" if allowed is not None else " (one lower-case word each)"
        problems.append(f"{where}: '{key}' has {', '.join(repr(v) for v in bad)}{hint}")
    return out


def _entry(raw, n, areas, problems):
    where = f"entries[{n}]"
    if not isinstance(raw, dict):
        problems.append(f"{where} must be a mapping")
        return None
    entry_id = raw.get("id")
    if isinstance(entry_id, str):
        where = f"{where} {entry_id}"
    unknown = sorted(str(k) for k in raw if k not in REQUIRED + OPTIONAL)
    if unknown:
        problems.append(f"{where}: unknown field {', '.join(unknown)}")
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        problems.append(f"{where}: missing {', '.join(missing)}")
        return None
    before = len(problems)
    match = ENTRY_ID_RE.match(entry_id) if isinstance(entry_id, str) else None
    if not match:
        problems.append(f"{where}: id must look like Q-FIN-01")
    area = raw["area"]
    if area not in areas:
        problems.append(f"{where}: area {area!r} is not one of {', '.join(areas)}")
    elif match and match["area"] != area:
        problems.append(f"{where}: id {entry_id} does not carry its area {area}")
    scope = raw["scope"]
    if scope not in SCOPES:
        problems.append(f"{where}: scope {scope!r} is not one of {', '.join(SCOPES)}")
    severity = raw["severity"]
    if severity not in SEVERITIES:
        problems.append(f"{where}: severity {severity!r} is not one of {', '.join(SEVERITIES)}")
    question, why = _text(raw, "question", problems, where), _text(raw, "why", problems, where)
    blocks = _word_list(raw, "blocks", BLOCK_KINDS, problems, where)
    mentions = _word_list(raw, "mentions", None, problems, where)
    creates = raw.get("creates", "")
    if creates and creates not in CREATES:
        problems.append(f"{where}: creates {creates!r} is not one of {', '.join(CREATES)}")
    if (creates or mentions) and scope != "initiative":
        problems.append(f"{where}: only an initiative-scope entry may create a subject or list mentions")
    if mentions and not creates:
        problems.append(f"{where}: mentions need a creates, the subject kind the words suggest")
    trigger = None
    if scope in SCOPES:
        try:
            trigger = parse_trigger(raw["trigger"], scope)
        except CatalogueError as exc:
            problems.append(f"{where}: {exc}")
    if len(problems) > before or trigger is None:
        return None
    return Entry(entry_id, area, scope, trigger, question, why, severity, blocks, creates or "", mentions)


def parse_catalogue(data):
    """The Catalogue the YAML describes, or CatalogueError listing every problem."""
    if not isinstance(data, dict):
        raise CatalogueError("the catalogue must be a mapping with version, areas and entries")
    problems = []
    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        problems.append("'version' must be a whole number, 1 or more")
    raw_areas = data.get("areas")
    areas = []
    if not isinstance(raw_areas, dict) or not raw_areas:
        problems.append("'areas' must map each area code, such as FIN, to its label")
    else:
        for code, label in raw_areas.items():
            if not isinstance(code, str) or not AREA_RE.match(code):
                problems.append(f"area code {code!r} must be three capital letters")
            elif not isinstance(label, str) or not label.strip():
                problems.append(f"area {code} needs a label")
            else:
                areas.append((code, " ".join(label.split())))
    codes = [code for code, _ in areas]
    raw_entries = data.get("entries")
    entries = []
    if not isinstance(raw_entries, list) or not raw_entries:
        problems.append("'entries' must be a non-empty list")
    else:
        for n, raw in enumerate(raw_entries, start=1):
            entry = _entry(raw, n, codes, problems)
            if entry is not None:
                entries.append(entry)
    seen = set()
    for entry in entries:
        if entry.id in seen:
            problems.append(f"{entry.id} is used by two entries")
        seen.add(entry.id)
    if problems:
        raise CatalogueError("; ".join(problems))
    return Catalogue(version, tuple(areas), tuple(sorted(entries, key=lambda e: e.id)))
