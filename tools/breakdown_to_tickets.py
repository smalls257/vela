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
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "plugin" / "lib"))

from planner.breakdown import SIZE_POINTS, build_rows, csv_text, parse  # noqa: E402  (the one reader of the format; the explorer's Build plan level uses it too)


class BreakdownError(Exception):
    """The breakdown could not be found, read or written; nothing was converted."""


def write_csv(rows, path):
    with path.open("w", encoding="utf-8", newline="") as out:
        out.write(csv_text(rows))


README = """# Tickets from the work breakdown

`tickets.csv` was written by `tools/breakdown_to_tickets.py` from `{source}`. No model touched it: each Story row is a
`### S-NN` section and each Task row is a row of that story's task table, in the breakdown's own words. Nothing was
added, merged or reworded. {counts}

## How each column is filled

| Column | From |
|---|---|
| Issue Id | `S-NN` for a story, `S-NN-Tn` for its nth task. Used only to link rows during import. |
| Summary | the story heading (`S-NN name`), or the task's name |
| Description | story: its Traces to line, its acceptance criteria under an "Acceptance criteria" heading, its Blocked by line, then any "Open for the design" notes and "Conflicts" notes, each as written. Task: its component, size, and its story's Traces to line |
| Issue Type | Story for a section, Task for a task row. The breakdown has no epic level, so there are no Epics |
| Parent | a task's Issue Id of its story. Blank for stories |
| Story Points | tasks only: S = {s}, M = {m}, L = {l}. The work-breakdown skill gives sizes in days, not points, so this mapping is ours, and sizes are for ordering, not commitments. Stories carry no points so the total is not counted twice |
| Labels | the requirement, contract, criterion and app IDs in the story's Traces to line (`CAP-nnn.FRn@APP-slug`, `CON-nnn`, `EPC-nnn.ACn`, `FR-nnn`, `APP-slug`), one per Labels column; a task has its story's. A story with an "Open for ..." note also gets `needs-design`, and one with a "Conflict with ..." note gets `conflict` |
| Blocked by | the stories a story is blocked by, from its Blocked by line. Anything else it names (an open question, a gap, an outside party) is in the Description only |

## Import into Jira

1. Jira Cloud: Settings, System, External system import, CSV. (Team-managed or company-managed project: choose the target project first.)
2. Upload `tickets.csv`, tick the comma delimiter, and map the columns: Summary to Summary, Description to Description,
   Issue Type to Issue Type, Issue Id to Issue ID, Parent to Parent, Story Points to Story point estimate, every Labels
   column to Labels, Blocked by to the issue link "Blocks" (as "is blocked by").
3. Map the values Story and Task to your project's issue types. If your project only allows a Sub-task under a Story,
   map Task to Sub-task.
4. Import, then check one story and one of its tasks against `{source}`.
{problems}{not_planned}"""


def write_readme(path, source, stories, rows, problems, not_planned):
    counts = f"{len(stories)} stories and {sum(len(s.tasks) for s in stories)} tasks, {len(rows)} rows."
    prob = ("\n## Problems\n\nThese lines could not be mapped cleanly. Fix the breakdown (or the ticket by hand), then run again.\n\n"
            + "\n".join(f"- {p}" for p in problems) + "\n") if problems else "\nNo problems: every line of the breakdown mapped.\n"
    notp = ("\n## Not ticketed\n\nThe breakdown lists these under Not planned, so they have no ticket:\n\n"
            + "\n".join(f"- {n}" for n in not_planned) + "\n") if not_planned else ""
    path.write_text(README.format(source=source, counts=counts, s=SIZE_POINTS["S"], m=SIZE_POINTS["M"], l=SIZE_POINTS["L"],
                                  problems=prob, not_planned=notp), encoding="utf-8")


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
    except OSError as exc:
        raise BreakdownError(f"cannot read {breakdown} or create {out}: {exc}") from exc
    stories, not_planned, problems = parse(text)
    rows = build_rows(stories)
    try:
        write_csv(rows, out / "tickets.csv")
        write_readme(out / "README.md", breakdown.name, stories, rows, problems, not_planned)
    except OSError as exc:
        raise BreakdownError(f"cannot write to {out}: {exc}") from exc
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
