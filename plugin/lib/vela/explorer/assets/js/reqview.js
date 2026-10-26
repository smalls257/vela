/* The Requirements section: every functional requirement and whether it is met so far, and a focus on one.

   What the Violation is. A "met" light that the page works out for itself is a Distributed Monolith of rules (a second
   copy of "is it designed, is it in an epic" that drifts from the first), and one that says "met" is a Paper Tiger: the plan
   cannot see code or tests. This file draws only what D.requirements says; reqs_data.py decided every check once, and
   says in words what it could not work out. Nothing here counts, filters or words a check for itself.

   - List (the section's default): one row for each requirement, a dot and a few words for each of the first five checks, and
     the open questions that hold it as chips. A filter chip shows the rows the data tagged for it; a group-by only orders them.
   - Focus (a requirement is the section's open item, #s=requirements&open=CAP-003.FR1): a hero card, then six columns
     left to right in the order the work goes: who carries it, what it goes through, when it ships, the epics, the designs,
     the stories. A red dashed box is a gap. What is missing is listed under them, with who to ask.
   - The panel: the six checks and Decided with the plan's words, then the acceptance criteria and what each one names.
   Every box and chip is a button, so the keyboard has it, and opens the thing's own details in the right-hand panel. */
const ReqView = (() => {
  const R = D.requirements, ROWS = R.rows, BY = Object.fromEntries(ROWS.map((r) => [r.key, r]));
  const st = { filter: "all", group: "capability" };
  const DOT = { yes: "rv-ok", part: "rv-part", no: "rv-no" };
  const MARK = { yes: "✓", part: "◐", no: "✕" };
  const LABEL = { carried: "Carried", release: "On a release", epic: "In an epic", designed: "Designed", stories: "Has stories", open: "Nothing open", decided: "Decided" };
  const FILTERS = [["all", "All"], ["gap", "Has a gap"], ["held", "Waits on a question"], ["design", "No design yet"]];
  const GROUPS = [["capability", "Capability"], ["release", "Release"], ["app", "App"], ["none", "None"]];
  const check = (r, k) => r.checks.find((c) => c.k === k);
  const capKey = (r) => (D.trace.capabilities.find((c) => c.id === r.capability) || { key: "" }).key;
  const isReq = (k) => !!BY[k];
  const picked = () => Nav.st.child;
  const pick = (key) => DetailsPanel.show(key);
  const press = (el, fn) => { el.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); fn(); } }); };
  const metWords = (r) => `${r.met} of ${r.checks.length} checks met`;

  /* ------------------------------------------------------------ parts both views use */
  function questionChip(u, cls) {
    const lv = unknownLevel(u), tone = lv === "resolved" || lv === "dark" ? "" : lv, ask = ASK[u];
    return h("button", { class: `${cls} ${tone}`, type: "button", "data-key": u, title: ask ? `${ask.ask.name}${ask.askBy ? ", by " + day(ask.askBy) : ""}` : titleOf(u),
      onclick: (ev) => { ev.stopPropagation(); pick(u); } }, titleOf(u));
  }
  const dot = (v) => h("i", { class: "rv-dot " + DOT[v], "aria-hidden": "true" });
  function toggle(here) {
    const k = picked() || (ROWS[0] || {}).key;
    const items = [["list", "List", () => Nav.open("requirements")], ["focus", "One requirement", () => k && Nav.open("requirements", k)]];
    return h("div", { class: "rv-toggle", role: "group", "aria-label": "How to look at the requirements" },
      items.map(([id, label, run]) => h("button", { class: "chip" + (id === here ? " on" : ""), type: "button", "aria-pressed": id === here ? "true" : "false", "data-rv": id, disabled: id === "focus" && !k ? true : null, onclick: run }, label)));
  }
  function head(main, here, lede) {
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Requirements"), h("p", {}, lede)), h("div", { class: "spacer" }), toggle(here), Nav.pageActions()));
  }

  /* ------------------------------------------------------------ the list */
  function groups(rows) {
    if (st.group === "none") return [{ title: null, key: "", rows }];
    const out = new Map();
    const put = (id, title, key, tag, r) => { if (!out.has(id)) out.set(id, { id, title, key, tag, rows: [] }); out.get(id).rows.push(r); };
    for (const r of rows) {
      if (st.group === "capability") put(r.capability, titleOf(capKey(r)), capKey(r), r.capability, r);
      else if (st.group === "release") put(r.release ? r.release.name : "~", r.release ? r.release.short : "On no release", r.release ? "release:" + r.release.index : "", "", r);
      else if (r.apps.length) r.apps.forEach((a) => put(a.key, a.name, a.key, "", r));
      else put("~", "No app carries it yet", "", "", r);
    }
    return [...out.values()].sort((a, b) => (a.id === "~") - (b.id === "~"));
  }
  function row(r) {
    const cells = r.checks.slice(0, 5).map((c) => h("td", {}, h("div", { class: "rv-cell" }, dot(c.v), h("span", { title: c.long }, c.short))));
    const qs = r.questions.length ? r.questions.map((u) => questionChip(u, "rv-q")) : h("span", { class: "rv-cell" }, dot("yes"), h("span", {}, "none"));
    const go1 = () => Nav.open("requirements", r.key);
    const tr = h("tr", { class: "rv-row" + (App.trail.includes(r.key) ? " picked" : ""), tabindex: "0", role: "link", "data-key": r.key, "data-req": r.key, "aria-label": `${r.name}, ${metWords(r)}. Open everything it touches.`, onclick: go1 },
      h("td", {}, h("span", { class: "rv-name" }, r.name), idTag(r.id)), h("td", {}, statePill(r.state)), ...cells, h("td", {}, h("div", { class: "rv-qs" }, qs)));
    press(tr, go1);
    return tr;
  }
  function table(rows) {
    const body = h("tbody", {});
    for (const g of groups(rows)) {
      if (g.title) body.append(h("tr", { class: "rv-group", "data-group": g.id }, h("td", { colspan: "8" }, g.key ? h("button", { type: "button", "data-key": g.key, onclick: () => pick(g.key) }, g.title) : h("b", {}, g.title), g.tag ? idTag(g.tag) : null)));
      g.rows.forEach((r) => body.append(row(r)));
    }
    const th = (w, text, small) => h("th", { style: w ? { width: w } : {} }, text, small ? h("small", {}, small) : null);
    return h("table", { class: "rv-table" }, h("thead", {}, h("tr", {}, th("20%", "Requirement"), th("13%", "State"), th("", "Carried", "by apps"), th("", "Release"), th("", "Epic", "criteria"), th("", "Designed"), th("", "Stories"), th("19%", "Open questions"))), body);
  }
  function legend() {
    const key = (v, text) => h("span", { class: "rv-cell" }, dot(v), h("span", {}, text));
    return h("div", { class: "rv-legend" }, key("yes", "done"), key("part", "some apps, not all"), key("no", "missing"), h("span", { class: "rv-known" }, R.notKnown));
  }
  function list(main) {
    head(main, "list", R.lede);
    const sc = h("div", { class: "scroll pages rv-scroll" });
    main.append(sc);
    sc.append(h("div", { class: "rv-controls" },
      FILTERS.map(([id, label]) => h("button", { class: "chip" + (st.filter === id ? " on" : ""), type: "button", "aria-pressed": st.filter === id ? "true" : "false", "data-filter": id, onclick: () => { st.filter = id; rerender(); } },
        label, h("span", { class: "ct" }, String(R.counts[id])))),
      h("span", { class: "lbl" }, "Group by"),
      h("select", { "aria-label": "Group by", onchange: (ev) => { st.group = ev.target.value; rerender(); } }, GROUPS.map(([id, label]) => h("option", { value: id, selected: st.group === id ? true : null }, label)))));
    const rows = ROWS.filter((r) => r.in.includes(st.filter));
    sc.append(rows.length ? table(rows) : h("p", { class: "rv-none" }, "No requirement matches this filter."), legend());
  }

  /* ------------------------------------------------------------ the focus on one requirement */
  /* A box: the whole of it is one button, except the small chips a design box carries, which are buttons of their own. */
  function node(key, title, sub, cls, ...extra) {
    return h("div", { class: "rv-node " + (cls || "") },
      h("button", { class: "rv-main", type: "button", "data-key": key, onclick: () => pick(key) }, h("b", {}, title), sub ? h("small", {}, sub) : null), ...extra);
  }
  const column = (title, sub, ...nodes) => h("section", { class: "rv-col" }, h("h3", {}, title, h("em", {}, sub)), ...nodes);
  function carriedColumn(r) {
    return column("Carried by", `${plural(r.apps.length, "app")}, each its share`, r.apps.length ? r.apps.map((a) => node(a.key, a.name, a.share || "its share is on its app page")) : node(r.key, "No app carries it", check(r, "carried").long, "gap"));
  }
  function goesThroughColumn(r) {
    const nodes = [...r.through.map((c) => node(c, titleOf(c), idTag(E[c].id))), ...r.flows.map((f) => node(f, titleOf(f), ["journey · ", idTag(E[f].id)]))];
    return column("Goes through", "contracts and journeys", nodes.length ? nodes : h("p", { class: "muted small" }, "Nothing crosses to another app."));
  }
  function releaseColumn(r) {
    const c = check(r, "release");
    return column("Ships in", "release", r.release ? node("release:" + r.release.index, r.release.short, [r.release.date, r.release.note ? h("br") : null, r.release.note], r.release.note ? "warn" : "") : node(D.releases.page || r.key, "No release", c.long, "gap"));
  }
  function epicColumn(r) {
    return column("Epics", "criteria that trace to it", r.epics.length ? r.epics.map((e) => node(e.key, titleOf(e.key), [plural(e.criteria, "criterion", "criteria"), " · ", idTag(E[e.key].id)])) : node(r.key, "No epic", check(r, "epic").long, "gap"));
  }
  function designColumn(r) {
    const boxes = r.designs.map((d) => {
      if (!d.designed) return node(d.app, "No design yet", d.say, "gap");
      const chips = h("div", { class: "rv-comps" }, d.components.map((c) => h("button", { class: "rv-comp", type: "button", "data-key": Inside.kit.key(d.app, "c", c), onclick: () => pick(Inside.kit.key(d.app, "c", c)) }, c)));
      return node(Inside.kit.key(d.app, "sec", "overview"), `${titleOf(d.app)} design`, d.doc, "", chips);
    });
    return column("Designed in", "one per app", boxes.length ? boxes : node(r.key, "No design yet", check(r, "designed").long, "gap"));
  }
  function storyColumn(r) {
    const boxes = r.stories.map((s) => {
      if (!s.stories.length || s.putOff) return node(s.stories.length ? Inside.kit.key(s.app, "story", s.stories[0]) : s.app, s.stories.length ? s.stories.map((i) => `${i} (put off)`).join(", ") : "No stories yet", s.say, "gap");
      return node(Inside.kit.key(s.app, "story", s.stories[0]), s.stories.join(", "), `${titleOf(s.app)} breakdown`);
    });
    return column("Built by", "stories, per app", boxes.length ? boxes : node(r.key, "No stories yet", check(r, "stories").long, "gap"));
  }
  function hero(r) {
    return h("div", { class: "rv-hero", "data-req": r.key },
      h("div", {}, h("div", { class: "rv-hero-t" }, r.name, idTag(r.id)), h("div", { class: "rv-hero-d" }, r.text)),
      h("div", { class: "rv-score" }, h("div", { class: "big" }, `${r.met} of ${r.checks.length}`), h("small", {}, "checks met · ", statePill(r.state)),
        h("div", { class: "rv-bar" }, r.checks.map((c) => h("button", { class: "rv-seg " + DOT[c.v], type: "button", "data-check": c.k, title: `${LABEL[c.k]}: ${c.long}`, "aria-label": `${LABEL[c.k]}: ${c.long}`, onclick: () => pick(r.key) })))));
  }
  function missing(r) {
    const gaps = r.checks.filter((c) => c.v !== "yes");
    if (!gaps.length) return null;
    return h("section", { class: "rv-before" }, h("h3", {}, `Before it's met: ${plural(gaps.length, "thing")}`),
      h("ol", {}, gaps.map((c) => h("li", { "data-check": c.k }, upFirst(c.long) + ". ", c.next ? h("span", { class: "next" }, c.next) : null))));
  }
  function holding(r) {
    if (!r.questions.length) return null;
    return [h("h3", { class: "rv-holding" }, "Open questions holding it"),
      h("div", { class: "rv-holding-row" }, r.questions.map((u) => [questionChip(u, "rv-q"), h("span", { class: "who" }, ASK[u] ? `${ASK[u].ask.name}${ASK[u].askBy ? ", due " + day(ASK[u].askBy) : ""}` : "")]))];
  }
  function focus(main, r) {
    head(main, "focus", "Everything one requirement touches, in the order the work goes: who carries it, what it goes through, when it ships, how it's built. A red dashed box is a gap.");
    const sc = h("div", { class: "scroll pages rv-scroll" });
    main.append(sc);
    sc.append(hero(r), h("div", { class: "rv-cols" }, carriedColumn(r), goesThroughColumn(r), releaseColumn(r), epicColumn(r), designColumn(r), storyColumn(r)), missing(r), holding(r), legend());
  }

  /* ------------------------------------------------------------ render */
  function render(main) {
    if (!ROWS.length) { head(main, "list", R.lede); return; }
    const r = BY[picked()];
    if (r) focus(main, r); else list(main);
  }

  /* ------------------------------------------------------------ the panel */
  const quiet = (text) => Panel.empty(text);
  function waits(id) {
    const lv = unknownLevel(id), tone = lv === "resolved" || lv === "dark" ? "" : lv;
    return h("button", { class: `rv-waits ${tone}`, type: "button", "data-key": keyForId(id), onclick: () => pick(keyForId(id)) }, `waits on: ${titleOf(keyForId(id))}`);
  }
  const traceChip = (id) => (UNKNOWN[id] && isOpen(UNKNOWN[id]) ? waits(id) : refChip(keyForId(id)));
  function summary() {
    return [h("div", { class: "p-head" }, h("div", { class: "kind" }, "Requirements"), h("h2", {}, "Is each one met so far?"),
        h("p", { class: "p-lede" }, "Six checks for each requirement, from the plan alone: carried by an app, on a release, in an epic, designed, with stories, and nothing open holding it. Pick a row to see what it touches.")),
      h("div", { class: "p-body" }, h("p", { class: "p-note" }, R.notKnown)), PlanDetails.aboutSection()];
  }
  function checklist(r) {
    const items = [...r.checks, r.decided];
    return h("ul", { class: "rv-checks" }, items.map((c) => h("li", { class: DOT[c.v], "data-check": c.k }, h("span", { class: "mk", "aria-hidden": "true" }, MARK[c.v]),
      h("span", {}, LABEL[c.k], h("small", {}, upFirst(c.long) + (c.v !== "yes" && c.next ? `. ${c.next}` : ""))))));
  }
  function detail(k) {
    const r = BY[k], cap = capKey(r);
    return [h("div", { class: "p-head" }, h("div", { class: "kind" }, `Requirement · ${cap ? titleOf(cap) : r.capability}`), h("h2", {}, r.name),
        h("div", { class: "p-meta" }, idTag(r.id), " ", statePill(r.state), ` ${metWords(r)}`)),
      h("div", { class: "p-body" }, h("p", {}, r.text),
        Panel.section("Is it met so far?", null, checklist(r)),
        Panel.section("Its acceptance criteria", r.criteria.length, r.criteria.length ? h("ol", { class: "rv-crit" }, r.criteria.map((c) => h("li", {}, c.text, c.trace.length ? h("span", { class: "tr" }, c.trace.map(traceChip)) : null))) : quiet("No criteria are listed under it.")),
        picked() === k ? null : h("button", { class: "btn", type: "button", "data-open-focus": "", onclick: () => Nav.open("requirements", k) }, "See everything it touches →"))];
  }
  function mark(key) {
    for (const el of $$("#main [data-key]")) el.classList.remove("picked");
    if (!key) return;
    for (const el of $$("#main [data-key]")) if (el.dataset.key === key) el.classList.add("picked");
  }
  DetailsPanel.register("reqs", {
    view: "reqs", live: () => true, rootLabel: "Requirements", summary, owns: isReq, detail, label: (k) => titleOf(k), focus: mark,
  });
  return { render, st, isReq, check };
})();
View("reqs", { label: "Requirements", title: "Every requirement, and whether it is met so far", render: ReqView.render, count: () => String(D.requirements.rows.length) });
