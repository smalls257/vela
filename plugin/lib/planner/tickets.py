"""Tickets from a build plan: the checks against the vault, and the two files a person can ask for. No model, no network.

    convert_text(text, source)         -> (tickets.csv text, README text, problems); the caller writes the files
    markdown_text(plan, source)        -> the Markdown ticket list
    check(plan, vault, app_id, ...)    -> [Finding]; every finding is a line a person reads before any ticket exists
    summary(plan, findings)            -> "9 stories, 42 tasks, 2 flagged"

The Violation this exists to prevent is a Paper Tiger: a ticket list that mirrors the plan and passes the converter
while a story rests on no criterion in the vault, quotes one loosely, or waits on a story that is not there. The
converter (breakdown.py) reads the plan alone; this module holds the plan against the vault, so the check runs before
the people downstream get a ticket. It reads, never writes the vault, and creates nothing in any outside system.

Pure, like the rest of the core: text in, text out. `tools/breakdown_to_tickets.py` and `planner tickets` both call
convert_text() and write what it returns, so the installed plugin and a repo checkout write the same files.
"""
import difflib
import re

from planner import allocation, criteria, releases, slices, trace
from planner import breakdown
from planner.breakdown import SIZE_POINTS, build_rows, csv_text, parse

CRITERION_ID = re.compile(r"^EPC-\d+\.AC\d+$")
REQUIREMENT_ID = re.compile(r"^CAP-\d+\.FR\d+(?:@APP-[A-Za-z0-9-]+)?$")
UNKNOWN_ID = re.compile(r"\bUNK-\d+\b")
WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
LOOSE = 0.75  # how alike a bullet and a vault sentence must be before the bullet counts as a reworded copy of it


class TicketsError(Exception):
    """The plan could not be found, read or written; nothing was converted."""


# ------------------------------------------------------------------------------------------------- the files

README = """# Tickets from the work breakdown

`tickets.csv` was written by `{tool}` from `{source}`. No model touched it: each Story row is a
`### S-NN` section and each Task row is a row of that story's task table, in the breakdown's own words. Nothing was
added, merged or reworded. {counts}

## How each column is filled

| Column | From |
|---|---|
| Issue Id | `S-NN` for a story, `S-NN-Tn` for its nth task. Used only to link rows during import. |
| Summary | the story heading (`S-NN name`), or the task's name |
| Description | story: its Traces to line, its acceptance criteria under an "Acceptance criteria" heading, its Blocked by line, then its Done when, Components, Slice and Release fit lines, any "Open for the design" notes and "Conflicts" notes, each as written. Task: its component, size, and its story's Traces to line |
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

TOOL = "tools/breakdown_to_tickets.py"


def not_ticketed(stories):
    """Lines for the stories the plan will not build, so the README names them instead of leaving a silent gap."""
    return [f"{s.id} {s.name}: {s.status}" for s in stories if not s.built]


def readme_text(source, stories, rows, problems, not_planned, tool=TOOL):
    built = [s for s in stories if s.built]
    counts = f"{len(built)} stories and {sum(len(s.tasks) for s in built)} tasks, {len(rows)} rows."
    prob = ("\n## Problems\n\nThese lines could not be mapped cleanly. Fix the breakdown (or the ticket by hand), then run again.\n\n"
            + "\n".join(f"- {p}" for p in problems) + "\n") if problems else "\nNo problems: every line of the breakdown mapped.\n"
    listed = [*not_ticketed(stories), *not_planned]
    notp = ("\n## Not ticketed\n\nThe breakdown lists these as deferred, merged or not planned, so they have no ticket:\n\n"
            + "\n".join(f"- {n}" for n in listed) + "\n") if listed else ""
    return README.format(source=source, counts=counts, s=SIZE_POINTS["S"], m=SIZE_POINTS["M"], l=SIZE_POINTS["L"],
                         problems=prob, not_planned=notp, tool=tool)


def retire_pointers(stories, problems):
    """An old plan's "(merged into S-05)" heading with no tasks is a pointer, not work: named in the problems, not ticketed.
    A story carrying `Status: merged` is already a pointer to the reader."""
    pattern = re.compile(r"\bmerged into (S-\d+[a-z]?)", re.I)
    retired = [s for s in stories if s.built and not s.tasks and pattern.search(" ".join([s.name, *s.extra]))]
    kept = [s for s in stories if s not in retired]
    problems = [p for p in problems if not any(p.startswith(f"{s.id}:") for s in retired)]
    problems += [f"{s.id}: merged into {pattern.search(' '.join([s.name, *s.extra])).group(1)}, so not exported" for s in retired]
    return kept, problems


def convert_text(text, source, tool=TOOL):
    """(tickets.csv text, README text, problems) for one plan's text. Problems is empty when every line mapped."""
    stories, not_planned, problems = parse(text)
    stories, problems = retire_pointers(stories, problems)
    rows = build_rows(stories)
    return csv_text(rows), readme_text(source, stories, rows, problems, not_planned, tool), problems


