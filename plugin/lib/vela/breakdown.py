"""Read a work-breakdown plan (docs/plan/<slug>-breakdown.md) into stories and tasks, without a model and without
inventing a word.

    read(text)  -> {meta, stories, summary, order, coverage, not_planned, problems}
    parse(text) -> (stories, not_planned, problems)
    csv_text(stories) -> the Jira CSV import as text

The work-breakdown skill writes the file: frontmatter (status, prereqs, gaps), a summary table, one `### S-NN <name>`
section per story (a "Traces to:" line, acceptance criteria as bullets, a `| Task | Size | Component |` table, a
"Blocked by:" line), then Build order, Coverage and Not planned. A story may also carry an "Acceptance criteria:" label
(with a lead-in on the same line), "Open for tech-design-grill: ..." notes and "Conflict with an epic criterion: ..."
notes; they are read into `open_notes` and `conflicts`, not flagged. A story may also carry the lines the team skills
write since design session 18: "Done when:", "Components:", "Slice:" (tracer, vertical or layer), "Release fit:" and
"Status:" (deferred, held, split, or merged into another story). A deferred or held story keeps its tasks and criteria;
a merged one is a pointer and needs none. Plans written without those lines read exactly as before. This is the one
reader of that format.
A story may also carry a "Summary:" line and a "Ticket criteria (from <stamp>):" block, the ticket's own copy of its
criteria, read into `summary` and `ticket_groups` and never into `criteria`.
tools/breakdown_to_tickets.py turns it into tickets; the explorer's Build plan level (explorer/plan_data.py) draws
it. They share this module so the ticket a story becomes and the card it is drawn as can never read the file two ways.

Anything the reader cannot map is a line in `problems`, never dropped and never guessed.
"""
import csv
import hashlib
import io
import re

from vela import parse as vault_parse

from vela import export

