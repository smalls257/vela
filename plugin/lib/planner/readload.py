"""Reading load, second half: the shape of a paragraph, a cell, a phrase and an abbreviation.

Pure: a page (or the pages of a vault) in, findings out. W360 to W364 look at codes, lists and length of a page. These
five look at what a reader meets word by word, and none of them shows in one paragraph read alone, which is why the
reviewer cannot be the Sensor for them:

- W365 a paragraph over the word or link limit; a page's opening is held to a tighter limit, because most readers read
  only the first screen.
- W366 a table cell over the word limit: a cell is read as one chunk.
- W367 a three- or four-word phrase repeated across pages (vault-level, reported once with the pages). One clause stamped
  on thirty pages is the loudest tell in the Heron vault, and it comes from a rule applied everywhere.
- W368 the opening is a line the template wrote, so the page still says what a page of its kind is about, not what is
  true now.
- W369 a capitalised abbreviation not spelled out on the page: a definition elsewhere does not undo the cost.

All are warnings. Every limit is in `schema.py`, and each finding carries a plain fix line.
"""
import re
from collections import defaultdict

from planner import schema
from planner.readability import (HEADING, LIST_ITEM, NO_PROSE_TYPES, SUMMARY_MIN_WORDS, _is_prose, _regions,
                                 BARE_VAULT_ID, CODE_SPAN, URL, WIKILINK)
from planner.parse import split_frontmatter
from planner.reading import BREADCRUMB, is_folded, visible

BOLD_LABEL = re.compile(r"^\s*\*\*[^*]+:\*\*")  # "**Domain:** Sell": a label the page carries, not a sentence
MD_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’@-]*")
SPACES = re.compile(r"\s+")
ABBREVIATION = re.compile(r"(?<![\w@./#-])[A-Z]{2,5}(?![\w-])")
SMALL_WORDS = {"of", "the", "and", "for", "to", "a", "an", "in", "on", "or", "by", "with"}


def _readable(page):
    return page.meta and page.type not in NO_PROSE_TYPES


def _link_count(text):
    return len(WIKILINK.findall(text)) + len(MD_LINK.findall(text))


def _word_count(text):
    return len(visible(text).split())


def paragraphs(page):
    """(first line, text, is the opening) for each paragraph of the page's own prose. A list item, a quote, a table
    row, a heading, a fact bullet, a Trace line and History are not paragraphs. The opening is the first paragraph of
    real words before the first `##` heading."""
    out, lines, start, seen_h2, opened = [], [], 0, False, False

    def flush():
        nonlocal lines, opened
        if lines:
            text = " ".join(lines)
            is_opening = not seen_h2 and not opened and _word_count(text) >= SUMMARY_MIN_WORDS
            opened = opened or is_opening
            out.append((start, text, is_opening))
        lines = []

    for n, raw, _, history in _regions(page):
        heading = HEADING.match(raw)
        if heading:
            flush()
            seen_h2 = seen_h2 or len(heading.group(1)) == 2
            continue
        stripped = raw.strip()
        paragraph = (not history and stripped and _is_prose(raw) and not LIST_ITEM.match(raw)
                     and not stripped.startswith(">") and not BREADCRUMB.match(stripped) and not BOLD_LABEL.match(raw))
        if not paragraph:
            flush()
            continue
        if not lines:
            start = n
        lines.append(stripped)
    flush()
    return out


# ---------------------------------------------------------------------------------------------------- W365

def paragraph_findings(page):
    out = []
    for n, text, is_opening in paragraphs(page):
        words, links = _word_count(text), _link_count(text)
        max_words = schema.OPENING_WORD_LIMIT if is_opening else schema.PARAGRAPH_WORD_LIMIT
        max_links = schema.PARAGRAPH_LINK_LIMIT
        if words <= max_words and links <= max_links:
            continue
        where = "The opening" if is_opening else "This paragraph"
        why = f"{words} words" if words > max_words else f"{links} links"
        if words > max_words and links > max_links:
            why = f"{words} words and {links} links"
        fix = ("Say in two or three sentences what is true now and the one thing that holds it up. Name the threads, not "
               "every item, and send the reader to the table or block below for the rest."
               if is_opening else
               "Split at the second topic, or move the pointers to a table under a heading.")
        out.append((n, "W365", f"{where} runs {why}; the limit is {max_words} words and {max_links} links.", fix))
    return out


# ---------------------------------------------------------------------------------------------------- W366

def cell_findings(page):
    record = {n: in_history or is_folded(heading) for n, _, heading, in_history in _regions(page)}
    out = []
    for table in page.tables:
        if table.generated:
            continue
        for row, line in zip(table.rows, table.row_lines):
            if record.get(line, True):
                continue  # History, the question ledger, a fence or a generated block: a record, not read top to bottom
            words = max((_word_count(cell) for cell in row), default=0)
            if words > schema.CELL_WORD_LIMIT:
                out.append((line, "W366", f"A table cell runs {words} words; a cell is read as one chunk, and the limit is "
                            f"{schema.CELL_WORD_LIMIT}.", "One clause per row, or point at the requirement page."))
    return out


