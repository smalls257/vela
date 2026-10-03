#!/usr/bin/env python3
"""Throwaway viewer for the Unified Booking example vault.

Checks every [[wikilink]] in the vault, then bundles all pages into one HTML file
that renders them in the browser. It's a prototype of what Quartz would do, not
the real generator.

Usage:  python3 build-viewer.py            (from examples/)
Output: unified-booking-viewer.html, plus a link report on stdout.
Exit code 1 if any link is broken, so the report can't be missed.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
VAULT = HERE / "unified-booking"
OUT = HERE / "unified-booking-viewer.html"

WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 4 :].lstrip("\n")


def parse_link(inner):
    inner = inner.replace("\\|", "|")
    target, _, alias = inner.partition("|")
    name, _, anchor = target.partition("#")
    return name.strip(), anchor.strip(), alias.strip()


def load_pages():
    pages = []
    for path in sorted(VAULT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        pages.append(
            {
                "path": str(path.relative_to(VAULT)),
                "name": path.stem,
                "fm": fm,
                "body": body,
                "headings": HEADING.findall(body),
            }
        )
    return pages


def check_links(pages):
    """Report links whose page doesn't exist, or whose anchor matches no heading."""
    by_name = {}
    for p in pages:
        by_name.setdefault(p["name"], []).append(p)
    broken, ambiguous_names, count = [], [], 0
    for name, ps in by_name.items():
        if len(ps) > 1:
            ambiguous_names.append((name, [p["path"] for p in ps]))
    for p in pages:
        for m in WIKILINK.finditer(p["body"]):
            count += 1
            name, anchor, _ = parse_link(m.group(1))
            name = name or p["name"]
            targets = by_name.get(name)
            if not targets:
                broken.append((p["path"], m.group(0), "no such page"))
                continue
            if anchor and not any(
                h.startswith(anchor) for h in targets[0]["headings"]
            ):
                broken.append((p["path"], m.group(0), f"no heading starting '{anchor}'"))
    return count, broken, ambiguous_names


# ---------------------------------------------------------------------------
# Status block: computed from the pages, written into README between markers.
# Everything here is counted, never typed, so it can't drift from the pages.

STAGES = ["frame", "baseline", "target", "boundaries", "contracts", "handoff", "epics"]
DONE_STATES = {"decided", "addressed", "handed-off", "resolved", "mitigated"}
STATUS_START, STATUS_END = "<!-- status:start -->", "<!-- status:end -->"


