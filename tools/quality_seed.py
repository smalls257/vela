#!/usr/bin/env python3
"""Regenerate or renew .quality/complexity-waivers.tsv. Only the owner runs this, from their own terminal or with
`! python3 tools/quality_seed.py ...` at the Claude prompt; the guard-bash hook denies it to an agent.

  python3 tools/quality_seed.py --owner OWNER --reason TEXT [--today YYYY-MM-DD] [--first]
  python3 tools/quality_seed.py --renew KEY... --until YYYY-MM-DD --reason TEXT [--owner OWNER] [--today YYYY-MM-DD]

The waiver file is delete-only (Paper Tiger: a green gate whose exceptions grow), and these two commands are the
sanctioned ways to add to it. The gate does not trust the label: it recomputes what a seed of the tree would write
and fails any changed line that differs.

A reseed keeps the owner, expiry and reason of every old entry that is still over its cap, and writes the measured
values. A function that is new to the file (a rename counts) gets the owner's --reason and a fresh expiry.

Expiry rule for new entries: sort them by overage, the biggest first, where overage is the sum over the metrics of
(value - cap) / cap. The first expires 183 days out (six months) and the last 365 days out, the rest spaced evenly
between, so the worst debt comes due first and no day carries them all.

A missing waiver file is refused unless --first: a deleted file must be restored from git, not reseeded, because a
reseed from nothing resets every expiry.
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

FIRST_SEED_REASON = "over the cap when the gate arrived"
FIRST_EXPIRY_DAYS = 183
LAST_EXPIRY_DAYS = 365
HEADER = """# Complexity waivers: functions and files that were over their caps when the quality gate arrived.
# Delete-only: a line may be removed (fix the code, then delete it) but never added or raised by hand.
# Only the owner regenerates this file, and a reseed keeps every old expiry.
# Regenerate: python3 tools/quality_seed.py --owner OWNER --reason TEXT"""


def overage(over: dict, caps) -> float:
    """How far past its caps a measure is, summed over the metrics, as a fraction of each cap."""
    return sum((value - getattr(caps, metric)) / getattr(caps, metric) for metric, value in over.items())


