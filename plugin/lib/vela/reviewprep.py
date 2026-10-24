"""What a review checkpoint needs before any reviewer runs: its number, the pages each reviewer reads, the areas it
skips and why, and one packet per area (overhaul Task 20, `vela reviewers prepare`). Also the record's
`Digest shown:` line, which `vela questions --digest --session` reads and writes.

REVIEW sections 1 and 2 used to be lists and lookups the model walked by hand: count the `### ` headings, grep for the
ledger heading, diff each page for its changed lines, decide which areas owe nothing. Each step was a place to guess,
and a guessed number or a missing page is invisible until a reviewer reports on the wrong thing. The Violation this
module's shape prevents is a Leaky Narrative: the skill should say "prepare the checkpoint" and dispatch what comes
back, never assemble paths and line ranges itself (Filter). Dispatching and the digest's wording stay in the skill.

The rules, each with its reason:

- **The number comes from the record** (`checkpoint_number`): 1 plus the `### ` headings under `## Reviews`, so it stays
  right after a resume or on a second machine. A re-run of some areas, or running an area a checkpoint skipped, is a
  checkpoint of its own, `n+1`, so the finding IDs of earlier checkpoints (`F<n>.1` on) never change.
- **A reviewer reads only what the focus touches** (`reviewer_pages`), because each page it reads is paid for again on
  each of its turns: this session's record, every page the session changed, the goals, constraints, context and
  sources pages, the focus pages, and the subject page of each pending copy in its own area. The unknowns page is read
  only above its `## Question ledger` heading (`ledger_limit`): the rows a reviewer needs are already in its area's
  questions file, and the ledger is most of that page. Never an earlier session's record, `voice/` or `handoffs/`:
  what earlier sessions settled is on the pages already.
- **`Changed:` carries line ranges** (`changed_ranges`): a page that existed before the session goes in with the lines
  it changed (`11-unknowns-and-risks.md:40-52+88-90`), a new page whole. A new question is about what this session
  changed; one about a line it left alone was owed when that line was written, and the merge drops it.
- **An area is skipped only when it owes nothing and nothing changed touches it** (`skip_reason`): no pending copy and
  no pending reviewer question in it, and no page this checkpoint reads closely (changed or focus) is the subject page
  of any copy in it. When in doubt it is reviewed. A skipped area is listed with its reason, never silently absent,
  and `--rerun N --areas` runs it later.
- **One checkpoint a session below large** (`session_skip`): one checkpoint covers what changed, so a second `prepare` in
  the same session lists every area as skipped, with the reason, unless the plan's size asks for a review after each
  mode (`Need.REVIEW_EACH_MODE`). `--rerun N --areas` still runs any area, so the lead can always ask. A checkpoint
  counts once it was prepared (its findings folder exists) or merged (its `### ` heading is in the record).
- **The design checkpoint has five fixed reviewers** (`TEAM_AREAS`): a design opens no session record and touches no
  vault page, so it has no catalog areas; its reviewers each take one angle on the design doc.

Pure: pages arrive as the vault model and texts; no disk, git or clock.
"""
import difflib
import re
from dataclasses import dataclass, field

from vela import closegate
from vela.sizing import Need

REVIEWS = "## Reviews"
LEDGER_HEADING = "## Question ledger"
# The pages every checkpoint reads besides what changed: what the plan is for, what limits it, where its edges are, and
# where its facts come from. A reviewer judging any area needs those four to know what counts as a gap.
STANDING_PAGES = ("01-goals.md", "02-constraints.md", "03-context-and-scope.md", "sources.md")
UNKNOWNS_PAGE = "11-unknowns-and-risks.md"
SKIP_PREFIXES = ("sessions/", "voice/", "handoffs/")
DIGEST_SHOWN = "Digest shown:"
_DIGEST_LINE = re.compile(r"^Digest shown:\s*(?P<ids>.*)$")
_CHECKPOINT = re.compile(r"^### (?P<n>\d+)\.")
_TAKEN_ID = re.compile(r"\bQ-[A-Z]{3}-\d{2,}@[\w.-]+\*?|\bR-[A-Z]{3}-\d{2,}\b")

