#!/usr/bin/env python3
"""Precision of what a run wrote: one judge call over a fixed, stratified sample of the final vault's items, each
classed as backed, duplicate, padding or unsupported.

The Violation this exists to prevent is the Paper Tiger: recall against the persona key can rise because a session
wrote more, and more is not better when the extra is padding, the same fact twice, or facts nobody gave. Recall says
what the vault caught; precision says what share of what it wrote can be trusted. compare_runs.py reads both, and
the verdict needs both.

How an item is read:
- backed: it says what a source document or the lead's own words say (the judge quotes the place), or it is plainly
  an open question, an assumption or a risk put to the lead rather than a fact (the judge quotes the item's own
  words that frame it so). A gap the assistant surfaced from its own knowledge is a question, so it is not punished.
- duplicate: the same fact as another item of the vault; the driver lists each item's two nearest neighbours by
  shared words, and the judge names the one it repeats.
- padding: no information: a placeholder, a restated heading, boilerplate.
- unsupported: stated as fact, and in neither the sources nor the lead's words.
A citation the driver can't find (a quote not in the document, the turn or the item, a neighbour not listed) turns
the item unsupported, and the reason is listed under `dropped`, as run.py's judge drops an unquoted yes.
Precision is 1 - (unsupported + padding) / sampled; the duplicate rate is reported beside it.

Only text the model wrote is sampled. The Violation this prevents is a Paper Tiger of the measurement itself: a
generated or fixed-format line judged as padding moves the score with the tool's output, not with the voice. These
kinds are excluded from the population by rule (GENERATED_KINDS below), whatever the persona or the run:
- handoff pages (handoffs/): written whole by vela handoff, its table rows and "Not settled" sentences included;
- "- Trace:" lines (epics, capabilities, slices, any page) and the "- **Decision:** [[link]]" line of an epic:
  bookkeeping the CLI's format fixes, the model only picks the IDs;
- lines a template generates: any line in plugin/catalog/template-lines.txt or template-lines-retired.txt, and any
  paragraph the vault template already holds word for word;
- tables and rows the CLI renders verbatim: the <!-- generated: --> blocks.
A table cell, a sentence or a capture the model wrote stays in, however thin it is.

The default pass is POOLED: SEEDS (4 seeds of SAMPLE_SIZE 30 = 120 items), one judge call per seed. One 30-item pass
swings about 15 points, so the headline is the pooled precision with a plus-minus, the half-range of the per-seed
precisions. --quick runs one pass, for a cheap look; its score has no plus-minus and carries that swing.

Each pass is stratified by page type with a fixed seed, so two runs are sampled the same way and a rerun of one run
picks the same items. Session records (sessions/) and the team's documents (docs/) are left out: the first copy the
lead's words by design, and the second are the team's, not the plan's.

Usage (a paid judge call unless --stub; the preflight sends one tiny call first):
  python3 tests/sim/precision.py <run-dir> --judge-model <id> --budget <usd> [--arm vela] [--stub]
                                 [--size 30] [--seed N]
Writes <run-dir>/<arm>/precision.json and prints the rates. Exit: 0 scored; 2 a tool failure (claude, the judge's
JSON twice, a run folder it can't read); 4 the preflight failed, so nothing else was sent.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import random
import re
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
SAMPLE_SIZE = 30
SEED = 20261015  # the single quick pass
SEEDS = (101, 202, 303, 404)  # the default pooled pass: 4 x SAMPLE_SIZE
CLASSES = ("backed", "duplicate", "padding", "unsupported")
BASES = ("source", "lead", "question")
AGAINST = ("unsupported", "padding")  # what counts against precision
BUDGET_USD = 1.50  # one call's cap: about 50k tokens in, a thinking reply out
PREFLIGHT_USD = 0.50
INPUT_CHARS = 220_000
ITEM_CHARS = 1_400
NEIGHBOUR_CHARS = 350
NEIGHBOURS = 2
MIN_JACCARD = 0.3
MIN_WORDS = 6
LEAD_TURN_LIMITS = (None, 1200, 600, 300)
SKIP_TOP = {"docs", "sessions"}
STOP = frozenset("""a about above after again all also an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here hers him
his how i if in into is it its itself just me more most my no nor not now of off on once only or other our ours out over
own same she should so some such than that the their theirs them then there these they this those through to too under
until up very was we were what when where which while who whom why will with would you your yours""".split())


class JudgeFailure(Exception):
    """The judge did not give a reply the driver can read. run.py turns it into its ToolFailure (exit 2)."""


def sibling(name):
    """A module of tests/sim, loaded by path under its own name, as probe.py loads run.py."""
    key = f"sim_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        spec.loader.exec_module(module)
    return sys.modules[key]


compare = sibling("compare_runs")


def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[\"'“”‘’`*_]", "", str(text))).strip().lower()


# ------------------------------------------------------------------ the items of a vault

class Unit:
    """One written item: a section under an item heading, or, on a page with none, a paragraph, bullet or table row."""

    def __init__(self, path, page_type, key, text):
        self.path, self.page_type, self.key, self.text = path, page_type, key, text.strip()[:ITEM_CHARS]
        self.words = frozenset(w for w in re.findall(r"[a-z0-9]{4,}", normalize(self.text)) if w not in STOP)

    def __repr__(self):
        return f"Unit({self.path}#{self.key})"


def clean(body):
    return compare.FENCE.sub(" ", compare.COMMENT.sub(" ", compare.GENERATED.sub(" ", body)))


def item_sections(lines):
    """compare_runs.sections, each body cut at its first nested item heading, so a parent and its child are two
    items, not one item written twice."""
    out = []
    for level, item_id, name, body in compare.sections(lines):
        cut = next((i for i, line in enumerate(body) if compare.ITEM_HEADING.match(line)), len(body))
        out.append((item_id, name, body[:cut]))
    return out


def loose_units(body):
    """Paragraphs, bullets and table rows of a page with no item headings, each long enough to say something."""
    out = []
    for block in re.split(r"\n\s*\n", body):
        lines = [x for x in block.splitlines() if x.strip() and not compare.HEADING.match(x)]
        if not lines:
            continue
        if all(re.match(r"^\s*(?:[-*+]|\d+\.)\s|^\s*\|", x) for x in lines):
            out += [x for x in lines if not re.match(r"^\s*\|[\s|:-]*\|\s*$", x)]
        else:
            out.append(" ".join(x.strip() for x in lines))
    return [x for x in out if len(re.findall(r"\w+", x)) >= MIN_WORDS]


TEMPLATE = HERE.parent.parent / "plugin" / "template"
CATALOG = HERE.parent.parent / "plugin" / "catalog"
GENERATED_KINDS = ("handoff page", "epic trace line", "epic decision link", "template line", "generated block")
BOOKKEEPING = {  # name: (page types it applies to, or None for every page, the line)
    "epic trace line": (None, re.compile(r"^\s*[-*+]\s+Trace:")),
    "epic decision link": ({"epic"}, re.compile(r"^\s*[-*+]\s+\*\*Decision:\*\*\s+\[\[[^\]]*\]\]\s*$")),
}


def is_handoff_page(rel):
    return pathlib.PurePosixPath(rel).parts[0] == "handoffs"


def template_lines(catalog=CATALOG):
    """Normalized lines the templates generate, current and retired, so a vault that still carries one is not sampled."""
    out = set()
    for name in ("template-lines.txt", "template-lines-retired.txt"):
        path = pathlib.Path(catalog) / name
        if path.is_file():
            out |= {normalize(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()}
    return out


def without_generated_lines(body, page_type, lines_given):
    """The body minus the lines the tool wrote: an epic's trace and decision-link lines, and template sentences."""
    kept = []
    for line in body.splitlines():
        if any(r.match(line) for types, r in BOOKKEEPING.values() if types is None or page_type in types):
            continue
        if line.strip() and normalize(line.strip()) in lines_given:
            continue
        kept.append(line)
    return "\n".join(kept)


