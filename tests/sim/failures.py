#!/usr/bin/env python3
"""Turn a finished sim run into GENERIC failure patterns for skill authors: what the assistant did wrong, in terms of
behavior, with turn and session numbers, and nothing of the answer key.

The Violation this exists to prevent is the Paper Tiger, by way of teaching to the test: a skill author who reads
"missed K27: works council in December" writes a skill that asks about works councils in December, the score rises
on this persona and nothing improves for the next lead. So the report never names a key item, never says which items
were missed, never quotes a turn, a page or the brief, and never names a person, an organization or a product from a
persona. It says what kind of thing went wrong and where to look: "when the lead said they weren't sure, the session
filed an owner and a due date instead of proposing one and asking (T52)".

Every line is built from a fixed template of behavior words and numbers; no text from the run is copied into it.
Then an explicit redaction pass (seal.redact) replaces any persona name, key keyword or run of brief text that got
in anyway with [redacted] and counts it, and the tool refuses to print (exit 2) if a term survives the pass.

A holdout persona (its file says `split: holdout`) gets scores only: per-kind counts and precision, no patterns,
unless --reveal is given. The iteration loop reads patterns from the dev persona only (tests/sim/README.md,
"Iterating without teaching to the test").

Usage:
  python3 tests/sim/failures.py <run-dir> [--arm vela] [--reveal] [--out FILE]
  python3 tests/sim/failures.py <probe-run-dir> [--reveal] [--out FILE]   (a folder holding probe.json)
  python3 tests/sim/run.py --failures <run-dir> [--reveal]
It reads only, calls nothing and costs nothing. Exit 0 printed; 2 the run can't be read, or a term survived redaction.
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent


def sibling(name):
    key = f"sim_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        spec.loader.exec_module(module)
    return sys.modules[key]


compare = sibling("compare_runs")
seal = sibling("seal")

UNSURE = re.compile(r"\b(?:not sure|unsure|no idea|don'?t know|do not know|couldn'?t tell you|can'?t say|no clue|"
                    r"haven'?t (?:a clue|checked|seen)|beats me)\b", re.I)
OWNER_OR_DATE = re.compile(r"--owner\b|--due\b|--by\b|--date\b|\*\*(?:Owner|Due|By|Date):\*\*|^\s*(?:owner|due):", re.I | re.M)
# A proposal put to the lead as a question: an owner or a date named, and a question mark within the next sentence
# or two ("I'd put the endpoint lead down as owner. Is that right?").
PROPOSED_AND_ASKED = re.compile(r"\b(?:owner|own it|owns it|take it on|due|deadline|by when|what date|which date|"
                                r"by (?:mon|tues|wednes|thurs|fri)day|by the end of)\b[^?]{0,160}\?", re.I)
CORRECTED = re.compile(r"^\W*(?:no[,.!]?\s+)?(?:not quite\b|that'?s not (?:right|what)|that isn'?t (?:right|what)|"
                       r"that is not (?:right|what)|i said\b|as i said\b|i already (?:said|told)\b|you already\b|"
                       r"i just (?:said|told)\b|that'?s wrong\b|wrong\b)", re.I)
MAX_QUESTIONS = 3  # references/REVIEW.md: at most three questions at a time
LONG_TURN_WORDS = 250
TURN_LIST = 12  # turns listed per pattern; the rest are counted

KIND_WORDS = {  # what each key kind measures, in behavior terms, for the scores section
    "knows": "facts the lead knows that reached the final vault",
    "unaware": "gaps the lead didn't know about that the assistant raised first",
    "wrong": "confident beliefs of the lead's that the assistant questioned or checked against a source",
    "conflicts": "disagreements between stakeholders named as something to settle, not a side picked",
    "decisions": "decisions recorded as decided",
}


class Pattern:
    """One behavior, the places it happened, and how many times."""

    def __init__(self, behavior, where, unit="T"):
        self.behavior, self.where, self.unit = behavior, sorted(set(where)), unit

    def line(self):
        shown = ", ".join(f"{self.unit}{n}" for n in self.where[:TURN_LIST])
        more = f" and {len(self.where) - TURN_LIST} more" if len(self.where) > TURN_LIST else ""
        times = f"{len(self.where)} time{'s' if len(self.where) != 1 else ''}"
        return f"- {self.behavior} ({times}: {shown}{more})"


# ------------------------------------------------------------------ detectors: each reads the run, never quotes it

def by_session(run):
    spoken = run.spoken()
    return spoken, {i: e for i, e in enumerate(spoken)}


def next_assistant(spoken, i):
    """The first assistant turn after spoken[i] in the same session, or None."""
    for e in spoken[i + 1:]:
        if e.get("session") != spoken[i].get("session"):
            return None
        if e["speaker"] == "assistant":
            return e
    return None


def ran(run, turn):
    return "\n".join(compare.ran_text(t, run.wrappers) for t in run.turn_tools.get(turn, []))


def unsure_filed(run):
    """The lead said they didn't know; the next turn wrote an owner or a date anyway, without proposing and asking."""
    spoken, hits = run.spoken(), []
    for i, e in enumerate(spoken):
        if e["speaker"] != "lead" or not UNSURE.search(e.get("text") or ""):
            continue
        reply = next_assistant(spoken, i)
        if reply and OWNER_OR_DATE.search(ran(run, reply["turn"])) and not PROPOSED_AND_ASKED.search(reply.get("text") or ""):
            hits.append(reply["turn"])
    return Pattern("when the lead said they weren't sure, the session filed an owner or a due date instead of "
                   "proposing one and asking", hits)


