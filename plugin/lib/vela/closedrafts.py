"""Which paragraphs a session owes before it closes: the checklist behind `vela close drafts` (overhaul Task 21a). Pure.

The Violation this exists to prevent is a Black Box in close's "Write the items and the prose". That section was a long list the model walked
by memory (changed pages, `query refs` for every resolved or decided ID, Strategy paragraphs, decision records, the
glossary), so nobody could see which paragraph it skipped. Finding the paragraphs is mechanical; writing them isn't
(Filter). So this module finds them, each with the reason it is owed, and the skill drafts every one it is handed.

Sources, each with the reason close's "Write the items and the prose" gives for it:

- **Opening** of every page this session changed, leaving out `sessions/` and `sources.md`: the opening says what is
  true now, and the session may have made it untrue. A page whose only change is inside generated blocks owes
  nothing: that is `vela render`'s churn, not new facts.
- **Sentences that mention an item this session resolved or decided** (`query.refs` for each): a sentence still
  calling an answered question open misleads (W334). A mention inside a generated block (render rewrites it), under
  `## History` (history is never rewritten), in frontmatter, in a session record or in the item's own section owes
  nothing.
- **The `## Strategy` paragraph** of each concern page whose cells changed: the strategy is the prose behind the
  cells, so new cells can leave it saying the old thing.
- **The opening sentence of each `### <ID>` item** the session wrote or changed, before its fact bullets: bullets
  alone are not a sentence a reader can follow.
- **A decision record** for each page made `decided` whose decision shapes the whole design (an initiative section
  such as the solution strategy, an app page, a flow), unless a decision record already links it. Contracts and
  unknowns get no record of their own.
- For a session whose modes include `epics`, **each epic it changed** owes its summary, its `Still open:` line and
  its `## Who this is for and what changes` section, in the template's order, because the PR lists them under
  "Prose drafted".

A paragraph drafted earlier in the session counts as done (Anchor: the house voice is written when an item settles,
not rebuilt at close). It is done unless the facts it stands on changed after its last write: `history` says when each
paragraph was last written and hands back the pages as they stood then, and this module compares the facts then with
the facts now. What is left is either missing (never written this session) or stale (written, then the facts moved);
each entry says which, and for stale what moved.

Alongside the paragraphs:

- **Lists over seven** (plan 2.13): a page section holding more than about seven items or bullets reads as a wall;
  the skill puts the few that matter first and the rest under `## Also open (n)`. Choosing the few stays the skill's.
- **Split facts** (house-voice "Size"): past about 20 paragraphs one PR is hard to review, so the lead is asked
  whether to split by page group. This module counts and groups; the question is the skill's to ask.
- **Glossary** is judgment (which terms a newcomer would not know), so it is a reminder, never a count.
"""
import posixpath
import re
from collections import OrderedDict
from dataclasses import dataclass, field

from vela import closegate, drafts, model, parse, query, schema, sizing, wording

DECIDED, RESOLVED = "decided", "resolved"
LONG_LIST = 7  # "more than about seven" (close's "Write the items and the prose")
SPLIT_AT = 20  # "more than about 20 prose paragraphs" (house-voice "Size")
SKIP_PATHS = ("sources.md",)
SKIP_FOLDERS = ("sessions/",)
ADR_TYPES = ("initiative-section", "app-building-blocks", "app-runtime", "flow")
EPIC_SECTIONS = (("summary", "the epic's summary, first in the template's order"),
                 ("Still open", "the epic's `Still open:` line"),
                 ("Who this is for and what changes", "the epic's `## Who this is for and what changes` section"))
FOLDED = ("history",)
PLAIN_BULLET = re.compile(r"^- (?!\*\*[^*:]+:\*\*)\S")
OPENING = "opening"
MISSING, STALE = "missing", "stale"
SHOWN = 80  # characters of a changed line quoted in a stale reason
NOT_PROSE = re.compile(r"^\s*(?:[-*+] |\d+[.)] |\||#|<!--|\[generated block|```)")
STILL_OPEN = re.compile(r"^Still open:")

JUDGMENT = ("A glossary entry on 12-glossary.md for each term this session used that a newcomer to the initiative "
            "would not know: the term in bold, then what it means here.",)

