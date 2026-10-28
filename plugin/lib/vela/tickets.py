"""Tickets from a build plan: the checks against the vault, and the files a person can ask for.

    convert_text(text, source, ...)    -> (tickets.csv text, README text, problems); the caller writes the files
    markdown_text(plan, source, ...)   -> the Markdown ticket list
    jira_text(plan, source, vault, ...) -> tickets-jira.json, each ticket as a Jira tool would create it
    check(plan, vault, app_id, ...)    -> [Finding]; every finding is a line a person reads before any ticket exists
    summary(plan, findings)            -> "9 stories, 42 tasks, 2 flagged"

The summary and grouped criteria of each story are model-written, into the plan; this module checks them (ticketcopy)
and copies everything else from the plan and the vault by code (ticketrefs). No network.

The Violation this exists to prevent is a Paper Tiger: a ticket list that mirrors the plan and passes the converter
while a story rests on no criterion in the vault, quotes one loosely, or waits on a story that is not there. A ticket
that drops a criterion while reading better than the plan is the same Paper Tiger, which the coverage check is for.
The converter (breakdown.py) reads the plan alone; this module holds the plan against the vault, so the check runs before
the people downstream get a ticket. It reads, never writes the vault, and creates nothing in any outside system.

Pure, like the rest of the core: text in, text out. `tools/breakdown_to_tickets.py` and `vela tickets` both call
convert_text() and write what it returns, so the installed plugin and a repo checkout write the same files.
"""
import difflib
import json
import re

from vela import allocation, criteria, releases, slices, ticketcopy, ticketrefs, trace
from vela.say import date_words
from vela import breakdown
from vela.ticketrefs import normal, statement_of
from vela.breakdown import SIZE_POINTS, csv_text, parse

CRITERION_ID = re.compile(r"^EPC-\d+\.AC\d+$")
REQUIREMENT_ID = re.compile(r"^CAP-\d+\.FR\d+(?:@APP-[A-Za-z0-9-]+)?$")
UNKNOWN_ID = re.compile(r"\bUNK-\d+\b")
LOOSE = 0.75  # how alike a bullet and a vault sentence must be before the bullet counts as a reworded copy of it


class TicketsError(Exception):
    """The plan could not be found, read or written; nothing was converted."""


# ------------------------------------------------------------------------------------------------- the files