def template_text(rel, template=TEMPLATE):
    path = pathlib.Path(template) / rel
    return normalize(path.read_text(encoding="utf-8", errors="replace")) if path.is_file() else ""


def units_of(vault, template=TEMPLATE, catalog=CATALOG):
    """Every item the model wrote, in page order (nothing in GENERATED_KINDS). A paragraph or section the vault template already holds, word
    for word, was never written by a session, so it is not sampled (it would read as padding the run never wrote)."""
    out, lines_given = [], template_lines(catalog)
    for rel, text in compare.vault_files(pathlib.Path(vault)):
        if rel.parts[0] in SKIP_TOP or is_handoff_page(rel.as_posix()):
            continue
        meta, body = compare.frontmatter(text)
        page_type = meta.get("type") or f"untyped ({rel.parts[0] if len(rel.parts) > 1 else 'root'})"
        if page_type == "session":
            continue
        body, given = without_generated_lines(clean(body), page_type, lines_given), template_text(rel, template)
        written = lambda text: not (given and normalize(text) in given)
        found = item_sections(body.splitlines())
        if found:
            for item_id, name, lines in found:
                text = f"{item_id} {name}\n" + "\n".join(lines)
                if len(re.findall(r"\w+", text)) >= MIN_WORDS and written(text):
                    out.append(Unit(rel.as_posix(), page_type, item_id, text))
            continue
        for n, text in enumerate(loose_units(body), 1):
            if written(text):
                out.append(Unit(rel.as_posix(), page_type, f"part {n}", text))
    return out


