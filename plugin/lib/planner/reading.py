"""The viewer's reading order for a page: what is true now first, its history folded at the end. Pure: text in, text out.

The files keep their IDs, fact bullets and history where `planner check` reads them. A reader wants none of that up
top. So, for display only:
- history bullets (Decision, Override, Decided by, Confirmed by, Options considered, Dissent), and the page's own
  "## History" section, move into one folded "History" at the end, grouped by the item they belong to;
- generated blocks move after the page's own text, each under a plain heading, with no box and no banner;
- an item heading shows its name without its ID, and a link labelled with a bare ID shows the name it points at;
- a bracket of citations in prose, such as "(SRC-02; [[x|First instruments]], decided)", becomes a small superscript
  of links, so the sentence reads on.

It runs after viewer.neutralise, so the only raw HTML it adds is its own fixed tags.
"""
import re

from planner import schema

HISTORY_BULLET = re.compile(r"^\s*-\s+\*\*(" + "|".join(re.escape(label) for label in schema.HISTORY_LABELS)
                            + r"):\*\*", re.I)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s{0,3}(```|~~~)")
GEN_OPEN = re.compile(r"^\s*<!--\s*generated:([a-z0-9-]+)[^>]*-->\s*$")
GEN_CLOSE = re.compile(r"^\s*<!--\s*/generated:[a-z0-9-]+\s*-->\s*$")
ID = r"(?:[A-Z][A-Z0-9]*-\d+(?:\.FR\d+)?|G\d+)"
ID_ONLY = re.compile(rf"^\s*{ID}\s*$")
LEADING_ID = re.compile(rf"^{ID}\s+")
LINK = re.compile(r"\[\[([^\]|#]*)(#[^\]|]*)?\|([^\]]*)\]\]")
WIKI = re.compile(r"\[\[[^\]]+\]\]")
SOURCE = re.compile(r"\bSRC-\d+\b")
CITATION = re.compile(r"\s*\(([^()]*(?:\bSRC-\d+\b|\[\[)[^()]*)\)")
BLOCK_TITLES = {
    "where-it-stands": "Where it stands", "progress-map": "Progress", "app-context": "Diagram",
    "contracts-consumed": "Contracts it uses", "context-map": "Context map", "concern-matrix": "Concerns by app",
    "traceability": "Traceability", "unknowns-index": "All unknowns", "undisposed-questions": "Questions still owed",
    "capability-map": "Capability map", "flow-index": "Flows", "decision-index": "Decisions",
}


def friendly_label(match):
    """[[page#UNK-027 Brightwater terms|UNK-027]] reads "Brightwater terms"; any other label stays."""
    target, anchor, label = match.group(1), match.group(2) or "", match.group(3)
    if ID_ONLY.match(label) and anchor:
        name = LEADING_ID.sub("", anchor[1:]).strip()
        if name:
            label = name
    return f"[[{target}{anchor}|{label}]]"


def citation_sup(match):
    """A bracket that cites rather than says, kept as small links at the end of its clause."""
    inside = match.group(1)
    links = WIKI.findall(inside)
    rest = WIKI.sub("", SOURCE.sub("", inside))
    if re.search(r"[A-Za-z]{4,}", re.sub(r"\b(decided|assumption|fact|inkling|see|and|or|on|in)\b", "", rest, flags=re.I)):
        return match.group(0)  # the bracket says something of its own, so it stays prose
    sources = ["[[sources|source]]"] * (1 if SOURCE.search(inside) else 0)
    parts = links + sources
    return f"<sup>{', '.join(parts)}</sup>" if parts else ""


def tidy(line):
    line = LINK.sub(friendly_label, line)
    if not line.lstrip().startswith(("|", "-", "*", "#", ">")):
        line = CITATION.sub(citation_sup, line)
    return line


def drop_empty_sections(lines):
    """A heading with nothing under it before the next heading of its level or higher says nothing to a reader."""
    out = []
    for i, line in enumerate(lines):
        heading = HEADING.match(line)
        if heading and len(heading.group(1)) >= 2:
            level = len(heading.group(1))
            rest = lines[i + 1:]
            end = next((j for j, l in enumerate(rest) if HEADING.match(l) and len(HEADING.match(l).group(1)) <= level), len(rest))
            if not any(l.strip() for l in rest[:end]):
                continue
        out.append(line)
    return out


def item_names(lines):
    names = {}
    for line in lines:
        heading = HEADING.match(line)
        if heading:
            words = heading.group(2).split()
            if words and re.fullmatch(ID, words[0]):
                names[words[0]] = " ".join(words[1:]) or words[0]
    return names


def arrange(markdown):
    """The page reordered for reading. Every line of the page is still shown, in one of three places."""
    lines = markdown.split("\n")
    names = item_names(lines)
    body, blocks, history = [], [], {}
    owner, in_fence, in_history, block = "", None, False, None
    for line in lines:
        if in_fence:
            (block if block is not None else history.setdefault(owner, []) if in_history else body).append(line)
            if FENCE.match(line) and FENCE.match(line).group(1) == in_fence:
                in_fence = None
            continue
        if block is not None:
            if GEN_CLOSE.match(line):
                blocks.append(block)
                block = None
            else:
                block.append(line)
                if FENCE.match(line):
                    in_fence = FENCE.match(line).group(1)
            continue
        opened = GEN_OPEN.match(line)
        if opened:
            block = [f"## {BLOCK_TITLES.get(opened.group(1), opened.group(1).replace('-', ' ').capitalize())}", ""]
            continue
        if FENCE.match(line):
            in_fence = FENCE.match(line).group(1)
            (history.setdefault(owner, []) if in_history else body).append(line)
            continue
        heading = HEADING.match(line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2)
            words = text.split()
            first = words[0] if words else ""
            if level <= 2:
                in_history = text.strip().lower() == schema.HISTORY_HEADING.lower()
                owner = ""
                if in_history:
                    continue
            if re.fullmatch(ID, first) and level >= 3:
                owner = first
                if in_history:
                    continue
                line = f"{heading.group(1)} {names.get(first, first)}"
            elif level <= 3 and not in_history:
                owner = ""
        if in_history:
            history.setdefault(owner, []).append(line)
            continue
        if HISTORY_BULLET.match(line):
            history.setdefault(owner, []).append(line.strip())
            continue
        body.append(tidy(line))
    out = "\n".join(drop_empty_sections(body)).rstrip("\n")
    for found in blocks:
        out += "\n\n" + "\n".join(found).rstrip("\n")
    kept = {k: [l for l in v if l.strip()] for k, v in history.items()}
    kept = {k: v for k, v in kept.items() if v}
    if kept:
        out += "\n\n<details><summary>History</summary>\n"
        for key in [""] + [k for k in kept if k]:
            if key not in kept:
                continue
            if key:
                out += f"\n#### {names.get(key, key)}\n"
            out += "\n" + "\n".join(tidy(l) for l in kept[key]) + "\n"
        out += "\n</details>"
    return out + "\n"


def not_started(markdown):
    """True when a page holds only what its template wrote: headings, a table header, and at most one line of
    description. A bullet, a table row, a second line of prose or a diagram means someone has written in it.
    Generated blocks are not the page's own words, so they do not count."""
    rows, prose, in_gen, after_separator = 0, 0, False, False
    for line in markdown.split("\n"):
        stripped = line.strip()
        if GEN_OPEN.match(line):
            in_gen = True
            continue
        if GEN_CLOSE.match(line):
            in_gen = False
            continue
        if in_gen:
            continue
        if stripped.startswith("|"):
            if re.fullmatch(r"\|[-| :]*\|", stripped):
                after_separator = True
            elif after_separator and any(c.strip() and c.strip().lower() != "unexamined"
                                         for c in re.split(r"(?<!\\)\|", stripped.strip("|"))[1:]):
                rows += 1  # a concern row that only says "unexamined" claims nothing
            continue
        after_separator = False
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("-", "*", "```", "~~~")) or re.match(r"\d+\.", stripped):
            return False
        prose += 1
    return rows == 0 and prose <= 1


# ------------------------------------------------------------------ planner style

PROSE_PAGE_TYPES = ("app-building-blocks", "app-runtime", "initiative-section", "capability", "epic", "concern", "flow")
BARE_ID = re.compile(rf"(?<![\w#\[|-]){ID}(?![\w-])")


def visible(line):
    """A prose line as a reader sees it: link targets dropped, labels kept, code spans dropped."""
    line = re.sub(r"`[^`]*`", "", line)
    return re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]|\[\[([^\]]*)\]\]", lambda m: m.group(1) or m.group(2), line)


