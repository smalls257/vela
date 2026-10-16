#!/usr/bin/env python3
"""Keep or revert one skill change, from the probe summaries before and after it (probe.py writes one
`<stamp>-<case>-<persona>-summary.json` per invocation into its --out folder).

The Violation this exists to prevent is the Silent Fallback in the loop itself: a change kept because one run moved,
because one brief happened to suit it, or because accuracy rose while the lead started reading codes again. The rule,
all four parts at once, over one before and after pair for every persona the case maps (its `snapshot:`):

1. every dev persona's accuracy improves beyond the spread: for each, at least one accuracy measure is a real gain and
   none is a real loss ("real" is probe_scale.compare: the mean moves by more than the larger of the two spreads);
2. no holdout's accuracy gets worse: no accuracy measure of any holdout is a real loss;
3. no voice measure, dev or holdout, is a real loss;
4. the voice-loading, leak and conversation-voice tests pass (GATE_TESTS).

A change that lifts one dev persona and not the other learned that brief, not the job, and is reverted. A persona the
case maps with no pair is refused (exit 2), never skipped: a missing holdout would read as "didn't get worse". A change
that helps accuracy but hurts the voice is reverted. An oracle (ceiling) summary is refused: it measures the material,
never a skill. Output is persona file names, measure names and numbers only, so a holdout stays sealed.

Usage:
  python3 tests/sim/probe_keep.py --dev-before A.json --dev-after B.json [--dev-before ... --dev-after ...]
                                  --holdout-before C.json --holdout-after D.json [--holdout-before ... ...]
                                  [--skip-tests]
Each flag repeats once per persona the case maps; the n-th before pairs with the n-th after.
Exit codes: 0 keep; 1 revert; 2 a tool failed (a summary missing, unreadable, mismatched, or an oracle run).
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "plugin" / "lib"))
sys.path.insert(0, str(HERE))
import probe_scale  # noqa: E402
import seal  # noqa: E402
import yaml  # noqa: E402  (the plugin's bundled PyYAML, as seal loads it)

CASE_FOLDERS = (HERE / "probes", HERE / "scale" / "cases")

# conversation voice and the voice-loading order (START step 0), the for-lead voice, the leak seal, the load measure
GATE_TESTS = ("tests/test_conversation_voice.py", "tests/test_lead_voice.py", "tests/test_sim_seal.py",
              "tests/test_skill_load.py")


class Refused(Exception):
    pass


def load(path):
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refused(f"{path} is not a probe summary: {type(exc).__name__}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("measures"), dict):
        raise Refused(f"{path} has no measures")
    if data.get("oracle"):
        raise Refused(f"{path} is an oracle (ceiling) run, which measures the material, not a skill")
    return data


def pair(before_path, after_path, want_split):
    """(case, persona, compare rows) for one persona's before and after."""
    before, after = load(before_path), load(after_path)
    if (before.get("case"), before.get("persona")) != (after.get("case"), after.get("persona")):
        raise Refused("a before and after summary must be the same case and persona")
    split = "holdout" if seal.sealed(before.get("persona"))[0] else "dev"
    if split != want_split:
        raise Refused(f"the {want_split} pair is a {split} persona")
    return before.get("case"), before.get("persona"), probe_scale.compare(before["measures"], after["measures"])


def pairs(befores, afters, want_split):
    if len(befores) != len(afters):
        raise Refused(f"give one --{want_split}-after for every --{want_split}-before")
    return [pair(b, a, want_split) for b, a in zip(befores, afters)]


