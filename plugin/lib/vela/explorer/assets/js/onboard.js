/* Getting up to speed: a path of modules on the left (with minutes and progress) and the module on the right, a view of
   the real items for this person beside an explanation, with links that open the dashboard's own views. Everything it
   says comes from D.onboard, which `vela onboard` reads too (explorer/onboard_data.py), so a path the person's Claude
   sets is exactly the path shown here. The page adds no text of its own beyond its labels; a module the plan is silent
   on says "Not recorded yet" and who to ask, and is never hidden. Routes: #onboard=<role>&m=<module>.
   - The role switcher is the front doors' (Roles.ROLES). The standard path is the plan's, shaped by the lead's page; a
     person's own path (D.onboard.mine) replaces it for their role, and "Show the standard path" brings the other back.
   - Progress is kept in this browser per vault, person and role: which parts were moved through with Next. Clicking a
     part in the list skips to it and ticks nothing. Start over clears it.
   - The items are nodes (Nodes.wire): cards by default, or a board of boxes with arrows where order matters, with a key.
     The bar over them is the diagram bar's (Menus.frame). */
const Onboard = (() => {
  const O = D.onboard;
  const ORDERED = ["approach", "slices", "dates", "progress"];  // items that come in an order: the board joins them with arrows
  const STAGE_SAY = { discovery: "This initiative is in discovery: the goals, the people and the open questions matter most.",
    design: "This initiative is in design: the apps, contracts, journeys and slices matter most.",
    delivery: "This initiative is in delivery: slice status, the build plan and what is stuck matter most." };
  const DEPTHS = [["gist", "Just the gist"], ["normal", "Normal"], ["everything", "Everything"]];
  const st = { role: "", at: 0, standard: false, depth: null, shape: null };
  const lastKey = `onboard:${D.vaultId}:role`;
  const who = () => (O.mine ? O.mine.handle : "reader");
  /* Depth and diagrams are kept per reader too: a choice made on the shared copy ("reader") must not override the path a person's own page was built with. */
  const depthKey = () => `onboard:${D.vaultId}:${who()}:depth`, shapeKey = () => `onboard:${D.vaultId}:${who()}:shape`;
  const doneKey = (role) => `onboard:${D.vaultId}:${who()}:${role}`;
  const readDone = (role) => { const v = Settings.readJson(doneKey(role), null, "your onboarding progress"); return new Set(v && Array.isArray(v.done) ? v.done : []); };
  const writeDone = (role, set) => Settings.write(doneKey(role), JSON.stringify({ done: [...set] }));
  const mine = (role) => (O.mine && O.mine.audience === role && !st.standard ? O.mine : null);
  const keys = (role) => (mine(role) ? mine(role).keys : O.paths[role].modules);
  const mod = (k) => O.modules[k];
  const depth = () => st.depth || Settings.read(depthKey()) || (O.mine && O.mine.depth) || "normal";
  const shape = () => st.shape || Settings.read(shapeKey()) || (mine(st.role) && mine(st.role).diagrams ? "diagram" : "cards");
  const roleLabel = (id) => (Roles.ROLES.find(([r]) => r === id) || [id, id])[1];
  const current = () => { const ks = keys(st.role); return ks[Math.min(st.at, ks.length - 1)]; };
  const hashParts = () => [`onboard=${st.role}`, `m=${encodeURIComponent(current())}`];

  /* ------------------------------------------------------------ the key: what a box's edge says */
  const { bx, ln } = Legend;
  Legend.define("ob.ok", [bx({ fill: "deck-2", stroke: "mix-fact", w: 2 })], "Blue edge: decided or confirmed");
  Legend.define("ob.open", [bx({ fill: "deck-2", stroke: "caution", w: 2 })], "Amber edge: proposed, or still open");
  Legend.define("ob.late", [bx({ fill: "deck-2", stroke: "warning", w: 2 })], "Red edge: overdue");
  Legend.define("ob.arrow", [ln({ stroke: "ink-3", head: "fill" })], "Arrow: the order they come in");

  /* ------------------------------------------------------------ going places */
  /* A role the reader chose (the menu here, or #onboard=<role>) is the role door they picked, the same one the front doors set
     (Roles.st), so the page has one answer to "who is reading" whichever way they chose. Opening the door with no role named
     is not a choice: it opens as the best guess and leaves the reader unknown. */
  function rememberDoor(role) { Roles.st.role = role; Roles.st.chosen = true; Settings.write(lastKey, role); }
  function open(role, key, remember) {
    st.role = O.paths[role] ? role : "exec";
    if (remember) rememberDoor(st.role);
    const ks = keys(st.role), at = ks.indexOf(key);
    if (at >= 0) st.at = at;
    else { const done = readDone(st.role), first = ks.findIndex((k) => !done.has(k)); st.at = first < 0 ? 0 : first; }
  }
  /* Who the reader is, as a role. A role the reader picked (the Viewing as menu, onboarding's Reading as, a role door or
     #role= / #onboard= route; this browser remembers the last one) always wins: a pick that did nothing would be a dead
     control. When nothing has been picked, the default follows the same order as onboarding.role_for: the plan's record for
     the handle this page was built for, then that person's own choice (`vela whoami --role`). The "Waiting on you" filter
     asks this too (queue.js). Returns {role, source} (source "pick", "record" or "choice") or {role: "", source: ""}. */
  const recordFor = (handle) => { const at = Object.keys(O.roles).find((k) => k.toLowerCase() === String(handle).toLowerCase()); return at ? O.roles[at] : ""; };
  const recorded = () => { const r = O.me ? recordFor(O.me.handle) : ""; return r && O.paths[r] ? r : ""; };
  function myRole() {
    const pick = Roles.st.chosen ? Roles.st.role : Settings.read(lastKey);
    const picks = [["pick", pick], ["record", O.me ? recordFor(O.me.handle) : ""], ["choice", O.me ? O.me.role : ""]];
    const found = picks.find(([, r]) => r && O.paths[r]);
    return found ? { role: found[1], source: found[0] } : { role: "", source: "" };
  }
  /* A person's own page opens on their path's role; only a role named in the address (or, on the shared copy, the best guess) changes that. */
  function defaultRole() { return HASH.get("onboard") || (O.mine && O.mine.audience) || myRole().role || "exec"; }
  function pick(key) { st.at = Math.max(0, keys(st.role).indexOf(key)); Nav.syncHash({ replace: true }); rerender(); }
  function step(by) { st.at = clamp(st.at + by, 0, keys(st.role).length - 1); Nav.syncHash({ replace: true }); rerender(); }
  function finishOne() {
    const ks = keys(st.role), done = readDone(st.role);
    done.add(current()); writeDone(st.role, done);
    if (st.at >= ks.length - 1) toast("That is the whole path. You can start over any time."); else st.at++;
    Nav.syncHash({ replace: true }); rerender();
  }
  function startOver() { writeDone(st.role, new Set()); st.at = 0; Nav.syncHash({ replace: true }); rerender(); }

  /* ------------------------------------------------------------ the items */
  const shownItems = (m) => { const cap = O.depths[depth()].items; return cap === null ? m.items : m.items.slice(0, cap); };
  function wired(el, it, m) {
    const aria = [it.label, it.pill, it.note].filter(Boolean).join(". ");
    if (it.key && ent(it.key)) return Nodes.wire(el, { label: it.label, key: it.key, aria });
    const note = Nodes.note({ diagram: "Getting up to speed", name: it.label, kind: m.title, text: it.note || "", facts: it.pill ? [["Status", it.pill]] : [] });
    return Nodes.wire(el, { label: it.label, note, aria });
  }
  function itemEl(it, m, cls) {
    const el = h("button", { class: `${cls} ${it.tone || ""}`.trim(), type: "button" }, h("span", { class: "ob-t" }, it.label),
      it.pill ? h("span", { class: `pill ob-pill ${it.tone || ""}`.trim() }, it.pill) : null, it.note ? h("small", {}, it.note) : null);
    return wired(el, it, m);
  }
  /* A link that only opens a section (#asks, #s=releases) is named for the section; one that opens the item is named for the item. */
  function openName(it) {
    const sec = it.href === "#asks" ? "unknowns" : (/^#s=([a-z-]+)$/.exec(it.href) || [])[1], s = sec && D.sections.find((x) => x.id === sec);
    return s ? `Open ${s.id === "unknowns" ? "Who to ask" : s.label}` : `Open ${it.label} in its own view`;
  }
  const openLink = (it) => (it.href ? h("a", { class: "ob-open", href: it.href, title: openName(it), "aria-label": openName(it) }, "↗") : null);
  function cards(m, shown) { return h("ul", { class: "ob-items" }, shown.map((it) => h("li", { class: "ob-row" }, itemEl(it, m, "ob-item"), openLink(it)))); }
  function board(m, shown, key) {
    const ordered = ORDERED.includes(m.id), kids = [];
    shown.forEach((it, i) => {
      if (ordered && i) { kids.push(h("span", { class: "ob-arrow", "aria-hidden": "true" }, "→")); key.saw("ob.arrow"); }
      kids.push(h("span", { class: "ob-cell" }, itemEl(it, m, "ob-node"), openLink(it)));
      if (it.tone) key.saw("ob." + it.tone);
    });
    return h("div", { class: "ob-board" + (ordered ? " ordered" : "") }, kids);
  }
  function viewColumn(m) {
    const shown = shownItems(m), diagram = shape() === "diagram" && shown.length > 0;
    const key = Legend.open("onboard", { root: () => $(".onb-view"), probes: { "ob.ok": ".ob-node.ok", "ob.open": ".ob-node.open", "ob.late": ".ob-node.late", "ob.arrow": ".ob-arrow" } });
    const body = !m.items.length ? emptyState(m.notRecorded ? "Not recorded yet." : "There is nothing to list.", m.notRecorded ? `Ask ${m.notRecorded.ask}.` : "")
      : diagram ? board(m, shown, key) : cards(m, shown);
    const more = m.items.length - shown.length;
    const showMenu = Menus.menu({ id: "onb-show", label: "Show", current: diagram ? "Diagram" : "Cards", items: () => [
      { id: "cards", label: "Cards", say: "Each thing as a card", checked: shape() !== "diagram", run: () => { st.shape = "cards"; Settings.write(shapeKey(), "cards"); rerender(); } },
      { id: "diagram", label: "Diagram", say: "Boxes you can click, joined by arrows where order matters", checked: shape() === "diagram", run: () => { st.shape = "diagram"; Settings.write(shapeKey(), "diagram"); rerender(); } }] });
    const wrap = Menus.frame({ left: [m.items.length ? showMenu : null], right: [diagram ? Menus.keyButton(key) : null],
      say: [h("span", { class: "dia-hint" }, m.items.length ? `${plural(m.items.length, "thing")} from the plan, as it stands today` : "")] },
      h("div", { class: "ob-scroll" }, body, more > 0 ? h("p", { class: "muted small ob-more" }, `${plural(more, "more thing")} at the Everything depth.`) : null));
    key.paint();
    return h("div", { class: "onb-view", "data-module": m.id }, wrap);
  }

  /* ------------------------------------------------------------ the explanation */
  function termsFirstUsed(m, ks, at) {
    const seen = new Set();
    ks.slice(0, at).forEach((k) => mod(k).terms.forEach((t) => seen.add(t)));
    return m.terms.filter((t) => !seen.has(t));
  }
  function explainColumn(m, ks, done) {
    const d = O.depths[depth()], body = d.body === null ? m.body : m.body.slice(0, d.body), last = st.at >= ks.length - 1;
    return h("div", { class: "onb-explain" }, h("h3", {}, m.title), h("p", { class: "ob-gist" }, m.gist),
      body.map((b) => h("p", {}, b)),
      termsFirstUsed(m, ks, st.at).map((t) => h("p", { class: "ob-term" }, termTip(t))),
      m.links.length ? h("div", { class: "ob-links" }, m.links.map((l) => h("a", { class: "ob-link", href: l.href }, l.label))) : null,
      m.tryIt ? h("div", { class: "ob-try" }, h("b", {}, "Try it: "), m.tryIt) : null,
      h("div", { class: "ob-depth", role: "radiogroup", "aria-label": "How much to show" }, h("span", { class: "muted small" }, "Depth"),
        DEPTHS.map(([id, label]) => h("button", { type: "button", role: "radio", "aria-checked": String(depth() === id), onclick: () => { st.depth = id; Settings.write(depthKey(), id); rerender(); } }, label))),
      h("div", { class: "onb-nav" }, h("button", { class: "btn", type: "button", disabled: st.at === 0 ? "" : null, onclick: () => step(-1) }, "Back"),
        h("button", { class: "btn go", type: "button", onclick: finishOne }, last ? "Finish" : `Next: ${mod(ks[st.at + 1]).title}`)));
  }

  /* ------------------------------------------------------------ the path and the page */
  function pathPane(role, ks, done) {
    const total = ks.reduce((n, k) => n + mod(k).minutes, 0), n = ks.filter((k) => done.has(k)).length, own = mine(role);
    return h("aside", { class: "onb-path", "aria-label": "The path" }, h("h2", {}, own ? "Your path" : "The standard path"),
      h("p", { class: "muted small" }, `${roleLabel(role)}: ${plural(ks.length, "part")}, about ${total} minutes.`),
      O.mine && O.mine.audience === role ? h("button", { class: "btn tiny", type: "button", onclick: () => { st.standard = !st.standard; open(role); Nav.syncHash({ replace: true }); rerender(); } },
        st.standard ? "Show my path" : "Show the standard path") : null,
      h("div", { class: "onb-bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(ks.length), "aria-valuenow": String(n), "aria-label": `${n} of ${ks.length} parts done` }, h("i", { style: `width:${ks.length ? (100 * n) / ks.length : 0}%` })),
      h("ol", { class: "onb-mods" }, ks.map((k, i) => { const m = mod(k); return h("li", {}, h("button", { type: "button", class: "onb-mod" + (done.has(k) ? " done" : "") + (i === st.at ? " on" : ""), "data-module": k, "aria-current": i === st.at ? "step" : null, onclick: () => pick(k) },
        h("span", { class: "onb-n" }, done.has(k) ? "✓" : String(i + 1)), h("span", { class: "onb-mt" }, m.title, h("small", {}, m.lede)), h("small", { class: "onb-min" }, `${m.minutes} min`))); })),
      n ? h("button", { class: "btn tiny", type: "button", onclick: startOver }, "Start over") : null,
      O.paths[role].note ? h("div", { class: "onb-lead" }, h("b", {}, "From the lead: "), O.paths[role].note) : null);
  }
  function render(main) {
    if (!st.role) open(defaultRole(), HASH.get("m"));
    const role = st.role, ks = keys(role), done = readDone(role);
    if (st.at >= ks.length) st.at = 0;
    const m = mod(ks[st.at]);
    const roleMenu = Menus.menu({ id: "onb-role", label: "Reading as", current: roleLabel(role), items: () => Roles.ROLES.filter(([id]) => O.paths[id]).map(([id, label, say]) =>
      ({ id, label, say, checked: id === role, run: () => Nav.onboard(id) })) });
    const head = h("div", { class: "view-head" }, h("div", {}, h("div", { class: "kicker" }, "Get up to speed"), h("h1", {}, `${roleLabel(role)}: what to know first`), h("p", {}, STAGE_SAY[O.stage])),
      h("div", { class: "spacer" }), h("div", { class: "page-actions" }, roleMenu));
    main.append(head, h("div", { class: "onb", "data-role": role },
      h("div", { class: "onb-body" }, pathPane(role, ks, done),
        h("section", { class: "onb-stage", "aria-live": "polite" }, h("h2", {}, `${st.at + 1} · ${m.title}`), h("p", { class: "lede" }, m.lede),
          h("div", { class: "onb-grid" }, viewColumn(m), explainColumn(m, ks, done))))));
  }
  /* ------------------------------------------------------------ the Details panel (detailspanel.js)
     Picking an item here shows what picking it on its own page shows: a question is the Who to ask question, a decision the
     decision log's record, a person their waiting questions and what they own, a release what it ships. Nothing here words them. */
  const decided = (k) => (k.startsWith("decision:") && typeof Decisions !== "undefined" ? Decisions.entries.find((x) => x.id === k.slice(9)) || null : null);
  function summaryNodes() {
    const m = mod(current());
    return [PlanDetails.head("Get up to speed", m.title), h("div", { class: "p-body" }, h("div", { class: "p-note" }, `Pick a thing in ${m.title} to read its details here: what it is, who it waits on and what it holds up.`))];
  }
  DetailsPanel.register("onboard", {
    view: "onboard", live: () => true, rootLabel: "Get up to speed", summary: summaryNodes,
    owns: (k) => !!decided(k) || PlanDetails.owns(k),
    detail: (k) => (decided(k) ? Decisions.decisionNodes(decided(k)) : PlanDetails.detail(k, "onboard")),
    label: (k) => (decided(k) ? decided(k).name : PlanDetails.label(k)),
    open: (k) => (decided(k) ? { label: "Open", title: "See it in the decision log", run: () => { showView("decisions"); Decisions.showFor(decided(k).key); } } : PlanDetails.openFor(k, "onboard")),
    waiting: (k) => PlanDetails.waitingTab(k, "queue"), waitingCount: () => PlanDetails.waitingCount("queue"), focus: () => {},
  });
  return { render, open, rememberDoor, st, keys, mod, hashParts, current, defaultRole, myRole, recorded };
})();
View("onboard", { label: "Get up to speed", title: "A path through the plan for your role", render: Onboard.render });
