"""The viewer's reading order for a page: what is true now first, its history folded at the end. Pure: text in, text out.

The files keep their IDs, fact bullets and history where `planner check` reads them. A reader wants none of that up
top. So, for display only:
- history bullets (Decision, Override, Decided by, Confirmed by, Options considered, Dissent), and the page's own
  "## History" section, move into one folded "History" at the end, grouped by the item they belong to;
- generated blocks move after the page's own text, each under a plain heading, with no box and no banner;
- an item heading shows its name without its ID, and a link labeled with a bare ID shows the name it points at;
- a bracket of citations in prose, such as "(SRC-02; [[x|First instruments]], decided)", becomes a small superscript
  of links, so the sentence reads on.

It runs after viewer.neutralize, so the only raw HTML it adds is its own fixed tags.
"""
import re

from planner import schema
from planner.parse import FENCE, closes_fence

HISTORY_BULLET = re.compile(r"^\s*-\s+\*\*(" + "|".join(re.escape(label) for label in schema.HISTORY_LABELS)
                            + r"):\*\*", re.I)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
GEN_OPEN = re.compile(r"^\s*<!--\s*generated:([a-z0-9-]+)[^>]*-->\s*$")
GEN_CLOSE = re.compile(r"^\s*<!--\s*/generated:[a-z0-9-]+\s*-->\s*$")
ID = r"(?:[A-Z][A-Z0-9]*-\d+(?:\.FR\d+)?|G\d+)"
ID_ONLY = re.compile(rf"^\s*{ID}\s*$")
LEADING_ID = re.compile(rf"^{ID}\s+")
LINK = re.compile(r"\[\[([^\]|#]*)(#[^\]|]*)?\|([^\]]*)\]\]")
WIKI = re.compile(r"\[\[[^\]]+\]\]")
SOURCE = re.compile(r"\bSRC-\d+\b")
TRACE_LINE = re.compile(r"^(?P<indent>\s*)[-*]\s+(?:\*\*Trace:\*\*|Trace:)\s*(?P<ids>.*?)\s*$")
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


CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
BARE_LINK = re.compile(r"\[\[([^\]|#]*)#([^\]|]+)\]\]")


def tidy(line):
    """Friendly link labels and folded citations, outside code spans only: a rewrite that crossed a code span could
    move text out of it, and the code span is what kept that text from being read as HTML."""
    pieces, last = [], 0
    for span in CODE_SPAN.finditer(line):
        pieces.append(tidy_prose(line[last:span.start()], line))
        pieces.append(span.group(0))
        last = span.end()
    pieces.append(tidy_prose(line[last:], line))
    return "".join(pieces)


def tidy_prose(text, whole):
    text = BARE_LINK.sub(lambda m: f"[[{m.group(1)}#{m.group(2)}|{LEADING_ID.sub('', m.group(2)).strip() or m.group(2)}]]"
                         if re.match(ID, m.group(2)) else m.group(0), text)
    text = LINK.sub(friendly_label, text)
    if not whole.lstrip().startswith(("|", "-", "*", "#", ">")):
        text = CITATION.sub(citation_sup, text)
    return text


# Sections that are a record, not the current state: they fold like History, in place.
FOLDED_SECTIONS = ("Question ledger", "Also open")  # "Also open (7)": the few that matter sit above it


def is_folded(title):
    title = title.strip()
    return any(title == name or title.startswith(name + " (") for name in FOLDED_SECTIONS)


def fold_records(lines):
    out, inside = [], False
    for line in lines:
        heading = HEADING.match(line)
        if heading and len(heading.group(1)) <= 2:
            if inside:
                out += ["", "</details>", ""]
                inside = False
            if is_folded(heading.group(2)):
                out += ["", f"<details><summary>{heading.group(2).strip()}</summary>", ""]
                inside = True
                continue
        out.append(line)
    if inside:
        out += ["", "</details>"]
    return out


