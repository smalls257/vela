"use strict";
/* Vault explorer, shared core. Every fact on this page comes from the JSON build.py wrote from vela's own
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
/* The one empty state. A view with nothing to draw says what is missing, in plain words, and which planning session
   writes it, so a reader on a live call can tell "not recorded yet" from "broken". `writer` is a slash command, or a list
   of them; the reader sees the session's name ("the boundary session"), not the command (label sweep: names, not codes).
   Every view uses this; none writes its own "nothing here" block. */
const sessionName = (cmd) => `the ${String(cmd).replace(/^\/vela:/, "").replace(/-/g, " ")} session`;
function emptyState(missing, detail, writer, extraClass) {
  return h("div", { class: "empty-state" + (extraClass ? " " + extraClass : ""), "data-empty": missing },
    h("b", {}, missing), detail ? " " + detail : "",
    writer ? h("div", { class: "es-writer", title: [].concat(writer).join(", ") }, "The plan's lead adds this in ", [].concat(writer).map(sessionName).join(" and "), ".") : null);
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
  return h("span", { class: cls + " off", "aria-disabled": "true", title: "This page can only open files that are part of the plan, and this one isn't. Open it from your editor, or open the page as a file." }, ...kids, " (outside the plan)");
}
/* Slice, tracer and grill are the only working words the page keeps (the user's ruling); each carries its one-line
   definition as a tooltip wherever it shows. The text comes from vela/terms.py through the data, so the CLI, the
   generated pages and this page say the same thing. An unknown word throws rather than showing an undefined term. */
function termEl(word, shown) {
  const text = (D.terms || {})[word];
  if (!text) throw new Error(`termEl: no definition for "${word}" in vela/terms.py`);
  return h("span", { class: "term", title: text, tabindex: "0", "aria-label": `${shown || word}: ${text}` }, shown || word);
}
const termTip = (word) => { const text = (D.terms || {})[word]; if (!text) throw new Error(`termTip: no definition for "${word}"`); return text; };
const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;
const shorten = (t, n) => { t = t || ""; return t.length > n ? t.slice(0, n - 1).trimEnd() + "…" : t; };
/* Words in a drawing are never cut. A label wraps to a second line, shrinks only down to FLOOR pixels, and past that wraps to as
   many lines as it needs; the caller sizes the box to `lines.length`. Cutting a name to "Consent and identit…" hides that it was
   cut (a Silent Fallback), and the reader cannot tell one name from another that starts the same. */