README = """# Tickets from the work breakdown

`tickets.csv` was written by `{tool}` from `{source}`. Each Story row is a `### S-NN` section of the plan and each Task row a row of its task table. {copy_note} What a story relies on (contracts and requirements) and what it still waits on (open questions) are copied by code from the vault and the design. {counts}{vault_note}

## How each column is filled

| Column | From |
|---|---|
| Issue Id | `S-NN` for a story, `S-NN-Tn` for its nth task. Used only to link rows during import. |
| Summary | the story's name, or the task's name |
| Description | story: its summary, its acceptance criteria (grouped, each line tagged with the plan criteria it covers, or the plan's own list when the story has no grouped criteria yet), Done when, What this story relies on, Still open, then Components, Slice, Size, Blocked by (stories by name), anything else it waits on, Release fit, and any "Open for the design" and "Conflicts" notes. Task: its component, size and its story's name |
| Issue Type | Story for a section, Task for a task row. The breakdown has no epic level, so there are no Epics |
| Parent | a task's Issue Id of its story. Blank for stories |
| Story Points | tasks only: S = {s}, M = {m}, L = {l}. The work-breakdown skill gives sizes in days, not points, so this mapping is ours, and sizes are for ordering, not commitments. Stories carry no points so the total is not counted twice |
| Labels | the requirement and contract IDs on the story's Traces to line, each epic a criterion belongs to (`EPC-nnn`) and any app ID; then its slice shape (tracer, vertical, layer) and vault slice; `needs-design` for an "Open for ..." note and `conflict` for a "Conflict with ..." note. A task has its story's IDs only |
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

TOOL = "tools/breakdown_to_tickets.py"


def not_ticketed(stories):
    """Lines for the stories the plan will not build, so the README names them instead of leaving a silent gap."""
    return [f"{s.name}{suffix(s.id, SUB)}: {s.status}" for s in stories if not s.built]


def readme_text(source, stories, rows, problems, not_planned, tool=TOOL, with_vault=True):
    built = [s for s in stories if s.built]
    counts = f"{len(built)} stories and {sum(len(s.tasks) for s in built)} tasks, {len(rows)} rows."
    prob = ("\n## Problems\n\nThese lines could not be mapped cleanly. Fix the breakdown (or the ticket by hand), then run again.\n\n"
            + "\n".join(f"- {p}" for p in problems) + "\n") if problems else "\nNo problems: every line of the breakdown mapped.\n"
    listed = [*not_ticketed(stories), *not_planned]
    notp = ("\n## Not ticketed\n\nThe breakdown lists these as deferred, merged or not planned, so they have no ticket:\n\n"
            + "\n".join(f"- {n}" for n in listed) + "\n") if listed else ""
    lacking = [s for s in built if not ticketcopy.has_copy(s)]
    copy_note = ("A story's summary and its grouped acceptance criteria were written into the plan in the house voice, and vela checked that every one of the plan's criteria is still covered; the plan keeps its criteria word for word."
                 if not lacking else
                 "None of the stories has ticket copy yet, so each ticket carries the plan's criteria as a flat list." if len(lacking) == len(built) else
                 f"{len(built) - len(lacking)} of {len(built)} stories have a summary and grouped acceptance criteria, written into the plan in the house voice and checked against the plan's criteria; the other {len(lacking)} carry the plan's criteria as a flat list.")
    vault_note = "" if with_vault else " This file was written without the vault, so each ticket names what it relies on by ID only."
    return README.format(source=source, counts=counts, s=SIZE_POINTS["S"], m=SIZE_POINTS["M"], l=SIZE_POINTS["L"],
                         problems=prob, not_planned=notp, tool=tool, vault_note=vault_note, copy_note=copy_note)


def retire_pointers(stories, problems):
    """An old plan's "(merged into S-05)" heading with no tasks is a pointer, not work: named in the problems, not ticketed.
    A story carrying `Status: merged` is already a pointer to the reader."""
    pattern = re.compile(r"\bmerged into (S-\d+[a-z]?)", re.I)
    retired = [s for s in stories if s.built and not s.tasks and pattern.search(" ".join([s.name, *s.extra]))]
    kept = [s for s in stories if s not in retired]
    problems = [p for p in problems if not any(p.startswith(f"{s.id}:") for s in retired)]
    problems += [f"{s.id}: merged into {pattern.search(' '.join([s.name, *s.extra])).group(1)}, so not exported" for s in retired]
    return kept, problems


def copy_problems(stories):
    """The flagged lines about ticket copy, as the README lists them."""
    return [f"{s.id}: {t}" for s in stories if s.built for t, flag in ticketcopy.problems(s) if flag]


def app_of_plan(text):
    return str((breakdown.read(text)["meta"].get("vault") or {}).get("app", ""))


def convert_text(text, source, vault=None, app_id="", questions=None, tool=TOOL, keys=None, design_gap=""):
    """(tickets.csv text, README text, problems) for one plan's text. Problems is empty when every line mapped and
    every story has ticket copy that covers its criteria."""
    stories, not_planned, problems = parse(text)
    stories, problems = retire_pointers(stories, problems)
    ctx = Context(stories, vault, app_id or app_of_plan(text), questions, keys)
    problems = problems + copy_problems(stories)
    if vault is not None:
        problems += [f"{s.id}: {t}" for s in stories if s.built for t, flag in ticketrefs.open_problems(vault, s, questions, design_gap) if flag]
    rows = build_rows(stories, ctx)
    return csv_text(rows), readme_text(source, stories, rows, problems, not_planned, tool, with_vault=vault is not None), problems


# ------------------------------------------------------------------------------- one ticket, two renderings

SUB, PARENS = "sub", "parens"  # an ID as a small suffix in tickets.md, or in brackets where HTML would show as text
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
ANY_ID = re.compile(r"\b[A-Z]{1,4}-\d+[a-z]?\b")
KEY_LINE = re.compile(r"^\s*(S-\d+[a-z]?)\s*[:=]?\s+([A-Z][A-Z0-9_]*-\d+)\s*$")


class Context:
    """What a ticket is written from besides its story: the loaded vault (None writes names only, and says so), the
    plan's app, the design's open questions, each story's name for "Blocked by", and ticket keys already created."""

    def __init__(self, stories, vault=None, app_id="", questions=None, keys=None):
        self.vault, self.app_id, self.questions, self.keys = vault, app_id, questions, dict(keys or {})
        self.names = {s.id: s.name for s in stories}


