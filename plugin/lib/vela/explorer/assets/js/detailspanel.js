/* The Details panel: one scope at a time, with a trail back, for any page that has a diagram and a summary behind it.

   The Violation this exists to prevent is a Distributed Monolith of panel behavior: if each page grows its own copy of
   "pick a thing, show only that thing, keep a way back, clear on Escape", the copies drift and every page behaves a
   little differently. The panel owns the behavior; a page owns only what it says.

   What the panel owns
   - The two tabs, Details and What's waiting.
   - The trail. The page's summary is the root; every thing shown is a key in App.trail (the same trail go() keeps), so
     a link, a chip with data-ref, a node wired with Nodes.wire and the browser's own history all land in one place.
     The trail reads "Design › NoteClient › Note request", each earlier name returns there, and "← back" pops one.
   - Open. A thing with a view of its own (another app, a flow) shows an Open button in its Details header. The first
     click on the thing only shows its details; Open is the second click and is the one that jumps.
   - Escape, and the page calling clear() on empty space, return to the summary. Hovering never changes the panel.
   - Falling back: a key the page does not own (a vault page, a contract) is drawn by Panel.keyNodes, so the panel
     is never empty and a page need not know how every vault thing looks.

   What a page supplies (DetailsPanel.register(name, spec)); every function may be asked many times and must be cheap
     view      the App.view this page lives on                                    (required)
     live()    true while the page wants this panel (e.g. it has a design loaded) (required)
     root      the summary's key, which is App.root while live                    (the page sets App.root itself)
     rootLabel the summary's name in the trail, e.g. "Design"                     (required)
     summary() nodes for nothing picked: the page at a glance                     (required)
     owns(key) true for a key the page draws itself                               (required)
     detail(key)  nodes for an owned key; its first .p-head may take the Open button
     label(key)   the key's short name in the trail (owned keys; others use titleOf)
     open(key)    null, or {label, run} when the key has a view of its own
     waiting(key) nodes for the What's waiting tab, given what is picked (or null)  (required)
     waitingCount() the number on the tab                                        (required)
     focus(key)   paint the diagram for what is picked, or clear it when null     (required)
     rendered()   called after Details is drawn, for a drawing that must be placed once it is on the page
   and it calls DetailsPanel.show(key) to pick (reset: true starts a new trail), .clear() for empty space, and
   .link(key, text) for an inline link that pushes onto the trail.

   Used by: Inside this app (inside.js). Flows, the Apps map, What's waiting and Decisions can register the same way. */