SIZE_POINTS = {"S": 2, "M": 5, "L": 8}  # work-breakdown defines S, M, L (about 2 days, 3 to 5 days, 1 to 2 weeks) and no points
STATUSES = ("complete", "complete-with-gaps")
COLUMNS = ["Issue Id", "Summary", "Description", "Issue Type", "Parent", "Story Points"]
STORY_HEADING = re.compile(r"^###\s+(S-\d+[a-z]?)\b[\s:\-\u2013\u2014]*(.*?)\s*$")
TRACES = re.compile(r"^\W*Traces to\W*:\W*(.*)$", re.I)
BLOCKED = re.compile(r"^\W*Blocked by\W*:\W*(.*)$", re.I)
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
VAULT_ID = re.compile(r"CAP-\d+(?:\.FR\d+)?(?:@APP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)?|CON-\d+|EPC-\d+(?:\.AC\d+)?|FR-\d+"
                      r"|APP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
CONSTRAINT_ID = re.compile(r"\bCST-\d+\b")  # a story may rest on a constraint; it is not a label, so the tickets of earlier plans stay as they were
NOTHING = re.compile(r"^(none|nothing|n/a|-+|\u2014|\u2013)\.?$", re.I)
# The label above a story's bullets. The skill writes "Acceptance criteria:"; the real files also write a lead-in on the
# same line ("Acceptance criteria. Design behavior, except where marked:"), which is kept as the label.
CRITERIA_LABEL = re.compile(r"^\W*Acceptance criteria\b.*:\s*$", re.I)
# Notes the skill writes under a story: a question only the design can answer, and a clash with an epic criterion.
OPEN_NOTE = re.compile(r"^\W*Open for\b", re.I)
CONFLICT_NOTE = re.compile(r"^\W*Conflicts? with\b", re.I)
DONE_WHEN = re.compile(r"^\W*Done when\W*:\W*(.*)$", re.I)
COMPONENTS = re.compile(r"^\W*Components\W*:\W*(.*)$", re.I)
SLICE = re.compile(r"^\W*Slice\W*:\W*(.*)$", re.I)
RELEASE_FIT = re.compile(r"^\W*Release fit\W*:\W*(.*)$", re.I)
TRACER_FACT = re.compile(r"^\s*[-*+]\s+\*\*Tracer:\*\*\s*(.*?)\s*$", re.I)  # the team's tracer story: `- **Tracer:** yes`
NO_BLOCKERS = re.compile(r"^\W*none\b", re.I)  # "none. D-001 runs in parallel, not a gate": no blockers, the rest is a note
STATUS = re.compile(r"^\W*Status\W*:\W*(.*)$", re.I)
SUMMARY = re.compile(r"^\W*Summary\W*:\W*(.*)$", re.I)
# The ticket's own copy of the criteria, regrouped and reworded by a session; the stamp is criteria_stamp() of the
# criteria it was written from, so a copy left behind by an edit is flagged instead of read as current.
TICKET_LABEL = re.compile(r"^\W*Ticket criteria\b(?:\s*\(from\s+([0-9a-f]{6})\))?\s*:\s*$", re.I)
SLICES = ("tracer", "vertical", "layer")
VAULT_SLICE = re.compile(r"\bSLC-\d{3}\b")  # the vault's slice a story belongs to (slices.py), not its shape above
NOT_BUILT = ("deferred", "merged")  # a story in either state is in no total and has no ticket
# A story the plan says traces to nothing ("Traces to: no requirement row or epic criterion; ...") is stated, not unreadable.
NO_TRACE = re.compile(r"^\W*(none|no |nothing|design only)", re.I)
STORY_RANGE = re.compile(r"\b(S-\d+[a-z]?)\s+(?:to|through|until|\u2013|\u2014|-)\s+(S-\d+[a-z]?)\b")
LABEL_NEEDS_DESIGN, LABEL_CONFLICT = "needs-design", "conflict"


class Story:
    def __init__(self, sid, name):
        self.id, self.name = sid, name
        self.traces, self.criteria, self.tasks, self.blocked, self.extra = None, [], [], None, []
        self.criteria_label, self.open_notes, self.conflicts = "", [], []
        self.done_when, self.components, self.slice_text, self.fit, self.status = None, None, None, None, None
        self.tracer = False
        self.summary, self.ticket_stamp, self.ticket_label, self.ticket_groups = None, None, False, []

    @property
    def state(self):
        """planned, or the first word of the Status line: deferred, held, split or merged."""
        words = re.findall(r"[a-z]+", (self.status or "").lower())
        return words[0] if words else "planned"

    @property
    def slice(self):
        """tracer (the Tracer fact bullet, or a Slice line that starts with it), vertical or layer; "" when absent or something else."""
        if self.tracer:
            return "tracer"
        words = re.findall(r"[a-z]+", (self.slice_text or "").lower())
        return words[0] if words and words[0] in SLICES else ""

    @property
    def slice_id(self):
        """The vault slice the story is part of, SLC-nnn, named on its Slice line ("Slice: vertical, SLC-002 The digest
        reaches a pilot user") or its Traces to line; "" when it names none. Breakdown and tickets group by it."""
        for text in (self.slice_text, self.traces):
            found = VAULT_SLICE.search(text or "")
            if found:
                return found.group(0)
        return ""

    @property
    def built(self):
        return self.state not in NOT_BUILT


def cells(line):
    """A table row's cells, read as the vault's own tables are: an escaped pipe stays inside its cell."""
    return list(vault_parse.split_row(line))


def is_separator(line):
    return bool(re.fullmatch(r"\s*\|?[\s:\-|]+\|?\s*", line)) and "-" in line


def split_frontmatter(text):
    """(meta, body, problem). The vault's own reader finds the block, so a BOM or CRLF file reads as an LF one does;
    `problem` says why no frontmatter was read, and is "" when it was."""
    text = vault_parse.normalize_text(text)
    meta, body_start, error = vault_parse.split_frontmatter(text)
    body = "\n".join(text.split("\n")[body_start - 1:]) if not error else text
    return meta, body, (error.message if error else "")


def sections_of(body):
    """(heading text, lines) for each `## ` section, plus the lines before the first one under the key ''."""
    out, name = {"": []}, ""
    for line in body.split("\n"):
        match = re.match(r"^##\s+(.*?)\s*$", line)
        if match:
            name = match.group(1)
            out.setdefault(name, [])
        else:
            out[name].append(line)
    return out


def criteria_stamp(criteria):
    """Six hex digits that change whenever any of a story's acceptance criteria change, and not when one is only
    rewrapped. The Ticket criteria label records the stamp it was written from (TICKET_LABEL)."""
    joined = "\n".join(" ".join(c.split()) for c in criteria)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:6]


FIELD_LINES = (TRACES, BLOCKED, TRACER_FACT, DONE_WHEN, COMPONENTS, SLICE, RELEASE_FIT, STATUS, SUMMARY,
               CRITERIA_LABEL, TICKET_LABEL, OPEN_NOTE, CONFLICT_NOTE)


def is_field_line(line):
    return line.lstrip().startswith("|") or any(p.match(line) for p in FIELD_LINES)


def take_ticket_line(story, line, state):
    """A line inside a Ticket criteria block: a bullet is a ticket line, a line ending in a colon starts a group,
    any other line continues the ticket line above it. A field line or a table row ends the block, and so does a
    line that fits none of these: it goes back to the story's reader, which reports it."""
    if is_field_line(line):
        state["block"] = None
        return False
    bullet = BULLET.match(line)
    if bullet:
        if not story.ticket_groups:
            story.ticket_groups.append(["", []])
        story.ticket_groups[-1][1].append(bullet.group(1).strip())
        state["last"] = "ticket"
        return True
    if line.strip().endswith(":"):
        story.ticket_groups.append([line.strip()[:-1].strip(), []])
        state["last"] = "ticket"
        return True
    if state["last"] == "ticket" and not state["gap"] and story.ticket_groups and story.ticket_groups[-1][1]:
        story.ticket_groups[-1][1][-1] += " " + line.strip()
        return True
    state["block"] = None
    return False