def suffix(ident, style):
    if not ident:
        return ""
    return f" <sub>{ident}</sub>" if style == SUB else f" ({ident})"


def count_words(n, one):
    word = NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)
    return f"{word} {one if n == 1 else one + 's'}"


def american(text):
    return ISO_DATE.sub(lambda m: date_words(m.group(0)), text or "")


def criteria_parts(story):
    """[(heading, [(words, tag)])]: the grouped ticket copy, or, with no copy yet, the plan's list as one group."""
    if not ticketcopy.has_copy(story):
        return [("", [(c, f"AC{n}") for n, c in enumerate(story.criteria, 1)])]
    out = []
    for heading, lines in story.ticket_groups:
        rows = []
        for line in lines:
            words, numbers, _ = ticketcopy.tag_of(line)
            rows.append((words, "covers " + ", ".join(f"AC{n}" for n in numbers) if numbers else ""))
        out.append((heading, rows))
    return out


def lead_in(story):
    """The plan's own lead-in on its criteria label ("Acceptance criteria. No epic criterion covers this story, ..."), kept."""
    label = (story.criteria_label or "").strip()
    return label if label and label.lower().rstrip(":").strip() != "acceptance criteria" else ""


def contract_facts(ref):
    if ref["sends"] is not None:
        sends, gets = ("Receives", "Answers with") if ref["provides"] else ("Sends", "Gets back")
        facts = [(sends, ref["sends"]), (gets, ref["gets"])]
    else:
        facts = [("What crosses", ref["crosses"] or "not written in the vault")]
    held = f", {count_words(ref['open'], 'open question')} on it" if ref["open"] else ""
    return facts + [("Provided by", ref["provider"]), ("Status", (ref["state"] or "not written in the vault") + held)]


def relies_entries(story, ctx):
    """[(title, id, paragraph or None, [(label, value)])] for each contract and requirement, or one names-only line."""
    if ctx.vault is None:
        ids = [t.split("@")[0] for t in breakdown.labels_of(story) if re.match(r"^(CON-\d+|CAP-\d+\.FR\d+)", t)]
        return [("Written without the vault, so what this story relies on is named by ID only: " + ", ".join(ids) + ".", "", None, [])] if ids else []
    out = []
    for ref in ticketrefs.relies_on(ctx.vault, story, ctx.app_id):
        if ref["kind"] == "contract":
            out.append((ref["name"], ref["id"], ref["description"] or None, contract_facts(ref)))
        elif ref["kind"] == "requirement":
            out.append((ref["name"], ref["id"], ref["statement"], []))
        else:
            out.append(("Not found in the vault", ref["id"], None, []))
    return out


def open_entries(story, ctx):
    if ctx.vault is None:
        return []
    out = []
    for q in ticketrefs.still_open(ctx.vault, story, ctx.questions):
        if not q["found"]:
            unread = q["id"].startswith("OQ-") and ctx.questions is None
            out.append(("Not looked up: the plan's design wasn't read" if unread else "Not found in the plan's design or the vault", q["id"], None, []))
            continue
        out.append((q["question"], q["id"], None, [("Until it's answered", q["until"] or "the plan doesn't say"),
                                                  (q["waits_label"], q["waits"] or "not written down")]))
    return out


def blocked_words(story, ctx, style):
    ids = breakdown.blockers(story)
    if not ids:
        return "nothing"
    return ", ".join(f"{ctx.keys[s] + ' ' if s in ctx.keys else ''}{ctx.names.get(s, s)}{suffix(s, style)}" for s in ids)


def also_waits(story, shown):
    """The plan's Blocked by sentences a reader would otherwise lose: each that names anything besides the blocking
    stories (shown by name) and the questions shown under Still open, in the plan's own words."""
    text = story.blocked or ""
    if breakdown.NO_BLOCKERS.match(text):
        text = breakdown.NO_BLOCKERS.sub("", text, count=1).lstrip(" .;:,")
    kept = []
    for sentence in re.split(r"(?<=[.?!])\s+", text.strip()):
        named = set(ANY_ID.findall(sentence))
        if sentence and not (named and named <= shown):
            kept.append(sentence)
    return " ".join(kept)


