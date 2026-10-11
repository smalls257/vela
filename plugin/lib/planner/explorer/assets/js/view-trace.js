/* Trace: capability, then requirement, each app's share and the contracts that carry it, then the epics that build
   it; or capability to epic when the vault has no functional requirements yet. From trace.epics, trace.report,
   allocation.requirements and allocation.rows. Cards collapse past eight; a filter shows only those with a gap. */
const TraceView = (() => {
  const st = { open: null, gaps: false, expanded: new Set() };
  function render(main) {
    const T = D.trace, hasFR = T.requirements.length > 0, sc = h("div", { class: "scroll pages" });
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Requirement trace"),
      h("p", {}, hasFR ? "Each capability, its functional requirements, each app's share and the contracts that carry it, then the epics that build it." : "Each capability and the epics that deliver it, with the apps and contracts each epic lists.")),
      h("div", { class: "spacer" }),
      h("button", { class: "chip" + (st.open ? " on" : ""), onclick: () => { st.open = !st.open; rerender(); } }, st.open ? "Collapse all" : "Expand all"),
      h("button", { class: "chip" + (st.gaps ? " on" : ""), onclick: () => { st.gaps = !st.gaps; rerender(); } }, "Only those with a gap")), sc);
    if (!hasFR) sc.append(emptyState("No requirement rows yet.", "No capability page has a CAP-nnn.FRn row and no app has a Requirements allocated table, so the trace runs capability → epic → apps and contracts. Once requirements are allocated it runs capability → requirement → app share → contracts → epic.", ["/planner:requirements", "/planner:allocate"], "inline"));
    if (st.open === null) st.open = T.capabilities.length <= 8;
    const gapsT1 = new Set(T.gaps.filter((g) => g.rule === "T1").map((g) => g.subject));
    let hidden = 0;
    for (const c of T.capabilities) {
      const e = E[c.key], epics = T.epics.filter((x) => x.delivers.includes(c.id)), reqs = T.requirements.filter((r) => r.capability === c.id);
      const unallocated = reqs.filter((r) => !T.allocation.some((a) => a.requirement === r.id)).length;
      const hasGap = !epics.length || unallocated > 0 || T.gaps.some((g) => g.subject.startsWith(c.id));
      if (st.gaps && !hasGap) { hidden++; continue; }
      const body = h("div", { class: "cap-body" });
      if (hasFR && reqs.length) {
        body.append(h("div", { class: "tr-col-h" }, h("span"), h("span", {}, "Requirement"), h("span", {}, "App share and contracts"), h("span", {}, "Epics for that app")));
        for (const r of reqs) {
          const rows = T.allocation.filter((a) => a.requirement === r.id);
          body.append(h("div", { class: "tr-row" }, h("span", { class: "arrow" }, "↳"),
            h("div", {}, refChip(r.id), statePill(r.state), h("div", { class: "muted small" }, E[r.id] ? E[r.id].title : "")),
            h("div", {}, rows.length ? rows.map((a) => h("div", { class: "alloc" }, h("div", {}, refChip(a.app), " ", statePill(a.state)), h("div", { class: "muted small" }, a.share), a.through.length ? h("div", {}, h("span", { class: "muted small" }, "through "), a.through.map((x) => refChip(x))) : null)) : h("span", { class: "gap" }, "no app carries it")),
            h("div", {}, rows.length ? [...new Set(rows.flatMap((a) => epics.filter((x) => x.apps.includes(E[a.app].id)).map((x) => x.key)))].map((k) => refChip(k)) : null)));
        }
      }
      if (epics.length) {
        body.append(h("div", { class: "tr-col-h" }, h("span"), h("span", {}, "Epic that delivers it"), h("span", {}, "Apps"), h("span", {}, "Contracts it delivers or consumes")));
        for (const x of epics) body.append(h("div", { class: "tr-row" }, h("span", { class: "arrow" }, "↳"), h("div", {}, refChip(x.key), statePill(E[x.key].state)),
          h("div", {}, x.apps.map((id) => (APP_BY_ID[id] ? refChip(APP_BY_ID[id].key) : id))),
          h("div", {}, x.delivers.filter((id) => CONTRACT[id]).map((id) => refChip(id, h("span", { class: "rid" }, "delivers"))), x.consumes.filter((id) => CONTRACT[id]).map((id) => refChip(id, h("span", { class: "rid" }, "consumes"))))));
      } else body.append(h("div", { class: "gap" }, gapsT1.has(c.id) ? "No epic delivers it, and its change says something should be built (T1)." : `No epic delivers it (its change is ${e.change || "not set"}).`));
      const fl = flowsFor(c.key);
      if (fl.length) body.append(h("div", { class: "small", style: "margin-top:8px" }, h("span", { class: "muted" }, "Flows: "), fl.map((r) => refChip(r.flow))));
      const isOpenCard = st.open || st.expanded.has(c.key);
      sc.append(h("div", { class: "cap-card" + (hasGap ? " has-gap" : "") },
        h("div", { class: "cap-head", onclick: () => { go(c.key, { reset: true }); if (!st.open) { st.expanded.has(c.key) ? st.expanded.delete(c.key) : st.expanded.add(c.key); rerender(); } } },
          h("span", { class: "muted" }, isOpenCard ? "▾" : "▸"), h("span", { class: "p-id" }, c.id), h("b", {}, e.title), e.change ? h("span", { class: "pill" }, e.change) : null, statePill(e.state),
          c.domain ? h("span", { class: "muted small" }, c.domain) : null,
          h("span", { class: "ct" }, [reqs.length ? `${plural(reqs.length, "requirement")}${unallocated ? `, ${unallocated} not allocated` : ""}` : "", plural(epics.length, "epic")].filter(Boolean).join(" · "), hasGap ? h("span", { class: "gap" }, " · gap") : null)),
        isOpenCard ? body : null));
    }
    if (hidden) sc.append(h("div", { class: "note" }, `${plural(hidden, "capability", "capabilities")} with no gap hidden by the filter.`));
    const orphan = T.epics.filter((x) => !x.delivers.some((id) => T.capabilities.some((c) => c.id === id)));
    if (orphan.length) sc.append(h("section", { class: "card" }, h("h2", {}, "Epics that deliver no capability", h("span", { class: "sub" }, "they trace to goals, contracts or decisions instead")),
      h("div", {}, orphan.map((x) => refChip(x.key, h("span", { class: "rid" }, x.delivers.join(", ") || "delivers nothing"))))));
    sc.append(h("section", { class: "card" }, h("h2", {}, "Trace gaps", h("span", { class: "sub" }, `${T.gaps.length} of ${T.checked} checks, from the planner's T rules`)),
      T.gaps.length ? h("table", { class: "t" }, h("tr", {}, h("th", {}, "Rule"), h("th", {}, "About"), h("th", {}, "Gap"), h("th", {}, "Fix")),
        T.gaps.map((g) => h("tr", {}, h("td", {}, g.rule), h("td", {}, g.subject), h("td", {}, g.message), h("td", { class: "muted" }, g.fix)))) : h("div", { class: "note" }, "No gaps: every check the T rules run passes.")));
  }
  return { render, highlight: (key) => { const c = D.trace.capabilities.find((x) => x.key === key); if (c && !st.expanded.has(key)) { st.expanded.add(key); rerender(); } } };
})();
View("trace", { label: "Trace", title: "Capability to requirement to epic", render: TraceView.render, highlight: TraceView.highlight,
  count: () => D.trace.requirements.length ? String(D.trace.requirements.length) : String(D.trace.capabilities.length) });
