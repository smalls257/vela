"""The question catalog as data. Pure: takes the parsed YAML, returns a Catalog.

Code decides what a vault owes; the model only decides how to ask. So a trigger is a small
declarative condition this module reads, never Python it runs: no eval, no exec, no lookup of
an attribute by name. A trigger may test only the fields TRIGGER_FIELDS lists for its scope,
against values those fields can take, so a typo in the catalog is an error at load, not a
question that silently never fires. A catalog that cannot be read raises CatalogError, and
the CLI exits 2: an empty catalog would make every vault look as if it owed nothing.
"""
import re
from dataclasses import dataclass

import yaml

from vela import schema

SCOPES = ("initiative", "app", "contract", "capability", "party", "stored-value")
SEVERITIES = ("high", "normal")
BLOCK_KINDS = ("app", "contract", "requirement", "capability", "decision", "epic")
CREATES = ("party", "stored-value")
REQUIRED = ("id", "area", "scope", "trigger", "question", "why", "severity")
OPTIONAL = ("blocks", "creates", "mentions", "mention_why", "mention_except", "follows")
ENTRY_ID_RE = re.compile(r"^Q-(?P<area>[A-Z]{3})-\d{2}$")
AREA_RE = re.compile(r"^[A-Z]{3}$")
WORD_RE = re.compile(r"^[a-z]+$")
PHRASE_RE = re.compile(r"^[a-z]+\*?( [a-z]+\*?)*$")

# The fields a trigger may test, per scope, and the values each may take. None: any text.
TRIGGER_FIELDS = {
    "initiative": {},
    "app": {"change": schema.ENUMS["change@app-building-blocks"], "state": schema.STATE_ITEM},
    "contract": {"change": schema.CONTRACT_CHANGES, "state": schema.CONTRACT_STATES, "provider": ("external", "app")},
    "capability": {"change": schema.ENUMS["change@capability"], "state": schema.PAGE_TYPES["capability"]["states"],
                   "origin": schema.ENUMS["origin"], "domain": None},
    "party": {"relationship": schema.PARTY_RELATIONSHIPS},
    "stored-value": {},
}
CONDITION_RE = re.compile(r"^(?P<field>[a-z][a-z_]*)(?:: (?P<value>[^\[\],]+)| in \[(?P<values>[^\[\]]+)\])$")


class CatalogError(ValueError):
    """The catalog cannot be read. The message lists every problem found."""


class StrictLoader(yaml.SafeLoader):
    """A YAML loader that refuses a key written twice in one mapping. PyYAML keeps the last one, so a
    pasted second `severity:` would silently win and the first would never be read."""

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
            seen = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=True)
                if isinstance(key, (str, int, float, bool)) or key is None:
                    if key in seen:
                        raise yaml.constructor.ConstructorError(
                            "while reading a mapping", node.start_mark,
                            f"found duplicate key {key!r}", key_node.start_mark)
                    seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml(text):
    """The data in catalog YAML text. Raises yaml.YAMLError, including for a duplicate key."""
    return yaml.load(text, Loader=StrictLoader)  # noqa: S506 - StrictLoader is a SafeLoader


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
    mention_why: tuple = ()  # (word, why) for every mention: the reason that word is on the list
    mention_except: tuple = ()  # phrases ("credit card*") that contain a mention word and are not the subject
    follows: str = ""  # the entry ID whose copy on the same subject must be answered first; "" for none


@dataclass(frozen=True)
class Kind:
    """A kind of thing every plan needs (goals, people, money...), the running topic map's unit. `near` is symmetric:
    the kinds this one lists and the kinds that list it."""
    name: str
    means: str
    areas: tuple  # focus area codes whose questions fall under this kind
    near: tuple  # kind names, in catalog order


@dataclass(frozen=True)
class Catalog:
    version: int
    areas: tuple  # ((code, label), ...) in file order
    entries: tuple  # of Entry, sorted by id
    kinds: tuple = ()  # of Kind, in file order; () only in a test catalog that leaves `kinds` out

    def entry(self, entry_id):
        return next((e for e in self.entries if e.id == entry_id), None)

    @property
    def area_codes(self):
        return tuple(code for code, _ in self.areas)

    def area_label(self, code):
        return dict(self.areas).get(code, code)

    def kind(self, name):
        return next((k for k in self.kinds if k.name == name), None)

    @property
    def kind_names(self):
        return tuple(k.name for k in self.kinds)


EMPTY = Catalog(0, (), ())