def slice_words(story, ctx, style):
    sid = story.slice_id
    if sid and ctx.vault is not None and story.slice:
        return f"{story.slice}, {ctx.vault.name_of(sid)}{suffix(sid, style)}"
    return story.slice_text or ""


def details(story, ctx, style):
    shown = set(breakdown.blockers(story)) | {q[1] for q in open_entries(story, ctx)}
    rest = "Note" if breakdown.NO_BLOCKERS.match(story.blocked or "") else "Also waits on"  # "none. D-001 runs in parallel" is a note, not a wait
    rows = [("Components", story.components or ""), ("Slice", slice_words(story, ctx, style)),
            ("Size", breakdown.size_total(story)), ("Blocked by", blocked_words(story, ctx, style)),
            (rest, also_waits(story, shown)), ("Release fit", american(story.fit)), ("Status", story.status or "")]
    return [(label, value) for label, value in rows if value]


def trace_labels(story):
    """The story's trace IDs as Jira labels: a requirement without its app, a criterion as its epic, each once."""
    out = []
    for found in breakdown.labels_of(story):
        base = found.split("@")[0]
        base = base.split(".AC")[0] if base.startswith("EPC-") else base
        if base not in out:
            out.append(base)
    return out


def ticket_labels(story):
    shape = [story.slice] if story.slice else []
    vault_slice = [story.slice_id] if story.slice_id else []
    flags = ([breakdown.LABEL_NEEDS_DESIGN] if story.open_notes else []) + ([breakdown.LABEL_CONFLICT] if story.conflicts else [])
    return trace_labels(story) + shape + vault_slice + flags


def entries_markdown(heading, entries, style):
    if not entries:
        return []
    out = [f"### {heading}", ""]
    for title, ident, text, facts in entries:
        out += [f"**{title}**{suffix(ident, style)}" if ident else title, ""]
        out += [text, ""] if text else []
        out += [f"- {label}: {value}" for label, value in facts] + ([""] if facts else [])
    return out


def ticket_markdown(story, ctx, style):
    """A story's ticket description as Markdown: tickets.md uses SUB; the Jira tools path uses PARENS."""
    out = [story.summary, ""] if story.summary else []
    out += ["### Acceptance criteria", ""] + ([lead_in(story), ""] if lead_in(story) else [])
    for heading, rows in criteria_parts(story):
        out += [f"**{heading}**", ""] if heading else []
        out += [f"- {words}{suffix(tag, style)}" for words, tag in rows] + [""]
    out += [f"Done when: {story.done_when}", ""] if story.done_when else []
    out += entries_markdown("What this story relies on", relies_entries(story, ctx), style)
    out += entries_markdown("Still open", open_entries(story, ctx), style)
    for label, notes in (("Open for the design", story.open_notes), ("Conflicts", story.conflicts)):
        out += [f"### {label}", ""] + [f"- {n}" for n in notes] + [""] if notes else []
    out += ["### Details", ""] + [f"- {label}: {value}" for label, value in details(story, ctx, style)]
    out += [f"- Labels: {', '.join(ticket_labels(story))}"] + ([""] + story.extra if story.extra else [])
    return "\n".join(out).rstrip() + "\n"


def entries_plain(heading, entries):
    if not entries:
        return []
    out = [f"{heading}:"]
    for title, ident, text, facts in entries:
        out += [f"{title}{suffix(ident, PARENS)}"] + ([text] if text else []) + [f"- {label}: {value}" for label, value in facts]
    return out + [""]


def ticket_plain(story, ctx):
    """The same ticket as plain lines, for the CSV Description: headings end in a colon, IDs in brackets."""
    out = [story.summary, ""] if story.summary else []
    out.append(lead_in(story) or "Acceptance criteria:")
    for heading, rows in criteria_parts(story):
        out += [f"{heading}:"] if heading else []
        out += [f"- {words}{suffix(tag, PARENS)}" for words, tag in rows]
    out += [""] + ([f"Done when: {story.done_when}", ""] if story.done_when else [])
    out += entries_plain("What this story relies on", relies_entries(story, ctx))
    out += entries_plain("Still open", open_entries(story, ctx))
    out += [f"{label}: {value}" for label, value in details(story, ctx, PARENS)]
    if story.open_notes:
        out += ["Open for the design:"] + [f"- {n}" for n in story.open_notes]
    if story.conflicts:
        out += ["Conflicts:"] + [f"- {c}" for c in story.conflicts]
    return "\n".join(out + story.extra).rstrip()