WHY = {
    "opening": "this session changed the page; its opening must say what is true now",
    "ref": "it mentions {names}, which this session {verbs}; say what is true now",
    "strategy": "this session changed the concern's cells; the Strategy paragraph must still match them",
    "item": "this session wrote or changed the item; open it with a sentence before its bullets",
    "adr": "this session decided the page and it shapes the whole design: start its decision record with vela add "
           "adr --state decided --decision <session id> --capture <the lead's yes, ^cNN> --decides <ID> --title "
           "\"<what was decided>\", then draft its sections",
    "epic": "an epics session owes {what}",
}


@dataclass
class Owed:
    """One paragraph the session owes. `heading` is "opening" for the prose above the first `##`."""
    page: str
    title: str
    heading: str
    kind: str
    whys: list = field(default_factory=list)
    items: list = field(default_factory=list)
    mentions: dict = field(default_factory=dict)  # ID -> what this session did to it, for a sentence that names it
    status: str = MISSING
    moved: str = ""  # for a stale paragraph, what changed after it was written

    @property
    def why(self):
        said = list(self.whys)
        if self.mentions:
            verbs = " or ".join(sorted(set(self.mentions.values())))
            said.insert(0, WHY["ref"].format(names=", ".join(self.mentions), verbs=verbs))
        if self.moved:
            said.append(f"written earlier in this session, but stale since a later change: {self.moved}")
        return "; ".join(said)

    def as_json(self):
        return {"page": self.page, "title": self.title, "heading": self.heading, "kind": self.kind,
                "status": self.status, "why": self.why, "items": self.items}


@dataclass(frozen=True)
class LongList:
    page: str
    title: str
    heading: str
    count: int

    def as_json(self):
        return {"page": self.page, "heading": self.heading, "count": self.count}


@dataclass(frozen=True)
class Split:
    paragraphs: int
    pages: int
    groups: dict  # page group (top folder, or the page at the root) -> paragraphs owed there

    @property
    def question(self):
        return (f"{self.paragraphs} paragraphs changed, which is a lot to review at once. I'd send them in "
                f"{len(self.groups)} parts, one for each part of the plan. OK, or one review?")

    def as_json(self):
        return {"paragraphs": self.paragraphs, "pages": self.pages, "groups": self.groups, "question": self.question}


@dataclass
class Drafts:
    paragraphs: list
    long_lists: list
    split: object  # Split or None
    judgment: tuple = JUDGMENT
    kept: list = field(default_factory=list)  # imported pages that keep the documents' words: owed no voiced prose
    done: list = field(default_factory=list)  # paragraphs written this session whose facts have not moved since

    @property
    def count(self):
        return len(self.paragraphs)


def vault_before(after, changes):
    """The vault as it was: today's pages with each changed one swapped for its old text, and new ones left out.
    `changes` is {path: text before, or None when it is new}, for pages only."""
    pages = [p for p in after.pages if p.path not in changes]
    pages += [parse.parse_page(path, text) for path, text in sorted(changes.items()) if text is not None]
    return model.build(pages, after.config, sorted(after.other_names), after.catalog, after.template_lines)


def owes_prose(path):
    return not path.startswith(SKIP_FOLDERS) and path not in SKIP_PATHS


def heading_before(page, line, deepest=6):
    """The nearest heading at or above `line` whose level is at most `deepest`, or None."""
    found = None
    for heading in page.headings:
        if heading.line > line:
            break
        if heading.level <= deepest:
            found = heading
    return found


def section_name(page, line):
    heading = heading_before(page, line)
    return OPENING if heading is None or heading.level == 1 else heading.text


def in_generated(page, line):
    return any(block.start <= line <= block.end for block in page.blocks)


def item_lines(item):
    """(first, last) line of an item's section: its heading to the line before the next heading of level 3 or above."""
    nxt = next((h.line for h in item.page.headings if h.line > item.line and h.level <= 3), None)
    total = len(parse.lines_of(item.page.text))
    return item.line, (nxt - 1 if nxt else total)


def item_text(item):
    first, last = item_lines(item)
    return "\n".join(parse.lines_of(item.page.text)[first - 1:last]).strip()


def title_of(page):
    title = page.meta.get("title")
    return str(title) if title else page.name


