"""What the focused reviewers found, merged. Pure: the CLI reads each reviewer's JSON file and passes
what it read; this module checks it against the Vault and returns the merge.

Each reviewer covers one focus area in a fresh context and returns findings, each with an evidence
quote and the page it is on. The merge never votes and never debates: it keeps the union, removes
exact duplicates, and drops a finding whose quote is not on the page it cites, listing every drop
with its reason. An area whose reviewer failed, or whose output cannot be read, says "did not run"
with the reason. It never reads as "checked, none", which means the reviewer ran and found nothing.
"""
import re
from dataclasses import dataclass

from planner import catalog, questions

FIELDS = ("finding", "quote", "page", "copy", "severity", "question")
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


@dataclass(frozen=True)
class Kept:
    n: int  # its number in the merge, from 1
    area: str
    severity: str
    copy: str  # an owed copy ID, or "new" for a question the catalogue does not owe
    question: str
    finding: str
    quote: str
    page: str  # vault-relative path of the page the quote is on

    def as_dict(self):
        return {"n": self.n, "area": self.area, "severity": self.severity, "copy": self.copy, "question": self.question,
                "finding": self.finding, "quote": self.quote, "page": self.page}


@dataclass(frozen=True)
class Dropped:
    area: str
    question: str
    reason: str

    def as_dict(self):
        return {"area": self.area, "question": self.question, "reason": self.reason}


@dataclass(frozen=True)
class Duplicate:
    area: str
    question: str
    same_as: int  # the n of the kept finding it repeats

    def as_dict(self):
        return {"area": self.area, "question": self.question, "same_as": self.same_as}


@dataclass(frozen=True)
class AreaRun:
    area: str
    label: str
    reason: str  # why it did not run; "" when it ran
    found: int  # findings kept or repeated, after the drops
    dropped: int

    @property
    def ran(self):
        return not self.reason

    @property
    def status(self):
        if not self.ran:
            return f"did not run ({self.reason})"
        if not self.found and not self.dropped:
            return "checked, none"
        return f"found {self.found}" + (f", {self.dropped} dropped" if self.dropped else "")

    def as_dict(self):
        return {"area": self.area, "label": self.label, "status": self.status, "ran": self.ran, "found": self.found,
                "dropped": self.dropped, "reason": self.reason or None}


@dataclass(frozen=True)
class Merge:
    areas: tuple
    kept: tuple
    duplicates: tuple
    dropped: tuple
    ignored: tuple  # files that name no area of the catalogue

    @property
    def coverage(self):
        return "coverage: " + "; ".join(f"{a.area} {a.status}" for a in self.areas)

    @property
    def clean(self):
        """Every area ran, every quote was found, and no file was ignored."""
        return all(a.ran for a in self.areas) and not self.dropped and not self.ignored

    def as_dict(self, version):
        return {"catalogue": version, "coverage": self.coverage, "areas": [a.as_dict() for a in self.areas],
                "kept": [k.as_dict() for k in self.kept], "duplicates": [d.as_dict() for d in self.duplicates],
                "dropped": [d.as_dict() for d in self.dropped], "ignored": list(self.ignored)}


def flat(text):
    """Text as a quote is compared: curly quotes made straight, every run of whitespace one space."""
    return " ".join(text.translate(QUOTES).split())


def dedupe_key(copy, question):
    words = re.sub(r"[^a-z0-9 ]", "", flat(question).lower())
    return (copy, " ".join(words.split()))


def find_page(vault, ref):
    """The page a finding cites: by its vault-relative path, or by its basename with or without .md."""
    ref = ref.strip()
    for page in vault.pages:
        if page.path == ref:
            return page
    name = ref.rsplit("/", 1)[-1]
    return vault.page(name[:-3] if name.endswith(".md") else name)


def _check_finding(vault, raw, owed_ids):
    """(Kept fields without n, or None, and the reason it was dropped)."""
    if not isinstance(raw, dict):
        return None, "it is not an object with " + ", ".join(FIELDS)
    missing = [f for f in FIELDS if not isinstance(raw.get(f), str) or not raw[f].strip()]
    if missing:
        return None, f"it has no {', '.join(missing)}"
    severity = raw["severity"].strip().lower()
    if severity not in catalog.SEVERITIES:
        return None, f"severity '{raw['severity']}' is not high or normal"
    copy = raw["copy"].strip()
    if copy.lower() == "new":
        copy = "new"
    elif copy not in owed_ids:
        return None, f"it names {copy}, which this vault does not owe; write new for a question of your own"
    page = find_page(vault, raw["page"])
    if page is None:
        return None, f"it cites {raw['page'].strip()}, which is not a page in this vault"
    # One quote checker for the ledger and the merge, so the two rules cannot drift apart.
    problem = questions.quote_problem(vault, f'"{raw["quote"].strip()}" in [[{page.name}]]', "its quote")
    if problem:
        return None, problem
    return (severity, copy, flat(raw["question"]), flat(raw["finding"]), flat(raw["quote"]), page.path), ""


def merge(vault, outputs, ignored=()):
    """The merge of every area's output. `outputs` maps each area code of the catalogue to
    (data, problem): the reviewer's parsed JSON, or None and why the CLI could not read it."""
    owed_ids = {c.id for c in questions.owed(vault)}
    areas, kept, duplicates, dropped, seen = [], [], [], [], {}
    for code, label in vault.catalogue.areas:
        data, problem = outputs.get(code, (None, "no findings file"))
        reason = problem
        if not reason and not isinstance(data, dict):
            reason = "its output is not a findings object"
        elif not reason and str(data.get("area", "")).strip().upper() != code:
            reason = f"its output says area {data.get('area')!r}"
        elif not reason and data.get("error"):
            reason = f"the reviewer reported: {flat(str(data['error']))}"
        elif not reason and not isinstance(data.get("findings"), list):
            reason = "its output has no findings list"
        if reason:
            areas.append(AreaRun(code, label, reason, 0, 0))
            continue
        found = lost = 0
        for raw in data["findings"]:
            fields, why = _check_finding(vault, raw, owed_ids)
            question = flat(str(raw.get("question", ""))) if isinstance(raw, dict) else ""
            if fields is None:
                dropped.append(Dropped(code, question or "(no question)", why))
                lost += 1
                continue
            found += 1
            severity, copy, question, finding, quote, page = fields
            key = dedupe_key(copy, question)
            if key in seen:
                duplicates.append(Duplicate(code, question, seen[key]))
                continue
            entry = Kept(len(kept) + 1, code, severity, copy, question, finding, quote, page)
            seen[key] = entry.n
            kept.append(entry)
        areas.append(AreaRun(code, label, "", found, lost))
    return Merge(tuple(areas), tuple(kept), tuple(duplicates), tuple(dropped), tuple(sorted(ignored)))