def task_description(story, row):
    component = row[2] if len(row) > 2 else ""
    size = row[1] if len(row) > 1 else ""
    return f"Component: {component}\nSize: {size}\nStory: {story.name} ({story.id})"


def build_rows(stories, ctx):
    """One row per story that will be built and one per task row, in file order."""
    rows = []
    for story in stories:
        if not story.built:
            continue  # deferred or merged: the README lists it as not ticketed
        rows.append({"Issue Id": story.id, "Summary": story.name.strip(), "Description": ticket_plain(story, ctx),
                     "Issue Type": "Story", "Parent": "", "Story Points": "", "labels": ticket_labels(story),
                     "Blocked by": ", ".join(dict.fromkeys(breakdown.blockers(story)))})
        for number, row in enumerate(story.tasks, 1):
            size = row[1].strip().upper() if len(row) > 1 else ""
            rows.append({"Issue Id": f"{story.id}-T{number}", "Summary": row[0], "Description": task_description(story, row),
                         "Issue Type": "Task", "Parent": story.id, "Story Points": SIZE_POINTS.get(size, ""),
                         "labels": trace_labels(story), "Blocked by": ""})
    return rows


def csv_for(stories, ctx):
    """The Jira CSV import: what `vela tickets write --format csv`, the tool and the explorer's "Copy as Jira CSV" all write."""
    return csv_text(build_rows(stories, ctx))


def read_keys(text, stories):
    """{story ID: ticket key} from a keys file of `S-01 HERON-11` lines. A line that isn't one, a story the plan doesn't
    ticket (deferred or merged) and a story named twice each stop the write."""
    ticketed = {s.id for s in stories if s.built}
    named = {s.id for s in stories}
    keys = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        found = KEY_LINE.match(line)
        if not found or found.group(1) not in named:
            raise TicketsError(f"line {n} of the keys file isn't 'S-nn KEY-n' for a story of this plan: {line.strip()!r}")
        if found.group(1) not in ticketed:
            raise TicketsError(f"line {n} of the keys file names {found.group(1)}, which the plan doesn't ticket (deferred or merged)")
        if found.group(1) in keys:
            raise TicketsError(f"line {n} of the keys file names {found.group(1)} a second time")
        keys[found.group(1)] = found.group(2)
    return keys


# ----------------------------------------------------------------------------------------------- Markdown

def story_markdown(story, ctx):
    lines = [f"## {story.name}{suffix(story.id, SUB)}", "", ticket_markdown(story, ctx, SUB).rstrip()]
    if story.tasks:
        lines += ["", "Tasks:", ""]
        for number, row in enumerate(story.tasks, 1):
            size, component = (row[1] if len(row) > 1 else ""), (row[2] if len(row) > 2 else "")
            lines.append(f"- [ ] {row[0]} (size {size}; {component}){suffix(f'{story.id}-T{number}', SUB)}")
    return lines + [""]


def waves_text(text):
    """The plan's own "Ticket waves" section, if it has one: which tickets to create now and which to hold."""
    _, body, _ = breakdown.split_frontmatter(text)
    for name, lines in breakdown.sections_of(body).items():
        if name.lower().startswith("ticket waves"):
            return "\n".join(lines).strip()
    return ""


def tracer_id(vault):
    """The tracer slice's ID, "" while the vault has no slice pages."""
    first = slices.tracer(slices.read_slices(vault)) if vault is not None and slices.on_pages(vault) else None
    return first.id if first else ""


