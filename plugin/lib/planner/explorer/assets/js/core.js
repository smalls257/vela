"use strict";
/* Vault explorer, shared core. Every fact on this page comes from the JSON build.py wrote from the planner's own
   model; the lights are attention.lights, the one rule for what needs the lead. This script arranges and draws. */
window.__errors = [];
window.addEventListener("error", (ev) => window.__errors.push(String(ev.message)));
window.addEventListener("unhandledrejection", (ev) => window.__errors.push("promise: " + String(ev.reason && ev.reason.message || ev.reason)));

const D = JSON.parse(document.getElementById("data").textContent);
const E = D.entities;
const HASH = new URLSearchParams((location.hash || "").slice(1));
/* The address bar's hash again, in the same object, when a pasted link or Back changes it. */
function reloadHash() {
  for (const k of [...HASH.keys()]) HASH.delete(k);
  new URLSearchParams((location.hash || "").slice(1)).forEach((v, k) => HASH.append(k, v));
}
const STILL = HASH.has("still") || HASH.has("selftest");  // screenshots and checks: no transitions to wait out

/* ------------------------------------------------------------------ small helpers */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
function h(tag, attrs, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;  // only ever HTML that build.py escaped
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.appendChild(typeof kid === "string" || typeof kid === "number" ? document.createTextNode(String(kid)) : kid);
  }
  return node;
}
/* The one empty state. A view with nothing to draw says what is missing, in plain words, and which planner step
   writes it, so a reader on a live call can tell "not recorded yet" from "broken". `writer` is a slash command, or a list of them.
   Every view uses this; none writes its own "nothing here" block. */
function emptyState(missing, detail, writer, extraClass) {
  return h("div", { class: "empty-state" + (extraClass ? " " + extraClass : ""), "data-empty": missing },
    h("b", {}, missing), detail ? " " + detail : "",
    writer ? h("div", { class: "es-writer" }, "Written by ", [].concat(writer).flatMap((w, i) => [i ? " and " : "", h("code", {}, w)]), ".") : null);
}
const SVGNS = "http://www.w3.org/2000/svg";
function s(tag, attrs, parent) {
  const node = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v !== undefined && v !== null) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
/* The files the page links to: Open the file, the design doc, the plan, the tickets. Opened as a file, a path relative
   to the page works. Served from this machine, the helper answers /vault-file/<path> for the vault's own files and
   nothing else (vault_files.py), so a design or plan kept in a team repo has no link there and says why. */
const SERVED_HERE = /^https?:$/.test(location.protocol) && ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
const urlPath = (path) => path.split("/").map(encodeURIComponent).join("/");  // per segment, so a # or ? in a file name stays in the name
function openHref(relative, inVault) {
  if (SERVED_HERE) return inVault ? "/vault-file/" + urlPath(inVault) : null;
  return relative ? urlPath(relative) : null;
}
function openLink(kids, relative, inVault, title, cls = "btn quiet") {
  const href = openHref(relative, inVault);
  if (href) return h("a", { class: cls, href, target: "_blank", title }, ...kids);
  if (!SERVED_HERE) return null;
  return h("span", { class: cls + " off", "aria-disabled": "true", title: "This helper opens only files inside the vault, and this one is outside it. Open it from your editor, or open the page as a file." }, ...kids, " (outside the vault)");
}
const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;
const shorten = (t, n) => { t = t || ""; return t.length > n ? t.slice(0, n - 1).trimEnd() + "…" : t; };
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hash = (t) => { let x = 7; for (const ch of t) x = (x * 31 + ch.charCodeAt(0)) >>> 0; return x; };
const DAY = 86400000;
const dayNum = (iso) => Math.round(Date.parse(iso + "T00:00:00Z") / DAY);
const TODAY = dayNum(D.today);
const isDate = (t) => /^\d{4}-\d{2}-\d{2}$/.test(t || "");
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const day = (iso) => isDate(iso) ? `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]}` : (iso || "no date");
/* Motion is off for screenshots and checks (STILL), in the Plain view (FX, fx.js), and when the system asks for less. */
const reducedMotion = () => STILL || (typeof FX !== "undefined" && !FX.on) || matchMedia("(prefers-reduced-motion: reduce)").matches;
/* Glow (halos, lit shadows) is part of the effects; Plain keeps every colour and drops the glow. */
const glowOn = () => typeof FX === "undefined" || FX.on;
function dueText(iso) {
  if (!isDate(iso)) return iso ? `ask by "${iso}"` : "no ask-by date";
  const d = dayNum(iso) - TODAY;
  if (d < 0) return `${plural(-d, "day")} overdue`;
  if (d === 0) return "due today";
  return `due in ${plural(d, "day")}`;
}
/* Settings this browser keeps (effects, theme, motion): a browser that keeps none says so in the console, and the
   page carries on with its defaults. */