def allocation(sizes, size):
    """Items per stratum: each stratum's share of `size`, at least one each, rounded by largest remainder."""
    total = sum(sizes.values())
    if total <= size:
        return dict(sizes)
    quota = {n: size * k / total for n, k in sizes.items()}
    out = {n: min(sizes[n], max(1, int(quota[n]))) for n in sizes}
    while sum(out.values()) < size:
        n = max((n for n in sizes if out[n] < sizes[n]), key=lambda n: (quota[n] - out[n], n))
        out[n] += 1
    while sum(out.values()) > size:
        n = min((n for n in sizes if out[n] > 1), key=lambda n: (quota[n] - out[n], n))
        out[n] -= 1
    return out


def stratified_sample(units, size=SAMPLE_SIZE, seed=SEED):
    """[(label, unit)]: `size` items drawn per page type with a fixed seed, labelled P1, P2... in page-type order."""
    strata = collections.defaultdict(list)
    for u in units:
        strata[u.page_type].append(u)
    counts = allocation({k: len(v) for k, v in strata.items()}, size)
    picked = []
    for page_type in sorted(strata):
        pool = sorted(strata[page_type], key=lambda u: (u.path, u.key))
        rng = random.Random(f"{seed}:{page_type}")
        picked += sorted(rng.sample(pool, counts[page_type]), key=lambda u: (u.path, u.key))
    return [(f"P{i}", u) for i, u in enumerate(picked, 1)]


def neighbours(unit, units, k=NEIGHBOURS):
    """The k other items that share most words with `unit` (Jaccard at least MIN_JACCARD), most similar first."""
    scored = []
    for other in units:
        if other is unit or not (unit.words and other.words):
            continue
        j = len(unit.words & other.words) / len(unit.words | other.words)
        if j >= MIN_JACCARD:
            scored.append((-j, other.path, other.key, other))
    return [s[-1] for s in sorted(scored, key=lambda s: s[:3])[:k]]


# ------------------------------------------------------------------ the judge's input

