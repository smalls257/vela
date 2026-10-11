"""Reading the record: one key per page and item, and vault text made safe to show.

Shared by every part of the build, so a link means the same thing in a panel, a flow step and a strip.
Every value here comes from the planner's own parser (planner.parse, planner.reading)."""
import html
import re

from planner import reading
from planner.parse import WIKILINK, parse_link

HANDLE = re.compile(r"@[A-Za-z0-9][\w./-]*")
STEP = re.compile(r"^(\d+)\.\s+(.*)$")
BLOCK_REF = re.compile(r"\s\^[A-Za-z0-9-]+\s*$")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
LABELLED_LINE = re.compile(r"^\*\*[^*]+:\*\*")
PROSE_LIMIT = 1100  # characters of opening prose kept for the panel; the panel says when the page goes on


class Keys:
    """One key per page and item, so the page's JavaScript can name anything the vault holds."""

    def __init__(self, vault):
        self.vault = vault
        self.page_key = {}
        seen = {}
        for page in vault.pages:
            seen[page.id] = seen.get(page.id, 0) + 1
        for page in vault.pages:
            self.page_key[page.path] = page.id if page.id and seen[page.id] == 1 else "page:" + page.name

    def page(self, page):
        return self.page_key[page.path]

    def link(self, link, from_page):
        """The key a wikilink points at: an item when its anchor names one on that page, else the page."""
        target = self.vault.resolve(link, from_page)
        if target is None:
            return None
        first = link.anchor.split()[0].upper() if link.anchor.split() else ""
        item = self.vault.item(first) if first else None
        if item is not None and item.page is target:
            return item.id
        return self.page(target)


def link_label(vault, link, from_page):
    if link.label:
        return link.label
    if link.anchor and not link.anchor.startswith("^"):
        return reading.LEADING_ID.sub("", link.anchor).strip() or link.anchor
    target = vault.resolve(link, from_page)
    return title_of(target) if target is not None else link.target


def title_of(page):
    title = page.meta.get("title")
    return title.strip() if isinstance(title, str) and title.strip() else page.name


def inline_html(text, keys, page):
    """Markdown inline text to safe HTML: wikilinks become clickable references, the rest is escaped."""
    text = BLOCK_REF.sub("", text)
    text = MD_LINK.sub(r"\1", text)
    parts, refs = [], []

    def hold(match):
        link = parse_link(match.group(1), 0)
        refs.append((link, keys.link(link, page), link_label(keys.vault, link, page)))
        return f"\x00{len(refs) - 1}\x00"

    held = WIKILINK.sub(hold, text)
    out = html.escape(held, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", out)
    for i, (link, key, label) in enumerate(refs):
        label_html = html.escape(label, quote=False)
        anchor = (f'<a class="ref" data-ref="{html.escape(key)}">{label_html}</a>{state_badge(keys.vault, key)}' if key
                  else f'<span class="ref-dead" title="This link points at nothing in the vault">{label_html}</span>')
        out = out.replace(f"\x00{i}\x00", anchor)
    parts.append(out)
    return "".join(parts)


def state_badge(vault, key):
    """An unknown's state as the unknowns page records it now, beside every link to it. Prose that calls a
    question open goes stale the day it is answered; the badge never does."""
    item = vault.item(key)
    if item is None or item.kind != "unknown":
        return ""
    state = item.fact("State") or "no state"
    return f'<span class="ustate us-{html.escape(state)}" title="{html.escape(key)} is {html.escape(state)} on the unknowns page">{html.escape(state)}</span>'


def plain(text):
    """What a reader sees of a line, for search: links as their labels, no markup."""
    return reading.visible(BLOCK_REF.sub("", text)).replace("**", "").replace("`", "")


def refs_in(text, keys, page):
    return [k for k in (keys.link(parse_link(m.group(1), 0), page) for m in WIKILINK.finditer(text)) if k]