const LabelFit = (() => {
  const ctx = document.createElement("canvas").getContext("2d"), FLOOR = 11, LEAD = 1.2;
  let faces = null, themeOf = null;
  const family = (mono) => {  // a theme can change the faces, so they are read again when the theme does
    const now = document.documentElement.dataset.theme;
    if (!faces || themeOf !== now) { themeOf = now; faces = { ui: getComputedStyle(document.body).fontFamily, mono: getComputedStyle(document.documentElement).getPropertyValue("--mono") }; }
    return mono ? faces.mono : faces.ui;
  };
  const width = (text, size, weight, mono) => { ctx.font = `${weight || 400} ${size}px ${family(mono)}`; return ctx.measureText(text).width; };
  /* Greedy wrap; a word wider than the line is broken by letters, so no text is ever left out. */
  function wrap(text, room, size, weight, mono) {
    const out = [], w = (x) => width(x, size, weight, mono);
    let line = "";
    for (const word of String(text == null ? "" : text).split(/\s+/).filter(Boolean)) {
      let rest = word;
      if (w(line ? line + " " + rest : rest) <= room) { line = line ? line + " " + rest : rest; continue; }
      if (line) { out.push(line); line = ""; }
      while (rest.length > 1 && w(rest) > room) {
        let n = rest.length - 1;
        while (n > 1 && w(rest.slice(0, n)) > room) n--;
        out.push(rest.slice(0, n)); rest = rest.slice(n);
      }
      line = rest;
    }
    if (line) out.push(line);
    return out.length ? out : [""];
  }
  /* The largest size from o.size down to the floor at which the text fits o.max lines (default two); at the floor, every line it needs. */
  function fit(text, room, o) {
    const floor = Math.min(o.size, o.floor || FLOOR), max = o.max || 2;
    for (let z = o.size; ; z -= 0.5) {
      const size = Math.max(z, floor), lines = wrap(text, room, size, o.weight, o.mono);
      if (lines.length <= max || size <= floor) return { lines, size, lh: Math.round(size * LEAD * 10) / 10 };
    }
  }
  /* A <text> whose lines are tspans; attrs.y is the first line's baseline. Whole words only, so the text reads the same joined. */
  function put(parent, attrs, text, room, o) {
    const f = fit(text, room, o), t = s("text", attrs, parent);
    t.style.fontSize = f.size + "px";  // the size it was fitted at, whatever the stylesheet says
    f.lines.forEach((line, i) => { const sp = s("tspan", { x: attrs.x, dy: i ? f.lh : null }, t); sp.textContent = i < f.lines.length - 1 ? line + " " : line; });
    t.__lines = f;
    return t;
  }
  /* Move a text made by put (x, y of its first line, anchor): every line follows. */
  function place(t, x, y, anchor) {
    t.setAttribute("x", x); t.setAttribute("y", y); if (anchor) t.setAttribute("text-anchor", anchor);
    for (const sp of t.children) sp.setAttribute("x", x);
  }
  return { fit, put, place, wrap, width, FLOOR };
})();
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hash = (t) => { let x = 7; for (const ch of t) x = (x * 31 + ch.charCodeAt(0)) >>> 0; return x; };
const DAY = 86400000;
const dayNum = (iso) => Math.round(Date.parse(iso + "T00:00:00Z") / DAY);
const TODAY = dayNum(D.today);
const isDate = (t) => /^\d{4}-\d{2}-\d{2}$/.test(t || "");
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// American order, as everywhere vela writes a date: "Oct 12", and "Oct 12, 2026" when the year is wanted.
const day = (iso) => isDate(iso) ? `${MONTHS[+iso.slice(5, 7) - 1]} ${+iso.slice(8, 10)}` : (iso || "no date");
const dayYear = (iso) => isDate(iso) ? `${day(iso)}, ${iso.slice(0, 4)}` : (iso || "no date");
/* Motion is off for screenshots and checks (STILL), in the Plain view (FX, fx.js), and when the system asks for less. */
const reducedMotion = () => STILL || (typeof FX !== "undefined" && !FX.on) || matchMedia("(prefers-reduced-motion: reduce)").matches;
/* Glow (halos, lit shadows) is part of the effects; Plain keeps every color and drops the glow. */
const glowOn = () => typeof FX === "undefined" || FX.on;
function dueText(iso) {
  if (!isDate(iso)) return iso ? `answer wanted by "${iso}"` : "no answer date yet";
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
/* A vault that gains a vault_id in .vela.yaml (E18) keeps what this browser saved under the id it had before: the
   asks board, the layout, the Ask conversations and the rehearsals are copied to the new id once, never moved or
   overwritten, so going back to an older page still finds them. Returns the keys it copied. */
function migrateSaved(legacy, current, store = localStorage) {
  if (!legacy || legacy === current) return [];
  const moves = [];
  try {
    for (let i = 0; i < store.length; i++) {
      const key = store.key(i);
      const to = [["asks:", ""], ["explorer.layout.", ""], ["explorer.ask.", ""], ["rehearse:", ":"], ["onboard:", ":"]].map(([p, tail]) => (key === p + legacy || (tail && key.startsWith(p + legacy + tail))) ? p + current + key.slice((p + legacy).length) : null).find(Boolean);
      if (to && store.getItem(to) === null) moves.push([key, to]);
    }
    for (const [from, to] of moves) store.setItem(to, store.getItem(from));
  } catch (e) { console.warn("[settings] could not move what this browser saved under the vault's old id:", e.message); }
  return moves.map(([, to]) => to);
}
migrateSaved(D.legacyVaultId, D.vaultId);
/* How far off a date is: "in 17 d" where a cell is narrow (the asks strip), "in 17 days" where there is room to say it. */
const relDue = (iso) => { if (!isDate(iso)) return "no date"; const d = dayNum(iso) - TODAY; return d < 0 ? `${-d} d late` : d === 0 ? "today" : `in ${d} d`; };
const relDueWords = (iso) => { if (!isDate(iso)) return "no date"; const d = dayNum(iso) - TODAY; return d < 0 ? `${plural(-d, "day")} late` : d === 0 ? "today" : `in ${plural(d, "day")}`; };

/* ------------------------------------------------------------------ the status vocabulary: attention.py's levels */
// Color is never the only signal: each level has a word, and the maps add shape and motion. The colors here are
// Console's; theme.js re-reads them from the theme's --warning, --caution, ... so a lamp means the same in every room.
const LIGHT = {
  warning: { color: "#ff5a48", ink: "#2a0703", word: "Overdue", say: "a question blocking it missed its answer date" },
  caution: { color: "#ffb21e", ink: "#2b1a00", word: "Waiting", say: "not decided yet, or blocked by an open question" },
  pending: { color: "#b79cff", ink: "#150c33", word: "Pending approval", say: "someone decided this for the owner, and the owner hasn't confirmed it yet, so it isn't settled" },
  unexamined: { color: "#52c8ff", ink: "#04202e", word: "Not reviewed yet", say: "nobody has reviewed this yet; it only turns gray once someone has" },
  override: { color: "#f2f1e8", ink: "#1d1d18", word: "Overridden", say: "the plan's lead chose to skip a rule here; shown for the record, not a problem" },
  dark: { color: "#2a3236", ink: "#9aa7ad", word: "Decided", say: "decided, and nothing is blocking it" },
};
const LEVELS = D.levels;  // most urgent first, from attention.LEVELS
const rank = (level) => LEVELS.length - LEVELS.indexOf(level);
const lightOf = (key) => D.lights[key] || null;
const levelOf = (key) => (lightOf(key) || { level: "dark" }).level;
/* Breathing: slow and soft when an answer is weeks away, quicker and brighter as it falls due. */
const pulsePeriod = (urgency) => Math.round(5200 - 3400 * clamp(urgency || 0, 0, 1));
const ASK = Object.fromEntries(D.asks.map((u) => [u.id, u]));
const unknownLevel = (id) => { const u = ASK[id]; if (!u) return "dark"; return u.state === "open" ? u.light.level : "resolved"; };
/* The pending-approval mark in words: a clock glyph and the text, with who and when on hover, so color is never alone. */
const pendingPill = (p) => h("span", { class: "pill pending", title: p ? `Decided by ${p.by} on ${day(p.date)}; the owner hasn't confirmed it yet` : LIGHT.pending.say }, "◷ Pending approval");
function lampEl(level, title) { return h("span", { class: "lamp " + level, title: title || (LIGHT[level] ? LIGHT[level].word : level) }); }
function reasonText(r) {
  if (r.kind === "held" && r.unknown && ASK[r.unknown]) {
    const u = ASK[r.unknown], e = E[r.unknown];
    const who = u.ask.name || (String(r.ask || "").startsWith("@") ? personName(r.ask) : r.ask);  // a name, never a handle
    const via = (r.via || []).map((k) => titleOf(keyForId(k) || k));  // the things it reaches by name, never by code
    return `${e ? e.title : r.unknown}: ask ${who} by ${day(u.askBy)}${via.length ? ", through " + (via.length > 1 ? via.slice(0, -1).join(", ") + " and " + via[via.length - 1] : via[0]) : ""}`;
  }
  return r.text;
}

/* ------------------------------------------------------------------ the record, indexed */
const KIND_WORD = { app: "App", runtime: "How it runs", contract: "Contract", party: "Outside service", external: "Outside service",
  unknown: "Open question", risk: "Risk", epic: "Epic", capability: "Capability", flow: "Flow", requirement: "Requirement",
  decision: "Decision", concern: "Concern", section: "Plan section", page: "Page", slice: "Slice",
  "stored-value": "Stored data", owner: "Person", bundle: "Contracts", lights: "Waiting", inside: "Inside this app", library: "Library item", grill: "Grill" };
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

/* ------------------------------------------------------------------ every diagram node opens the panel (E44)
   The Sensor rule, as a helper: a node that does nothing when clicked is a Black Box, and so is one a keyboard or a
   screen reader cannot reach. Every node of every diagram is drawn through Nodes.wire(el, spec), which refuses a node
   without a name and without somewhere to go. Where it goes is exactly one of
     key:  a vault page, or an Inside key (inside:...): go(key) opens it as a click on a chip would;
     note: a node with no page of its own (free text, a group, an outside party the vault has no page for, an entity
           of a data model): the panel gets a small entry with its text and what it relates to, never an empty one;
     open: a function, for a node whose click does more than open the panel; it must itself reach go().
   The selftest clicks and presses Enter on every [data-node] on every diagram and fails on an empty panel. */
const Nodes = (() => {
  const notes = {};
  const noteKey = (diagram, name) => "node:" + encodeURIComponent(diagram) + "|" + encodeURIComponent(name);
  /* spec: diagram (which drawing), name, kind (a short word for the panel's heading), text (what it says),
     facts [[label, value]], stands [keys of what a group stands for], relates [keys, or plain words]. Returns the key. */
  function note(spec) {
    if (!spec || !spec.name || !spec.diagram) throw new Error(`[nodes] a note needs a diagram and a name, got ${JSON.stringify(spec && [spec.diagram, spec.name])}`);
    const k = noteKey(spec.diagram, spec.name);
    notes[k] = Object.assign({ kind: "In a diagram", text: "", facts: [], stands: [], relates: [] }, spec, { key: k });
    return k;
  }
  const entOf = (k) => (notes[k] ? { key: k, kind: "note", title: notes[k].name, id: "" } : null);
  const isKey = (x) => !!ent(x);
  const line = (r) => h("li", {}, isKey(r) ? refChip(r) : r);
  function panel(k) {
    const n = notes[k];
    if (!n) return [h("div", { class: "p-empty" }, "That part of the drawing isn't there any more. Pick it again.")];
    const stands = n.stands.filter(isKey), relates = n.relates.filter(Boolean);
    const bare = !n.text && !n.facts.length && !stands.length && !relates.length;
    return [h("div", { class: "p-head" }, h("div", { class: "kind" }, n.kind, h("span", { class: "p-id" }, n.diagram)), h("h2", {}, n.name)),
      h("div", { class: "p-body" },
        n.text ? h("div", { class: "prose-text" }, n.text) : null,
        n.facts.length ? h("div", { class: "facts" }, n.facts.flatMap(([label, v]) => [h("div", { class: "fl" }, label), h("div", {}, v)])) : null,
        stands.length ? Panel.section("Stands for", stands.length, h("ul", { class: "mini-list" }, stands.map(line))) : null,
        relates.length ? Panel.section("Relates to", relates.length, h("ul", { class: "mini-list" }, relates.map(line))) : null,
        bare ? h("div", { class: "p-note" }, `Part of the ${n.diagram} drawing. The plan says nothing more about it.`) : null)];
  }
  /* Makes `el` a node: focusable, named, opened by click, Enter and Space. `guard` returns false to swallow a click (a
     box just dropped after a drag). `nested` leaves a small part inside a focusable parent out of the tab order (a
     mini-lamp in a cluster): the parent is the keyboard's way in, and its panel lists what it holds. */
  function wire(el, spec) {
    const name = spec && spec.label;
    const where = spec ? [spec.key, spec.note, spec.open].filter(Boolean).length : 0;
    if (!name || !String(name).trim() || where !== 1) throw new Error(`[nodes] a diagram node needs a name and exactly one of key, note or open, got ${JSON.stringify(name)} with ${where}`);
    const target = spec.key || spec.note || "";
    // a second click on the node already picked puts it down (DetailsPanel.toggle), on every diagram alike
    const open = spec.open || (() => DetailsPanel.toggle(target, spec.opts || { reset: true }));
    const fire = (ev) => { if (spec.guard && !spec.guard()) return; if (spec.stop && ev) ev.stopPropagation(); open(ev); };
    el.setAttribute("tabindex", spec.nested ? "-1" : "0");
    el.setAttribute("role", spec.role || "button");
    el.setAttribute("aria-label", spec.aria || name);
    el.setAttribute("data-node", name);
    if (target) el.setAttribute("data-opens", target);
    el.addEventListener("click", fire);
    el.addEventListener("keydown", (ev) => { if (ev.target !== el) return; if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); fire(ev); } });
    return el;
  }
  return { note, ent: entOf, panel, wire, noteKey };
})();

