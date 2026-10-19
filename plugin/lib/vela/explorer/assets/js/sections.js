/* The visuals of the sections that had no view of their own, each beside its page:
   - Goals: each goal row with its state, the open questions that hold it and the epics that deliver it.
   - Concerns: the concern cells, concern by app, as the concern pages' tables record them.
   - Epics: each epic with its acceptance criteria, concern markers, apps and what it delivers.
   - Context and scope: the system today beside the system after (releases.js's drawing).
   - A page read full width, with its contents list: Constraints, Strategy and Glossary are mostly words, so their
     page fills the main area; any other section's page reads this way from "Read the page". */
const Sections = (() => {
  const worst = (levels) => levels.slice().sort((p, q) => rank(q) - rank(p))[0] || "dark";
  const head = (fallback, lede, extra) => h("div", { class: "view-head" }, h("div", {}, h("h1", {}, Nav.title(fallback)), lede ? h("p", {}, lede, Nav.ledeLink()) : null), h("div", { class: "spacer" }), extra || null, Nav.pageActions());

  /* ------------------------------------------------------------ goals */
  function goals(main) {
    const blocked = D.goals.filter((g) => (D.blockedBy[g.id] || []).some((u) => isOpen(UNKNOWN[u])) || D.above.some((a) => a.holds === g.id)).length;
    main.append(head("Goals", D.goals.length ? `${plural(D.goals.length, "goal")}; ${blocked ? `${blocked} still blocked. Start with the lit ones.` : "nothing is blocking any of them."}` : ""));
    const sc = h("div", { class: "scroll pages" });
    main.append(sc);
    if (!D.goals.length) { sc.append(emptyState("No goals yet.", "The plan's lead writes them in the first planning session.")); return; }
    const grid = h("div", { class: "goal-grid" });
    for (const g of D.goals) {
      const held = (D.blockedBy[g.id] || []).filter((u) => isOpen(UNKNOWN[u]));
      const above = D.above.filter((a) => a.holds === g.id).map((a) => a.unknown);
      const qs = [...new Set([...held, ...above])], lv = worst(qs.map(unknownLevel));
      const epics = D.trace.epics.filter((x) => x.delivers.includes(g.id));
      grid.append(h("article", { class: "goal-card" + (lv !== "dark" ? " lit " + lv : "") },
        h("div", { class: "gc-top" }, h("span", { class: "gc-id id-tag" }, g.id), statePill(g.state), qs.length ? levelPill(lv, plural(qs.length, "open question")) : h("span", { class: "muted small" }, "nothing blocking it")),
        h("div", { class: "gc-goal", html: g.goal }), h("div", { class: "gc-measure" }, h("span", { class: "muted" }, "Measure "), h("span", { html: g.measure })),
        qs.length ? h("div", { class: "gc-row" }, qs.map((u) => refChip(u))) : null,
        h("div", { class: "gc-row" }, h("span", { class: "muted small" }, epics.length ? "Delivered by " : "No epic delivers it yet"), epics.map((x) => refChip(x.key)))));
    }
    sc.append(grid);
  }

  /* ------------------------------------------------------------ concerns: concern by app */
  /* A concern cell's state in words: "unexamined" means nobody has looked; "unknown" means someone looked and could not say. */
  const CELL_WORD = (s) => (!s ? "not recorded" : CELL_WORD_OF[s] ? cellWord(s) : stateWord(s));  // plainwords' cell words, else a state word
  const CELL_WORD_OF = D.words.cell;
  function concerns(main) {
    const unreviewed = D.cells.filter((c) => String(c.state || "").startsWith("unexamined")).length;
    main.append(head("Concerns", unreviewed ? `Nobody has reviewed ${unreviewed} of these yet; they're blue. Pick one to see who should.` : "Every concern has been reviewed for every app."));
    const sc = h("div", { class: "scroll pages" });
    main.append(sc);
    const conc = (D.sections.find((x) => x.id === "concerns") || { children: [] }).children;
    const apps = [...new Set(D.cells.map((c) => c.app))].filter((k) => APPS[k]).sort((a, b) => (NODE[a] && NODE[b] ? (NODE[a].col - NODE[b].col) || (NODE[a].row - NODE[b].row) : 0) || cmp(a, b));
    if (!conc.length || !apps.length) { sc.append(emptyState("No concerns recorded yet.", "No concerns have been recorded for any app yet.", "/vela:boundary")); return; }
    const table = h("table", { class: "cmx" }, h("tr", {}, h("th", { class: "corner" }, "concerns down, apps across"), apps.map((k) => h("th", { class: "col" }, h("a", { "data-ref": k }, h("span", {}, titleOf(k)))))));
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
    D.cells.forEach((c) => { const w = CELL_WORD(c.state); counts[w] = (counts[w] || 0) + 1; });
    sc.append(h("section", { class: "card" }, h("div", { class: "grid-wrap" }, table),
      h("p", { class: "p-note" }, Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${n} ${k}`).join(" · "))));
  }

  /* ------------------------------------------------------------ epics */
  const ep = { open: new Set() };
  function epics(main) {
    main.append(head("Epics", D.trace.epics.length ? `${plural(D.trace.epics.length, "epic")}. Open one to see what it delivers and how it's tested.` : ""));
    const sc = h("div", { class: "scroll pages" });
    main.append(sc);
    if (!D.trace.epics.length) { sc.append(emptyState("No epics yet.", "The plan's lead writes them in the epics session.", "/vela:epics")); return; }
    const grid = h("div", { class: "epic-grid" });
    for (const x of D.trace.epics) {
      const e = E[x.key], ac = D.epicCriteria[x.key] || [], open = ep.open.has(x.key) || App.focus === x.key || D.trace.epics.length <= 4;
      const markers = [...new Set(ac.flatMap((c) => c.markers))];
      grid.append(h("article", { class: "epic-card" + (App.focus === x.key ? " on" : ""), "data-key": x.key },
        h("button", { class: "ec-head", onclick: () => { ep.open.has(x.key) ? ep.open.delete(x.key) : ep.open.add(x.key); go(x.key, { reset: true }); rerender(); } },
          h("b", {}, e.title, idTag(e.id)), statePill(e.state), h("span", { class: "ct" }, plural(ac.length, "criterion", "criteria"))),
        h("div", { class: "ec-row" }, x.apps.map((id) => APP_BY_ID[id] ? refChip(APP_BY_ID[id].key) : h("span", { class: "ref-chip" }, id)), markers.map((m) => h("span", { class: "marker" }, m))),
        linkChips(x.key, { small: true }),
        open ? h("ol", { class: "ac-list" }, ac.map((c) => h("li", { class: c.struck ? "struck" : "", value: c.n }, c.heading ? h("b", { class: "ac-head" }, c.heading) : null, h("span", { html: c.html }), c.markers.map((m) => h("span", { class: "marker" }, m)), c.trace ? h("div", { class: "ac-trace", html: c.trace }) : null))) : null,
        open && x.delivers.length ? h("div", { class: "ec-row" }, h("span", { class: "muted small" }, "Delivers "), x.delivers.map((id) => refChip(keyForId(id)))) : null));
    }
    sc.append(grid);
  }

  /* ------------------------------------------------------------ context and scope: today beside after */
  function context(main) {
    main.append(head("Context and scope", "Today's system on the left, the system after the releases on the right."));
    const S = Releases.STATES, last = S.length - 1;
    const two = h("div", { class: "ctx-two" });
    const pane = (i, label) => { const box = h("div", { class: "rel-pane" }); two.append(h("div", { class: "ctx-pane" }, h("h3", {}, label), box)); return box; };
    const a = pane(0, `Today, ${day(D.today)}`), b = pane(last, last === 0 ? "Nothing says yet what it looks like after" : S[last].fromChange ? "After the releases" : `After ${S[last].heading || S[last].name}`);
    main.append(two);
    Releases.drawMap(a, 0, { max: 0.8 });
    if (last > 0) Releases.drawMap(b, last, { max: 0.8 });
    const parties = D.map.parties;
    main.append(h("div", { class: "ctx-parties" }, h("span", { class: "muted" }, `${plural(parties.length, "outside service")}: `), parties.map((p) => refChip(p.key, p.hasContract ? null : h("span", { class: "rid" }, "not connected")))));
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
      Object.entries(by).map(([ch, keys]) => h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, ch), h("span", {}, keys.map((k) => refChip(k))))));
  }
  return { goals, concerns, epics, context, readWide, doc };
})();
View("goals", { label: "Goals", render: Sections.goals });
View("concerns", { label: "Concerns", render: Sections.concerns });
View("epics", { label: "Epics", render: Sections.epics, highlight: (k) => { if (EPIC[k] && App.view === "epics") rerender(); } });
View("context", { label: "Context", render: Sections.context });
View("doc", { label: "Page", render: Sections.readWide });
