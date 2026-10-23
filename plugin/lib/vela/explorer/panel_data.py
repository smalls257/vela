"""What the right-hand panel says about a team's design, worked out ahead of the page so it can be tested without a browser.

    panels(vault, data) -> {app key: {summary, components, contracts, waiting, flows, links}}

The Violation this module's shape prevents is a Leaky Narrative: a panel that shows `CON-002` or `EPC-033.AC4` makes a
reader open the vault to learn what the team meant. Every name here is said in the vault's own words by `Namer`, and an
ID that the plan cannot name is said by its kind ("a contract the plan doesn't list"), never left bare. IDs still travel,
under keys called `id` or `key`, because a link needs them; no other string carries one.

The second thing it prevents is an invented link (a Paper Tiger that draws a tidy panel the design never wrote). Each
list is built only from what the design records:
- a component's open questions are the ones whose Affects line names it;
- its flows are the key flows whose sequence names it as a participant;
- what it delivers is the design's trace (recorded, or guessed from mentions, and `traceSource` says which);
- a decision or a risk is never tied to a component, because the design's risk and decision tables have no component column.
A section the design lacks is `None` or an empty list, and the page says "Not recorded"; nothing is filled in.
"""
import re

from vela import cases, criteria, trace

from . import branches_data, inside_data
from .record import title_of

SEVERITY = {"high": 0, "critical": 0, "medium": 1, "med": 1, "low": 2}
VAULT_ID = re.compile(r"\b(?:CAP-\d{3}\.FR\d+|EPC-\d{3}(?:\.AC\d+|\s+AC\d+)?|CAP-\d{3}|CON-\d{3}|UNK-\d{3}|CST-\d+|PTY-\d{2,3}|SV-\d{2,3}|FLO-\d{3}|APP-[a-z0-9-]+)(?:@APP-[a-z0-9-]+)?")
LOCAL_ID = re.compile(r"\b(?:OQ-\d{3}|D-\d{3}|ADR-\d{4})\b")
KIND_WORD = {"CON": "a contract", "UNK": "an open question", "CAP": "a capability", "EPC": "an epic", "CST": "a constraint",
             "PTY": "an outside party", "SV": "a stored value", "FLO": "a flow", "APP": "an app"}
SECTIONS = [("overview", "Overview"), ("coverage", "Coverage"), ("data", "Data model"), ("api", "API contracts"), ("flows", "Key flows"),
            ("stack", "Tech stack"), ("nfrs", "Quality targets"), ("constraints", "Constraints"), ("risks", "Risks"),
            ("adrs", "Design decisions"), ("ops", "Operations"), ("glossary", "Glossary")]


def plain(text):
    """Markdown the design wrote, said as plain words: no bold marks, no link syntax. Backticks stay; the page shows them as code."""
    text = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", str(text or ""))
    return re.sub(r"\*\*|__", "", text).strip()


def short(text, limit=72):
    """The first clause that fits: cut at a sentence end, else at a word, and say so with an ellipsis."""
    text = " ".join(plain(text).split())
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].rstrip(".")
    if len(first) <= limit:
        return first
    cut = first[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


class Namer:
    """Says a vault ID, or one of the design's own (OQ, D, ADR), by name."""

    def __init__(self, vault, design=None):
        self.vault = vault
        self.epics = {e.id: e for e in trace.epics(vault)}
        self.criteria = {}
        self.local = {}
        if design:
            for q in design["open_questions"]:
                self.local[q["id"]] = short(q["title"], 60)
            for d in design["frontmatter"].get("deferred", []):
                self.local[d["id"]] = short(d.get("reason", ""), 56)
            for a in design["adrs"]:
                self.local[a["id"]] = short(a.get("adr_title") or a.get("title") or "", 44)

    def _criterion(self, epic_id, n):
        if epic_id not in self.criteria:
            epic = self.epics.get(epic_id)
            self.criteria[epic_id] = {c.n: c for c in criteria.read(epic)} if epic is not None else {}
        return self.criteria[epic_id].get(n)

    def _row(self, ident):
        """The second cell of the vault table row that opens with `ident` (a constraint's own words), if there is one."""
        found = self.vault.row_ids.get(ident)
        if not found:
            return ""
        page, line = found
        for table in page.tables:
            if line in table.row_lines:
                cells = table.rows[table.row_lines.index(line)]
                return short(cells[1], 56) if len(cells) > 1 else ""
        return ""

    def name(self, ident):
        """The name for an ID, or "" when the plan has none."""
        base = ident.split("@")[0]
        if base in self.local:
            return self.local[base]
        ac = re.fullmatch(r"(EPC-\d{3})[. ]AC(\d+)", base)
        if ac:
            c = self._criterion(ac.group(1), int(ac.group(2)))
            return short(c.heading or c.text, 64) if c else ""
        epic = self.epics.get(base)
        if epic is not None:
            return title_of(epic)
        if base.startswith("CST-"):
            return self._row(base)
        named = self.vault.name_of(base)
        return "" if named == base else named

    def say(self, text):
        """`text` with every ID replaced by its name. A name the text already spells out right after the ID ("CON-003 Consent
        check", "D-001 spike") is not said twice."""
        text = plain(text)

        def swap(match):
            ident, word = match.group(1), match.group(2) or ""
            name = self.name(ident)
            if not name:
                kind = ident.split("-")[0]
                return KIND_WORD.get(kind, "an item") + ("" if kind == "APP" else " the plan doesn't list") + (" " + word if word else "")
            tail = text[match.end(1):].lstrip().lower()
            if tail.startswith(name.lower().rstrip("…")):
                return word  # the ID goes; the words the text already has stay
            if word and name.lower().rstrip("…").endswith(word.lower()):
                return name
            return name + (" " + word if word else "")
        pattern = re.compile(rf"({VAULT_ID.pattern}|{LOCAL_ID.pattern})(?:[ ]+([A-Za-z]+))?")
        out = pattern.sub(swap, text)
        return re.sub(r"\s{2,}", " ", re.sub(r"\(\s*\)", "", out)).strip()


def _first_paragraph(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return paras[0] if paras else ""


def opening(text, limit=260):
    """The first sentences of `text` that fit `limit`, whole: a card at a glance says what it is, the section says the rest."""
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(str(text or "").split()))
    out = ""
    for sentence in sentences:
        if out and len(out) + len(sentence) + 1 > limit:
            break
        out = f"{out} {sentence}".strip()
    return out


def _mentions(text, name):
    return bool(re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text or "", re.I))


