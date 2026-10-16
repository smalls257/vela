"""Who holds each answer, and why things are the way they are. Ported from prototypes/gallery/asks/extract.py.

Who to ask comes from the unknown's own **Ask:** line when it has one. Only when it is absent does the build guess,
from the parenthesis in **Owner:** ("asking @x", "who asks the y"), and the guess is marked `inferred` with the rule
that made it, so the page can show a question mark and say why.

Decisions come from History bullets: an **Options considered:** line is one decision, drawn once however many
pages repeat it. What rests on it is taken only from typed fields: the items whose own History carries the same
line, and the unknowns whose **Blocks:** links to the decided page or item. Prose that merely mentions a decision
is never drawn.
"""
import re

from vela import attention, model, progress
from .record import plain, refs_in

HANDLE = re.compile(r"@[a-z0-9][a-z0-9-]*", re.I)
NOTHING = re.compile(r"^\s*nothing", re.I)
HISTORY_LABELS = ("Decision", "Options considered", "Decided by", "Confirmed by", "Dissent", "Override")
ACRONYMS = {"ceo": "CEO", "cto": "CTO", "cio": "CIO", "ciso": "CISO", "cfo": "CFO", "coo": "COO", "dpo": "DPO",
            "hr": "HR", "pr": "PR", "qa": "QA", "ux": "UX"}


def human(handle):
    """@coach-lead -> Coach lead; @ceo -> CEO."""
    words = [ACRONYMS.get(w.lower(), w) for w in handle.lstrip("@").replace("-", " ").split()]
    text = " ".join(words)
    return text[:1].upper() + text[1:]


def resolve_role(role, handles):
    role = role.strip().strip(".").removeprefix("the ").strip()
    slug = role.lower().replace(" ", "-")
    for h in handles:
        if h.lstrip("@").lower() == slug:
            return h, human(h)
    return None, human(role)


def who_to_ask(unknown, handles):
    """{key, name, inferred, recorded, rule, owner, also, asked_by}: the rack a strip sits in. `recorded` is true only
    when the unknown has an Ask line; without one the rack is the owner's or a guess, and the page must not read it as
    a person having been asked."""
    owner = plain(unknown.fact("Owner"))
    found = HANDLE.findall(owner)
    owner_handle = found[0] if found else owner.strip() or "unassigned"
    base = {"owner": owner_handle, "also": [], "asked_by": "", "recorded": False}
    recorded = plain(unknown.fact("Ask"))
    if recorded:
        h = HANDLE.findall(recorded)
        key = h[0] if h else recorded
        return {**base, "key": key, "name": human(key) if h else recorded, "inferred": False, "recorded": True,
                "rule": f"{human(key) if h else recorded}, named on the question"}
    paren = " ".join(re.findall(r"\(([^)]*)\)", owner))
    owner_role = paren.split(",")[0].split(";")[0].strip() if paren else ""
    m = re.search(r"asking (@[a-z0-9-]+)", paren, re.I)
    if m:
        return {**base, "key": m.group(1), "name": human(m.group(1)), "inferred": True,
                "rule": f"A guess: the owner's note says to ask {human(m.group(1))}."}
    m = re.search(r"(?:asking|who asks|asks) (the [a-z ]+?|[a-z ]+?)(?:[;,)]|$)", paren, re.I)
    if m:
        parts = re.split(r"\s+and\s+", m.group(1).strip())
        resolved = [resolve_role(p, handles) for p in parts]
        h, name = resolved[0]
        return {**base, "key": h or name, "name": name, "inferred": True, "also": [n for _, n in resolved[1:]],
                "rule": f"A guess: the owner's note says to ask {' and '.join(n for _, n in resolved)}."}
    m = re.search(r"([a-z ]+?) gives the ruling", paren, re.I)
    if m:
        h, name = resolve_role(m.group(1), handles)
        return {**base, "key": h or name, "name": name, "inferred": True,
                "rule": f"A guess: the owner's note says {name} gives the ruling."}
    asked_by = "the product lead" if "product lead does the asking" in paren else ""
    name = human(owner_role) if owner_role and len(owner_role) < 30 else human(owner_handle)
    return {**base, "key": owner_handle, "name": name, "inferred": False, "also": [human(h) for h in found[1:]],
            "asked_by": asked_by,
            "rule": f"{name}, who owns it (nobody else is named)" + ("; the product lead does the asking" if asked_by else "")}