class Ledger:
    """The owed paragraphs, one per (page, heading): a paragraph owed for two reasons is still one paragraph."""

    def __init__(self, vault):
        self.vault, self.found = vault, OrderedDict()

    def entry(self, page, heading, kind, item):
        found = self.found.setdefault((page.path, heading), Owed(page.path, title_of(page), heading, kind))
        if item and item not in found.items:
            found.items.append(item)
        return found

    def owe(self, page, heading, kind, why, item=""):
        entry = self.entry(page, heading, kind, item)
        if why not in entry.whys:
            entry.whys.append(why)

    def owe_mention(self, page, heading, item, verb):
        self.entry(page, heading, "ref", item).mentions[item] = verb

    def all(self):
        return list(self.found.values())


def changed_pages(after, changes):
    return [p for p in after.pages if p.path in changes and owes_prose(p.path) and p.type != "session"]


def only_generated_changed(page, before_text):
    if before_text is None:
        return False
    return drafts.collapse_generated(before_text) == drafts.collapse_generated(page.text)


def owe_openings(ledger, pages, changes):
    for page in pages:
        if not only_generated_changed(page, changes[page.path]):
            ledger.owe(page, OPENING, "opening", WHY["opening"])


def owe_items(ledger, before, after, pages):
    paths = {p.path for p in pages}
    for item_id, items in sorted(after.items.items()):
        item = items[0]
        if item.page.path not in paths:
            continue
        was = before.items.get(item_id)
        if was and item_text(was[0]) == item_text(item):
            continue
        ledger.owe(item.page, item.heading, "item", WHY["item"], item_id)


def moved_to(before_states, after_states, state):
    return sorted(i for i, now in after_states.items() if now == state and before_states.get(i) != state)


def ref_skipped(vault, page, line, via, item_id):
    if page.type == "session" or not owes_prose(page.path) or via in query.LIST_FIELDS or not line:
        return True
    if in_generated(page, line):
        return True
    top = heading_before(page, line, deepest=2)
    if top is not None and top.level == 2 and top.text.strip().lower() in FOLDED:
        return True
    own = vault.item(item_id)
    if own is not None and own.page is page:
        first, last = item_lines(own)
        return first <= line <= last
    return page.id == item_id


def owe_refs(ledger, after, moved):
    """`moved` is [(ID, verb)]: each item resolved or decided this session and what happened to it."""
    by_path = {p.path: p for p in after.pages}
    for item_id, verb in moved:
        for ref in query.refs(after, item_id).get("refs", []):
            page = by_path.get(ref["page"])
            if page is None or ref_skipped(after, page, ref["line"], ref["via"], item_id):
                continue
            ledger.owe_mention(page, section_name(page, ref["line"]), item_id, verb)


def cells_of(vault, concern_path):
    return sorted((c.app, c.state, c.text) for c in vault.cells if c.concern.path == concern_path)


def owe_strategy(ledger, before, after, pages):
    for page in pages:
        if page.type == "concern" and cells_of(before, page.path) != cells_of(after, page.path):
            ledger.owe(page, "Strategy", "strategy", WHY["strategy"])


def decision_targets(vault):
    """Pages a decision record already links, so a decided page that has one owes no new one."""
    linked = set()
    for page in vault.of_type("decision"):
        for link in page.links:
            target = vault.resolve(link, page)
            if target is not None:
                linked.add(target.path)
    return linked


def owe_adrs(ledger, after, decided):
    linked = decision_targets(after)
    for item_id in decided:
        for page in after.by_id.get(item_id, [])[:1]:
            if page.type in ADR_TYPES and page.path not in linked:
                ledger.owe(page, "decision record", "adr", WHY["adr"], item_id)


def owe_epics(ledger, pages, modes):
    if "epics" not in modes:
        return
    for page in pages:
        if page.type == "epic":
            for heading, what in EPIC_SECTIONS:
                ledger.owe(page, heading, "epic", WHY["epic"].format(what=what), page.id)


def list_counts(page, item_sections):
    """{heading: count} of items and plain bullets per section, outside generated blocks and code fences."""
    counts = OrderedDict()
    for heading, n in item_sections.items():
        counts[heading] = counts.get(heading, 0) + n
    fence = None
    for number, raw in enumerate(parse.lines_of(page.text), 1):
        opener = parse.FENCE.match(raw)
        if fence:
            fence = None if parse.closes_fence(raw, fence) else fence
            continue
        if opener:
            fence = opener.group(1)
            continue
        if PLAIN_BULLET.match(raw) and not in_generated(page, number):
            heading = section_name(page, number)
            counts[heading] = counts.get(heading, 0) + 1
    return counts


