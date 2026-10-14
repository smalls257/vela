"""The vault's own pages, readable inside the explorer, and the sidebar that lists them in the vault's section order.

A page is shown in planner's reading order (`reading.arrange`, the same the planner viewer uses: what is true now
first, history folded at the end, generated blocks under plain headings). This module renders that Markdown to HTML
itself, escaping every character of vault text, so no page can add markup of its own. The only tags it writes are
fixed ones: headings, paragraphs, lists, tables, quotes, code, details and sup. Wikilinks become `data-ref` links,
so a link opens its target inside the explorer, not as a file.
"""
import html
import re

from vela import readability, reading
from vela.parse import closes_fence, protect_link_pipes
from vela.viewer import body_of

from .record import LISTED, PROSE, chips_html, inline_html, title_of

HEADING = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
FENCE = re.compile(r"^\s{0,3}(`{3,}(?=[^`]*$)|~{3,})\s*([\w-]*)")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*]|(\d+)\.)\s+(.*)$")
DETAILS_OPEN = re.compile(r"^\s*<details><summary>(.*?)</summary>\s*$")
DETAILS_CLOSE = re.compile(r"^\s*</details>\s*$")
TABLE_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def slug(text):
    return "h-" + re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def cells(line):
    """A table row's cells: split on unescaped pipes; a `\\|` inside a wikilink stays in its cell."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    # reading.tidy relabels [[page#X Name\\|X]] as Name, keeping the table's escaping backslash in the label: drop it
    inner = protect_link_pipes(inner)  # a bare | inside [[link|label]] is the link's, not a column break
    return [re.sub(r"\\(?=\]\])", "", c.replace("\x00", "|").replace("\\|", "|")).strip() for c in re.split(r"(?<!\\)\|", inner)]


class Renderer:
    def __init__(self, page, keys):
        self.page, self.keys = page, keys
        names = reading.item_names(page.text.split("\n"))
        self.item_by_name = {}
        for item_id, name in names.items():
            self.item_by_name.setdefault(name, item_id)
        self.toc, self.used = [], set()

    def inline(self, text, where=PROSE):
        out = inline_html(text, self.keys, self.page, where)
        # reading.arrange writes its own <sup> around folded citations; those, and only those, become tags again
        return out.replace("&lt;sup&gt;", "<sup>").replace("&lt;/sup&gt;", "</sup>")

    def anchor(self, level, text):
        item = self.item_by_name.get(text) if level >= 3 else None
        if item and self.keys.vault.item(item) is not None and item not in self.used:
            self.used.add(item)
            return item
        base, n = slug(text), 1
        found = base
        while found in self.used:
            n += 1
            found = f"{base}-{n}"
        self.used.add(found)
        return found

    def render(self, markdown):
        lines = markdown.split("\n")
        out, i = [], 0
        para = []

        def flush():
            if para:
                out.append(f"<p>{self.inline(' '.join(para))}</p>")
                para.clear()

        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()
            fence = FENCE.match(raw)
            if fence:
                flush()
                mark, lang = fence.group(1), fence.group(2)
                body = []
                i += 1
                while i < len(lines) and not closes_fence(lines[i], mark):
                    body.append(lines[i])
                    i += 1
                code = html.escape("\n".join(body))
                if lang == "mermaid":
                    out.append('<details class="r-diagram"><summary>Diagram source (the dashboard draws this system '
                               f'on its map)</summary><pre><code>{code}</code></pre></details>')
                else:
                    out.append(f"<pre><code>{code}</code></pre>")
                i += 1
                continue
            if not stripped:
                flush()
                i += 1
                continue
            opened = DETAILS_OPEN.match(raw)
            if opened:
                flush()
                out.append(f"<details class=\"r-fold\"><summary>{html.escape(opened.group(1))}</summary>")
                i += 1
                continue
            if DETAILS_CLOSE.match(raw):
                flush()
                out.append("</details>")
                i += 1
                continue
            heading = HEADING.match(raw)
            if heading:
                flush()
                level, text = len(heading.group(1)), heading.group(2)
                aid = self.anchor(level, text)
                if level <= 3:
                    self.toc.append({"level": level, "text": reading.visible(text), "id": aid})
                out.append(f'<h{level} id="{html.escape(aid)}">{self.inline(text)}</h{level}>')
                i += 1
                continue
            if not out and not para and reading.BREADCRUMB.match(stripped):
                i += 1  # the "Harborline / 05 Building blocks / Booking" trail: the sidebar already says where you are
                continue
            if stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1].strip()):
                flush()
                head = cells(stripped)
                i += 2
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append(cells(lines[i]))
                    i += 1
                th = "".join(f"<th>{self.inline(c)}</th>" for c in head)
                tb = "".join("<tr>" + "".join(f"<td>{self.inline(c, LISTED)}</td>" for c in r) + "</tr>" for r in rows)
                out.append(f'<div class="r-table"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
                continue
            if stripped.startswith(">"):
                flush()
                quote = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    quote.append(lines[i].strip()[1:].strip())
                    i += 1
                out.append(f"<blockquote>{self.inline(' '.join(quote))}</blockquote>")
                continue
            if stripped in ("---", "***"):
                flush()
                out.append("<hr>")
                i += 1
                continue
            item = LIST_ITEM.match(raw)
            if item:
                flush()
                i = self.list_block(lines, i, out)
                continue
            para.append(stripped)
            i += 1
        flush()
        return "\n".join(out)

    def trace_row(self, lines, i, out):
        """The run of Trace lines starting at `i` as one row of name chips; returns the line after the run."""
        ids = []
        while i < len(lines) and readability.is_trace(lines[i]):
            ids += readability.trace_ids(lines[i])
            i += 1
        out.append(chips_html(ids, self.keys))
        return i

    def list_block(self, lines, i, out):
        """A list, with one level of nesting by indentation."""
        first = LIST_ITEM.match(lines[i])
        if readability.is_trace(lines[i]):
            return self.trace_row(lines, i, out)
        ordered = first.group(2) is not None
        base = len(first.group(1))
        tag = "ol" if ordered else "ul"
        start = f' start="{int(first.group(2))}"' if ordered and first.group(2) != "1" else ""
        parts = [f"<{tag}{start}>"]
        open_li = False
        while i < len(lines):
            m = LIST_ITEM.match(lines[i])
            if m and readability.is_trace(lines[i]) and open_li:
                i = self.trace_row(lines, i, parts)  # a Trace line at this level belongs to the item above it
                continue
            if m and len(m.group(1)) <= base:
                if (m.group(2) is not None) != ordered:
                    break
                if open_li:
                    parts.append("</li>")
                parts.append(f"<li>{self.inline(m.group(3), LISTED)}")
                open_li = True
                i += 1
                continue
            if m and len(m.group(1)) > base:
                sub = []
                i = self.list_block(lines, i, sub)
                parts.extend(sub)
                continue
            if lines[i].strip() and lines[i][:1] in " \t" and open_li:
                parts.append(" " + self.inline(lines[i].strip(), LISTED))
                i += 1
                continue
            break
        if open_li:
            parts.append("</li>")
        parts.append(f"</{tag}>")
        out.append("".join(parts))
        return i


def page_reader(page, keys):
    """{"html", "toc"} for one page in planner's reading order."""
    r = Renderer(page, keys)
    body = r.render(reading.arrange(body_of(page)))
    return {"html": body, "toc": r.toc}