def fold_item_details(lines):
    """Under an item heading that opens with prose, its run of bullets folds into "Details": the sentence says what
    the item is, and the fact bullets are there for whoever wants them. An item with no prose keeps its bullets
    open, so nothing goes missing."""
    out, in_item, said, run = [], False, False, []

    def flush():
        nonlocal run
        if run and in_item and said:
            out.extend(["", "<details><summary>Details</summary>", ""] + run + ["", "</details>", ""])
        else:
            out.extend(run)
        run = []

    for line in lines:
        heading = HEADING.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            if level <= 3:
                in_item, said = level == 3, False
            out.append(line)
            continue
        stripped = line.strip()
        if TRACE_LINE.match(line) and not run:
            out.append(line)  # a Trace line under a numbered criterion stays beside it, not in Details
            continue
        if stripped.startswith(("- ", "* ")) or (run and stripped and line[:1] in " \t"):
            run.append(line)
            continue
        if run and not stripped:
            run.append(line)
            continue
        flush()
        if in_item and stripped and not stripped.startswith(("|", "<")):
            said = True
        out.append(line)
    flush()
    return out


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
    owner, in_fence, in_history, block, moving = "", None, False, None, False
    for line in lines:
        if moving and line.strip() and line[:1] in " \t" and not in_history:
            history.setdefault(owner, []).append(line.rstrip())  # a line nested under a moved history bullet
            continue
        moving = False
        if in_fence:
            (block if block is not None else history.setdefault(owner, []) if in_history else body).append(line)
            if closes_fence(line, in_fence):
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
            if re.fullmatch(ID, first) and (level == 3 or (level == 4 and in_history)):
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
            moving = True
            continue
        body.append(tidy(line))
    out = "\n".join(fold_records(fold_item_details(drop_empty_sections(body)))).rstrip("\n")
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


TEMPLATE_TYPES = ("initiative-section", "index", "concern")  # the kinds of page the template writes before anyone else


def not_started(markdown, page_type="", state=""):
    """True when a page the template made holds only what the template wrote: headings, a table header, and at most
    one line of description. A bullet, a table row, a second line of prose or a diagram means someone has written in
    it, and generated blocks are not the page's own words. A page of another kind, such as a capability or a voice
    example, or one past inkling, is never hidden: a single line there is someone's writing."""
    if page_type not in TEMPLATE_TYPES or state not in ("", "inkling"):
        return False
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
# The vault's own ID kinds, so ISO-8601, UTF-8 or SHA-256 in a sentence is not taken for one.
VAULT_ID = (r"(?:(?:APP|RUN|CAP|FLO|EPC|ADR|CON|UNK|PTY|SV|SRC|CST|INI)-\d+(?:\.FR\d+)?|R-\d+|R-[A-Z]{3}-\d+"
            r"|Q-[A-Z]{3}-\d+(?:@\S+)?)")
BARE_ID = re.compile(rf"(?<![\w-]){VAULT_ID}(?![\w-])")
BREADCRUMB = re.compile(r"^\s*(?:\[\[[^\]]+\]\]\s*/\s*)+[^/]*$")


def visible(line):
    """A prose line as a reader sees it: code and URLs dropped, a link shown as its label, or as its anchor when it
    has no label, which is what the viewer shows."""
    line = re.sub(r"`[^`]*`", "", line)
    line = re.sub(r"https?://\S+", "", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
    return re.sub(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]",
                  lambda m: m.group(3) if m.group(3) is not None else (m.group(2) or m.group(1)), line)


LABELED = re.compile(r"^\s*[-*]\s+\*\*([^*]+?):\*\*")
ASIDE = re.compile(r"\(([^()]*\b(?:no source|fact|assumption|inkling|decided|SRC-\d+|says|said)\b[^()]*)\)", re.I)
ID_LABEL = re.compile(rf"\[\[[^\]|]*\|\s*{VAULT_ID}\s*\]\]")


def lint_words(text):
    """The entries of plugin/references/lint-words.txt: one word or phrase a line, # starts a comment."""
    return [line.strip() for line in text.split("\n") if line.strip() and not line.lstrip().startswith("#")]


def lint_pattern(entry):
    """A whole word with its endings (s, es, d, ed, ing), or a phrase as written; case does not matter."""
    words = entry.lower().replace("\u2019", "'").split()
    if len(words) > 1:
        return re.compile(r"(?<![\w'])" + r"\s+".join(re.escape(w) for w in words) + r"(?![\w'])", re.I)
    stem = re.escape(words[0])
    clipped = re.escape(words[0][:-1]) if words[0].endswith("e") else stem
    return re.compile(rf"(?<![\w'])(?:{stem}(?:s|es|d|ed|ing)?|{clipped}ing)(?![\w'])", re.I)


