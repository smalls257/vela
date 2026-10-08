"""Vault model to one offline HTML file. Pure: the CLI passes in the library
sources and the build stamp, and writes the result.

The file needs no network: marked and mermaid are inlined and fonts are system
fonts. Session records and voice files are left out, and links to them render
as plain text.
"""
import base64
import hashlib
import html as html_lib
import json
import re

from planner import override, reading

EXCLUDED_FOLDERS = ("sessions/",)
DRAFT_STATES = ("inkling", "assumption", "fact", "proposed", "draft", "reopened")
START_PAGE = "01-goals"


def bundled(vault):
    return [p for p in vault.pages if not p.path.startswith(EXCLUDED_FOLDERS)]


def excluded_names(vault):
    names = {p.name.lower() for p in vault.pages if p.path.startswith(EXCLUDED_FOLDERS)}
    return names | set(vault.other_names)

# Vault markdown is untrusted input. Raw HTML would run in the reader's browser,
# so every "<" outside code is escaped before the text is embedded. Only the
# comment markers that `planner render` writes are left alone.
GENERATED_MARKER = re.compile(
    r"<!--\s*/?generated:[a-z0-9-]+(?: sha=[0-9a-f]{8}: do not edit, run planner render)?\s*-->")
FENCE = re.compile(r"^\s{0,3}(```|~~~)")
CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
MD_LINK = re.compile(r"(!?)\[([^\]\n]*)\]\(((?:[^()\n]|\([^()\n]*\))*)\)")
SAFE_LINK_SCHEMES = ("http:", "https:", "mailto:")


def scheme_of(url):
    """Lower-case scheme of a URL as a browser reads it: whitespace and control
    characters inside a URL are ignored, so "java\tscript:" is "javascript:"."""
    squeezed = re.sub(r"[\x00-\x20]", "", html_lib.unescape(url)).lower()
    match = re.match(r"([a-z][a-z0-9+.-]*):", squeezed)
    return match.group(0) if match else ""


def neutralise_links(text):
    def swap(m):
        bang, label, dest = m.group(1), m.group(2), m.group(3)
        url = dest.strip().lstrip("<")
        scheme = scheme_of(url)
        if bang:
            remote = bool(scheme) or url.startswith(("/", "\\")) or re.sub(r"[\x00-\x20]", "", url).startswith("//")
            return f"{label} ({url})" if remote else m.group(0)
        if scheme and scheme not in SAFE_LINK_SCHEMES:
            return label
        return m.group(0)
    return MD_LINK.sub(swap, text)


def neutralise_prose(text):
    pieces, last = [], 0
    for marker in GENERATED_MARKER.finditer(text):
        pieces.append(neutralise_links(text[last:marker.start()]).replace("<", "&lt;"))
        pieces.append(marker.group(0))
        last = marker.end()
    pieces.append(neutralise_links(text[last:]).replace("<", "&lt;"))
    return "".join(pieces)


def neutralise(markdown):
    """Defence in depth ahead of the browser, whose Content-Security-Policy and
    sanitiser are the guarantee: no raw HTML, no script or data links, and no
    images that fetch. Code fences and code spans are left as written."""
    out, in_fence, fence_mark = [], False, ""
    for line in markdown.split("\n"):
        fence = FENCE.match(line)
        if in_fence:
            out.append(line)
            if fence and fence.group(1) == fence_mark:
                in_fence = False
            continue
        if fence:
            in_fence, fence_mark = True, fence.group(1)
            out.append(line)
            continue
        pieces, last = [], 0
        for span in CODE_SPAN.finditer(line):
            pieces.append(neutralise_prose(line[last:span.start()]))
            pieces.append(span.group(0))
            last = span.end()
        pieces.append(neutralise_prose(line[last:]))
        out.append("".join(pieces))
    return "\n".join(out)


def body_of(page):
    """The page text after its frontmatter."""
    lines = page.text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:]).lstrip("\n")
    return page.text


