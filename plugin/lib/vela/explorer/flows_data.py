"""Each flow as a played sequence: lanes, the messages each step sends, and the open questions pinned to it.

Widened to every vault the explorer opens. Everything is read with the
vela's own parser and model. Two things the record does not say directly, each labeled on the page:

- Direction. A step that starts "Sender -> Receiver:" records it, and is "stated". Otherwise a step names a
  contract, not who sends to whom. A sentence such as "Rider app sends Dock service the code"
  names both ends, so the direction is "stated". Otherwise the page's own sequence diagram may draw the contract between
  two lanes (read once, by the flow checker's parser; a contract drawn between several pairs is picked by the lanes
  the sentence names, else not at all), and that pair is "stated". Last comes a guess, marked "inferred", that follows
  the contract's style: a request (an API a consumer calls) goes consumer to provider, because the consumer calls;
  a push (an event or a webhook, `c["push"]`, read from the contract's Delivery bullet or its own words) goes provider to
  consumer. When a contract has several consumers and the step names some of them, only those are drawn; when it
  names none, every consumer is drawn, because the record does not say which.
- Arrow words. One arrow, one label: the diagram's own words for that call ("Capacity check") or else the contract's
  title. The step's sentence shows once, on the step, never again under each of its arrows.
- Steps that link no contract in their text. A flow's "Contracts used" table can give a step its contracts; those
  messages are always "inferred", and the step says the contracts came from the table.

- Ends. Every sender and receiver a step records is an app or an outside party, and gets a lane. One the plan does
  not know (no link to an app page, no registered party) gets its own lane marked `gap`: the dashboard draws it dashed,
  "not in the plan", so the end is never dropped and never guessed. A recorded pair with no contract draws a plain
  arrow with `contract: ""`.
- Self and bands. A step is drawn as one lane's own action (`self`) only when its words name exactly one lane and it
  records no pair. A step that names two or more lanes and records no usable pair sets `unrecorded`: the dashboard draws
  a band with "who sends to whom isn't recorded", never an arrow from an app to itself.

An open question's state always comes from the unknown itself, never from the flow's prose: a sentence that still
calls an answered question open is flagged (textSaysOpen) and the marker shows the record's state.

Two more fields group a long list of flows in the picker (assets/js/flowpicker.js), both computed here so the page
only reads them:

- capabilities. The capabilities the flow serves: its `capabilities:` frontmatter (first is primary), else, as a
  guess, every capability its text links ("Uses [[CAP-002-...]]") in text order. capabilitiesFrom says which:
  "frontmatter", "steps" or "" (none), so the picker can mark a guessed group.
- domain. The domain most of the apps the flow crosses carry (a tie goes to the name that sorts first, so a rebuild
  never reshuffles the groups). "" when none of its apps names a domain.
"""
import re

from vela import flows as flow_steps, model
from . import starts_data
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
    ("Spokewell repairs" makes "repairs" mean Spokewell)."""
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
    contract named "Spokewell repairs" is not mistaken for a mention of Spokewell. Returns (text, [keys])."""
    from vela.parse import WIKILINK, parse_link
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


def lane_of(vault, keys, flow, end, words, outside=None):
    """The lane a step's recorded sender or receiver names: an app link by its key, an app written as plain text by
    its title, name or ID, anything else by the lane's whole name or alias; `outside` ({name: lane id}) holds the lanes of parties
    and gaps the plan does not draw from a contract. None when the end is on no lane."""
    from vela.parse import WIKILINK, parse_link
    found = WIKILINK.search(end)
    if found:
        link = parse_link(found.group(1), 0)
        target = vault.resolve(link, flow)
        if target is not None and target.type == "app-building-blocks":
            return keys.page(target)
        end = link_label(vault, link, flow)
    key = flow_steps.endpoint(vault, flow, end)
    app = next((a for a in vault.apps if a.id == key), None)
    if app is not None:
        return keys.page(app)
    if key in (outside or {}):
        return outside[key]
    # By the lane's whole name, as the check reads it: "FERRYMASTER vendor" is a party, not the FERRYMASTER app it mentions.
    return next((lane for lane, names in words.items() if key in {flow_steps._name(n) for n in names}), None)