# ----------------------------------------------------------------------------------------------- Markdown

def blocked_in_words(story):
    return story.blocked if story.blocked and not breakdown.NOTHING.match(story.blocked) else "nothing"


def story_markdown(story):
    lines = [f"## {story.id} {story.name}", ""]
    meta = [("Slice", story.slice_text), ("Size", breakdown.size_total(story)), ("Components", story.components),
            ("Blocked by", blocked_in_words(story)), ("Traces to", story.traces), ("Release fit", story.fit)]
    lines += [f"- {label}: {value}" for label, value in meta if value]
    if story.done_when:
        lines += ["", f"Done when: {story.done_when}"]
    if story.criteria:
        lines += ["", story.criteria_label or "Acceptance criteria:", ""] + [f"- {c}" for c in story.criteria]
    if story.tasks:
        lines += ["", "Tasks:", ""]
        for number, row in enumerate(story.tasks, 1):
            size, component = (row[1] if len(row) > 1 else ""), (row[2] if len(row) > 2 else "")
            lines.append(f"- [ ] {story.id}-T{number} {row[0]} (size {size}; {component})")
    for note in [*story.open_notes, *story.conflicts]:
        lines += ["", note]
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


def markdown_text(text, source, vault=None):
    """The Markdown ticket list for a plan's text: one section per story that will be built, its tasks as a checklist.
    Grouped by slice: the tracer first, then each slice in the vault's order, then stories that name none, each group
    in the plan's build order."""
    plan = breakdown.read(text)
    stories, _ = retire_pointers(plan["stories"], [])
    ranked = {o["id"]: i for i, o in enumerate(plan["order"])}
    order = {s.id: s.order for s in slices.read_slices(vault)} if vault is not None and slices.on_pages(vault) else {}
    first = tracer_id(vault)

    def place(story):
        group = order.get(story.slice_id, len(order) + (0 if story.slice_id else 1))
        return (not is_tracer(story, first), group, story.slice_id, ranked.get(story.id, len(ranked)))

    built = sorted((s for s in stories if s.built), key=place)
    title = str(plan["meta"].get("slug", source))
    counts = summary_line(built, 0).rsplit(",", 1)[0]
    lines = [f"# Tickets for {title}", "", f"From `{source}`: {counts}, tracer stories first, then grouped by slice. "
             "Sizes are for ordering, not commitments.", ""]
    for story in built:
        lines += story_markdown(story)
    skipped = not_ticketed(stories)
    if skipped:
        lines += ["## Not ticketed", ""] + [f"- {s}" for s in skipped] + [""]
    waves = waves_text(text)
    if waves:
        lines += ["## When to create them", "", waves, ""]
    return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------------------------------------- the checks

class Finding:
    """One line for a person: `story` is "" when it belongs to the plan as a whole; `flag` says it counts as flagged."""

    def __init__(self, kind, story, text, flag=True):
        self.kind, self.story, self.text, self.flag = kind, story, text, flag

    def __str__(self):
        return f"{'Story ' + self.story + ' ' if self.story else ''}{self.text}"

    def __repr__(self):
        return f"Finding({self.kind!r}, {self.story!r}, {self.text!r})"


def normal(text):
    """A sentence as a reader compares it: wiki links shown as their words, runs of space as one, curly quotes straight."""
    text = WIKILINK.sub(r"\1", text or "")
    for fancy, plain in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"')):
        text = text.replace(fancy, plain)
    return re.sub(r"\s+", " ", text).strip()


def statement_of(item):
    """The sentence under a requirement's heading, before its fact bullets: what the requirement says."""
    out = []
    for line in item.page.text.split("\n")[item.line:]:
        if line.startswith("#") or line.lstrip().startswith("-") or (out and not line.strip()):
            break
        if line.strip():
            out.append(line.strip())
    return " ".join(out)


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
    from planner.explorer import design_data
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


def check(text, vault, app_id=""):
    """Every finding about a plan's text held against the vault. `app_id` defaults to the plan's `vault.app`."""
    from planner.explorer import design_data
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
