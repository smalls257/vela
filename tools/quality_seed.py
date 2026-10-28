#!/usr/bin/env python3
"""Regenerate .quality/complexity-waivers.tsv from a scan of the whole tree. Only the owner runs this.

  python3 tools/quality_seed.py --owner OWNER --reason TEXT [--today YYYY-MM-DD] [--days 182]

The waiver file is delete-only (Paper Tiger: a green gate whose exceptions grow), and a reseed is the one
sanctioned way to add to it, for example after a rename moved a waived function. A reseed never resets an
expiry: an old entry keeps its owner, date and reason, so renewing time stays a reviewed edit.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import quality_complexity  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
import quality_gate  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
import quality_waivers  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable
from quality_waivers import Waiver  # noqa: E402 -- after the sys.path insert above, which makes the sibling tools importable

NEW_ENTRY_REASON = "over the cap when the gate arrived"
HEADER = """# Complexity waivers: functions and files that were over their caps when the quality gate arrived.
# Delete-only: a line may be removed (fix the code, then delete it) but never added or raised by hand.
# Only the owner regenerates this file, and a reseed keeps every old expiry.
# Regenerate: python3 tools/quality_seed.py --owner OWNER --reason TEXT"""


def reseed(measures: list, old: dict, owner: str, reason: str, expires: datetime.date) -> list[Waiver]:
    """A waiver for each measure over its layer's caps. Old entries keep their owner, expiry and reason."""
    waivers = []
    for measure in measures:
        layer = quality_complexity.layer_of(measure.path)
        over = quality_complexity.over_caps(measure, quality_complexity.CAPS[layer]) if layer else {}
        if not over:
            continue
        before = old.get(measure.key)
        if before:
            waivers.append(Waiver(measure.key, over, before.owner, before.expires, before.reason, 0))
        else:
            waivers.append(Waiver(measure.key, over, owner, expires, NEW_ENTRY_REASON, 0))
    return waivers


def _changes(waivers: list[Waiver], old: dict) -> list[str]:
    lines = []
    for w in sorted(waivers, key=lambda w: w.key):
        before = old.get(w.key)
        if before is None:
            lines.append(f"added: {w.key}")
        elif any(v > before.limits.get(m, 0) for m, v in w.limits.items()):
            lines.append(f"raised: {w.key}")
    return lines


def _counts(waivers: list[Waiver]) -> list[str]:
    tally: dict[str, list[int]] = {}
    for w in waivers:
        layer = quality_complexity.layer_of(w.key.split("::")[0])
        row = tally.setdefault(layer, [0, 0])
        row[0 if "::" in w.key else 1] += 1
    return [f"{layer}: {fn} functions, {files} files" for layer, (fn, files) in sorted(tally.items())]


def _old_waivers(root: pathlib.Path) -> dict:
    path = root / quality_waivers.WAIVER_FILE
    if not path.is_file():
        return {}
    return quality_waivers.parse_waivers(path.read_text(encoding="utf-8"))


def _short_head(root: pathlib.Path) -> str:
    done = quality_gate._git(root, "rev-parse", "--short", "HEAD")
    if done.returncode != 0:
        raise quality_gate.GateCannotRun(f"git rev-parse HEAD failed: {done.stderr.strip()}")
    return done.stdout.strip()


def seed(root: pathlib.Path, args: argparse.Namespace) -> int:
    today = args.today or datetime.date.today()
    old = _old_waivers(root)
    measures, _ = quality_gate.scan(root, quality_gate.choose_files(root, []))
    waivers = reseed(measures, old, args.owner, args.reason, today + datetime.timedelta(days=args.days))
    seeded = f"# seeded {today.isoformat()} at {_short_head(root)} by {args.owner}: {args.reason}"
    (root / quality_waivers.WAIVER_FILE).parent.mkdir(exist_ok=True)
    (root / quality_waivers.WAIVER_FILE).write_text(quality_waivers.format_waivers(waivers, HEADER + "\n" + seeded),
                                                    encoding="utf-8")
    print("\n".join([f"{len(waivers)} waived", *_counts(waivers), *_changes(waivers, old)]))
    return 0


def main(argv: list[str], root: pathlib.Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quality_seed.py", description=__doc__.split("\n")[0])
    parser.add_argument("--owner", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--today", type=datetime.date.fromisoformat)
    parser.add_argument("--days", type=int, default=182)
    args = parser.parse_args(argv)
    try:
        return seed(root or quality_gate.find_root(), args)
    except (quality_gate.GateCannotRun, quality_complexity.MeasureError, quality_waivers.WaiverFileError) as exc:
        print(f"quality seed: could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