def outside_lanes(vault, keys, lanes, words):
    """(lanes, {name: lane id}) for every recorded end that is on no lane yet: a registered party that no contract
    joins gets a party lane, and anything else gets a `gap` lane named as written. Sorted by name, so a rebuild never
    reshuffles them."""
    from vela.parse import WIKILINK, parse_link
    parties = {flow_steps._name(p.name): p for p in vault.parties}
    made, index = {}, {}
    for step in flow_steps.steps(vault):
        for end in step.pair:
            if lane_of(vault, keys, step.page, end, words, index) is not None:
                continue
            key = flow_steps.endpoint(vault, step.page, end)
            found = WIKILINK.search(end)
            written = link_label(vault, parse_link(found.group(1), 0), step.page) if found else plain(end)
            written = " ".join(flow_steps.PARENTHETICAL.sub("", written).split()) or written
            party = parties.get(key)
            lane = ({"id": party.id, "name": party.name, "kind": "partner"} if party is not None
                    else {"id": "gap:" + key, "name": written, "kind": "outside", "gap": True})
            made[lane["id"]] = lane
            index[key] = lane["id"]
    return sorted(made.values(), key=lambda l: (l["kind"] != "partner", l["name"].lower(), l["id"])), index


class Drawing:
    """The calls a flow page's sequence diagram draws, as {contract: [(from lane, to lane, words)]}, with a count of how
    many times each pair has been used so a contract drawn twice between the same lanes ("BKHOLD" then "BKCONF") hands its words
    out in the order the steps use it."""

    def __init__(self, calls=None):
        self.calls, self.used = {}, {}
        for frm, to, item, words in calls or ():
            if frm and to:
                self.calls.setdefault(item, []).append((frm, to, words))

    def words(self, item, frm, to):
        """The diagram's words for the next use of item between these two lanes (either way round), or ""."""
        mine = [w for f, t, w in self.calls.get(item, ()) if {f, t} == {frm, to}]
        if not mine:
            return ""
        k = self.used.get((item, frm, to), 0)
        self.used[(item, frm, to)] = k + 1
        return mine[min(k, len(mine) - 1)]

    def pair(self, item, named):
        """(from, to) the diagram draws item between, when it draws one pair, or one pair among several that the
        sentence's lanes single out; None otherwise."""
        pairs = list(dict.fromkeys((f, t) for f, t, _ in self.calls.get(item, ())))
        if len(pairs) > 1:
            pairs = [p for p in pairs if p[0] in named and p[1] in named] or [p for p in pairs if p[0] in named or p[1] in named]
        return pairs[0] if len(pairs) == 1 else None


def message(sentence, c, words, pair=(), drawing=None):
    """One or more messages for contract c cited in a sentence. A recorded sender and receiver (`pair`) wins over
    the verb, so a step that writes its arrow is always "stated"; then the verb; then the page's diagram; then a guess."""
    drawing = drawing or Drawing()
    parties = [c["provider"]] + c["consumers"]

    def stated(frm, to, kind):
        return [{"from": frm, "to": to, "contract": c["id"], "direction": "stated", "kind": kind, "words": drawing.words(c["id"], frm, to)}]
    if pair and pair[0] != pair[1] and pair[0] in parties and pair[1] in parties:
        verb = SEND_VERB.search(sentence)
        return stated(pair[0], pair[1], "request" if verb and verb.group(1) in REQUEST_VERBS else "send")
    named = mentions(sentence, words)
    verb = SEND_VERB.search(sentence)
    if verb:
        before = [lane for pos, lane in named if pos < verb.start() and lane in parties]
        after = [lane for pos, lane in named if pos > verb.end() and lane in parties]
        sender = before[0] if before else None
        receiver = next((lane for lane in after if lane != sender), None)
        if sender and receiver:
            return stated(sender, receiver, "request" if verb.group(1) in REQUEST_VERBS else "send")
    return inferred(c, [lane for _, lane in named], drawing)


def inferred(c, named, drawing=None):
    """What the step leaves unsaid. The diagram's pair when it draws one ("stated"); else a guess that follows the
    contract's style: a push goes provider to consumers, a request goes consumers to provider."""
    drawing = drawing or Drawing()
    drawn = drawing.pair(c["id"], set(named))
    if drawn:
        return [{"from": drawn[0], "to": drawn[1], "contract": c["id"], "direction": "stated", "kind": "send",
                 "words": drawing.words(c["id"], *drawn)}]
    consumers = [k for k in c["consumers"] if k != c["provider"]]
    if not consumers:
        return []
    chosen = [k for k in consumers if k in named] or consumers
    if c.get("push"):
        return [{"from": c["provider"], "to": k, "contract": c["id"], "direction": "inferred", "kind": "send", "words": ""} for k in chosen]
    return [{"from": k, "to": c["provider"], "contract": c["id"], "direction": "inferred", "kind": "send", "words": ""} for k in chosen]