SYSTEM_PROMPT = """SIMULATOR JUDGE: precision. You check what a simulated planning assistant wrote in its vault. You are
mechanical, not a critic. You have no tools. Reply with one JSON object and nothing else: no prose, no fences.

You get the lead's source documents, every lead turn of the conversation, and a sample of items the assistant wrote,
each with up to two other items of the vault that share words with it. Class every sampled item as exactly one of:
- padding: the item carries no information: a placeholder, a heading restated, boilerplate a template would hold.
- duplicate: it states the same fact as one of the OTHER ITEMS listed under it. "duplicate_of" is that item's label.
- backed: what it says is in a source document or the lead's words, or it is plainly an open question, an assumption
  or a risk put to the lead, not a statement of fact. "basis" is "source" (then "where" is the document's name exactly
  as listed after SOURCE, and "quote" is copied from that document), "lead" (then "turn" is the lead turn's number
  and "quote" is copied from that turn), or "question" (then "quote" is copied from the item itself, the words that
  make it a question, an assumption or a risk).
- unsupported: it states as fact something neither the documents nor the lead's words give. "quote" is copied from
  the item: the words that are unsupported.
Check in that order: padding, then duplicate, then backed or unsupported. An item that adds a reasonable inference to
what the lead said is backed only if the inference is marked as one; a fact stated plainly must be in the sources.
Every quote is copied exactly, at most 25 words. A quote the driver can't find in the place you name turns the item
unsupported. If you are unsure whether an item is backed, it is unsupported.

For every item write "grounds" first: one or two sentences naming what you compared it with. Then the class.

The JSON shape, with every sampled ID listed exactly once:
{"items": [{"id": "P1", "grounds": "...", "class": "backed", "basis": "lead", "turn": 12, "where": null,
  "quote": "...", "duplicate_of": null}]}
"""


def lead_turns(spoken):
    return {e["turn"]: e for e in spoken if e.get("speaker") == "lead" and "turn" in e}


def lead_block(turns, limit):
    parts = []
    for n, e in sorted(turns.items()):
        text = " ".join(str(e.get("text") or "").split())
        if limit and len(text) > limit:
            text = text[:limit] + " [...]"
        who = f" ({e['persona']})" if e.get("persona") else ""
        parts.append(f"[T{n}] LEAD{who}: {text}")
    return "\n".join(parts) or "none"


def build_input(sample, units, docs, spoken):
    """(text, neighbour labels per item, cuts). docs is [{name, text}]; spoken the transcript's spoken turns."""
    sources = "\n\n".join(f"----- SOURCE {d['name']} -----\n{d['text']}" for d in docs) or "none"
    items, labels = [], {}
    for label, unit in sample:
        near = neighbours(unit, units)
        labels[label] = {f"{label}.N{i}" for i in range(1, len(near) + 1)}
        others = "\n".join(f"  {label}.N{i} ({o.path}): {' '.join(o.text.split())[:NEIGHBOUR_CHARS]}"
                           for i, o in enumerate(near, 1)) or "  none"
        items.append(f"----- ITEM {label} ({unit.page_type}, {unit.path}) -----\n{unit.text}\nOTHER ITEMS NEAR IT:\n{others}")
    head = [f"IDS precision: {', '.join(label for label, _ in sample)}", f"SOURCE DOCUMENTS:\n{sources}"]
    tail = ["THE SAMPLED ITEMS:\n" + "\n\n".join(items)]
    turns, cuts = lead_turns(spoken), []
    for limit in LEAD_TURN_LIMITS:
        chat = lead_block(turns, limit)
        text = "\n\n".join(head + [f"THE LEAD'S WORDS, every lead turn:\n{chat}"] + tail) + "\n"
        if len(text) <= INPUT_CHARS:
            if limit:
                cuts.append(f"every lead turn cut to {limit} characters to fit {INPUT_CHARS}")
            return text, labels, cuts
    raise JudgeFailure(f"the precision input is {len(text)} characters with every lead turn cut to "
                       f"{LEAD_TURN_LIMITS[-1]}, over its {INPUT_CHARS} budget")


# ------------------------------------------------------------------ the reply