def take_story_line(story, line, state):
    """File one line of a story's section under the field it belongs to. Returns False if it fits none."""
    if state.get("block") == "ticket" and take_ticket_line(story, line, state):
        return True
    if TRACES.match(line):
        story.traces, state["last"] = TRACES.match(line).group(1).strip(), "traces"
    elif BLOCKED.match(line):
        story.blocked, state["last"] = BLOCKED.match(line).group(1).strip(), "blocked"
    elif TRACER_FACT.match(line):
        story.tracer = TRACER_FACT.match(line).group(1).lower().startswith(("yes", "true"))
        state["last"] = None
    elif DONE_WHEN.match(line):
        story.done_when, state["last"] = DONE_WHEN.match(line).group(1).strip(), "done_when"
    elif COMPONENTS.match(line):
        story.components, state["last"] = COMPONENTS.match(line).group(1).strip(), "components"
    elif SLICE.match(line):
        story.slice_text, state["last"] = SLICE.match(line).group(1).strip(), "slice"
    elif RELEASE_FIT.match(line):
        story.fit, state["last"] = RELEASE_FIT.match(line).group(1).strip(), "fit"
    elif STATUS.match(line):
        story.status, state["last"] = STATUS.match(line).group(1).strip(), "status"
    elif SUMMARY.match(line):
        story.summary, state["last"] = SUMMARY.match(line).group(1).strip(), "summary"
    elif TICKET_LABEL.match(line):
        story.ticket_label, story.ticket_stamp = True, TICKET_LABEL.match(line).group(1)
        state["block"], state["last"] = "ticket", "ticket_label"
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


CONTINUES = ("traces", "blocked", "criteria", "open", "conflict", "done_when", "components", "slice", "fit", "status", "summary")
WRAPPED = {"done_when": "done_when", "components": "components", "slice": "slice_text", "fit": "fit", "status": "status", "summary": "summary"}


def continue_line(story, line, field):
    """A wrapped line belongs to the field above it."""
    text = " " + line.strip()
    if field == "traces":
        story.traces += text
    elif field == "blocked":
        story.blocked += text
    elif field == "criteria":
        story.criteria[-1] += text
    elif field in WRAPPED:
        setattr(story, WRAPPED[field], getattr(story, WRAPPED[field]) + text)
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
    for line in body.split("\n"):
        heading = STORY_HEADING.match(line)
        if not heading and re.match(r"^###\s+S-", line):
            stories.append(Story("?", line.lstrip("# ").strip()))  # kept, so the caller reports it instead of dropping it
            stories[-1].extra.append("unreadable story heading: " + line.strip())
            current, state = stories[-1], {"last": None, "gap": False, "table": False, "block": None}
            continue
        if heading:
            current = Story(heading.group(1), heading.group(2))
            stories.append(current)
            state = {"last": None, "gap": False, "table": False, "block": None}
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
    if story.state == "merged":  # a pointer to the story that took its work; it needs no fields of its own
        problems += [f"{story.id}: blocked by {sid}, which is not a story in this plan" for sid in blockers(story) if sid not in story_ids]
        if not set(story_refs(story.status)) & story_ids:
            problems.append(f"{story.id}: 'Status: merged' names no story of this plan to merge into")
        return problems
    if not story.traces:
        problems.append(f"{story.id}: no 'Traces to:' line")
    elif not VAULT_ID.findall(story.traces) and not CONSTRAINT_ID.search(story.traces) and not NO_TRACE.match(story.traces):
        problems.append(f"{story.id}: 'Traces to' names no requirement ID, so the ticket has no labels")
    if not story.criteria:
        problems.append(f"{story.id}: no acceptance criteria bullets")
    if not story.tasks and story.state != "deferred":  # a deferred story may not be sized yet; a held one is
        problems.append(f"{story.id}: no task table rows")
    if story.blocked is None:
        problems.append(f"{story.id}: no 'Blocked by:' line")
    if story.slice_text is not None and story.slice_text.split()[:1] and story.slice_text.split()[0].lower().strip(".,;:") not in SLICES:
        problems.append(f"{story.id}: 'Slice:' starts with {story.slice_text.split()[0] if story.slice_text.split() else 'nothing'!r}, not tracer, vertical or layer")
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
    return [] if NO_BLOCKERS.match(story.blocked or "") else story_refs(story.blocked)


def labels_of(story):
    seen = []
    for found in VAULT_ID.findall(story.traces or ""):
        found = found.rstrip("-")
        if found not in seen:
            seen.append(found)
    return seen


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
    meta, body, why = split_frontmatter(text)
    problems = []
    if why:
        problems.append(f"no frontmatter was read ({why[0].lower()}{why[1:]}) so the plan has no status")
    elif meta.get("status") not in STATUSES:
        problems.append(f"frontmatter status is {meta.get('status')!r}; the plan should be {' or '.join(STATUSES)}")
    stories = parse_story_sections(body)
    if not stories:
        problems.append("no `### S-NN <name>` story section found")
    sections = sections_of(body)
    summary = summary_table(body.split("\n"))
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
        cells = [r[c] for c in COLUMNS] + r["labels"] + [""] * (width - len(r["labels"])) + [r["Blocked by"]]
        writer.writerow([export.defuse(cell) if isinstance(cell, str) else cell for cell in cells])
    return out.getvalue()