def ticket_order(plan, stories, vault):
    """The stories that will be built, tracer first, then each slice in the vault's order, then stories that name
    none, each group in the plan's build order. Tickets.md and the Jira file are written in this one order."""
    ranked = {o["id"]: i for i, o in enumerate(plan["order"])}
    order = {s.id: s.order for s in slices.read_slices(vault)} if vault is not None and slices.on_pages(vault) else {}
    first = tracer_id(vault)

    def place(story):
        group = order.get(story.slice_id, len(order) + (0 if story.slice_id else 1))
        return (not is_tracer(story, first), group, story.slice_id, ranked.get(story.id, len(ranked)))

    return sorted((s for s in stories if s.built), key=place)


def markdown_text(text, source, vault=None, questions=None, keys=None):
    """The Markdown ticket list for a plan's text: one section per story that will be built, its tasks as a checklist.
    Grouped by slice: the tracer first, then each slice in the vault's order, then stories that name none, each group
    in the plan's build order."""
    plan = breakdown.read(text)
    stories, _ = retire_pointers(plan["stories"], [])
    ctx = Context(stories, vault, app_of_plan(text), questions, keys)
    built = ticket_order(plan, stories, vault)
    title = str(plan["meta"].get("slug", source))
    counts = summary_line(built, 0).rsplit(",", 1)[0]
    lines = [f"# Tickets for {title}", "", f"From `{source}`: {counts}, tracer stories first, then grouped by slice. "
             "Sizes are for ordering, not commitments.", ""]
    for story in built:
        lines += story_markdown(story, ctx)
    skipped = not_ticketed(stories)
    if skipped:
        lines += ["## Not ticketed", ""] + [f"- {s}" for s in skipped] + [""]
    waves = waves_text(text)
    if waves:
        lines += ["## When to create them", "", waves, ""]
    return "\n".join(lines).rstrip() + "\n"


def jira_text(text, source, vault, questions=None, keys=None):
    """tickets-jira.json: each ticket as a Jira tool would create it, in the order of tickets.md. A skill copies each
    field as it is; it never assembles or retypes a description."""
    plan = breakdown.read(text)
    stories, _ = retire_pointers(plan["stories"], [])
    ctx = Context(stories, vault, app_of_plan(text), questions, keys)
    built = ticket_order(plan, stories, vault)
    tasks = lambda s: [{"id": f"{s.id}-T{n}", "summary": row[0], "description": task_description(s, row),
                        "labels": trace_labels(s),
                        "points": SIZE_POINTS.get(row[1].strip().upper(), "") if len(row) > 1 else ""}
                       for n, row in enumerate(s.tasks, 1)]
    data = {"source": source,
            "stories": [{"id": s.id, "summary": s.name, "description": ticket_markdown(s, ctx, PARENS),
                         "labels": ticket_labels(s), "blocked_by": breakdown.blockers(s), "tasks": tasks(s)} for s in built],
            "not_ticketed": not_ticketed(stories)}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ------------------------------------------------------------------------------------------------- the checks

class Finding:
    """One line for a person: `story` is "" when it belongs to the plan as a whole; `flag` says it counts as flagged."""

    def __init__(self, kind, story, text, flag=True):
        self.kind, self.story, self.text, self.flag = kind, story, text, flag

    def __str__(self):
        return f"{'Story ' + self.story + ' ' if self.story else ''}{self.text}"

    def __repr__(self):
        return f"Finding({self.kind!r}, {self.story!r}, {self.text!r})"


def vault_sentence(vault, target):
    """The words the vault gives for a trace target a story must quote, or None when the vault has none to quote."""
    base = target.split("@")[0]
    if CRITERION_ID.match(base):
        epic_id, ac = base.split(".AC")
        epic = next((e for e in trace.epics(vault) if e.id == epic_id), None)
        found = next((c for c in criteria.read(epic) if c.n == int(ac) and not c.struck), None) if epic else None
        return found.raw if found else None
    if REQUIREMENT_ID.match(target):
        items = vault.items.get(base)
        return statement_of(items[0]) if items else None
    return None


def check_quote(story, target, sentence):
    """A finding when none of the story's bullets is `sentence` word for word, naming the nearest bullet if there is one."""
    want = normal(sentence)
    bullets = [normal(c) for c in story.criteria]
    if want in bullets:
        return None
    near = max(bullets, key=lambda b: difflib.SequenceMatcher(None, want, b).ratio(), default="")
    if near and difflib.SequenceMatcher(None, want, near).ratio() >= LOOSE:
        return Finding("criteria", story.id, f"the criterion for {target} is reworded; the vault says: {sentence!r}")
    return Finding("criteria", story.id, f"no acceptance criterion quotes {target}; the vault says: {sentence!r}")