const Settings = {
  read(k) { try { return localStorage.getItem(k); } catch (e) { console.warn("[settings] this browser keeps no settings:", e.message); return null; } },
  /* JSON saved by this page (the asks board, rehearsal tries). A value that will not parse is not silently replaced by an
     empty one: it is kept under "<key>.unreadable" so the next save cannot overwrite it, the console says so, and a note shows once. */
  readJson(k, fallback, what) {
    const raw = this.read(k);
    if (raw === null) return fallback;
    try { return JSON.parse(raw) ?? fallback; } catch (e) {
      console.warn(`[settings] ${what} saved in this browser cannot be read (${e.message}); the unreadable copy is kept under ${k}.unreadable`);
      this.write(k + ".unreadable", raw);
      toast(`Could not read ${what} saved in this browser, so it starts empty. The old copy is kept.`);
      return fallback;
    }
  },
  write(k, v) { try { localStorage.setItem(k, v); } catch (e) { console.warn("[settings] this browser keeps no settings:", e.message); } },
};
/* A vault that gains a vault_id in .planner.yaml (E18) keeps what this browser saved under the id it had before: the
   asks board, the layout, the Ask conversations and the rehearsals are copied to the new id once, never moved or
   overwritten, so going back to an older page still finds them. Returns the keys it copied. */
function migrateSaved(legacy, current, store = localStorage) {
  if (!legacy || legacy === current) return [];
  const moves = [];
  try {
    for (let i = 0; i < store.length; i++) {
      const key = store.key(i);
      const to = [["asks:", ""], ["explorer.layout.", ""], ["explorer.ask.", ""], ["rehearse:", ":"]].map(([p, tail]) => (key === p + legacy || (tail && key.startsWith(p + legacy + tail))) ? p + current + key.slice((p + legacy).length) : null).find(Boolean);
      if (to && store.getItem(to) === null) moves.push([key, to]);
    }
    for (const [from, to] of moves) store.setItem(to, store.getItem(from));
  } catch (e) { console.warn("[settings] could not move what this browser saved under the vault's old id:", e.message); }
  return moves.map(([, to]) => to);
}
migrateSaved(D.legacyVaultId, D.vaultId);
const relDue = (iso) => { if (!isDate(iso)) return "no date"; const d = dayNum(iso) - TODAY; return d < 0 ? `${-d} d late` : d === 0 ? "today" : `in ${d} d`; };

