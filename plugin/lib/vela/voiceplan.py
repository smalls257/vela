"""The voice examples' rules, as code: which examples a draft reads and in what order, which retire when one is added,
the exact file a save writes, and how harvest tells the owner's edits from the tool's (overhaul Task 18). Pure.

The Violation this shape prevents is Forensic Coding by hand: voice-seed's retire plan, its verbatim write and `cmp`,
and close's harvest (about 90% git and file handling) were prose a model followed step by step, and a model doing them
by hand drops a byte or retires the wrong seed. Each rule below keeps its reason (Anchor), and none reaches a disk,
git, `gh` or a clock: `edge/voicegit.py` reads, `commands/voice.py` decides when.

The rules, with why (from house-voice, voice-seed and CONVENTIONS "Voice examples"):

- **Reading order** (`reading_order`): active examples only; local `owner` and `owner-edit` first, then
  `voice/examples/`, then any other local example, each in file-name order. Fixed so two drafts of one page start
  from the same context, and so on the owner's machine their own words lead.
- **Page type to voice type** (`PAGE_VOICE`): a page's key is its `id` when the table lists it, its `type` otherwise.
  `structured` pages hold no voiced prose.
- **Seed retirement is folder-local** (`plan`): a `public-seed` retires once its own folder holds at least 2 active
  `owner`/`owner-edit` examples of the type after the save. A local example never retires a committed seed: that
  would drop every teammate's house voice below 2 examples of the type. No yes is asked for it; it is the rule.
- **The cap of 5** counts both folders together. The surplus retires `public-seed` first, then `owner-edit`, then
  `owner`, oldest `added` first and then file name; in a local-only save only local examples may retire. The owner may
  refuse a cap retirement, so it needs their yes. When nothing may retire, the save is blocked and nothing is stored.
- **Numbering** (`next_id`): one higher than the highest number of the type in both folders, retired files included,
  so a retired file's ID is never reused.
- **The file** (`file_text`, `stored_body`): frontmatter, one blank line, then the passage byte for byte. The store
  must equal the passage, and a difference stops the save; the file is never repaired by hand.
- **Retiring** (`retired`) changes only the frontmatter's `state:` line. Nothing is deleted: a seed's license and
  attribution stay in its file.
- **Harvest** (`is_tool_commit`, `paragraph_span`, `added_hunks`, `harvest_hash`): the skill's own commits (`draft: `,
  `Checkpoint `, `Close session `, or a Claude trailer) are never the owner's edits. A paragraph is the blank-line
  block holding the added lines, and its hash is the first 12 characters of the SHA-1 of the paragraph as `sed -n`
  prints it, the hash CONVENTIONS "Sessions" puts on a decline line.
"""
import hashlib
import re
from dataclasses import dataclass, field

from vela import privaterecord

VOICE_TYPES = ("diagnosis", "decision", "how-it-works", "conversation")
PAGE_TYPES = ("diagnosis", "decision", "how-it-works")
STRUCTURED = "structured"
FOLDERS = {"committed": "voice/examples", "local": "voice/local"}
CAP = 5  # most active examples a type holds, both folders together
SEED_RETIRES_AT = 2  # owner examples in one folder that retire that folder's public seed
OWNER_SOURCES = ("owner", "owner-edit")
RETIRE_ORDER = ("public-seed", "owner-edit", "owner")
WORDS_LOW, WORDS_HIGH = 80, 300  # voice-seed's "about 80 to 300 words"; conversation exchanges skip the note

# house-voice's table. A page's key is its id when listed here, else its type.
PAGE_VOICE = {
    "goals": "diagnosis", "solution-strategy": "decision", "capability-delta": "decision",
    "context-and-scope": "how-it-works", "constraints": STRUCTURED, "glossary": STRUCTURED,
    "initiative-section": "how-it-works", "index": STRUCTURED, "sources": STRUCTURED, "session": STRUCTURED,
    "app-building-blocks": "how-it-works", "app-runtime": "how-it-works", "flow": "how-it-works",
    "concern": "how-it-works", "decision": "decision", "epic": "how-it-works", "capability": "how-it-works",
    "entity": STRUCTURED, "slice": "how-it-works",
}