def link_problems(vault):
    """Links in bundled pages that would not resolve inside the viewer."""
    pages = {p.name.lower(): p for p in bundled(vault)}
    skipped = excluded_names(vault)
    problems = []
    for page in bundled(vault):
        for link in page.links:
            name = (link.target or page.name).lower()
            if name in skipped:
                continue
            target = pages.get(name)
            if target is None:
                problems.append(f"{page.path}:{link.line}: [[{link.target}]] is not in the viewer")
            elif link.anchor and not link.anchor.startswith("^") and link.anchor not in [h.text for h in target.headings]:
                problems.append(f"{page.path}:{link.line}: #{link.anchor} matches no heading in {target.name}")
    return problems


def override_lines(page):
    """One entry per well-formed Override on the page, page level and items alike. The
    parser is planner.override's, so the viewer cannot disagree with `planner check`."""
    lines = []
    for found, behalf in override.decisions(page):
        pending = behalf is not None and not behalf.confirmed_by
        for item in found:
            lines.append({"rules": ", ".join(item.rules), "by": item.by, "date": item.date, "reason": item.reason,
                          "pending_for": " ".join(behalf.owners) if pending else ""})
    return lines


def page_data(page):
    state = str(page.meta.get("state", ""))
    return {
        "path": page.path,
        "name": page.name,
        "title": str(page.meta.get("title") or page.name),
        "meta": {k: (v if isinstance(v, (str, list)) else str(v)) for k, v in page.meta.items()},
        "body": reading.arrange(neutralise(body_of(page))),
        "not_started": reading.not_started(body_of(page)),
        "headings": [h.text for h in page.headings],
        "draft": state in DRAFT_STATES,
        "state": state,
        "overrides": override_lines(page),
    }


JSON_UNSAFE = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026", "\u2028": "\\u2028", "\u2029": "\\u2029"}


def script_json(data):
    """JSON that cannot end, or confuse, the <script> element holding it: every
    "<" is a \\u003c escape, so "<!--<script" in a page cannot start the HTML
    parser's double-escaped script state."""
    text = json.dumps(data, ensure_ascii=False)
    return "".join(JSON_UNSAFE.get(ch, ch) for ch in text)


PLACEHOLDER = re.compile(r"__(TITLE|CSP|MARKED|MERMAID|DATA|APP)__")


def script_hash(source):
    return "'sha256-" + base64.b64encode(hashlib.sha256(source.encode("utf-8")).digest()).decode("ascii") + "'"


def content_security_policy(inline_scripts):
    """The structural guarantee that the file never touches the network, whatever
    a page or diagram manages to put into the DOM. Only the viewer's own inline
    scripts run (by hash). Mermaid needs no 'unsafe-eval'; the viewer tests render
    its diagrams under this policy."""
    hashes = " ".join(script_hash(source) for source in inline_scripts)
    return ("default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'; "
            f"script-src {hashes}; connect-src 'none'; frame-src 'none'; object-src 'none'; "
            "base-uri 'none'; form-action 'none'")


def script_safe(source):
    return source.replace("</script", "<\\/script")


def build(vault, marked_js, mermaid_js, stamp):
    """(html text, problems). `stamp` is {"commit", "date", "repo", "errors", "warnings"}."""
    problems = link_problems(vault)
    data = {
        "title": str(vault.config.get("title", "")),
        "initiative": str(vault.config.get("initiative", "")),
        "start": START_PAGE,
        "excluded": sorted(excluded_names(vault)),
        "stamp": stamp,
        "pages": [page_data(p) for p in sorted(bundled(vault), key=lambda p: p.path)],
    }
    payload = script_json(data)
    scripts = {"MARKED": script_safe(marked_js), "MERMAID": script_safe(mermaid_js), "APP": APP_JS}
    values = {"TITLE": html_lib.escape(data["title"]), "DATA": payload, "CSP": content_security_policy(scripts.values()),
              **scripts}
    html = PLACEHOLDER.sub(lambda m: values[m.group(1)], TEMPLATE)
    return html, problems


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="__CSP__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg: #F4F6F9; --surface: #FFFFFF; --fg: #19212D; --muted: #5A6474; --line: #D3D9E2;
  --accent: #2448B8; --accent-soft: #E2E8F8; --gen: #F1F3F6; --warn: #8A4B00; --warn-soft: #FBEFD9;
  --bad: #B3261E; --bad-soft: #FBE4E2;
  --body: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0F131A; --surface: #161C26; --fg: #E5E9EF; --muted: #9AA4B3; --line: #2D3543;
    --accent: #86A2FF; --accent-soft: #1D2742; --gen: #1B222D; --warn: #F0B65C; --warn-soft: #2E2210;
    --bad: #FF8A80; --bad-soft: #3A1714; color-scheme: dark;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15.5px; line-height: 1.6; }