def requirements_of(vault, ids):
    """The functional requirements (CAP-nnn.FRn) a story rests on: the ones it names, and those its epic criteria trace to."""
    found = [i.split("@")[0] for i in ids if REQUIREMENT_ID.match(i)]
    for target in ids:
        if CRITERION_ID.match(target):
            epic_id, ac = target.split(".AC")
            epic = next((e for e in trace.epics(vault) if e.id == epic_id), None)
            for c in criteria.read(epic) if epic else []:
                if c.n == int(ac):
                    found += [t for t in c.trace if re.match(r"^CAP-\d+\.FR\d+$", t)]
    return list(dict.fromkeys(found))


def release_dates(vault):
    """{requirement ID: earliest release target (YYYY-MM-DD) that delivers it}."""
    out = {}
    for release in releases.releases(vault):
        for row in release.rows:
            if row.requirement and re.match(r"^\d{4}-\d{2}-\d{2}$", release.target):
                out[row.requirement] = min(release.target, out.get(row.requirement, release.target))
    return out


def story_release(vault, story, dates):
    ids = breakdown.labels_of(story)
    found = [dates[r] for r in requirements_of(vault, ids) if r in dates]
    return min(found) if found else ""


def check_story(vault, story, known, dates):
    """The findings about one story the team will build."""
    out = []
    ids = breakdown.labels_of(story)
    checkable = [i for i in ids if CRITERION_ID.match(i) or REQUIREMENT_ID.match(i)]
    constraints = breakdown.CONSTRAINT_ID.findall(story.traces or "")
    if not checkable and constraints:
        out.append(Finding("trace", story.id, f"is linked only to a constraint ({', '.join(constraints)}), with no criterion to quote, so when it counts as done comes from the design", flag=False))
    elif not checkable:
        out.append(Finding("trace", story.id, "isn't linked to an epic's acceptance criterion or to a requirement the app owns, so nothing in the plan says when it's done"))
    for target in [*ids, *constraints]:
        if target not in known and target.split("@")[0] not in known:
            out.append(Finding("trace", story.id, f"is linked to {target}, which isn't in the plan"))
    for target in checkable:
        sentence = vault_sentence(vault, target)
        found = check_quote(story, target, sentence) if sentence else None
        if found:
            out.append(found)
    for unknown in UNKNOWN_ID.findall(story.blocked or ""):
        if unknown not in known:
            out.append(Finding("blocked", story.id, f"is blocked by {unknown}, which isn't in the plan"))
    out += check_slice(story)
    out += check_fit(vault, story, dates)
    return out


def check_slice(story):
    if story.slice == "layer":
        return [Finding("slice", story.id, "builds a layer nobody can see on its own, not a slice: fold it into the slice that needs it, or say why it stays separate")]
    if not story.slice:
        return [Finding("slice", story.id, "has no 'Slice:' line, so it isn't clear whether it is part of the tracer, a slice or a layer")]
    return []


def check_fit(vault, story, dates):
    release = story_release(vault, story, dates)
    if not story.fit:
        return [Finding("release", story.id, "has no 'Release fit:' line")]
    named = re.findall(r"\d{4}-\d{2}-\d{2}", story.fit)
    if release and named[:1] != [release]:
        return [Finding("release", story.id, f"has a 'Release fit' that doesn't start from {release}, the date of the first release that delivers what it is linked to")]
    if not release and named:
        return [Finding("release", story.id, "has a 'Release fit' that names a date, but nothing it is linked to is on a release")]
    return []


def check_coverage(vault, app_id, plan, stories):
    """A finding for each trace target of the app that no story to be built covers and no plan gap accepts."""
    from vela.explorer import design_data
    covered = {t.split("@")[0] for s in stories if s.built for t in breakdown.labels_of(s)}
    gaps = " ".join(str(g.get("what", "")) for g in plan["meta"].get("gaps") or [] if isinstance(g, dict))
    out = []
    for target in sorted(design_data.trace_targets(vault, app_id)):
        if target.split("@")[0] in covered:
            continue
        epic_or_requirement = target.split("@")[0].split(".")[0]  # a gap that names EPC-035 or "EPC-035.AC1 to AC5" accepts the whole epic's criteria
        accepted = re.search(rf"\b{re.escape(target.split('@')[0])}\b", gaps) or (target.startswith("EPC-") and re.search(rf"\b{epic_or_requirement}\b", gaps))
        out.append(Finding("coverage", "", f"No story builds {vault.named(target.split('@')[0])}"
                           + (f" for {vault.name_of(target.split('@')[1])}" if "@" in target else "")
                           + ("; the plan lists this as a known gap" if accepted else ""), flag=not accepted))
    return out