_NUMBER = re.compile(r"^VX-(?P<type>[\w-]+?)-(?P<n>\d+)\.md$")
_STATE = re.compile(r"^state:.*$")
TOOL_HEADLINES = ("draft: ", "Checkpoint ", "Close session ")
_TRAILER = re.compile(r"^(?:Co-Authored-By:\s*Claude\b|Claude-Session:)", re.I | re.M)
_HUNK = re.compile(r"^@@ -(?P<old>\d+)(?:,(?P<old_n>\d+))? \+(?P<new>\d+)(?:,(?P<new_n>\d+))? @@")
# Lines that start a block house-voice never voices: headings, tables, generated blocks, code, lists and quotes.
UNVOICED_STARTS = ("#", "|", "<!--", "```", "- ", "* ", "> ")
DECLINE = privaterecord.DECLINE


@dataclass(frozen=True)
class Example:
    path: str  # relative to the vault root
    place: str  # "committed" or "local"
    name: str  # file name
    meta: dict = field(default_factory=dict)
    body: str = ""

    @property
    def id(self):
        return str(self.meta.get("id") or self.name[:-3])

    @property
    def voice_type(self):
        return str(self.meta.get("voice_type", ""))

    @property
    def source(self):
        return str(self.meta.get("source", ""))

    @property
    def active(self):
        return str(self.meta.get("state", "")) == "active"

    @property
    def added(self):
        return str(self.meta.get("added", ""))

    @property
    def is_owner(self):
        return self.source in OWNER_SOURCES

    def as_json(self):
        return {"id": self.id, "path": self.path, "place": self.place, "source": self.source, "added": self.added}


def voice_type_of(meta):
    """The voice type for a page's frontmatter, STRUCTURED, or None when house-voice's table does not list it."""
    key = str(meta.get("id", ""))
    if key in PAGE_VOICE:
        return PAGE_VOICE[key]
    return PAGE_VOICE.get(str(meta.get("type", "")))


def of_type(examples, voice_type):
    return [e for e in examples if e.voice_type == voice_type]


def reading_order(examples, voice_type):
    """The active examples of a type in house-voice's fixed order (see the module docstring)."""
    active = sorted((e for e in of_type(examples, voice_type) if e.active), key=lambda e: e.name)
    local_owner = [e for e in active if e.place == "local" and e.is_owner]
    committed = [e for e in active if e.place == "committed"]
    other_local = [e for e in active if e.place == "local" and not e.is_owner]
    return local_owner + committed + other_local


def next_id(examples, voice_type):
    """`VX-<type>-NNN`, one past the highest number of the type in both folders, retired files included."""
    numbers = [int(m.group("n")) for m in (_NUMBER.match(e.name) for e in examples)
               if m and m.group("type") == voice_type]
    return f"VX-{voice_type}-{max(numbers, default=0) + 1:03d}"


@dataclass
class Plan:
    voice_type: str
    place: str
    adding: int
    seed_retires: list  # retire by the folder rule; no question
    cap_retires: list  # the cap forces these; the owner must say yes
    blocked: bool = False
    reason: str = ""

    @property
    def retires(self):
        return self.seed_retires + self.cap_retires

    def as_json(self):
        return {"voice_type": self.voice_type, "place": self.place, "adding": self.adding,
                "retires": [dict(e.as_json(), why="cap") for e in self.cap_retires]
                + [dict(e.as_json(), why="seed") for e in self.seed_retires],
                "seed_retires": [e.id for e in self.seed_retires], "cap_retires": [e.id for e in self.cap_retires],
                "blocked": self.blocked, "reason": self.reason}