const DetailsPanel = (() => {
  const pages = {};
  const st = { tab: "details", seen: "" };
  const current = () => Object.values(pages).find((p) => p.view === App.view && p.live()) || null;
  const active = () => !!current();
  const topKey = () => App.trail[App.trail.length - 1] || "";

  function register(name, spec) {
    for (const need of ["view", "live", "rootLabel", "summary", "owns", "waiting", "waitingCount", "focus"]) {
      if (spec[need] === undefined) throw new Error(`[details panel] ${name} must supply ${need}`);
    }
    pages[name] = spec;
  }

  const labelOf = (spec, key) => (spec.owns(key) && spec.label ? spec.label(key) : titleOf(key));
  const refresh = () => { Panel.render(); const p = current(); if (p) p.focus(topKey() || null); };

  /* Pick a thing: its details show, the trail keeps the thread, and the diagram lights what it touches. */
  function show(key, opts = {}) {
    st.tab = "details";
    go(key, opts);  // go() reveals a hidden panel, keeps the trail and renders; the page's highlight follows from it
    const p = current();
    if (p) p.focus(topKey() || null);
  }
  function back() {
    if (!App.trail.length) return;
    App.trail = App.trail.slice(0, -1);
    st.tab = "details"; refresh();
  }
  function trailTo(i) { App.trail = App.trail.slice(0, i + 1); st.tab = "details"; refresh(); }
  /* Back to the page's summary: empty space, Escape, the crumb that names the page. */
  function clear() {
    if (!App.trail.length && st.tab === "details") return false;
    App.trail = []; st.tab = "details"; refresh();
    return true;
  }
  /* A page was entered fresh: nothing is picked and Details shows. */
  function reset() { st.tab = "details"; st.seen = ""; }
  function setTab(tab) { st.tab = tab; Panel.render(); const p = current(); if (p) p.focus(topKey() || null); }
  /* An inline link inside Details that pushes the thing onto the trail. A button, so the keyboard has it. */
  function link(key, text, title) {
    return h("button", { class: "linkish dp-link", type: "button", "data-dp": key, title: title || null, onclick: (ev) => { ev.stopPropagation(); show(key); } }, text);
  }

  function tabs(spec) {
    const n = spec.waitingCount();
    const tab = (id, text) => h("button", { role: "tab", "aria-selected": String(st.tab === id), "aria-pressed": String(st.tab === id), "data-dp-tab": id, onclick: () => setTab(id) }, text);
    return h("div", { class: "p-homes dp-tabs", role: "tablist", "aria-label": "Details" }, tab("details", "Details"), tab("waiting", n ? `What's waiting ${n}` : "What's waiting"));
  }
  function trail(spec) {
    const keys = App.trail, last = keys.length - 1;
    const first = h("button", { class: "linkish", type: "button", onclick: () => clear() }, typeof spec.rootLabel === "function" ? spec.rootLabel() : spec.rootLabel);
    const crumbs = keys.map((k, i) => [h("span", { class: "sep" }, "›"),
      i === last ? h("span", { class: "cur" }, shorten(labelOf(spec, k), 28)) : h("button", { class: "linkish", type: "button", onclick: () => trailTo(i) }, shorten(labelOf(spec, k), 22))]);
    const prev = keys.length > 1 ? labelOf(spec, keys[last - 1]) : null;
    return [h("nav", { class: "crumbs dp-trail", "aria-label": "Trail" }, first, ...crumbs),
      h("button", { class: "btn dp-back", type: "button", onclick: () => back() }, prev ? `← back to ${shorten(prev, 26)}` : "← back to the summary")];
  }
  /* The Open button goes in the thing's header, as the page described it; without a header it leads the body. */
  function withOpen(spec, key, nodes) {
    const o = spec.open ? spec.open(key) : null;
    if (!o) return nodes;
    const btn = h("button", { class: "btn dp-open", type: "button", title: o.title || null, onclick: () => o.run() }, o.label || "Open");
    const header = nodes.find((n) => n && n.classList && n.classList.contains("p-head"));
    if (header) header.append(h("div", { class: "p-actions" }, btn)); else nodes.unshift(btn);
    return nodes;
  }

  function render(root) {
    const spec = current();
    const key = topKey();
    if (key !== st.seen) { st.seen = key; st.tab = "details"; }  // a new thing is picked: show it
    root.append(tabs(spec));
    if (st.tab === "waiting") { root.append(...[].concat(spec.waiting(key || null)).filter(Boolean)); return; }
    if (key) root.append(...trail(spec));
    const nodes = key ? (spec.owns(key) ? spec.detail(key) : Panel.keyNodes(key)) : spec.summary();
    root.append(...(key ? withOpen(spec, key, nodes.filter(Boolean)) : nodes.filter(Boolean)));
    if (spec.rendered) spec.rendered();
  }

  /* Escape goes back to the summary, unless something nearer wants it: a menu, a field, the full-screen view. */
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape" || ev.defaultPrevented || !active() || Menus.isOpen) return;
    if (ev.target.closest && ev.target.closest("input,textarea,select")) return;
    if (document.querySelector("#main.inside-full")) return;  // the page leaves full screen first
    if ($("#overlay") && !$("#overlay").hidden) return;
    if (clear()) { ev.preventDefault(); }
  });

  return { register, active, current, render, show, back, clear, trailTo, setTab, link, refresh, reset, get tab() { return st.tab; } };
})();