.shell { display: grid; grid-template-columns: 290px minmax(0, 1fr) 260px; min-height: 100%; }
@media (max-width: 1100px) { .shell { grid-template-columns: 260px minmax(0, 1fr); } .rail { grid-column: 2; } }
@media (max-width: 760px) { .shell { grid-template-columns: 1fr; } .rail { grid-column: 1; } .nav { position: static; height: auto; max-height: 40vh; } }
.nav { position: sticky; top: 0; height: 100vh; overflow-y: auto; border-right: 1px solid var(--line); background: var(--surface); padding: 18px 14px 40px; font-size: 0.84rem; }
.nav h1 { font-size: 1.05rem; margin: 0 0 4px; }
.stamp { font-family: var(--mono); font-size: 0.68rem; color: var(--muted); margin-bottom: 12px; overflow-wrap: anywhere; }
.nav input { width: 100%; padding: 6px 8px; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); color: var(--fg); font: inherit; margin-bottom: 12px; }
.nav ul { list-style: none; margin: 0; padding: 0; }
.nav ul ul { padding-left: 12px; border-left: 1px solid var(--line); margin: 2px 0 4px 6px; }
.nav .folder { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; color: var(--muted); margin: 8px 0 2px; }
.nav a { display: block; padding: 2px 6px; border-radius: 3px; color: var(--fg); text-decoration: none; }
.nav a:hover, .nav a:focus-visible { background: var(--accent-soft); outline: none; }
.nav a.on { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
main { padding: 28px 40px 80px; min-width: 0; }
@media (max-width: 760px) { main { padding: 20px 16px 60px; } }
.crumb { font-family: var(--mono); font-size: 0.72rem; color: var(--muted); margin-bottom: 10px; }
.status-line { color: var(--muted); font-size: 0.85rem; margin-bottom: 4px; }
details { border-top: 1px solid var(--line); margin-top: 24px; padding-top: 8px; }
summary { cursor: pointer; color: var(--muted); font-weight: 600; }
sup { font-size: 0.7rem; margin-left: 2px; }
sup a { color: var(--muted); }
.not-started { color: var(--muted); font-size: 0.8rem; margin-top: 12px; }
article { max-width: 82ch; }
article h1 { font-size: 2rem; line-height: 1.15; margin: 0 0 12px; }
article h2 { font-size: 1.3rem; margin: 30px 0 8px; }
article h3 { font-size: 1.08rem; margin: 22px 0 6px; scroll-margin-top: 16px; }
article a { color: var(--accent); }
article a.missing { color: var(--bad); text-decoration: wavy underline; }
article .offline-link { border-bottom: 1px dotted var(--muted); }
article table { border-collapse: collapse; width: 100%; font-size: 0.86rem; margin: 10px 0; display: block; overflow-x: auto; }
article th, article td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
article th { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; color: var(--muted); }
article code { font-family: var(--mono); font-size: 0.85em; background: var(--accent-soft); padding: 1px 4px; border-radius: 3px; }
article pre { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 12px; overflow-x: auto; }
article pre code { background: none; padding: 0; }
.gen { background: var(--gen); border: 1px dashed var(--line); border-radius: 4px; padding: 4px 12px 6px; margin: 12px 0; }
.gen::before { content: "generated by planner render, not edited by hand"; display: block; font-family: var(--mono); font-size: 0.64rem; text-transform: uppercase; color: var(--muted); padding-top: 4px; }
.mermaid { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 12px; margin: 12px 0; overflow-x: auto; text-align: center; }
.diagram-error { border: 1px solid var(--bad); background: var(--bad-soft); color: var(--bad); border-radius: 4px; padding: 10px 12px; margin: 12px 0; font-family: var(--mono); font-size: 0.8rem; white-space: pre-wrap; }
.rail { border-left: 1px solid var(--line); padding: 28px 18px 60px; font-size: 0.82rem; min-width: 0; }
.rail h2 { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }
.rail dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 3px 10px; margin: 0 0 22px; }
.rail dt { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); }
.rail dd { margin: 0; overflow-wrap: anywhere; }
.rail ul { margin: 0; padding-left: 16px; }
.rail a { color: var(--accent); }
</style>
<script>__MARKED__</script>
<script>__MERMAID__</script>
</head>
<body>
<div class="shell">
  <nav class="nav" aria-label="Vault pages">
    <h1 id="vault-title"></h1>
    <div class="stamp" id="stamp"></div>
    <div class="stamp" id="health"></div>
    <label for="filter" class="stamp" style="display:block;margin:0 0 4px">Filter pages</label>
    <input id="filter" type="search" placeholder="e.g. contract, kiosk, EPC-03">
    <div id="tree"></div>
  </nav>
  <main><div class="crumb" id="crumb"></div><div id="banner"></div><article id="page"></article></main>
  <aside class="rail" aria-label="Page details">
    <h2>Properties</h2><dl id="props"></dl>
    <h2>Linked from</h2><ul id="backlinks"></ul>
  </aside>
