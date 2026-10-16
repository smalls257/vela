"""Build the vault explorer: one static HTML page drawn from a vela vault. `vela explore` runs it.

Every node, edge, light and number on the page comes from vela's own parser and model: `cli.load_vault`,
`model`, `attention`, `progress`, `completeness`, `allocation`, `trace`, `ladder`, `override`, `handoff` and
`search`. The lights on every map and view are `attention.lights`, the one rule for what needs the lead.

Three things are heuristic, and the page labels each one where it shows:
- the direction of a message in a played flow when the step does not say who sends (flows_data.py);
- an app or party named in a step's text without a link;
- who holds an answer when the unknown has no **Ask:** line, guessed from its **Owner:** line (asks_data.py).

Positions are pinned in the vault, <vault>/.vela/explorer-pins.json (pins.py), so an app never moves between
views or builds. The page needs no network: it draws with its own SVG, canvas and Web Audio. Generated art is
optional (assets_inline.py).

"Inside this app" draws each app's main containers from its page, and, for each design given, the team's own tech
design beside the vault (design_data.py reads it, inside_data.py checks it against the vault; DESIGN-INSIDE.md).

`generate` is the one entry point. It takes the date and every path as arguments and returns the report lines;
the caller (cli.cmd_explore, or prototypes/explorer/build.py) reads the clock and does the printing.
"""
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import uuid

from vela import (allocation, attention, cli, completeness, handoff, ladder, links, model, override, pending, plainwords,
                     progress, reading, roles, say, schema, slices, terms, trace)
from vela import search as vela_search
from vela.edge import atomic
from vela.parse import FENCE, closes_fence

from . import (asks_data, assets_inline, branches_data, breakdown_find, design_data, design_find, draft_data, flows_data, icons_data, inside_data, pages_data,
               plan_data, roles_data, serve, slices_data)
from . import pins as pinning
from .record import (HANDLE, LABELED_LINE, PROSE_LIMIT, Keys, inline_html,
                     plain, refs_in, title_of)

HERE = pathlib.Path(__file__).resolve().parent
# marked, the Markdown parser the offline viewer already vendors (its license and checksum are in that folder's NOTICE.md).
# The page inlines it whole, with its copyright header, so Ask Claude can show an answer as Markdown with no network.
MARKED = HERE.parent / "assets" / "marked.min.js"


class ExplorerError(Exception):
    """A build that cannot go on: the vault, the assets, a pins file or a design could not be read. The message
    says which and why; nothing is written."""

# The page's script and style, in load order: shared code first, one module per view, the boot last.
JS_MODULES = ("core", "theme", "fx", "sound", "assets", "icons", "layout", "pan", "geometry", "search", "minimap", "reader", "queue", "panel", "panelsize", "motion", "view-map",
              "wires", "mapgroups", "releases", "slices", "flowkit", "flowpicker", "branches", "view-flows", "rehearse", "view-asks", "view-decisions", "view-progress",
              "view-trace", "sections", "roles", "nav", "markdown", "ask", "inside", "plan", "drafts", "freshness", "main")
SELFTEST_MODULES = ("selftest", "selftest-branches")  # 120 KB of checks: bundled only when asked (`vela explore --selftest`), not shipped to every reader
CSS_MODULES = ("base", "nav", "panel", "map", "queue", "flows", "rehearse", "asks", "decisions", "pages", "reader", "roles",
               "releases", "slices", "branches", "ask", "inside", "plan", "pending", "drafts", "themes", "plain")

# The themes the page offers, first the default. Each is a palette in assets/css/themes.css (Console is base.css's
# :root); the picker in the top bar lists them in this order and remembers the choice in the browser.
# The ids are what a browser remembers, so they stay; the labels and hints are what a reader picks from.
THEMES = (("console", "Dark", "dark, the default"),
          ("graphite", "Gray", "neutral gray with brighter type, for projectors"),
          ("daylight", "Light", "light, for screen-sharing and print"),
          ("vaporwave", "Sunset", "purple and pink, for fun"))
THEME_IDS = tuple(t[0] for t in THEMES)

# --------------------------------------------------------------------------- vault identity

VAULT_ID_KEY = "vault_id"
VAULT_ID_OK = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def legacy_vault_id(initiative, title):
    """The id every vault had before .vela.yaml could name one: a hash of its initiative ID and title, never of where
    the folder sits (a path in the key would give every clone a different page, so a committed dashboard.html would
    change on each machine's build). Two vaults left at the template's INI-001 / New initiative share it, and retitling
    changes it, which is why a vault_id is better."""
    return hashlib.sha256(f"{initiative}|{title}".encode()).hexdigest()[:12]


def vault_id(initiative, title, configured=None):
    """The short, stable identifier that scopes this vault's localStorage keys (board marks, layout, Ask conversations,
    rehearsals), so vaults and copies do not mix their state. The `vault_id:` line in .vela.yaml when there is one:
    it survives a retitle and tells two vaults apart. Else the legacy hash. A value that cannot scope a key is refused."""
    if configured is None:
        return legacy_vault_id(initiative, title)
    if not isinstance(configured, str) or not VAULT_ID_OK.match(configured):
        raise ExplorerError(f".vela.yaml's {VAULT_ID_KEY} is {configured!r}; write 8 to 64 letters, digits or dashes, such as {mint_vault_id()}")
    return configured


def vault_id_for(root):
    """The id the page for the vault at `root` will carry (the same one generate puts in the page)."""
    config = cli.load_config(pathlib.Path(root))
    return vault_id(str(config.get("initiative", "")), str(config.get("title", "")), config.get(VAULT_ID_KEY))


def mint_vault_id():
    """Starts with a letter so YAML reads it as text: a bare 1234567890123456 or 12e45678 would load as a number."""
    return "v-" + uuid.uuid4().hex[:14]