def _table_rows(raw):
    """[[cells]] of a markdown table in `raw`, header and rule rows dropped."""
    rows = []
    for line in str(raw or "").split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows[1:]


def failure_rows(design):
    """[(contract IDs in the call cell, call, when, does)] from the API contracts section's failure table, if the design has one."""
    out = []
    for api in design["api"]:
        for cells in _table_rows(api["raw"]):
            if len(cells) >= 3 and re.search(r"CON-\d{3}", cells[0]):
                out.append((re.findall(r"CON-\d{3}", cells[0]), cells[0], cells[1], cells[2]))
    return out


def sequence_participants(mermaid):
    """The names a sequence diagram's participants go by: 'participant V as NoteView' is NoteView; a bare one is its id."""
    names = []
    for line in str(mermaid or "").split("\n")[1:]:
        m = re.match(r"\s*(?:participant|actor)\s+(\S+)(?:\s+as\s+(.+?))?\s*$", line)
        if m:
            names.append((m.group(2) or m.group(1)).strip())
    return names


def untitled_flow(flow, index):
    """A flow the design did not title is named by what happens first in it, so the name is the design's, not a guess."""
    first = re.search(r"-{1,2}>>?[+-]?\s*[^:\n]+:\s*(.+)", str(flow.get("mermaid") or ""))
    return f"Key flow {index + 1}: {first.group(1).strip()}" if first else f"Key flow {index + 1}"


def design_flows(design, namer):
    """Each key flow: its title, the participants, and the vault flow it names (FLO-nnn in its title), if any."""
    out = []
    for i, f in enumerate(design["flows"]):
        who = sequence_participants(f["mermaid"]) if f.get("kind") == "sequenceDiagram" else []
        flo = re.search(r"\bFLO-\d{3}\b", f.get("title") or "")
        title = namer.say(f.get("title") or "") or untitled_flow(f, i)
        out.append({"index": i, "title": title, "who": who, "flow": flo.group(0) if flo else None,
                    "line": f.get("line")})
    return out


def waiting(design, namer, comps):
    out = []
    for q in design["open_questions"]:
        affects = q.get("affects", "")
        holds = [c for c in comps if _mentions(affects, c)]
        words = [w.strip() for w in plain(namer.say(affects)).split(",") if w.strip()]
        out.append({"id": q["id"], "question": namer.say(q["title"]), "knows": namer.say(q.get("what_we_know", "")),
                    "unblocks": namer.say(q.get("what_would_unblock", "")), "holds": holds,
                    "alsoAffects": [w for w in words if w not in holds and w.rstrip(".") not in holds]})
    return out