def reply_problems(data, ids):
    rows = data.get("items") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return ["the reply has no 'items' list"]
    problems = []
    got = [r.get("id") for r in rows if isinstance(r, dict)]
    if sorted(got) != sorted(ids):
        problems.append(f"'items' must list {', '.join(ids)} once each, not {', '.join(map(str, got))}")
    for r in rows:
        if not isinstance(r, dict):
            problems.append("every item must be an object")
            continue
        if not str(r.get("grounds") or "").strip():
            problems.append(f"{r.get('id')}: 'grounds' is missing")
        if r.get("class") not in CLASSES:
            problems.append(f"{r.get('id')}: 'class' must be one of {', '.join(CLASSES)}")
        if r.get("class") == "backed" and r.get("basis") not in BASES:
            problems.append(f"{r.get('id')}: a backed item needs 'basis', one of {', '.join(BASES)}")
    return problems


def turn_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    found = re.fullmatch(r"\s*T?(\d+)\s*", str(value)) if isinstance(value, str) else None
    return int(found.group(1)) if found else None


def holds(text, quote):
    return isinstance(quote, str) and bool(normalize(quote)) and normalize(quote) in normalize(text)


def citation_problem(row, unit, labels, docs, turns):
    """Why the row's class can't be checked against what it cites, or None."""
    cls, quote = row["class"], row.get("quote")
    if cls == "duplicate":
        return None if row.get("duplicate_of") in labels else f"duplicate_of {row.get('duplicate_of')!r} is not listed under it"
    if cls != "backed":
        return None
    basis = row.get("basis")
    if basis == "source":
        doc = docs.get(str(row.get("where") or ""))
        return None if doc is not None and holds(doc, quote) else f"source {row.get('where')!r} does not hold the quote"
    if basis == "lead":
        n = turn_number(row.get("turn"))
        if n is None or n not in turns:
            return f"turn {row.get('turn')!r} is not a lead turn"
        return None if holds(turns[n].get("text") or "", quote) else f"lead turn T{n} does not hold the quote"
    return None if holds(unit.text, quote) else "the item does not hold the quote that frames it as a question"


def enforce(data, sample, labels, docs, spoken):
    """The judge's rows with every citation checked: a failed one turns the row unsupported and is listed."""
    by_id = {r["id"]: r for r in data["items"]}
    docs = {d["name"]: d["text"] for d in docs}
    turns = lead_turns(spoken)
    rows, dropped = [], []
    for label, unit in sample:
        row = dict(by_id[label])
        why = citation_problem(row, unit, labels[label], docs, turns)
        if why:
            dropped.append(f"{label} ({row['class']}): {why}")
            row.update(judged=row["class"], dropped=why, **{"class": "unsupported"})
        rows.append({**row, "path": unit.path, "item": unit.key, "page_type": unit.page_type})
    return rows, dropped


def summarize(rows, dropped, population, **extra):
    n = len(rows)
    counts = {c: sum(1 for r in rows if r["class"] == c) for c in CLASSES}
    rates = {c: round(counts[c] / n, 3) if n else None for c in CLASSES}
    by_type = {}
    for r in rows:
        t = by_type.setdefault(r["page_type"], {c: 0 for c in CLASSES})
        t[r["class"]] += 1
    return {"sampled": n, "population": population, "counts": counts, "rates": rates,
            "precision": round(1 - sum(counts[c] for c in AGAINST) / n, 3) if n else None,
            "by_page_type": dict(sorted(by_type.items())), "dropped": dropped, "items": rows, **extra}


def ask(send, stdin, ids):
    """(reply, None) or (None, why not scored). `send(text)` makes one call and returns claude's result object. Bad
    JSON is sent back once with the problems named, then it is a JudgeFailure; a refusal is not scored."""
    problems = []
    for _ in (1, 2):
        result = send(stdin if not problems else stdin + "\n\nYOUR LAST REPLY WAS REJECTED:\n- " + "\n- ".join(problems)
                      + "\nReply again with the JSON object only.")
        if result.get("stop_reason") == "refusal":
            return None, "the judge model refused the precision call"
        if result.get("is_error"):
            raise JudgeFailure(f"the precision judge call reported an error ({result.get('subtype')})")
        text = str(result.get("result") or "").strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
        try:
            data = json.loads(fenced.group(1) if fenced else text)
        except json.JSONDecodeError as exc:
            problems = [f"the reply is not JSON: {exc}"]
            continue
        problems = reply_problems(data, ids)
        if not problems:
            return data, None
    raise JudgeFailure("the precision judge's JSON was bad twice: " + "; ".join(problems))