/* ------------------------------------------------------------------ the lamp vocabulary: attention.py's levels */
// Colour is never the only signal: each level has a word, and the maps add shape and motion. The colours here are
// Console's; theme.js re-reads them from the theme's --warning, --caution, ... so a lamp means the same in every room.
const LIGHT = {
  warning: { colour: "#ff5a48", ink: "#2a0703", word: "Overdue", say: "an open question holding it is past its ask-by date" },
  caution: { colour: "#ffb21e", ink: "#2b1a00", word: "Needs you", say: "not decided yet, or held by an open question" },
  pending: { colour: "#b79cff", ink: "#150c33", word: "Pending approval", say: "a reader decided this and the owner has not reviewed it: it looks settled and is not" },
  unexamined: { colour: "#52c8ff", ink: "#04202e", word: "Never examined", say: "no state recorded, or a concern nobody has looked at: dark has to be earned" },
  override: { colour: "#f2f1e8", ink: "#1d1d18", word: "Overridden", say: "a rule was set aside by the lead: visible, not an alarm" },
  dark: { colour: "#2a3236", ink: "#9aa7ad", word: "Settled", say: "settled, and nothing holds it" },
};
const LEVELS = D.levels;  // most urgent first, from attention.LEVELS
const rank = (level) => LEVELS.length - LEVELS.indexOf(level);
const lightOf = (key) => D.lights[key] || null;
const levelOf = (key) => (lightOf(key) || { level: "dark" }).level;
/* Breathing: slow and soft when an answer is weeks away, quicker and brighter as it falls due. */
const pulsePeriod = (urgency) => Math.round(5200 - 3400 * clamp(urgency || 0, 0, 1));
const ASK = Object.fromEntries(D.asks.map((u) => [u.id, u]));
const unknownLevel = (id) => { const u = ASK[id]; if (!u) return "dark"; return u.state === "open" ? u.light.level : "resolved"; };
/* The pending-approval mark in words: a clock glyph and the text, with who and when on hover, so colour is never alone. */
const pendingPill = (p) => h("span", { class: "pill pending", title: p ? `Decided by ${p.by} on ${p.date}; the owner has not reviewed it` : LIGHT.pending.say }, "◷ Pending approval");
function lampEl(level, title) { return h("span", { class: "lamp " + level, title: title || (LIGHT[level] ? LIGHT[level].word : level) }); }
function reasonText(r) {
  if (r.kind === "held" && r.unknown && ASK[r.unknown]) {
    const u = ASK[r.unknown], e = E[r.unknown];
    const who = r.ask || u.ask.name;
    return `${r.unknown} ${e ? e.title : ""}: ask ${who} by ${day(u.askBy)}${r.text.includes(" through ") ? ", through " + r.text.split(" through ")[1].split(";")[0] : ""}`;
  }
  return r.text;
}

/* ------------------------------------------------------------------ the record, indexed */
const KIND_WORD = { app: "App", runtime: "Runtime page", contract: "Contract", party: "Outside party", external: "Outside provider",
  unknown: "Open question", risk: "Risk", epic: "Epic", capability: "Capability", flow: "Flow", requirement: "Requirement",
  decision: "Decision", concern: "Concern", session: "Session", section: "Initiative section", page: "Page",
  "stored-value": "Value held", owner: "Person", bundle: "Contracts", lights: "Lights", inside: "Inside this app" };
const CONTRACT = Object.fromEntries(D.map.contracts.map((c) => [c.id, c]));
const UNKNOWN = Object.fromEntries(D.unknowns.map((u) => [u.id, u]));
const APPS = Object.fromEntries(D.map.apps.map((a) => [a.key, a]));
const APP_BY_ID = Object.fromEntries(D.map.apps.map((a) => [a.id, a]));
const EXTERNAL = Object.fromEntries(D.map.externals.map((x) => [x.key, x]));
const NODE = Object.fromEntries(D.nodes.map((n) => [n.key, n]));
const FLOW = Object.fromEntries(D.flows.map((f) => [f.key, f]));
const EPIC = Object.fromEntries(D.trace.epics.map((e) => [e.key, e]));
const LANE_INDEX = Object.fromEntries(D.lanes.map((l, i) => [l.id, i]));
const RUNTIME_TO_APP = {};
for (const [k, a] of Object.entries(D.apps)) if (a.runtime) RUNTIME_TO_APP[a.runtime] = k;
const isOpen = (u) => u && u.state === "open";