def vault_id_advice(root, role):
    """What to tell an owner whose .vela.yaml has no vault_id, or None. The build never edits .vela.yaml: two
    folders of one vault must build the same page, and a build must not leave the vault with an uncommitted change.
    So the owner adds the line; the page then moves what the browser saved under the old id to the new one."""
    if role != roles.OWNER or VAULT_ID_KEY in cli.load_config(pathlib.Path(root)):
        return None
    return (f"this vault has no {VAULT_ID_KEY} in .vela.yaml, so the browser keeps its saved marks, layout and Ask conversations under a name made "
            f"from the initiative and title: another vault with the same two shares them, and a new title loses them. Add the line "
            f"`{VAULT_ID_KEY}: {mint_vault_id()}` and commit it; what was saved before moves over once")


# --------------------------------------------------------------------------- opening prose

def skipped_lines(page):
    skip = set()
    for block in page.blocks:
        skip.update(range(block.start, block.end + 1))
    fence = None
    for n, raw in enumerate(page.text.split("\n"), start=1):
        stripped = raw.strip()
        if fence:
            skip.add(n)
            if closes_fence(raw, fence):
                fence = None
            continue
        opening = FENCE.match(raw)
        if opening:
            fence = opening.group(1)
            skip.add(n)
    return skip


def paragraphs(page, start, stop):
    """Prose paragraphs between two 1-based lines, skipping bullets, tables, quotes, headings and generated blocks."""
    lines = page.text.split("\n")
    skip = skipped_lines(page)
    found, current = [], []
    for n in range(start, min(stop, len(lines) + 1)):
        raw = lines[n - 1]
        stripped = raw.strip()
        prose = (stripped and n not in skip and not stripped.startswith(("-", "*", "|", "#", ">", "<!--", "<"))
                 and not re.match(r"^\d+\.\s", stripped) and not reading.BREADCRUMB.match(stripped)
                 and not LABELED_LINE.match(stripped) and stripped != "---")
        if prose:
            current.append(stripped)
        elif current:
            found.append(" ".join(current))
            current = []
    if current:
        found.append(" ".join(current))
    return found


def body_start(page):
    lines = page.text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 2
    return 1


def next_heading_line(page, after, max_level=6):
    for heading in page.headings:
        if heading.line > after and heading.level <= max_level:
            return heading.line
    return len(page.text.split("\n")) + 1


def opening(paras, keys, page):
    """(html, plain text, cut) for the first paragraphs, up to PROSE_LIMIT characters."""
    kept, size = [], 0
    for para in paras:
        if kept and size + len(para) > PROSE_LIMIT:
            break
        kept.append(para)
        size += len(para)
    cut = len(kept) < len(paras)
    return ("".join(f"<p>{inline_html(p, keys, page)}</p>" for p in kept), " ".join(plain(p) for p in kept), cut)


def page_opening(page, keys):
    h1 = next((h for h in page.headings if h.level == 1), None)
    start = h1.line + 1 if h1 else body_start(page)
    return opening(paragraphs(page, start, next_heading_line(page, start - 1, 2)), keys, page)


def item_opening(item, keys):
    return opening(paragraphs(item.page, item.line + 1, next_heading_line(item.page, item.line)), keys, item.page)


# --------------------------------------------------------------------------- entities

def owner_handle(text):
    match = HANDLE.search(text or "")
    return match.group(0) if match else ""


def item_facts(item, keys):
    """Every bullet in the item's own section, in order. Repeated labels (Notes) all stay."""
    out = []
    for bullet in item.page.bullets:
        if bullet.item == item.id and not bullet.generated and bullet.line > item.line:
            out.append({"label": bullet.label, "html": inline_html(bullet.value, keys, item.page),
                        "text": plain(bullet.value), "refs": refs_in(bullet.value, keys, item.page)})
    return out


LINK_KINDS = (("tracker", r"jira|ticket|issue|tracker|backlog"), ("wiki", r"confluence|wiki|space"),
              ("repo", r"github|gitlab|bitbucket|repo|source"), ("api", r"api|openapi|swagger|spec|schema"),
              ("docs", r"doc|guide|manual|runbook|handbook"))


def link_kind(label):
    """Which glyph a link chip wears, from its label: a tracker, a wiki, a repo, an API spec, docs, or a plain link."""
    return next((kind for kind, pattern in LINK_KINDS if re.search(pattern, label, re.I)), "link")


def link_rows(found):
    return [{"label": x.label, "url": x.url, "kind": link_kind(x.label)} for x in found]


def page_entity(page, keys, config=None):
    prose_html, prose_text, cut = page_opening(page, keys)
    meta = page.meta
    owner = meta.get("owner") if isinstance(meta.get("owner"), str) else ""
    return {
        "key": keys.page(page), "id": page.id, "kind": page_kind(page), "title": title_of(page),
        "path": page.path, "state": str(meta.get("state") or ""), "change": str(meta.get("change") or ""),
        "stage": str(meta.get("stage") or ""), "owner": owner, "ownerKey": owner_handle(owner),
        "prose": prose_html, "text": prose_text, "cut": cut,
        "facts": [{"label": b.label, "html": inline_html(b.value, keys, page), "text": plain(b.value),
                   "refs": refs_in(b.value, keys, page)} for b in page.bullets if not b.item and not b.generated],
        "links": link_rows(links.of_page(page, config or {})[0]), "pending": pending_row(pending.pending_for(page)),
    }


def pending_row(found):
    """A reader's unreviewed decision as the page shows it: who and when, or None."""
    return {"by": found.by, "date": found.date} if found else None


PAGE_KINDS = {"app-building-blocks": "app", "app-runtime": "runtime", "epic": "epic", "capability": "capability",
              "flow": "flow", "decision": "decision", "concern": "concern", "session": "session", "slice": "slice",
              "initiative-section": "section", "sources": "page", "index": "page"}


def page_kind(page):
    return PAGE_KINDS.get(page.type, "page")


