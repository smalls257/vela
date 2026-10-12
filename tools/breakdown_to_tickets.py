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
import csv
import pathlib
import re
import sys

import yaml

SIZE_POINTS = {"S": 2, "M": 5, "L": 8}  # work-breakdown defines S, M, L (about 2 days, 3 to 5 days, 1 to 2 weeks) and no points
STATUSES = ("complete", "complete-with-gaps")
COLUMNS = ["Issue Id", "Summary", "Description", "Issue Type", "Parent", "Story Points"]
STORY_HEADING = re.compile(r"^###\s+(S-\d+)\b[\s:\-\u2013\u2014]*(.*?)\s*$")
TRACES = re.compile(r"^\W*Traces to\W*:\W*(.*)$", re.I)
BLOCKED = re.compile(r"^\W*Blocked by\W*:\W*(.*)$", re.I)
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
VAULT_ID = re.compile(r"CAP-\d+(?:\.FR\d+)?(?:@APP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)?|CON-\d+|EPC-\d+(?:\.AC\d+)?|FR-\d+"
                      r"|APP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
NOTHING = re.compile(r"^(none|nothing|n/a|-+|\u2014|\u2013)\.?$", re.I)


class BreakdownError(Exception):
    """The breakdown could not be found, read or written; nothing was converted."""


class Story:
    def __init__(self, sid, name):
        self.id, self.name = sid, name
        self.traces, self.criteria, self.tasks, self.blocked, self.extra = None, [], [], None, []


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(line):
    return bool(re.fullmatch(r"\s*\|?[\s:\-|]+\|?\s*", line)) and "-" in line


def split_frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    return (yaml.safe_load(match.group(1)) or {}, text[match.end():]) if match else ({}, text)


def sections_of(body):
    """(heading text, lines) for each `## ` section, plus the lines before the first one under the key ''."""
    out, name = {"": []}, ""
    for line in body.splitlines():
        match = re.match(r"^##\s+(.*?)\s*$", line)
        if match:
            name = match.group(1)
            out.setdefault(name, [])
        else:
            out[name].append(line)
    return out


def take_story_line(story, line, state):
    """File one line of a story's section under the field it belongs to. Returns False if it fits none."""
    if TRACES.match(line):
        story.traces, state["last"] = TRACES.match(line).group(1).strip(), "traces"
    elif BLOCKED.match(line):
        story.blocked, state["last"] = BLOCKED.match(line).group(1).strip(), "blocked"
    elif BULLET.match(line):
        story.criteria.append(BULLET.match(line).group(1).strip())
        state["last"] = "criteria"
    elif line.lstrip().startswith("|"):
        take_table_line(story, line, state)
    elif state["last"] in ("traces", "blocked", "criteria") and not state["gap"]:
        if state["last"] == "traces":
            story.traces += " " + line.strip()
        elif state["last"] == "blocked":
            story.blocked += " " + line.strip()
        else:
            story.criteria[-1] += " " + line.strip()
    else:
        return False
    return True


def take_table_line(story, line, state):
    row = cells(line)
    if is_separator(line):
        return
    if row[0].lower() == "task":
        state["table"], state["last"] = True, "table"
        return
    story.tasks.append(row)
    state["last"] = "table"


def parse_story_sections(body):
    """The stories in file order, from the `### S-NN` headings anywhere after the frontmatter."""
    stories, current, state = [], None, {}
    for line in body.splitlines():
        heading = STORY_HEADING.match(line)
        if heading:
            current = Story(heading.group(1), heading.group(2))
            stories.append(current)
            state = {"last": None, "gap": False, "table": False}
            continue
        if re.match(r"^#{1,3}\s", line):
            current = None  # a `## ` section after the stories, or any other heading, ends the story
            continue
        if current is None:
            continue
        if not line.strip():
            state["gap"] = True
            continue
        fitted = take_story_line(current, line, state)
        state["gap"] = False
        if not fitted:
            current.extra.append(line.strip())
            state["last"] = "extra"
    return stories


def summary_rows(lines):
    """The story ids named in the summary table (the table whose first header cell is Story), in order."""
    ids, inside = [], False
    for line in lines:
        if not line.lstrip().startswith("|"):
            inside = False
            continue
        row = cells(line)
        if row[0].lower() == "story":
            inside = True
        elif inside and not is_separator(line):
            found = re.match(r"^\W*(S-\d+)\b", row[0])
            if found:
                ids.append(found.group(1))
    return ids


def not_planned_lines(sections):
    for name, lines in sections.items():
        if name.lower().startswith("not planned"):
            return [BULLET.sub(r"\1", ln).strip() if BULLET.match(ln) else ln.strip() for ln in lines if ln.strip()]
    return []


def parse(text):
    """(stories, not_planned, problems) for one breakdown document."""
    meta, body = split_frontmatter(text)
    problems = []
    if meta.get("status") not in STATUSES:
        problems.append(f"frontmatter status is {meta.get('status')!r}; the plan should be {' or '.join(STATUSES)}")
    stories = parse_story_sections(body)
    if not stories:
        problems.append("no `### S-NN <name>` story section found")
    sections = sections_of(body)
    problems += cross_check(stories, summary_rows(body.splitlines()), sections)
    for story in stories:
        problems += story_problems(story, {s.id for s in stories})
    return stories, not_planned_lines(sections), problems


def cross_check(stories, summary_ids, sections):
    problems, seen = [], set()
    for story in stories:
        if story.id in seen:
            problems.append(f"{story.id}: the heading appears more than once")
        seen.add(story.id)
    for sid in summary_ids:
        if sid not in seen:
            problems.append(f"{sid}: is in the summary table but has no story section")
    for story in stories:
        if summary_ids and story.id not in summary_ids:
            problems.append(f"{story.id}: has a section but is not in the summary table")
    order = next((" ".join(lines) for name, lines in sections.items() if name.lower().startswith("build order")), None)
    for story in stories:
        if order is not None and story.id not in order:
            problems.append(f"{story.id}: is not in the Build order")
    return problems


def story_problems(story, story_ids):
    problems = []
    if not story.traces:
        problems.append(f"{story.id}: no 'Traces to:' line")
    elif not VAULT_ID.findall(story.traces):
        problems.append(f"{story.id}: 'Traces to' names no requirement ID, so the ticket has no labels")
    if not story.criteria:
        problems.append(f"{story.id}: no acceptance criteria bullets")
    if not story.tasks:
        problems.append(f"{story.id}: no task table rows")
    if story.blocked is None:
        problems.append(f"{story.id}: no 'Blocked by:' line")
    for number, row in enumerate(story.tasks, 1):
        if len(row) != 3 or not all(row):
            problems.append(f"{story.id} task {number} ({row[0]!r}): expected three filled cells, Task | Size | Component")
        size = row[1] if len(row) > 1 else ""
        if size.strip().upper() not in SIZE_POINTS:
            problems.append(f"{story.id} task {number} ({row[0]!r}): size {size!r} is not S, M or L, so it has no points")
    for sid in blockers(story):
        if sid not in story_ids:
            problems.append(f"{story.id}: blocked by {sid}, which is not a story in this plan")
    for line in story.extra:
        problems.append(f"{story.id}: line not mapped to a column, kept in Description: {line!r}")
    return problems


def blockers(story):
    return re.findall(r"\bS-\d+\b", story.blocked or "")


def labels_of(story):
    seen = []
    for found in VAULT_ID.findall(story.traces or ""):
        found = found.rstrip("-")
        if found not in seen:
            seen.append(found)
    return seen


def story_description(story):
    parts = [f"Traces to: {story.traces}" if story.traces is not None else "Traces to: (none stated)"]
    parts += ["Acceptance criteria:"] + [f"- {c}" for c in story.criteria] if story.criteria else []
    parts.append(f"Blocked by: {story.blocked}" if story.blocked is not None else "Blocked by: (none stated)")
    parts += story.extra
    return "\n".join(parts)


def task_description(story, row):
    component = row[2] if len(row) > 2 else ""
    size = row[1] if len(row) > 1 else ""
    return (f"Component: {component}\nSize: {size}\nStory {story.id} {story.name}\nTraces to: {story.traces}")


def build_rows(stories):
    """One row per story and one per task row, in file order. Labels go in as many trailing Labels cells as needed."""
    rows = []
    for story in stories:
        rows.append({"Issue Id": story.id, "Summary": f"{story.id} {story.name}".strip(), "Description": story_description(story),
                     "Issue Type": "Story", "Parent": "", "Story Points": "", "labels": labels_of(story),
                     "Blocked by": ", ".join(dict.fromkeys(blockers(story)))})
        for number, row in enumerate(story.tasks, 1):
            size = row[1].strip().upper() if len(row) > 1 else ""
            rows.append({"Issue Id": f"{story.id}-T{number}", "Summary": row[0], "Description": task_description(story, row),
                         "Issue Type": "Task", "Parent": story.id, "Story Points": SIZE_POINTS.get(size, ""),
                         "labels": labels_of(story), "Blocked by": ""})
    return rows


def write_csv(rows, path):
    width = max([len(r["labels"]) for r in rows] or [1]) or 1
    header = COLUMNS + ["Labels"] * width + ["Blocked by"]
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(header)
        for r in rows:
            writer.writerow([r[c] for c in COLUMNS] + r["labels"] + [""] * (width - len(r["labels"])) + [r["Blocked by"]])
    return header


README = """# Tickets from the work breakdown

`tickets.csv` was written by `tools/breakdown_to_tickets.py` from `{source}`. No model touched it: each Story row is a
`### S-NN` section and each Task row is a row of that story's task table, in the breakdown's own words. Nothing was
added, merged or reworded. {counts}

## How each column is filled

| Column | From |
|---|---|
| Issue Id | `S-NN` for a story, `S-NN-Tn` for its nth task. Used only to link rows during import. |
| Summary | the story heading (`S-NN name`), or the task's name |
| Description | story: its Traces to line, acceptance criteria and Blocked by line as written. Task: its component, size, and its story's Traces to line |
| Issue Type | Story for a section, Task for a task row. The breakdown has no epic level, so there are no Epics |
| Parent | a task's Issue Id of its story. Blank for stories |
| Story Points | tasks only: S = {s}, M = {m}, L = {l}. The work-breakdown skill gives sizes in days, not points, so this mapping is ours, and sizes are for ordering, not commitments. Stories carry no points so the total is not counted twice |
| Labels | the requirement, contract, criterion and app IDs in the story's Traces to line (`CAP-nnn.FRn@APP-slug`, `CON-nnn`, `EPC-nnn.ACn`, `FR-nnn`, `APP-slug`), one per Labels column; a task has its story's |
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