ONE_PER_SESSION = ("this session already had its review checkpoint, and at this plan's size one a session covers "
                   "what changed; --rerun N --areas runs any area anyway")
NOTHING_OWED = "nothing is owed in it and no page this checkpoint changed or focuses on is about a subject it covers"

# REVIEW-CHECKPOINT section 1: the design's five angles. Each asks what the interview cannot surface, because nobody in
# the room knew it: a vendor limit, a license clause, a weekend freeze window.
TEAM_AREAS = (
    ("vendors", "Vendors and integrations",
     "What does each outside service, SDK and partner actually allow: rate limits, sandboxes and their resets, quotas, "
     "terms, what happens when it changes or is down?"),
    ("data", "Data and licensing",
     "What may be stored, cached, shown, shared or used for training, under which license or consent, for how long, "
     "and who may see it?"),
    ("failure", "Failure and recovery",
     "What happens when each dependency is slow, wrong or gone, mid-operation; what is retried, what is lost, what "
     "does the user see, how is it repaired?"),
    ("security", "Security", "Who can do what, how it is proven, where secrets live, what an attacker gains from each "
                             "component."),
    ("operations", "Operations", "How it is deployed, observed, paged, rolled back and paid for; what someone on call "
                                 "needs at 3am?"),
)
# A reviewer that returns more than this buries the few findings that matter; the senior disposes of about four a turn.
TEAM_MAX_FINDINGS = 8
TEAM_FOLDER = "design"


# ------------------------------------------------------------------ the record

def _reviews_span(lines):
    """(start, end) line indexes of the `## Reviews` section's body, or None when the record has none."""
    for i, line in enumerate(lines):
        if line.strip() == REVIEWS:
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
            return i + 1, end
    return None


def checkpoints(record_text):
    """The numbers of the checkpoints the record holds, from its `### <n>.` headings under `## Reviews`."""
    lines = record_text.split("\n")
    span = _reviews_span(lines)
    if span is None:
        return []
    found = (_CHECKPOINT.match(lines[i]) for i in range(*span))
    return [int(m.group("n")) for m in found if m]


def checkpoint_number(record_text):
    """1 plus the number of `### ` headings under `## Reviews`; 1 when the record has no such section."""
    lines = record_text.split("\n")
    span = _reviews_span(lines)
    if span is None:
        return 1
    return 1 + sum(1 for i in range(*span) if lines[i].startswith("### "))


def session_skip(record_text, sized, prepared=0):
    """"" when a checkpoint is due: none has run in this record yet (no `### ` heading under `## Reviews`, and none
    `prepared` whose findings folder exists), or the plan's size asks for a review after each mode. Else why every
    area is skipped."""
    if sized.needs(Need.REVIEW_EACH_MODE):
        return ""
    return ONE_PER_SESSION if prepared or checkpoint_number(record_text) > 1 else ""


def heading(n, checkpoint, today, rerun_of=None, areas=()):
    """The `### ` heading REVIEW section 4 writes for this checkpoint once its merge is in."""
    if rerun_of is not None:
        return f"### {n}. Re-run of checkpoint {rerun_of}: {', '.join(areas)}, {today}"
    return f"### {n}. {checkpoint}, {today}"


def digest_shown(record_text):
    """Every ID the record's `Digest shown:` lines list, in the order first shown. Several lines (two machines each
    wrote one) are read as one."""
    lines = record_text.split("\n")
    span = _reviews_span(lines)
    if span is None:
        return []
    seen = []
    for i in range(*span):
        match = _DIGEST_LINE.match(lines[i].strip())
        if match:
            for ident in (x.strip() for x in match.group("ids").split(",")):
                if ident and ident not in seen:
                    seen.append(ident)
    return seen