def _retire_key(example):
    return RETIRE_ORDER.index(example.source) if example.source in RETIRE_ORDER else len(RETIRE_ORDER), \
        example.added, example.name


def plan(examples, voice_type, place, adding=1, source="owner"):
    """What retires when `adding` examples of `source` are stored in `place` (see the module docstring)."""
    active = [e for e in of_type(examples, voice_type) if e.active]
    owners_here = sum(1 for e in active if e.place == place and e.is_owner) + (adding if source in OWNER_SOURCES else 0)
    seed = [e for e in active if e.place == place and e.source == "public-seed"] \
        if owners_here >= SEED_RETIRES_AT else []
    staying = [e for e in active if e not in seed]
    surplus = len(staying) + adding - CAP
    result = Plan(voice_type, place, adding, sorted(seed, key=lambda e: e.name), [])
    if surplus <= 0:
        return result
    may_retire = sorted((e for e in staying if place == "committed" or e.place == "local"), key=_retire_key)
    if len(may_retire) < surplus:
        result.blocked = True
        folder = FOLDERS["local"] + "/" if place == "local" else "either folder"
        result.reason = (f"The cap blocks a {'local' if place == 'local' else 'committed'} save: {voice_type} holds "
                         f"{len(staying)} active examples and none in {folder} may retire.")
        return result
    result.cap_retires = may_retire[:surplus]
    return result


def frontmatter(fields):
    """The frontmatter block for an owner or owner-edit example, ending with `---` and one blank line. Free values
    are single-quoted with `'` doubled, so YAML reads back exactly what was given."""
    lines = ["---"]
    for key, value in fields:
        lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n---\n\n"


def quoted(text):
    return "'" + str(text).replace("'", "''") + "'"


def example_fields(ident, voice_type, author, today, where=None, page=None, harvested_from=None):
    """The ordered frontmatter fields: `from` for an owner passage; `page` and `harvested_from` for a harvested one."""
    source = "owner-edit" if page is not None else "owner"
    fields = [("id", ident), ("voice_type", voice_type), ("source", source), ("author", f'"@{author.lstrip("@")}"')]
    if source == "owner":
        fields.append(("from", quoted(where or "")))
    else:
        fields += [("page", quoted(page)), ("harvested_from", quoted(harvested_from))]
    return fields + [("state", "active"), ("added", today)]


def file_text(fields, body):
    return frontmatter(fields) + body


def stored_body(text):
    """Everything after the frontmatter's closing `---` line and its one blank line, byte for byte (WRITE.md's awk,
    without the newline awk adds)."""
    lines = text.splitlines(keepends=True)
    fences = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == "---"][:2]
    if len(fences) < 2:
        return None
    rest = lines[fences[1] + 1:]
    if rest and rest[0] in ("\n", "\r\n"):
        rest = rest[1:]
    return "".join(rest)


def body_notes(body, voice_type):
    """What the owner is told before a passage is stored: a line that is exactly `---` or holds `<!-- generated:`
    (tools may take it for a boundary or a generated block), a word count outside 80 to 300 (page types only), and a
    missing final newline. Notes, not refusals: the owner already said yes to storing the text as it is."""
    notes = []
    for number, line in enumerate(body.splitlines(), 1):
        if line.strip() == "---":
            notes.append(f"line {number} is exactly ---, which tools may read as a frontmatter boundary")
        if "<!-- generated:" in line:
            notes.append(f"line {number} holds <!-- generated:, which tools may read as a generated block")
    words = len(body.split())
    if voice_type != "conversation" and words < WORDS_LOW:
        notes.append(f"{words} words, under {WORDS_LOW}")
    elif voice_type != "conversation" and words > WORDS_HIGH:
        notes.append(f"{words} words, over {WORDS_HIGH}")
    if body and not body.endswith("\n"):
        notes.append("the passage has no final newline; it is stored as given")
    return notes