def score(vault, docs, spoken, send, size=SAMPLE_SIZE, seed=SEED, vault_ref=""):
    """The precision record for one vault: sample, one judge call through `send`, citations checked, rates."""
    units = units_of(vault)
    sample = stratified_sample(units, size, seed)
    base = {"seed": seed, "size": size, "vault": vault_ref or str(vault)}
    if not sample:
        return {**base, "sampled": 0, "population": 0, "missing": "the final vault has no written items to sample"}
    text, labels, cuts = build_input(sample, units, docs, spoken)
    data, why = ask(send, text, [label for label, _ in sample])
    if data is None:
        return {**base, "sampled": len(sample), "population": len(units), "missing": why}
    rows, dropped = enforce(data, sample, labels, docs, spoken)
    return summarize(rows, dropped, len(units), cuts=cuts, **base)


def pool(records, seeds):
    """One record from the passes of several seeds: items and counts added up, precision over all of them, and the
    spread between the passes (plus-minus is the half-range of the per-seed precisions)."""
    rows = [r for rec in records for r in rec["items"]]
    dropped = [f"seed {rec['seed']}: {d}" for rec in records for d in rec["dropped"]]
    pooled = summarize(rows, dropped, records[0]["population"], cuts=sorted({c for rec in records for c in rec["cuts"]}),
                       seed=list(seeds), size=sum(rec["sampled"] for rec in records), vault=records[0]["vault"])
    per_seed = [{"seed": rec["seed"], "sampled": rec["sampled"], "precision": rec["precision"],
                 "counts": rec["counts"]} for rec in records]
    values = [p["precision"] for p in per_seed]
    pooled["passes"] = per_seed
    pooled["plus_minus"] = round((max(values) - min(values)) / 2, 3)
    pooled["precision_range"] = [min(values), max(values)]
    return pooled


def score_pooled(vault, docs, spoken, send, size=SAMPLE_SIZE, seeds=SEEDS, vault_ref=""):
    """The default precision record: one pass per seed, pooled. Any pass not scored makes the whole record missing,
    since a pooled score over fewer items than asked would read as a full one."""
    records = [score(vault, docs, spoken, send, size, seed, vault_ref) for seed in seeds]
    for rec in records:
        if "missing" in rec:
            return {"size": size, "vault": rec["vault"], "seed": list(seeds), "sampled": rec["sampled"],
                    "population": rec["population"], "missing": rec["missing"] if not rec["sampled"] else f"seed {rec['seed']}: {rec['missing']}"}
    return pool(records, seeds)


# ------------------------------------------------------------------ the preflight's made-up run

PREFLIGHT_DOCS = [{"name": "cio-note.md", "text": "The pilot is 40 desks in Leeds. Legal reviews the privacy notice."}]
PREFLIGHT_SPOKEN = [{"turn": 1, "speaker": "lead", "text": "We're piloting at 40 desks in Leeds."},
                    {"turn": 2, "speaker": "assistant", "text": "Noted the 40-desk Leeds pilot."}]
PREFLIGHT_VAULT = {
    "01-goals.md": "---\ntype: goals\n---\n# Goals\n\nPilot the desk helper at 40 desks in the Leeds office this year.\n",
    "11-unknowns-and-risks.md": "---\ntype: unknowns\n---\n# Unknowns\n\n### UNK-001 Privacy sign-off\n\nWho signs off "
                                "the privacy notice before the pilot starts?\n\n- **State:** open\n",
}