def meta(page):
    out = {}
    for line in page["fm"].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*?)\s*(#.*)?$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"')
    return out


def bar(n, d, width=10):
    if d == 0:
        return "n/a"
    filled = round(width * n / d)
    return "▰" * filled + "▱" * (width - filled) + f" {n}/{d}"


def table_rows(body, first_header):
    """Rows of the first Markdown table whose first header cell is first_header."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        cells = split_row(line)
        if cells and cells[0] == first_header:
            rows = []
            for row in lines[i + 2 :]:
                if not row.startswith("|"):
                    break
                rows.append(split_row(row))
            return [cells] + rows
    return []


def split_row(line):
    if not line.startswith("|"):
        return []
    return [c.strip().replace("\x00", "|") for c in line.replace("\\|", "\x00").strip().strip("|").split("|")]


def col(rows, name):
    if not rows or name not in rows[0]:
        return []
    i = rows[0].index(name)
    return [r[i] for r in rows[1:] if len(r) > i]


def compute_status(pages):
    by_name = {p["name"]: p for p in pages}
    for p in pages:
        p["meta"] = meta(p)
    body = lambda n: by_name[n]["body"] if n in by_name else ""
    of_type = lambda t: [p for p in pages if p["meta"].get("type") == t]
    done = lambda ps: sum(1 for p in ps if p["meta"].get("state") in DONE_STATES)

    apps = of_type("app-building-blocks")
    stage_idx = [STAGES.index(p["meta"].get("stage", "frame")) for p in apps]
    slowest = STAGES[min(stage_idx)] if stage_idx else "frame"
    furthest = STAGES[max(stage_idx)] if stage_idx else "frame"
    at_epics = sum(1 for i in stage_idx if i == len(STAGES) - 1)

    sections = [
        ("Goals to strategy (§1–4)", [p for p in pages if p["meta"].get("type") == "initiative-section" and p["name"] != "12-glossary"]),
        ("Building blocks (§5)", apps),
        ("Runtime (§6)", of_type("app-runtime") + of_type("flow")),
        ("Concerns (§8)", of_type("concern")),
        ("Decisions (§9)", of_type("decision")),
        ("Epics", of_type("epic")),
        ("Capabilities", of_type("capability")),
    ]

    unk = table_rows(body("11-unknowns-and-risks"), "ID")
    ids, states = col(unk, "ID"), col(unk, "State")
    unknowns = [(i, s) for i, s in zip(ids, states) if "UNK-" in i]
    risks = [(i, s) for i, s in zip(ids, states) if "R-0" in i]
    unk_open = [re.search(r"(UNK-\d+)", i).group(1) for i, s in unknowns if not s.startswith("resolved")]
    unk_links = ", ".join(f"[[11-unknowns-and-risks#{u}\\|{u}]]" for u in unk_open) or "none"

    contracts = col(table_rows(body("05-building-blocks"), "Contract"), "State")
    delta = col(table_rows(body("04a-capability-delta"), "Capability"), "State")
    epics = of_type("epic")
    in_jira = sum(1 for p in epics if p["meta"].get("jira"))
    caps = of_type("capability")
    reconciled = sum(1 for p in caps if p["meta"].get("state") == "reconciled")

    modes = col(table_rows(body("session-history"), "Date"), "Mode")
    mode_counts = {m: modes.count(m) for m in ["Dump & Diverge", "Discover", "Shape", "Probe", "Grill"]}

    dated = sorted(p["meta"].get("last_verified", "") for p in pages if p["meta"].get("last_verified"))
    oldest = dated[0] if dated else "never"

    L = []
    stage = (f"every area is at {furthest.capitalize()}" if slowest == furthest
             else f"areas range from {slowest.capitalize()} to {furthest.capitalize()}")
    plural = "s" if len(unk_open) != 1 else ""
    L.append(f"**Stage:** {stage} · {at_epics} of {len(apps)} apps at Epics · "
             f"{len(unk_open)} open unknown{plural} · oldest verification {oldest}")
    L.append("")
    L.append("| | Progress | Notes |")
    L.append("|---|---|---|")
    L.append(f"| **Apps through the ladder** | {bar(at_epics, len(apps))} | slowest area: {slowest.capitalize()} |")
    for label, ps in sections:
        note = ""
        if label == "Capabilities":
            note = f"{reconciled} of {len(caps)} reconciled with an official capability map; the rest are proposed"
        elif label == "Epics":
            note = f"{in_jira} of {len(epics)} have a Jira key"
        L.append(f"| {label} | {bar(done(ps), len(ps))} | {note or str(len(ps)) + ' pages'} |")
    L.append("")
    L.append("| Decisions and open questions | Progress | Notes |")
    L.append("|---|---|---|")
    L.append(f"| ADRs decided | {bar(done(of_type('decision')), len(of_type('decision')))} | |")
    L.append(f"| Contracts decided | {bar(contracts.count('decided'), len(contracts))} | |")
    L.append(f"| Capability changes decided | {bar(delta.count('decided'), len(delta))} | |")
    unexamined = [p["meta"].get("title", p["name"]) for p in of_type("concern") if p["meta"].get("state") == "unexamined"]
    L.append(f"| Concerns addressed | {bar(done(of_type('concern')), len(of_type('concern')))} | unexamined: {', '.join(unexamined) or 'none'} |")
    L.append(f"| Unknowns resolved | {bar(len(unknowns) - len(unk_open), len(unknowns))} | open: {unk_links} |")
    L.append(f"| Risks mitigated | {bar(sum(1 for _, s in risks if s.startswith('mitigated')), len(risks))} | |")
    L.append("")
    L.append("**Sessions:** " + " · ".join(f"{m} {n}" for m, n in mode_counts.items()) + f" · {len(modes)} in total, see [[session-history|Session history]]")
    return "\n".join(L)


def write_status(pages):
    readme = VAULT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if STATUS_START not in text or STATUS_END not in text:
        raise SystemExit("README.md has no status markers; refusing to guess where the status goes")
    block = compute_status(pages)
    a = text.index(STATUS_START) + len(STATUS_START)
    b = text.index(STATUS_END)
    new = text[:a] + "\n<!-- generated: do not edit -->\n" + block + "\n<!-- /generated -->\n" + text[b:]
    if new != text:
        readme.write_text(new, encoding="utf-8")
    return block


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unified Booking Vault</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Public+Sans:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>
/* Layout: wiki shell. Left nav tree, centre page, right rail with properties and backlinks. */
:root {
  --bg: #F4F6F9; --surface: #FFFFFF; --fg: #19212D; --muted: #5A6474; --line: #D3D9E2;
  --accent: #2448B8; --accent-soft: #E2E8F8; --gen: #F1F3F6;
  --au: #2448B8; --mix: #9A5C08; --mix-soft: #F8ECD9; --gen-fg: #646C79;
  --display: "Bricolage Grotesque", "Segoe UI", system-ui, sans-serif;
  --body: "Public Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0F131A; --surface: #161C26; --fg: #E5E9EF; --muted: #9AA4B3; --line: #2D3543;
    --accent: #86A2FF; --accent-soft: #1D2742; --gen: #1B222D;
    --au: #86A2FF; --mix: #E6AA52; --mix-soft: #2E2210; --gen-fg: #A0A7B2; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0F131A; --surface: #161C26; --fg: #E5E9EF; --muted: #9AA4B3; --line: #2D3543;
  --accent: #86A2FF; --accent-soft: #1D2742; --gen: #1B222D;
  --au: #86A2FF; --mix: #E6AA52; --mix-soft: #2E2210; --gen-fg: #A0A7B2; color-scheme: dark;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15.5px; line-height: 1.6; }
.shell { display: grid; grid-template-columns: 290px minmax(0, 1fr) 280px; min-height: 100%; }
@media (max-width: 1100px) { .shell { grid-template-columns: 260px minmax(0, 1fr); } .rail { grid-column: 2; border-left: none; border-top: 1px solid var(--line); } }
@media (max-width: 760px) { .shell { grid-template-columns: 1fr; } .nav { position: static; max-height: 40vh; border-right: none; border-bottom: 1px solid var(--line); } .rail { grid-column: 1; } }
.nav { position: sticky; top: 0; height: 100vh; overflow-y: auto; border-right: 1px solid var(--line); background: var(--surface); padding: 18px 14px 40px; font-size: 0.84rem; }
.nav h1 { font-family: var(--display); font-size: 1.05rem; margin: 0 0 4px; }
.nav .sub { font-family: var(--mono); font-size: 0.68rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 12px; }
.nav input { width: 100%; padding: 6px 8px; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); color: var(--fg); font: inherit; margin-bottom: 12px; }
.nav ul { list-style: none; margin: 0; padding: 0; }
.nav ul ul { padding-left: 12px; border-left: 1px solid var(--line); margin: 2px 0 4px 6px; }
.nav .folder { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 8px 0 2px; }
.nav a { display: flex; justify-content: space-between; gap: 6px; padding: 2px 6px; border-radius: 3px; color: var(--fg); text-decoration: none; }
.nav a:hover, .nav a:focus-visible { background: var(--accent-soft); outline: none; }
.nav a.on { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.nav a em { font-style: normal; font-family: var(--mono); font-size: 0.64rem; color: var(--muted); white-space: nowrap; }
main { padding: 28px 40px 80px; min-width: 0; }
@media (max-width: 760px) { main { padding: 20px 16px 60px; } }
.crumb { font-family: var(--mono); font-size: 0.72rem; color: var(--muted); margin-bottom: 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.chip { font-family: var(--mono); font-size: 0.66rem; letter-spacing: .04em; text-transform: uppercase; padding: 1px 7px; border-radius: 3px; border: 1px solid var(--line); color: var(--muted); font-weight: 600; }
.chip.authored { color: var(--au); border-color: var(--au); }
.chip.mixed { color: var(--mix); border-color: var(--mix); background: var(--mix-soft); }
.chip.generated { color: var(--gen-fg); }
article { max-width: 82ch; }
article h1 { font-family: var(--display); font-size: 2rem; line-height: 1.15; margin: 0 0 12px; text-wrap: balance; }
article h2 { font-family: var(--display); font-size: 1.3rem; margin: 30px 0 8px; }
article h3 { font-family: var(--display); font-size: 1.08rem; margin: 22px 0 6px; scroll-margin-top: 16px; }
article p, article li { max-width: 72ch; }
article a { color: var(--accent); }
article a.missing { color: #C2412B; text-decoration: wavy underline; }
article table { border-collapse: collapse; width: 100%; font-size: 0.86rem; margin: 10px 0; display: block; overflow-x: auto; }
article th, article td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
article th { font-family: var(--mono); font-size: 0.68rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); font-weight: 600; white-space: nowrap; }
article code { font-family: var(--mono); font-size: 0.85em; background: var(--accent-soft); padding: 1px 4px; border-radius: 3px; }
article pre { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 12px; overflow-x: auto; }
article pre code { background: none; padding: 0; }
article blockquote { border-left: 3px solid var(--accent); margin: 12px 0; padding: 4px 14px; color: var(--muted); }
.gen { background: var(--gen); border: 1px dashed var(--line); border-radius: 4px; padding: 4px 12px 6px; margin: 12px 0; }
.gen::before { content: "generated from other entities · not edited by hand"; display: block; font-family: var(--mono); font-size: 0.64rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding-top: 4px; }
.mermaid { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 12px; margin: 12px 0; overflow-x: auto; text-align: center; }
.rail { border-left: 1px solid var(--line); padding: 28px 18px 60px; font-size: 0.82rem; min-width: 0; }
.rail h2 { font-family: var(--mono); font-size: 0.68rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }
.rail dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 3px 10px; margin: 0 0 22px; }
.rail dt { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); }
.rail dd { margin: 0; overflow-wrap: anywhere; }
.rail ul { margin: 0; padding-left: 16px; }
.rail a { color: var(--accent); }
.report { font-family: var(--mono); font-size: 0.72rem; color: var(--muted); margin-top: 18px; }
</style>
</head>
<body>
<div class="shell">
  <nav class="nav" aria-label="Vault pages">
    <h1>Unified Booking</h1>
    <div class="sub">INI-002 · mock · made-up company</div>
    <label for="filter" class="sub" style="display:block;margin:0 0 4px">Filter pages</label>
    <input id="filter" type="search" placeholder="e.g. contract, kiosk, EPC-03">
    <div id="tree"></div>
    <div class="report" id="report"></div>
  </nav>
  <main><div class="crumb" id="crumb"></div><div class="chips" id="chips"></div><article id="page"></article></main>
  <aside class="rail" aria-label="Page details">
    <h2>Properties</h2><dl id="props"></dl>
    <h2>Linked from</h2><ul id="backlinks"></ul>
  </aside>
</div>
<script id="vault" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('vault').textContent);
const pages = DATA.pages;
const byName = Object.fromEntries(pages.map(p => [p.name, p]));
const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
if (window.mermaid) mermaid.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'neutral', securityLevel: 'loose' });

function parseFm(fm) {
  const out = {};
  for (const line of fm.split('\n')) {
    const m = line.match(/^([A-Za-z_]+):\s*(.*)$/);
    if (!m) continue;
    let v = m[2].replace(/\s+#.*$/, '').trim();
    if (v.startsWith('"') && v.endsWith('"')) v = v.slice(1, -1);
    if (v.startsWith('[') && v.endsWith(']')) v = v.slice(1, -1).split(',').map(s => s.trim().replace(/^"|"$/g, '')).filter(Boolean);
    out[m[1]] = v;
  }
  return out;
}
pages.forEach(p => { p.meta = parseFm(p.fm); p.title = p.meta.title || (p.body.match(/^#\s+(.+)$/m) || [, p.name])[1]; });

function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function parseLink(inner) {
  inner = inner.replace(/\\\|/g, '|');
  const [target, alias] = inner.split(/\|(.*)/s);
  const [name, anchor] = target.split('#');
  return { name: name.trim(), anchor: (anchor || '').trim(), alias: (alias || '').trim() };
}
let current = null;
function linkHtml(inner) {
  const l = parseLink(inner);
  if (!l.name && current) l.name = current;
  const label = esc(l.alias || (l.anchor ? l.anchor : (byName[l.name] ? byName[l.name].title : l.name)));
  const ok = !!byName[l.name];
  return `<a href="#/${encodeURIComponent(l.name)}${l.anchor ? '::' + encodeURIComponent(l.anchor) : ''}"${ok ? '' : ' class="missing" title="missing page"'}>${label}</a>`;
}
function render(body) {
  let md = body.replace(/\[\[([^\]]+?)\]\]/g, (_, inner) => linkHtml(inner));
  md = md.replace(/<!--\s*generated: do not edit\s*-->/g, '<div class="gen">\n').replace(/<!--\s*\/generated\s*-->/g, '\n</div>');
  return window.marked ? marked.parse(md) : '<pre>' + esc(md) + '</pre>';
}

function buildTree(filter) {
  const root = {};
  const f = (filter || '').toLowerCase();
  for (const p of pages) {
    if (f && !(p.path + ' ' + p.title + ' ' + (p.meta.id || '')).toLowerCase().includes(f)) continue;
    const parts = p.path.split('/'); let node = root;
    for (const part of parts.slice(0, -1)) node = (node[part] = node[part] || {});
    (node.__pages = node.__pages || []).push(p);
  }
  function pageLink(p, label) {
    const a = p.meta.arc42 ? `<em>${esc(p.meta.arc42)}</em>` : '';
    return `<a href="#/${encodeURIComponent(p.name)}" data-name="${esc(p.name)}"><span>${esc(label || p.title)}</span>${a}</a>`;
  }
  function html(node, folderName) {
    const items = [];
    for (const p of (node.__pages || [])) if (p.name !== folderName) items.push({ key: p.name === 'README' ? '00' : p.name, page: p });
    for (const k of Object.keys(node).filter(k => k !== '__pages')) items.push({ key: k, folder: k });
    items.sort((x, y) => x.key.localeCompare(y.key, undefined, { numeric: true }));
    let s = '<ul>';
    for (const it of items) {
      if (it.page) { s += `<li>${pageLink(it.page)}</li>`; continue; }
      const child = node[it.folder];
      const index = (child.__pages || []).find(p => p.name === it.folder);
      const head = index ? pageLink(index) : `<div class="folder">${esc(it.folder)}</div>`;
      s += `<li>${head}${html(child, it.folder)}</li>`;
    }
    return s + '</ul>';
  }
  document.getElementById('tree').innerHTML = html(root);
}

const backlinks = {};
for (const p of pages) for (const m of p.body.matchAll(/\[\[([^\]]+?)\]\]/g)) {
  const n = parseLink(m[1]).name || p.name; (backlinks[n] = backlinks[n] || new Set()).add(p.name);
}

async function show() {
  const h = decodeURIComponent(location.hash.replace(/^#\//, ''));
  const [name, anchor] = h.split('::');
  const p = byName[name] || byName['README'];
  current = p.name;
  document.title = p.title + ' · Unified Booking';
  document.getElementById('crumb').textContent = 'unified-booking / ' + p.path;
  const a = p.meta.authored;
  document.getElementById('chips').innerHTML =
    (a ? `<span class="chip ${esc(a)}">${esc(a)}</span>` : '') +
    (p.meta.type ? `<span class="chip">${esc(p.meta.type)}</span>` : '') +
    (p.meta.arc42 ? `<span class="chip">arc42 ${esc(p.meta.arc42)}</span>` : '') +
    (p.meta.c4 ? `<span class="chip">C4 ${esc(p.meta.c4)}</span>` : '') +
    (p.meta.state ? `<span class="chip">${esc(p.meta.state)}</span>` : '');
  const art = document.getElementById('page');
  art.innerHTML = render(p.body);
  art.querySelectorAll('h1,h2,h3,h4').forEach(el => el.id = slug(el.textContent));
  art.querySelectorAll('pre code.language-mermaid').forEach(code => {
    const div = document.createElement('div'); div.className = 'mermaid'; div.textContent = code.textContent;
    code.parentElement.replaceWith(div);
  });
  if (window.mermaid) { try { await mermaid.run({ nodes: art.querySelectorAll('.mermaid') }); } catch (e) { console.error('mermaid', e); } }
  const props = Object.entries(p.meta).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(Array.isArray(v) ? v.join('; ') : v)}</dd>`).join('');
  document.getElementById('props').innerHTML = props || '<dd>none</dd>';
  const bl = [...(backlinks[p.name] || [])].filter(n => n !== p.name).map(n => byName[n]).filter(Boolean)
    .sort((x, y) => x.title.localeCompare(y.title));
  document.getElementById('backlinks').innerHTML = bl.length ? bl.map(b => `<li><a href="#/${encodeURIComponent(b.name)}">${esc(b.title)}</a></li>`).join('') : '<li>nothing links here</li>';
  document.querySelectorAll('.nav a').forEach(el => el.classList.toggle('on', el.dataset.name === p.name));
  if (anchor) {
    const target = [...art.querySelectorAll('h1,h2,h3,h4')].find(el => el.textContent.trim().startsWith(anchor));
    if (target) { target.scrollIntoView(); return; }
  }
  window.scrollTo(0, 0);
}
buildTree('');
document.getElementById('filter').addEventListener('input', e => { buildTree(e.target.value); show(); });
document.getElementById('report').textContent = DATA.report;
window.addEventListener('hashchange', show);
show();
</script>
</body>
</html>
"""


def main():
    write_status(load_pages())
    pages = load_pages()
    count, broken, ambiguous = check_links(pages)
    lines = [f"{len(pages)} pages, {count} links, {len(broken)} broken, {len(ambiguous)} ambiguous names"]
    for src, link, why in broken:
        lines.append(f"BROKEN  {src}: {link} ({why})")
    for name, paths in ambiguous:
        lines.append(f"AMBIGUOUS  {name}: {', '.join(paths)}")
    report = "\n".join(lines)
    print(report)
    data = {"pages": pages, "report": lines[0]}
    payload = json.dumps(data).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"wrote {OUT.relative_to(HERE)}")
    return 1 if broken or ambiguous else 0


if __name__ == "__main__":
    sys.exit(main())
