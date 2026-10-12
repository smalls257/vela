"""Each flow as a played sequence: lanes, the messages each step sends, and the open questions pinned to it.

Ported from prototypes/gallery/flows/extract.py and widened to the explorer's vaults. Everything is read with the
planner's own parser and model. Two things the record does not say directly, each labelled on the page:

- Direction. A step that starts "Sender -> Receiver:" records it, and is "stated". Otherwise a step names a
  contract, not who sends to whom. A sentence such as "TickerTalk sends Coach the ID"
  names both ends, so the direction is "stated". Otherwise the sender is the contract's provider and the receivers
  its consumers, marked "inferred". When a contract has several consumers and the step names some of them, only
  those receive; when it names none, every consumer is drawn, because the record does not say which.
- Steps that link no contract in their text. A flow's "Contracts used" table can give a step its contracts; those
  messages are always "inferred", and the step says the contracts came from the table.

An open question's state always comes from the unknown itself, never from the flow's prose: a sentence that still
calls an answered question open is flagged (textSaysOpen) and the marker shows the record's state.
"""
import re

from planner import flows as flow_steps, model
from .record import STEP, inline_html, link_label, plain, refs_in

SEND_VERB = re.compile(r"\b(sends|asks|calls|reports|writes|publishes|tells)\b")
REQUEST_VERBS = ("asks", "calls")
OPEN_WORDS = re.compile(r"\b(still open|not decided|until|is open|not yet)\b", re.I)


def lanes_of(vault, keys, contracts, pins, names):
    """Every app, then every outside party a contract joins, in the map's left-to-right order, so a lane sits
    where its station sits on the map."""
    used = {c["provider"] for c in contracts} | {k for c in contracts for k in c["consumers"]}
    lanes = [{"id": keys.page(a), "name": names[keys.page(a)], "kind": "app"} for a in vault.apps]
    lanes += [{"id": k, "name": names[k], "kind": "partner"} for k in sorted(used) if k in names and not k.startswith("APP")
              and k not in {l["id"] for l in lanes}]
    lanes = [l for l in lanes if l["kind"] == "app" or l["id"] in used]
    at = lambda l: tuple(pins.get(l["id"], [99, 99]))
    return sorted(lanes, key=lambda l: (l["kind"] != "app", at(l)[0], at(l)[1], l["id"]))


def aliases(lanes, contracts):
    """Words that name a lane in step prose: its name, and a partner contract's name minus the partner's name
    ("Brightwater sandbox" makes "sandbox" mean Brightwater)."""
    out = {l["id"]: [l["name"]] for l in lanes}
    for c in contracts:
        lane = next((l for l in lanes if l["id"] == c["provider"] and l["kind"] == "partner"), None)
        if lane and c["title"].startswith(lane["name"] + " "):
            out[lane["id"]].append(c["title"][len(lane["name"]) + 1:])
    return out


def mentions(sentence, words):
    found = []
    for lane_id, names in words.items():
        for word in names:
            flags = re.I if word[:1].islower() else 0
            for m in re.finditer(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", sentence, flags):
                found.append((m.start(), lane_id))
    return sorted(found)


def masked(text, keys, page, vault):
    """The step as plain text where app links read as the app's name and every other link is a «n» token, so a
    contract named "Brightwater sandbox" is not mistaken for a mention of Brightwater. Returns (text, [keys])."""
    from planner.parse import WIKILINK, parse_link
    tokens = []

    def swap(m):
        link = parse_link(m.group(1), 0)
        key = keys.link(link, page)
        target = vault.resolve(link, page)
        if target is not None and target.type == "app-building-blocks" and key == keys.page(target):
            return str(target.meta.get("title") or target.name)
        tokens.append({"key": key, "label": link_label(vault, link, page)})
        return f"«{len(tokens) - 1}»"
    return plain(WIKILINK.sub(swap, text)), tokens


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z«\[])", text.strip()) if s]


def lane_of(vault, keys, flow, end, words):
    """The lane a step's recorded sender or receiver names: an app link by its key, anything else by the lane name."""
    from planner.parse import WIKILINK, parse_link
    found = WIKILINK.search(end)
    if found:
        link = parse_link(found.group(1), 0)
        target = vault.resolve(link, flow)
        if target is not None and target.type == "app-building-blocks":
            return keys.page(target)
        end = link_label(vault, link, flow)
    named = mentions(plain(end), words)
    return named[0][1] if named else None