function ent(key) {
  if (E[key]) return E[key];
  if (key && key.startsWith("node:")) return Nodes.ent(key);
  if (key && key.startsWith("owner:")) {
    const o = D.owners[key.slice(6)], asked = D.asks.find((u) => u.ask.key === key.slice(6));  // a person who owns nothing but is asked is still a person
    return o ? { key, kind: "owner", title: o.handle, id: "" } : asked ? { key, kind: "owner", title: asked.ask.name, id: "" } : null;
  }
  if (key && key.startsWith("decision:")) {  // a decision as the decision log records it, whatever page carries it
    const t = [...D.garden.trees, ...D.garden.bare].find((x) => (x.adr ? x.adr.id : x.id) === key.slice(9));
    return t ? { key, kind: "decision-record", title: t.picked.label, id: "" } : null;
  }
  if (key && key.startsWith("release:")) {
    const at = +key.slice(8), s = D.releases.count && at > 0 ? D.releases.states[at] : null;  // 0 is Today, not a release
    return s ? { key, kind: "release", title: s.heading || s.name, id: "" } : null;
  }
  if (key && key.startsWith("grill:")) return typeof Grills !== "undefined" ? Grills.entry(key) : null;  // a grill waiting, as the Grills waiting view lists it
  if (key && key.startsWith("lib:")) return typeof Library !== "undefined" ? Library.entry(key) : null;  // a Library row, whatever page cites it
  if (key && key.startsWith("grp:")) return typeof FlowView !== "undefined" ? FlowView.groupEnt(key) : null;  // lanes a reader drew as one on the Flows view
  if (key && key.startsWith("gap:")) { const l = D.lanes[LANE_INDEX[key]]; return l ? { key, kind: "gap", title: l.name, id: "" } : null; }  // an end a flow step names that the plan doesn't know
  if (EXTERNAL[key]) return { key, kind: "external", title: EXTERNAL[key].title, id: "" };
  if (key === "lights") return { key, kind: "lights", title: "Needs you", id: "" };
  if (key && key.startsWith("inside:")) return typeof Inside !== "undefined" ? Inside.ent(key) : null;
  if (key && key.startsWith("read:")) { const [pk] = key.slice(5).split("#"); const p = E[pk]; return p ? { key, kind: "reader", title: p.title, id: "", page: pk } : null; }
  return null;
}
const titleOf = (key) => { const e = ent(key); return e ? e.title : key; };
// An ID worth showing beside a title: CON-004, UNK-069, FLO-002. An app page's "APP-coach" only repeats its name.
const idOf = (key) => { const e = ent(key); return e && e.id && e.id !== e.title && /-\d/.test(e.id) ? e.id : ""; };
/* A name first, its code after it in small type: what a person reads is the name, and the code is there to quote or search. */
const idTag = (id) => (id ? h("span", { class: "id-tag" }, id) : null);
/* A prose block that may be taller than its room: the cut line fades, and "Show more" opens it in place (a button, so the
   keyboard reaches it). Nothing is cut without a way to the rest. The button goes away again if the text turns out to fit. */