def parse_trigger(text, scope):
    """A Trigger, or CatalogError naming what is wrong with the text.

    Grammar: `exists`, or conditions joined by ` and `, each `field: value` or `field in [a, b]`.
    Values are lower-case words and may hold spaces, as in `new consumers`."""
    if scope not in SCOPES:
        raise CatalogError(f"trigger scope {scope!r} is not one of {', '.join(SCOPES)}")
    if not isinstance(text, str) or not text.strip():
        raise CatalogError("trigger must be text, such as 'exists' or 'change in [new, changed]'")
    text = " ".join(text.split())
    if text == "exists":
        return Trigger(text, ())
    fields = TRIGGER_FIELDS.get(scope, {})
    conditions = []
    seen_fields = set()
    for part in text.split(" and "):
        match = CONDITION_RE.match(part)
        if not match:
            raise CatalogError(f"trigger part '{part}' is not 'field: value' or 'field in [a, b]'")
        field = match["field"]
        if field in seen_fields:
            raise CatalogError(f"trigger field '{field}' appears twice; use 'field in [a, b]' for either value")
        seen_fields.add(field)
        if field not in fields:
            allowed = ", ".join(fields) or "none: use exists"
            raise CatalogError(f"trigger field '{field}' is not one a {scope} subject has (fields: {allowed})")
        raw = [match["value"]] if match["value"] is not None else match["values"].split(",")
        values = tuple(v.strip().lower() for v in raw)
        if any(not v for v in values):
            raise CatalogError(f"trigger part '{part}' has an empty value")
        repeated = sorted({v for v in values if values.count(v) > 1})
        if repeated:
            raise CatalogError(f"trigger part '{part}' lists {', '.join(repr(v) for v in repeated)} twice")
        dangling = [v for v in values if v == "and" or v.endswith(" and") or v.startswith("and ")]
        if dangling:
            raise CatalogError(f"trigger value {dangling[0]!r} has a stray 'and'; join conditions as "
                                 "'field: value and field: value'")
        allowed_values = fields[field]
        bad = [v for v in values if allowed_values is not None and v not in allowed_values]
        if bad:
            raise CatalogError(f"trigger value {', '.join(repr(v) for v in bad)} is not one {field} can take "
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
    if value is None:
        problems.append(f"{where}: '{key}' is empty; leave it out or list words")
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        problems.append(f"{where}: '{key}' must be a list of words")
        return ()
    out = tuple(v.strip().lower() for v in value)
    bad = [v for v in out if (allowed is not None and v not in allowed) or (allowed is None and not WORD_RE.match(v))]
    if bad:
        hint = f" (use: {', '.join(allowed)})" if allowed is not None else " (one lower-case word each)"
        problems.append(f"{where}: '{key}' has {', '.join(repr(v) for v in bad)}{hint}")
    return out


def _phrases(raw, where, problems):
    value = raw.get("mention_except", [])
    if not isinstance(value, list) or not all(isinstance(v, str) and PHRASE_RE.match(v.strip().lower()) for v in value):
        problems.append(f"{where}: 'mention_except' must be a list of lower-case phrases, a word may end in *")
        return ()
    return tuple(v.strip().lower() for v in value)


def _mention_groups(raw, where, problems):
    """`mentions` is a list of groups written `point/points`: the forms one stem is accepted in. Returns
    (forms in order, heads in order). Only the forms listed match, so `pointer` never does."""
    value = raw.get("mentions", [])
    if value is None:
        problems.append(f"{where}: 'mentions' is empty; leave it out or list words")
        return (), ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        problems.append(f"{where}: 'mentions' must be a list of words")
        return (), ()
    forms, heads, bad = [], [], []
    for group in value:
        parts = [p.strip().lower() for p in group.split("/")]
        if not all(WORD_RE.match(p) for p in parts):
            bad.append(group)
            continue
        heads.append(parts[0])
        forms.extend((parts[0], p) for p in parts)
    if bad:
        problems.append(f"{where}: 'mentions' has {', '.join(repr(v) for v in bad)} (one lower-case word each, "
                        f"or forms joined by /)")
    return tuple(forms), tuple(heads)


def _mention_reasons(raw, where, forms, heads, problems):
    """(form, why) for every form: `mention_why` gives one reason per group, keyed by its first form."""
    whys = raw.get("mention_why", {})
    if whys is None or (whys != {} and not isinstance(whys, dict)) or \
            not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in (whys or {}).items()):
        problems.append(f"{where}: 'mention_why' must map each mention to a reason")
        return ()
    if not heads and not whys:
        return ()
    missing = [h for h in heads if h not in whys]
    extra = sorted(k for k in whys if k not in heads)
    if missing:
        problems.append(f"{where}: 'mention_why' has no reason for {', '.join(repr(h) for h in missing)}")
    if extra:
        problems.append(f"{where}: 'mention_why' names {', '.join(repr(k) for k in extra)}, which 'mentions' does not list")
    return tuple((form, whys[head].strip()) for head, form in forms if head in whys)


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
    pairs, heads = _mention_groups(raw, where, problems)
    mentions = tuple(form for _, form in pairs)
    mention_why = _mention_reasons(raw, where, pairs, heads, problems)
    exceptions = _phrases(raw, where, problems)
    if exceptions and not mentions:
        problems.append(f"{where}: mention_except needs mentions")
    creates = raw.get("creates", "")
    if creates is None or (isinstance(creates, str) and not creates.strip() and "creates" in raw):
        problems.append(f"{where}: 'creates' is empty; leave it out or use one of {', '.join(CREATES)}")
        creates = ""
    elif creates and creates not in CREATES:
        problems.append(f"{where}: creates {creates!r} is not one of {', '.join(CREATES)}")
    if (creates or mentions) and scope != "initiative":
        problems.append(f"{where}: only an initiative-scope entry may create a subject or list mentions")
    if mentions and not creates:
        problems.append(f"{where}: mentions need a creates, the subject kind the words suggest")
    follows = raw.get("follows", "")
    if "follows" in raw and not (isinstance(follows, str) and ENTRY_ID_RE.match(follows)):
        problems.append(f"{where}: follows must name an entry such as Q-REG-01")
        follows = ""
    trigger = None
    if scope in SCOPES:
        try:
            trigger = parse_trigger(raw["trigger"], scope)
        except CatalogError as exc:
            problems.append(f"{where}: {exc}")
    if len(problems) > before or trigger is None:
        return None
    return Entry(entry_id, area, scope, trigger, question, why, severity, blocks, creates or "", mentions, mention_why, exceptions, follows)