def style_problems(markdown, page_type, known_labels=(), lint=()):
    """(line, problem) for each place a page reads as a list or a log rather than a document. Read by `planner
    style`. `known_labels` are the fact-bullet labels `planner check` reads; any other bold label is prose dressed up
    as data. `lint` is the word list, as lint_words reads it: each word on the page is one problem, with the count."""
    known = {label.lower() for label in known_labels}
    patterns, hits = {entry: lint_pattern(entry) for entry in lint}, {}
    problems, in_fence, in_gen, in_history, seen_h2, opening = [], None, False, False, False, 0
    item_line, item_said = 0, True
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
            if item_line and not item_said:
                problems.append((item_line, "this item has only bullets; open it with a sentence or two that say "
                                            "what it is now"))
            item_line, item_said = 0, True
            if len(heading.group(1)) == 2:
                seen_h2 = True
                in_history = heading.group(2).strip().lower() == schema.HISTORY_HEADING.lower()
            words = heading.group(2).split()
            if len(heading.group(1)) == 3 and words and re.fullmatch(VAULT_ID, words[0]) and not in_history:
                item_line, item_said = n, False
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if ID_LABEL.search(line) and not in_history:
            problems.append((n, f"a link shows the code {ID_LABEL.search(line).group(0).split('|')[-1].rstrip(']')}; "
                                "show the name of what it links to instead"))
        labeled = LABELED.match(line)
        if item_line and not item_said and not stripped.startswith(("-", "*", "|")):
            item_said = True
        if labeled and not HISTORY_BULLET.match(line) and labeled.group(1).strip().lower() not in known and not in_history:
            problems.append((n, f"'{labeled.group(1).strip()}' is not a fact bullet planner check reads; write it as "
                                "prose"))
            continue
        if HISTORY_BULLET.match(line) and not in_history:
            problems.append((n, f"{HISTORY_BULLET.match(line).group(1)} bullet sits above ## History; move it there"))
            continue
        listed = (stripped.startswith(("-", "*")) or re.match(r"\d+\.", stripped)) and not labeled
        if listed and not in_history and not TRACE_LINE.match(line) and BARE_ID.search(visible(stripped)):
            problems.append((n, f"an ID ({BARE_ID.search(visible(stripped)).group(0)}) in a list item; name the thing, "
                                "and put the ID on a '- Trace:' line under it"))
        prose = not stripped.startswith(("|", "-", "*", ">")) and not re.match(r"\d+\.", stripped) \
            and not BREADCRUMB.match(stripped)
        if prose and not seen_h2:
            opening += 1
        if prose and not in_history:
            for entry, pattern in patterns.items():
                hits.setdefault(entry, []).extend([n] * len(pattern.findall(visible(stripped))))
        if prose and not in_history and ASIDE.search(stripped):
            problems.append((n, f"a bracketed aside, ({ASIDE.search(stripped).group(1)[:40]}); say it in the sentence, "
                                "as \"the product lead says\" or a link on the words"))
        if prose and not in_history:
            if re.search(r"\(\s*SRC-\d+", stripped) or re.search(r"\bSRC-\d+\b", visible(stripped)):
                problems.append((n, "a bare source ID in prose; put the link on the words that rely on it"))
            elif BARE_ID.search(visible(stripped)):
                problems.append((n, f"an ID ({BARE_ID.search(visible(stripped)).group(0)}) in prose; name the thing, "
                                    "link the name, and put the ID on a '- Trace:' line"))
    if item_line and not item_said:
        problems.append((item_line, "this item has only bullets; open it with a sentence or two that say what it is now"))
    for entry, lines in hits.items():
        if lines:
            times = f"{len(lines)} times" if len(lines) > 1 else "once"
            problems.append((lines[0], f"'{entry}' is on the list of words to avoid and appears {times} on this page; say what the thing "
                                       "does in plain words"))
    if page_type in PROSE_PAGE_TYPES and opening == 0:
        problems.append((1, "no opening prose: the page should say in a paragraph or two what is true now"))
    return problems