def long_lists(after, pages):
    out = []
    for page in pages:
        sections = OrderedDict()
        for items in after.items.values():
            if items[0].page is page:
                top = heading_before(page, items[0].line, deepest=2)
                heading = OPENING if top is None or top.level == 1 else top.text
                sections[heading] = sections.get(heading, 0) + 1
        for heading, count in list_counts(page, sections).items():
            folded = heading.lower().startswith("also open") or heading.lower() in FOLDED
            if count > LONG_LIST and not folded:
                out.append(LongList(page.path, title_of(page), heading, count))
    return out


def page_group(path):
    head, _, rest = path.partition("/")
    return head if rest else posixpath.splitext(head)[0]


def split_facts(paragraphs):
    if len(paragraphs) <= SPLIT_AT:
        return None
    groups = OrderedDict()
    for entry in paragraphs:
        group = page_group(entry.page)
        groups[group] = groups.get(group, 0) + 1
    return Split(len(paragraphs), len({p.page for p in paragraphs}), dict(groups))


def section_range(page, heading):
    """(first, last) line of the prose a heading owns: after the page title for "opening", else after the heading to
    the next heading of any level. None when the page has no such heading."""
    heads = page.headings
    if heading == OPENING:
        start = next((h.line for h in heads if h.level == 1), 0)
        stop = next((h.line for h in heads if h.line > start and h.level >= 2), None)
    else:
        found = next((h for h in heads if h.text == heading), None)
        if found is None:
            return None
        start = found.line
        stop = next((h.line for h in heads if h.line > start), None)
    return start + 1, (stop - 1 if stop else len(parse.lines_of(page.text)))


def names_any(line, names):
    low = line.lower()
    return any(name.lower() in low for name in names)


def paragraph(text, heading, names=()):
    """(prose, facts) of a page as tuples of lines. Prose is the paragraph a section's heading owns: plain lines, not
    bullets, table rows, headings or fences, and "Still open:" for the epic line of that name. Facts are every other
    line of the page, so a changed state, bullet or cell shows. A line that names one of `names` (the items a sentence
    mentions) is prose wherever it sits, because a mention in a table row or a bullet is rewritten like a sentence. Generated blocks are collapsed: render's churn is not
    a fact."""
    if text is None:
        return (), ()
    page = parse.parse_page("page.md", "\n".join(drafts.collapse_generated(text)))
    lines = parse.lines_of(page.text)
    if heading == "Still open":
        prose = {n for n, line in enumerate(lines, 1) if STILL_OPEN.match(line)}
    else:
        rng = section_range(page, OPENING if heading == "summary" else heading)
        first, last = rng if rng else (1, 0)
        prose = {n for n in range(first, last + 1) if lines[n - 1].strip() and not STILL_OPEN.match(lines[n - 1])
                 and (not NOT_PROSE.match(lines[n - 1]) or names_any(lines[n - 1], names))}
    return (tuple(lines[n - 1].strip() for n in sorted(prose)),
            tuple(line.strip() for n, line in enumerate(lines, 1) if n not in prose and line.strip()))


def has_section(text, heading):
    """True when the page had a place for this paragraph: the page itself for its opening, else the heading."""
    if text is None:
        return False
    if heading in (OPENING, "summary", "Still open"):
        return True
    page = parse.parse_page("page.md", text)
    return any(h.text == heading for h in page.headings)


def item_facts(text, item_id):
    """The lines of one item's section, or of the whole page when the ID names the page itself."""
    if text is None:
        return ()
    page = parse.parse_page("page.md", "\n".join(drafts.collapse_generated(text)))
    lines = parse.lines_of(page.text)
    heading = next((h for h in page.headings if h.text.startswith(f"{item_id} ")), None)
    if heading is None:
        return tuple(line.strip() for line in lines if line.strip())
    stop = next((h.line for h in page.headings if h.line > heading.line and h.level <= 3), len(lines) + 1)
    return tuple(line.strip() for line in lines[heading.line - 1:stop - 1] if line.strip())


def first_difference(then, now):
    """A short quote of the first line that is in `now` and not in `then`, else of one that went away."""
    gained = next((line for line in now if line not in then), None)
    lost = next((line for line in then if line not in now), None)
    line = gained if gained is not None else lost
    if line is None:
        return "its lines moved"
    quote = line if len(line) <= SHOWN else line[:SHOWN].rstrip() + "..."
    return f"now has \"{quote}\"" if gained is not None else f"no longer has \"{quote}\""


