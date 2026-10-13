/* The visuals of the sections that had no view of their own, each beside its page:
   - Goals: each goal row with its state, the open questions that hold it and the epics that deliver it.
   - Concerns: the concern cells, concern by app, as the concern pages' tables record them.
   - Epics: each epic with its acceptance criteria, concern markers, apps and what it delivers.
   - Context and scope: the system today beside the system after (releases.js's drawing).
   - A page read full width, with its contents list: Constraints, Strategy and Glossary are mostly words, so their
     page fills the main area; any other section's page reads this way from "Read the page". */
const Sections = (() => {
  const worst = (levels) => levels.slice().sort((p, q) => rank(q) - rank(p))[0] || "dark";
  const head = (fallback, lede, extra) => h("div", { class: "view-head" }, h("div", {}, h("h1", {}, Nav.title(fallback)), lede ? h("p", {}, lede) : null), h("div", { class: "spacer" }), extra || null, Nav.pageActions());

  /* ------------------------------------------------------------ goals */
  function goals(main) {
    main.append(head("Goals", "Each goal from the Goals table: its state, what holds it, and the epics that deliver it."));
    const sc = h("div", { class: "scroll pages" });
    main.append(sc);
    if (!D.goals.length) { sc.append(emptyState("No goals recorded yet.", "The goals page has no Goals table (ID | Goal | Measure | State).")); return; }
    const grid = h("div", { class: "goal-grid" });
    for (const g of D.goals) {
      const held = (D.blockedBy[g.id] || []).filter((u) => isOpen(UNKNOWN[u]));
      const above = D.above.filter((a) => a.holds === g.id).map((a) => a.unknown);
      const qs = [...new Set([...held, ...above])], lv = worst(qs.map(unknownLevel));
      const epics = D.trace.epics.filter((x) => x.delivers.includes(g.id));
      grid.append(h("article", { class: "goal-card" + (lv !== "dark" ? " lit " + lv : "") },
        h("div", { class: "gc-top" }, h("span", { class: "gc-id" }, g.id), statePill(g.state), qs.length ? levelPill(lv, plural(qs.length, "open question")) : h("span", { class: "muted small" }, "nothing holds it")),
        h("div", { class: "gc-goal", html: g.goal }), h("div", { class: "gc-measure" }, h("span", { class: "muted" }, "Measure "), h("span", { html: g.measure })),
        qs.length ? h("div", { class: "gc-row" }, qs.map((u) => refChip(u))) : null,
        h("div", { class: "gc-row" }, h("span", { class: "muted small" }, epics.length ? "Delivered by " : "No epic delivers it"), epics.map((x) => refChip(x.key)))));
    }
    sc.append(grid);
  }

  /* ------------------------------------------------------------ concerns: concern by app */
  const CELL_WORD = (s) => s || "no state";
  function concerns(main) {
    main.append(head("Concerns", "Every concern cell, concern by app, as the concern pages record it. Blue is never examined: dark has to be earned."));
    const sc = h("div", { class: "scroll pages" });
    main.append(sc);
    const conc = (D.sections.find((x) => x.id === "concerns") || { children: [] }).children;
    const apps = [...new Set(D.cells.map((c) => c.app))].filter((k) => APPS[k]).sort((a, b) => (NODE[a] && NODE[b] ? (NODE[a].col - NODE[b].col) || (NODE[a].row - NODE[b].row) : 0) || cmp(a, b));
    if (!conc.length || !apps.length) { sc.append(emptyState("No concern cells recorded yet.", "No concern page has a cell table of apps.", "/planner:boundary")); return; }
    const table = h("table", { class: "cmx" }, h("tr", {}, h("th", { class: "corner" }, "concern ↓  app →"), apps.map((k) => h("th", { class: "col" }, h("a", { "data-ref": k }, h("span", {}, titleOf(k)))))));
    for (const ck of conc) {
      const row = h("tr", { "data-concern": ck }, h("th", { class: "row" }, h("a", { "data-ref": ck }, titleOf(ck))));
      for (const a of apps) {
        const cell = D.cells.find((c) => c.concern === ck && c.app === a);
        if (!cell) { row.append(h("td", { class: "none" })); continue; }
        const unexamined = cell.state === "unexamined";
        row.append(h("td", {}, h("button", { class: "cmx-cell" + (unexamined ? " unexamined" : "") + (cell.state ? " s-" + cell.state.replace(/[^a-z-]/g, "") : ""), title: `${titleOf(ck)} × ${titleOf(a)}: ${CELL_WORD(cell.state)}${cell.text ? ". " + cell.text : ""}`,
          onclick: () => go(ck, { reset: false }) }, CELL_WORD(cell.state))));
      }
      table.append(row);
    }
    const counts = {};
    D.cells.forEach((c) => { counts[c.state || "no state"] = (counts[c.state || "no state"] || 0) + 1; });
    sc.append(h("section", { class: "card" }, h("div", { class: "grid-wrap" }, table),
      h("p", { class: "p-note" }, Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${n} ${k}`).join(" · "))));
  }

  /* ------------------------------------------------------------ epics */
  const ep = { open: new Set() };
  function epics(main) {
    main.append(head("Epics", "Each epic with its acceptance criteria and concern markers, the apps it touches and what it delivers. Criteria are read as trace.ac_markers reads them."));
    const sc = h("div", { class: "scroll pages" });
    main.append(sc);
    if (!D.trace.epics.length) { sc.append(emptyState("No epics yet.", "There are no epic pages to show.", "/planner:epics")); return; }
    const grid = h("div", { class: "epic-grid" });
    for (const x of D.trace.epics) {
      const e = E[x.key], ac = D.epicCriteria[x.key] || [], open = ep.open.has(x.key) || App.focus === x.key || D.trace.epics.length <= 4;
      const markers = [...new Set(ac.flatMap((c) => c.markers))];
      grid.append(h("article", { class: "epic-card" + (App.focus === x.key ? " on" : ""), "data-key": x.key },
        h("button", { class: "ec-head", onclick: () => { ep.open.has(x.key) ? ep.open.delete(x.key) : ep.open.add(x.key); go(x.key, { reset: true }); rerender(); } },
          h("span", { class: "p-id" }, e.id), h("b", {}, e.title), statePill(e.state), h("span", { class: "ct" }, plural(ac.length, "criterion", "criteria"))),
        h("div", { class: "ec-row" }, x.apps.map((id) => APP_BY_ID[id] ? refChip(APP_BY_ID[id].key) : h("span", { class: "ref-chip" }, id)), markers.map((m) => h("span", { class: "marker" }, m))),
        linkChips(x.key, { small: true }),
        open ? h("ol", { class: "ac-list" }, ac.map((c) => h("li", { class: c.struck ? "struck" : "", value: c.n }, c.heading ? h("b", { class: "ac-head" }, c.heading) : null, h("span", { html: c.html }), c.markers.map((m) => h("span", { class: "marker" }, m)), c.trace ? h("div", { class: "ac-trace", html: c.trace }) : null))) : null,
        open && x.delivers.length ? h("div", { class: "ec-row" }, h("span", { class: "muted small" }, "Delivers "), x.delivers.map((id) => refChip(keyForId(id)))) : null));
    }
    sc.append(grid);
  }

  /* ------------------------------------------------------------ context and scope: today beside after */
  function context(main) {
    main.append(head("Context and scope", "The system today beside the system after, worked out by planner.releases. The page itself, with the outside parties, sits beside."));
    const S = Releases.STATES, last = S.length - 1;
    const two = h("div", { class: "ctx-two" });
    const pane = (i, label) => { const box = h("div", { class: "rel-pane" }); two.append(h("div", { class: "ctx-pane" }, h("h3", {}, label), box)); return box; };
    const a = pane(0, `Today, ${day(D.today)}`), b = pane(last, last === 0 ? "No end state recorded" : S[last].fromChange ? "After: the end state, from each app's change" : `After ${S[last].heading || S[last].name}`);
    main.append(two);
    Releases.drawMap(a, 0, { max: 0.8 });
    if (last > 0) Releases.drawMap(b, last, { max: 0.8 });
    const parties = D.map.parties;
    main.append(h("div", { class: "ctx-parties" }, h("span", { class: "muted" }, `${plural(parties.length, "outside party", "outside parties")}: `), parties.map((p) => refChip(p.key, p.hasContract ? null : h("span", { class: "rid" }, "no contract")))));
  }

  /* ------------------------------------------------------------ a page read full width */
  const doc = { page: "" };
  function readWide(main) {
    const pk = doc.page || Nav.sectionPage();
    const e = E[pk];
    if (!e) { main.append(head("Page", ""), emptyState(Nav.missingPage())); return; }
    main.append(h("div", { class: "view-head" }, h("div", {}, h("div", { class: "kicker" }, Nav.title("Page")), h("h1", {}, e.title)), h("div", { class: "spacer" }), Nav.pageActions({ reading: true })));
    const sc = h("div", { class: "scroll doc-scroll" });
    const body = Reader.body(pk, { wide: true });
    sc.append(body);
    if (App.section === "strategy") sc.append(capabilityChanges());
    main.append(sc);
    const anchor = doc.anchor;
    doc.anchor = "";
    if (anchor) requestAnimationFrame(() => Reader.scrollTo(body, anchor));
  }
  /* Strategy's visual: the capabilities this initiative changes, by their change, as the capability delta lists them. */
  function capabilityChanges() {
    const by = {};
    for (const c of D.trace.capabilities) { const ch = E[c.key].change || "not set"; (by[ch] = by[ch] || []).push(c.key); }
    return h("aside", { class: "doc-aside" }, h("h3", {}, "What the strategy changes"),
      Object.entries(by).map(([ch, keys]) => h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, ch), h("span", {}, keys.map((k) => refChip(k))))),
      h("p", { class: "p-note" }, "Each capability page's change, the move the strategy makes."));
  }
  return { goals, concerns, epics, context, readWide, doc };
})();
View("goals", { label: "Goals", render: Sections.goals });
View("concerns", { label: "Concerns", render: Sections.concerns });
View("epics", { label: "Epics", render: Sections.epics, highlight: (k) => { if (EPIC[k] && App.view === "epics") rerender(); } });
View("context", { label: "Context", render: Sections.context });
View("doc", { label: "Page", render: Sections.readWide });