def with_digest_shown(record_text, ids):
    """The record with one `Digest shown:` line, the first line under `## Reviews`, listing `ids` after what it already
    listed. Adds `## Reviews` before `## Changes` (or at the end) when the record has none. Every other line stays."""
    shown = digest_shown(record_text)
    shown += [i for i in ids if i not in shown]
    line = f"{DIGEST_SHOWN} {', '.join(shown)}"
    lines = record_text.split("\n")
    span = _reviews_span(lines)
    if span is None:
        at = next((i for i, l in enumerate(lines) if l.strip() == "## Changes"), None)
        if at is None:
            body = record_text.rstrip("\n")
            return f"{body}\n\n{REVIEWS}\n\n{line}\n"
        lines[at:at] = [REVIEWS, "", line, ""]
        return "\n".join(lines)
    start, end = span
    kept = [l for l in lines[start:end] if not _DIGEST_LINE.match(l.strip())]
    while kept and not kept[0].strip():
        kept.pop(0)
    return "\n".join(lines[:start] + ["", line, ""] + kept + lines[end:])


def taken_in_captures(record_text):
    """The copy and reviewer IDs this session's captures name (`Q-FIN-03@SV-01`, `Q-DAT-02@APP-*`, `R-OPS-12`). REVIEW
    section 6 starts a taken line, a ruling-out or a "waits on" group with the IDs it covers, so a named ID has been
    dealt with this session and is not asked again."""
    found = []  # closegate's capture grammar is the one close reads, so the two never drift apart
    for capture in closegate.captures(record_text).values():
        for ident in _TAKEN_ID.findall(capture.words):
            if ident not in found:
                found.append(ident)
    return found


def covered(copy_id, named):
    """True when a named ID covers this copy: the same ID, or a wildcard (`Q-DAT-02@APP-*`) whose prefix it has."""
    return any(copy_id == n or (n.endswith("*") and copy_id.startswith(n[:-1])) for n in named)


# ------------------------------------------------------------------ the pages

def ledger_limit(page_text):
    """The last line a reviewer reads of the unknowns page: the line before `## Question ledger`, or None (read whole)."""
    for n, line in enumerate(page_text.split("\n"), start=1):
        if line.strip() == LEDGER_HEADING:
            return n - 1
    return None


def changed_ranges(before, after):
    """The (first, last) lines of `after` that differ from `before`, 1-based. A hunk that only deletes adds no range."""
    old, new = before.split("\n"), after.split("\n")
    ranges = []
    for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag in ("replace", "insert") and j2 > j1:
            ranges.append((j1 + 1, j2))
    return ranges


def changed_ref(path, ranges):
    """One `--changed` entry: the path, with `:40-52+88-90` when only some lines changed."""
    if not ranges:
        return path
    return path + ":" + "+".join(f"{a}-{b}" for a, b in ranges)


def reviewed_changes(changes, now, record_path):
    """{path: ranges or None (whole page)} for the pages this session changed that a reviewer may read. `changes` maps
    each changed vault page to its text before (None when new); `now` maps a path to its text now. A deleted page,
    another session's record, `voice/` and `handoffs/` are left out. The record is always in, whole."""
    out = {record_path: None}
    for path in sorted(changes):
        if path == record_path or path not in now or path.startswith(SKIP_PREFIXES):
            continue
        before = changes[path]
        if before is None:
            out[path] = None
            continue
        ranges = changed_ranges(before, now[path])
        out[path] = ranges or None
    return out


def changed_arg(changed):
    """The `Changed:` list the reviewers get and `vela findings merge --changed` takes, comma-separated."""
    return ",".join(changed_ref(p, r) for p, r in changed.items())


def reviewer_pages(base, subject_pages, ledger_page, limit):
    """The page list for one reviewer, in order and without repeats; the unknowns page carries its line range."""
    out = []
    for path in list(base) + list(subject_pages):
        if not path or path in out:
            continue
        out.append(path)
    return [f"{p}, lines 1 to {limit}" if p == ledger_page and limit else p for p in out]


def base_pages(record_path, changed, standing, focus):
    """What every area's reviewer reads: the record, the changed pages, the standing pages that exist, the focus."""
    return [record_path] + [p for p in changed if p != record_path] + list(standing) + list(focus)


# ------------------------------------------------------------------ the areas