def style_problems(markdown, page_type):
    """(line, problem) for each place a page reads as a log rather than a document. Read by `planner style`."""
    problems, in_fence, in_gen, in_history, seen_h2, opening = [], None, False, False, False, 0
    for n, line in enumerate(markdown.split("\n"), 1):
        fence = FENCE.match(line)
        if in_fence:
            in_fence = None if fence and fence.group(1) == in_fence else in_fence
            continue
        if fence:
            in_fence = fence.group(1)
            continue
        if GEN_OPEN.match(line):
            in_gen = True
            continue
        if GEN_CLOSE.match(line):
            in_gen = False
            continue
        if in_gen:
            continue
        heading = HEADING.match(line)
        if heading:
            if len(heading.group(1)) == 2:
                seen_h2 = True
                in_history = heading.group(2).strip().lower() == schema.HISTORY_HEADING.lower()
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if HISTORY_BULLET.match(line) and not in_history:
            problems.append((n, f"{HISTORY_BULLET.match(line).group(1)} bullet sits above ## History; move it there"))
            continue
        prose = not stripped.startswith(("|", "-", "*", ">")) and not re.match(r"\d+\.", stripped)
        if prose and not seen_h2:
            opening += 1
        if prose and not in_history:
            if re.search(r"\(\s*SRC-\d+", stripped) or re.search(r"\bSRC-\d+\b", visible(stripped)):
                problems.append((n, "a bare source ID in prose; put the link on the words that rely on it"))
            elif BARE_ID.search(visible(stripped)):
                problems.append((n, f"an ID ({BARE_ID.search(visible(stripped)).group(0)}) in prose; name the thing, "
                                    "and link the name"))
    if page_type in PROSE_PAGE_TYPES and opening == 0:
        problems.append((1, "no opening prose: the page should say in a paragraph or two what is true now"))
    return problems