def case_personas(case):
    """(dev, holdout): the personas the case file maps, split by the seal."""
    path = next((folder / f"{case}.yaml" for folder in CASE_FOLDERS if (folder / f"{case}.yaml").is_file()), None)
    if path is None:
        raise Refused(f"case {case!r} is in neither probes/ nor scale/cases/")
    mapped = set((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("snapshot") or {})
    holdout = {name for name in mapped if seal.sealed(name)[0]}
    return mapped - holdout, holdout


def require_every_persona(dev, holdout):
    """Refuses unless every pair is one case and each persona that case maps has exactly one pair."""
    cases = {case for case, _, _ in dev + holdout}
    if len(cases) != 1:
        raise Refused("every summary must be the same case")
    want = dict(zip(("dev", "holdout"), case_personas(cases.pop())))
    for label, group in (("dev", dev), ("holdout", holdout)):
        names = [persona for _, persona, _ in group]
        if len(set(names)) != len(names):
            raise Refused(f"a {label} persona is given twice")
        missing, extra = sorted(want[label] - set(names)), sorted(set(names) - want[label])
        if missing or extra:
            raise Refused(f"the {label} pairs must be every {label} persona the case maps"
                          + (f"; missing: {', '.join(missing)}" if missing else "")
                          + (f"; not mapped: {', '.join(extra)}" if extra else ""))


def run_gate_tests():
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", *GATE_TESTS], cwd=REPO, capture_output=True,
                          text=True, timeout=1800)
    tail = (done.stdout.strip().splitlines() or ["no output"])[-1]
    return done.returncode == 0, tail


def decide(dev, holdout, tests_ok):
    """(keep, reasons): the four-part rule over each persona's compare rows, given as (persona, rows) pairs."""
    reasons = []
    for persona, rows in dev:
        acc = [r for r in rows if not r["voice"]]
        if not any(r["verdict"] == "gain" for r in acc):
            reasons.append(f"dev accuracy did not improve beyond the spread on {persona}")
        reasons += [f"dev accuracy fell beyond the spread on {persona}: {r['name']}" for r in acc if r["verdict"] == "loss"]
    for persona, rows in holdout:
        reasons += [f"holdout accuracy fell beyond the spread on {persona}: {r['name']}" for r in rows
                    if not r["voice"] and r["verdict"] == "loss"]
    reasons += [f"{who} voice got worse beyond the spread on {persona}: {r['name']}"
                for who, group in (("dev", dev), ("holdout", holdout)) for persona, rows in group
                for r in rows if r["voice"] and r["verdict"] == "loss"]
    if not tests_ok:
        reasons.append("the voice-loading, leak or conversation-voice tests fail")
    return not reasons, reasons


def lines(label, rows):
    out = [f"{label}:"]
    for r in rows:
        out.append(f"  {r['name']}: {r['before']:g} -> {r['after']:g} (moved {r['delta']:+g}; spread {r['threshold']:g}): "
                   f"{r['verdict']}")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("dev-before", "dev-after", "holdout-before", "holdout-after"):
        parser.add_argument(f"--{name}", required=True, action="append",
                            help="a probe summary JSON file; once per persona the case maps")
    parser.add_argument("--skip-tests", action="store_true", help="for this tool's own tests only; a real verdict runs them")
    args = parser.parse_args(argv)
    try:
        dev = pairs(args.dev_before, args.dev_after, "dev")
        holdout = pairs(args.holdout_before, args.holdout_after, "holdout")
        require_every_persona(dev, holdout)
    except Refused as exc:
        print(f"probe_keep: {exc}", file=sys.stderr)
        return 2
    if args.skip_tests:
        tests_ok, tail = True, "skipped (--skip-tests): not a real verdict"
    else:
        tests_ok, tail = run_gate_tests()
    dev, holdout = [(p, rows) for _, p, rows in dev], [(p, rows) for _, p, rows in holdout]
    keep, reasons = decide(dev, holdout, tests_ok)
    shown = [line for label, group in (("dev", dev), ("holdout", holdout)) for persona, rows in group
             for line in lines(f"{label} {persona}", rows)]
    for line in shown + [f"gate tests: {tail}"]:
        print(line)
    print("KEEP: every part of the rule holds" if keep else "REVERT: " + "; ".join(reasons))
    return 0 if keep else 1


if __name__ == "__main__":
    sys.exit(main())
