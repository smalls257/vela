"""Read a work-breakdown plan (docs/plan/<slug>-breakdown.md) into stories and tasks, without a model and without
inventing a word.

    read(text)  -> {meta, stories, summary, order, coverage, not_planned, problems}
    parse(text) -> (stories, not_planned, problems)
    csv_text(stories) -> the Jira CSV import as text

The work-breakdown skill writes the file: frontmatter (status, prereqs, gaps), a summary table, one `### S-NN <name>`
section per story (a "Traces to:" line, acceptance criteria as bullets, a `| Task | Size | Component |` table, a
"Blocked by:" line), then Build order, Coverage and Not planned. A story may also carry an "Acceptance criteria:" label
(with a lead-in on the same line), "Open for tech-design-grill: ..." notes and "Conflict with an epic criterion: ..."
notes; they are read into `open_notes` and `conflicts`, not flagged. This is the one reader of that format.
tools/breakdown_to_tickets.py turns it into tickets; the explorer's Build plan level (explorer/plan_data.py) draws
it. They share this module so the ticket a story becomes and the card it is drawn as can never read the file two ways.

Anything the reader cannot map is a line in `problems`, never dropped and never guessed.
"""
import csv
import io
import re

import yaml

SIZE_POINTS = {"S": 2, "M": 5, "L": 8}  # work-breakdown defines S, M, L (about 2 days, 3 to 5 days, 1 to 2 weeks) and no points
STATUSES = ("complete", "complete-with-gaps")
COLUMNS = ["Issue Id", "Summary", "Description", "Issue Type", "Parent", "Story Points"]
STORY_HEADING = re.compile(r"^###\s+(S-\d+[a-z]?)\b[\s:\-\u2013\u2014]*(.*?)\s*$")
TRACES = re.compile(r"^\W*Traces to\W*:\W*(.*)$", re.I)
BLOCKED = re.compile(r"^\W*Blocked by\W*:\W*(.*)$", re.I)
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
VAULT_ID = re.compile(r"CAP-\d+(?:\.FR\d+)?(?:@APP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)?|CON-\d+|EPC-\d+(?:\.AC\d+)?|FR-\d+"
                      r"|APP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
NOTHING = re.compile(r"^(none|nothing|n/a|-+|\u2014|\u2013)\.?$", re.I)
# The label above a story's bullets. The skill writes "Acceptance criteria:"; the real files also write a lead-in on the
# same line ("Acceptance criteria. Design behaviour, except where marked:"), which is kept as the label.
CRITERIA_LABEL = re.compile(r"^\W*Acceptance criteria\b.*:\s*$", re.I)
# Notes the skill writes under a story: a question only the design can answer, and a clash with an epic criterion.
OPEN_NOTE = re.compile(r"^\W*Open for\b", re.I)
CONFLICT_NOTE = re.compile(r"^\W*Conflicts? with\b", re.I)
# A story the plan says traces to nothing ("Traces to: no requirement row or epic criterion; ...") is stated, not unreadable.
NO_TRACE = re.compile(r"^\W*(none|no |nothing|design only)", re.I)
STORY_RANGE = re.compile(r"\b(S-\d+[a-z]?)\s+(?:to|through|until|\u2013|\u2014|-)\s+(S-\d+[a-z]?)\b")
LABEL_NEEDS_DESIGN, LABEL_CONFLICT = "needs-design", "conflict"


class Story:
    def __init__(self, sid, name):
        self.id, self.name = sid, name
        self.traces, self.criteria, self.tasks, self.blocked, self.extra = None, [], [], None, []
        self.criteria_label, self.open_notes, self.conflicts = "", [], []


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
    elif CRITERIA_LABEL.match(line):
        story.criteria_label, state["last"] = line.strip(), "label"
    elif OPEN_NOTE.match(line):
        story.open_notes.append(line.strip())
        state["last"] = "open"
    elif CONFLICT_NOTE.match(line):
        story.conflicts.append(line.strip())
        state["last"] = "conflict"
    elif line.lstrip().startswith("|"):
        take_table_line(story, line, state)
    elif state["last"] in CONTINUES and not state["gap"]:
        continue_line(story, line, state["last"])
    else:
        return False
    return True


CONTINUES = ("traces", "blocked", "criteria", "open", "conflict")


def continue_line(story, line, field):
    """A wrapped line belongs to the field above it."""
    text = " " + line.strip()
    if field == "traces":
        story.traces += text
    elif field == "blocked":
        story.blocked += text
    elif field == "criteria":
        story.criteria[-1] += text
    elif field == "open":
        story.open_notes[-1] += text
    else:
        story.conflicts[-1] += text


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
        if not heading and re.match(r"^###\s+S-", line):
            stories.append(Story("?", line.lstrip("# ").strip()))  # kept, so the caller reports it instead of dropping it
            stories[-1].extra.append("unreadable story heading: " + line.strip())
            current, state = stories[-1], {"last": None, "gap": False, "table": False}
            continue
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


def not_planned_lines(sections):
    for name, lines in sections.items():
        if name.lower().startswith("not planned"):
            return [BULLET.sub(r"\1", ln).strip() if BULLET.match(ln) else ln.strip() for ln in lines if ln.strip()]
    return []


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
    elif not VAULT_ID.findall(story.traces) and not NO_TRACE.match(story.traces):
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


def story_refs(text):
    """The story IDs a line names, in order, with a range such as "S-03 to S-13" meaning every story between."""
    ranged, out = STORY_RANGE.sub(lambda m: " ".join(range_ids(m.group(1), m.group(2))), text or ""), []
    for sid in re.findall(r"\bS-\d+[a-z]?\b", ranged):
        if sid not in out:
            out.append(sid)
    return out


def range_ids(first, last):
    if not (first[2:].isdigit() and last[2:].isdigit()):
        return [first, last]  # "S-07a to S-09" names its ends; a lettered story has no place in a numeric run
    low, high = int(first[2:]), int(last[2:])
    width = len(first) - 2
    return [f"S-{n:0{width}d}" for n in range(low, high + 1)] if low <= high else [first, last]


def blockers(story):
    return story_refs(story.blocked)


def labels_of(story):
    seen = []
    for found in VAULT_ID.findall(story.traces or ""):
        found = found.rstrip("-")
        if found not in seen:
            seen.append(found)
    return seen


def story_labels(story):
    """The labels of the story's own ticket: its trace IDs, then what the plan flags for the design or the epics."""
    return labels_of(story) + ([LABEL_NEEDS_DESIGN] if story.open_notes else []) + ([LABEL_CONFLICT] if story.conflicts else [])


def story_description(story):
    parts = [f"Traces to: {story.traces}" if story.traces is not None else "Traces to: (none stated)"]
    if story.criteria:
        parts += [story.criteria_label or "Acceptance criteria:"] + [f"- {c}" for c in story.criteria]
    parts.append(f"Blocked by: {story.blocked}" if story.blocked is not None else "Blocked by: (none stated)")
    if story.open_notes:
        parts += ["Open for the design:"] + [f"- {n}" for n in story.open_notes]
    if story.conflicts:
        parts += ["Conflicts:"] + [f"- {c}" for c in story.conflicts]
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
                     "Issue Type": "Story", "Parent": "", "Story Points": "", "labels": story_labels(story),
                     "Blocked by": ", ".join(dict.fromkeys(blockers(story)))})
        for number, row in enumerate(story.tasks, 1):
            size = row[1].strip().upper() if len(row) > 1 else ""
            rows.append({"Issue Id": f"{story.id}-T{number}", "Summary": row[0], "Description": task_description(story, row),
                         "Issue Type": "Task", "Parent": story.id, "Story Points": SIZE_POINTS.get(size, ""),
                         "labels": labels_of(story), "Blocked by": ""})
    return rows



