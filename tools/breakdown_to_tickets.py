#!/usr/bin/env python3
"""Turn a work-breakdown plan into a Jira CSV import, without a model and without inventing a word.

The work-breakdown skill writes docs/plan/<slug>-breakdown.md: a summary table, then one `### S-NN <name>` section per
story (a "Traces to:" line, acceptance criteria as bullets, a `| Task | Size | Component |` table, a "Blocked by:"
line), then Build order, Coverage and Not planned. This reads that file and writes docs/work/tickets.csv and a README
beside it. Each story becomes a Story row and each task row a Task row, one for one, with the breakdown's own words.

It exists so the tickets come from the grilling (the requirements, the design, the breakdown) and not from a fresh
conversation that would invent them. Anything it cannot map to a column is listed as a problem in the README and on
stderr, never dropped; the CSV is still written with everything that did map.

    python3 tools/breakdown_to_tickets.py --repo ~/code/desk-agent
    python3 tools/breakdown_to_tickets.py --breakdown docs/plan/x-breakdown.md --out /tmp/tickets

Exit 0: every line mapped. 1: the CSV is written but the README lists problems. 2: nothing could be read or written.
"""
import re
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "plugin" / "lib"))

from vela.tickets import build_rows, parse  # noqa: E402,F401  (the one reader of the format; the explorer's Build plan level uses it too)
from vela import tickets  # noqa: E402  (the conversion itself: `vela tickets` writes the same files from an installed plugin)


class BreakdownError(Exception):
    """The breakdown could not be found, read or written; nothing was converted."""


def find_breakdown(repo):
    found = sorted((repo / "docs" / "plan").glob("*-breakdown.md"))
    if len(found) != 1:
        raise BreakdownError(f"expected exactly one docs/plan/*-breakdown.md in {repo}, found {len(found)}: "
                             + ", ".join(str(f.name) for f in found) + " (name one with --breakdown)")
    return found[0]


def convert(breakdown, out):
    """Write out/tickets.csv and out/README.md. Returns the problems found (empty when every line mapped)."""
    try:
        text = breakdown.read_text(encoding="utf-8")
        out.mkdir(parents=True, exist_ok=True)
        csv_body, readme, problems = tickets.convert_text(text, breakdown.name)
        with (out / "tickets.csv").open("w", encoding="utf-8", newline="") as handle:
            handle.write(csv_body)
        (out / "README.md").write_text(readme, encoding="utf-8")
    except OSError as exc:
        raise BreakdownError(f"cannot read {breakdown} or write to {out}: {exc}") from exc
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path("."), help="the team repo; default the current folder")
    parser.add_argument("--breakdown", type=pathlib.Path, help="the breakdown file; default the one docs/plan/*-breakdown.md")
    parser.add_argument("--out", type=pathlib.Path, help="where to write; default <repo>/docs/work")
    args = parser.parse_args(argv)
    try:
        breakdown = args.breakdown or find_breakdown(args.repo)
        out = args.out or args.repo / "docs" / "work"
        problems = convert(breakdown, out)
    except BreakdownError as exc:
        print(f"breakdown_to_tickets: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"breakdown_to_tickets: problem: {problem}", file=sys.stderr)
    print(f"wrote {out / 'tickets.csv'} and {out / 'README.md'}" + (f" with {len(problems)} problems" if problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