def item_entity(item, keys):
    prose_html, prose_text, cut = item_opening(item, keys)
    owner = item.fact("Owner")
    return {
        "key": item.id, "id": item.id, "kind": item.kind if item.kind != "requirement" else "requirement",
        "title": item.name, "path": item.page.path, "anchor": item.heading, "pageKey": keys.page(item.page),
        "state": item.fact("State"), "change": item.fact("Change"), "owner": owner, "ownerKey": owner_handle(owner),
        "prose": prose_html, "text": prose_text, "cut": cut,
        "facts": [f for f in item_facts(item, keys) if f["label"] != schema.LINKS_LABEL], "links": link_rows(links.of_item(item)[0]),
        "pending": pending_row(pending.pending_for(item.page, item.id)),
    }


# --------------------------------------------------------------------------- the system map

def provider_key(vault, keys, contract, parties_by_name):
    """(node key, kind) of a contract's provider: the app whose page it lives on, a party it links, or a
    named outside provider. A plain-text provider whose name is exactly a party's name is that party."""
    bullet = contract.facts.get("Provider")
    if not bullet:
        return keys.page(contract.page), "app"
    for link in bullet.links:
        key = keys.link(link, contract.page)
        item = vault.item(key) if key else None
        if item is not None and item.kind == "party":
            return item.id, "party"
    name = re.sub(r"\s*\(external\)\s*$", "", plain(bullet.value)).strip()
    party = parties_by_name.get(name.lower())
    if party is not None:
        return party.id, "party"
    return "ext:" + name, "external"


PROSE_BREAK = re.compile(r"\s*(?:[,;:\u2014]|\s-\s|\()")
NAME_CAP = 32


def external_title(said):
    """The name to draw for a provider a contract names in running text: the words before the first comma, colon or
    bracket, cut at a word under NAME_CAP characters. "the pilot user, on their own laptop" is drawn "the pilot user".
    A short plain name ("Stripe") is returned unchanged. The full text stays on the node as `said`."""
    head = PROSE_BREAK.split(said, 1)[0].strip() or said
    if len(head) <= NAME_CAP:
        return head
    return head[:NAME_CAP].rsplit(" ", 1)[0].rstrip(" ,;:") + "\u2026"


def system_map(vault, keys):
    parties_by_name = {p.name.lower(): p for p in vault.parties}
    contracts, externals = [], {}
    for c in vault.contracts:
        pkey, pkind = provider_key(vault, keys, c, parties_by_name)
        if pkind == "external":
            externals[pkey] = pkey[4:]
        crosses = c.facts.get("Crosses the boundary")
        contracts.append({
            "id": c.id, "title": c.name, "provider": pkey, "providerKind": pkind, "keptOn": keys.page(c.page),
            "consumers": [keys.page(p) for p in vault.consumers(c)], "state": c.fact("State"),
            "change": c.fact("Change"), "crosses": inline_html(crosses.value, keys, c.page) if crosses else "",
        })
    apps = [{"key": keys.page(a), "id": a.id, "title": title_of(a), "change": str(a.meta.get("change") or ""),
             "state": str(a.meta.get("state") or ""), "stage": str(a.meta.get("stage") or ""),
             "domain": str(a.meta.get("domain") or "").strip()} for a in vault.apps]
    with_contract = {c["provider"] for c in contracts}
    parties = [{"key": p.id, "title": p.name, "hasContract": p.id in with_contract} for p in vault.parties]
    return {"apps": apps, "contracts": contracts, "parties": parties,
            "externals": [{"key": k, "title": external_title(v), "said": v,
                           "contracts": [c["id"] for c in contracts if c["provider"] == k]} for k, v in sorted(externals.items())]}


def app_details(vault, keys, blocked):
    out = {}
    for app in vault.apps:
        provided = [c for c in progress.provided(vault, app) if not c.fact("Provider")]
        consumed = progress.consumed(vault, app) + [c for c in progress.provided(vault, app) if c.fact("Provider")]
        epics = [e for e in trace.epics(vault) if app.id in trace.listed(e, "apps")]
        units = [u.id for u in progress.units(vault, app)] + [c.id for c in consumed] + [e.id for e in epics]
        questions = {}
        for u in model.blocking_unknowns(vault, app):
            questions.setdefault(u.id, []).append(keys.page(app))
        for unit_id in units:
            for u in blocked.get(unit_id, []):
                questions.setdefault(u.id, []).append(unit_id)
        runtime = progress.runtime_page(vault, app)
        reached, needs = ladder.allows(vault, app)
        seen = {(c.concern.id, c.app): c.state for c in vault.cells}
        unexamined = ([p.id for p in sorted(vault.of_type("concern"), key=lambda p: p.id)
                       if seen.get((p.id, app.name), "unexamined") == "unexamined"]
                      if app.meta.get("change") in schema.LADDERED_CHANGES else [])
        out[keys.page(app)] = {
            "provides": [c.id for c in provided], "consumes": [c.id for c in consumed],
            "epics": [keys.page(e) for e in epics], "runtime": keys.page(runtime) if runtime else "",
            "questions": [{"id": k, "via": sorted(set(v))} for k, v in sorted(questions.items())],
            "reached": reached, "needs": needs, "unexamined": unexamined,
        }
    return out


# --------------------------------------------------------------------------- unknowns

def unknowns(vault, keys):
    out = []
    for u in vault.unknowns:
        blocks = u.facts.get("Blocks")
        direct, expanded = [], []
        for link in blocks.links if blocks else ():
            key = keys.link(link, u.page)
            if key and key not in direct:
                direct.append(key)
            for unit_id, _state, page, _line in model.blocked_units(vault, link, u.page):
                unit_key = unit_id if vault.item(unit_id) else (keys.page(page) if page.id == unit_id else unit_id)
                if unit_key not in expanded:
                    expanded.append(unit_key)
        ask_by = u.fact("Ask by")
        out.append({
            "id": u.id, "state": u.fact("State"), "owner": u.fact("Owner"), "ownerKey": owner_handle(u.fact("Owner")),
            "askBy": ask_by if progress.is_date(ask_by) else "", "askByText": ask_by,
            "opened": progress.opened_date(u), "blocks": direct, "holds": expanded,
            "blocksText": plain(blocks.value) if blocks else "",
        })
    return out