function ent(key) {
  if (E[key]) return E[key];
  if (key && key.startsWith("owner:")) { const o = D.owners[key.slice(6)]; return o ? { key, kind: "owner", title: o.handle, id: "" } : null; }
  if (EXTERNAL[key]) return { key, kind: "external", title: EXTERNAL[key].title, id: "" };
  if (key === "lights") return { key, kind: "lights", title: "What needs you", id: "" };
  if (key && key.startsWith("inside:")) return typeof Inside !== "undefined" ? Inside.ent(key) : null;
  if (key && key.startsWith("read:")) { const [pk] = key.slice(5).split("#"); const p = E[pk]; return p ? { key, kind: "reader", title: p.title, id: "", page: pk } : null; }
  return null;
}
const titleOf = (key) => { const e = ent(key); return e ? e.title : key; };
// An ID worth showing beside a title: CON-004, UNK-069, FLO-002. An app page's "APP-coach" only repeats its name.
const idOf = (key) => { const e = ent(key); return e && e.id && e.id !== e.title && /-\d/.test(e.id) ? e.id : ""; };
function keyForId(id) {
  if (E[id]) return id;
  const page = Object.values(E).find((x) => x.id === id && x.path);
  return page ? page.key : id;
}
function levelForKey(key) {
  if (UNKNOWN[key]) return unknownLevel(key);
  return lightOf(key) ? lightOf(key).level : null;
}
function refChip(key, extra) {
  const e = ent(key);
  if (!e) return h("span", { class: "ref-chip ref-dead", title: "Not a page or item in this vault" }, key);
  // a team's design question that challenges the item lights it "needs you" (inside.js), where attention leaves it dark
  const id = idOf(key), own = levelForKey(key), challenged = typeof Inside !== "undefined" && Inside.challenge(key);
  const lvl = challenged && (!own || own === "dark") ? "caution" : own;
  return h("a", { class: "ref-chip", "data-ref": key, title: (KIND_WORD[e.kind] || "") + (challenged && lvl === "caution" && own !== "caution" ? ": challenged by a team's design" : "") },
    lvl && lvl !== "dark" ? lampEl(lvl, challenged && own !== "caution" ? "Needs you: challenged by a team's design, not by attention.lights" : null) : null,
    id ? h("span", { class: "rid" }, id) : null, e.title, extra || null);
}
/* Where a thing's work lives outside the vault (planner's links.py: a page's links:, an item's **Links:**). Each chip
   is a plain link that opens in a new tab; the page never fetches it. Only http(s) reaches an href: a file:// link is a
   local clone, read at build time for the team's design (design_find.py), and draws no chip. */