def size_total(story):
    """The story's task sizes as the summary table writes them: largest first, joined by +, e.g. 'M+S'."""
    sizes = [r[1].strip().upper() for r in story.tasks if len(r) > 1 and r[1].strip().upper() in SIZE_POINTS]
    return "+".join(sorted(sizes, key=lambda s: -SIZE_POINTS[s])) or "none"


def size_counts(text):
    """{size: how many} from a size total written either way: the skill's counts ("2S 4M 1L") or letters ("M+M+S", "L")."""
    counted = re.findall(r"(\d+)\s*([SML])\b", (text or "").upper())
    if counted:
        out = {}
        for n, size in counted:
            out[size] = out.get(size, 0) + int(n)
        return out
    letters = re.findall(r"\b([SML])\b", (text or "").upper())
    return {size: letters.count(size) for size in dict.fromkeys(letters)}


def points(story):
    return sum(SIZE_POINTS.get(r[1].strip().upper(), 0) for r in story.tasks if len(r) > 1)


def summary_table(lines):
    """{story id: {traces, size, blocked}} as the summary table states them (the table whose first header is Story)."""
    out, inside = {}, False
    for line in lines:
        if not line.lstrip().startswith("|"):
            inside = False
            continue
        row = cells(line)
        if row[0].lower() == "story":
            inside = True
        elif inside and not is_separator(line):
            found = re.match(r"^\W*(S-\d+[a-z]?)\b", row[0])
            if found:
                row += [""] * (4 - len(row))
                out[found.group(1)] = {"traces": row[1], "size": row[2], "blocked": row[3]}
    return out