def staggered_expiries(count: int, today: datetime.date) -> list[datetime.date]:
    """`count` dates from six months out to twelve, evenly spaced, earliest first."""
    span = LAST_EXPIRY_DAYS - FIRST_EXPIRY_DAYS
    return [today + datetime.timedelta(days=FIRST_EXPIRY_DAYS + (span * i) // max(count - 1, 1)) for i in range(count)]


def _over_by_key(measures: list) -> dict:
    found = {}
    for measure in measures:
        layer = quality_complexity.layer_of(measure.path)
        over = quality_complexity.over_caps(measure, quality_complexity.CAPS[layer]) if layer else {}
        if over:
            found[measure.key] = (over, overage(over, quality_complexity.CAPS[layer]))
    return found


def reseed(measures: list, old: dict, owner: str, reason: str, today: datetime.date) -> list[Waiver]:
    """A waiver for each measure over its layer's caps. Old entries keep their owner, expiry and reason."""
    over_by_key = _over_by_key(measures)
    waivers = [Waiver(key, over, old[key].owner, old[key].expires, old[key].reason, 0)
               for key, (over, _) in over_by_key.items() if key in old]
    new = sorted((key for key in over_by_key if key not in old), key=lambda key: (-over_by_key[key][1], key))
    for key, expires in zip(new, staggered_expiries(len(new), today)):
        waivers.append(Waiver(key, over_by_key[key][0], owner, expires, reason, 0))
    return waivers


def renewed(waivers: dict, keys: list, over_by_key: dict, until: datetime.date, reason: str) -> list[Waiver]:
    """The waivers with `keys` given a new expiry and reason and the measured limits; the rest are untouched."""
    return [Waiver(w.key, over_by_key[w.key][0], w.owner, until, reason, 0) if w.key in keys else w
            for w in waivers.values()]


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


def _short_head(root: pathlib.Path) -> str:
    done = quality_gate._git(root, "rev-parse", "--short", "HEAD")
    if done.returncode != 0:
        raise quality_gate.GateCannotRun(f"git rev-parse HEAD failed: {done.stderr.strip()}")
    return done.stdout.strip()


def _old_waivers(root: pathlib.Path, first: bool) -> dict:
    """The waivers on disk. A missing file is refused without --first, and --first refuses an existing one."""
    path = root / quality_waivers.WAIVER_FILE
    if first:
        if path.exists():
            raise quality_gate.GateCannotRun(f"{quality_waivers.WAIVER_FILE} already exists; --first is only for a tree that has none")
        return {}
    if not path.is_file():
        raise quality_gate.GateCannotRun(quality_gate.MISSING_WAIVER_FILE + "; --first is only for the very first seed")
    return quality_waivers.parse_waivers(path.read_text(encoding="utf-8"))


def _write(root: pathlib.Path, waivers: list[Waiver], seeded: str) -> None:
    path = root / quality_waivers.WAIVER_FILE
    path.parent.mkdir(exist_ok=True)
    path.write_text(quality_waivers.format_waivers(waivers, HEADER + "\n" + seeded), encoding="utf-8")


def seed(root: pathlib.Path, args: argparse.Namespace) -> int:
    today = args.today or datetime.date.today()
    old = _old_waivers(root, args.first)
    measures, _ = quality_gate.scan(root, quality_gate.choose_files(root, []))
    waivers = reseed(measures, old, args.owner, FIRST_SEED_REASON if args.first else args.reason, today)
    _write(root, waivers, f"# seeded {today.isoformat()} at {_short_head(root)} by {args.owner}: {args.reason}")
    print("\n".join([f"{len(waivers)} waived", *_counts(waivers), *_changes(waivers, old)]))
    return 0


def _renewal_problem(args: argparse.Namespace, old: dict, over_by_key: dict, today: datetime.date) -> str | None:
    if not today <= args.until <= today + datetime.timedelta(days=quality_waivers.MAX_RENEWAL_DAYS):
        return f"--until {args.until} must fall between today and {quality_waivers.MAX_RENEWAL_DAYS} days out"
    unknown = [k for k in args.renew if k not in old]
    if unknown:
        return f"not in the waiver file: {', '.join(unknown)}"
    cleared = [k for k in args.renew if k not in over_by_key]
    if cleared:
        return f"already within the caps, so delete the line instead: {', '.join(cleared)}"
    return None


def renew(root: pathlib.Path, args: argparse.Namespace) -> int:
    today = args.today or datetime.date.today()
    old = _old_waivers(root, False)
    measures, _ = quality_gate.scan(root, quality_gate.choose_files(root, []))
    over_by_key = _over_by_key(measures)
    problem = _renewal_problem(args, old, over_by_key, today)
    if problem:
        raise quality_gate.GateCannotRun(problem)
    waivers = renewed(old, args.renew, over_by_key, args.until, args.reason)
    seeded = quality_waivers.seeded_line((root / quality_waivers.WAIVER_FILE).read_text(encoding="utf-8"))
    _write(root, waivers, seeded)
    print(f"renewed {len(args.renew)} until {args.until.isoformat()}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="quality_seed.py", description=__doc__.split("\n")[0])
    parser.add_argument("--owner", default="smalls257")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--today", type=datetime.date.fromisoformat)
    parser.add_argument("--first", action="store_true")
    parser.add_argument("--renew", nargs="+", metavar="KEY")
    parser.add_argument("--until", type=datetime.date.fromisoformat)
    args = parser.parse_args(argv)
    if args.renew and (args.until is None or args.first):
        parser.error("--renew needs --until and cannot be combined with --first")
    if args.until and not args.renew:
        parser.error("--until only goes with --renew")
    return args


def main(argv: list[str], root: pathlib.Path | None = None) -> int:
    args = parse_args(argv)
    try:
        return (renew if args.renew else seed)(root or quality_gate.find_root(), args)
    except (quality_gate.GateCannotRun, quality_complexity.MeasureError, quality_waivers.WaiverFileError,
            UnicodeDecodeError) as exc:
        print(f"quality seed: could not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
