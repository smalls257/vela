#!/usr/bin/env python3
"""Keep or revert one skill change, from the probe summaries before and after it (probe.py writes one
`<stamp>-<case>-<persona>-summary.json` per invocation into its --out folder).

The Violation this exists to prevent is the Silent Fallback in the loop itself: a change kept because one run moved,
or because accuracy rose while the lead started reading codes again. The rule, all four parts at once:

1. the dev persona's accuracy improves beyond the spread: at least one accuracy measure is a real gain and none is a
   real loss ("real" is probe_scale.compare: the mean moves by more than the larger of the two spreads);
2. the holdout's accuracy doesn't get worse: no accuracy measure is a real loss;
3. no voice measure, dev or holdout, is a real loss;
4. the voice-loading, leak and conversation-voice tests pass (GATE_TESTS).

A change that helps accuracy but hurts the voice is reverted. An oracle (ceiling) summary is refused: it measures the
material, never a skill. Output is measure names and numbers only, so a holdout stays sealed.

Usage:
  python3 tests/sim/probe_keep.py --dev-before A.json --dev-after B.json --holdout-before C.json --holdout-after D.json
                                  [--skip-tests]
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
    before, after = load(before_path), load(after_path)
    if (before.get("case"), before.get("persona")) != (after.get("case"), after.get("persona")):
        raise Refused("a before and after summary must be the same case and persona")
    split = "holdout" if seal.sealed(before.get("persona"))[0] else "dev"
    if split != want_split:
        raise Refused(f"the {want_split} pair is a {split} persona")
    return probe_scale.compare(before["measures"], after["measures"])


def run_gate_tests():
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", *GATE_TESTS], cwd=REPO, capture_output=True,
                          text=True, timeout=1800)
    tail = (done.stdout.strip().splitlines() or ["no output"])[-1]
    return done.returncode == 0, tail


def decide(dev, holdout, tests_ok):
    """(keep, reasons): the four-part rule over compare rows."""
    reasons = []
    dev_acc = [r for r in dev if not r["voice"]]
    if not any(r["verdict"] == "gain" for r in dev_acc):
        reasons.append("dev accuracy did not improve beyond the spread")
    reasons += [f"dev accuracy fell beyond the spread: {r['name']}" for r in dev_acc if r["verdict"] == "loss"]
    reasons += [f"holdout accuracy fell beyond the spread: {r['name']}" for r in holdout
                if not r["voice"] and r["verdict"] == "loss"]
    reasons += [f"{who} voice got worse beyond the spread: {r['name']}" for who, rows in (("dev", dev), ("holdout", holdout))
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
        parser.add_argument(f"--{name}", required=True, help="a probe summary JSON file")
    parser.add_argument("--skip-tests", action="store_true", help="for this tool's own tests only; a real verdict runs them")
    args = parser.parse_args(argv)
    try:
        dev = pair(args.dev_before, args.dev_after, "dev")
        holdout = pair(args.holdout_before, args.holdout_after, "holdout")
    except Refused as exc:
        print(f"probe_keep: {exc}", file=sys.stderr)
        return 2
    if args.skip_tests:
        tests_ok, tail = True, "skipped (--skip-tests): not a real verdict"
    else:
        tests_ok, tail = run_gate_tests()
    keep, reasons = decide(dev, holdout, tests_ok)
    for line in lines("dev", dev) + lines("holdout", holdout) + [f"gate tests: {tail}"]:
        print(line)
    print("KEEP: every part of the rule holds" if keep else "REVERT: " + "; ".join(reasons))
    return 0 if keep else 1


if __name__ == "__main__":
    sys.exit(main())