def retired(text):
    """`text` with only its frontmatter `state:` line set to `retired`."""
    lines = text.splitlines(keepends=True)
    fences = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == "---"][:2]
    end = fences[1] if len(fences) == 2 else 0
    for i in range(1, end):
        if _STATE.match(lines[i].rstrip("\r\n")):
            ending = lines[i][len(lines[i].rstrip("\r\n")):]
            lines[i] = "state: retired" + ending
            return "".join(lines)
    raise ValueError("the example has no state: line in its frontmatter")


def owner_handles(examples):
    """The vault's owner: the authors of `owner` examples in either folder, without the `@`."""
    return sorted({str(e.meta.get("author", "")).strip().lstrip("@") for e in examples if e.source == "owner"} - {""})


def is_tool_commit(headline, body):
    """The skill's own commits, which are never the owner's edits: a `draft: `, `Checkpoint ` or `Close session `
    headline, or a `Co-Authored-By: Claude` or `Claude-Session:` trailer."""
    return headline.startswith(TOOL_HEADLINES) or bool(_TRAILER.search(body or ""))


def added_hunks(diff_text):
    """[(old start line, [added lines])] for every hunk of a `git diff -U0` that adds a non-blank line."""
    hunks, current = [], None
    for line in diff_text.splitlines():
        found = _HUNK.match(line)
        if found:
            current = (int(found.group("old")), int(found.group("old_n") or 1), [])
            hunks.append(current)
        elif current is not None and line.startswith("+") and not line.startswith("+++"):
            current[2].append(line[1:])
    return [(old if old_n else old + 1, [a for a in added if a.strip()]) for old, old_n, added in hunks
            if any(a.strip() for a in added)]


def body_start(lines):
    """Index of the first line after the frontmatter (0 when there is none)."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return len(lines)


def paragraph_span(lines, index):
    """(first, last) 0-based indexes of the voiced paragraph holding line `index`, or None for a blank line, the
    frontmatter, or a block house-voice never voices."""
    if index < body_start(lines) or index >= len(lines) or not lines[index].strip():
        return None
    first = index
    while first > body_start(lines) and lines[first - 1].strip():
        first -= 1
    last = index
    while last + 1 < len(lines) and lines[last + 1].strip():
        last += 1
    if lines[first].lstrip().startswith(UNVOICED_STARTS):
        return None
    return first, last


def find_line(lines, text, near):
    """The index of the line equal to `text` nearest to `near`, or None when no line is (a later commit removed it)."""
    hits = [i for i, line in enumerate(lines) if line == text]
    return min(hits, key=lambda i: abs(i - near)) if hits else None


def paragraph_text(lines, span):
    """A paragraph as `sed -n 'first,lastp'` prints it: each line with its newline."""
    return "".join(line + "\n" for line in lines[span[0]:span[1] + 1])


def harvest_hash(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def decline_line(pr, page, digest):
    return f"Harvest declined: PR {pr} {page} {digest}"


def declined(metas):
    """{(pr, page, hash)} of every decline listed in the records' frontmatter (`harvest_declined:`)."""
    found = set()
    for meta in metas:
        for entry in privaterecord.listed(meta, "harvest_declined"):
            match = DECLINE.match(privaterecord.DECLINE_PREFIX + entry)
            if match:
                found.add((int(match["pr"]), match["page"], match["hash"]))
    return found


def with_decline(record_text, line):
    """The record with `line` directly under `## Captures`, never a bullet; None when it has no `## Captures`."""
    lines = record_text.split("\n")
    for i, text in enumerate(lines):
        if text.strip() == "## Captures":
            return "\n".join(lines[:i + 1] + [line] + lines[i + 1:])
    return None


def already_saved(examples, page, baseline, merged):
    """True when an example in either folder holds this paragraph from this draft: same page, same draft commit,
    same body."""
    return any(str(e.meta.get("page", "")) == page and str(e.meta.get("harvested_from", "")) == baseline
               and e.body == merged for e in examples)