</div>
<script id="vault" type="application/json">__DATA__</script>
<script>__APP__</script>
</body>
</html>
"""


APP_JS = r"""
// Grab every element the viewer writes into before any page content exists, so
// nothing a page contains can shadow them.
const ui = Object.fromEntries(['vault', 'vault-title', 'stamp', 'health', 'filter', 'tree', 'crumb', 'banner', 'page', 'props', 'backlinks']
  .map(id => [id, document.getElementById(id)]));
const DATA = JSON.parse(ui.vault.textContent);
const pages = DATA.pages;
const byName = new Map(pages.map(p => [p.name.toLowerCase(), p]));
const pageNamed = name => byName.get(String(name).toLowerCase());
// Classes the viewer puts on its own markup carry a per-load secret suffix, so
// the sanitiser can tell them from a class a page tries to claim.
const NONCE = Array.from(crypto.getRandomValues(new Uint32Array(3)), n => n.toString(36)).join('');
const OWN_CLASS = { ['gen-' + NONCE]: 'gen', ['offline-link-' + NONCE]: 'offline-link', ['missing-' + NONCE]: 'missing' };
const excluded = new Set(DATA.excluded);
const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
if (window.mermaid) mermaid.initialize({
  startOnLoad: false, theme: dark ? 'dark' : 'neutral', securityLevel: 'strict', htmlLabels: false,
  flowchart: { htmlLabels: false }, sequence: { useMaxWidth: true }, class: { htmlLabels: false }, state: { htmlLabels: false },
  secure: ['secure', 'securityLevel', 'startOnLoad', 'maxTextSize', 'maxEdges', 'themeCSS', 'themeVariables', 'htmlLabels',
    'flowchart', 'class', 'state', 'fontFamily', 'theme'],
});
ui['vault-title'].textContent = DATA.title;
ui.stamp.textContent =
  `${DATA.initiative} · Built from ${DATA.stamp.commit} on ${DATA.stamp.date}. Newer versions: ${DATA.stamp.repo}`;
if (Number.isInteger(DATA.stamp.errors) && Number.isInteger(DATA.stamp.warnings)) {
  ui.health.textContent = `Check at build time: ${DATA.stamp.errors} errors, ${DATA.stamp.warnings} warnings.`;
  if (DATA.stamp.errors > 0) { ui.health.style.color = 'var(--bad)'; ui.health.style.fontWeight = '700'; }
}