def message(sentence, c, words, pair=()):
    """One or more messages for contract c cited in a sentence. A recorded sender and receiver (`pair`) wins over
    the verb, so a step that writes its arrow is always "stated"."""
    parties = [c["provider"]] + c["consumers"]
    if pair and pair[0] != pair[1] and pair[0] in parties and pair[1] in parties:
        verb = SEND_VERB.search(sentence)
        kind = "request" if verb and verb.group(1) in REQUEST_VERBS else "send"
        return [{"from": pair[0], "to": pair[1], "contract": c["id"], "direction": "stated", "kind": kind}]
    named = mentions(sentence, words)
    verb = SEND_VERB.search(sentence)
    if verb:
        before = [lane for pos, lane in named if pos < verb.start() and lane in parties]
        after = [lane for pos, lane in named if pos > verb.end() and lane in parties]
        sender = before[0] if before else None
        receiver = next((lane for lane in after if lane != sender), None)
        if sender and receiver:
            kind = "request" if verb.group(1) in REQUEST_VERBS else "send"
            return [{"from": sender, "to": receiver, "contract": c["id"], "direction": "stated", "kind": kind}]
    return inferred(c, [lane for _, lane in named])


def inferred(c, named):
    consumers = [k for k in c["consumers"] if k != c["provider"]]
    if not consumers:
        return []
    chosen = [k for k in consumers if k in named] or consumers
    return [{"from": c["provider"], "to": k, "contract": c["id"], "direction": "inferred", "kind": "send"} for k in chosen]


def short_caption(text, tokens, contracts):
    """The first sentence, without "over <contract>" (the arrow carries it), cut at a clause if still long. For
    present mode and clips, where a step is on screen for about two seconds."""
    parts = sentences(text) or [text]
    first = parts[0]
    if re.fullmatch(r"«\d+»[.:]?", first.strip()) and len(parts) > 1:
        first = first.rstrip(".:") + ". " + parts[1]  # "Hold a seat." alone says nothing: keep the sentence after
    drop = lambda m: "" if tokens[int(m.group(2))]["key"] in contracts else m.group(0)
    first = re.sub(r",?\s*\b(over|using|through|via)\s+«(\d+)»", drop, first)
    first = re.sub(r"«(\d+)»", lambda m: tokens[int(m.group(1))]["label"], first)
    first = re.sub(r"\s+([,.])", r"\1", first).strip()
    if len(first) > 130:
        cut = max(first.rfind(", and", 0, 130), first.rfind(", which", 0, 130), first.rfind(", so", 0, 130), first.rfind("; ", 0, 130))
        first = first[:cut] + "." if cut > 40 else first[:127].rsplit(" ", 1)[0] + " …"
    return first


def table_contracts(flow, keys):
    """{step number: [contract keys]} from the flow's "Contracts used" table."""
    out = {}
    for table in flow.tables:
        if table.generated or not table.header or table.header[0].strip().lower() != "step":
            continue
        for row in table.rows:
            number = re.match(r"\s*(\d+)", row[0]) if row else None
            if number:
                out.setdefault(int(number.group(1)), []).extend(refs_in(" | ".join(row[1:]), keys, flow))
    return out


def next_heading(page, after):
    return next((h.line for h in page.headings if h.line > after and h.level <= 2), len(page.text.split("\n")) + 1)