# --------------------------------------------------------------------------- progress

def overrides_awaiting(vault, keys):
    """Decisions made on someone's behalf that the owner has not yet confirmed, plus every override, by scope."""
    awaiting, recorded = [], []
    for page in vault.pages:
        scopes = []
        for bullet in page.bullets:
            if bullet.label in schema.OVERRIDE_LABELS and not bullet.generated and bullet.item not in scopes:
                scopes.append(bullet.item)
        for scope in scopes:
            key = scope if scope else keys.page(page)
            behalf = override.on_behalf(page, scope)
            if behalf is not None and not behalf.confirmed_by:
                awaiting.append({"key": key, "by": behalf.by, "owners": list(behalf.owners)})
            for o in override.valid_overrides(page, scope):
                recorded.append({"key": key, "rules": list(o.rules), "skipped": [attention.skipped_check(r) for r in o.rules],
                                 "by": o.by, "date": o.date, "reason": o.reason,
                                 "confirmed": bool(behalf and behalf.confirmed_by)})
    return awaiting, recorded


def handoff_status(vault, root, keys, app):
    path = root / "handoffs" / f"{app.id}.md"
    status = {"handedOff": str(app.meta.get("handed_off") or ""), "manifest": "", "changed": 0, "added": 0,
              "removed": 0, "problem": "", "written": ""}
    if not path.is_file():
        return status
    status["manifest"] = path.relative_to(root).as_posix()
    try:
        facts, accepted = handoff.read(path.read_text(encoding="utf-8"))
        handoff.check_manifest(app.id, facts, accepted)
    except (OSError, UnicodeDecodeError, handoff.ManifestError) as exc:
        status["problem"] = str(exc)
        return status
    diff = handoff.verify(accepted, handoff.handoff_list(vault, app), vault)
    status.update(changed=len(diff.changed), added=len(diff.added), removed=len(diff.removed),
                  written=facts.get("Written", ""),
                  changes=[handoff.describe(o, n, n.id in diff.left) for o, n in diff.changed][:12])
    return status


def progress_data(vault, root, keys, today):
    rows = []
    for r in progress.grid(vault, today):
        rows.append({"app": keys.page(r.app), "stage": r.stage, "mix": list(r.mix), "byOverride": r.by_override,
                     "oldest": r.oldest.id if r.oldest else "", "opened": r.opened, "rule": r.rule, "mode": r.mode,
                     "subject": r.subject, "reason": r.reason,
                     "handoff": handoff_status(vault, root, keys, r.app)})
    percent, shares = completeness.measure(vault)
    awaiting, recorded = overrides_awaiting(vault, keys)
    best = progress.best(progress.grid(vault, today))
    return {"rows": rows, "stages": list(schema.ENUMS["stage"]), "percent": percent,
            "shares": [{"name": s.name, "done": s.done, "total": s.total} for s in shares],
            "awaiting": awaiting, "overrides": recorded,
            "next": {"app": keys.page(best.app), "mode": best.mode, "subject": best.subject, "reason": best.reason} if best else None}


# --------------------------------------------------------------------------- trace

def trace_data(vault, keys):
    epics = [{"key": keys.page(e), "id": e.id, "apps": trace.listed(e, "apps"), "delivers": trace.listed(e, "delivers"),
              "consumes": trace.listed(e, "consumes"), "flows": trace.listed(e, "flows"),
              "dependsOn": trace.listed(e, "depends_on")} for e in trace.epics(vault)]
    caps = [{"key": keys.page(c), "id": c.id, "domain": str(c.meta.get("domain") or "")}
            for c in sorted(vault.of_type("capability"), key=lambda p: p.id)]
    reqs = [{"id": r.id, "capability": r.id.split(".")[0], "state": r.fact("State")} for r in allocation.requirements(vault)]
    rows = [{"app": keys.page(r.app), "requirement": r.requirement, "share": r.share, "through": list(r.through),
             "state": r.state} for r in allocation.rows(vault)]
    report = trace.report(vault)
    gaps = [{"rule": g.rule, "subject": g.subject, "message": g.message, "fix": g.fix} for g in report.gaps]
    return {"epics": epics, "capabilities": caps, "requirements": reqs, "allocation": rows, "gaps": gaps,
            "checked": report.checked}


# --------------------------------------------------------------------------- flows

# --------------------------------------------------------------------------- search

CHECK_QUERIES = ("paper order", "how does booking talk to pricing", "how does a reader place a paper trade",
                 "hold a seat", "who is on call")


def search_index(vault, keys):
    """vela.search's own sections and stems, so the page ranks exactly as `vela query search` does.
    The page's script ports only the scoring; the parity block lets it check itself against the CLI."""
    pages = [p for p in vault.pages if vela_search.searchable(p)]
    flows = [(p, {l for s in vela_search.sections(p) for l in s.links}) for p in pages if p.type == "flow"]
    rows = []
    for page in pages:
        title = str(page.meta.get("title") or page.name)
        for section in vela_search.sections(page):
            first = section.heading.split()[0] if section.heading.split() else ""
            item = vault.item(first.upper()) if first else None
            key = item.id if item is not None and item.page is page else keys.page(page)
            t = vela_search.stems_of(title) if not section.heading else set()
            hd = vela_search.stems_of(section.heading) - t
            o = vela_search.stems_of(section.opening) - t - hd
            x = vela_search.stems_of(section.text) - t - hd - o
            crossing = {f"{page.name}#{section.heading}"} if section.heading else {page.name}  # search.flows_crossing's rule
            rows.append({"key": key, "page": page.path, "heading": section.heading, "t": sorted(t), "h": sorted(hd),
                         "o": sorted(o), "x": sorted(x), "snip": vela_search.snippet(section),
                         "flows": [keys.page(f) for f, links in flows if f is not page and links & crossing]})
    check = []
    for q in CHECK_QUERIES:
        answer = vela_search.search(vault, q.split(), limit=8)
        check.append({"q": q, "hits": [f"{h['page']}::{h['heading']}" for h in answer["hits"]]})
    return {"rows": rows, "stop": sorted(vela_search.STOP), "weight": vela_search.WEIGHT, "check": check}