def readers(vault, keys):
    out = {}
    for page in vault.pages:
        if page.path.startswith("voice/"):
            continue
        out[keys.page(page)] = page_reader(page, keys)
    return out


# --------------------------------------------------------------------------- the sidebar, in the vault's own order

SECTIONS = (  # (id, label, the section's own page path, a test for the pages listed under it, list them open?)
    ("goals", "Goals", "01-goals.md", None),
    ("constraints", "Constraints", "02-constraints.md", None),
    ("context", "Context and scope", "03-context-and-scope.md", None),
    ("strategy", "Strategy", "04-solution-strategy.md", None),
    ("capabilities", "Capabilities", "04a-capability-delta.md", lambda p: p.type == "capability"),
    ("releases", "Releases", "04b-releases.md", None),
    ("slices", "Slices", "slices/", lambda p: p.type == "slice"),  # no page of its own: each slice is one
    ("apps", "Apps", "05-building-blocks/05-building-blocks.md", lambda p: p.type == "app-building-blocks"),
    ("flows", "Flows", "06-runtime/06-flows.md", lambda p: p.type == "flow"),
    ("concerns", "Concerns", "08-concerns/08-concerns.md", lambda p: p.type == "concern"),
    ("decisions", "Decisions", "09-decisions/09-decisions.md", lambda p: p.type == "decision"),
    ("unknowns", "Unknowns and risks", "11-unknowns-and-risks.md", None),
    ("glossary", "Glossary", "12-glossary.md", None),
    ("epics", "Epics", "13-epics/13-epics.md", lambda p: p.type == "epic"),
)


def sections(vault, keys):
    by_path = {p.path: p for p in vault.pages}
    out = []
    for sid, label, path, member in SECTIONS:
        page = by_path.get(path)
        children = sorted((p for p in vault.pages if member and member(p)), key=lambda p: (p.id or p.name))
        out.append({"id": sid, "label": label, "page": keys.page(page) if page else "", "path": path,
                    "title": title_of(page) if page else "",
                    "children": [keys.page(p) for p in children]})
    return out


def outgoing(vault, keys):
    """Every page's and item's outgoing links, as keys: what a decision's ripple starts from."""
    out = {}
    for page in vault.pages:
        if page.path.startswith(("voice/", "sessions/")):
            continue
        source = keys.page(page)
        seen = out.setdefault(source, [])
        for link in page.links:
            key = keys.link(link, page)
            if key and key != source and key not in seen:
                seen.append(key)
    return out