def is_tracer(story, tracer_id=""):
    """A story is the team's part of the tracer when it says so, or when it names the vault's tracer slice."""
    return story.slice == "tracer" or bool(tracer_id and story.slice_id == tracer_id)


def check_slices(vault, stories, app_id):
    """A story that names a slice the vault does not have, or one the app takes no part in, would be grouped under a
    slice nobody can find, or built for a journey that never reaches the app."""
    found = slices.read_slices(vault) if slices.on_pages(vault) else []
    known = {s.id: s for s in found}
    app = next((a for a in vault.apps if a.id == app_id), None)
    ours = {s.id for s in slices.for_app(vault, found, app)} if app is not None else set()
    out = []
    for story in stories:
        sid = story.slice_id
        if not sid or not story.built:
            continue
        if sid not in known:
            out.append(Finding("slice", story.id, f"names the slice {sid}, which isn't in the plan"))
        elif sid not in ours:
            out.append(Finding("slice", story.id, f"names the slice {known[sid].name} ({sid}), which {vault.name_of(app_id)} takes no part in"))
    return out


def check_tracer(stories, order, tracer_id=""):
    """Tracer stories come first in the build order; none at all needs an override the plan records."""
    tracers = [s.id for s in stories if s.built and is_tracer(s, tracer_id)]
    if not tracers:
        return [Finding("slice", "", "No story is marked as part of the tracer, and the plan doesn't record an exception saying the team starts elsewhere")]
    ranked = [o["id"] for o in order]
    first_other = next((i for i, sid in enumerate(ranked) if sid not in tracers), len(ranked))
    late = [sid for sid in tracers if sid in ranked and ranked.index(sid) > first_other]
    return [Finding("slice", sid, "is part of the tracer, but the build order puts another story before it") for sid in late]


def check(text, vault, app_id="", questions=None, design_gap=""):
    """Every finding about a plan's text held against the vault. `app_id` defaults to the plan's `vault.app`."""
    from vela.explorer import design_data
    plan = breakdown.read(text)
    app_id = app_id or str((plan["meta"].get("vault") or {}).get("app", ""))
    if not app_id or all(a.id != app_id for a in vault.apps):
        raise TicketsError(f"the plan names no app of this vault (found {app_id!r}); add `vault: {{app: APP-x}}` to its frontmatter or pass the app")
    known = design_data.vault_ids(vault)
    stories, _ = retire_pointers(plan["stories"], [])
    dates = release_dates(vault)
    out = [Finding("reading", "", p) for p in plan["problems"]]
    for story in stories:
        if story.built:
            out += check_story(vault, story, known, dates)
            out += [Finding("ticket", story.id, t, flag) for t, flag in ticketcopy.problems(story)]
            out += [Finding("open", story.id, t, flag) for t, flag in ticketrefs.open_problems(vault, story, questions, design_gap)]
    out += check_coverage(vault, app_id, plan, stories)
    out += check_slices(vault, stories, app_id)
    out += check_tracer(stories, plan["order"], tracer_id(vault))
    if "**Override:**" in text:
        out = [f for f in out if not (f.kind == "slice" and f.story == "" and f.text.startswith("No story is marked"))]
    return out


def summary_line(stories, flagged):
    built = [s for s in stories if s.built]
    return f"{len(built)} stories, {sum(len(s.tasks) for s in built)} tasks, {flagged} flagged"


def summary(text, findings):
    """The closing line: how many stories and tasks, how many stories or plan-wide lines are flagged."""
    plan = breakdown.read(text)
    stories, _ = retire_pointers(plan["stories"], [])
    flagged = {f.story or "(plan)" for f in findings if f.flag}
    return summary_line(stories, len(flagged))