def labeled(m, c):
    """The message as the page reads it: the words under its arrow are the diagram's own for that call, else the contract's
    title, never the step's sentence. The diagram's words are consumed here."""
    words = m["words"]
    return {**{k: v for k, v in m.items() if k != "words"}, "says": (words[:1].upper() + words[1:]) if words else c["title"], "answer": ""}


def short_caption(text, tokens, contracts, limit=130):
    """The first sentence, without "over <contract>" (the arrow carries it), cut at a clause if still long (limit
    None keeps it whole). For present mode and clips, where a step is on screen for about two seconds."""
    parts = sentences(text) or [text]
    first = parts[0]
    if re.fullmatch(r"«\d+»[.:]?", first.strip()) and len(parts) > 1:
        first = first.rstrip(".:") + ". " + parts[1]  # "Hold a seat." alone says nothing: keep the sentence after
    drop = lambda m: "" if tokens[int(m.group(2))]["key"] in contracts else m.group(0)
    first = re.sub(r",?\s*\b(over|using|through|via)\s+«(\d+)»", drop, first)
    first = re.sub(r"«(\d+)»", lambda m: tokens[int(m.group(1))]["label"], first)
    first = re.sub(r"\s+([,.])", r"\1", first).strip()
    if limit and len(first) > limit:
        cut = max(first.rfind(", and", 0, limit), first.rfind(", which", 0, limit), first.rfind(", so", 0, limit), first.rfind("; ", 0, limit))
        first = first[:cut] + "." if cut > 40 else first[:limit - 3].rsplit(" ", 1)[0] + " …"
    return first


PAIR_PREFIX = re.compile(r"^[^:→]{1,80}(?:→|->)[^:]{1,80}:\s+")
ANSWER_CLAUSE = re.compile(r",?\s+and\s+(?:then\s+)?((?:gets|receives|returns|hears|answers)\b.*)$", re.I)


def arrow_words(sentence, tokens, contracts):
    """(what the arrow does, what the answer coming back says) for the explorer's arrow labels. The sentence whole, with
    no sender-to-receiver prefix (the arrow draws that) and no "over <contract>" (the pill names it). When the sentence
    says "... and gets a reading token", that clause is the reply's own words and the call keeps the rest. No cut: the
    canvas wraps what it is given."""
    text = PAIR_PREFIX.sub("", short_caption(sentence, tokens, contracts, limit=None)).rstrip(".").strip()
    found = ANSWER_CLAUSE.search(text)
    if not found:
        return text, ""
    return text[:found.start()].strip(), found.group(1).strip()


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


def capabilities_of(vault, keys, flow):
    """(capability keys, where they came from) for a flow. The `capabilities:` frontmatter is the record and wins,
    first one primary; with none, the capabilities its text links ("Uses [[CAP-...]]") are a guess, in text order."""
    known = {keys.page(p) for p in vault.of_type("capability")}
    value = flow.meta.get("capabilities")
    declared = [v for v in (value if isinstance(value, list) else [value]) if isinstance(v, str) and v in known]
    if declared:
        return list(dict.fromkeys(declared)), "frontmatter"
    cited = [k for k in dict.fromkeys(refs_in(flow.text, keys, flow)) if k in known]
    return cited, "steps" if cited else ""


def domain_of(steps, app_domains):
    """The most common domain among the apps a flow's messages cross (or sit inside); "" when none names one."""
    counts = {}
    for step in steps:
        ends = [m[end] for m in step["messages"] for end in ("from", "to")] + ([step["self"]] if step["self"] else [])
        for end in ends:
            if app_domains.get(end):
                counts[app_domains[end]] = counts.get(app_domains[end], 0) + 1
    return min(counts, key=lambda d: (-counts[d], d)) if counts else ""


