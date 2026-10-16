/* Front doors, by audience: one screen each, built from the same data as every other view, everything else one
   click away. The lead's door is "What needs you", the cockpit. Where a door chooses what to show by a rule of its
   own (which questions are a "business question", which would "change a test"), the rule is written on the card.
   - Exec: goals and where they stand, what is decided, the top risks, what needs their decision, the timeline.
   - Product: capabilities and requirements, what each release delivers, the business questions, the user flows.
   - QA: acceptance criteria by epic, contracts and who tests each side, failure behavior per app, and unsettled
     questions that would change a test.
   - Engineering: pick an app for its handoff list: boundary, contracts in and out, flows, open questions, handoff state, and
     how far every app is from a build plan (no design, design only, plan with gaps, plan complete).
   - Managers: progress, completeness, the timeline, what is blocked on whom, and the build plans' stories and points. */
const Roles = (() => {
  const ROLES = [["lead", "Lead", "What needs you"], ["exec", "Exec", "Goals, decisions, risks and the timeline"], ["product", "Product", "Capabilities, requirements, releases and flows"],
    ["qa", "QA", "Criteria, contracts, failure and what would change a test"], ["eng", "Engineering", "One app's handoff list"], ["mgr", "Managers", "Progress, timeline and who is blocking what"]];
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
      h("b", {}, j === 0 ? "Today" : x.fromChange ? "End state" : `Release ${j}`), h("span", {}, j === 0 ? day(D.today) : x.target ? day(x.target) : "no date"),
      j > 0 ? h("small", {}, x.fromChange ? "after every app's change lands" : `${plural((x.rows || []).length, "item")}, ${releaseState(x.state)}`) : h("small", {}, "before the initiative")))),
      !D.releases.count ? h("li", { class: "none" }, missing("No releases recorded yet.", "Until releases are planned, the timeline runs from today to the end state.")) : null);
  }
  function qRow(u) {
    const a = ASK[u.id];
    return h("li", {}, lamp(a.light.level), h("a", { "data-ref": u.id, title: u.id }, shorten(E[u.id] ? E[u.id].title : "", 54), idTag(u.id)),
      h("span", { class: "muted small" }, ` ask ${a.ask.name}${a.ask.inferred ? " (our guess)" : ""}, ${relDue(u.askBy)}`));
  }
  /* A handed-off item by its name: a page's title, a requirement's own words; a code only where the vault holds nothing to name it by. */
  const shortName = (id) => { const k = keyForId(id), e = ent(k); return e && e.title && e.title !== id ? shorten(e.title, 38) : id; };
  const releaseState = (s) => (s ? STATE_WORD[s] || s : "no state yet");  // plainwords' words, the ones every pill uses
  const CHANGE_WORD = { new: "New app", changed: "Changed app", unchanged: "Unchanged app", retired: "App being retired" };
  const HANDED_KIND = { app: "the app", runtime: "runtime page", provides: "contracts it provides", consumes: "contracts it uses", requirement: "requirements",
    slice: "slices", flow: "journeys", unknown: "open questions", epic: "epics", decision: "decisions", party: "outside companies" };
  const stepText = (stage) => { const all = D.progress.stages, i = all.indexOf(stage); return i < 0 ? stage : `step ${i + 1} of ${all.length}: ${stage}`; };
  const holdsKinds = (u, kinds) => [...new Set([...u.blocks, ...u.holds])].some((k) => kinds.includes(kindOf(k)));

  /* ------------------------------------------------------------ exec */
  function exec(grid) {
    grid.append(card("Goals and where they stand", ["Goals", () => Nav.open("goals")], D.goals.length ? list(D.goals, 5, (g) => {
      const qs = [...new Set([...(D.blockedBy[g.id] || []).filter((u) => isOpen(UNKNOWN[u])), ...D.above.filter((a) => a.holds === g.id).map((a) => a.unknown)])];
      const lv = worst(qs.map(unknownLevel));
      return h("li", {}, lamp(lv), h("span", {}, h("span", { html: g.goal }), idTag(g.id)), " ", statePill(g.state), qs.length ? h("span", { class: "muted small" }, ` waiting on ${qs.map(titleOf).join(", ")}`) : null);
    }) : empty("No Goals table yet.")));
    const dec = Object.values(E).filter((e) => e.kind === "decision");
    const decided = dec.filter((e) => e.state === "decided"), proposed = dec.filter((e) => e.state === "proposed");
    grid.append(card("What is decided", ["Decisions", () => Nav.open("decisions")],
      h("div", { class: "kpi-row" }, h("div", {}, h("b", {}, decided.length), h("span", {}, "decisions recorded")), h("div", {}, h("b", {}, proposed.length), h("span", {}, "proposed")),
        h("div", {}, h("b", {}, D.progress.percent + "%"), h("span", { title: "The average of the five measures on the Progress view" }, "complete (average of five progress measures)"))),
      list(decided, 4, (e) => h("li", {}, h("a", { "data-ref": e.key, title: e.id }, shorten(e.title, 60), idTag(e.id))))));
    const risks = D.riskList;
    grid.append(card("Top risks", ["Unknowns and risks", () => Nav.open("unknowns")], risks.length ? list(risks, 4, (r) => {
      const f = r.facts, sev = f.Impact || f.Severity || f.Likelihood || "";
      return h("li", {}, h("a", { "data-ref": r.id, title: r.id }, r.title, idTag(r.id)), sev ? h("span", { class: "pill" }, sev) : null,
        f.Mitigation ? h("div", { class: "muted small" }, shorten(f.Mitigation, 120)) : null);
    }) : empty("No risks recorded yet."), risks.length ? rule("Listed in the order the risks page gives them (it doesn't rank them).") : null));
    // one line per question, in plain words, not one per thing it holds
    const asked = [...new Set(D.above.map((a) => a.unknown))].filter((u) => UNKNOWN[u]).map((u) => ({ kind: "question", key: u, say: `is holding up ${Queue.say(D.above.filter((a) => a.unknown === u).map((a) => a.key))}` }));
    const owed = [...asked,
      ...proposed.map((e) => ({ kind: "decision", key: e.key, say: "proposed, not decided" })),
      ...D.progress.awaiting.map((a) => ({ kind: "override", key: a.key, say: `decided for ${a.owners.join(", ")}, waiting for them to confirm` })),
      ...Releases.STATES.slice(1).filter((x) => !x.fromChange && x.state !== "decided").map((x) => ({ kind: "release", key: null, name: x.heading || x.name, say: `release ${releaseState(x.state)}` }))];
    grid.append(card("What needs your decision", null, owed.length ? list(owed, 5, (x) => h("li", {}, x.key ? lampEl(levelForKey(x.key) || "caution") : lampEl("caution"),
      x.kind === "question" ? h("a", { "data-ref": x.key, title: x.key }, titleOf(x.key)) : x.key ? refChip(x.key) : h("b", {}, x.name), h("span", { class: "muted small" }, " " + x.say))) : empty("Nothing is waiting on an executive decision."),
      rule("Shown here: open questions blocking a goal, the strategy or another question; decisions still proposed; decisions made for someone else that they haven't confirmed; releases not yet agreed.")));
    grid.append(card("Release timeline", ["Releases", () => Nav.open("releases")], timeline()));
  }

  /* ------------------------------------------------------------ product */
  function product(grid) {
    const T = D.trace;
    grid.append(card("Capabilities and requirements", ["Capabilities", () => Nav.open("capabilities")], T.capabilities.length ? list(T.capabilities, 6, (c) => {
      const reqs = T.requirements.filter((r) => r.capability === c.id), alloc = reqs.filter((r) => T.allocation.some((a) => a.requirement === r.id && a.state !== "inkling"));
      return h("li", {}, h("a", { "data-ref": c.key, title: c.id }, E[c.key].title, idTag(c.id)), " ", E[c.key].change ? h("span", { class: "pill" }, E[c.key].change) : null,
        h("span", { class: "muted small" }, reqs.length ? ` ${plural(reqs.length, "requirement")}, ${reqs.length > 1 && alloc.length === reqs.length ? "all" : alloc.length} assigned to an app` : " no requirements written"));
    }) : missing("No capability pages yet.", "", "/vela:boundary"), T.capabilities.length && !T.requirements.length ? missing("No requirement rows yet.", "No requirements are written yet, so none is assigned to an app.", ["/vela:requirements", "/vela:allocate"]) : null));
    grid.append(card("What each release delivers", ["Releases", () => Nav.open("releases")], D.releases.count ? list(Releases.STATES.slice(1), 4, (x) => h("li", {},
      h("b", {}, `Release ${Releases.STATES.indexOf(x)}: `), shorten((x.heading || x.name).replace(/^[^:]*:\s*/, ""), 40), h("span", { class: "muted small" }, x.target ? ` · ${day(x.target)}` : ""),
      h("div", { class: "chips" }, (x.rows || []).map((r) => refChip(r.requirement, r.criteria.length ? h("span", { class: "rid", title: r.criteria.map((n) => "AC" + n).join(", ") }, (r.criteria.length === 1 ? "criterion " : "criteria ") + r.criteria.join(", ")) : null)))))
      : missing("No releases recorded yet.", "Once releases are planned, each one lists the requirements it delivers.", ["/vela:requirements", "/vela:allocate"])));
    const biz = openQs().filter((u) => holdsKinds(UNKNOWN[u.id], ["goal", "capability", "requirement", "flow"]) || D.above.some((a) => a.unknown === u.id));
    grid.append(card("Business questions", ["Who to ask", () => Nav.open("unknowns")], biz.length ? list(biz.sort((a, b) => cmp(a.askBy || "9", b.askBy || "9")), 5, (u) => qRow(UNKNOWN[u.id])) : empty("No open question is blocking a goal, capability, requirement or flow."),
      rule("Shown here: open questions that block a goal, capability, requirement or flow, directly or through something they hold up.")));
    grid.append(card("User flows", ["Flows", () => Nav.open("flows")], D.flows.length ? list(D.flows, 5, (f) => h("li", {}, lamp(levelOf(f.key)), h("a", { "data-ref": f.key, "data-reveal": "", title: E[f.key].id }, E[f.key].title, idTag(E[f.key].id)),
      h("span", { class: "muted small" }, ` ${plural(f.steps.length, "step")}`), h("button", { class: "btn tiny", onclick: () => Flows.present(f.key, 0) }, "▶ Present"))) : missing("No flows yet.", "", "/vela:boundary")));
  }

  /* ------------------------------------------------------------ QA */
  function qa(grid) {
    const epics = D.trace.epics;
    grid.append(card("Acceptance criteria by epic", ["Epics", () => Nav.open("epics")], epics.length ? list(epics, 6, (x) => {
      const ac = D.epicCriteria[x.key] || [], markers = [...new Set(ac.flatMap((c) => c.markers))];
      return h("li", {}, h("a", { "data-ref": x.key, title: E[x.key].id }, shorten(E[x.key].title, 44), idTag(E[x.key].id)), h("span", { class: "muted small" }, ` ${plural(ac.length, "criterion", "criteria")} `), markers.map((m) => h("span", { class: "marker" }, m)),
        linkChips(x.key, { small: true }));
    }) : missing("No epics yet.", "Acceptance criteria live on epic pages.", "/vela:epics")));
    grid.append(card("Contracts and who tests each side", ["Apps", () => Nav.open("apps")], D.map.contracts.length ? list(D.map.contracts, 4, (c) => {
      const t = D.testedBy[c.id];
      return h("li", {}, lamp(levelOf(c.id)), h("a", { "data-ref": c.id, title: c.id }, c.title, idTag(c.id)), h("span", { class: "muted small" }, ` ${titleOf(c.provider)} → ${c.consumers.map(titleOf).join(", ")}`),
        h("div", { class: t ? "small muted" : "small gap" }, t ? shorten(t, 96) : "Nobody is named to test this yet."), linkChips(c.id, { small: true }));
    }) : empty("No contracts.")));
    grid.append(card("How each app behaves when something fails", null, D.map.apps.length ? list(D.map.apps, 6, (a) => {
      const f = D.failure[a.key];
      return h("li", {}, h("a", { "data-ref": a.key }, h("b", {}, a.title)), " ", f.sections.length ? h("span", { class: "muted small" }, f.sections.map((x) => x.heading).join("; ")) : h("span", { class: "gap small" }, f.runtime ? "no failure behavior written yet" : "no runtime page yet"));
    }) : empty("No apps."), rule("Sections of each app's runtime page with fail, down, slow or outage in the heading.")));
    const testy = openQs().filter((u) => holdsKinds(UNKNOWN[u.id], ["contract", "epic", "requirement", "flow"]));
    grid.append(card("Unsettled things that would change a test", ["Who to ask", () => Nav.open("unknowns")], testy.length ? list(testy, 5, (u) => qRow(UNKNOWN[u.id])) : empty("No open question is blocking a contract, epic, requirement or flow."),
      rule("Shown here: open questions that block a contract, epic, requirement or flow, the things a test is written against.")));
  }

  /* ------------------------------------------------------------ engineering: one app's handoff list */
  function eng(grid, root) {
    const apps = D.map.apps;
    if (!st.app || !APPS[st.app]) st.app = (apps.find((a) => a.stage) || apps[0] || {}).key || "";
    root.insertBefore(h("div", { class: "door-pick" }, h("span", { class: "muted" }, "App "), apps.map((a) => h("button", { class: "chip" + (a.key === st.app ? " on" : ""), onclick: () => { st.app = a.key; Nav.syncHash(); rerender(); } }, lampEl(levelOf(a.key)), a.title))), grid);
    if (!st.app) { grid.append(empty("This vault has no apps.")); return; }
    const k = st.app, a = D.apps[k], e = E[k], row = D.progress.rows.find((r) => r.app === k), ho = row ? row.handoff : null;
    grid.append(card("Boundary", ["Open the page", () => go(Reader.keyFor(k), {})], (() => { const text = h("div", { class: "prose-text door-prose", html: e.prose || "<p>The page has no opening prose.</p>" }); return foldProse(h("div", { class: "prose" }, text), text); })(),
      h("div", { class: "chips" }, h("span", { class: "pill" }, CHANGE_WORD[e.change] || e.change || "No change"), e.stage ? h("span", { class: "pill", title: stepText(e.stage) }, "Stage: " + e.stage) : null, h("span", { class: "pill" }, "Domain: " + D.domains[k])),
      linkChips(k), Inside.doorEntry(k)));
    grid.append(card("Build plans for all apps", ["This app's plan", () => Inside.open(k, "plan")], list(apps, 12, (x) => {
      const r = Plan.readiness(x.key);
      return h("li", { "data-app": x.key, "data-ready": r.id }, h("a", { "data-ref": x.key }, h("b", {}, x.title)), " ", Plan.readinessPill(x.key), r.counts ? h("span", { class: "muted small" }, " " + r.counts) : null,
        h("button", { class: "btn tiny", onclick: () => Inside.open(x.key, "plan") }, "Build plan"));
    }), rule("No design: the team hasn't shared a design yet. Design only: a design, but no build plan yet. Otherwise the plan's own status. Counts are the plan's stories, tasks and points.")));
    // a contract from an outside party carries the party's own links too: its API spec is where the engineer starts
    const con = (id, dir) => h("li", {}, lamp(levelOf(id)), h("a", { "data-ref": id, title: id }, CONTRACT[id].title, idTag(id)), " ", statePill(CONTRACT[id].state),
      h("span", { class: "muted small" }, dir === "out" ? ` to ${CONTRACT[id].consumers.map(titleOf).join(", ")}` : ` from ${titleOf(CONTRACT[id].provider)}`),
      linkChips(id, { small: true }), dir === "in" && CONTRACT[id].providerKind === "party" ? linkChips(CONTRACT[id].provider, { small: true }) : null);
    grid.append(card("Contracts in and out", ["Focus on the map", () => Nav.focusApp(k)], h("h3", {}, "Provides"), a.provides.length ? list(a.provides, 4, (id) => con(id, "out")) : empty("It doesn't provide any contracts."),
      h("h3", {}, "Uses"), a.consumes.length ? list(a.consumes, 4, (id) => con(id, "in")) : empty("It doesn't use any contracts.")));
    const flows = flowsFor(k);
    grid.append(card("Flows and open questions", null, flows.length ? list(flows, 3, (r) => h("li", {}, h("a", { "data-ref": r.flow, "data-reveal": "", title: E[r.flow].id }, E[r.flow].title, idTag(E[r.flow].id)),
      h("button", { class: "btn tiny", onclick: () => Flows.present(r.flow, firstStepTouching(FLOW[r.flow], k)) }, "▶ Present"))) : empty("No flow goes through it."),
      h("h3", {}, "Open questions blocking it"), a.questions.length ? list(a.questions.map((q) => UNKNOWN[q.id]).filter(Boolean), 4, qRow) : empty("None.")));
    const slice = D.handoffList[k] || [];
    grid.append(card("Handoff", null, h("div", { class: "small" }, ho && (ho.manifest || ho.handedOff) ? [ho.handedOff ? h("div", {}, "Handed off: ", ho.handedOff) : null,
      ho.manifest ? h("div", { class: ho.changed + ho.removed ? "gap" : "muted" }, ho.problem ? "The handoff file can't be read: " + ho.problem : ho.changed + ho.removed ? `${plural(ho.changed + ho.removed, "change")} since the app team's lead accepted it (${ho.changed} changed, ${ho.removed} removed)` : "Nothing the app team's lead accepted has changed.") : h("div", { class: "muted" }, "No handoff file yet.")] : h("div", { class: "muted" }, "Not handed off.")),
      h("h3", {}, `What this app was handed, ${plural(slice.length, "item")}`),
      h("ul", { class: "door-list" }, [...new Set(slice.map((x) => x.kind))].map((kind) => { const of = slice.filter((x) => x.kind === kind); return h("li", {}, h("span", { class: "muted small slice-k" }, (HANDED_KIND[kind] || kind) + " "), of.slice(0, 6).map((x) => h("a", { class: "slice-id", "data-ref": keyForId(x.id), title: x.id }, shortName(x.id))), of.length > 6 ? h("span", { class: "muted small" }, ` +${of.length - 6}`) : null); })),
      rule("This is the handoff list: what the app's handoff file records it was given.")));
  }

  /* ------------------------------------------------------------ managers */
  function mgr(grid) {
    const P = D.progress, stages = P.stages;
    grid.append(card("Progress", ["Progress", () => { Nav.open("apps"); showView("progress"); }],
      h("div", { class: "kpi-row" }, h("div", {}, h("b", {}, P.percent + "%"), h("span", {}, "complete")), h("div", {}, h("b", {}, P.rows.filter((r) => r.stage).length), h("span", {}, "apps in progress")),
        h("div", {}, h("b", {}, openQs().length), h("span", {}, "open questions"))),
      h("div", { class: "shares" }, P.shares.map((x) => h("div", { class: "share" }, h("span", {}, x.name), h("div", { class: "bar" }, h("span", { style: `width:${x.total ? ((100 * x.done) / x.total).toFixed(1) : 100}%` })), h("span", { class: "v" }, `${x.done} of ${x.total}`))))));
    grid.append(card("Where each app stands", ["Apps", () => Nav.open("apps")], list(P.rows.filter((r) => r.stage), 7, (r) => h("li", {}, lamp(levelOf(r.app)), h("a", { "data-ref": r.app }, E[r.app].title),
      h("span", { class: "ladder inline" }, stages.map((x, i) => h("span", { class: i < stages.indexOf(r.stage) ? "done" : i === stages.indexOf(r.stage) ? "cur" : "", title: x }))), h("span", { class: "muted small" }, ` ${stepText(r.stage)}`)))));
    grid.append(card("Release timeline", ["Releases", () => Nav.open("releases")], timeline()));
    buildPlans(grid);
    const who = {};
    for (const u of openQs()) {
      const k = u.ask.key || u.ask.name, w = who[k] || (who[k] = { key: k, name: u.ask.name, n: 0, late: 0, holds: new Set(), guessed: 0 });
      w.n++; if (isDate(u.askBy) && dayNum(u.askBy) < TODAY) w.late++; if (u.ask.inferred) w.guessed++;
      (UNKNOWN[u.id] ? UNKNOWN[u.id].holds : []).forEach((x) => w.holds.add(x));
    }
    const ranked = Object.values(who).sort((a, b) => b.late - a.late || b.n - a.n || cmp(a.name, b.name));
    grid.append(card("What is blocked on whom", ["Who to ask", () => Nav.open("unknowns")], ranked.length ? list(ranked, 6, (w) => h("li", {}, lamp(w.late ? "warning" : "caution"),
      h("button", { class: "linkish strong", onclick: () => { Nav.open("unknowns"); Asks.meet(w.key); } }, w.name), h("span", { class: "muted small" }, ` ${plural(w.n, "open question")}${w.late ? `, ${w.late} overdue` : ""}, ${w.holds.size ? `blocking ${plural(w.holds.size, "thing")}` : "not blocking anything yet"}${w.guessed ? `; ${w.guessed} assigned by guess (no one recorded who to ask)` : ""}`)))
      : empty("No open questions.")));
  }

  /* The teams' build plans: what each app has to build, in stories and points, and what its stories are waiting on. */
  function buildPlans(grid) {
    const apps = D.map.apps.filter((a) => Plan.plan(a.key)), whom = Plan.blockedOn();
    grid.append(card("Build plans", null, apps.length ? list(apps, 6, (a) => {
      const p = Plan.plan(a.key), t = p.totals, held = p.stories.filter((x) => x.blockers.some((b) => b.kind !== "story")).length;
      return h("li", { "data-app": a.key }, h("a", { "data-ref": a.key }, h("b", {}, a.title)), " ", Plan.readinessPill(a.key),
        h("span", { class: "muted small" }, ` ${plural(t.stories, "story", "stories")}, about ${plural(t.points, "point")} of effort${held ? `; ${held} blocked by something outside the plan` : ""}`),
        h("button", { class: "btn tiny", onclick: () => Inside.open(a.key, "plan") }, "Build plan"));
    }) : empty("No team has shared a build plan yet."),
    whom.length ? h("h3", {}, "What stories are waiting on") : null,
    whom.length ? list(whom, 5, (w) => h("li", { "data-waiting": w.kind }, w.kind === "question" ? refChip(keyForId(w.ref)) : h("b", { title: w.text }, shorten(String(w.text).split(/;\s|\.\s/)[0], 80)), h("span", { class: "muted small" },
      `: blocks ${w.stories.map((x) => x.name || x.id).join(", ")} (${w.stories.map((x) => titleOf(x.app)).filter((x, i, all) => all.indexOf(x) === i).join(", ")})${w.kind === "outside" ? ", an outside company" : w.kind === "question" && ASK[w.ref] ? `, ask ${ASK[w.ref].ask.name}` : ""}`))) : null,
    rule("Points: small = 2, medium = 5, large = 8. They're for ordering work, not promises. Waiting on: an open question in the plan, an outside company, or anything else that isn't another story.")));
  }

  function render(main) {
    const def = ROLES.find(([id]) => id === st.role) || ROLES[1];
    const root = h("div", { class: "door", "data-role": def[0] });
    root.append(h("div", { class: "door-head" }, h("div", {}, h("div", { class: "kicker" }, "Your view"), h("h1", {}, def[0] === "eng" ? "Engineering: one app's handoff list" : `${def[1]}: ${def[2].toLowerCase()}`)), switcher()));
    const grid = h("div", { class: "door-grid door-" + def[0] });
    root.append(grid);
    main.append(root);
    ({ exec, product, qa, eng, mgr })[def[0]](grid, root);
  }
  return { render, st, ROLES };
})();
View("role", { label: "Your view", render: Roles.render });