function foldProse(box, text) {
  const more = h("button", { class: "linkish show-more", "data-more": "", "aria-expanded": "false", onclick: () => {
    const open = box.classList.toggle("open");
    more.textContent = open ? "Show less" : "Show more"; more.setAttribute("aria-expanded", String(open));
  } }, "Show more");
  box.append(more);
  const fit = () => {
    if (box.classList.contains("open")) return;
    const cut = text.scrollHeight > text.clientHeight + 4;
    text.classList.toggle("is-cut", cut); more.hidden = !cut;
  };
  requestAnimationFrame(fit);
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(fit).observe(text);
  return box;
}
function keyForId(id) {
  if (E[id]) return id;
  const page = Object.values(E).find((x) => x.id === id && x.path);
  return page ? page.key : id;
}
function levelForKey(key) {
  if (UNKNOWN[key]) return unknownLevel(key);
  return lightOf(key) ? lightOf(key).level : null;
}
/* A person as a reader names them: the plan's own short name for the handle, else the handle said as words
   ("@booking-senior" -> "Booking senior"), never the handle itself (say.LEAD_PATTERNS' "handle"). */
function personName(handle) {
  const o = D.owners[handle], said = o && o.names && o.names[0];
  if (said && said.split(/\s+/).length <= 3 && !/^asking\b/i.test(said)) return said;
  const w = String(handle || "").replace(/^@/, "").replace(/^[^/]*\//, "").replace(/[-_]/g, " ");
  return w.charAt(0).toUpperCase() + w.slice(1);
}
/* Free text a page wrote with handles and ISO dates in it ("@agent-lead, 2026-10-12, PR pending"), said as a reader
   says it ("Agent lead, Oct 12, PR pending"). The one rewrite: the decision log, Progress and the doors all call it. */
const peopleWords = (text) => String(text || "").replace(/@[\w/-]+/g, personName).replace(/\b\d{4}-\d{2}-\d{2}\b/g, (d) => (isDate(d) ? day(d) : d));
function refChip(key, extra) {
  const e = ent(key);
  if (!e) return h("span", { class: "ref-chip ref-dead", title: "Not a page or item in this plan" }, key);
  // a team's design question that challenges the item lights it "waiting" (inside.js), where attention leaves it dark
  const id = idOf(key), own = levelForKey(key), challenged = typeof Inside !== "undefined" && Inside.challenge(key);
  const lvl = challenged && (!own || own === "dark") ? "caution" : own;
  return h("a", { class: "ref-chip", "data-ref": key, title: (KIND_WORD[e.kind] || "") + (challenged && lvl === "caution" && own !== "caution" ? ": the app team's design questions it" : "") },
    lvl && lvl !== "dark" ? lampEl(lvl, challenged && own !== "caution" ? "Waiting: the app team's design questions it" : null) : null,
    e.kind === "owner" ? personName(e.title) : e.title, id ? h("span", { class: "rid id-tag" }, id) : null, extra || null);
}
/* Where a thing's work lives outside the vault (vela's links.py: a page's links:, an item's **Links:**). Each chip
   is a plain link that opens in a new tab; the page never fetches it. Only http(s) reaches an href: a file:// link is a
   local clone, read at build time for the team's design (design_find.py), and draws no chip. */
const linksOf = (key) => ((E[key] || {}).links || []).filter((l) => /^https?:\/\//i.test(l.url));
function linkChips(key, opts = {}) {
  const list = linksOf(key);
  if (!list.length) return null;
  return h("div", { class: "link-chips" + (opts.small ? " small" : "") }, list.map((l) => h("a", { class: "link-chip", href: l.url, target: "_blank", rel: "noopener noreferrer",
    title: `${l.label}: ${l.url}`, onmousedown: (ev) => ev.stopPropagation(), onclick: (ev) => ev.stopPropagation() }, Icons.el(l.kind || "link"), l.label)));
}
/* A status pill's gap IDs: up to three are shown, each kept whole on one line; more than that become a count, with
   every ID in the pill's title, so a long list never runs out of the pill or breaks an ID across two lines. */
function gapsTag(gaps) {
  if (!gaps.length) return null;
  if (gaps.length > 3) return h("b", {}, ` · ${gaps.length} gaps`);
  return h("b", {}, gaps.map((g) => h("span", { class: "nowrap" }, " " + g)));
}
/* A recorded state in plain words: the vault's values (inkling, assumption, fact, ...) are field values, not reader words.
   The words are plainwords.py's, carried in the data, so a pill, a light's reason, a door and a generated page all
   name a state the same way; there is no second list here. An unknown value shows as written, so a new state is never hidden. */
const STATE_WORD = D.words.state, CELL_WORD = D.words.cell, STAGE_WORD = D.words.stage;
const upFirst = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const stateWord = (state) => { const w = STATE_WORD[String(state || "").toLowerCase()]; return w ? upFirst(w) : state; };
const cellWord = (cell) => CELL_WORD[String(cell || "").toLowerCase()] || cell;
const stageWord = (stage) => STAGE_WORD[String(stage || "").toLowerCase()] || stage;
function statePill(state) { return state ? h("span", { class: "pill" }, stateWord(state)) : null; }
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
    for (const m of st.messages) if (!m.contract) { touch(m.from, f.key, `step ${st.n} sends it`); touch(m.to, f.key, `step ${st.n} sends it`); }  // a recorded pair that names no contract
    for (const c of st.contracts) {
      touch(c, f.key, `step ${st.n} sends over it`);
      const con = CONTRACT[c];
      if (con) { touch(con.provider, f.key, `step ${st.n} sends over ${con.title}`); con.consumers.forEach((k) => touch(k, f.key, `step ${st.n} sends over ${con.title}`)); }
    }
    for (const k of st.linked) touch(k, f.key, `step ${st.n} mentions it`);
    for (const k of st.named) touch(k, f.key, `step ${st.n} mentions it`);
    for (const p of st.unknowns) touch(p.id, f.key, `step ${st.n} raises this question`);
  }
  for (const u of f.unknowns) touch(u, f.key, "the flow page cites it");
}
const flowsFor = (key) => (FLOW_TOUCH[key] || []).slice().sort((a, b) => cmp(a.flow, b.flow));
function stepEnds(st) {
  const ends = new Set();
  for (const m of st.messages) { ends.add(m.from); ends.add(m.to); }
  for (const x of st.run || []) for (const m of x.messages) { ends.add(m.from); ends.add(m.to); }  // a folded step: the lanes folded into its host
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
/* The lanes a step draws: its senders and receivers, or the app it happens in. The minimap and the lanes follow this one set. */
function laneEnds(st) {
  const ends = new Set();
  for (const m of st.messages) { ends.add(m.from); ends.add(m.to); }
  for (const x of st.run || []) for (const m of x.messages) { ends.add(m.from); ends.add(m.to); }
  if (st.self) ends.add(st.self);
  return ends;
}
function flowStations(f) {
  const out = [];
  for (const st of f.steps) for (const k of laneEnds(st)) if (NODE[k] && !out.includes(k)) out.push(k);
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
/* view: what fills the main area. section: the sidebar entry it belongs to ("apps", "role:qa", ...).
   root: what the panel returns to: "lights", or "read:<page key>" when a section's page sits beside its visual. */
const App = { view: "map", trail: [], focus: null, section: "apps", root: "lights" };
const viewDef = (id) => VIEWS.find((v) => v.id === id);

function showView(name, opts) {
  const prev = viewDef(App.view);
  if (prev && prev.leave && name !== App.view) prev.leave();
  App.view = viewDef(name) ? name : "map";
  if (typeof Nav !== "undefined") Nav.adopt(App.view, opts);  // the sidebar entry follows the view
  if (!(opts && opts.keepHash) && typeof Nav !== "undefined") Nav.syncHash();
  rerender();
  Panel.render();  // a page with its own Details (detailspanel.js) draws the panel for itself, not for the page that went
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
  // a capability picked on the map, or revealed from a chip, narrows the map and the sidebar to what it touches
  if (e && e.kind === "capability" && !opts.quiet && (["map", "capmap", "capmatrix"].includes(App.view) || opts.reveal) && !CapFocus.isIt(key)) { Nav.open("capabilities", key, { stay: App.view === "capmatrix" }); return; }
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
  if (e.kind === "capability") return "capmap";
  if (e.kind === "unknown") return "asks";
  if (e.kind === "decision") return "decisions";
  if (e.kind === "slice") return "slices";
  if (e.kind === "library") return "library";
  if (mapAnchors(e.key).length) return "map";
  if (e.kind === "capability" || e.kind === "requirement" || e.kind === "epic") return "trace";
  return null;
}
function afterReveal(key, e) {
  if (e.kind === "flow" && typeof Flows !== "undefined") Flows.select(key, -1);
  const v = viewDef(App.view);
  if (v.highlight) v.highlight(key);
  Panel.render();  // the page that came forward has its own Details, and the panel was drawn for the one that went
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
      lamp ? h("span", { class: "tab-lamp", style: `background:${LIGHT[lamp].color};box-shadow:0 0 6px ${LIGHT[lamp].color}` }) : null));
  }
}