def flow_record(vault, keys, flow, contracts_by_id, lanes, words, blockers, names, outside=None, drawing=None):
    drawing = drawing or Drawing()
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
            pair = tuple(lane_of(vault, keys, flow, e, words, outside) for e in ends) if ends else ()
            messages, pins, cited = [], [], []
            for sentence in sentences(text):
                for tok in re.findall(r"«(\d+)»", sentence):
                    key = tokens[int(tok)]["key"]
                    item = vault.item(key) if key else None
                    if key in contracts_by_id:
                        cited.append(key)
                        messages += [labeled(m, contracts_by_id[key])
                                     for m in message(sentence, contracts_by_id[key], words, pair, drawing)]
                    elif item is not None and item.kind == "unknown" and key not in [p["id"] for p in pins]:
                        pins.append({"id": key, "why": "cited", "textSaysOpen": bool(OPEN_WORDS.search(sentence))})
            named_here = [lane for _, lane in mentions(text, words)]
            lanes_named = list(dict.fromkeys(named_here))
            table_only = [k for k in dict.fromkeys(from_table.get(number, [])) if k in contracts_by_id and k not in cited]
            first_says, _ = arrow_words(text, tokens, contracts_by_id)
            for key in table_only:
                messages += [labeled(m, contracts_by_id[key]) for m in inferred(contracts_by_id[key], named_here, drawing)]
            seen, unique = set(), []
            for m in messages:
                sig = (m["from"], m["to"], m["contract"])
                if sig not in seen:
                    seen.add(sig)
                    unique.append(m)
            usable = len(pair) == 2 and all(pair) and pair[0] != pair[1]
            if not unique and usable:  # a recorded pair is drawn even when the step names no contract
                unique = [{"from": pair[0], "to": pair[1], "contract": "", "direction": "stated", "kind": "send", "says": first_says, "answer": ""}]
            alone = lanes_named[0] if not unique and not ends and len(lanes_named) == 1 else None
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
                "n": number, "html": inline_html(raw, keys, flow), "text": visible, "short": short_caption(text, tokens, contracts_by_id), "says": first_says,
                "messages": unique, "self": alone, "recordsPair": bool(ends), "lanesNamed": len(lanes_named),
                "unrecorded": not unique and alone is None and (len(lanes_named) > 1 or bool(ends)),
                "ref": refs[0] if refs else None, "unknowns": pins,
                "contracts": list(dict.fromkeys(cited + table_only)), "linked": linked, "named": named,
                "fromTable": bool(table_only),
            })
    intro_pins = [k for k in dict.fromkeys(refs_in(flow.text.split("## Steps", 1)[0], keys, flow))
                  if vault.item(k) is not None and vault.item(k).kind == "unknown"]
    for u in blockers.get(flow.id, []):
        if u.id not in intro_pins:
            intro_pins.append(u.id)
    caps, caps_from = capabilities_of(vault, keys, flow)
    return {"key": keys.page(flow), "steps": steps, "unknowns": intro_pins,
            "refs": list(dict.fromkeys(refs_in(flow.text, keys, flow))), "capabilities": caps, "capabilitiesFrom": caps_from}


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


def flows(vault, keys, contracts, pins, names, catalog=None):
    """{"lanes": [...], "flows": [...]} for every FLO page, with each flow's journey for the line map. `catalog` is the
    flow checker's read of the vault: with it, a contract the page's sequence diagram draws gets the diagram's sender and receiver."""
    by_id = {c["id"]: c for c in contracts}
    lanes = lanes_of(vault, keys, contracts, pins, names)
    extra, outside = outside_lanes(vault, keys, lanes, aliases(lanes, contracts))
    lanes += extra
    words = aliases(lanes, contracts)
    blockers = model.blockers(vault)
    by_name = {l["name"].lower(): l["id"] for l in lanes}
    app_domains = {keys.page(a): str(a.meta.get("domain") or "").strip() for a in vault.apps}
    out = []
    for page in sorted(vault.of_type("flow"), key=lambda p: p.id):
        drawing = Drawing(starts_data.drawn_calls(vault, keys, catalog, page, by_name)) if catalog is not None else Drawing()
        record = flow_record(vault, keys, page, by_id, lanes, words, blockers, names, outside, drawing)
        record["domain"] = domain_of(record["steps"], app_domains)
        record["groups"] = (starts_data.default_groups(vault, keys, catalog, page, by_name, {l["id"] for l in lanes})
                            if catalog is not None else [])
        record["hops"], record["segments"] = journey(record["steps"], by_id)
        out.append(record)
    return {"lanes": lanes, "flows": out}