def too_many_questions(run):
    hits = [e["turn"] for e in run.assistant_turns() if (e.get("text") or "").count("?") > MAX_QUESTIONS]
    return Pattern(f"asked the lead more than {MAX_QUESTIONS} questions in one turn", hits)


def long_turns(run):
    hits = [e["turn"] for e in run.assistant_turns() if len(re.findall(r"\w+", e.get("text") or "")) > LONG_TURN_WORDS]
    return Pattern(f"wrote the lead more than {LONG_TURN_WORDS} words in one turn", hits)


def lead_corrected(run):
    """A lead turn that opens by correcting or repeating; the turn listed is the assistant's turn before it."""
    spoken, hits = run.spoken(), []
    for i, e in enumerate(spoken):
        if e["speaker"] == "lead" and i and CORRECTED.search(e.get("text") or ""):
            before = next((x for x in reversed(spoken[:i]) if x["speaker"] == "assistant"
                           and x.get("session") == e.get("session")), None)
            if before:
                hits.append(before["turn"])
    return Pattern("the lead had to correct the assistant or repeat themselves right after this turn", hits)


def codes_to_lead(run):
    hits = [e["turn"] for e in run.assistant_turns()
            if any(compare.LEAK_KINDS[k][1] for k in compare.leaks_in(e.get("text") or ""))]
    return Pattern("showed the lead internal codes, IDs, file paths or tool commands", hits)


def scorecard_patterns(card):
    """The prose judge's lists, by turn or session only: its quotes are never copied."""
    if compare.is_missing(card):
        return []
    not_scored = card.get("not_scored") or {}
    out = []
    if "shape" not in not_scored:
        out += [Pattern("told the lead what the answer is instead of asking", [r.get("turn") for r in card.get("told_not_asked") or []
                                                                              if isinstance(r.get("turn"), int)]),
                Pattern("recorded something as decided without the lead's explicit yes",
                        [r.get("turn") for r in card.get("decided_without_yes") or [] if isinstance(r.get("turn"), int)]),
                Pattern("stated as fact something neither the documents nor the lead had said",
                        [r.get("turn") for r in card.get("invented_facts") or [] if isinstance(r.get("turn"), int)]),
                Pattern("ended a session without a clear next step for the lead",
                        [r.get("session") for r in card.get("session_endings") or []
                         if not r.get("clear_next_step") and isinstance(r.get("session"), int)], unit="S")]
    drafted = [t for t in card.get("drafted_messages") or [] if isinstance(t, int)]
    out.append(Pattern("drafted a message for the lead to send instead of saying who to ask and what", drafted))
    return out


def consent_patterns(run):
    c = compare.consent_section(run)
    if "missing" in c:
        return []
    return [Pattern("sent work for review without the lead's yes", [x["turn"] for x in c["without_consent"]])]


def close_patterns(run):
    c = compare.close_section(run)
    if "missing" in c:
        return []
    out = []
    for step in c["expected_steps"]:
        sessions = [x["session"] for x in c["per_close"] if step in x["missing_steps"] and x["counted_as"] == "skipped"]
        out.append(Pattern(f"skipped the close step '{step}' in a session the lead ended", sessions, unit="S"))
    return out


def precision_patterns(precision):
    """Unsupported, padding and duplicate items in the precision sample, by page type: never the items themselves."""
    if not precision or "missing" in precision:
        return []
    out = []
    words = {"unsupported": "wrote as fact something no source or lead turn gives",
             "padding": "wrote items that carry no information (placeholders, restated headings)",
             "duplicate": "wrote the same fact in two places"}
    for cls, behavior in words.items():
        counts = {t: c[cls] for t, c in (precision.get("by_page_type") or {}).items() if c.get(cls)}
        if counts:
            spread = ", ".join(f"{n} on {t} pages" for t, n in sorted(counts.items()))
            out.append(f"- {behavior}: {sum(counts.values())} of {precision['sampled']} sampled items ({spread})")
    return out


# ------------------------------------------------------------------ the report