# --------------------------------------------------------------------------- backlinks and owners

def backlinks(vault, keys):
    out = {}
    for page in vault.pages:
        if page.type == "session":
            continue  # sessions link everything they touched; they would drown the panel
        source = keys.page(page)
        for link in page.links:
            key = keys.link(link, page)
            if key and key != source:
                bucket = out.setdefault(key, [])
                if source not in bucket:
                    bucket.append(source)
    return out


def owners(entities):
    out = {}
    for e in entities.values():
        if e.get("ownerKey"):
            out.setdefault(e["ownerKey"], {"key": "owner:" + e["ownerKey"], "handle": e["ownerKey"], "owns": [],
                                           "names": []})
            entry = out[e["ownerKey"]]
            entry["owns"].append(e["key"])
            after = e["owner"].split(e["ownerKey"], 1)[-1]
            words = HANDLE.split(after)[0].strip(" ();,.")
            if words and words not in entry["names"]:
                entry["names"].append(words)
    return out


# --------------------------------------------------------------------------- assembly

def map_nodes(vault, keys, m, pins_path, seed=None):
    """Every station on the map, with its pinned cell. Outside parties are drawn only when a contract joins them."""
    nodes = [{"key": a["key"], "kind": "app", "title": a["title"]} for a in m["apps"]]
    joined = {c["provider"] for c in m["contracts"]} | {k for c in m["contracts"] for k in c["consumers"]}
    nodes += [{"key": p["key"], "kind": "partner", "title": p["title"]} for p in m["parties"] if p["key"] in joined]
    nodes += [{"key": x["key"], "kind": "partner", "title": x["title"], "external": True} for x in m["externals"]]
    try:
        found, added, stale, seeded, moved = pinning.pinned(pins_path, nodes, m["contracts"], seed)
    except ValueError as exc:
        raise ExplorerError(str(exc)) from exc
    for n in nodes:
        n["col"], n["row"] = found[n["key"]]
    return nodes, {"added": added, "stale": stale, "seededFrom": seeded, "moved": moved,
                   "all": dict(sorted(found.items())),  # sorted: a first build and a rebuild must write the same bytes
                   # the frame and box the overlap rule measures in, so the page's copy of the rule (layout.js) uses the same numbers
                   "frame": {**pinning.FRAME, "boxW": pinning.BOX["w"], "boxH": pinning.BOX["h"], "gap": pinning.GAP, "slack": pinning.SLACK},
                   "file": pathlib.Path(pins_path).name if pins_path else ""}


def lights_data(vault, keys, today):
    """attention.lights, keyed as the page keys things, plus the ranked order and what is held above the map."""
    found, above = attention.lights(vault, today)
    to_key = {p.id: keys.page(p) for p in vault.pages if p.id}
    lights = {to_key.get(k, k): v.as_dict() for k, v in found.items()}
    ranked = [to_key.get(k, k) for k, _ in attention.ranked(found)]
    page_by_id = {p.id: p for p in vault.pages if p.id}
    for a in above:
        target = vault.item(a["holds"]) or page_by_id.get(a["holds"])
        a["key"] = (a["holds"] if vault.item(a["holds"]) else keys.page(target)) if target is not None else ""
        a["title"] = (target.name if vault.item(a["holds"]) else title_of(target)) if target is not None else a["holds"]
    return {"lights": lights, "ranked": ranked, "above": above, "levels": list(attention.LEVELS)}


def extract(vault, root, today, pins_path=None, designs=None, seed=None, plans=None):
    keys = Keys(vault)
    entities = {}
    for page in vault.pages:
        if page.path.startswith("voice/"):
            continue  # voice examples are writing samples, not plan content
        entity = page_entity(page, keys, vault.config)
        entities[entity["key"]] = entity
    for found in vault.items.values():
        entity = item_entity(found[0], keys)
        entities[entity["key"]] = entity
    blocked = model.blockers(vault)
    initiative = str(vault.config.get("initiative", ""))
    data = {
        "initiative": initiative, "title": str(vault.config.get("title", "")),
        "vaultId": vault_id(initiative, str(vault.config.get("title", "")), vault.config.get(VAULT_ID_KEY)),
        "legacyVaultId": legacy_vault_id(initiative, str(vault.config.get("title", ""))) if VAULT_ID_KEY in vault.config else "",
        "today": today,
        "vault": "", "entities": entities, "role": roles.NONE, "draft": None, "freshness": None, "built": None,
        "map": system_map(vault, keys), "apps": app_details(vault, keys, blocked),
        "unknowns": unknowns(vault, keys), "risks": [r.id for r in vault.risks],
        "blockedBy": {k: [u.id for u in v] for k, v in blocked.items()},
        "progress": progress_data(vault, root, keys, today), "trace": trace_data(vault, keys),
        "backlinks": backlinks(vault, keys), "search": search_index(vault, keys), "ask": {"rules": list(serve.RULES)},
        "terms": dict(terms.TERMS), "words": plainwords.reader_words(),
    }
    data["pending"] = pending_list(vault, keys)
    data["owners"] = owners(entities)
    data["nodes"], data["pins"] = map_nodes(vault, keys, data["map"], pins_path, seed)
    app_meta = {keys.page(a): a.meta for a in vault.apps}
    domain_of = {a["key"]: a["domain"] for a in data["map"]["apps"]}
    data["icons"], data["iconsUnknown"] = icons_data.for_map(data["nodes"], entities, domain_of, app_meta)
    data["linkProblems"] = link_problems(vault)
    names = {n["key"]: n["title"] for n in data["nodes"]}
    played = flows_data.flows(vault, keys, data["map"]["contracts"], {n["key"]: [n["col"], n["row"]] for n in data["nodes"]}, names)
    data["lanes"], data["flows"] = played["lanes"], played["flows"]
    data.update(lights_data(vault, keys, today))
    data["asks"] = asks_data.asks(vault, keys, today)
    data["garden"] = asks_data.decisions(vault, keys)
    # Every count a view shows comes from here or from Queue.needsYou, never from a view's own filter (E60).
    data["counts"] = {"decisions": asks_data.settle_decisions(data["garden"], entities),
                      "openQuestions": sum(1 for u in data["asks"] if u["state"] == "open")}
    data["sessions"] = {s.name: {"title": str(s.meta.get("title", s.name)), "date": str(s.meta.get("date", ""))}
                        for s in vault.sessions}
    data["reader"] = pages_data.readers(vault, keys)
    data["sections"] = pages_data.sections(vault, keys)
    data["outgoing"] = pages_data.outgoing(vault, keys)
    data.update(roles_data.extract(vault, keys))
    recorded, _ = cli.recorded_standings(pathlib.Path(root), vault, [s.key for s in slices.read_slices(vault)], today)
    data["slicePlan"] = slices_data.extract(vault, keys, today, cli.spec_texts(pathlib.Path(root)), recorded)
    data["branches"] = branches_data.extract(vault, keys, today, cli.spec_texts(pathlib.Path(root)))
    data["containers"] = inside_data.containers(vault, keys)
    data["designs"] = inside_data.inside(vault, keys, designs or {})
    data["plans"] = plan_data.inside(vault, keys, plans or {}, data["designs"])
    data["themes"] = [{"id": i, "label": label, "say": say} for i, label, say in THEMES]
    data["theme"] = THEME_IDS[0]
    return data