let toastTimer = 0;
function toast(text) { const t = $("#toast"); t.textContent = text; t.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2800); }
/* The tip belongs to the element that showed it. A click that swaps the page removes that element under the pointer,
   so its mouseleave never fires and the tip would stay; the tip hides on any click, page change, scroll, Escape or
   blur, and whenever the pointer is no longer over the element that showed it or that element has gone. */
let tipSource = null;
function showTip(ev, html) {
  tipSource = ev.currentTarget instanceof Element ? ev.currentTarget : ev.target instanceof Element ? ev.target : null;
  const tip = $("#tip"); tip.innerHTML = html; tip.classList.add("on");
  const w = tip.offsetWidth, ht = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 16;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + ht > innerHeight - 8) y = ev.clientY - ht - 12;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function hideTip() { const tip = $("#tip"); if (tip) tip.classList.remove("on"); tipSource = null; }
const tipShown = () => { const tip = $("#tip"); return !!tip && tip.classList.contains("on"); };
document.addEventListener("pointerdown", hideTip, true);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideTip(); }, true);
document.addEventListener("scroll", hideTip, true);
addEventListener("hashchange", hideTip);
addEventListener("blur", hideTip);
document.addEventListener("mousemove", (e) => {
  if (tipShown() && (!tipSource || !tipSource.isConnected || !(e.target instanceof Node) || !tipSource.contains(e.target))) hideTip();
}, { capture: true, passive: true });