def now_text(vault, path):
    return next((p.text for p in vault.pages if p.path == path), None)


def home_of(vault, item_id):
    """The path of the page an item lives on, or of the page the ID names; None when the vault holds neither."""
    item = vault.item(item_id)
    if item is not None:
        return item.page.path
    pages = vault.by_id.get(item_id)
    return pages[0].path if pages else None


def mention_names(entry, vault):
    return [name for item_id in entry.mentions for name in (item_id, vault.name_of(item_id))]


def moved_since(entry, then, after):
    """What changed under a paragraph after it was written, in words; "" when nothing it stands on moved. The
    paragraph stands on the rest of its page, and a sentence that names a resolved or decided item also on that item."""
    names = mention_names(entry, after)
    facts_then = paragraph(then(entry.page), entry.heading, names)[1]
    facts_now = paragraph(now_text(after, entry.page), entry.heading, names)[1]
    if facts_then != facts_now:
        return f"the page {first_difference(facts_then, facts_now)}"
    for item_id in entry.mentions:
        path = home_of(after, item_id)
        if path is not None and item_facts(then(path), item_id) != item_facts(now_text(after, path), item_id):
            return f"{after.name_of(item_id)} changed"
    return ""


def settle(entries, history, after):
    """Split the ledger into (owed, done). With no `history` (a reader copy runs no git) everything is missing."""
    owing, done = [], []
    for entry in entries:
        then = history.written(entry.page, entry.heading, mention_names(entry, after)) if history and entry.kind != "adr" else None
        entry.status = MISSING
        if then is not None:
            entry.moved = moved_since(entry, then, after)
        if then is None or entry.moved:
            entry.status = MISSING if then is None else STALE
            owing.append(entry)
        else:
            done.append(entry)
    return owing, done


def voice_review(sized, paragraphs):
    """({"due": bool, "why": str}): whether a fresh reader should check the drafts' voice. From the plan's size, never
    from a number in skill prose (Forensic Coding): always from medium, else from `VOICE_REVIEW_MIN_PARAGRAPHS`."""
    if sized.needs(sizing.Need.VOICE_REVIEW_ALWAYS):
        return {"due": True, "why": "this plan's size always sends the drafts to a fresh reader"}
    if paragraphs >= schema.VOICE_REVIEW_MIN_PARAGRAPHS:
        return {"due": True, "why": f"{paragraphs} paragraphs is enough to send to a fresh reader"}
    return {"due": False, "why": f"only {paragraphs} paragraph{'' if paragraphs == 1 else 's'} (a fresh reader comes "
                                 f"from {schema.VOICE_REVIEW_MIN_PARAGRAPHS}), so the lead's own read-back covers it"}


def owed(before, after, changes, modes=(), history=None):
    """Everything close's "Write the items and the prose" needs from the facts: `before` and `after` are vault models, `changes` is
    {page path: text before, or None when new} for every page that differs, `modes` the session record's modes.
    `history.written(page, heading, names)` returns a function path -> the page's text as it stood when that paragraph was
    last written this session, or None when it was not written; None for `history` means nothing was written."""
    pages = changed_pages(after, changes)
    was, now = closegate.states(before), closegate.states(after)
    decided, resolved = moved_to(was, now, DECIDED), moved_to(was, now, RESOLVED)
    ledger = Ledger(after)
    owe_openings(ledger, pages, changes)
    owe_items(ledger, before, after, pages)
    owe_refs(ledger, after, sorted([(i, RESOLVED) for i in resolved] + [(i, DECIDED) for i in decided]))
    owe_strategy(ledger, before, after, pages)
    owe_adrs(ledger, after, decided)
    owe_epics(ledger, pages, tuple(modes))
    # An imported page the lead hasn't had voiced keeps the documents' words: it is never handed to the voice redraft,
    # and it is listed, so the skip is seen (wording.py).
    kept = sorted({p.page for p in ledger.all() if is_kept(after, p.page)})
    entries = sorted([p for p in ledger.all() if p.page not in kept], key=lambda p: p.page)  # stable order
    paragraphs, done = settle(entries, history, after)
    return Drafts(paragraphs, long_lists(after, pages), split_facts(entries), kept=kept, done=done)


def is_kept(vault, path):
    page = next((p for p in vault.pages if p.path == path), None)
    return page is not None and wording.wording_of(page.meta) == wording.KEEP