function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
// Keeps entities already written in the text (the build step writes &lt;) so a label is not escaped twice.
function escLabel(s) {
  return String(s).replace(/&(?!(?:[a-z][a-z0-9]*|#[0-9]+|#x[0-9a-f]+);)/gi, '&amp;').replace(/[<>"]/g, c => ({ '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}
function parseLink(inner) {
  inner = inner.replace(/\\\|/g, '|');
  const bar = inner.indexOf('|');
  const target = bar < 0 ? inner : inner.slice(0, bar);
  const alias = bar < 0 ? '' : inner.slice(bar + 1);
  const hash = target.indexOf('#');
  return { name: (hash < 0 ? target : target.slice(0, hash)).trim(), anchor: hash < 0 ? '' : target.slice(hash + 1).trim(), alias: alias.trim() };
}
let current = null;
function linkHtml(inner) {
  const l = parseLink(inner);
  const name = (l.name || current).toLowerCase();
  const target = pageNamed(name);
  const label = l.alias || l.anchor ? escLabel(l.alias || l.anchor) : esc(target ? target.title : l.name);
  if (!target && excluded.has(name)) return `<span class="offline-link-${NONCE}" title="Not in this viewer">${label}</span>`;
  if (!target) return `<a class="missing-${NONCE}" title="missing page">${label}</a>`;
  return `<a href="#/${encodeURIComponent(target.name)}${l.anchor ? '::' + encodeURIComponent(l.anchor) : ''}">${label}</a>`;
}
function decoded(s) { const t = document.createElement('textarea'); t.innerHTML = String(s); return t.value; }
function hrefOk(href) {
  const t = decoded(href).replace(/[\u0000-\u0020]/g, '');
  if (/^[\\/]{2}/.test(t)) return false;
  const m = /^([a-z][a-z0-9+.-]*):/i.exec(t);
  return !m || /^(https?|mailto)$/i.test(m[1]);
}
function imageFetches(href) {
  const t = decoded(href).replace(/[\u0000-\u0020]/g, '');
  return /^([a-z][a-z0-9+.-]*:|\/|\\)/i.test(t);
}
// Second line of defence behind the build-time neutralise(): reference-style and
// entity-encoded links reach marked in forms the build step does not rewrite.
if (window.marked) marked.use({ renderer: {
  link(href, title, text) { return hrefOk(href) ? false : text; },
  image(href, title, text) { return imageFetches(href) ? esc(text + ' (' + href + ')') : false; },
} });
// The sanitiser is the guarantee. Page markdown is untrusted, and marked and the
// build step can disagree about what is code, so everything marked produces is
// parsed into an inert <template> and rebuilt from an allowlist before it is shown.
const HTML_OK = new Set(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'strong', 'em', 'code', 'pre',
  'blockquote', 'hr', 'br', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'del', 'div', 'span', 'details', 'summary', 'sup']);
const HTML_DROP = new Set(['script', 'style', 'iframe', 'svg', 'img', 'object', 'embed', 'template', 'noscript', 'textarea',
  'title', 'math', 'video', 'audio', 'link', 'meta', 'base', 'form', 'select', 'option', 'button', 'input', 'frame',
  'frameset', 'applet', 'canvas', 'picture', 'source', 'track', 'map', 'area', 'head']);
const CLASS_OK = /^language-[a-z0-9_+-]+$/;
const XHTML = 'http://www.w3.org/1999/xhtml';
function cleanAttributes(el, tag) {
  for (const attr of [...el.attributes]) {
    const name = attr.name.toLowerCase();
    let keep = false;
    if (name === 'href') keep = tag === 'a' && hrefOk(attr.value.trim());
    else if (name === 'title') keep = tag === 'a' || tag === 'span';
    else if (name === 'class') {
      const classes = attr.value.split(/\s+/).map(c => OWN_CLASS[c] || (CLASS_OK.test(c) ? c : '')).filter(Boolean);
      keep = classes.length > 0;
      if (keep) el.setAttribute('class', classes.join(' '));
    }
    if (!keep) el.removeAttribute(attr.name);
  }
}
function cleanChildren(parent) {
  for (const node of [...parent.childNodes]) {
    if (node.nodeType === Node.TEXT_NODE) continue;
    if (node.nodeType !== Node.ELEMENT_NODE) { node.remove(); continue; }
    const tag = node.localName.toLowerCase();
    if (node.namespaceURI !== XHTML || HTML_DROP.has(tag)) { node.remove(); continue; }
    if (!HTML_OK.has(tag)) { node.replaceWith(document.createTextNode(node.textContent)); continue; }
    cleanAttributes(node, tag);
    cleanChildren(node);
  }
}
function sanitiseHtml(html) {
  const holder = document.createElement('template');
  holder.innerHTML = html;
  cleanChildren(holder.content);
  return holder.content;
}
const SVG_DROP = new Set(['script', 'image', 'foreignobject', 'iframe', 'object', 'embed', 'animate', 'set', 'animatemotion', 'animatetransform', 'video', 'audio']);
// Style text that could name an off-page resource is dropped whole. Escapes (\75rl) and
// image-set() are refused too, because deciding what such CSS means is the regex trap.
function offPageUrl(css) { return /@import|\\|image-set|cross-fade|element\(|\bsrc\(|url\(\s*(?!['"]?#)/i.test(css); }
function cleanSvgChildren(parent) {
  for (const el of [...parent.children]) {
    const tag = el.localName.toLowerCase();
    if (SVG_DROP.has(tag)) { el.remove(); continue; }
    for (const attr of [...el.attributes]) {
      const name = attr.name.toLowerCase();
      const off = (name === 'href' || name === 'xlink:href') && !attr.value.trim().startsWith('#');
      if (name.startsWith('on') || off || (name === 'style' && offPageUrl(attr.value))) el.removeAttribute(attr.name);
    }
    if (tag === 'style' && offPageUrl(el.textContent)) { el.remove(); continue; }
    cleanSvgChildren(el);
  }
}
function sanitiseSvg(svg) {
  const holder = document.createElement('template');
  holder.innerHTML = svg;
  cleanSvgChildren(holder.content);
  return holder.content;
}
// A diagram cannot carry its own configuration, and no attempt is made to clean
// it: init directives and frontmatter are refused so the reader sees why.
function hasDiagramConfig(source) { return /%%\{/.test(source) || /^\s*---/.test(source); }
function toNodes(body) {
  let md = body.replace(/\[\[([^\]]+?)\]\]/g, (_, inner) => linkHtml(inner));
  md = md.replace(/<!--\s*generated:[a-z0-9-]+ sha=[0-9a-f]{8}: do not edit, run planner render\s*-->/g, '<div class="gen-' + NONCE + '">\n')
         .replace(/<!--\s*\/generated:[a-z0-9-]+\s*-->/g, '\n</div>');
  return sanitiseHtml(window.marked ? marked.parse(md) : '<pre>' + esc(md) + '</pre>');
}

function buildTree(filter) {
  const root = {};
  const f = (filter || '').toLowerCase();
  for (const p of pages) {
    if (p.not_started) continue;
    if (f && !(p.path + ' ' + p.title + ' ' + (p.meta.id || '')).toLowerCase().includes(f)) continue;
    const parts = p.path.split('/'); let node = root;
    for (const part of parts.slice(0, -1)) node = (node[part] = node[part] || {});
    (node.__pages = node.__pages || []).push(p);
  }
  const pageLink = p => `<a href="#/${encodeURIComponent(p.name)}" data-name="${esc(p.name)}">${esc(p.title)}</a>`;
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
      s += `<li>${index ? pageLink(index) : `<div class="folder">${esc(it.folder)}</div>`}${html(child, it.folder)}</li>`;
    }
    return s + '</ul>';
  }
  const idle = pages.filter(p => p.not_started);
  ui.tree.innerHTML = html(root) + (idle.length ? `<div class="not-started">Not started: ${idle.map(p =>
    `<a href="#/${encodeURIComponent(p.name)}">${esc(p.title)}</a>`).join(', ')}</div>` : '');
}

const backlinks = new Map();
for (const p of pages) for (const m of p.body.matchAll(/\[\[([^\]]+?)\]\]/g)) {
  const n = (parseLink(m[1]).name || p.name).toLowerCase();
  if (!backlinks.has(n)) backlinks.set(n, new Set());
  backlinks.get(n).add(p.name);
}

let diagramCount = 0;
async function drawDiagrams(art) {
  for (const code of [...art.querySelectorAll('pre code.language-mermaid')]) {
    const source = code.textContent;
    const box = document.createElement('div');
    code.parentElement.replaceWith(box);
    if (!window.mermaid) { box.className = 'diagram-error'; box.textContent = 'Diagram not drawn: the Mermaid library did not load.\n\n' + source; continue; }
    if (hasDiagramConfig(source)) { box.className = 'diagram-error'; box.textContent = "Diagram not drawn: diagram directives aren't allowed in the offline viewer\n\n" + source; continue; }
    try {
      const { svg } = await mermaid.render('diagram-' + (++diagramCount), source);
      box.className = 'mermaid'; box.replaceChildren(sanitiseSvg(svg));
    } catch (e) {
      box.className = 'diagram-error';
      box.textContent = 'Diagram not drawn: ' + (e && e.message ? e.message : String(e)) + '\n\n' + source;
    }
  }
}

async function show() {
  let h = '';
  try { h = decodeURIComponent(location.hash.replace(/^#\//, '')); } catch (e) { h = ''; }
  const [name, anchor] = h.split('::');
  const p = pageNamed(name || DATA.start) || pageNamed(DATA.start) || pages[0];
  current = p.name;
  document.title = p.title + ' · ' + DATA.title;
  ui.crumb.textContent = p.path;
  const pending = p.overrides.filter(o => o.pending_for).map(o => o.pending_for);
  ui.banner.innerHTML = (p.draft ? `<div class="status-line">${esc(p.state)}: not agreed yet</div>` : '') +
    (pending.length ? `<div class="status-line">decided on behalf of ${esc([...new Set(pending)].join(', '))}, not yet confirmed</div>` : '');
  const art = ui.page;
  art.replaceChildren(toNodes(p.body));
  art.querySelectorAll('h1,h2,h3,h4').forEach(h => h.id = 'h-' + slug(h.textContent));
  await drawDiagrams(art);
  const props = Object.entries(p.meta).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(Array.isArray(v) ? v.join(', ') : v)}</dd>`).join('');
  ui.props.innerHTML = props || '<dd>none</dd>';
  const bl = [...(backlinks.get(p.name.toLowerCase()) || [])].filter(n => n !== p.name).map(n => pageNamed(n)).filter(Boolean)
    .sort((x, y) => x.title.localeCompare(y.title));
  ui.backlinks.innerHTML = bl.length ? bl.map(b => `<li><a href="#/${encodeURIComponent(b.name)}">${esc(b.title)}</a></li>`).join('') : '<li>nothing links here</li>';
  document.querySelectorAll('.nav a').forEach(el => el.classList.toggle('on', el.dataset.name === p.name));
  if (anchor) {
    const heads = [...art.querySelectorAll('h1,h2,h3,h4')];
    const bare = anchor.replace(/^(?:[A-Z][A-Z0-9]*-\d+(?:\.FR\d+)?|G\d+)\s+/, '');
    const target = heads.find(el => el.textContent.trim() === anchor) || heads.find(el => el.textContent.trim() === bare)
      || heads.find(el => el.textContent.trim().startsWith(anchor));
    if (target) { target.scrollIntoView(); return; }
  }
  window.scrollTo(0, 0);
}
buildTree('');
ui.filter.addEventListener('input', e => buildTree(e.target.value));
window.addEventListener('hashchange', show);
show();
"""
