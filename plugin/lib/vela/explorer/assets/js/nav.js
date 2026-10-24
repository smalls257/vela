/* Navigation: a collapsible sidebar in the vault's own section order, the front doors by audience at its top, and
   the router. Every section opens a section page: its visual in the main area, and its page, in the vault's own
   words, beside it in the panel. Constraints, Strategy and Glossary are mostly words, so their page fills the main
   area instead. The views the explorer already had are the visuals of their sections: the map is Apps, the capability
   cards, focus and matrix are Capabilities (capview.js), the played flows are Flows, Who to ask is Unknowns and risks, the decision log is
   Decisions, the stage ladder is Apps' second visual and the trace is Capabilities' and Epics'.

   Hash: #overview, #role=qa, #s=apps&open=APP-booking, #s=strategy&read, plus the map's &lens= &group= &focus= and the
   releases' &state=, and #onboard=eng&m=contracts for the path through the plan (onboard.js). The old deep links (#map, #flows&open=FLO-002, #asks&open=UNK-065, #garden&open=ADR-0002, now the decision log)
   still land where they did. */
const Nav = (() => {
  const OPEN_KEY = "explorer.side.open";  // the bar's width, and whether it is hidden, are SideSize's (panelsize.js)
  const SECTIONS = Object.fromEntries(D.sections.map((x) => [x.id, x]));
  // section -> its visuals, the first being the default; [] means its page is read full width
  const VISUALS = {
    goals: [["goals", "Goals"]], constraints: [], context: [["context", "Today and after"]], strategy: [],
    capabilities: [["capmap", "Capabilities"], ["capmatrix", "Dependency matrix"], ["trace", "Requirements to epics"]], releases: [["releases", "Timeline"]], slices: [["slices", "Slices"]],
    apps: [["map", "Map"], ["progress", "Progress"]], flows: [["flows", "Step through"]], concerns: [["concerns", "By app"]],
    decisions: [["decisions", "Decision log"]], unknowns: [["asks", "Who to ask"]], glossary: [], epics: [["epics", "Epics"], ["trace", "Requirements to epics"]],
    library: [["library", "Library"]],
  };
  const read = (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { console.warn("[nav] this browser keeps no settings:", e.message); return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { console.warn("[nav] this browser keeps no settings:", e.message); } };
  const st = { child: "", expanded: new Set(read(OPEN_KEY, ["apps", "flows"].filter((id) => (SECTIONS[id] || { children: [] }).children.length <= 12))) };
  const sec = () => SECTIONS[App.section] || null;
  const textLed = (id) => VISUALS[id] && !VISUALS[id].length;
  const worst = (levels) => levels.slice().sort((p, q) => rank(q) - rank(p))[0] || "dark";

  /* ------------------------------------------------------------ what the views ask of the section */
  function title(fallback) {
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
  function missingPage() { const s = sec(); return s ? `The ${s.label.toLowerCase()} page isn't written yet. The plan's lead writes it in a planning session.` : "No page."; }
  /* What each visual shows, one line, as the View menu says it. */
  const VISUAL_SAY = { capmap: "every capability as a card, and one in focus with what needs it and what it needs", capmatrix: "which capability needs which, across all of them", map: "the apps and the contracts between them", progress: "how far each app is, and what is waiting on someone", trace: "which requirements have an app and an epic behind them",
    epics: "every epic, and what it delivers", releases: "the system before and after each release" };
  const visualItem = ([v, label]) => ({ id: v, label, say: VISUAL_SAY[v] || null, checked: App.view === v, run: () => { Sections.doc.page = ""; showView(v); } });
  /* The View menu's items for the section the reader is in. A section with a map keeps the map's four views in the same
     menu as its other visuals, so Progress sits beside System map and Contracts only, whichever of them is showing. */
  function viewItems() {
    const s = sec(), vis = s ? VISUALS[s.id] || [] : [];
    if (!vis.some(([v]) => v === "map")) return vis.map(visualItem);
    const items = MapView.viewItems(), at = items.findIndex((x) => x.separator), others = vis.filter(([v]) => v !== "map").map(visualItem);
    items.splice(at < 0 ? items.length : at, 0, ...others);  // the other visuals sit with the views; the Moving markers switch stays last
    return items;
  }
  function viewMenu() {
    const items = viewItems();
    if (items.length < 2) return null;
    const here = items.find((x) => x.checked);
    return Menus.menu({ id: "view", label: "View", current: here ? here.label : "Reading the page", items: viewItems });
  }
  /* The page this section reads from, as a link in the lede under the title: "Read the full page". */
  function ledeLink() {
    const pk = sectionPage();
    if (!pk || App.view === "doc") return null;
    return h("a", { class: "lede-link", href: "#", title: "Read this section's page across the whole width", onclick: (ev) => { ev.preventDefault(); readWide(pk); } }, "Read the full page");
  }
  /* The ... menu: what the view adds (its `extra` items), then what every page has: Inside this app, and Open the page. */
  function moreItems(extra = []) {
    const s = sec(), pk = sectionPage(), items = (typeof extra === "function" ? extra() : extra).filter(Boolean);
    if (items.length) items.push({ separator: true });
    if (s && s.id === "apps" && st.child && APPS[st.child] && typeof Inside !== "undefined" && App.view !== "inside")
      items.push({ id: "inside", label: "Inside this app", say: "How this app is built, and the team's plan for building it", run: () => Inside.open(st.child, "containers") });
    const href = pk ? openHref(D.vault ? D.vault + "/" + E[pk].path : "", E[pk].path) : null;
    if (href) items.push({ id: "open-page", label: "Open the page", say: `${E[pk].title}, as it is written, in a new tab`, href, newTab: true });
    else if (pk && SERVED_HERE) items.push({ id: "open-page", label: "Open the page", disabled: true, why: "This page can only open files that are part of the plan, and this one isn't. Open it from your editor, or open the page as a file." });
    if (items.length && items[items.length - 1].separator) items.pop();  // nothing after the separator, so it goes
    return items;
  }
  function moreMenu(extra = []) {
    if (!moreItems(extra).length) return null;
    return Menus.menu({ id: "more", kind: "icon", glyph: "more", label: "More: layout and the page", align: "right", items: () => moreItems(extra) });
  }
  /* The section's own controls on a view head that has no diagram under it to carry them: its views, and the page. */
  function pageActions() {
    const s = sec();
    if (!s) return null;
    const kids = [viewMenu(), moreMenu()].filter(Boolean);
    return kids.length ? h("div", { class: "page-actions" }, ...kids) : null;
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
    const was = App.section === "capabilities" ? App.view : "";
    CapFocus.set(id === "capabilities" ? st.child : ""); Pan.forget("cockpit", "transit");
    if (id === "apps") { MapView.st.lens = MapView.st.lens === "releases" ? null : MapView.st.lens; if (st.child) { MapView.st.focus = st.child; MapView.st.lens = "cockpit"; } if (MapView.st.group === "capability") MapView.st.group = null; }
    if (id === "capabilities") view = CapView.enter(CapFocus.key(), opts, was);  // the cards, or the focus view when one is picked
    if (id === "flows" && st.child) { Flows.st.key = st.child; Flows.st.cur = -1; }
    if (id === "decisions" && st.child) Decisions.showFor(st.child);
    if (id === "releases" && opts.state !== undefined) Releases.open(opts.state);
    App.trail = []; App.focus = st.child || null;
    App.view = viewDef(view) ? view : "doc";
    setRoot();
    if (id === "library" && child) Library.showFor(child);  // #s=library&open=SRC-05 lands on the row, with its details beside it
    syncHash(); rerender(); Panel.render();
    /* A link lands on the exact item: a page with a Details panel shows the opened item there, not its summary. */
    if (st.child && ent(st.child) && DetailsPanel.active()) DetailsPanel.show(st.child, { reset: true, quiet: true });
    if (st.child && viewDef(App.view).highlight) viewDef(App.view).highlight(st.child);
  }
  function home() {
    App.section = "apps"; st.child = ""; App.root = "lights"; App.trail = []; App.focus = null;
    MapView.st.focus = null; if (MapView.st.group === "capability") MapView.st.group = null;
    CapFocus.set(""); Pan.forget("cockpit", "transit");
    App.view = "map"; syncHash(); rerender(); Panel.render();
  }
  /* The front page of whoever is viewing: their role's overview, which opens with Needs you. */
  function overview() { return role(viewingNow().id); }
  function role(r) {
    Roles.st.role = r; Roles.st.chosen = true; App.section = "role:" + r; st.child = ""; App.root = "lights"; App.trail = [];
    App.view = "role"; syncHash(); rerender(); Panel.render();
  }
  /* Getting up to speed, as `r` (named: the reader chose it, so it is their door from now on) or as the best guess for who is
     reading (not named). m: the part to open at. */
  function onboard(r, m, remember = !!r) {
    Onboard.open(r || Onboard.defaultRole(), m, remember); App.section = "onboard:" + Onboard.st.role; st.child = ""; App.root = "lights"; App.trail = [];
    App.view = "onboard"; syncHash(); rerender(); Panel.render();
  }
  function readWide(pk, anchor) {
    Sections.doc.page = pk; Sections.doc.anchor = anchor || "";
    App.view = "doc"; App.root = "lights"; App.trail = [];
    syncHash(); rerender(); Panel.render();
  }
  /* A view shown from anywhere (a search result, a link) brings its section with it. */
  function adopt(view) {
    if (view === "inside" || view === "ask" || view === "drafts" || view === "grills") return;  // Inside.open and Ask.open set the section themselves
    if (App.section.startsWith("role:") && view === "role") return;
    if (App.section.startsWith("onboard:") && view === "onboard") return;
    const s = sec();
    if (s && (VISUALS[s.id] || []).some(([v]) => v === view)) return;
    const owner = Object.entries(VISUALS).find(([, vs]) => vs.some(([v]) => v === view));
    App.section = view === "map" ? "apps" : owner ? owner[0] : App.section;
    st.child = "";
    MapView.st.focus = null;
    if (App.section !== "capabilities") CapFocus.set("");
    if (App.section !== "capabilities" && MapView.st.group === "capability") MapView.st.group = null;
    const keep = App.trail.slice();
    setRoot();
    App.trail = keep;
  }
  /* Where the reader is, so a view that takes them elsewhere (Ask) can bring them back to it. */
  function where() {
    return { section: App.section, child: st.child, view: App.view, trail: App.trail.slice(), focus: App.focus, root: App.root, doc: Sections.doc.page, module: App.section.startsWith("onboard:") ? Onboard.current() : undefined };
  }
  const whereLabel = (w) => {
    if (!w) return "the front door";
    if (w.section === "grills") return "Grills waiting";
    if (w.section.startsWith("role:")) return (Roles.ROLES.find(([id]) => id === w.section.slice(5)) || [0, "the front door"])[1];
    if (w.section.startsWith("onboard:")) return "Get up to speed";
    const s = SECTIONS[w.section];
    return s ? (w.child && E[w.child] ? E[w.child].title : s.label) : "the explorer";
  };
  function back(w) {
    if (!w || w.section === "ask" || w.section === "drafts") return home();
    if (w.section === "grills") Grills.open();
    else if (w.section.startsWith("role:")) role(w.section.slice(5));
    else if (w.section.startsWith("onboard:")) onboard(w.section.slice(8), w.module, false);
    else if (w.view === "doc") { open(w.section, w.child); readWide(w.doc || sectionPage()); }
    else { open(w.section, w.child); if (w.view !== App.view && viewDef(w.view) && w.view !== "inside") showView(w.view); }
    App.trail = w.trail; App.focus = w.focus; App.root = w.root;
    Panel.render();
  }
  function focusApp(key) { open("apps", key); }
  function trace(key) { if (!(App.view === "map" && App.section === "apps" && MapView.lens() === "cockpit")) { App.section = "apps"; MapView.st.lens = "cockpit"; App.view = "map"; App.root = "lights"; rerender(); }
    go(key, { reset: true }); Motion.trace(key); }
  function openRelease(i) { open("releases", "", { state: i }); }

  /* ------------------------------------------------------------ the hash */
  /* A move between views is a history entry, so Back returns to the view the lead came from (E33); the same address twice
     replaces, and so does a refinement inside a view (a flow's next step: view-flows.js). `written` is what this page last
     put in the address bar, so a hashchange the page did not make is a pasted link or a Back, and is followed. */
  let written = location.hash, following = false;
  function setHash(hash, replace) {
    if (hash === location.hash) return;
    if (following || replace) history.replaceState(null, "", hash); else history.pushState(null, "", hash);  // following a Back must not add an entry to go back to
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
  /* opts.replace: a refinement inside a view (a filter, a search word) replaces the entry instead of adding one. */
  function syncHash(opts) {
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
    if (App.section.startsWith("onboard:")) p.push(...Onboard.hashParts());
    else if (App.section.startsWith("role:")) { p.push("role=" + App.section.slice(5)); if (App.section === "role:eng" && Roles.st.app) p.push("app=" + encodeURIComponent(Roles.st.app)); }
    else { p.push("s=" + App.section); if (st.child) p.push("open=" + encodeURIComponent(st.child)); }
    if (App.view === "doc") p.push("read" + (Sections.doc.page && Sections.doc.page !== sectionPage() ? "=" + encodeURIComponent(Sections.doc.page) : ""));
    else if (App.view !== (VISUALS[App.section] && VISUALS[App.section][0] ? VISUALS[App.section][0][0] : App.view) && !App.section.startsWith("role:")) p.push("v=" + App.view);
    if (App.view === "map") { if (MapView.st.lens) p.push("lens=" + MapView.st.lens); if (MapView.st.group) p.push("group=" + MapView.st.group); }
    if (App.view === "releases" || (App.view === "map" && MapView.lens() === "releases")) p.push("state=" + Releases.st.at);
    for (const keep of ["still", "fx", "selftest", "trace"]) if (HASH.has(keep)) p.push(keep + (HASH.get(keep) ? "=" + HASH.get(keep) : ""));
    if (App.view === "slices" && typeof Slices !== "undefined") p.push(...Slices.hashParts());
    if (App.view === "grills") p.push(...Grills.hashParts());
    if (App.view === "flows" && typeof Branches !== "undefined" && Flows.st.key) { const b = Branches.hashPart(Flows.st.key); if (b) p.push(b.slice(1)); }
    if (App.view === "flows" && typeof FlowView !== "undefined" && Flows.st.key) { const b = FlowView.hashPart(Flows.st.key); if (b) p.push(b.slice(1)); }
    setHash("#" + p.join("&"), !!(opts && opts.replace));
  }
  function boot() {
    if (typeof Slices !== "undefined") Slices.readHash();  // a link to the slices brings its filters; one without clears them
    const hs = HASH.get("s"), legacy = VIEWS.find((v) => (HASH.has(v.id) || (v.alias && HASH.has(v.alias))) && !["role", "doc"].includes(v.id));
    if (HASH.get("lens")) MapView.st.lens = HASH.get("lens");
    if (MapView.GROUP_IDS.includes(HASH.get("group"))) MapView.st.group = HASH.get("group");  // only a grouping the map has: a stray value once broke its Group menu
    if (HASH.has("onboard")) { onboard(HASH.get("onboard"), HASH.get("m")); return true; }
    if (HASH.has("role")) { role(HASH.get("role")); return true; }
    if (HASH.has("overview")) { overview(); return true; }  // #overview: the front page of whoever is viewing, without naming a role
    if (HASH.has("inside") && typeof Inside !== "undefined" && Inside.boot()) return true;
    if (HASH.has("drafts")) return Drafts.boot();
    if (hs === "grills" && Grills.exists()) return Grills.boot();
    if (hs && SECTIONS[hs]) {
      open(hs, HASH.get("open") || "");
      if (HASH.has("v") && viewDef(HASH.get("v"))) showView(HASH.get("v"), { keepHash: true });
      if (HASH.has("read")) readWide(HASH.get("read") || sectionPage());
      if (HASH.get("focus") && NODE[HASH.get("focus")]) { MapView.st.focus = HASH.get("focus"); rerender(); }
      return true;
    }
    if (HASH.has("ask") && typeof Ask !== "undefined") { Ask.boot(HASH.get("c")); return true; }
    if (legacy) { App.view = legacy.id; adopt(legacy.id); return false; }  // main.js carries on as before
    App.section = "apps"; App.view = "map";
    if (HASH.get("focus") && NODE[HASH.get("focus")]) MapView.st.focus = HASH.get("focus");
    return false;
  }

  /* ------------------------------------------------------------ the sidebar */
  function sectionLamp(s) {
    if (s.id === "apps") return worst(D.map.apps.map((a) => levelOf(a.key)));
    if (s.id === "flows") return worst(D.flows.map((f) => levelOf(f.key)));
    if (s.id === "unknowns") return worst(D.asks.filter((u) => u.state === "open").map((u) => u.light.level));
    if (s.id === "slices") return worst(D.slicePlan.list.filter((x) => x.key).map((x) => levelOf(x.key)));
    if (s.id === "goals") return D.above.length ? worst(D.above.map((a) => (ASK[a.unknown] ? ASK[a.unknown].light.level : "caution"))) : "dark";
    return "dark";
  }
  function count(s) {
    if (s.id === "unknowns") return D.asks.filter((u) => u.state === "open").length || "";
    if (s.id === "goals") return D.goals.length || "";
    if (s.id === "releases") return D.releases.count || "";
    return s.children.length || "";
  }
  /* A section's count shows only beside a lit lamp: a dozen bare numbers down the side were a dozen things to hold. */
  function sideCount(s) {
    const n = count(s), open = s.id === "unknowns";
    return h("span", { class: "side-n", title: open ? `${plural(n, "open question")} in all` : `${s.label}: ${n}`, ...(open ? { "aria-label": `${plural(n, "open question")} in all` } : {}), ...(open ? { "data-quantity": "openQuestions", "data-n": n } : {}) }, n);
  }
  /* Flow names often start alike ("A person switches it on", "A person gets the morning digest"), and a narrow bar cuts every one
     to the same stub. The two words most of them share are left off in the bar (the hover keeps the whole name). */
  const READ = ["constraints", "context", "strategy", "glossary"];  // pages that are mostly words: one folded heading, not four rows between the diagrams
  function sharedLead(titles) {
    const lead = (t) => t.split(/\s+/).slice(0, 2).join(" "), tally = {};
    for (const t of titles) tally[lead(t)] = (tally[lead(t)] || 0) + 1;
    const [best, n] = Object.entries(tally).sort((a, b) => b[1] - a[1])[0] || ["", 0];
    return titles.length >= 3 && n >= 3 && n * 2 > titles.length ? best + " " : "";
  }
  function kidLabel(s, k) {
    const title = E[k].title, lead = s.id === "flows" ? sharedLead(s.children.map((x) => E[x].title)) : "";
    return lead && title.startsWith(lead) && title.length > lead.length ? title.slice(lead.length) : title;
  }
  /* The triangle and the row's name both fold a list: the name is the bigger target, and readers kept looking for the click there. */
  function foldList(id) { st.expanded.has(id) ? st.expanded.delete(id) : st.expanded.add(id); write(OPEN_KEY, [...st.expanded]); }
  function item(s) {
    const here = App.section === s.id, has = s.children.length > 0, openList = st.expanded.has(s.id), kept = CapFocus.kids(s);
    const lv = sectionLamp(s), missing = !s.page && !(s.id === "slices" && D.slicePlan.list.length) && s.id !== "library";  // slices have no index page: each slice is one; the library is a view of the register
    const row = h("div", { class: "side-row" + (here && !st.child ? " on" : here ? " in" : "") + (missing ? " missing" : "") },
      has ? h("button", { class: "side-caret", "aria-expanded": String(openList), "aria-label": `${openList ? "Hide" : "Show"} the ${s.label.toLowerCase()}`, onclick: () => { foldList(s.id); refresh(); } }, openList ? "▾" : "▸") : h("span", { class: "side-caret blank" }),
      h("button", { class: "side-link", "data-section": s.id, "aria-current": here && !st.child ? "page" : null, ...(has ? { "aria-expanded": String(openList) } : {}),
        title: missing ? `The ${s.label.toLowerCase()} page isn't written yet` : s.id === "slices" ? `${s.title}. ${termTip("slice")}` : s.id === "library" ? "Every spec, design, document and link the plan rests on, grouped by what it is" : s.title,
        onclick: () => { if (has) foldList(s.id); open(s.id); refresh(); } },
        h("span", { class: "side-label" }, s.label), lv !== "dark" ? lampEl(lv) : null, lv !== "dark" && count(s) ? sideCount(s) : null,
        CapFocus.narrowed(s) ? h("span", { class: "side-n capfocus-count", title: `${kept.length} of ${s.children.length} ${s.label.toLowerCase()} touch ${ent(CapFocus.key()).title}` }, `${kept.length} of ${s.children.length}`) : null));
    const out = [row];
    if (has && openList) out.push(h("div", { class: "side-kids" }, kept.map((k) => {
      const lvk = levelOf(k), cur = here && st.child === k;
      return h("button", { class: "side-kid" + (cur ? " on" : ""), "data-section": s.id, "data-child": k, "aria-current": cur ? "page" : null, onclick: () => open(s.id, k), title: E[k].title },
        s.id === "apps" && NODE[k] ? Icons.forKey(k, "side-glyph") : null,
        h("span", { class: "side-label" }, s.id === "capabilities" || s.id === "epics" || s.id === "decisions" ? [E[k].title, idTag(E[k].id)] : kidLabel(s, k)), lvk !== "dark" && D.lights[k] ? lampEl(lvk) : null);
    }).flatMap((kid) => (s.id === "apps" && here && st.child === kid.dataset.child && typeof Inside !== "undefined" ? [kid, Inside.sideEntry(kid.dataset.child)] : [kid]))));
    return out;
  }
  /* "Read": the text-first pages under one heading that stays folded until it is opened, or until one of them is the page. */
  function readGroup(reads) {
    const inside = reads.some((s) => s.id === App.section), open = st.expanded.has("read") || inside;
    const toggle = () => { st.expanded.has("read") ? st.expanded.delete("read") : st.expanded.add("read"); write(OPEN_KEY, [...st.expanded]); refresh(); };
    return [h("div", { class: "side-row side-read-row" + (inside ? " in" : "") },
        h("button", { class: "side-caret", "aria-expanded": String(open), "aria-controls": "side-read", "aria-label": `${open ? "Hide" : "Show"} the pages to read`, onclick: toggle }, open ? "▾" : "▸"),
        h("button", { class: "side-link", "data-group": "read", title: "Pages that are mostly words: " + reads.map((s) => s.label).join(", "), onclick: toggle }, h("span", { class: "side-label" }, "Read"))),
      h("div", { class: "side-kids side-read", id: "side-read", hidden: !open }, reads.flatMap((s) => item(s)))];
  }
  /* "Viewing as": the one place the reader says who they are. It is the same setting as onboarding's "Reading as" and the
     role door (Onboard.myRole), so the "Waiting on you" filter, the door and the path all follow it. A pick always applies;
     the plan's record and the person's own choice only decide the default before anything is picked. When the pick differs
     from the plan's record for this handle, a line under the menu says so and offers the way back. */
  function viewingNow() { const m = Onboard.myRole(); return { id: m.role || "lead", source: m.source }; }
  const roleName = (id) => (Roles.ROLES.find(([r]) => r === id) || [id, id])[1];
  function viewAs(r) {
    Onboard.rememberDoor(r);
    if (App.section.startsWith("role:")) role(r);
    else if (App.section.startsWith("onboard:")) onboard(r);
    else { rerender(); Panel.render(); }
    refresh();
    renderMasters();  // the "for you" and grills badges count for the role now viewing
  }
  function viewingAs() {
    const now = viewingNow(), label = roleName(now.id), rec = Onboard.recorded();
    const menu = Menus.menu({ id: "viewing-as", label: "Viewing as", current: label, extraClass: "side-as-btn",
      items: () => Roles.ROLES.map(([id, name, say]) => ({ id, label: name, say, checked: id === viewingNow().id, run: () => viewAs(id) })) });
    const id = now.id, onRole = App.section === "role:" + id;
    const note = rec && rec !== id ? h("p", { class: "side-note small muted" }, `Your recorded role is ${roleName(rec)}. `, h("button", { class: "linkish", type: "button", onclick: () => viewAs(rec) }, "Switch back")) : null;
    return h("div", { class: "side-group side-as" }, menu, note,
      h("button", { class: "side-sub side-overview" + (onRole ? " on" : ""), "aria-current": onRole ? "page" : null, onclick: () => role(id) }, `Overview for ${label} ›`),
      h("button", { class: "side-sub side-onboard" + (App.section.startsWith("onboard:") ? " on" : ""), "aria-current": App.section.startsWith("onboard:") ? "page" : null,
        title: "A short path through the plan for your role", onclick: () => onboard(id) }, `Get up to speed as ${label} ›`));
  }
  function refresh() {
    const side = $("#side");
    if (!side) return;
    side.innerHTML = "";
    side.append(viewingAs(), h("div", { class: "side-group" }, h("div", { class: "side-h" }, "Start here"),
      Grills.exists() ? h("button", { class: "side-grills-door" + (App.section === "grills" ? " on" : ""), "aria-current": App.section === "grills" ? "page" : null, title: Grills.badgeTip(), onclick: () => Grills.open() },
        h("span", { class: "side-label" }, "Grills waiting"), Grills.count() ? h("span", { class: "side-n lit caution", "data-grills-count": Grills.count() }, Grills.count()) : null) : null,
      typeof Ask !== "undefined" && Ask.served() ? h("button", { class: "side-home side-ask" + (App.section === "ask" ? " on" : ""), "aria-current": App.section === "ask" ? "page" : null, title: "Ask Claude about the plan", onclick: () => Ask.open() },
        h("span", { class: "side-label" }, "Ask Claude"), Ask.count() ? h("span", { class: "side-n" }, Ask.count()) : null) : null));
    const vault = h("div", { class: "side-group" }, CapFocus.bar("side"), h("div", { class: "side-h" }, "Plan pages"));
    const reads = D.sections.filter((s) => READ.includes(s.id));
    for (const s of D.sections) if (!READ.includes(s.id)) vault.append(...item(s));
    if (reads.length) vault.append(...readGroup(reads));
    side.append(vault);
    side.append(h("div", { class: "side-foot" }, h("span", { class: "muted", title: D.initiative ? `Initiative ${D.initiative}` : null }, `Search all ${plural(Object.keys(D.reader).length, "page")} with /`)));
  }
  return { where, whereLabel, back, title, sectionPage, pageBeside, missingPage, pageActions, viewMenu, moreMenu, moreItems, ledeLink, viewItems, open, home, overview, role, onboard, viewAs, readWide, adopt, focusApp, trace, openRelease, syncHash, followHash, boot, refresh, st, VISUALS, SECTIONS };
})();