/* Every lit subject, most urgent first, as attention.ranked orders them: the panel's home and the sidebar's count. */
function litSubjects() {
  return D.ranked.map((key) => ({ key, light: D.lights[key] })).filter((x) => x.light && ent(x.key));
}
function darkSubjects() {
  return Object.entries(D.lights).filter(([k, l]) => l.level === "dark" && ent(k)).map(([k]) => k).sort();
}

/* ------------------------------------------------------------------ the key under every diagram
   A drawing that uses a look (a dashed line, a lit box, a ringed one) must say what the look means, or a reader on a
   call has to ask. Without this, each view kept its own fixed list of looks, and a list written once drifts from the
   drawing: it names a look that is not on screen, or leaves out one that is.

   So the key is made from the drawing. A diagram opens a key (Legend.open) with the looks it can draw and, for each,
   a probe that finds it in the drawing; while it draws, every look it really uses calls saw(); the key then lists
   exactly those, in the order the probes were written. One look is described once (Legend.define), in plain words
   and a small picture, so a dashed line means the same thing in the same words wherever it appears.

   The probes are also the self-test's way to look at the page from outside: Legend.audit() finds each drawn look by
   its probe and compares it to what the key shows. A diagram that draws a look and forgets saw() fails there by name.
   The key sits under the drawing, never inside what scrolls, and folds away; the choice is kept per diagram. */