def skip_reason(area_answer, close_pages):
    """Why an area is skipped, or "" when it is reviewed. `area_answer` is `questions.listing` for the area."""
    pending = [c for c in area_answer["copies"] if c["pending"]] + [r for r in area_answer["reviewer"] if r["pending"]]
    if pending:
        return ""
    touched = {c["subject_page"] for c in area_answer["copies"] if c["subject_page"]} & set(close_pages)
    return "" if touched else NOTHING_OWED


def pending_subject_pages(area_answer):
    """The subject page of each pending copy in the area, in the listing's order."""
    out = []
    for copy in area_answer["copies"]:
        if copy["pending"] and copy["subject_page"] and copy["subject_page"] not in out:
            out.append(copy["subject_page"])
    return out


@dataclass(frozen=True)
class Packet:
    area: str
    label: str
    pages: tuple
    packet: str  # vault-relative path of the dispatch text
    questions_file: str  # "" for the design's reviewers
    findings_file: str
    text: str

    def as_json(self):
        return {"area": self.area, "label": self.label, "pages": list(self.pages), "packet": self.packet,
                "questions_file": self.questions_file or None, "findings_file": self.findings_file}


@dataclass(frozen=True)
class Skipped:
    area: str
    label: str
    reason: str

    def as_json(self):
        return {"area": self.area, "label": self.label, "reason": self.reason}


@dataclass
class Prep:
    n: object  # the checkpoint number; None for the design checkpoint
    heading: str
    folder: str
    findings_folder: str
    changed: str
    packets: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    rerun_of: object = None

    @property
    def first_finding(self):
        return f"F{self.n}.1" if self.n is not None else None

    def merge_command(self):
        if self.n is None:
            return None
        ran = ",".join(p.area for p in self.packets)
        cmd = f"vela findings merge {self.findings_folder} --changed {self.changed}"
        if self.rerun_of is not None or self.skipped:
            cmd += f" --areas {ran}"
        if self.skipped:
            cmd += f" --skipped {','.join(s.area for s in self.skipped)}"
        return cmd

    def as_json(self):
        return {"checkpoint": self.n, "heading": self.heading, "rerun_of": self.rerun_of, "folder": self.folder,
                "findings_folder": self.findings_folder, "first_finding": self.first_finding,
                "changed": self.changed, "merge": self.merge_command(),
                "packets": [p.as_json() for p in self.packets], "skipped": [s.as_json() for s in self.skipped]}


def area_packet_text(code, label, checkpoint, pages, changed, questions_file, findings_file, record_path):
    return "\n".join([
        f"Focus area: {code} {label}",
        f"Checkpoint: {checkpoint}",
        "Pages:",
        *[f"- {p}" for p in pages],
        f"Changed: {changed}",
        f"Questions file: {questions_file}",
        f"Skip the {REVIEWS} section of {record_path}: it holds earlier findings.",
        f"Return one JSON object, which is saved to {findings_file}.",
        "",
    ])


def team_packet_text(label, asks, checkpoint, pages, findings_file):
    return "\n".join([
        f"Focus area: {label}",
        f"Asks: {asks}",
        f"Checkpoint: {checkpoint}",
        "Pages:",
        *[f"- {p}" for p in pages],
        f"Return at most {TEAM_MAX_FINDINGS} findings, each with: the area, a severity (high, medium, low), the design "
        "text it rests on quoted exactly with its section, what goes wrong in one concrete scenario, and the question "
        "the design must answer. If you find nothing, say so.",
        f"Your reply is saved to {findings_file}.",
        "",
    ])


def team_prep(checkpoint, focus, today):
    """The design checkpoint: five packets over the focus pages, no numbering (a design has no session record)."""
    folder = f".vela/review/{TEAM_FOLDER}"
    findings = f".vela/findings/{TEAM_FOLDER}"
    prep = Prep(None, f"{checkpoint}, {today}", folder, findings, "")
    for code, label, asks in TEAM_AREAS:
        out = f"{findings}/{code}.json"
        prep.packets.append(Packet(code, label, tuple(focus), f"{folder}/{code}.md", "", out,
                                   team_packet_text(label, asks, checkpoint, focus, out)))
    return prep