def first_prose(page, after_line):
    out = []
    for raw in page.text.split("\n")[after_line:]:
        s = raw.strip()
        if s.startswith("#"):
            break
        if not s:
            if out:
                break
            continue
        if s.startswith(("- ", "|", "<!--", "```", ">")):
            if out:
                break
            continue
        out.append(s)
    return plain(" ".join(out))


def unknown_light(unknown, as_of):
    """The light an open question gives what it holds: attention.question_light, the same rule as every map."""
    light = attention.question_light(unknown, as_of)
    return {"level": light.level, "urgency": light.urgency}


def date_only(value):
    """The date when the whole value is one, else ''. A cut-off 'YYYY-MM-DD (maybe)' would look like a date the lights
    (attention.py) never read, and the page would show a date the board disagrees with."""
    return value if progress.is_date(value) else ""


def raw_unless_date(value):
    """What an Ask by line says when it is not a date, so the board can show it as text. The page escapes it."""
    return "" if progress.is_date(value) else plain(value)


def asks(vault, keys, as_of):
    handles = sorted({h for page in vault.pages for h in HANDLE.findall(page.text)})
    out = []
    for u in vault.unknowns:
        blocks = u.fact("Blocks")
        out.append({
            "id": u.id, "question": plain(u.fact("Question")), "summary": first_prose(u.page, u.line),
            "ownerRaw": plain(u.fact("Owner")), "ask": who_to_ask(u, handles), "state": u.fact("State"),
            "askBy": date_only(u.fact("Ask by")), "askByRaw": raw_unless_date(u.fact("Ask by")),
            "opened": date_only(u.fact("Opened")),
            "holdsReason": plain(blocks) if (not blocks or NOTHING.match(blocks)) else "",
            "outcome": plain(u.fact("Outcome")), "resolvedIn": plain(u.fact("Resolved in")),
            "light": unknown_light(u, as_of) if u.fact("State") == "open" else {"level": "dark", "urgency": 0},
        })
    return out


# ---------------------------------------------------------------- decisions, for the decision log

def parse_options(text):
    """'A (picked); B: rejected, why' or 'B. Rejected: why' -> (picked, [rejected])."""
    picked, rejected = None, []
    for part in re.split(r";\s+(?![^()]*\))", plain(text)):
        part = part.strip()
        m = re.match(r"(.+?)\s*\((picked[^)]*)\)\s*$", part)
        if m:
            picked = {"label": m.group(1).strip(), "condition": m.group(2)[len("picked"):].strip(" ,")}
            continue
        m = re.match(r"(.+?)(?::\s*|\.\s+)rejected(?: for now)?[,:]?\s*(.*)$", part, re.I)
        if m:
            later = "for now" in part.lower()[: len(m.group(1)) + 30]
            rejected.append({"label": m.group(1).strip(), "reason": m.group(2).strip().rstrip("."), "forNow": later})
        elif part:
            rejected.append({"label": part, "reason": "", "forNow": False})
    return picked, rejected


def norm(label):
    return re.sub(r"^(a|an|the)\s+", "", label.strip().lower())


def history_groups(page):
    """Decisions come from History bullets. An **Options considered:** line is one decision, drawn once however
    many pages repeat it. As of CONVENTIONS line 293, such bullets count anywhere on a page, not only under History."""
    history_line = next((h.line for h in page.headings if h.level == 2 and h.text.strip() == "History"), None)
    subs = [h for h in page.headings if h.level == 4 and (history_line is None or h.line > history_line)]
    groups = {}
    for b in page.bullets:
        if b.label not in HISTORY_LABELS or b.generated:
            continue
        # Bullets are grouped under their level-4 heading if they're in History; otherwise under "".
        under = ""
        if history_line is not None and b.line >= history_line:
            under_heads = [h for h in subs if h.line < b.line]
            if under_heads:
                under = under_heads[-1].text.strip()
        groups.setdefault(under, []).append(b)
    return groups