# ---------------------------------------------------------------------------------------------------- W368

def normal_line(text):
    return SPACES.sub(" ", text).strip()


def template_lines(markdown):
    """The prose lines a template page writes: no frontmatter, heading, table, list, comment, fence or generated block,
    and at least four words, since a short line is a label."""
    _, body_start, _ = split_frontmatter(markdown)
    lines, fence, generated = [], False, False
    for raw in markdown.replace("\r\n", "\n").split("\n")[body_start - 1:]:
        stripped = raw.strip()
        if stripped.startswith(("```", "~~~")):
            fence = not fence
        elif stripped.startswith("<!-- generated:"):
            generated = True
        elif stripped.startswith("<!-- /generated:"):
            generated = False
        elif not (fence or generated or not stripped or stripped.startswith(("#", "|", "-", "*", ">", "<!--"))):
            if len(stripped.split()) >= 4:
                lines.append(normal_line(stripped))
    return lines


def template_corpus(pages):
    """Every template line W368 knows, in file order. `pages` is (path parts under template/, text) for each file. Only
    the pages that become vault pages count. The shipped list `plugin/catalog/template-lines.txt` is this, written out;
    a test fails when the two differ."""
    found = []
    for parts, text in pages:
        if any(p.startswith(".") for p in parts[:-1]) or parts[0] in ("voice", "sessions") \
                or (len(parts) == 1 and parts[0] in schema.SKIP_FILES + ("README.md",)):
            continue
        found += [line for line in template_lines(text) if line not in found]
    return found


def _untouched(body, known):
    """True when nobody has written in the page: every prose line is one the template wrote, and there is no list item
    and no table row beyond a header."""
    if any(line not in known for line in template_lines(body)):
        return False
    rows, fence = 0, False
    for raw in body.split("\n"):
        stripped = raw.strip()
        if stripped.startswith(("```", "~~~")):
            fence = not fence
        elif fence:
            return False
        elif stripped.startswith(("- ", "* ")) or re.match(r"\d+\.\s", stripped):
            return False
        elif stripped.startswith("|"):
            rows += 1
    return rows <= 2


def template_opening_findings(page, known):
    """W368: a line before the page's first `##` heading that the template wrote and nobody replaced. An index only
    describes its folder, and a page nobody has written in yet is untouched, not one whose summary is a template line."""
    _, body_start, _ = split_frontmatter(page.text)
    body = "\n".join(page.text.split("\n")[body_start - 1:])
    if page.type == "index" or _untouched(body, known):
        return []
    for n, raw, _, history in _regions(page):
        heading = HEADING.match(raw)
        if heading and len(heading.group(1)) == 2:
            return []
        if not history and _is_prose(raw) and normal_line(raw) in known:
            return [(n, "W368", "The opening is a line the template wrote, not what is true now for this initiative.",
                     "Replace it with what is true now for this initiative.")]
    return []


# ---------------------------------------------------------------------------------------------------- W369

def _abbreviation_text(page):
    """(line number, prose with links, code and IDs taken out) for each prose line a reader meets, outside History."""
    for n, raw, _, history in _regions(page):
        if history or not _is_prose(raw):
            continue
        plain = URL.sub(" ", CODE_SPAN.sub(" ", WIKILINK.sub(" ", raw)))
        yield n, BARE_VAULT_ID.sub(" ", plain)


def _initials(words):
    return "".join(w[0].upper() for w in words if w.lower() not in SMALL_WORDS)


def spelled_out(text, found):
    """True when `text` writes the abbreviation's words beside it: 'Data Protection Officer (DPO)' or 'DPO (Data
    Protection Officer)'. The letters must be the words' initials, so a bracket that explains something else does not
    count."""
    letters = found.group(0)
    before = WORD.findall(text[:found.start()].rstrip(" (["))
    if text[:found.start()].rstrip().endswith(("(", "[")):
        take = [w for w in before[-len(letters) - 3:]]
        for size in range(1, len(take) + 1):
            if _initials(take[-size:]) == letters:
                return True
    after = re.match(r"\s*[\(\[,:–—-]\s*([^)\]\n]{3,80})", text[found.end():])
    if after:
        words = WORD.findall(after.group(1))
        for size in range(1, len(words) + 1):
            if _initials(words[:size]) == letters:
                return True
    return False


def abbreviation_findings(page):
    seen, out = set(), []
    allowed = set(schema.ABBREVIATIONS_UNDERSTOOD)
    lines = list(_abbreviation_text(page))
    whole = "\n".join(text for _, text in lines)
    for n, text in lines:
        for found in ABBREVIATION.finditer(text):
            letters = found.group(0)
            if letters in allowed or letters in seen:
                continue
            seen.add(letters)
            if spelled_out(text, found) or _spelled_anywhere(whole, letters):
                continue
            out.append((n, "W369", f"{letters} is used without being spelled out on this page.",
                        f"Write out what {letters} stands for at its first use, or use the plain name."))
    return out