def build_order(sections):
    """[{id, why}] from the Build order section: `1. S-01: why it sits there`, in the order written."""
    lines = next((ls for name, ls in sections.items() if name.lower().startswith("build order")), [])
    out = []
    for line in lines:
        found = re.match(r"^\s*(?:\d+[.)]|[-*+])\s*(S-\d+[a-z]?)\b[\s:\-\u2013\u2014]*(.*?)\s*$", line)
        if found:
            out.append({"id": found.group(1), "why": found.group(2)})
    return out


def coverage_table(sections):
    """[{target, stories}] from the Coverage tables, one row each; `stories` is empty when the cell names none, which
    the skill says fails the plan."""
    lines = next((ls for name, ls in sections.items() if name.lower().startswith("coverage")), [])
    out = []
    for line in lines:
        if not line.lstrip().startswith("|") or is_separator(line):
            continue
        row = cells(line)
        if len(row) < 2 or row[0].lower() in ("target", "component", "trace target"):
            continue
        ids = VAULT_ID.findall(row[0])
        out.append({"target": row[0], "id": ids[0] if ids else None, "stories": story_refs(row[1])})
    return out


def read(text):
    """The whole plan as plain data. `stories` are Story objects; `problems` is everything that did not map."""
    meta, body = split_frontmatter(text)
    problems = []
    if meta.get("status") not in STATUSES:
        problems.append(f"frontmatter status is {meta.get('status')!r}; the plan should be {' or '.join(STATUSES)}")
    stories = parse_story_sections(body)
    if not stories:
        problems.append("no `### S-NN <name>` story section found")
    sections = sections_of(body)
    summary = summary_table(body.splitlines())
    problems += cross_check(stories, list(summary), sections)
    for story in stories:
        problems += story_problems(story, {s.id for s in stories})
    return {"meta": meta, "stories": stories, "summary": summary, "order": build_order(sections),
            "coverage": coverage_table(sections), "not_planned": not_planned_lines(sections), "problems": problems}


def parse(text):
    """(stories, not_planned, problems) for one breakdown document."""
    plan = read(text)
    return plan["stories"], plan["not_planned"], plan["problems"]


def csv_text(rows):
    """The Jira import for `rows` (build_rows) as text: what breakdown_to_tickets.py writes to tickets.csv, byte for byte."""
    width = max([len(r["labels"]) for r in rows] or [1]) or 1
    header = COLUMNS + ["Labels"] * width + ["Blocked by"]
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(header)
    for r in rows:
        writer.writerow([r[c] for c in COLUMNS] + r["labels"] + [""] * (width - len(r["labels"])) + [r["Blocked by"]])
    return out.getvalue()