def delivers(design, namer, component):
    entries = design["trace"].get(component, [])
    out = {"requirements": [], "contracts": [], "criteria": [], "other": [], "total": len(entries)}
    by_epic = {}
    for e in entries:
        ident = e["id"].split("@")[0]
        if re.fullmatch(r"CAP-\d{3}\.FR\d+", ident):
            out["requirements"].append(namer.name(ident) or namer.say(ident))
        elif ident.startswith("CON-"):
            out["contracts"].append({"id": ident, "name": namer.name(ident) or namer.say(ident)})
        elif re.fullmatch(r"EPC-\d{3}\.AC\d+", ident):
            by_epic.setdefault(ident.split(".")[0], []).append(namer.name(ident) or namer.say(ident))
        else:
            out["other"].append(namer.say(ident))
    out["criteria"] = [{"epic": namer.name(epic) or namer.say(epic), "items": items} for epic, items in by_epic.items()]
    return out


def depends_text(design, namer, c):
    """What a component depends on, as segments: plain text, with a link wherever the text names a component or an outside system."""
    text = namer.say(c["depends_on"])
    names = [(n, "component") for n in (x["name"] for x in design["components"]) if n != c["name"]]
    systems = []
    for s in design.get("stubs", []):
        bare = inside_data._bare(s["system"])
        shown = re.sub(r"\s*\(.*?\)", "", s["system"]).strip()
        if bare:
            systems.append((shown, "outside"))
    parts, rest = [], text
    found = sorted(((m.start(), m.end(), n, kind) for n, kind in names + systems for m in re.finditer(rf"(?<![\w-]){re.escape(n)}(?![\w-])", rest, re.I)),
                   key=lambda t: (t[0], -(t[1] - t[0])))
    at = 0
    for start, end, n, kind in found:
        if start < at:
            continue
        if start > at:
            parts.append({"text": rest[at:start]})
        parts.append({"text": rest[start:end], "link": {"kind": kind, "name": n}})
        at = end
    if at < len(rest):
        parts.append({"text": rest[at:]})
    return parts or [{"text": text}]


def stub_lines(design, namer, stubs):
    """For each outside system: which component reaches it over which contracts, one line to draw per component."""
    owner = {}
    for comp, entries in design["trace"].items():
        for e in entries:
            if e["id"].startswith("CON-") and comp != "Operations":
                owner.setdefault(e["id"], comp)
    out = []
    for i, s in enumerate(stubs):
        by = {}
        for cid in s["contracts"]:
            by.setdefault(owner.get(cid) or s["component"], []).append(cid)
        if not s["contracts"] and s["component"]:
            by[s["component"]] = []
        lines = [{"component": comp, "contracts": [{"id": cid, "name": namer.name(cid) or namer.say(cid)} for cid in ids]}
                 for comp, ids in by.items() if comp]
        out.append({"index": i, "name": re.sub(r"\s*\(.*?\)", "", namer.say(s["system"])).strip(), "lines": lines,
                    "connection": {"direction": s["direction"] or None, "protocol": namer.say(s["protocol"]) or None, "auth": namer.say(s["auth"]) or None}})
    return out


def contract_details(design, namer, data, stubs):
    """Each contract the design connects to, with who provides and calls it, the ways it answers, and the connection."""
    nodes = {n["key"]: n["title"] for n in data["nodes"]}
    plan = {c["id"]: c for c in data["map"]["contracts"]}
    fails = failure_rows(design)
    out = {}
    for s in stubs:
        for cid in s["contracts"]:
            if cid in out:
                continue
            p = plan.get(cid, {})
            provider_key = p.get("provider") or ""
            owners = [c for c, entries in design["trace"].items() if any(e["id"] == cid for e in entries) and c != "Operations"]
            callers = owners or ([s["component"]] if s["component"] else [])
            answers = [{"when": plain(when), "does": namer.say(does)} for ids, call, when, does in fails if cid in ids]
            out[cid] = {
                "id": cid, "name": namer.name(cid) or namer.say(cid),
                "provider": {"name": nodes.get(provider_key) or re.sub(r"\s*\(.*?\)", "", namer.say(s["system"])).strip(),
                             "key": provider_key if provider_key.startswith("APP-") and provider_key in nodes else None},
                "callers": callers,
                "crosses": plain(p.get("crosses", "")) or None,
                "answers": answers,
                "connection": {"system": re.sub(r"\s*\(.*?\)", "", namer.say(s["system"])).strip(), "direction": s["direction"] or None,
                               "protocol": namer.say(s["protocol"]) or None, "auth": namer.say(s["auth"]) or None},
                "waiting": [q["id"] for q in design["open_questions"] if cid in q.get("affects_ids", []) or cid in q.get("challenges", [])
                            or _mentions(q.get("affects", ""), cid)],
            }
    return out


