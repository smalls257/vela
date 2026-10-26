"""The page index: what the companion panels need from each page, so a panel never loads the whole vault.

Pure. `entries` reads one page's text through the same `parse.parse_page` and `model.build` the checks use, so the
index can never name an item differently from the plan (a Distributed Monolith of names ruled out). The edge
(`edge/companionstore.py`) keeps one entry per page on disk and calls `entries` only for pages that changed
(Computational Friction ruled out: a panel after every write cannot afford 111 parses).

An index entry is JSON-shaped:
    {"page": {"id", "title", "type", "state", "owner"},
     "items": {id: {"kind", "name", "state", "owner", "ask", "ask_by", "opened", "blocks": [[target, anchor], ...]}},
     "steps": [{"n", "from", "to", "text"}]}
"""
from dataclasses import dataclass

from vela import askwho, flows, model, parse, progress, schema

VERSION = 1  # bump when an entry's shape changes; an index of another version is rebuilt whole


@dataclass(frozen=True)
class Name:
    id: str
    name: str      # an item's heading text after its ID; a page's title
    kind: str      # "contract" | "unknown" | ... for items; the page `type` for pages
    state: str     # lower-case first word of the State bullet or `state:`; "" when none
    page: str      # vault-relative path of the page it sits on


class _Facts:
    """Just enough of an item for askwho.who_to_ask: `.fact(label)` over the indexed owner and ask lines."""

    def __init__(self, owner, ask):
        self.values = {"Owner": owner, "Ask": ask}

    def fact(self, label):
        return self.values.get(label, "")


def first_word(text):
    words = str(text or "").strip().lower().split()
    return words[0].strip(".,;:") if words else ""


def _date_of(text):
    token = str(text or "").strip().split(" ")[0]
    return token if schema.DATE_RE.match(token) else ""


def _text(value):
    return "" if value is None else str(value)


def _blocks(item, page):
    bullet = item.facts.get("Blocks")
    if bullet is None:
        return []
    return [[link.target or page.name, link.anchor] for link in bullet.links]


def _item_entry(item, page):
    return {"kind": item.kind, "name": item.name, "state": first_word(item.fact("State")),
            "owner": item.fact("Owner"), "ask": item.fact("Ask"), "ask_by": _date_of(item.fact("Ask by")),
            "opened": progress.leading_date(item.fact("Opened")), "blocks": _blocks(item, page)}


def _steps(vault, page):
    if page.type != "flow":
        return []
    return [{"n": step.number, "from": step.pair[0] if step.pair else "", "to": step.pair[1] if step.pair else "",
             "text": step.raw} for step in flows.steps(vault)]


def entries(path, text):
    page = parse.parse_page(path, text)
    vault = model.build([page], {})
    items = {item.id: _item_entry(item, page) for found in vault.items.values() for item in found}
    return {"page": {"id": page.id, "title": _text(page.meta.get("title")) or page.name, "type": page.type,
                     "state": first_word(page.meta.get("state")), "owner": _text(page.meta.get("owner"))},
            "items": items, "steps": _steps(vault, page)}


def _pages(index):
    return index.get("pages", {})


def names(index):
    """{id: Name} over every page and item in the index."""
    found = {}
    for path, entry in _pages(index).items():
        page = entry["page"]
        if page["id"]:
            found[page["id"]] = Name(page["id"], page["title"], page["type"], page["state"], path)
        for item_id, item in entry["items"].items():
            found[item_id] = Name(item_id, item["name"], item["kind"], item["state"], path)
    return found


def _stem(path):
    return path.rsplit("/", 1)[-1][:-3]


def resolve(index, link):
    """[target, anchor] -> an item or page ID, "" when none. An anchor that starts with an item ID names that item;
    otherwise the target names the page."""
    target, anchor = link[0], link[1]
    first = anchor.split()[0] if anchor.split() else ""
    if first and any(first in entry["items"] for entry in _pages(index).values()):
        return first
    for path, entry in _pages(index).items():
        if _stem(path).lower() == target.lower() and entry["page"]["id"]:
            return entry["page"]["id"]
    return ""


def blocking(index, item_id):
    """Ids of open unknowns whose Blocks resolve to `item_id`, in page order."""
    found = []
    for entry in _pages(index).values():
        for unknown_id, item in entry["items"].items():
            if item["kind"] == "unknown" and item["state"] == "open" \
                    and any(resolve(index, link) == item_id for link in item["blocks"]):
                found.append(unknown_id)
    return found


def handles(index):
    """Every @handle in the index's owner and ask fields, for askwho.resolve_role."""
    found = set()
    for entry in _pages(index).values():
        for item in entry["items"].values():
            found.update(askwho.HANDLE.findall(item["owner"] + " " + item["ask"]))
        found.update(askwho.HANDLE.findall(entry["page"]["owner"]))
    return found


def who(index, unknown_id):
    """The name to show for whoever holds this question: askwho.who_to_ask on the indexed facts."""
    for entry in _pages(index).values():
        item = entry["items"].get(unknown_id)
        if item is not None:
            return askwho.who_to_ask(_Facts(item["owner"], item["ask"]), sorted(handles(index)))["name"]
    return ""
