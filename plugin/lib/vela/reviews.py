"""What the focused reviewers found, merged. Pure: the CLI reads each reviewer's JSON file and passes
what it read; this module checks it against the Vault and returns the merge.

Each reviewer covers one focus area in a fresh context and returns findings, each with an evidence
quote and the page it is on. The merge never votes and never debates: it keeps the union, removes
exact duplicates, folds the same gap raised by several areas into one finding that lists them all,
and drops a finding whose quote is not on the page it cites, or says nothing about what the finding
asks, listing every drop with its reason. An area whose reviewer failed, or whose output cannot be
read, says "did not run" with the reason. It never reads as "checked, none", which means the reviewer
ran and found nothing. An area the session left out because nothing in it was in scope says so.
"""
import re
from dataclasses import dataclass

from vela import catalog, parse, questions

FIELDS = ("finding", "quote", "page", "copy", "severity", "question")
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})

# Near-duplicates across areas. Each area's reviewer asks about one gap in its own words: in the v3 full run
# the hotel agreements were asked three times (DAT, PTN, REG) with a Jaccard of 0.16 to 0.30 between them,
# and all three quoted the same line. So near-identical wording alone (NEAR) merges, and so does a looser
# match when both findings quote the same words on the same page (NEAR_SAME_QUOTE). Code decides, never a model.
NEAR = 0.6
NEAR_SAME_QUOTE = 0.2
SKIPPED = "skipped (nothing in scope)"
UNRELATED_QUOTE = "the quote does not mention what the finding is about"
# A new question is about what this session changed. One about a page it left alone was owed when that page was
# written, and raising it again every session is what made the digest grow faster than any lead could answer it.
OUTSIDE_CHANGE = "it is a new question about a page this session did not change"
# A decided page or item is settled. A new question about it reopens what a Grill closed, so only one that would
# change a decision, a contract, a liability or the lawful use of data, which is what high severity means, is kept.
ON_DECIDED = "it is a new question about something already decided, and it is not high severity"