const linksOf = (key) => ((E[key] || {}).links || []).filter((l) => /^https?:\/\//i.test(l.url));
function linkChips(key, opts = {}) {
  const list = linksOf(key);
  if (!list.length) return null;
  return h("div", { class: "link-chips" + (opts.small ? " small" : "") }, list.map((l) => h("a", { class: "link-chip", href: l.url, target: "_blank", rel: "noopener noreferrer",
    title: `${l.label}: ${l.url}`, onmousedown: (ev) => ev.stopPropagation(), onclick: (ev) => ev.stopPropagation() }, Icons.el(l.kind || "link"), l.label)));
}
function statePill(state) { return state ? h("span", { class: "pill" }, state) : null; }
function levelPill(level, text) { return level === "pending" && !text ? pendingPill(null) : h("span", { class: "pill " + level }, text || LIGHT[level].word); }

/* ------------------------------------------------------------------ flows that cross each thing */
// A flow crosses a thing when the flow page links it, a step sends over a contract it provides or consumes, or a
// step names it. The panel says which of these it was.
const FLOW_TOUCH = {};
function touch(key, flow, why) {
  if (!key) return;
  const list = FLOW_TOUCH[key] || (FLOW_TOUCH[key] = []);
  let row = list.find((r) => r.flow === flow);
  if (!row) list.push(row = { flow, why: new Set() });
  row.why.add(why);
}
for (const f of D.flows) {
  for (const r of f.refs) { touch(r, f.key, "linked from the flow page"); if (RUNTIME_TO_APP[r]) touch(RUNTIME_TO_APP[r], f.key, "linked from the flow page"); }
  for (const st of f.steps) {
    for (const c of st.contracts) {
      touch(c, f.key, `step ${st.n} uses it`);
      const con = CONTRACT[c];
      if (con) { touch(con.provider, f.key, `step ${st.n} uses ${c}`); con.consumers.forEach((k) => touch(k, f.key, `step ${st.n} uses ${c}`)); }
    }
    for (const k of st.linked) touch(k, f.key, `step ${st.n} links it`);
    for (const k of st.named) touch(k, f.key, `step ${st.n} names it`);
    for (const p of st.unknowns) touch(p.id, f.key, `pinned at step ${st.n}`);
  }
  for (const u of f.unknowns) touch(u, f.key, "the flow page cites it");
}
const flowsFor = (key) => (FLOW_TOUCH[key] || []).slice().sort((a, b) => cmp(a.flow, b.flow));
function stepEnds(st) {
  const ends = new Set();
  for (const m of st.messages) { ends.add(m.from); ends.add(m.to); }
  if (st.self) ends.add(st.self);
  for (const c of st.contracts) { const con = CONTRACT[c]; if (con) { ends.add(con.provider); con.consumers.forEach((k) => ends.add(k)); } }
  st.linked.forEach((k) => ends.add(RUNTIME_TO_APP[k] || k));
  return ends;
}
function firstStepTouching(f, key) {
  const k = RUNTIME_TO_APP[key] || key;
  const i = f.steps.findIndex((st) => st.contracts.includes(k) || st.linked.includes(k) || st.named.includes(k) || stepEnds(st).has(k)
    || st.unknowns.some((p) => p.id === k));
  return Math.max(0, i);
}
function flowStations(f) {
  const out = [];
  for (const st of f.steps) for (const k of stepEnds(st)) if (NODE[k] && !out.includes(k)) out.push(k);
  return out;
}

/* Where a thing lives on the map: itself, or the apps and contracts it is about, all from typed fields. */
function onMap(key) { return !!(NODE[key] || CONTRACT[key]); }
function mapAnchors(key) {
  if (onMap(key)) return [key];
  const e = ent(key);
  if (!e) return [];
  const out = new Set();
  if (FLOW[key]) flowStations(FLOW[key]).forEach((k) => out.add(k));
  if (e.kind === "runtime" && RUNTIME_TO_APP[key]) out.add(RUNTIME_TO_APP[key]);
  if (e.kind === "unknown") {
    for (const [k, a] of Object.entries(D.apps)) if (a.questions.some((q) => q.id === key)) out.add(k);
    for (const t of (UNKNOWN[key] || { holds: [] }).holds) if (CONTRACT[t]) out.add(t);
  }
  const appOf = (id) => APP_BY_ID[id] ? APP_BY_ID[id].key : null;
  if (e.kind === "epic" && EPIC[key]) EPIC[key].apps.map(appOf).forEach((k) => k && out.add(k));
  if (e.kind === "capability") {
    D.trace.epics.filter((x) => x.delivers.includes(e.id)).forEach((x) => x.apps.map(appOf).forEach((k) => k && out.add(k)));
    D.trace.allocation.filter((r) => r.requirement.startsWith(e.id + ".")).forEach((r) => out.add(r.app));
  }
  if (e.kind === "requirement") D.trace.allocation.filter((r) => r.requirement === key).forEach((r) => out.add(r.app));
  return [...out];
}

/* ------------------------------------------------------------------ views, the trail, and the router */
const VIEWS = [];
function View(id, def) { VIEWS.push(Object.assign({ id }, def)); }
/* view: what fills the main area. section: the sidebar entry it belongs to ("home", "apps", "role:qa", ...).
   root: what the panel returns to: "lights", or "read:<page key>" when a section's page sits beside its visual. */
const App = { view: "map", trail: [], focus: null, section: "home", root: "lights" };
const viewDef = (id) => VIEWS.find((v) => v.id === id);

function showView(name, opts) {
  const prev = viewDef(App.view);
  if (prev && prev.leave && name !== App.view) prev.leave();
  App.view = viewDef(name) ? name : "map";
  if (typeof Nav !== "undefined") Nav.adopt(App.view, opts);  // the sidebar entry follows the view
  if (!(opts && opts.keepHash) && typeof Nav !== "undefined") Nav.syncHash();
  rerender();
}
function rerender() {
  renderTabs();
  const main = $("#main");
  main.innerHTML = "";
  main.dataset.view = App.view;
  viewDef(App.view).render(main);
  Minimap.refresh();
}
/* Open something: the panel shows it, the trail keeps the thread, and with reveal the right view comes forward. */
function go(key, opts = {}) {
  if (!key) return;
  PanelSize.reveal();  // whatever is picked shows in the panel, so a hidden panel opens for it
  if (key === "lights") App.root = "lights";
  if (opts.reset) App.trail = key === "lights" || key === App.root ? [] : [key];
  else {
    const at = App.trail.indexOf(key);
    if (at >= 0) App.trail = App.trail.slice(0, at + 1); else App.trail.push(key);
    if (App.trail.length > 8) App.trail = App.trail.slice(-8);
  }
  if (key.startsWith("read:")) { Panel.render(); return; }  // reading a page changes nothing on the map
  App.focus = key === "lights" ? null : key;
  Panel.render();
  const e = ent(key);
  if (opts.reveal && e) {
    const target = revealView(e);
    if (target && target !== App.view) { showView(target); afterReveal(key, e); Minimap.refresh(); return; }
    afterReveal(key, e);
  }
  const v = viewDef(App.view);
  if (v.highlight && !opts.quiet) v.highlight(key);
  Minimap.refresh();
}
function revealView(e) {
  if (e.kind === "flow") return "flows";
  if (e.kind === "unknown") return "asks";
  if (e.kind === "decision") return "decisions";
  if (mapAnchors(e.key).length) return "map";
  if (e.kind === "capability" || e.kind === "requirement" || e.kind === "epic") return "trace";
  return null;
}
function afterReveal(key, e) {
  if (e.kind === "flow" && typeof Flows !== "undefined") Flows.select(key, -1);
  const v = viewDef(App.view);
  if (v.highlight) v.highlight(key);
}
document.addEventListener("click", (ev) => {
  const a = ev.target.closest("[data-ref]");
  if (!a || a.closest("#overlay")) return;
  ev.preventDefault();
  go(a.getAttribute("data-ref"), { reveal: a.hasAttribute("data-reveal") });
});

function renderTabs() {
  if (typeof Nav !== "undefined") Nav.refresh();
  const nav = $("#tabs");
  if (!nav) return;
  nav.innerHTML = "";
  for (const v of VIEWS) {
    const lamp = v.lamp ? v.lamp() : null;
    nav.append(h("button", { class: "tab", "aria-current": v.id === App.view ? "page" : null, onclick: () => showView(v.id), title: v.title || "" },
      v.label, v.count ? h("span", { class: "tab-n" }, v.count()) : null,
      lamp ? h("span", { class: "tab-lamp", style: `background:${LIGHT[lamp].colour};box-shadow:0 0 6px ${LIGHT[lamp].colour}` }) : null));
  }
}

let toastTimer = 0;
function toast(text) { const t = $("#toast"); t.textContent = text; t.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2800); }
function showTip(ev, html) {
  const tip = $("#tip"); tip.innerHTML = html; tip.classList.add("on");
  const w = tip.offsetWidth, ht = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 16;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + ht > innerHeight - 8) y = ev.clientY - ht - 12;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function hideTip() { $("#tip").classList.remove("on"); }

/* Every lit subject, most urgent first, as attention.ranked orders them: the panel's home and the sidebar's count. */
function litSubjects() {
  return D.ranked.map((key) => ({ key, light: D.lights[key] })).filter((x) => x.light && ent(x.key));
}
function darkSubjects() {
  return Object.entries(D.lights).filter(([k, l]) => l.level === "dark" && ent(k)).map(([k]) => k).sort();
}
