/* Front doors, by audience: one screen each, built from the same data as every other view, everything else one
   click away. The lead's door is "What needs you", the cockpit. Where a door chooses what to show by a rule of its
   own (which questions are a "business question", which would "change a test"), the rule is written on the card.
   - Exec: goals and where they stand, what is decided, the top risks, what needs their decision, the timeline.
   - Product: capabilities and requirements, what each release delivers, the business questions, the user flows.
   - QA: acceptance criteria by epic, contracts and who tests each side, failure behaviour per app, and unsettled
     questions that would change a test.
   - Engineering: pick an app for its slice: boundary, contracts in and out, flows, open questions, handoff state.
   - Managers: progress, completeness, the timeline, and what is blocked on whom. */
const Roles = (() => {
  const ROLES = [["lead", "Lead", "What needs you"], ["exec", "Exec", "Goals, decisions, risks and the timeline"], ["product", "Product", "Capabilities, requirements, releases and flows"],
    ["qa", "QA", "Criteria, contracts, failure and what would change a test"], ["eng", "Engineering", "One app's slice"], ["mgr", "Managers", "Progress, timeline and who is blocking what"]];
  const st = { role: HASH.get("role") || "exec", app: HASH.get("app") || "" };
  const lamp = (lv) => (lv && lv !== "dark" ? lampEl(lv) : null);  // a settled thing needs no lamp in a short list
  const worst = (levels) => levels.slice().sort((p, q) => rank(q) - rank(p))[0] || "dark";
  const openQs = () => D.asks.filter((u) => u.state === "open");
  const kindOf = (k) => { const e = ent(k); return e ? e.kind : /^G\d+$/.test(k) ? "goal" : ""; };
  function card(title, more, ...kids) {
    return h("section", { class: "door-card" }, h("header", {}, h("h2", {}, title), more ? h("button", { class: "linkish", onclick: more[1] }, more[0] + " →") : null), ...kids.flat().filter(Boolean));
  }
  const rule = (text) => h("p", { class: "rule heuristic" }, text);
  const empty = (text) => h("div", { class: "p-empty-line" }, text);
  const missing = (what, detail, writer) => emptyState(what, detail, writer, "small");
  function list(items, max, row) {
    const shown = items.slice(0, max);
    return h("ul", { class: "door-list" }, shown.map(row), items.length > max ? h("li", { class: "more muted" }, `and ${items.length - max} more`) : null);
  }
  function switcher() {
    return h("div", { class: "door-switch", role: "tablist", "aria-label": "Who is reading" }, ROLES.map(([id, label, say]) =>
      h("button", { role: "tab", "aria-selected": String(id === st.role), title: say, onclick: () => Nav.role(id) }, label)));
  }

  /* ------------------------------------------------------------ shared pieces */
  function timeline() {
    const S = Releases.STATES;
    return h("ol", { class: "mini-time" }, S.map((x, j) => h("li", {}, h("button", { onclick: () => Nav.openRelease(j) },
      h("b", {}, j === 0 ? "Today" : x.fromChange ? "End" : `R${j}`), h("span", {}, j === 0 ? day(D.today) : x.target ? day(x.target) : "from change"),
      j > 0 ? h("small", {}, x.fromChange ? "every app's change" : `${plural((x.rows || []).length, "item")}, ${x.state || "no state"}`) : h("small", {}, "before the initiative")))),
      !D.releases.count ? h("li", { class: "none" }, missing("No releases recorded yet.", "They go in 04b-releases.md, so this runs from today to the end state.")) : null);
  }
  function qRow(u) {
    const a = ASK[u.id];
    return h("li", {}, lamp(a.light.level), h("a", { "data-ref": u.id }, h("b", {}, u.id), " ", shorten(E[u.id] ? E[u.id].title : "", 54)),
      h("span", { class: "muted small" }, ` ask ${a.ask.name}${a.ask.inferred ? " (guess)" : ""}, ${relDue(u.askBy)}`));
  }
  const holdsKinds = (u, kinds) => [...new Set([...u.blocks, ...u.holds])].some((k) => kinds.includes(kindOf(k)));

  /* ------------------------------------------------------------ exec */
  function exec(grid) {
    grid.append(card("Goals and where they stand", ["Goals", () => Nav.open("goals")], D.goals.length ? list(D.goals, 5, (g) => {
      const qs = [...new Set([...(D.blockedBy[g.id] || []).filter((u) => isOpen(UNKNOWN[u])), ...D.above.filter((a) => a.holds === g.id).map((a) => a.unknown)])];
      const lv = worst(qs.map(unknownLevel));
      return h("li", {}, lamp(lv), h("span", {}, h("b", {}, g.id + " "), h("span", { html: g.goal })), " ", statePill(g.state), qs.length ? h("span", { class: "muted small" }, ` held by ${qs.join(", ")}`) : null);
    }) : empty("No Goals table yet.")));
    const dec = Object.values(E).filter((e) => e.kind === "decision");
    const decided = dec.filter((e) => e.state === "decided"), proposed = dec.filter((e) => e.state === "proposed");
    grid.append(card("What is decided", ["Decisions", () => Nav.open("decisions")],
      h("div", { class: "kpi-row" }, h("div", {}, h("b", {}, decided.length), h("span", {}, "decisions recorded")), h("div", {}, h("b", {}, proposed.length), h("span", {}, "proposed")),
        h("div", {}, h("b", {}, D.progress.percent + "%"), h("span", {}, "complete, by planner's five measures"))),
      list(decided, 4, (e) => h("li", {}, h("a", { "data-ref": e.key }, h("b", {}, e.id), " ", shorten(e.title, 60))))));
    const risks = D.riskList;
    grid.append(card("Top risks", ["Unknowns and risks", () => Nav.open("unknowns")], risks.length ? list(risks, 4, (r) => {
      const f = r.facts, sev = f.Impact || f.Severity || f.Likelihood || "";
      return h("li", {}, h("a", { "data-ref": r.id }, h("b", {}, r.id), " ", r.title), sev ? h("span", { class: "pill" }, sev) : null,
        f.Mitigation ? h("div", { class: "muted small" }, shorten(f.Mitigation, 120)) : null);
    }) : empty("No risk (R-nn) is recorded."), risks.length ? rule("In the order the risks page lists them; the page records no ranking the explorer could use.") : null));
    const above = D.above.map((a) => ({ u: UNKNOWN[a.unknown], holds: a.title })).filter((x) => x.u);
    const owed = [...above.map((x) => ({ kind: "question", key: x.u.id, say: `holds ${x.holds}` })),
      ...proposed.map((e) => ({ kind: "decision", key: e.key, say: "proposed, not decided" })),
      ...D.progress.awaiting.map((a) => ({ kind: "override", key: a.key, say: `decided on behalf of ${a.owners.join(", ")}, not yet confirmed` })),
      ...Releases.STATES.slice(1).filter((x) => !x.fromChange && x.state !== "decided").map((x) => ({ kind: "release", key: null, name: x.heading || x.name, say: `release at ${x.state || "no state"}` }))];
    grid.append(card("What needs your decision", null, owed.length ? list(owed, 5, (x) => h("li", {}, x.key ? lampEl(levelForKey(x.key) || "caution") : lampEl("caution"),
      x.key ? refChip(x.key) : h("b", {}, x.name), h("span", { class: "muted small" }, " " + x.say))) : empty("Nothing waits on an executive decision by this rule."),
      rule("Rule: open questions that hold a goal, the strategy or another question (held above the map), decisions still proposed, overrides awaiting their owner, and releases not yet decided.")));
    grid.append(card("Release timeline", ["Releases", () => Nav.open("releases")], timeline()));
  }

  /* ------------------------------------------------------------ product */
  function product(grid) {
    const T = D.trace;
    grid.append(card("Capabilities and requirements", ["Capabilities", () => Nav.open("capabilities")], T.capabilities.length ? list(T.capabilities, 6, (c) => {
      const reqs = T.requirements.filter((r) => r.capability === c.id), alloc = reqs.filter((r) => T.allocation.some((a) => a.requirement === r.id && a.state !== "inkling"));
      return h("li", {}, h("a", { "data-ref": c.key }, h("b", {}, c.id), " ", E[c.key].title), " ", E[c.key].change ? h("span", { class: "pill" }, E[c.key].change) : null,
        h("span", { class: "muted small" }, reqs.length ? ` ${plural(reqs.length, "requirement")}, ${alloc.length} allocated` : " no requirements written"));
    }) : missing("No capability pages yet.", "", "/planner:boundary"), T.capabilities.length && !T.requirements.length ? missing("No requirement rows yet.", "No capability page has a CAP-nnn.FRn row, so none is counted as allocated.", ["/planner:requirements", "/planner:allocate"]) : null));
    grid.append(card("What each release delivers", ["Releases", () => Nav.open("releases")], D.releases.count ? list(Releases.STATES.slice(1), 4, (x) => h("li", {},
      h("b", {}, `R${Releases.STATES.indexOf(x)} `), shorten((x.heading || x.name).replace(/^[^:]*:\s*/, ""), 40), h("span", { class: "muted small" }, x.target ? ` · ${day(x.target)}` : ""),
      h("div", { class: "chips" }, (x.rows || []).map((r) => refChip(r.requirement, r.criteria.length ? h("span", { class: "rid" }, r.criteria.map((n) => "AC" + n).join(",")) : null)))))
      : missing("No releases recorded yet.", "They go in 04b-releases.md, and each release lists the requirements it delivers.", ["/planner:requirements", "/planner:allocate"])));
    const biz = openQs().filter((u) => holdsKinds(UNKNOWN[u.id], ["goal", "capability", "requirement", "flow"]) || D.above.some((a) => a.unknown === u.id));
    grid.append(card("Business questions", ["Who to ask", () => Nav.open("unknowns")], biz.length ? list(biz.sort((a, b) => cmp(a.askBy || "9", b.askBy || "9")), 5, (u) => qRow(UNKNOWN[u.id])) : empty("No open question holds a goal, capability, requirement or flow."),
      rule("Rule: open questions whose Blocks line reaches a goal, capability, requirement or flow, or that hold something above the map.")));
    grid.append(card("User flows", ["Flows", () => Nav.open("flows")], D.flows.length ? list(D.flows, 5, (f) => h("li", {}, lamp(levelOf(f.key)), h("a", { "data-ref": f.key, "data-reveal": "" }, h("b", {}, E[f.key].id), " ", E[f.key].title),
      h("span", { class: "muted small" }, ` ${plural(f.steps.length, "step")}`), h("button", { class: "btn tiny", onclick: () => Flows.present(f.key, 0) }, "▶ Present"))) : missing("No flows yet.", "", "/planner:boundary")));
  }

  /* ------------------------------------------------------------ QA */
  function qa(grid) {
    const epics = D.trace.epics;
    grid.append(card("Acceptance criteria by epic", ["Epics", () => Nav.open("epics")], epics.length ? list(epics, 6, (x) => {
      const ac = D.epicCriteria[x.key] || [], markers = [...new Set(ac.flatMap((c) => c.markers))];
      return h("li", {}, h("a", { "data-ref": x.key }, h("b", {}, E[x.key].id), " ", shorten(E[x.key].title, 44)), h("span", { class: "muted small" }, ` ${plural(ac.length, "criterion", "criteria")} `), markers.map((m) => h("span", { class: "marker" }, m)),
        linkChips(x.key, { small: true }));
    }) : missing("No epics yet.", "Acceptance criteria live on epic pages.", "/planner:epics")));
    grid.append(card("Contracts and who tests each side", ["Apps", () => Nav.open("apps")], D.map.contracts.length ? list(D.map.contracts, 4, (c) => {
      const t = D.testedBy[c.id];
      return h("li", {}, lamp(levelOf(c.id)), h("a", { "data-ref": c.id }, h("b", {}, c.id), " ", c.title), h("span", { class: "muted small" }, ` ${titleOf(c.provider)} → ${c.consumers.map(titleOf).join(", ")}`),
        h("div", { class: t ? "small muted" : "small gap" }, t ? shorten(t, 96) : "No Tested by line."), linkChips(c.id, { small: true }));
    }) : empty("No contracts.")));
    grid.append(card("Failure behaviour per app", null, D.map.apps.length ? list(D.map.apps, 6, (a) => {
      const f = D.failure[a.key];
      return h("li", {}, h("a", { "data-ref": a.key }, h("b", {}, a.title)), " ", f.sections.length ? h("span", { class: "muted small" }, f.sections.map((x) => x.heading).join("; ")) : h("span", { class: "gap small" }, f.runtime ? "runtime page has no failure section" : "no runtime page"));
    }) : empty("No apps."), rule("A runtime page section whose heading ladder.FAILURE accepts (fail, down, slow, outage).")));
    const testy = openQs().filter((u) => holdsKinds(UNKNOWN[u.id], ["contract", "epic", "requirement", "flow"]));
    grid.append(card("Unsettled things that would change a test", ["Who to ask", () => Nav.open("unknowns")], testy.length ? list(testy, 5, (u) => qRow(UNKNOWN[u.id])) : empty("No open question holds a contract, epic, requirement or flow."),
      rule("Rule: open questions whose Blocks line reaches a contract, epic, requirement or flow, the things a test is written against.")));
  }

  /* ------------------------------------------------------------ engineering: one app's slice */
  function eng(grid, root) {
    const apps = D.map.apps;
    if (!st.app || !APPS[st.app]) st.app = (apps.find((a) => a.stage) || apps[0] || {}).key || "";
    root.insertBefore(h("div", { class: "door-pick" }, h("span", { class: "muted" }, "App "), apps.map((a) => h("button", { class: "chip" + (a.key === st.app ? " on" : ""), onclick: () => { st.app = a.key; Nav.syncHash(); rerender(); } }, lampEl(levelOf(a.key)), a.title))), grid);
    if (!st.app) { grid.append(empty("This vault has no apps.")); return; }
    const k = st.app, a = D.apps[k], e = E[k], row = D.progress.rows.find((r) => r.app === k), ho = row ? row.handoff : null;
    grid.append(card("Boundary", ["Open the page", () => go(Reader.keyFor(k), {})], h("div", { class: "prose-text door-prose", html: e.prose || "<p>The page has no opening prose.</p>" }),
      h("div", { class: "chips" }, h("span", { class: "pill" }, e.change || "no change"), e.stage ? h("span", { class: "pill" }, "stage " + e.stage) : null, h("span", { class: "pill" }, D.domains[k])),
      linkChips(k), Inside.doorEntry(k)));
    // a contract from an outside party carries the party's own links too: its API spec is where the engineer starts
    const con = (id, dir) => h("li", {}, lamp(levelOf(id)), h("a", { "data-ref": id }, h("b", {}, id), " ", CONTRACT[id].title), " ", statePill(CONTRACT[id].state),
      h("span", { class: "muted small" }, dir === "out" ? ` to ${CONTRACT[id].consumers.map(titleOf).join(", ")}` : ` from ${titleOf(CONTRACT[id].provider)}`),
      linkChips(id, { small: true }), dir === "in" && CONTRACT[id].providerKind === "party" ? linkChips(CONTRACT[id].provider, { small: true }) : null);
    grid.append(card("Contracts in and out", ["Focus on the map", () => Nav.focusApp(k)], h("h3", {}, "Provides"), a.provides.length ? list(a.provides, 4, (id) => con(id, "out")) : empty("Provides none."),
      h("h3", {}, "Consumes"), a.consumes.length ? list(a.consumes, 4, (id) => con(id, "in")) : empty("Consumes none.")));
    const flows = flowsFor(k);
    grid.append(card("Flows and open questions", null, flows.length ? list(flows, 3, (r) => h("li", {}, h("a", { "data-ref": r.flow, "data-reveal": "" }, h("b", {}, E[r.flow].id), " ", E[r.flow].title),
      h("button", { class: "btn tiny", onclick: () => Flows.present(r.flow, firstStepTouching(FLOW[r.flow], k)) }, "▶ Present"))) : empty("No flow crosses it."),
      h("h3", {}, "Open questions holding it"), a.questions.length ? list(a.questions.map((q) => UNKNOWN[q.id]).filter(Boolean), 4, qRow) : empty("None.")));
    const slice = D.slices[k] || [];
    grid.append(card("Handoff", null, h("div", { class: "small" }, ho && (ho.manifest || ho.handedOff) ? [ho.handedOff ? h("div", {}, "Handed off: ", ho.handedOff) : null,
      ho.manifest ? h("div", { class: ho.changed + ho.removed ? "gap" : "muted" }, ho.problem ? "Manifest unreadable: " + ho.problem : ho.changed + ho.removed ? `${ho.changed} changed and ${ho.removed} removed since the senior accepted it` : "Nothing the senior accepted has changed.") : h("div", { class: "muted" }, "No manifest in handoffs/.")] : h("div", { class: "muted" }, "Not handed off.")),
      h("h3", {}, `The slice, ${plural(slice.length, "item")}`),
      h("ul", { class: "door-list" }, [...new Set(slice.map((x) => x.kind))].map((kind) => { const of = slice.filter((x) => x.kind === kind); return h("li", {}, h("span", { class: "muted small slice-k" }, kind + " "), of.slice(0, 6).map((x) => h("a", { class: "slice-id", "data-ref": keyForId(x.id), title: titleOf(keyForId(x.id)) }, x.id)), of.length > 6 ? h("span", { class: "muted small" }, ` +${of.length - 6}`) : null); })),
      rule("The slice is handoff.slice_of: what a handoff manifest records for this app.")));
  }

  /* ------------------------------------------------------------ managers */
  function mgr(grid) {
    const P = D.progress, stages = P.stages;
    grid.append(card("Progress", ["Progress", () => { Nav.open("apps"); showView("progress"); }],
      h("div", { class: "kpi-row" }, h("div", {}, h("b", {}, P.percent + "%"), h("span", {}, "complete")), h("div", {}, h("b", {}, P.rows.filter((r) => r.stage).length), h("span", {}, "apps on the ladder")),
        h("div", {}, h("b", {}, openQs().length), h("span", {}, "open questions"))),
      h("div", { class: "shares" }, P.shares.map((x) => h("div", { class: "share" }, h("span", {}, x.name), h("div", { class: "bar" }, h("span", { style: `width:${x.total ? ((100 * x.done) / x.total).toFixed(1) : 100}%` })), h("span", { class: "v" }, `${x.done} of ${x.total}`))))));
    grid.append(card("Where each app stands", ["Apps", () => Nav.open("apps")], list(P.rows.filter((r) => r.stage), 7, (r) => h("li", {}, lamp(levelOf(r.app)), h("a", { "data-ref": r.app }, E[r.app].title),
      h("span", { class: "ladder inline" }, stages.map((x, i) => h("span", { class: i < stages.indexOf(r.stage) ? "done" : i === stages.indexOf(r.stage) ? "cur" : "", title: x }))), h("span", { class: "muted small" }, ` ${r.stage}`)))));
    grid.append(card("Release timeline", ["Releases", () => Nav.open("releases")], timeline()));
    const who = {};
    for (const u of openQs()) {
      const k = u.ask.key || u.ask.name, w = who[k] || (who[k] = { key: k, name: u.ask.name, n: 0, late: 0, holds: new Set(), guessed: 0 });
      w.n++; if (isDate(u.askBy) && dayNum(u.askBy) < TODAY) w.late++; if (u.ask.inferred) w.guessed++;
      (UNKNOWN[u.id] ? UNKNOWN[u.id].holds : []).forEach((x) => w.holds.add(x));
    }
    const ranked = Object.values(who).sort((a, b) => b.late - a.late || b.n - a.n || cmp(a.name, b.name));
    grid.append(card("What is blocked on whom", ["Who to ask", () => Nav.open("unknowns")], ranked.length ? list(ranked, 6, (w) => h("li", {}, lamp(w.late ? "warning" : "caution"),
      h("button", { class: "linkish strong", onclick: () => { Nav.open("unknowns"); Asks.meet(w.key); } }, w.name), h("span", { class: "muted small" }, ` ${plural(w.n, "open question")}${w.late ? `, ${w.late} overdue` : ""}, holding ${plural(w.holds.size, "thing")}${w.guessed ? `; ${w.guessed} guessed from the Owner line` : ""}`)))
      : empty("No open questions.")));
  }

  function render(main) {
    const def = ROLES.find(([id]) => id === st.role) || ROLES[1];
    const root = h("div", { class: "door", "data-role": def[0] });
    root.append(h("div", { class: "door-head" }, h("div", {}, h("div", { class: "kicker" }, "Front door"), h("h1", {}, def[0] === "eng" ? "Engineering: one app's slice" : `${def[1]}: ${def[2].toLowerCase()}`)), switcher()));
    const grid = h("div", { class: "door-grid door-" + def[0] });
    root.append(grid);
    main.append(root);
    ({ exec, product, qa, eng, mgr })[def[0]](grid, root);
  }
  return { render, st, ROLES };
})();
View("role", { label: "Front door", render: Roles.render });
