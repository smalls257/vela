"""Reading the record: one key per page and item, and vault text made safe to show.

Shared by every part of the build, so a link means the same thing in a panel, a flow step and a strip.
Every value here comes from the planner's own parser (planner.parse, planner.reading)."""
import html
import re

from planner import readability, reading
from planner.parse import WIKILINK, parse_link

HANDLE = re.compile(r"@[A-Za-z0-9][\w./-]*")
STEP = re.compile(r"^(\d+)\.\s+(.*)$")
BLOCK_REF = re.compile(r"\s\^[A-Za-z0-9-]+\s*$")
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
WEB_ADDRESS = re.compile(r"^(?:https?://[^\s<>\"']+|mailto:[^\s<>\"']+)$")
LABELLED_LINE = re.compile(r"^\*\*[^*]+:\*\*")
PROSE_LIMIT = 1100  # characters of opening prose kept for the panel; the panel says when the page goes on


class Keys:
    """One key per page and item, so the page's JavaScript can name anything the vault holds."""

    def __init__(self, vault):
        self.vault = vault
        self.names = readability.NameIndex(vault)
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


    def key_of(self, entry):
        """The key an ID's name points at: the item for an item ID, else the page that holds it."""
        return entry.id if self.vault.item(entry.id) is not None else self.page(entry.page)


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


PROSE, LISTED = "prose", "listed"


def inline_html(text, keys, page, where=LISTED):
    """Markdown inline text to safe HTML: wikilinks become clickable references, the rest is escaped. `where` says what
    surrounds the text: running PROSE shows a question's state only when it is worth flagging (an "open" pill mid-sentence
    is noise, since open is what a linked question is by default); a LISTED item or table cell shows every state."""
    text = BLOCK_REF.sub("", text)
    parts, refs, web_links = [], [], []

    def hold_web_link(match):
        """A web link keeps its address; any other target (a relative file, javascript:) shows its label only."""
        label, target = match.group(1), match.group(2).strip()
        if not WEB_ADDRESS.match(target):
            return label
        web_links.append((label, target))
        return f"\x01{len(web_links) - 1}\x01"

    text = MD_LINK.sub(hold_web_link, text)

    def hold(match):
        link = parse_link(match.group(1), 0)
        label = link_label(keys.vault, link, page)
        entry = keys.names.lookup(label) if label else None
        # a link whose words are only a code (a generated table writes [[page|CON-002]]) reads as the thing's name, the code on hover
        named = entry.id if entry is not None and entry.name != label else None
        refs.append((link, keys.link(link, page), entry.name if named else label, named))
        return f"\x00{len(refs) - 1}\x00"

    def name_it(entry):
        refs.append((None, keys.key_of(entry), entry.name, entry.id))
        return f"\x00{len(refs) - 1}\x00"

    held = readability.name_ids(WIKILINK.sub(hold, text), keys.names, name_it)
    out = html.escape(held, quote=False)
    code = []  # code spans are set aside so a `*.md` glob is never read as emphasis
    out = re.sub(r"`([^`]+)`", lambda m: (code.append(m.group(1)), f"\x02{len(code) - 1}\x02")[1], out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", out)
    for i, span in enumerate(code):
        out = out.replace(f"\x02{i}\x02", f"<code>{span}</code>")
    for i, (label, target) in enumerate(web_links):
        anchor = (f'<a class="ext" href="{html.escape(target)}" target="_blank" rel="noopener noreferrer">'
                  f'{html.escape(label, quote=False)}</a>')
        out = out.replace(f"\x01{i}\x01", anchor)
    for i, (link, key, label, named) in enumerate(refs):
        label_html = html.escape(label, quote=False)
        if named:
            anchor = name_anchor(key, label_html, named)
        else:
            anchor = (f'<a class="ref" data-ref="{html.escape(key)}">{label_html}</a>{state_badge(keys.vault, key, where)}' if key
                  else f'<span class="ref-dead" title="This link points at nothing in the vault">{label_html}</span>')
        out = out.replace(f"\x00{i}\x00", anchor)
    parts.append(out)
    return "".join(parts)


def name_anchor(key, label_html, item_id):
    """A bare ID shown as the thing's name. The ID sits in the tooltip, and as a small muted suffix on hover only."""
    ident = html.escape(item_id)
    return (f'<a class="ref idname" data-ref="{html.escape(key)}" title="{ident}">{label_html}'
            f'<span class="idsuf"> {ident}</span></a>')


def chips_html(ids, keys):
    """One quiet, collapsible row of name chips for a `- Trace:` line. An ID the vault does not hold is left out, since
    a chip that opens nothing is noise; the line in the file still carries it."""
    entries = readability.chip_entries(ids, keys.names)
    if not entries:
        return ""
    chips = "".join(f'<a class="ref chip" data-ref="{html.escape(keys.key_of(e))}" title="{html.escape(e.id)}">'
                    f'{html.escape(e.name)}</a>' for e in entries)
    return f'<details class="r-trace"><summary>Traces to ({len(entries)})</summary><span class="chips">{chips}</span></details>'


def state_badge(vault, key, where=LISTED):
    """An unknown's state as the unknowns page records it now, beside a link to it. Prose that calls a question open
    goes stale the day it is answered; the badge never does. A real space stands between link and pill, and the pill
    carries its own parentheses (hidden on screen, kept when copied), so the text reads "made (resolved)" and never
    "madeopen"."""
    item = vault.item(key)
    if item is None or item.kind != "unknown":
        return ""
    state = item.fact("State") or "no state"
    if where == PROSE and state == "open":
        return ""
    s = html.escape(state)
    return (f' <span class="ustate us-{s}" role="note" aria-label="{html.escape(key)} is {s}" '
            f'title="{html.escape(key)} is {s} on the unknowns page"><span class="sr-only">(</span>{s}<span class="sr-only">)</span></span>')


def plain(text):
    """What a reader sees of a line, for search: links as their labels, no markup."""
    return reading.visible(BLOCK_REF.sub("", text)).replace("**", "").replace("`", "")


def refs_in(text, keys, page):
    return [k for k in (keys.link(parse_link(m.group(1), 0), page) for m in WIKILINK.finditer(text)) if k]


