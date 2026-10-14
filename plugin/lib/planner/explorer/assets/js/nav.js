/* Navigation: a collapsible sidebar in the vault's own section order, the front doors by audience at its top, and
   the router. Every section opens a section page: its visual in the main area, and its page, in the vault's own
   words, beside it in the panel. Constraints, Strategy and Glossary are mostly words, so their page fills the main
   area instead. The views the explorer already had are the visuals of their sections: the map is Apps (and
   Capabilities, grouped by capability), the played flows are Flows, Who to ask is Unknowns and risks, the decision log is
   Decisions, the stage ladder is Apps' second visual and the trace is Capabilities' and Epics'.

   Hash: #home, #role=qa, #s=apps&open=APP-booking, #s=strategy&read, plus the map's &lens= &group= &focus= and the
   releases' &state=. The old deep links (#map, #flows&open=FLO-002, #asks&open=UNK-065, #garden&open=ADR-0002, now the decision log)
   still land where they did. */
const Nav = (() => {
  const SIDE_KEY = "explorer.side", OPEN_KEY = "explorer.side.open";
  const SECTIONS = Object.fromEntries(D.sections.map((x) => [x.id, x]));
  // section -> its visuals, the first being the default; [] means its page is read full width
  const VISUALS = {
    goals: [["goals", "Goals"]], constraints: [], context: [["context", "Today and after"]], strategy: [],
    capabilities: [["map", "Capability map"], ["trace", "Trace"]], releases: [["releases", "Timeline"]],
    apps: [["map", "Map"], ["progress", "Progress"]], flows: [["flows", "Played"]], concerns: [["concerns", "Concern cells"]],
    decisions: [["decisions", "Log"]], unknowns: [["asks", "Who to ask"]], glossary: [], epics: [["epics", "Epics"], ["trace", "Trace"]],
  };
  const read = (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { console.warn("[nav] this browser keeps no settings:", e.message); return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { console.warn("[nav] this browser keeps no settings:", e.message); } };
  const st = { child: "", hidden: read(SIDE_KEY, false), expanded: new Set(read(OPEN_KEY, ["apps", "flows"].filter((id) => (SECTIONS[id] || { children: [] }).children.length <= 12))) };
  const sec = () => SECTIONS[App.section] || null;
  const textLed = (id) => VISUALS[id] && !VISUALS[id].length;
  const worst = (levels) => levels.slice().sort((p, q) => rank(q) - rank(p))[0] || "dark";

  /* ------------------------------------------------------------ what the views ask of the section */
  function title(fallback) {
    if (App.section === "home") return "What needs you";
    const s = sec();
    if (!s) return fallback;
    if (st.child && E[st.child]) return s.id === "apps" || s.id === "flows" ? E[st.child].title : `${s.label}: ${E[st.child].title}`;
    return s.label;
  }
  function sectionPage() {
    const s = sec();
    if (!s) return "";
    if (st.child && D.reader[st.child]) return st.child;
    return s.page && D.reader[s.page] ? s.page : "";
  }
  /* The page that sits beside the visual in the panel: none when the page itself fills the main area. */
  function pageBeside() { return textLed(App.section) || App.view === "doc" ? "" : sectionPage(); }
  function missingPage() { const s = sec(); return s ? `This vault has no ${s.path} yet, so there is no ${s.label.toLowerCase()} page to read.` : "No page."; }
  /* The section's own controls on every view head: its visuals, and the page to read. */
  function pageActions(opts = {}) {
    const s = sec();
    if (!s) return null;
    const box = h("div", { class: "page-actions" });
    const vis = VISUALS[s.id] || [];
    if (vis.length > 1 || (opts.reading && vis.length)) box.append(h("div", { class: "seg", role: "group", "aria-label": "Visual" }, vis.map(([v, label]) =>
      h("button", { "aria-pressed": String(App.view === v), onclick: () => { Sections.doc.page = ""; showView(v); } }, label))));
    const pk = sectionPage();
    if (s.id === "apps" && st.child && APPS[st.child] && typeof Inside !== "undefined" && App.view !== "inside") box.append(h("button", { class: "btn inside-btn", title: "Its context, its main containers, the team's components and its build plan", onclick: () => Inside.open(st.child, "containers") }, "Inside this app"));
    if (pk && App.view !== "doc") box.append(h("button", { class: "btn", title: "Read the section's page full width", onclick: () => readWide(pk) }, "Read the page"));
    const file = pk ? openLink(["Open the file"], D.vault ? D.vault + "/" + E[pk].path : "", E[pk].path, E[pk].path) : null;
    if (file) box.append(file);  // openLink is null when the page is opened from a file; Element.append would print the word "null"
    return box;
  }

  /* ------------------------------------------------------------ going places */
  function setRoot() {
    const pk = sectionPage();
    App.root = pk && !textLed(App.section) && App.view !== "doc" ? "read:" + pk : "lights";
  }
  function open(id, child, opts = {}) {
    const s = SECTIONS[id];
    if (!s) return home();
    App.section = id; st.child = child && E[child] ? child : "";
    Sections.doc.page = "";
    if (typeof Motion !== "undefined") Motion.clear();
    let view = (VISUALS[id] || [])[0] ? VISUALS[id][0][0] : "doc";
    MapView.st.focus = null;
    if (id === "apps") { MapView.st.lens = MapView.st.lens === "releases" ? null : MapView.st.lens; if (st.child) { MapView.st.focus = st.child; MapView.st.lens = "cockpit"; } if (MapView.st.group === "capability") MapView.st.group = null; }
    if (id === "capabilities") { MapView.st.group = "capability"; MapView.st.lens = "cockpit"; }
    if (id === "flows" && st.child) { Flows.st.key = st.child; Flows.st.cur = -1; }
    if (id === "decisions" && st.child) Decisions.showFor(st.child);
    if (id === "releases" && opts.state !== undefined) Releases.open(opts.state);
    App.trail = []; App.focus = st.child || null;
    App.view = viewDef(view) ? view : "doc";
    setRoot();
    syncHash(); rerender(); Panel.render();
    if (st.child && viewDef(App.view).highlight) viewDef(App.view).highlight(st.child);
  }
  function home() {
    App.section = "home"; st.child = ""; App.root = "lights"; App.trail = []; App.focus = null;
    MapView.st.focus = null; if (MapView.st.group === "capability") MapView.st.group = null;
    App.view = "map"; syncHash(); rerender(); Panel.render();
  }
  function role(r) {
    if (r === "lead") return home();
    Roles.st.role = r; App.section = "role:" + r; st.child = ""; App.root = "lights"; App.trail = [];
    App.view = "role"; syncHash(); rerender(); Panel.render();
  }
  function readWide(pk, anchor) {
    Sections.doc.page = pk; Sections.doc.anchor = anchor || "";
    App.view = "doc"; App.root = "lights"; App.trail = [];
    syncHash(); rerender(); Panel.render();
  }
  /* A view shown from anywhere (a search result, a link) brings its section with it. */
  function adopt(view) {
    if (view === "inside" || view === "ask" || view === "drafts") return;  // Inside.open and Ask.open set the section themselves
    if (App.section === "home" && view === "map") return;
    if (App.section.startsWith("role:") && view === "role") return;
    const s = sec();
    if (s && (VISUALS[s.id] || []).some(([v]) => v === view)) return;
    const owner = Object.entries(VISUALS).find(([, vs]) => vs.some(([v]) => v === view));
    App.section = view === "map" ? "apps" : owner ? owner[0] : App.section;
    st.child = "";
    MapView.st.focus = null;
    if (App.section !== "capabilities" && MapView.st.group === "capability") MapView.st.group = null;
    const keep = App.trail.slice();
    setRoot();
    App.trail = keep;
  }
  /* Where the reader is, so a view that takes them elsewhere (Ask) can bring them back to it. */
  function where() {
    return { section: App.section, child: st.child, view: App.view, trail: App.trail.slice(), focus: App.focus, root: App.root, doc: Sections.doc.page };
  }
  const whereLabel = (w) => {
    if (!w || w.section === "home") return "What needs you";
    if (w.section.startsWith("role:")) return (Roles.ROLES.find(([id]) => id === w.section.slice(5)) || [0, "the front door"])[1];
    const s = SECTIONS[w.section];
    return s ? (w.child && E[w.child] ? E[w.child].title : s.label) : "the explorer";
  };
  function back(w) {
    if (!w || w.section === "ask" || w.section === "drafts") return home();
    if (w.section === "home") home();
    else if (w.section.startsWith("role:")) role(w.section.slice(5));
    else if (w.view === "doc") { open(w.section, w.child); readWide(w.doc || sectionPage()); }
    else { open(w.section, w.child); if (w.view !== App.view && viewDef(w.view) && w.view !== "inside") showView(w.view); }
    App.trail = w.trail; App.focus = w.focus; App.root = w.root;
    Panel.render();
  }
  function focusApp(key) { open("apps", key); }
  function trace(key) { if (!(App.view === "map" && ["home", "apps"].includes(App.section) && MapView.lens() === "cockpit")) { App.section = "home"; MapView.st.lens = "cockpit"; App.view = "map"; App.root = "lights"; rerender(); }
    FX.setMotion("trace"); go(key, { reset: true }); Motion.trace(key); }
  function ripple(key) { if (!(App.view === "map" && MapView.lens() === "cockpit")) { App.section = "home"; MapView.st.lens = "cockpit"; App.view = "map"; App.root = "lights"; rerender(); }
    FX.setMotion("ripple"); const bar = $(".map-tools"); if (bar) $$("[data-motion]", bar).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.motion === "ripple")));
    App.trail = [key]; App.focus = key; Panel.render(); MapView.highlight(NODE[key] ? key : null); Motion.ripple(key); syncHash(); }
  function openRelease(i) { open("releases", "", { state: i }); }

  /* ------------------------------------------------------------ the hash */
  /* A move between views is a history entry, so Back returns to the view the lead came from (E33); the same address twice
     replaces, and so does a refinement inside a view (a flow's next step: view-flows.js). `written` is what this page last
     put in the address bar, so a hashchange the page did not make is a pasted link or a Back, and is followed. */
  let written = location.hash, following = false;
  function setHash(hash) {
    if (hash === location.hash) return;
    if (following) history.replaceState(null, "", hash); else history.pushState(null, "", hash);  // following a Back must not add an entry to go back to
    written = location.hash;
  }
  function followHash() {
    if (location.hash === written) return;
    written = location.hash;
    reloadHash();
    Flows.closePresent();
    following = true;
    try { followBoot(); } finally { following = false; }
    refresh();
  }
  function followBoot() {
    if (!boot()) {
      const open = HASH.get("open");
      if (open && ent(open)) { App.trail = [open]; App.focus = open; }
      if (App.view === "flows" && open && FLOW[open]) { Flows.st.key = open; Flows.st.cur = HASH.has("step") ? +HASH.get("step") - 1 : -1; }
      Panel.render(); rerender();
    }
    if (HASH.get("present") && FLOW[HASH.get("present")]) Flows.present(HASH.get("present"), (+HASH.get("step") || 1) - 1);
  }
  window.addEventListener("hashchange", followHash);
  function syncHash() {
    const p = [];
    if (App.view === "ask" && typeof Ask !== "undefined") {
      for (const keep of ["still", "fx", "selftest", "trace", "theme"]) if (HASH.has(keep)) p.push(keep + (HASH.get(keep) ? "=" + HASH.get(keep) : ""));
      setHash("#" + [Ask.hash(), ...p].join("&"));
      return;
    }
    if (App.view === "drafts") {
      for (const keep of ["still", "fx", "selftest", "trace", "theme"]) if (HASH.has(keep)) p.push(keep + (HASH.get(keep) ? "=" + HASH.get(keep) : ""));
      setHash("#" + ["drafts", ...p].join("&"));
      return;
    }
    if (App.view === "inside" && typeof Inside !== "undefined") {
      for (const keep of ["still", "fx", "selftest", "trace", "theme"]) if (HASH.has(keep)) p.push(keep + (HASH.get(keep) ? "=" + HASH.get(keep) : ""));
      setHash("#" + [Inside.hash(), ...p].join("&"));
      return;
    }
    if (App.section === "home") p.push("home");
    else if (App.section.startsWith("role:")) { p.push("role=" + App.section.slice(5)); if (App.section === "role:eng" && Roles.st.app) p.push("app=" + encodeURIComponent(Roles.st.app)); }
    else { p.push("s=" + App.section); if (st.child) p.push("open=" + encodeURIComponent(st.child)); }
    if (App.view === "doc") p.push("read" + (Sections.doc.page && Sections.doc.page !== sectionPage() ? "=" + encodeURIComponent(Sections.doc.page) : ""));
    else if (App.view !== (VISUALS[App.section] && VISUALS[App.section][0] ? VISUALS[App.section][0][0] : App.view) && !App.section.startsWith("role:") && App.section !== "home") p.push("v=" + App.view);
    if (App.view === "map") { if (MapView.st.lens) p.push("lens=" + MapView.st.lens); if (MapView.st.group) p.push("group=" + MapView.st.group); }
    if (App.view === "releases" || (App.view === "map" && MapView.lens() === "releases")) p.push("state=" + Releases.st.at);
    for (const keep of ["still", "fx", "selftest", "trace"]) if (HASH.has(keep)) p.push(keep + (HASH.get(keep) ? "=" + HASH.get(keep) : ""));
    setHash("#" + p.join("&"));
  }
  function boot() {
    const hs = HASH.get("s"), legacy = VIEWS.find((v) => (HASH.has(v.id) || (v.alias && HASH.has(v.alias))) && !["role", "doc"].includes(v.id));
    if (HASH.get("lens")) MapView.st.lens = HASH.get("lens");
    if (HASH.get("group")) MapView.st.group = HASH.get("group");
    if (HASH.has("role")) { role(HASH.get("role")); return true; }
    if (HASH.has("inside") && typeof Inside !== "undefined" && Inside.boot()) return true;
    if (HASH.has("drafts")) return Drafts.boot();
    if (hs && SECTIONS[hs]) {
      open(hs, HASH.get("open") || "");
      if (HASH.has("v") && viewDef(HASH.get("v"))) showView(HASH.get("v"), { keepHash: true });
      if (HASH.has("read")) readWide(HASH.get("read") || sectionPage());
      if (HASH.get("focus") && NODE[HASH.get("focus")]) { MapView.st.focus = HASH.get("focus"); rerender(); }
      return true;
    }
    if (HASH.has("ask") && typeof Ask !== "undefined") { Ask.boot(HASH.get("c")); return true; }
    if (legacy) { App.view = legacy.id; adopt(legacy.id); return false; }  // main.js carries on as before
    App.section = "home"; App.view = "map";
    if (HASH.get("focus") && NODE[HASH.get("focus")]) MapView.st.focus = HASH.get("focus");
    return false;
  }

  /* ------------------------------------------------------------ the sidebar */
  function sectionLamp(s) {
    if (s.id === "apps") return worst(D.map.apps.map((a) => levelOf(a.key)));
    if (s.id === "flows") return worst(D.flows.map((f) => levelOf(f.key)));
    if (s.id === "unknowns") return worst(D.asks.filter((u) => u.state === "open").map((u) => u.light.level));
    if (s.id === "goals") return D.above.length ? worst(D.above.map((a) => (ASK[a.unknown] ? ASK[a.unknown].light.level : "caution"))) : "dark";
    return "dark";
  }
  function count(s) {
    if (s.id === "unknowns") return D.asks.filter((u) => u.state === "open").length || "";
    if (s.id === "goals") return D.goals.length || "";
    if (s.id === "releases") return D.releases.count || "";
    return s.children.length || "";
  }
  function item(s) {
    const here = App.section === s.id, has = s.children.length > 0, openList = st.expanded.has(s.id);
    const lv = sectionLamp(s), missing = !s.page;
    const row = h("div", { class: "side-row" + (here && !st.child ? " on" : here ? " in" : "") + (missing ? " missing" : "") },
      has ? h("button", { class: "side-caret", "aria-expanded": String(openList), "aria-label": `${openList ? "Hide" : "Show"} the ${s.label.toLowerCase()}`, onclick: () => { openList ? st.expanded.delete(s.id) : st.expanded.add(s.id); write(OPEN_KEY, [...st.expanded]); refresh(); } }, openList ? "▾" : "▸") : h("span", { class: "side-caret blank" }),
      h("button", { class: "side-link", "data-section": s.id, "aria-current": here && !st.child ? "page" : null, title: missing ? `No ${s.path} in this vault yet` : s.title, onclick: () => open(s.id) },
        h("span", { class: "side-label" }, s.label), lv !== "dark" ? lampEl(lv) : null, h("span", { class: "side-n" }, count(s))));
    const out = [row];
    if (has && openList) out.push(h("div", { class: "side-kids" }, s.children.map((k) => {
      const lvk = levelOf(k), cur = here && st.child === k;
      return h("button", { class: "side-kid" + (cur ? " on" : ""), "data-section": s.id, "data-child": k, "aria-current": cur ? "page" : null, onclick: () => open(s.id, k), title: E[k].title },
        s.id === "apps" && NODE[k] ? Icons.forKey(k, "side-glyph") : null,
        h("span", { class: "side-label" }, s.id === "capabilities" || s.id === "epics" || s.id === "decisions" ? [E[k].title, idTag(E[k].id)] : E[k].title), lvk !== "dark" && D.lights[k] ? lampEl(lvk) : null);
    }).flatMap((kid) => (s.id === "apps" && here && st.child === kid.dataset.child && typeof Inside !== "undefined" ? [kid, Inside.sideEntry(kid.dataset.child)] : [kid]))));
    return out;
  }
  function refresh() {
    const side = $("#side");
    if (!side) return;
    document.body.classList.toggle("side-hidden", !!st.hidden);
    $("#side-toggle").setAttribute("aria-expanded", String(!st.hidden));
    side.innerHTML = "";
    const lit = Queue.total();
    side.append(h("div", { class: "side-group" }, h("div", { class: "side-h" }, "Front doors"),
      h("button", { class: "side-home" + (App.section === "home" ? " on" : ""), "aria-current": App.section === "home" ? "page" : null, title: Queue.needsYouSays(), onclick: home },
        h("span", { class: "side-label" }, "What needs you"), lit ? h("span", { class: "side-n lit " + (litSubjects()[0] ? litSubjects()[0].light.level : "caution") }, lit) : null),
      typeof Ask !== "undefined" && Ask.served() ? h("button", { class: "side-home side-ask" + (App.section === "ask" ? " on" : ""), "aria-current": App.section === "ask" ? "page" : null, title: "Ask Claude about the vault", onclick: () => Ask.open() },
        h("span", { class: "side-label" }, "Ask Claude"), Ask.count() ? h("span", { class: "side-n" }, Ask.count()) : null) : null,
      h("div", { class: "side-roles", role: "tablist", "aria-label": "Front doors by audience" }, Roles.ROLES.slice(1).map(([id, label, say]) =>
        h("button", { role: "tab", "aria-selected": String(App.section === "role:" + id), title: say, onclick: () => role(id) }, label)))));
    const vault = h("div", { class: "side-group" }, h("div", { class: "side-h" }, "The vault"));
    for (const s of D.sections) vault.append(...item(s));
    side.append(vault);
    side.append(h("div", { class: "side-foot" }, h("span", { class: "muted" }, `${D.initiative} · ${Object.keys(D.reader).length} pages`)));
  }
  $("#side-toggle").addEventListener("click", () => { st.hidden = !st.hidden; write(SIDE_KEY, st.hidden); refresh(); rerender(); });
  return { where, whereLabel, back, title, sectionPage, pageBeside, missingPage, pageActions, open, home, role, readWide, adopt, focusApp, trace, ripple, openRelease, syncHash, followHash, boot, refresh, st, VISUALS, SECTIONS };
})();