def _kind_list(raw, key, allowed, where, problems):
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        problems.append(f"{where}: '{key}' must be a list")
        return ()
    bad = [v for v in value if v not in allowed]
    if bad:
        problems.append(f"{where}: '{key}' has {', '.join(repr(v) for v in bad)} (use: {', '.join(allowed)})")
    return tuple(v for v in value if v in allowed)


def parse_kinds(raw_kinds, codes, problems):
    """The Kinds `kinds:` describes, with `near` made symmetric. Every focus area must sit under some kind: the kinds
    are the one list of what a plan covers, so an area no kind holds would be a second list nobody's map reads."""
    if raw_kinds is None:
        return ()
    if not isinstance(raw_kinds, dict) or not raw_kinds:
        problems.append("'kinds' must map each kind, such as money, to its means, areas and near")
        return ()
    names = [n for n in raw_kinds if isinstance(n, str) and WORD_RE.match(n)]
    for name in raw_kinds:
        if name not in names:
            problems.append(f"kind {name!r} must be one lower-case word")
    parsed = {}
    for name in names:
        raw, where = raw_kinds[name], f"kinds.{name}"
        if not isinstance(raw, dict):
            problems.append(f"{where} must be a mapping")
            continue
        unknown = sorted(str(k) for k in raw if k not in ("means", "areas", "near"))
        if unknown:
            problems.append(f"{where}: unknown field {', '.join(unknown)}")
        means = _text(raw, "means", problems, where)
        areas = _kind_list(raw, "areas", codes, where, problems)
        near = _kind_list(raw, "near", names, where, problems)
        if name in near:
            problems.append(f"{where}: a kind is not near itself")
        parsed[name] = (means, areas, set(near) - {name})
    for name, (_, _, near) in parsed.items():
        for other in near:
            if other in parsed:
                parsed[other][2].add(name)
    held = {code for _, areas, _ in parsed.values() for code in areas}
    for code in codes:
        if code not in held:
            problems.append(f"area {code} sits under no kind; add it to a kind's 'areas'")
    return tuple(Kind(n, m, a, tuple(k for k in names if k in near)) for n, (m, a, near) in parsed.items())


def _follows_problems(entries):
    """Why a `follows` cannot hold: it names itself, no entry, an entry of another scope, or an entry that follows one
    itself (one level only, so a follow-up never waits on a chain)."""
    by_id = {e.id: e for e in entries}
    out = []
    for entry in entries:
        if not entry.follows:
            continue
        parent = by_id.get(entry.follows)
        if entry.follows == entry.id:
            out.append(f"{entry.id}: follows itself")
        elif parent is None:
            out.append(f"{entry.id}: follows {entry.follows}, which names no entry in the catalog")
        elif parent.scope != entry.scope:
            out.append(f"{entry.id}: follows {entry.follows}, which has another scope ({parent.scope}, not {entry.scope})")
        elif parent.follows:
            out.append(f"{entry.id}: follows {entry.follows}, which follows {parent.follows} itself; one level only")
    return out


def parse_catalog(data):
    """The Catalog the YAML describes, or CatalogError listing every problem."""
    if not isinstance(data, dict):
        raise CatalogError("the catalog must be a mapping with version, areas and entries")
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
    kinds = parse_kinds(data.get("kinds"), codes, problems)
    raw_entries = data.get("entries")
    entries = []
    if not isinstance(raw_entries, list) or not raw_entries:
        problems.append("'entries' must be a non-empty list")
    else:
        for n, raw in enumerate(raw_entries, start=1):
            entry = _entry(raw, n, codes, problems)
            if entry is not None:
                entries.append(entry)
    used = {raw.get("area") for raw in raw_entries if isinstance(raw, dict)} if isinstance(raw_entries, list) else set()
    for code in codes:
        if code not in used:
            problems.append(f"area {code} is listed in 'areas' but no entry uses it")
    seen = set()
    for entry in entries:
        if entry.id in seen:
            problems.append(f"{entry.id} is used by two entries")
        seen.add(entry.id)
    problems += _follows_problems(entries)
    if problems:
        raise CatalogError("; ".join(problems))
    return Catalog(version, tuple(areas), tuple(sorted(entries, key=lambda e: e.id)), kinds)