def pending_list(vault, keys):
    """Every well-formed Pending approval marker, for the header chip and the Drafts view."""
    page_of = {p.path: p for p in vault.pages}
    return [{"key": m.item or keys.page(page_of[m.path]), "subject": m.subject, "by": m.by, "date": m.date, "path": m.path}
            for m in pending.items(vault)]


def link_problems(vault):
    """Every link vela could not read, so the build says which were left out instead of dropping them quietly."""
    out = [f"{p.path}: {msg}" for p in vault.pages if p.meta for msg in links.of_page(p, vault.config)[1]]
    out += [f"{i[0].page.path}: {msg}" for i in vault.items.values() for msg in links.of_item(i[0])[1]]
    return out


def safe_json(value):
    """JSON for inside a <script>: every "<" escaped, so no vault text can close the tag or open a comment."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


# The lead patterns the page's own voice check sweeps every view for: say.LEAD_PATTERNS, the one copy, less the item
# and goal IDs (the page shows those on purpose, in a small tag beside the name; TextFit.bareLabels guards the names).
PAGE_LEAK_KINDS = tuple(k for k in say.LEAD_PATTERNS if k not in ("item", "goal"))


def lead_patterns():
    """{kind: JavaScript regex source} for the selftest. Python and JavaScript read these patterns alike (lookbehind,
    \\b, non-capturing groups), so the page checks the same rule `--for-lead` enforces."""
    return {k: say.LEAD_PATTERNS[k].pattern for k in PAGE_LEAK_KINDS}


def render(data, assets=None, selftest=False):
    if selftest:
        data = {**data, "leadPatterns": lead_patterns()}
    shell = (HERE / "assets" / "shell.html").read_text(encoding="utf-8")
    css = "\n".join((HERE / "assets" / "css" / f"{m}.css").read_text(encoding="utf-8") for m in CSS_MODULES)
    js = "\n".join(f"/* ---- {m}.js ---- */\n" + (HERE / "assets" / "js" / f"{m}.js").read_text(encoding="utf-8")
                   for m in (*JS_MODULES[:-1], *(SELFTEST_MODULES if selftest else ()), JS_MODULES[-1]))
    if assets:
        resolver = assets["resolver"]
        if "</script" in resolver.lower():
            raise assets_inline.AssetError("resolve.js contains </script and cannot be inlined")
        inline = (f"<script>window.ASSET_BUNDLE = {safe_json(assets['bundle'])};\n"
                  # the bundle is keyed by the resolver's own manifest paths; the page asks resolve.js by slot id
                  "// nosemgrep: prototype-asset-by-slot-id -- the resolver's inlined manifest, keyed by its own paths\n"
                  f"window.ASSET_FILES = {safe_json(assets['files'])};\nwindow.ASSET_REPORT = {safe_json(assets['report'])};</script>\n"
                  # resolve.js finds its folder from document.currentScript.src, which an inline script lacks; a
                  # document whose currentScript is null makes it fall back to "./", and the bundle does the rest.
                  f"<script>(function (document) {{\n{resolver}\n}})(Object.create(document, {{ currentScript: {{ value: null }} }}));</script>")
    else:
        inline = "<script>window.ASSET_REPORT = null;</script>"
    try:
        marked = MARKED.read_text(encoding="utf-8").replace("</script", "<\\/script")
    except OSError as exc:
        raise ExplorerError(f"cannot read {MARKED}, which Ask Claude needs to show an answer as Markdown: {exc}") from exc
    title = html.escape(f"{data['title']} ({data['initiative']}): vault explorer")
    theme = data.get("theme") or THEME_IDS[0]
    if theme not in THEME_IDS:
        raise ValueError(f"theme {theme!r} is not one of {', '.join(THEME_IDS)}")
    page = (shell.replace("{{TITLE}}", title).replace("{{THEME}}", theme).replace("/*{{CSS}}*/", css).replace("{{DATA}}", safe_json(data))
            .replace("<!--{{ASSETS}}-->", inline).replace("<!--{{MARKED}}-->", f"<script>{marked}</script>").replace("/*{{JS}}*/", js))
    return page.replace("<style>", f'<meta http-equiv="Content-Security-Policy" content="{content_security_policy(page)}">\n<style>', 1)


INLINE_SCRIPT = re.compile(r"<script(?![^>]*application/json)[^>]*>(.*?)</script>", re.S)


def content_security_policy(page):
    """What the page may do, so an escaping slip in vault text cannot become script or send the vault anywhere: only the
    page's own inline scripts run (each by hash, no inline handlers, no eval), nothing loads from outside, and the one
    connection allowed is to the helper that served it. Styles may be inline: the page sets them from script, and a style
    cannot run code. (Defense in depth: viewer.py keeps the same rule for the offline viewer.)"""
    hashes = " ".join(f"'sha256-{base64.b64encode(hashlib.sha256(m.group(1).encode('utf-8')).digest()).decode()}'"
                      for m in INLINE_SCRIPT.finditer(page))
    return (f"default-src 'none'; script-src {hashes}; style-src 'unsafe-inline'; img-src data: blob:; media-src data: blob:; "
            "font-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'")


# A shared folder this close to the root (/, or one folder under it) names the whole path on the way down.
SHALLOW_SHARED_FOLDER = 2


def relative_href(target, page_dir):
    """The href a page in `page_dir` uses to reach `target`, relative so no absolute path is built in. A relative
    href in a file:// page resolves beside it. The walk climbs to the folder the two share and then names every folder
    below it, so it is None when that would name the path: when it descends through the builder's home folder (the
    target is under it and the page is not), or when the shared folder is the disk's root or a folder just under it
    (/tmp, /private), where the folders named below are the absolute path. Sibling folders such as ~/Code/vault and
    ~/Code/booking share a deep folder, so their link is kept."""
    target, page_dir, home = pathlib.Path(target).resolve(), pathlib.Path(page_dir).resolve(), pathlib.Path.home().resolve()
    under_home = lambda p: p == home or home in p.parents  # noqa: E731
    if under_home(target) and not under_home(page_dir):
        return None
    if len(pathlib.Path(os.path.commonpath([target, page_dir])).parts) <= SHALLOW_SHARED_FOLDER:
        return None
    return pathlib.Path(os.path.relpath(target, page_dir)).as_posix()


def vault_path(target, root):
    """`target` as a path inside the vault, or '' when it lies outside. The served page opens only what lies inside
    (vault_files.py); a design or plan in a team repo beside the vault has no link there."""
    try:
        return pathlib.Path(target).resolve().relative_to(pathlib.Path(root).resolve()).as_posix()
    except ValueError:
        return ""


def link_sources(data, root, design_args, out_dir, plan_args=()):
    """Set the page's relative hrefs to the vault, to each team design and to each build plan (and the tickets
    beside it), and return what the build should say about links it left out. A link that cannot be relative
    without naming the home folder is left out; it is never made absolute."""
    said = []
    data["vault"] = relative_href(root, out_dir) or ""
    if not data["vault"]:
        said.append("no Open the file links, the vault and the page sit apart under the home folder; "
                    "build the page beside the vault to get them")
    paths = {m.group(1): m.group(2) for m in (design_data.SPEC.match(a.strip()) for a in design_args)}
    for design in data["designs"].values():
        design["href"] = relative_href(paths[design["appId"]], out_dir) or ""
        design["vaultPath"] = vault_path(paths[design["appId"]], root)
        if not design["href"]:
            said.append(f"no Open the design doc link for {design['appId']}, the doc and the page sit apart under the home folder")
    plan_paths = {m.group(1): pathlib.Path(m.group(2)) for m in (design_data.SPEC.match(a.strip()) for a in plan_args)}
    for plan in data["plans"].values():
        path = plan_paths[plan["appId"]]
        plan["href"] = relative_href(path, out_dir) or ""
        tickets = plan_data.tickets_path(path)
        plan["ticketsHref"] = (relative_href(tickets, out_dir) or "") if tickets else ""
        plan["hasTickets"] = bool(tickets)
        plan["vaultPath"], plan["ticketsVaultPath"] = vault_path(path, root), vault_path(tickets, root) if tickets else ""
        if not plan["href"] or (tickets and not plan["ticketsHref"]):
            said.append(f"no Open the plan or Tickets link for {plan['appId']}, the file and the page sit apart under the home folder")
    return said


def asset_lines(assets):
    r = assets["report"]
    return [f"assets from {r['source']}, provider {r['provider']}, {len(r['slots'])} slots, "
            f"{r['inlinedBytes'] // 1024} KB inlined, {len(r['fallbacks'])} fell back to builtin"
            + "".join(f"\n  {f['slot']}: {f['because']}" for f in r["fallbacks"])]


def design_lines(designs):
    lines = []
    for design in designs.values():
        problems = design["problems"]
        lines.append(f"{design['appId']} design {design['path']}: {design['frontmatter']['status']}, "
                     f"{len(design['components'])} components, {len(problems)} things it could not read"
                     + "".join(f"\n  line {p['line'] or '-'}, {p['section']}: {p['message']}" for p in problems))
    return lines


def plan_lines(plans):
    lines = []
    for plan in plans.values():
        t = plan["totals"]
        lines.append(f"{plan['appId']} build plan {plan['file']}: {plan['status'] or 'no status'}, {t['stories']} stories, {t['tasks']} tasks, "
                     f"{t['points']} points, {len(plan['problems'])} things it could not read"
                     + "".join(f"\n  {p}" for p in plan["problems"]))
    return lines


def shown(path, root):
    """A path as the report names it: inside the vault, relative to it; otherwise as given."""
    try:
        return pathlib.Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def pin_lines(data, pins_path, was_there, root):
    pins = data["pins"]
    if pins_path and not was_there:
        return [f"first build: wrote the pinned positions of {len(data['nodes'])} apps and parties to {shown(pins_path, root)}. "
                "They keep every app in the same place on every later build; delete the file to lay the map out afresh."]
    said = []
    if pins["moved"]:
        said.append(f"moved {', '.join(pins['moved'])} to the nearest free cell in {shown(pins_path, root) if pins_path else 'the layout'}: "
                    "each stood on another box, and the map would have drawn them over one another")
    if not pins["added"]:
        return said
    names = ", ".join(pins["added"])
    if not pins_path:
        return said + [f"computed positions for {names}; nothing keeps them, so the next build may place them differently"]
    return said + [f"pinned new positions in {shown(pins_path, root)}: {names}"]


def party_lines(data):
    """One line per outside provider a contract names in running text instead of linking an outside party, so the
    lead can name it in 03-context-and-scope.md. The map draws its first words and shows the full text on hover."""
    return [f"{'/'.join(x['contracts'])} names its provider in running text, \"{x['said']}\", so the map draws \"{x['title']}\". "
            "Add the party under Outside parties in 03-context-and-scope.md and link it as the contract's Provider."
            for x in data["map"]["externals"] if x["title"] != x["said"]]


def access_data(root, vault, freshness):
    """Who is looking, what a reader has drafted, and how fresh the copy was when the page was built."""
    found = cli.detect_role(root)
    draft = draft_data.for_workspace(root, vault, Keys(vault)) if found.role == roles.READER else None
    return {"role": found.role, "draft": draft, "freshness": freshness}


def draft_lines(data):
    draft = data["draft"]
    if draft is None:
        return []
    if draft["problem"]:
        return [f"draft: cannot compare with the baseline, {draft['problem']}"]
    said = [f"draft: {plural_pages(draft['count'])} changed since the copy you opened"] if draft["count"] else []
    waiting = len(draft.get("conflicts", []))
    if waiting:
        said.insert(0, f"draft: {waiting} {'conflict' if waiting == 1 else 'conflicts'} from the last re-open still to settle (your version sits beside each page as .mine.md)")
    return said


def plural_pages(n):
    return f"{n} page" if n == 1 else f"{n} pages"


def generate(root, out, today, pins_path=None, seed=None, assets_config=None, design_args=(), theme=THEME_IDS[0], freshness=None,
             breakdown_args=(), built=None, selftest=False):
    """Build the page for the vault at `root` and write it to `out`. Returns the report lines: what the build
    chose, what it left out and why, and the one-line summary last. Raises ExplorerError, writing nothing, when
    the vault, the assets, the pins, a design or a named breakdown cannot be read.

    `built` is {"date", "commit"}, the line the page shows at the top about what it was built from (commit "" when
    there is none). Nothing in the page comes from the clock, so the same vault, `today` and `built` write the same bytes.

    `pins_path` is the file that keeps every app's cell (None computes the layout and keeps nothing); `seed` is a
    pins file to start from when that one does not exist yet. `freshness` is the report (a dict) `vela freshness`
    gave at build time, or None; the build stamps it into the page, and never asks for it itself, so a build makes
    no network call."""
    root, out = pathlib.Path(root).resolve(), pathlib.Path(out)
    if not progress.is_date(today):
        raise ExplorerError(f"--today {today!r} is not a YYYY-MM-DD date")
    if theme not in THEME_IDS:
        raise ExplorerError(f"theme {theme!r} is not one of {', '.join(THEME_IDS)}")
    try:
        vault = cli.load_vault(root)
    except cli.ToolError as exc:
        raise ExplorerError(str(exc)) from exc
    try:
        assets = assets_inline.bundle(today, assets_config)
    except assets_inline.AssetError as exc:
        raise ExplorerError(f"--assets: {exc}") from exc
    was_there = bool(pins_path) and pathlib.Path(pins_path).exists()
    found, find_lines = design_find.discover(vault, root, design_args)  # local files only; an app named by --design is not looked up
    design_args = [*design_args, *found]
    plans_found, plan_find_lines = breakdown_find.discover(vault, root, breakdown_args, design_args)
    plan_args = [*breakdown_args, *plans_found]
    try:
        data = extract(vault, root, today, pins_path, design_data.designs_for(design_args), seed, plan_data.plans_for(plan_args))
    except design_data.DesignError as exc:
        raise ExplorerError(f"--design: {exc}") from exc
    except plan_data.PlanError as exc:
        raise ExplorerError(f"--breakdown: {exc}") from exc
    data["theme"] = theme
    data["built"] = built
    data.update(access_data(root, vault, freshness))
    said = link_sources(data, root, design_args, out.parent, plan_args)
    # Which apps this build newly pinned is a fact about the pins file, not the vault: the page does not read it, and
    # carrying it would make the first build and every later build of one vault differ. The report lines still say it.
    # A selftest build also carries the layout rule's cases with pins.check_move's answers, for the page to play against its own copy.
    cases = {"cases": pinning.move_cases()} if selftest else {}
    page = render({**data, "pins": {**data["pins"], "added": [], **cases}}, assets, selftest)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(out, page)
    said += pin_lines(data, pins_path, was_there, root)
    said += party_lines(data)
    said += asset_lines(assets)
    said += [f"{key} asks for icon: {asked}, which is not in the built-in set; it is drawn by keyword instead"
             for key, asked in data["iconsUnknown"]]
    said += [f"a link was left out, {problem} (vela check reports it as E105)" for problem in data["linkProblems"]]
    said += find_lines
    said += design_lines(data["designs"])
    said += plan_find_lines
    said += plan_lines(data["plans"])
    said += draft_lines(data)
    m = data["map"]
    said.append(f"wrote {out} for {data['initiative']} {data['title']}: {len(m['apps'])} apps, "
                f"{len(m['contracts'])} contracts, {len(data['unknowns'])} unknowns, {len(data['trace']['epics'])} epics, "
                f"{len(data['flows'])} flows, as of {today}.")
    return said