def summary(design, namer, app_title, untraced_names):
    risks = sorted(design["risks"], key=lambda r: SEVERITY.get(str(r.get("severity", "")).strip().lower(), 3))
    high = [r for r in design["risks"] if SEVERITY.get(str(r.get("severity", "")).strip().lower()) == 0]
    stack = [plain(r.get("choice", "")) for r in design["tech_stack"] if r.get("choice")]
    what = _first_paragraph((design["summary"] or {}).get("text")) or _first_paragraph(design["overview"].get("text"))
    counts = {"overview": None, "coverage": sum(len(v) for v in design["trace"].values()) or None, "data": len(design["data_model"]["entities"]) or None,
              "api": len(design["api"]) or None, "flows": len(design["flows"]) + len(design["diagrams"]) or None,
              "stack": len(design["tech_stack"]) or None, "nfrs": len(design["nfrs"]) or None, "constraints": len(design["constraints"]) or None,
              "risks": len(design["risks"]) or None, "adrs": len(design["adrs"]) or None, "ops": None,
              "glossary": len(design["context"]["glossary"]) if design.get("context") else None}
    gaps = [{"name": n, "known": known, "why": why} for n, known, why in untraced_names]
    for g in design["frontmatter"]["gaps"]:
        gaps.append({"name": namer.say(g.get("what", "")), "known": True, "why": namer.say(g.get("why", "")) or None})
    for d in design["frontmatter"].get("deferred", []):
        gaps.append({"name": f"Deferred: {namer.say(d.get('section', ''))}", "known": True, "why": namer.say(d.get("reason", "")) or None})
    return {
        "app": app_title, "what": opening(namer.say(what)) if what else None,
        "stack": " · ".join(stack) if stack else None,
        "risks": {"total": len(design["risks"]), "high": len(high),
                  "top": [{"risk": namer.say(r.get("risk", "")), "severity": str(r.get("severity", "")).strip().lower() or "unrated",
                           "mitigation": namer.say(r.get("mitigation", "")) or None} for r in risks[:3]]},
        "targets": [{"concern": namer.say(n.get("concern", "")), "target": namer.say(n.get("target", "")), "how": namer.say(n.get("how_enforced", "")) or None}
                    for n in design["nfrs"]],
        "gaps": {"items": gaps[:6], "total": len(gaps)},
        "sections": [{"id": i, "label": label, "count": counts.get(i)} for i, label in SECTIONS],
    }


def contract_answers(vault):
    """{contract id: [every way it can answer]} from each contract's case table, for the Details of a contract on Flows,
    the map and Decisions.

    A Paper Tiger guard: a contract panel that lists only the success answer says nothing about what a caller must
    handle. Each answer carries its status and whether it is an error, so the panel can say which are the error
    branches. A contract with no case table has no entry, and the page says "Not recorded"; nothing is guessed."""
    namer = Namer(vault)
    out = {}
    for contract in vault.contracts:
        table = cases.case_table(contract.page, contract)
        if table is None or not table.cases:
            continue
        out[contract.id] = [{"case": branches_data.case_words(c.key), "when": plain(c.when) or None, "status": c.status or None,
                             "says": namer.say(c.answer) or None, "error": c.is_error} for c in table.cases]
    return out


def panels(vault, data):
    """{app key: the panel's content for that app's design}; empty for an app with no design."""
    out = {}
    for app_key, design in data["designs"].items():
        namer = Namer(vault, design)
        comps = [c["name"] for c in design["components"]]
        app_title = next((n["title"] for n in data["nodes"] if n["key"] == app_key), design["title"])
        resolved = design["resolved"]
        untraced = [(namer.name(t) or namer.say(t), t in resolved["acknowledged"], resolved["acknowledged"].get(t)) for t in resolved["untraced"]]
        flows = design_flows(design, namer)
        asks = waiting(design, namer, comps)
        stubs = stub_lines(design, namer, design["stubs"])
        contracts = contract_details(design, namer, data, design["stubs"])
        for c in contracts.values():
            c["waiting"] = [{"id": q["id"], "question": q["question"]} for q in asks if q["id"] in c["waiting"]]
        components = {}
        for c in design["components"]:
            name = c["name"]
            components[name] = {
                "name": name, "partOf": app_title, "container": c.get("container"),
                "lead": namer.say(c["responsibility"]) or None, "owns": namer.say(c["owns"]) or None,
                "delivers": delivers(design, namer, name), "traceSource": design["trace_source"],
                "dependsOn": depends_text(design, namer, c) if c["depends_on"] else None,
                "exposes": plain(c["exposes"]) or None,
                "contracts": [{"id": cid, "name": v["name"]} for cid, v in contracts.items() if name in v["callers"]],
                "flows": [{"index": f["index"], "title": f["title"]} for f in flows if name in f["who"]],
                "waiting": [{"id": q["id"], "question": q["question"]} for q in asks if name in q["holds"]],
            }
        out[app_key] = {"summary": summary(design, namer, app_title, untraced), "components": components, "contracts": contracts,
                        "waiting": asks, "flows": flows, "links": stubs}
    return out