def _spelled_anywhere(whole, letters):
    """A page may spell the abbreviation out at a later use; what counts is that the words stand beside it once."""
    return any(spelled_out(whole, found) for found in re.finditer(rf"(?<![\w-]){letters}(?![\w-])", whole))


# ---------------------------------------------------------------------------------------------------- W367

def clauses(text):
    """Runs of words with no punctuation or link inside: a phrase never crosses a comma, a full stop or a link."""
    plain = MD_LINK.sub("|", WIKILINK.sub("|", URL.sub("|", CODE_SPAN.sub("|", text))))
    for run in re.split(r"[|.,;:!?()\[\]\"“”—–]|\s-\s", plain):
        words = [w.lower().replace("’", "'") for w in WORD.findall(run)]
        if words:
            yield words


def phrases(words):
    size = schema.PHRASE_WORDS
    for i in range(len(words) - size + 1):
        gram = words[i:i + size]
        if any(w not in schema.PHRASE_FILLER for w in gram):
            yield " ".join(gram)


def name_words(vault):
    """The content words of every page title and heading in the vault. A phrase made only of these is a thing's name
    ("consent and identity"), which a page has to repeat to refer to it; it is not a stamped clause."""
    texts = [h.text for page in vault.pages for h in page.headings]
    texts += [str(page.meta.get("title") or page.name) for page in vault.pages]
    texts += [h for page in vault.pages for h in _handles(page.meta.get("owner"))]  # "@solution-lead" names a role
    return {w for text in texts for w in (x.lower() for x in WORD.findall(visible(text))) if w not in schema.PHRASE_FILLER}


def _handles(owner):
    owners = owner if isinstance(owner, list) else [owner]
    return [o.lstrip("@").replace("-", " ").replace("/", " ") for o in owners if isinstance(o, str)]


def repeated_phrases(vault):
    """{phrase: (times, [(page, first line)])} for each phrase over the page or time limit, with a phrase that is only a
    name left out and overlapping phrases joined into the whole clause they come from (one stamped sentence is dozens of
    overlapping four-word runs, and is one finding). Pages are in path order."""
    counts, where = defaultdict(int), defaultdict(dict)
    names = name_words(vault)
    for page in sorted(vault.pages, key=lambda p: p.path):
        if not _readable(page):
            continue
        for n, text, _ in paragraphs(page):
            for words in clauses(text):
                for phrase in phrases(words):
                    counts[phrase] += 1
                    where[phrase].setdefault(page.path, n)
    over = {p: (counts[p], where[p])
            for p in counts if (len(where[p]) > schema.PHRASE_PAGE_LIMIT or counts[p] > schema.PHRASE_TIME_LIMIT)
            and not _only_a_name(p, names)}
    return {p: (times, sorted(spots.items())) for p, (times, spots) in _joined(over).items()}


def _only_a_name(phrase, names):
    return all(w in names for w in phrase.split() if w not in schema.PHRASE_FILLER)


def _joined(over):
    """Three-word phrases that overlap by two words and are used about as often are one clause: follow each run from its
    first phrase to its last and report it once, with the pages of its least-used part. A four-word phrase over the
    limit makes its two three-word parts over it too, so three words find everything four would."""
    def close(a, b):
        return min(over[a][0], over[b][0]) * 10 >= max(over[a][0], over[b][0]) * 7

    after = {a: [b for b in over if b != a and b.split()[:2] == a.split()[1:] and close(a, b)] for a in over}
    has_before = {b for nexts in after.values() for b in nexts}
    used, runs = set(), {}
    for start in sorted(over, key=lambda p: (p in has_before, p)):
        if start in used:
            continue
        parts, here = [start], start
        used.add(start)
        while True:
            options = [b for b in after[here] if b not in used]
            if not options:
                break
            here = max(options, key=lambda p: (over[p][0], p))
            used.add(here)
            parts.append(here)
        words = parts[0].split() + [p.split()[-1] for p in parts[1:]]
        weakest = min(parts, key=lambda p: (over[p][0], len(over[p][1])))
        runs[" ".join(words)] = over[weakest]
    return runs


def phrase_findings(vault):
    """(page, line, code, message, fix) for each stock phrase, once, on the first page that uses it."""
    pages = {p.path: p for p in vault.pages}
    out = []
    for phrase, (times, spots) in sorted(repeated_phrases(vault).items()):
        names = [pages[path].name for path, _ in spots]
        listed = ", ".join(names[:6]) + (f" and {len(names) - 6} more" if len(names) > 6 else "")
        first_path, line = spots[0]
        out.append((pages[first_path], line, "W367",
                    f"'{phrase}' appears {times} times on {len(spots)} page{'s' if len(spots) != 1 else ''} ({listed}); a clause repeated across pages reads as stamped.",
                    "Say the state once in the paragraph; put the rest on a Trace line or in the table."))
    return out


def page_findings(page, template_known):
    """W365, W366, W368 and W369 for one page, as (line, code, message, fix)."""
    if not _readable(page):
        return []
    return sorted(paragraph_findings(page) + cell_findings(page) + template_opening_findings(page, template_known)
                  + abbreviation_findings(page))
