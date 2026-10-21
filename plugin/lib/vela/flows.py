"""Flow steps and who sends each message. Pure.

A step that crosses between two lanes begins with a sender-to-receiver pair, then a colon and the sentence:
`3. [[rider-building-blocks|Rider app]] -> [[docks-building-blocks|Dock service]]: sends the unlock code over [[...#CON-005 Dock unlock|Dock unlock]].`
The pair is the recorded direction. Without it a reader (the explorer) can only guess the direction from the
contract's provider and consumers. E350 and W351 read the same steps through `steps()`.

Each end of a pair must be an app in the plan or an outside party the plan knows, and an app is written as a link,
so the explorer can draw the step between two lanes it recognizes (E351, W354). A step that names several lanes and
gives no pair, no contract, leaves the explorer unable to say who hands what to whom (W374).
"""
import re
from dataclasses import dataclass

from vela import diagrams, parse

STEP = re.compile(r"^(\d+)\.\s+(.*)$")
_END = r"\[\[[^\]]+\]\]|[^\[\]:→>\n]{1,60}?"
PAIR = re.compile(rf"^\s*({_END})\s*(?:→|->)\s*({_END})\s*:\s")
PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")


@dataclass(frozen=True)
class Step:
    page: object  # the flow page
    number: int
    line: int
    raw: str
    pair: tuple  # (sender text, receiver text) as written, or () when the step names none
    contracts: tuple  # contract items the step links


def split_pair(raw):
    """(sender, receiver) as written at the start of a step, or () when the step has no arrow pair."""
    found = PAIR.match(raw)
    return (found.group(1).strip(), found.group(2).strip()) if found else ()


def _contracts_linked(vault, page, raw, line):
    out = []
    for link in parse.links_in(raw, line):
        first = link.anchor.split()[0].upper() if link.anchor.split() else ""
        item = vault.item(first) if first else None
        if item is not None and item.kind == "contract" and item.page is vault.resolve(link, page) and item not in out:
            out.append(item)
    return tuple(out)


def steps(vault):
    """Every numbered line under `## Steps` of every flow page, in page and line order."""
    out = []
    for page in sorted(vault.of_type("flow"), key=lambda p: p.path):
        heading = next((h for h in page.headings if h.level == 2 and h.text.strip().lower() == "steps"), None)
        if heading is None:
            continue
        end = next((h.line for h in page.headings if h.line > heading.line and h.level <= 2), None)
        lines = page.text.split("\n")
        for n in range(heading.line + 1, (end or len(lines) + 1)):
            match = STEP.match(lines[n - 1].strip())
            if match:
                raw = match.group(2)
                out.append(Step(page, int(match.group(1)), n, raw, split_pair(raw), _contracts_linked(vault, page, raw, n)))
    return out


def _name(text):
    return " ".join(PARENTHETICAL.sub("", text).split()).lower()


def endpoint(vault, page, text):
    """A stable key for one end of a pair: an app's ID, or an outside party's lower-cased name."""
    found = parse.WIKILINK.search(text)
    if found:
        link = parse.parse_link(found.group(1), 0)
        target = vault.resolve(link, page)
        if target is not None and target.type == "app-building-blocks":
            return target.id
        label = link.label or re.sub(r"^[A-Z]+-\d+\s+", "", link.anchor) or link.target
        return _name(label)
    plain = _name(text)
    for app in vault.apps:
        title = app.meta.get("title")
        if plain in (_name(str(title)) if title else "", app.name.lower(), app.id.lower()):
            return app.id
    return plain


def contract_parties(vault, contract):
    """Keys of everyone a contract joins: its provider (the page it is kept on, or its outside **Provider:**) and
    each consumer."""
    external = contract.fact("Provider")
    parties = {_name(diagrams.external_name(external)) if external else contract.page.id}
    parties |= {app.id for app in vault.consumers(contract)}
    bullet = contract.facts.get("Consumers")
    for link in (bullet.links if bullet else ()):
        target = vault.resolve(link, contract.page)
        if target is None or target.type != "app-building-blocks":
            parties.add(_name(link.label or re.sub(r"^[A-Z]+-\d+\s+", "", link.anchor) or link.target))
    return parties


def passes_through(vault, flow_ids):
    """(app ids, contract ids) the named flows pass through, unioned, in first-seen order. Reads each step's
    sender and receiver (`endpoint`) and the contracts it links, then keeps only the vault's own apps and contracts:
    an outside party never counts, because the lead cannot build it."""
    wanted = {p.path for fid in flow_ids for p in vault.by_id.get(fid, ())}
    app_ids = {a.id for a in vault.apps}
    contract_ids = {c.id for c in vault.contracts}
    apps, contracts = [], []
    for step in steps(vault):
        if step.page.path not in wanted:
            continue
        for end in step.pair:
            key = endpoint(vault, step.page, end)
            if key in app_ids and key not in apps:
                apps.append(key)
        for contract in step.contracts:
            if contract.id in contract_ids and contract.id not in contracts:
                contracts.append(contract.id)
    return apps, contracts


APP, APP_PLAIN, PARTY, UNKNOWN = "app", "app written as plain text", "party", "unknown"


def outside_names(vault):
    """Lower-cased names of every outside party the plan knows: registered parties, and the providers and
    consumers its contracts name."""
    names = {_name(p.name) for p in vault.parties}
    for contract in vault.contracts:
        names |= {k for k in contract_parties(vault, contract) if not k.startswith("APP-")}
    return names


def end_kind(vault, page, text, outside):
    """How one end of a pair reads: APP, APP_PLAIN (an app named without a link), PARTY, or UNKNOWN (neither an app
    in the plan nor a party it knows)."""
    key = endpoint(vault, page, text)
    if key in {a.id for a in vault.apps}:
        return APP if parse.WIKILINK.search(text) else APP_PLAIN
    return PARTY if key in outside else UNKNOWN


def app_link(vault, page, text):
    """The link to write for an app named in plain text: [[rider-app-building-blocks|Rider app]]."""
    app = vault.by_id.get(endpoint(vault, page, text), ())
    return f"[[{app[0].name}|{' '.join(text.split())}]]" if app else ""


def lanes_named(vault, step):
    """Keys of the apps and outside parties a step's words name, linked or not, each once."""
    found = []
    text = step.raw
    for link in parse.links_in(text, step.line):
        target = vault.resolve(link, step.page)
        if target is not None and target.type == "app-building-blocks" and target.id not in found:
            found.append(target.id)
    text = parse.WIKILINK.sub(lambda m: " ", text)
    candidates = [(a.id, str(a.meta.get("title") or a.name)) for a in vault.apps]
    candidates += [(_name(p.name), p.name) for p in vault.parties]
    for key, word in candidates:
        flags = re.I if word[:1].islower() else 0
        if key not in found and re.search(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", text, flags):
            found.append(key)
    return found