def section_text(page, title):
    for h in page.headings:
        if h.level == 2 and h.text.strip().lower() == title.lower():
            return first_prose(page, h.line)
    return ""


def page_opening(page):
    h1 = next((h for h in page.headings if h.level == 1), None)
    return first_prose(page, h1.line if h1 else 1)


def section_range(page, title):
    start = next((h for h in page.headings if h.level == 2 and h.text.strip().lower() == title), None)
    if start is None:
        return None
    end = next((h.line for h in page.headings if h.line > start.line and h.level <= 2), 10 ** 9)
    return start.line, end


def adr_tree(adr, keys, count):
    """A decision record whose History has no Options considered line: its Alternatives considered table is the
    pruned options, and the unknowns its Assumptions it depends on section links are what it rests on."""
    span = section_range(adr, "alternatives considered")
    rejected = []
    for table in adr.tables:
        if span and span[0] < table.line < span[1] and not table.generated:
            for row in table.rows:
                if row and row[0].strip():
                    rejected.append({"label": plain(row[0]), "reason": plain(row[1]) if len(row) > 1 else "", "forNow": False})
    assumes = []
    span_a = section_range(adr, "assumptions it depends on")
    if span_a:
        lines = adr.text.split("\n")[span_a[0]:span_a[1] - 1]
        for k in refs_in("\n".join(lines), keys, adr):
            if k.startswith("UNK-") and k not in assumes:
                assumes.append(k)
    if not rejected and not assumes:
        return None
    where = {"key": keys.page(adr), "page": keys.page(adr), "pageTitle": str(adr.meta.get("title", adr.name)),
             "type": "decision", "item": "", "under": "", "state": str(adr.meta.get("state", "")),
             "text": section_text(adr, "Decision"), "decidedBy": [], "confirmedBy": [],
             "decision": [plain(b.value) for b in adr.bullets if b.label == "Decision"], "overrides": 0,
             "owner": str(adr.meta.get("owner", "")), "status": section_text(adr, "Status")}
    return {"id": f"D{count + 1:02d}", "picked": {"label": str(adr.meta.get("title", adr.name)), "condition": ""},
            "rejected": rejected, "carriedBy": [where], "assumes": assumes, "fromTable": True,
            "adr": {"id": adr.id, "key": keys.page(adr), "decision": section_text(adr, "Decision")}}


def picked_line_before(page, line):
    """The 'Picked option' bullet nearest above `line`: what a page says in words when its opening prose is only a
    heading and a list, as a strategy page whose decisions sit under `##` headings."""
    above = [b for b in page.bullets if b.label == "Picked option" and b.line < line and not b.generated]
    return plain(above[-1].value) if above else ""


