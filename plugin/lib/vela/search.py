"""Plain-word search over the vault: "paper order", "how does coach talk to brightwater". Pure.

`query find` needs every word in a title or heading, which suits /ask checking an ID but fails a person
mid-conversation, who types the words they are saying, not the vault's. This ranks every page and section
by how many of the meaningful words it holds and where (title, heading, opening, text), and attaches the
flows that cross each hit, because "how does X work" is usually answered by a flow, and a flow page lives in
a folder nobody remembers in the moment. No model is involved: the same words always give the same answer.
"""
import math
import re
from dataclasses import dataclass, field

FENCE = re.compile(r"```.*?```", re.S)
GENERATED = re.compile(r"<!-- generated:.*?<!-- /generated:[^>]*-->", re.S)
WIKILINK = re.compile(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\\?\|([^\]]*))?\]\]")
HEADING = re.compile(r"^(#{1,4})\s+(.*?)(?:\s+#+)?\s*$")
WORD = re.compile(r"[a-z0-9]+")  # "brightwater's" gives "brightwater" and "s", and "s" is a stop word
SKIP_TOP = ("sessions/", "voice/", ".inbox/", "handoffs/", ".claude/", "docs/")
SKIP_FILES = ("CONVENTIONS.md", "CLAUDE.md", "README.md")
STOP = set("""a an and are as at be by can do does for from get gets how i in is it its of on or our so that the
their them then there they this to was we what when where which who why will with you your about into over
work works talk talks happen happens go goes s""".split())
# Where a word is found, and what it is worth there.
WEIGHT = {"title": 6, "heading": 4, "opening": 2, "text": 1}


def stem(word):
    """A crude stem, enough that "orders" finds "order", "places" finds "place" and "trading" finds "trade".
    A final "e" goes too, so "place", "places" and "placed" all come to "plac"."""
    for suffix in ("ing", "ies", "es", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)] + ("y" if suffix == "ies" else "")
            break
    return word[:-1] if word.endswith("e") and len(word) >= 4 else word


def terms(words):
    """The meaningful stems of what the person typed, in order, without repeats."""
    seen = []
    for w in WORD.findall(" ".join(words).lower()):
        s = stem(w)
        if w not in STOP and s not in seen:
            seen.append(s)
    return seen


def plain(markdown):
    """Readable text: links become their labels, markup goes."""
    def label(m):
        return m.group(3) or m.group(2) or m.group(1).rsplit("/", 1)[-1]
    out = WIKILINK.sub(label, markdown)
    out = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", out)
    return re.sub(r"[*_`>|]+", " ", out)


def stems_of(text):
    return {stem(w) for w in WORD.findall(text.lower())}


@dataclass
class Section:
    page: object
    heading: str  # "" for the page's opening
    opening: str  # first paragraph of the section, plain
    text: str  # the rest, plain
    links: set = field(default_factory=set)  # "page-name" and "page-name#heading" this section links to


def body(page):
    text = page.text.split("\n---\n", 1)[1] if page.text.startswith("---") else page.text
    return GENERATED.sub("", FENCE.sub("", text))


def first_paragraph(lines):
    para = []
    for line in lines:
        if not line.strip():
            if para:
                break
            continue
        para.append(line.strip())
    return " ".join(para)


def sections(page):
    """The page cut at its headings. The first section is the page's own opening, under its title. Everything
    under `## History` is left out: it is how the page got here, not what it says."""
    out, heading, lines, in_history = [], "", [], False
    for line in body(page).split("\n") + ["## "]:
        m = HEADING.match(line)
        if m and len(m.group(1)) >= 2 or line == "## ":
            raw = "\n".join(lines)
            if not in_history and (raw.strip() or heading):
                links = {t + (f"#{a}" if a else "") for t, a, _ in WIKILINK.findall(raw)} | {t for t, _, _ in WIKILINK.findall(raw)}
                out.append(Section(page, heading, plain(first_paragraph(lines)), plain(raw), links))
            heading, lines = (m.group(2) if m else ""), []
            if m and len(m.group(1)) == 2:
                in_history = heading.lower() == "history"
        elif not (m and len(m.group(1)) == 1):
            lines.append(line)
    return out


@dataclass(frozen=True)
class Hit:
    page: str
    title: str
    kind: str
    heading: str
    snippet: str
    score: int
    matched: tuple
    flows: tuple  # (flow title, flow path) for each flow that crosses this hit


def searchable(page):
    return not page.path.startswith(SKIP_TOP) and page.path.rsplit("/", 1)[-1] not in SKIP_FILES


def score(section, title, wanted):
    places = {"title": stems_of(title) if not section.heading else set(), "heading": stems_of(section.heading),
              "opening": stems_of(section.opening), "text": stems_of(section.text)}
    total, matched = 0, []
    for term in wanted:
        best = max((WEIGHT[k] for k, found in places.items() if term in found), default=0)
        if best:
            total += best
            matched.append(term)
    return total, tuple(matched)


def snippet(section, limit=220):
    text = re.sub(r"\s+", " ", section.opening or section.text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def flows_crossing(flows, page, heading):
    """Flows whose steps link this section, or for a page's opening, the page itself. A flow that links one
    contract on a page does not cross every other section of that page."""
    keys = {f"{page.name}#{heading}"} if heading else {page.name}
    return tuple((str(f.meta.get("title") or f.name), f.path) for f, links in flows
                 if f is not page and links & keys)


def view_link(vault, hit):
    """The hit's address in `planner view`'s HTML, to append to the viewer file's path."""
    name = next(p.name for p in vault.pages if p.path == hit.page)
    return f"#/{name}" + (f"::{hit.heading}" if hit.heading else "")


def search(vault, words, limit=10):
    """{"words", "terms", "hits": [...]} ranked best first; "not_found" when nothing holds enough of the words."""
    wanted = terms(words)
    answer = {"words": list(words), "terms": wanted, "hits": []}
    if not wanted:
        answer["not_found"] = True
        return answer
    need = max(1, math.ceil(len(wanted) / 2))
    pages = [p for p in vault.pages if searchable(p)]
    flows = [(p, {l for s in sections(p) for l in s.links}) for p in pages if p.type == "flow"]
    hits = []
    for page in pages:
        title = str(page.meta.get("title") or page.name)
        for section in sections(page):
            points, matched = score(section, title, wanted)
            if len(matched) < need:
                continue
            if page.type == "flow" and re.search(r"\bhow\b", " ".join(words).lower()):
                points += 4  # "how does X" is a flow's question
            hits.append(Hit(page.path, title, page.type, section.heading, snippet(section), points, matched,
                            flows_crossing(flows, page, section.heading)))
    hits.sort(key=lambda h: (-h.score, -len(h.matched), h.page, h.heading))
    # One page should not fill the list: keep its best two sections.
    kept, per_page = [], {}
    for h in hits:
        if per_page.get(h.page, 0) < 2:
            kept.append(h)
            per_page[h.page] = per_page.get(h.page, 0) + 1
    answer["hits"] = [h.__dict__ | {"matched": list(h.matched), "flows": [{"title": t, "page": p} for t, p in h.flows],
                                    "view": view_link(vault, h)} for h in kept[:limit]]
    answer["more"] = max(0, len(kept) - limit)
    if not kept:
        answer["not_found"] = True
    return answer