def scores(card, precision):
    lines = ["## Scores", ""]
    recall = compare.recall_section(card)
    if "missing" in recall and len(recall) == 1:
        lines.append(f"- Recall: missing ({recall['missing']})")
    else:
        for kind, _ in compare.RECALL_KINDS:
            r = recall[kind]
            label = KIND_WORDS[kind]
            lines.append(f"- {label}: missing ({r['missing']})" if compare.is_missing(r)
                         else f"- {label}: {r['found']} of {r['of']} ({r['share'] * 100:.0f}%)")
        pooled = recall["pooled"]
        if not compare.is_missing(pooled):
            lines.append(f"- all key items: {pooled['found']} of {pooled['of']} ({pooled['share'] * 100:.0f}%)")
    if precision and "missing" not in precision:
        c = precision["counts"]
        lines.append(f"- precision: {precision['precision'] * 100:.0f}% of {precision['sampled']} sampled items "
                     f"(backed {c['backed']}, duplicate {c['duplicate']}, padding {c['padding']}, "
                     f"unsupported {c['unsupported']})")
    else:
        lines.append("- precision: not scored (run tests/sim/precision.py on the run)")
    return lines + [""]


def read_precision(arm_dir):
    path = arm_dir / "precision.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def probe_scores(record):
    """A probe run's criteria, as probe.py printed them: counts and categories only, never an item."""
    lines = ["## Scores", "", f"- probe {record.get('case')}: ended {record.get('ending')} after "
             f"{record.get('assistant_turns')} assistant turns"]
    for row in record.get("criteria") or []:
        lines.append(f"- {'PASS' if row.get('passed') else 'FAIL'} {row.get('check')}: {row.get('summary')}")
    return lines + [""]


def report(run, card, precision, sealed, why, probe=None):
    lines = [f"# Failure patterns: {run.arm.name if probe is not None else run.dir.name}", "",
             "Generic patterns for skill authors. Nothing here names a key item, says which ones were missed, or "
             "quotes the run: read the turns listed to see the behavior, and fix the behavior, not the case.", ""]
    lines += probe_scores(probe) if probe is not None else scores(card, precision)
    if sealed:
        lines += [f"Sealed: {why}. Scores only; the patterns are printed for a dev persona, or with --reveal.", ""]
        return "\n".join(lines)
    patterns = [unsure_filed(run), too_many_questions(run), long_turns(run), lead_corrected(run), codes_to_lead(run)]
    if probe is None:
        patterns += scorecard_patterns(run.scorecard) + consent_patterns(run) + close_patterns(run)
    found = [p for p in patterns if p.where]
    lines += ["## What went wrong, by behavior", ""]
    lines += [p.line() for p in sorted(found, key=lambda p: -len(p.where))] or ["- no pattern found"]
    lines += [""]
    vault = precision_patterns(precision)
    if vault:
        lines += ["## What the vault holds that it shouldn't", ""] + vault + [""]
    clean = [p.behavior for p in patterns if not p.where and not p.behavior.startswith("skipped the close step")]
    if not any(p.where for p in patterns if p.behavior.startswith("skipped the close step")):
        clean.append("skipped a close step in a session the lead ended")
    if clean:
        lines += ["## Not seen in this run", ""] + [f"- {b}" for b in clean] + [""]
    return "\n".join(lines)


def redacted(text, terms):
    """(text, replaced): the redaction pass. A term that survives it is a bug in the pass, so it raises."""
    text, count = seal.redact(text, terms)
    left = seal.leaks_in(text, terms)
    if left:
        raise RuntimeError(f"{len(left)} key terms survived the redaction pass")
    return text, count


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("run", type=pathlib.Path)
    p.add_argument("--arm", default="vela")
    p.add_argument("--reveal", action="store_true", help="print the patterns for a holdout persona too")
    p.add_argument("--out", type=pathlib.Path, help="also write the report here")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    run_dir = args.run.resolve()
    if (run_dir / "probe.json").is_file():
        return probe_main(args, run_dir)
    arm = compare.stored_arm(run_dir, args.arm)
    if arm is None or not (run_dir / "run.json").is_file():
        print(f"failures: {run_dir} is not a run folder with a {args.arm!r} arm", file=sys.stderr)
        return 2
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    checkout = compare.checkout_for(None, run_dir, [])
    run = compare.Run("run", run_dir, arm, checkout)
    locked, why = seal.sealed(summary.get("persona"))
    card = compare.scorecard_section(run)
    text = report(run, card, read_precision(run.arm), locked and not args.reveal, why)
    return emit(text, args)


def probe_main(args, run_dir):
    """A probe run folder (tests/sim/probe.py) is its own arm: transcript.jsonl, raw/ and vault/ sit in it, and
    probe.json holds the persona and the blind criteria summaries. A holdout persona's probe is sealed the same way."""
    record = json.loads((run_dir / "probe.json").read_text(encoding="utf-8"))
    checkout = compare.checkout_for(None, run_dir, [])
    run = compare.Run("probe", run_dir.parent, run_dir.name, checkout)
    locked, why = seal.sealed(record.get("persona"))
    text = report(run, None, None, locked and not args.reveal, why, probe=record)
    return emit(text, args)


def emit(text, args):
    try:
        text, count = redacted(text, seal.persona_terms())
    except RuntimeError as exc:
        print(f"failures: refused to print: {exc}", file=sys.stderr)
        return 2
    text += f"\nRedaction: {count} persona term{'s' if count != 1 else ''} replaced with {seal.REDACTED}.\n"
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