def preflight_input(work):
    """The judge input over a tiny made-up vault written under `work`: the real prompt and shape, for cents."""
    vault = pathlib.Path(work) / "precision-vault"
    for name, text in PREFLIGHT_VAULT.items():
        (vault / name).parent.mkdir(parents=True, exist_ok=True)
        (vault / name).write_text(text, encoding="utf-8")
    units = units_of(vault)
    return build_input(stratified_sample(units), units, PREFLIGHT_DOCS, PREFLIGHT_SPOKEN)[0]


# ------------------------------------------------------------------ a finished run, from the command line

def final_vault(arm_dir, workdir):
    """(path, ref): the arm's origin/main in a temporary clone, as compare_runs.py scores it, else the working tree."""
    shim = types.SimpleNamespace(vault=arm_dir / "vault", arm=arm_dir, notes=[])
    scored = compare.scoring_copy(shim, pathlib.Path(workdir))
    return scored.path, scored.ref


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("run", type=pathlib.Path, help="a finished run folder")
    p.add_argument("--judge-model", required=True)
    p.add_argument("--budget", type=float, required=True, help="USD cap for the preflight and the call together")
    p.add_argument("--arm", default="vela")
    p.add_argument("--stub", action="store_true", help="use the scripted fake claude in tests/sim/stub/")
    p.add_argument("--size", type=int, default=SAMPLE_SIZE)
    p.add_argument("--seeds", default=",".join(map(str, SEEDS)), help="comma-separated seeds, one pass of --size each, pooled")
    p.add_argument("--quick", action="store_true", help=f"one pass of --size with seed {SEED}, no plus-minus")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    sim = sibling("run")
    run_dir = args.run.resolve()
    try:
        summary = sim.load_run(run_dir)
        persona, _, _ = sim.brief_of_run(summary, sim.load_yaml(sim.resolve(summary["persona"], "personas")))
        arm_name = compare.stored_arm(run_dir, args.arm)
        if arm_name is None:
            raise sim.ToolFailure(f"{run_dir} has no {args.arm!r} arm")
        args.model = summary["models"].get("assistant")
        args.persona_model = summary["models"].get("persona")
        arm = sim.Arm.reopen(arm_name, run_dir, args, persona, args.budget, summary["per_arm"].get(arm_name) or {})
        if not args.stub:
            spent, problem = sim.precision_preflight(args, run_dir)
            arm.ledger.add(spent)
            if problem:
                print(f"precision: the preflight failed, so nothing else was sent (${spent:.2f}): {problem}",
                      file=sys.stderr)
                return 4
        with tempfile.TemporaryDirectory(prefix="precision-") as work:
            vault, ref = final_vault(arm.dir, work)
            seeds = (SEED,) if args.quick else tuple(int(x) for x in args.seeds.split(","))
            record = sim.judge_precision(arm, vault, ref, size=args.size, seeds=seeds, quick=args.quick)
    except (sim.ToolFailure, JudgeFailure) as exc:
        print(f"precision: {exc}", file=sys.stderr)
        return 2
    record["spent_usd"] = round(arm.ledger.spent, 4)
    record["judge_model"] = args.judge_model
    (arm.dir / "precision.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(render(record))
    print(f"Wrote {arm.dir / 'precision.json'} (${record['spent_usd']:.2f} of ${args.budget:.2f})")
    return 0


def render(record):
    if "missing" in record:
        return f"Precision: not scored ({record['missing']})"
    c, r = record["counts"], record["rates"]
    pm = f" ±{record['plus_minus'] * 100:.0f} points (seed spread, {len(record['passes'])} passes)" if "passes" in record else ""
    return (f"Precision {record['precision']:.0%}{pm} over {record['sampled']} sampled items of {record['population']}: "
            + ", ".join(f"{k} {c[k]} ({r[k]:.0%})" for k in CLASSES)
            + (f"; {len(record['dropped'])} citations failed and read unsupported" if record["dropped"] else ""))


if __name__ == "__main__":
    sys.exit(main())