def flow_record(vault, keys, flow, contracts_by_id, lanes, words, blockers, names):
    steps_heading = next((h for h in flow.headings if h.level == 2 and h.text.strip().lower() == "steps"), None)
    lines = flow.text.split("\n")
    from_table = table_contracts(flow, keys)
    lane_ids = {l["id"] for l in lanes}
    title_names = sorted(((k, v) for k, v in names.items() if k in lane_ids), key=lambda kv: -len(kv[1]))
    steps, pinned = [], set()
    if steps_heading is not None:
        for n in range(steps_heading.line + 1, next_heading(flow, steps_heading.line)):
            match = STEP.match(lines[n - 1].strip())
            if not match:
                continue
            number, raw = int(match.group(1)), match.group(2)
            text, tokens = masked(raw, keys, flow, vault)
            ends = flow_steps.split_pair(raw)
            pair = tuple(lane_of(vault, keys, flow, e, words) for e in ends) if ends else ()
            messages, pins, cited = [], [], []
            for sentence in sentences(text):
                for tok in re.findall(r"«(\d+)»", sentence):
                    key = tokens[int(tok)]["key"]
                    item = vault.item(key) if key else None
                    if key in contracts_by_id:
                        cited.append(key)
                        messages += message(sentence, contracts_by_id[key], words, pair)
                    elif item is not None and item.kind == "unknown" and key not in [p["id"] for p in pins]:
                        pins.append({"id": key, "why": "cited", "textSaysOpen": bool(OPEN_WORDS.search(sentence))})
            named_here = [lane for _, lane in mentions(text, words)]
            table_only = [k for k in dict.fromkeys(from_table.get(number, [])) if k in contracts_by_id and k not in cited]
            for key in table_only:
                messages += inferred(contracts_by_id[key], named_here)
            seen, unique = set(), []
            for m in messages:
                sig = (m["from"], m["to"], m["contract"])
                if sig not in seen:
                    seen.add(sig)
                    unique.append(m)
            for m in unique:
                for u in blockers.get(m["contract"], []):
                    if u.fact("State") == "open" and u.id not in pinned and u.id not in [p["id"] for p in pins]:
                        pins.append({"id": u.id, "why": "holds " + m["contract"], "textSaysOpen": False})
            pinned |= {p["id"] for p in pins}
            visible = plain(raw)
            linked = [k for k in dict.fromkeys(refs_in(raw, keys, flow)) if k not in contracts_by_id]
            refs = [k for k in linked if (vault.item(k) is None) and any(p.type == "flow" and keys.page(p) == k for p in vault.of_type("flow"))]
            named = [k for k, t in title_names if re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", visible)]
            steps.append({
                "n": number, "html": inline_html(raw, keys, flow), "text": visible, "short": short_caption(text, tokens, contracts_by_id),
                "messages": unique, "self": None if unique else (named_here[0] if named_here else None),
                "ref": refs[0] if refs else None, "unknowns": pins,
                "contracts": list(dict.fromkeys(cited + table_only)), "linked": linked, "named": named,
                "fromTable": bool(table_only),
            })
    intro_pins = [k for k in dict.fromkeys(refs_in(flow.text.split("## Steps", 1)[0], keys, flow))
                  if vault.item(k) is not None and vault.item(k).kind == "unknown"]
    for u in blockers.get(flow.id, []):
        if u.id not in intro_pins:
            intro_pins.append(u.id)
    return {"key": keys.page(flow), "steps": steps, "unknowns": intro_pins,
            "refs": list(dict.fromkeys(refs_in(flow.text, keys, flow)))}


def journey(steps, contracts_by_id):
    """The order a train visits stations on the line map: each step's contract ends, consumer first, joined over
    the line's own track. Returns (hops, segments). Ported from the gallery's maps/extract.py."""
    segments, adj = [], {}
    for step in steps:
        for cid in step["contracts"]:
            c = contracts_by_id[cid]
            for consumer in c["consumers"]:
                if consumer == c["provider"]:
                    continue
                seg = (c["provider"], consumer, cid)
                if seg not in segments:
                    segments.append(seg)
                adj.setdefault(c["provider"], set()).add(consumer)
                adj.setdefault(consumer, set()).add(c["provider"])

    def shortest(start, goal):
        frontier, seen = [[start]], {start}
        while frontier:
            path = frontier.pop(0)
            if path[-1] == goal:
                return path
            for nxt in sorted(adj.get(path[-1], ())):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(path + [nxt])
        return None

    hops, here = [], None
    for step in steps:
        for cid in step["contracts"]:
            c = contracts_by_id[cid]
            consumer = c["consumers"][0] if c["consumers"] else c["provider"]
            if here is None:
                here = consumer
            for stop in (consumer, c["provider"]):
                if stop == here:
                    continue
                path = shortest(here, stop) or [here, stop]
                for a, b in zip(path, path[1:]):
                    hops.append({"from": a, "to": b, "step": step["n"], "contracts": [cid]})
                here = stop
    return hops, [{"a": a, "b": b, "contract": cid} for a, b, cid in segments]


def flows(vault, keys, contracts, pins, names):
    """{"lanes": [...], "flows": [...]} for every FLO page, with each flow's journey for the line map."""
    by_id = {c["id"]: c for c in contracts}
    lanes = lanes_of(vault, keys, contracts, pins, names)
    words = aliases(lanes, contracts)
    blockers = model.blockers(vault)
    out = []
    for page in sorted(vault.of_type("flow"), key=lambda p: p.id):
        record = flow_record(vault, keys, page, by_id, lanes, words, blockers, names)
        record["hops"], record["segments"] = journey(record["steps"], by_id)
        out.append(record)
    return {"lanes": lanes, "flows": out}