const Legend = (() => {
  const CATALOG = new Map(), live = new Map();
  let active = null;
  const token = (c) => `var(--${c})`;
  const LAMPS = ["warning", "caution", "pending", "unexamined", "override", "dark"];
  /* One part of a picture: a line, a box, a clipped box, a dot or a few letters, on a 34 x 16 canvas. */
  function part(k, o) {
    const paint = (el) => {
      el.style.fill = o.fill ? token(o.fill) : "none";
      if (o.stroke) { el.style.stroke = token(o.stroke); el.style.strokeWidth = o.w || 1.6; }
      if (o.dash) el.style.strokeDasharray = o.dash;
      if (o.opacity) el.style.opacity = o.opacity;
      return el;
    };
    if (k === "line") {
      const g = s("g", {}), y = o.y ?? 8;
      paint(s("path", { d: `M3 ${y}H${o.head ? 26 : 31}`, "stroke-linecap": "round" }, g)).style.fill = "none";
      if (o.head === "fill") { const t = s("path", { d: `M24 ${y - 4}L31 ${y}L24 ${y + 4}Z` }, g); t.style.fill = token(o.stroke); }
      if (o.head === "open") { const t = s("path", { d: `M24 ${y - 4}L30 ${y}L24 ${y + 4}`, "stroke-linecap": "round", "stroke-linejoin": "round" }, g); t.style.fill = "none"; t.style.stroke = token(o.stroke); t.style.strokeWidth = o.w || 1.6; }
      return g;
    }
    if (k === "box") return paint(s("rect", { x: o.x ?? 3, y: o.y ?? 2.5, width: o.width ?? 28, height: o.height ?? 11, rx: o.rx ?? 3 }));
    if (k === "clip") return paint(s("path", { d: "M7 2.5H27L31 6.5V9.5L27 13.5H7L3 9.5V6.5Z" }));
    if (k === "dot") return paint(s("circle", { cx: o.x ?? 17, cy: o.y ?? 8, r: o.r ?? 4.5 }));
    const t = s("text", { x: o.x ?? 17, y: o.y ?? 12, "text-anchor": "middle" });
    t.textContent = o.t; t.style.fill = token(o.fill || "ink-2"); t.style.fontSize = (o.size || 11) + "px"; t.style.fontWeight = 700;
    return t;
  }
  function picture(parts) {
    const svg = s("svg", { class: "lg-sw", viewBox: "0 0 34 16", width: 34, height: 16, "aria-hidden": "true" });
    for (const p of [].concat(parts)) svg.appendChild(part(p.k, p));
    return svg;
  }
  /* A look, once. `text` is "Lead words: what it means"; the lead is what to look for, the rest is the meaning. */
  function define(id, parts, text) { CATALOG.set(id, { parts, text }); }
  const ln = (o) => ({ k: "line", stroke: "ink-3", ...o }), bx = (o) => ({ k: "box", ...o });
  /* The lamp levels: the same words and meanings as LIGHT, drawn as the color they are drawn in. */
  const lampPicture = (lv) => lv === "dark" ? [bx({ fill: "unlit", stroke: "rule-3", w: 1 })]
    : lv === "pending" ? [bx({ stroke: "pending", w: 2.2 })] : lv === "override" ? [bx({ fill: "override", stroke: "override-edge", w: 1 })] : [bx({ fill: lv })];
  for (const lv of LAMPS) {
    define("lamp." + lv, lampPicture(lv), lv === "dark" ? "Gray: decided, and nothing is blocking it" : `${LIGHT[lv].word}: ${LIGHT[lv].say}`);
  }
  define("picked", [bx({ fill: "deck-2", stroke: "focus", w: 2.2 })], "White outline: what you picked, or what it touches");
  const lampProbes = (selector) => Object.fromEntries(LAMPS.map((lv) => ["lamp." + lv, selector(lv)]));

  /* Opens the key for one diagram.
       root    () => the element the drawing is in, for the probes
       probes  { look id: CSS selector, or (root) => boolean }, in the order the key lists them
       open    whether the key starts open (a reader's choice, once made, wins) */
  function open(name, def) {
    const lg = { name, def, seen: new Map(), host: null, last: "" };
    lg.saw = (id, text) => { if (id) lg.seen.set(id, text || null); };
    lg.unsaw = (id) => { lg.seen.delete(id); };
    lg.set = (id, on, text) => (on ? lg.saw(id, text) : lg.unsaw(id));
    lg.within = (fn) => { const was = active; active = lg; try { return fn(); } finally { active = was; } };
    lg.paint = () => paint(lg);
    lg.el = () => lg.host || (lg.host = build(lg));
    live.set(name + "#" + (def.instance || ""), lg);  // one key per drawing: a page can hold several of one kind (each sequence)
    return lg;
  }
  const saw = (id, text) => { if (active) active.saw(id, text); };
  const textOf = (lg, id) => lg.seen.get(id) || (CATALOG.get(id) || { text: id }).text;
  function build(lg) {
    const remembered = Settings.read("explorer.legend." + lg.name);
    const isOpen = remembered === null ? lg.def.open !== false && innerHeight >= 700 : remembered === "1";
    const host = h("details", { class: "legend", "data-legend": lg.name, hidden: true, open: isOpen ? "" : null });
    host.addEventListener("toggle", () => { Settings.write("explorer.legend." + lg.name, host.open ? "1" : "0"); dispatchEvent(new Event("resize")); });
    return host;
  }
  function paint(lg) {
    const host = lg.el(), ids = Object.keys(lg.def.probes).filter((id) => lg.seen.has(id));
    for (const id of lg.seen.keys()) if (!ids.includes(id)) { console.warn(`[legend] ${lg.name} drew "${id}", which it gave no probe; the self-test cannot check it`); ids.push(id); }
    const signature = ids.map((id) => id + "=" + textOf(lg, id)).join("|");
    if (signature === lg.last) return;
    lg.last = signature;
    host.replaceChildren();
    host.hidden = !ids.length;
    if (!ids.length) return;
    host.append(h("summary", {}, "Key"),
      h("ul", { class: "lg-items" }, ids.map((id) => {
        const text = textOf(lg, id), at = text.indexOf(": "), entry = CATALOG.get(id);
        return h("li", { "data-lg": id }, entry ? picture(entry.parts) : null, h("span", {}, at > 0 ? [h("b", {}, text.slice(0, at)), text.slice(at)] : text));
      })));
    if (host.isConnected && !lg.def.quiet) dispatchEvent(new Event("resize"));  // the key took or gave back room, so the drawing above refits
  }
  const present = (lg, root) => Object.entries(lg.def.probes).filter(([, p]) => (typeof p === "function" ? p(root) : !!root.querySelector(p))).map(([id]) => id);
  /* What the self-test asks: for every key in the page, each look its drawing really has is in the key, and each look
     the key lists is in the drawing. Each problem names the diagram and the meaning. */
  function audit() {
    const problems = [];
    for (const lg of live.values()) {
      if (!lg.host || !lg.host.isConnected) continue;
      const root = lg.def.root();
      if (!root) { problems.push(`${lg.name}: its key is on the page but its drawing is not`); continue; }
      const drawn = present(lg, root), shown = [...lg.host.querySelectorAll("[data-lg]")].map((li) => li.dataset.lg);
      for (const id of drawn) if (!shown.includes(id)) problems.push(`${lg.name}: the drawing has "${textOf(lg, id)}" but the key does not say so`);
      for (const id of shown) if (!drawn.includes(id)) problems.push(`${lg.name}: the key says "${textOf(lg, id)}" but the drawing does not have it`);
    }
    return problems;
  }
  const keyed = () => [...live.values()].filter((lg) => lg.host && lg.host.isConnected);
  const forget = (name) => live.delete(name + "#");
  return { define, open, saw, audit, keyed, forget, lampProbes, LAMPS, ln, bx, part, picture, CATALOG };
})();