def decisions(vault, keys):
    """{"trees": [...], "bare": [...]}: one tree per distinct Options considered line."""
    trees, lone = {}, []
    for page in vault.pages:
        if page.type == "session" or page.path.startswith("voice/"):
            continue
        for under, bullets in history_groups(page).items():
            item_id = under.split(" ")[0] if re.match(r"^[A-Z]+-\d", under) else ""
            item = vault.item(item_id) if item_id else None
            where = {"key": item.id if item else keys.page(page), "page": keys.page(page),
                     "pageTitle": str(page.meta.get("title", page.name)), "type": page.type, "item": item.id if item else "",
                     "under": under, "state": (item.fact("State") if item else str(page.meta.get("state", ""))) or "",
                     "text": (item.name + ". " + first_prose(item.page, item.line)) if item else page_opening(page),
                     "decidedBy": [plain(b.value) for b in bullets if b.label == "Decided by"],
                     "confirmedBy": [plain(b.value) for b in bullets if b.label == "Confirmed by"],
                     "decision": [plain(b.value) for b in bullets if b.label == "Decision"],
                     "overrides": len([b for b in bullets if b.label == "Override"]),
                     "owner": str(page.meta.get("owner", ""))}
            options = [b for b in bullets if b.label == "Options considered"]
            if not options:
                if where["decision"]:
                    lone.append(where)
                continue
            for b in options:
                picked, rejected = parse_options(b.value)
                sig = "|".join([norm(picked["label"]) if picked else plain(b.value)] + sorted(norm(r["label"]) for r in rejected))
                if picked is None:
                    picked = {"label": where["text"] or f"{where['pageTitle']}, {under}", "condition": "", "fromText": True}
                where_here = where if where["text"] else {**where, "text": picked_line_before(page, b.line)}
                tree = trees.setdefault(sig, {"id": f"D{len(trees) + 1:02d}", "picked": picked, "rejected": rejected,
                                              "carriedBy": []})
                tree["carriedBy"].append(where_here)
    for adr in vault.of_type("decision"):
        title = str(adr.meta.get("title", "")).lower()
        for tree in trees.values():
            if norm(tree["picked"]["label"]) == norm(title):
                tree["picked"]["label"] = str(adr.meta.get("title"))
                tree["adr"] = {"id": adr.id, "key": keys.page(adr), "decision": section_text(adr, "Decision")}
    folded = {t["adr"]["key"] for t in trees.values() if t.get("adr")}
    for adr in sorted(vault.of_type("decision"), key=lambda p: p.id):
        if keys.page(adr) in folded:
            continue
        tree = adr_tree(adr, keys, len(trees))
        if tree:
            trees["adr:" + adr.id] = tree
            folded.add(keys.page(adr))
    lone = [w for w in lone if w["page"] not in folded]
    blocked = {}
    for unit_id, unknowns in model.blockers(vault).items():
        for u in unknowns:
            blocked.setdefault(unit_id, set()).add(u.id)
    resolved_on = {}
    for u in vault.unknowns:
        if u.fact("State") == "open":
            continue
        bullet = u.facts.get("Blocks")
        for link in bullet.links if bullet else ():
            key = keys.link(link, u.page)
            if key:
                resolved_on.setdefault(key, set()).add(u.id)
    bare = [{"id": f"S{i + 1:02d}", "picked": {"label": w["pageTitle"], "condition": ""}, "rejected": [],
             "carriedBy": [w], "bare": True} for i, w in enumerate(lone)]
    for tree in list(trees.values()) + bare:
        rests = {w["key"] for w in tree["carriedBy"]} | {w["page"] for w in tree["carriedBy"] if not w["item"]}
        if tree.get("adr"):
            rests.add(tree["adr"]["key"])
        assumed = tree.get("assumes", [])
        tree["buds"] = sorted({u for k in rests for u in blocked.get(k, ())} | {u for u in assumed if vault.item(u).fact("State") == "open"})
        tree["leaves"] = sorted({u for k in rests for u in resolved_on.get(k, ())} | {u for u in assumed if vault.item(u).fact("State") != "open"})
    return {"trees": list(trees.values()), "bare": bare}


DECISION_STATES = ("pending", "proposed", "overridden", "decided")


def decision_state(tree, entities):
    """One decision's state, the one every view counts (the log, the Exec door): pending approval when a reader decided
    it and the owner hasn't reviewed it, overridden when it stands on a set-aside check nobody has confirmed, decided
    when a page carrying it says decided, else proposed. Computed here, once, so two views can't count it two ways
    (E60: the Exec door counted decision pages and said 0 proposed beside the log's 1)."""
    keys = [tree["adr"]["key"]] if tree.get("adr") else []
    keys += [k for w in tree["carriedBy"] for k in (w["key"], w["page"])]
    if any((entities.get(k) or {}).get("pending") for k in keys if k):
        return "pending"
    if sum(w.get("overrides", 0) for w in tree["carriedBy"]) and not any(w["confirmedBy"] for w in tree["carriedBy"]):
        return "overridden"
    return "decided" if any(w["state"] == "decided" for w in tree["carriedBy"]) else "proposed"


def settle_decisions(garden, entities):
    """Stamp each decision with its state and return the counts by state. The counts are over the decisions with their
    options written down, the set the log lists until the reader asks for the bare ones too."""
    counts = dict.fromkeys(DECISION_STATES, 0)
    for tree in garden["trees"] + garden["bare"]:
        tree["state"] = decision_state(tree, entities)
    for tree in garden["trees"]:
        counts[tree["state"]] += 1
    counts["all"] = len(garden["trees"])
    return counts