# Content words: English, lower case, function words gone, then a crude stem (one suffix off, a final e off,
# the first STEM_LENGTH letters kept), so "owner", "owns" and "ownership" meet. Crude on purpose: the rule
# must be one a reader can run by hand.
STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being below between
both but by can could did do does doing done down during each either else ever every few for from further had
has have having he her here hers him his how i if in into is it its itself just let may me might more most must
my no nor not now of off on once one only or other our ours out over own per same shall she should so some such
than that the their theirs them then there these they this those through to too two under until up upon us very
was we were what when where whether which while who whom whose why will with within without would yet you your
""".split())
SUFFIXES = (("ations", ""), ("ation", ""), ("ments", ""), ("ment", ""), ("ships", ""), ("ship", ""), ("ions", ""),
            ("ion", ""), ("ings", ""), ("ing", ""), ("ies", "y"), ("ied", "y"), ("ers", ""), ("er", ""), ("ed", ""),
            ("es", ""), ("s", ""))
STEM_LENGTH = 6
WORD_RE = re.compile(r"\w+")
BULLET_LABEL_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\*\*([^*]+?)\*\*")


@dataclass(frozen=True)
class Kept:
    n: int  # its number in the merge, from 1
    area: str  # the first area that raised it
    severity: str
    copy: str  # an owed copy ID, an open reviewer question (R-FIN-01), or "new" for a question nobody has recorded
    question: str
    finding: str
    quote: str
    page: str  # vault-relative path of the page the quote is on
    areas: tuple = ()  # every area that raised it, the first first; the others' own words are in the duplicates

    @property
    def area_list(self):
        return self.areas or (self.area,)

    def as_dict(self):
        return {"n": self.n, "area": self.area, "areas": list(self.area_list), "severity": self.severity,
                "copy": self.copy, "question": self.question, "finding": self.finding, "quote": self.quote,
                "page": self.page}


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
    skipped: bool = False  # the session found nothing of this area in scope, so it sent no reviewer

    @property
    def ran(self):
        return not self.reason and not self.skipped

    @property
    def status(self):
        if self.skipped:
            return SKIPPED
        if not self.ran:
            return f"did not run ({self.reason})"
        if not self.found and not self.dropped:
            return "checked, none"
        return f"found {self.found}" + (f", {self.dropped} dropped" if self.dropped else "")

    def as_dict(self):
        return {"area": self.area, "label": self.label, "status": self.status, "ran": self.ran,
                "skipped": self.skipped, "found": self.found, "dropped": self.dropped, "reason": self.reason or None}


@dataclass(frozen=True)
class Merge:
    areas: tuple
    kept: tuple
    duplicates: tuple
    dropped: tuple
    ignored: tuple  # files that name no area of the catalog

    @property
    def coverage(self):
        return "coverage: " + "; ".join(f"{a.area} {a.status}" for a in self.areas)

    @property
    def clean(self):
        """Every area ran or was skipped as out of scope, every quote held up, and no file was ignored."""
        return all(a.ran or a.skipped for a in self.areas) and not self.dropped and not self.ignored

    def as_dict(self, version):
        return {"catalog": version, "coverage": self.coverage, "areas": [a.as_dict() for a in self.areas],
                "kept": [k.as_dict() for k in self.kept], "duplicates": [d.as_dict() for d in self.duplicates],
                "dropped": [d.as_dict() for d in self.dropped], "ignored": list(self.ignored)}


def flat(text):
    """Text as a quote is compared: curly quotes made straight, every run of whitespace one space."""
    return " ".join(text.translate(QUOTES).split())


def dedupe_key(copy, question):
    words = re.sub(r"[^\w ]", "", flat(question).lower())
    return (copy, " ".join(words.split()))


def stem(word):
    for suffix, replacement in SUFFIXES:
        if word.endswith(suffix) and not word.endswith("ss") and len(word) - len(suffix) + len(replacement) >= 3:
            word = word[:len(word) - len(suffix)] + replacement
            break
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word[:STEM_LENGTH]


def content_words(text):
    """The stems of the words that carry meaning: no function word, no bare number, no single letter."""
    text = re.sub(r"'s\b", "", flat(text).lower())
    return frozenset(stem(w) for w in WORD_RE.findall(text) if w not in STOPWORDS and len(w) > 1 and not w.isdigit())


def similarity(a, b):
    """The Jaccard of two texts' content words: those shared over all of them, 0 when neither has any."""
    a, b = content_words(a), content_words(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def reads_english(text):
    """True when the text has an English function word. The relevance check reads English only, so it does not
    judge a question in another language, rather than drop it for sharing no English word with its quote."""
    return any(w in STOPWORDS for w in WORD_RE.findall(flat(text).lower()))


def quote_context(page, quote):
    """Where the quote sits: the nearest heading above its line and the bold label of its bullet. A gap is
    quoted where its answer belongs, such as "- **Agreements:** none known" under "PTY-03 Repair vendors",
    so where it sits is part of what it says."""
    want = questions.normal_text(quote)
    for n, line in enumerate(page.text.split("\n"), start=1):
        if want and want in questions.normal_text(line):
            above = [h.text for h in page.headings if h.line <= n]
            label = BULLET_LABEL_RE.match(line)
            return " ".join(filter(None, (above[-1] if above else "", label.group(1) if label else "")))
    return ""


def compatible(a, b):
    """Two copies one finding can stand for: the same copy, or a question of the reviewer's own (`new`) beside
    another one or beside an open reviewer question, which the merged finding then addresses."""
    if a == b:
        return True
    return (a == "new" and b.startswith("R-")) or (b == "new" and a.startswith("R-"))


def near_duplicate(one, other):
    """True when two findings, as dicts with copy, question, quote and page, ask the same thing."""
    if not compatible(one["copy"], other["copy"]):
        return False
    score = similarity(one["question"], other["question"])
    same_quote = (one["page"] == other["page"]
                  and questions.normal_text(one["quote"]) == questions.normal_text(other["quote"]))
    return score >= NEAR or (same_quote and score >= NEAR_SAME_QUOTE)


def find_page(vault, ref):
    """The page a finding cites: by its vault-relative path, or by its basename with or without .md."""
    ref = ref.strip()
    for page in vault.pages:
        if page.path == ref:
            return page
    name = ref.rsplit("/", 1)[-1]
    return vault.page(name[:-3] if name.endswith(".md") else name)


def _check_finding(vault, raw, owed_ids, about, changed=None):
    """(Kept fields without n, or None, and the reason it was dropped). `about` maps a copy ID to what else
    names its subject: an owed copy's subject name, or an open reviewer question's own words."""
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
    elif copy.upper() in owed_ids:
        copy = owed_ids[copy.upper()]
    else:
        return None, (f"it names {copy}, which this vault does not owe and has no open reviewer question for; "
                      "write new for a question of your own")
    page = find_page(vault, raw["page"])
    if page is None:
        return None, f"it cites {raw['page'].strip()}, which is not a page in this vault"
    if copy == "new" and changed is not None and not in_change(page, raw["quote"], changed):
        return None, OUTSIDE_CHANGE
    if copy == "new" and changed is not None and severity != "high" and on_decided(vault, page, raw["quote"]):
        return None, ON_DECIDED
    # One quote checker for the ledger and the merge, so the two rules cannot drift apart.
    # A straight quote mark inside the words would end the quoted span early; quote_problem reads curly as straight.
    words = raw["quote"].strip().replace('"', "”")
    problem = questions.quote_problem(vault, f'"{words}" in [[{page.name}]]', "its quote")
    if problem:
        return None, problem
    # On the page is not enough: the quote, read where it sits, must share a content word with what is asked.
    said = content_words(raw["quote"] + " " + quote_context(page, raw["quote"]))
    if reads_english(raw["question"]) and not said & content_words(raw["question"] + " " + (about.get(copy) or "")):
        return None, UNRELATED_QUOTE
    return (severity, copy, flat(raw["question"]), flat(raw["finding"]), flat(raw["quote"]), page.path), ""


def line_of_quote(page, quote):
    """The line the quote starts on, reading curly and straight quote marks alike, or None."""
    for words in (quote.strip(), quote.strip().replace("”", '"').replace("“", '"'), quote.strip().replace('"', "”")):
        at = page.text.find(words)
        if at >= 0:
            return page.text.count("\n", 0, at) + 1
    return None


def in_change(page, quote, changed):
    """Whether a quote sits in what the session changed: `changed` maps a page path to None (the whole page) or to
    its changed (first, last) line ranges."""
    if page.path not in changed:
        return False
    ranges = changed[page.path]
    if ranges is None:
        return True
    line = line_of_quote(page, quote)
    return line is not None and any(first <= line <= last for first, last in ranges)


def on_decided(vault, page, quote):
    """Whether a quote sits on a decided page, or under a decided item's heading or History block."""
    if page.meta.get("state") == "decided":
        return True
    line = line_of_quote(page, quote)
    if line is None:
        return False
    history = parse.history_items(page)
    for found in vault.items.values():
        for item in found:
            if item.page is not page or item.fact("State") != "decided":
                continue
            later = [h.line for h in page.headings if h.line > item.line and h.level <= 3]
            end = later[0] if later else len(page.text.split("\n")) + 1
            span = history.get(item.id)
            if item.line <= line < end or (span and span[0] <= line < span[1]):
                return True
    return False


def open_reviewer_ids(vault):
    """The R-<AREA>-nn ids a finding may address: reviewer questions still open, or whose row has an error."""
    return {r.copy.upper(): r.copy for r in questions.reviewer_rows(vault)
            if r.state == "open" or not questions.row_valid(vault, r)}


def merge(vault, outputs, ignored=(), only=None, skipped=(), changed=None):
    """The merge of every area's output. `outputs` maps each area code of the catalog to
    (data, problem): the reviewer's parsed JSON, or None and why the CLI could not read it.
    `only` lists the area codes that ran, for a re-run or a checkpoint that skips some. The others are neither
    read nor reported, except those in `skipped`, which are reported as skipped and never read. `changed`, when
    given, maps each page this session changed to None or its changed line ranges: a new question quoting any
    other page or line is dropped."""
    owed = questions.owed(vault)
    owed_ids = {c.id.upper(): c.id for c in owed}
    owed_ids.update(open_reviewer_ids(vault))
    about = {c.id: c.subject.title for c in owed}
    about.update({r.copy: r.get("question") for r in questions.reviewer_rows(vault)})
    areas, kept, duplicates, dropped, seen = [], [], [], [], {}
    for code, label in vault.catalog.areas:
        if code in skipped:
            areas.append(AreaRun(code, label, "", 0, 0, skipped=True))
            continue
        if only is not None and code not in only:
            continue
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
            fields, why = _check_finding(vault, raw, owed_ids, about, changed)
            question = flat(str(raw.get("question", ""))) if isinstance(raw, dict) else ""
            if fields is None:
                dropped.append(Dropped(code, question or "(no question)", why))
                lost += 1
                continue
            found += 1
            severity, copy, question, finding, quote, page = fields
            new = {"n": len(kept) + 1, "areas": [code], "severity": severity, "copy": copy, "question": question,
                   "finding": finding, "quote": quote, "page": page}
            key = dedupe_key(copy, question)
            same = kept[seen[key] - 1] if key in seen else next(
                (k for k in kept if code not in k["areas"] and near_duplicate(k, new)), None)
            if same is not None:
                _fold(same, new)
                duplicates.append(Duplicate(code, question, same["n"]))
                continue
            seen[key] = new["n"]
            kept.append(new)
        areas.append(AreaRun(code, label, "", found, lost))
    entries = tuple(Kept(k["n"], k["areas"][0], k["severity"], k["copy"], k["question"], k["finding"], k["quote"],
                         k["page"], tuple(k["areas"])) for k in kept)
    return Merge(tuple(areas), entries, tuple(duplicates), tuple(dropped), tuple(sorted(ignored)))


def _fold(kept, other):
    """One finding for one gap: every area that raised it, high if any of them said high, and an open reviewer
    question's ID when one of them addressed it, so close never opens a second row for the same question."""
    if other["areas"][0] not in kept["areas"]:
        kept["areas"].append(other["areas"][0])
    if other["severity"] == "high":
        kept["severity"] = "high"
    if kept["copy"] == "new" and other["copy"] != "new":
        kept["copy"] = other["copy"]
