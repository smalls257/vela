/* The capability views: cards for every capability, a focus on one, and a matrix of who needs whom.

   What the Violation is. A dependency picture built from apps or from requirement allocation is a Paper Tiger: it
   passes on the data it was given and claims a lean no journey needs. These views draw only what D.capDeps says, and
   capdeps.py derives that from the flows alone (CONVENTIONS: How capabilities depend on each other). This file never
   works out a dependency itself, so the rule has one home (a second copy here would be a Distributed Monolith).

   - Cards (overview): one per capability, grouped by the release that first delivers it, the stripe colored by state,
     open questions or how much of it is settled. A card opens the focus view and the detail panel.
   - Focus: the picked capability in the middle, what needs it on the left, what it needs on the right, about seven a side
     with "+N more"; each arrow carries a chip naming the flow and the number of contracts. A chip lists them in the panel.
   - Matrix: every capability against every other, the row needs the column, the cell the number of flows. A cell lists them.
   The picked capability is CapFocus's key (the section's open item), so the sidebar, a chip elsewhere and a link all land
   on the focus view, and the cards and the matrix keep it marked. The dependency itself is a panel key, dep:<from>><to>. */
const CapView = (() => {
  const st = { mode: "cards", color: "state", more: { left: false, right: false }, scroll: null };
  const PER_SIDE = 7, WIDE = 12;  // about seven a side in the focus view; past about twelve capabilities the matrix is offered
  const EDGES = D.capDeps.edges, NO_CAPS = D.capDeps.noCapabilities;
  const EDGE = new Map(EDGES.map((e) => [e.from + ">" + e.to, e]));
  const caps = () => D.trace.capabilities.map((c) => c.key);
  const depKey = (a, b) => `dep:${a}>${b}`;
  const isDep = (k) => k.startsWith("dep:");
  const parseDep = (k) => { const [a, b] = k.slice(4).split(">"); return { a, b }; };
  const isCap = (k) => !!ent(k) && ent(k).kind === "capability";
  const needs = (k) => EDGES.filter((e) => e.from === k);     // k depends on e.to
  const neededBy = (k) => EDGES.filter((e) => e.to === k);    // e.from depends on k
  const byTitle = (side) => (p, q) => (q.nFlows - p.nFlows) || cmp(titleOf(side(p)).toLowerCase(), titleOf(side(q)).toLowerCase());
  const SETTLED = ["fact", "decided"];

  /* ------------------------------------------------------------ what a card says about a capability */
  function releaseOf(id) {
    const states = D.releases.states;
    if (!D.releases.count) return 0;
    for (let i = 1; i < states.length; i++) if ((states[i].rows || []).some((r) => r.requirement.startsWith(id + "."))) return i;
    return 0;  // 0: no release lists a requirement of it yet
  }
  function facts(k) {
    const id = E[k].id, reqs = D.trace.requirements.filter((r) => r.capability === id);
    const asked = [...new Set([id, ...reqs.map((r) => r.id)].flatMap((x) => D.blockedBy[x] || []))].filter((u) => isOpen(UNKNOWN[u]));
    return { id, reqs, settled: reqs.filter((r) => SETTLED.includes(r.state)).length, questions: asked,
      epics: D.trace.epics.filter((x) => x.delivers.includes(id)).map((x) => x.key),
      apps: Object.entries(D.appCaps || {}).filter(([, v]) => v.caps.includes(id)).map(([a]) => a), release: releaseOf(id) };
  }
  const worstLevel = (levels) => levels.slice().sort((a, b) => rank(b) - rank(a))[0] || "dark";
  /* [stripe color, the words that say the same thing], so color is never the only signal */
  function stripe(k, f) {
    if (st.color === "open") {
      const lv = worstLevel(f.questions.map(unknownLevel));
      return f.questions.length ? [LIGHT[lv].color, plural(f.questions.length, "open question")] : ["var(--ink-4)", "no open questions"];
    }
    if (st.color === "ready") {
      if (!f.reqs.length) return ["var(--ink-4)", "no requirements written"];
      return f.settled === f.reqs.length ? ["var(--mix-decided)", "all settled"] : f.settled ? ["var(--mix-fact)", "partly settled"] : ["var(--mix-inkling)", "none settled yet"];
    }
    const state = E[k].state;
    return [`var(--mix-${state}, var(--ink-4))`, state ? stateWord(state) : "no state recorded"];
  }
  const COLOR_BY = [["state", "State"], ["open", "Open questions"], ["ready", "Requirements settled"]];

  /* ------------------------------------------------------------ the section's shared parts */
  /* How many flows the picture leaves out, and which, so the lead can add the field. */
  function flowNote() {
    const total = D.flows.length, left = NO_CAPS.length;
    if (!total) return emptyState("No flows are written yet, so no capability depends on another.", "A flow lists the capabilities its journey needs, the first one primary.", "/vela:shape", "inline");
    if (left === total) return emptyState("No flow lists its capabilities yet, so no capability depends on another.", "Add a capabilities: list to a flow page, the first one primary.", "/vela:shape", "inline");
    if (!left) return null;
    const shown = NO_CAPS.slice(0, 6);
    return h("p", { class: "p-note cv-note", "data-no-caps": left }, `${plural(left, "flow")} ${left === 1 ? "lists" : "list"} no capabilities yet, so ${left === 1 ? "it adds" : "they add"} no dependencies: `,
      shown.map((f) => refChip(f)), left > shown.length ? ` and ${left - shown.length} more.` : null);
  }
  const ledeText = () => `${plural(caps().length, "capability", "capabilities")}; ${plural(EDGES.length, "dependency", "dependencies")}, read from the flows that list more than one.`;
  function toggle(here) {
    const sel = CapFocus.key();
    const items = [["cards", "Cards", () => { st.mode = "cards"; if (App.view !== "capmap") showView("capmap"); else { rerender(); Panel.render(); } }],
      ["focus", "Focus", () => Nav.open("capabilities", sel || caps()[0])],
      ["matrix", "Matrix", () => showView("capmatrix")]];
    return h("div", { class: "cv-toggle", role: "group", "aria-label": "How to look at the capabilities" },
      items.map(([id, label, run]) => h("button", { class: "chip" + (id === here ? " on" : ""), type: "button", "aria-pressed": id === here ? "true" : "false", "data-cv": id, disabled: id === "focus" && !caps().length ? true : null, onclick: run }, label)));
  }
  function head(main, here, extra) {
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, Nav.title("Capabilities")), h("p", {}, ledeText(), Nav.ledeLink())),
      h("div", { class: "spacer" }), extra || null, toggle(here), Nav.pageActions()));
  }
  function nothing(main, here) {
    head(main, here);
    main.append(h("div", { class: "scroll pages" }, emptyState("No capabilities yet.", "The plan's lead adds them when shaping the initiative.", "/vela:shape")));
  }
  /* Called by Nav.open: which view a section visit lands on. The focus is the open item; with none, the cards. */
  function enter(child, opts, here) {
    st.more = { left: false, right: false };
    if (opts && opts.stay && here === "capmatrix") return "capmatrix";
    st.mode = child ? "focus" : "cards";
    return "capmap";
  }

  /* ------------------------------------------------------------ cards */
  function card(k) {
    const f = facts(k), [color, said] = stripe(k, f), e = E[k], n = needs(k).length, by = neededBy(k).length;
    const on = CapFocus.key() === k;
    return h("button", { class: "cv-card" + (on ? " on" : ""), type: "button", "data-cap": k, "aria-pressed": on ? "true" : "false", style: { "--k": color }, onclick: () => Nav.open("capabilities", k) },
      h("span", { class: "cv-title" }, e.title, idTag(f.id)),
      h("span", { class: "cv-row" }, statePill(e.state), st.color === "state" ? null : h("span", { class: "cv-said" }, said)),
      h("span", { class: "cv-row cv-apps" }, f.apps.length ? f.apps.map((a) => h("span", { class: "cv-app" }, titleOf(a))) : h("span", { class: "muted small" }, "No app delivers it yet")),
      h("span", { class: "cv-row" }, h("i", {}, "Requirements settled"), f.reqs.length ? `${f.settled} of ${f.reqs.length}` : "none written",
        h("span", { class: "cv-bar", "aria-hidden": "true" }, h("span", { style: { width: (f.reqs.length ? Math.round(100 * f.settled / f.reqs.length) : 0) + "%" } }))),
      h("span", { class: "cv-row" }, h("i", {}, "Open questions"), String(f.questions.length)),
      h("span", { class: "cv-row" }, h("i", {}, "Epics"), f.epics.length ? f.epics.map((x) => E[x].id).join(", ") : "none yet"),
      h("span", { class: "cv-row cv-deps" }, h("i", {}, "Needs"), String(n), h("span", { class: "cv-gap" }), h("i", {}, "Needed by"), String(by)));
  }
  function releaseGroups() {
    const groups = new Map();
    for (const k of caps()) { const r = facts(k).release; if (!groups.has(r)) groups.set(r, []); groups.get(r).push(k); }
    const heading = (i) => {
      if (!i) return D.releases.count ? "Not in a release yet" : "All capabilities";
      const S = D.releases.states[i], name = (S.heading || S.name || "").replace(/^[^:]*:\s*/, "") || S.name;
      return `Release ${i}: ${name}${S.target ? ` (${day(S.target)})` : ", no date yet"}`;
    };
    return [...groups.keys()].sort((a, b) => (a || 1e9) - (b || 1e9)).map((i) => ({ index: i, title: heading(i), keys: groups.get(i) }));
  }
  function legend() {
    const pairs = st.color === "open" ? [["var(--ink-4)", "none"], ...["caution", "warning"].map((l) => [LIGHT[l].color, LIGHT[l].word.toLowerCase()])]
      : st.color === "ready" ? [["var(--mix-decided)", "all settled"], ["var(--mix-fact)", "partly"], ["var(--mix-inkling)", "none yet"]]
        : ["inkling", "assumption", "fact", "decided"].map((s) => [`var(--mix-${s})`, stateWord(s).toLowerCase()]);
    return h("span", { class: "cv-legend" }, pairs.map(([c, w]) => h("span", {}, h("i", { class: "cv-sw", style: { background: c } }), w)));
  }
  function cards(main) {
    if (!caps().length) return nothing(main, "cards");
    head(main, "cards");
    const sc = h("div", { class: "scroll pages cv-scroll" });
    main.append(sc);
    sc.append(h("div", { class: "cv-controls" }, h("span", { class: "muted small" }, "Color by"),
      COLOR_BY.map(([id, label]) => h("button", { class: "chip" + (st.color === id ? " on" : ""), type: "button", "aria-pressed": st.color === id ? "true" : "false", "data-color": id, onclick: () => { st.color = id; rerender(); } }, label)), legend()));
    if (caps().length > WIDE) sc.append(h("p", { class: "p-note cv-wide" }, `${caps().length} capabilities are a lot to read as cards. `,
      h("button", { class: "linkish", type: "button", "data-cv-matrix": "", onclick: () => showView("capmatrix") }, "The matrix shows every dependency at once.")));
    const note = flowNote();
    if (note) sc.append(note);
    for (const g of releaseGroups()) sc.append(h("section", { class: "cv-group", "data-release": g.index }, h("h2", { class: "cv-h" }, g.title), h("div", { class: "cv-grid" }, g.keys.map(card))));
  }

  /* ------------------------------------------------------------ focus */
  const edgeWords = (e) => `${e.nFlows === 1 ? titleOf(e.flows[0].flow) : plural(e.nFlows, "flow")} · ${plural(e.nContracts, "contract")}`;
  const GEO = { W: 1100, NW: 240, NH: 76, GAP: 26, TOP: 44, CHIP: 150 };
  function focus(main, k) {
    head(main, "focus", h("button", { class: "chip", type: "button", "data-cv-all": "", onclick: () => Nav.open("capabilities") }, "All capabilities"));
    const sc = h("div", { class: "cv-focus-wrap" });
    main.append(sc);
    const note = flowNote();
    if (note) sc.append(h("div", { class: "cv-focus-note" }, note));
    const left = neededBy(k).sort(byTitle((e) => e.from)), right = needs(k).sort(byTitle((e) => e.to));
    if (!left.length && !right.length) {
      sc.append(h("div", { class: "cv-board cv-lone", "data-lone": k }, h("div", {}, h("b", {}, titleOf(k)), " has no dependencies in the flows: no flow lists it with another capability, and nothing needs it.")));
      return;
    }
    const board = h("div", { class: "cv-board", id: "cv-board" });
    sc.append(board);
    draw(board, k, left, right);
    const both = right.filter((e) => left.some((l) => l.from === e.to));
    if (both.length) sc.append(h("p", { class: "p-note cv-both" }, h("b", {}, "Both ways: "), both.map((e) => titleOf(e.to)).join(", "), ` ${both.length === 1 ? "needs" : "need"} ${titleOf(k)}, and ${titleOf(k)} needs ${both.length === 1 ? "it" : "them"}, so ${both.length === 1 ? "it appears" : "they appear"} on both sides.`));
    sc.append(h("p", { class: "p-note" }, `Each arrow reads "needs". Up to ${PER_SIDE} a side; the rest fold into "+N more".`));
  }
  function draw(board, k, left, right) {
    const { W, NW, NH, GAP, TOP, CHIP } = GEO, PITCH = NH + GAP;
    const showL = st.more.left ? left : left.slice(0, PER_SIDE), showR = st.more.right ? right : right.slice(0, PER_SIDE);
    const moreL = left.length - showL.length, moreR = right.length - showR.length;
    const rows = Math.max(showL.length + (moreL ? 1 : 0), showR.length + (moreR ? 1 : 0), 1);
    const H = TOP + rows * PITCH + 24, xL = 20, xM = (W - NW) / 2, xR = W - NW - 20, yM = H / 2;
    const colY = (n, i) => (H - (n * PITCH - GAP)) / 2 + i * PITCH + NH / 2;  // the middle of row i of n
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "cv-svg", role: "group", "aria-label": `${titleOf(k)}: what needs it, and what it needs` }, board);
    const defs = s("defs", {}, svg);
    const mk = s("marker", { id: "cv-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 8, markerHeight: 8, orient: "auto" }, defs);
    s("path", { d: "M0 0L10 5L0 10z", class: "cv-head" }, mk);
    const label = (x, y, text) => { const t = s("text", { x, y, class: "cv-col-h" }, svg); t.textContent = text; };
    label(xL, 24, `WHAT NEEDS IT (${left.length})`); label(xM, 24, "PICKED"); label(xR, 24, `WHAT IT NEEDS (${right.length})`);
    const gPaths = s("g", {}, svg), gNodes = s("g", {}, svg), gChips = s("g", {}, svg);
    const bothKeys = new Set(right.filter((e) => left.some((l) => l.from === e.to)).map((e) => e.to));
    const node = (cap, x, yc, cls) => {
      const g = s("g", { class: "cv-node " + (cls || "") + (bothKeys.has(cap) ? " both" : ""), tabindex: 0, role: "button", "data-key": cap, "data-cap": cap,
        "aria-label": `${titleOf(cap)}${cls === "sel" ? ", picked" : ", refocus on it"}${bothKeys.has(cap) ? ", needs each other" : ""}` }, gNodes);
      s("rect", { x, y: yc - NH / 2, width: NW, height: NH, rx: 10 }, g);
      LabelFit.put(g, { x: x + 12, y: yc - NH / 2 + 22, class: "cv-name" }, titleOf(cap), NW - 24, { size: 14, weight: 600, max: 3 });
      LabelFit.put(g, { x: x + 12, y: yc + NH / 2 - 10, class: "cv-meta" }, `${E[cap].id}${E[cap].state ? " · " + stateWord(E[cap].state) : ""}${bothKeys.has(cap) ? " · needs each other" : ""}`, NW - 24, { size: 11.5, weight: 500, max: 1 });
      const go1 = () => (cls === "sel" ? DetailsPanel.show(cap, { reset: true }) : Nav.open("capabilities", cap));
      g.addEventListener("click", go1);
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go1(); } });
    };
    const chip = (e, x, y) => {
      const name = e.nFlows === 1 ? titleOf(e.flows[0].flow) : plural(e.nFlows, "flow"), count = plural(e.nContracts, "contract");
      const f = LabelFit.fit(name, CHIP, { size: 12.5, weight: 500, max: 2 }), lh = f.lh;
      const w = Math.max(...f.lines.map((l) => LabelFit.width(l, f.size, 500)), LabelFit.width(count, 11.5, 400)) + 18, hh = Math.ceil((f.lines.length + 1) * lh + 10);
      const g = s("g", { class: "cv-edge", tabindex: 0, role: "button", "data-key": depKey(e.from, e.to), "data-dep": e.from + ">" + e.to,
        "aria-label": `${titleOf(e.from)} needs ${titleOf(e.to)}: ${edgeWords(e)}` }, gChips);
      s("rect", { x: x - w / 2, y: y - hh / 2, width: w, height: hh, rx: Math.min(hh / 2, 14) }, g);
      LabelFit.put(g, { x: x - w / 2 + 9, y: y - hh / 2 + 5 + f.size, class: "cv-chip-t" }, name, CHIP, { size: 12.5, weight: 500, max: 2 });
      const c = LabelFit.put(g, { x: x - w / 2 + 9, y: y - hh / 2 + 5 + f.size + f.lines.length * lh, class: "cv-chip-n" }, count, CHIP, { size: 11.5, weight: 400, max: 1 });
      c.setAttribute("data-count", e.nContracts);
      const open = () => DetailsPanel.show(depKey(e.from, e.to), { reset: true });
      g.addEventListener("click", open);
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } });
    };
    const link = (x1, y1, x2, y2) => s("path", { d: `M${x1} ${y1}C${(x1 + x2) / 2} ${y1} ${(x1 + x2) / 2} ${y2} ${x2} ${y2}`, class: "cv-link", "marker-end": "url(#cv-arrow)" }, gPaths);
    const more = (n, x, y, side) => {
      const g = s("g", { class: "cv-more", tabindex: 0, role: "button", "aria-label": `Show ${n} more`, "data-more": side }, gNodes);
      s("rect", { x, y: y - 16, width: NW, height: 32, rx: 8 }, g);
      const t = s("text", { x: x + NW / 2, y: y + 5, "text-anchor": "middle", class: "cv-more-t" }, g);
      t.textContent = `+${n} more`;
      const expand = () => { st.more[side] = true; rerender(); };
      g.addEventListener("click", expand);
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); expand(); } });
    };
    showL.forEach((e, i) => { const y = colY(showL.length + (moreL ? 1 : 0), i); link(xL + NW, y, xM, yM); node(e.from, xL, y); chip(e, (xL + NW + xM) / 2, (y + yM) / 2); });
    if (moreL) more(moreL, xL, colY(showL.length + 1, showL.length), "left");
    showR.forEach((e, i) => { const y = colY(showR.length + (moreR ? 1 : 0), i); link(xM + NW, yM, xR, y); node(e.to, xR, y); chip(e, (xM + NW + xR) / 2, (y + yM) / 2); });
    if (moreR) more(moreR, xR, colY(showR.length + 1, showR.length), "right");
    node(k, xM, yM, "sel");
    MapView.fitSvg(svg, board, W, H, 1.15);
    Pan.attach(board, { key: "capfocus", svg: () => board.querySelector("svg.cv-svg") });
  }

  /* ------------------------------------------------------------ matrix */
  function matrix(main) {
    if (!caps().length) return nothing(main, "matrix");
    head(main, "matrix");
    const sc = h("div", { class: "scroll pages cv-scroll", id: "cv-matrix-scroll" });
    main.append(sc);
    const ids = caps(), sel = CapFocus.key();
    sc.append(h("p", { class: "p-note" }, "Read a cell as: the row needs the column. The number is how many flows make it. ",
      h("b", {}, "⇄"), " marks a pair that needs each other; the mirror cell is filled too. Hatched cells are a capability against itself."));
    const note = flowNote();
    if (note) sc.append(note);
    const pick = (cap) => { const box = $("#cv-matrix-scroll"); st.scroll = box ? [box.scrollLeft, box.scrollTop] : null; Nav.open("capabilities", cap, { stay: true }); };
    const name = (cap) => titleOf(cap);
    const head1 = h("tr", {}, h("th", { class: "corner" }), ids.map((c) => h("th", { class: "col" + (sel === c ? " on" : "") }, h("button", { class: "linkish", type: "button", "data-cap": c, title: name(c), onclick: () => pick(c) }, name(c)))));
    const body = ids.map((a) => h("tr", { "data-row": a }, h("th", { class: "row" + (sel === a ? " on" : "") }, h("button", { class: "linkish", type: "button", "data-cap": a, onclick: () => pick(a) }, name(a))),
      ids.map((b) => {
        if (a === b) return h("td", {}, h("div", { class: "cv-cell x", "aria-hidden": "true" }));
        const e = EDGE.get(a + ">" + b);
        if (!e) return h("td", {}, h("div", { class: "cv-cell none" + (sel === a || sel === b ? " hl" : ""), "aria-hidden": "true" }));
        return h("td", {}, h("button", { class: "cv-cell d" + (e.both ? " both" : "") + (sel === a || sel === b ? " hl" : ""), type: "button", "data-dep": a + ">" + b,
          "aria-label": `${name(a)} needs ${name(b)}: ${plural(e.nFlows, "flow")}${e.both ? ", and the reverse is true too" : ""}`,
          onclick: () => { pick(a); DetailsPanel.show(depKey(a, b), { reset: true }); } }, String(e.nFlows), e.both ? h("span", { class: "cv-both-mark", "aria-hidden": "true" }, "⇄") : null));
      })));
    sc.append(h("div", { class: "cv-mx-wrap" }, h("table", { class: "cv-mx" }, h("thead", {}, head1), h("tbody", {}, body))));
    if (st.scroll) { sc.scrollLeft = st.scroll[0]; sc.scrollTop = st.scroll[1]; st.scroll = null; }
  }

  /* ------------------------------------------------------------ render */
  function render(main) {
    const k = CapFocus.key();
    if (st.mode === "focus" && k && caps().includes(k)) return focus(main, k);
    st.mode = "cards";
    cards(main);
  }

  /* ------------------------------------------------------------ the panel */
  const quiet = (text) => Panel.empty(text);
  const head2 = (kind, title, meta) => h("div", { class: "p-head" }, h("div", { class: "kind" }, kind), h("h2", {}, title), meta ? h("div", { class: "p-meta" }, meta) : null);
  function summary() {
    const note = flowNote();
    return [h("div", { class: "p-head" }, h("div", { class: "kind" }, "Capabilities"), h("h2", {}, "What needs what"),
      h("p", { class: "p-lede" }, "A capability depends on another when a journey that serves it lists the other. Pick a card, a box, a chip or a cell to see why."), h("div", { class: "p-meta" }, ledeText())),
      note ? h("div", { class: "p-body" }, note) : null, PlanDetails.aboutSection()];
  }
  function depList(title, edges, side) {
    return Panel.section(title, edges.length, edges.length ? h("ul", { class: "mini-list cv-deplist" }, edges.map((e) => h("li", {}, DetailsPanel.link(side(e), titleOf(side(e))),
      h("div", { class: "ml-sub" }, DetailsPanel.link(depKey(e.from, e.to), edgeWords(e), "Which flows and contracts make this"))))) : quiet(title === "Needs" ? "Nothing: no flow lists another capability with it." : "Nothing yet: no flow lists it as one it needs."));
  }
  function capNodes(k) {
    const nodes = Panel.keyNodes(k), body = nodes.find((n) => n.classList && n.classList.contains("p-body"));
    const mine = [depList("Needs", needs(k).sort(byTitle((e) => e.to)), (e) => e.to), depList("Needed by", neededBy(k).sort(byTitle((e) => e.from)), (e) => e.from)];
    if (body) body.prepend(...mine); else nodes.push(...mine);
    return nodes;
  }
  function depNodes(key) {
    const { a, b } = parseDep(key), e = EDGE.get(a + ">" + b);
    if (!e) return [head2("Dependency", `${titleOf(a)} and ${titleOf(b)}`), h("div", { class: "p-body" }, quiet(`No flow makes ${titleOf(a)} depend on ${titleOf(b)}.`))];
    const back = EDGE.get(b + ">" + a);
    const flowRow = (f) => h("li", {}, refChip(f.flow), h("div", { class: "ml-sub" }, f.lists ? `Lists both capabilities, ${titleOf(a)} first.` : null,
      f.repeats.length ? ["Repeats ", f.repeats.map((r) => refChip(r)), `, whose first capability is ${titleOf(b)}.`] : null),
      f.contracts.length ? h("div", {}, h("span", { class: "muted small" }, "Contracts its steps cross: "), f.contracts.map((c) => refChip(c))) : h("div", { class: "muted small" }, "None of its steps crosses a contract."));
    return [head2("Dependency", `${titleOf(a)} needs ${titleOf(b)}`, `${plural(e.nFlows, "flow")} · ${plural(e.nContracts, "contract")}`),
      h("div", { class: "p-body" },
        h("p", { class: "p-note" }, `The journey for ${titleOf(a)} needs ${titleOf(b)} in place. This comes from the flows below and nothing else.`),
        Panel.section("Flows that make it", e.nFlows, h("ul", { class: "mini-list" }, e.flows.map(flowRow))),
        Panel.section("Contracts across them", e.nContracts, e.contracts.map((c) => refChip(c))),
        back ? Panel.section("Both ways", null, h("p", { class: "p-note" }, `${titleOf(b)} also needs ${titleOf(a)}: `, DetailsPanel.link(depKey(b, a), edgeWords(back)))) : null,
        Panel.section("The two capabilities", null, DetailsPanel.link(a, titleOf(a)), " ", DetailsPanel.link(b, titleOf(b))))];
  }
  /* The picked thing is marked in whichever drawing is on screen; a pick is never only in the panel. */
  function mark(key) {
    for (const el of $$("#main [data-key], #main [data-cap]")) el.classList.remove("picked");
    if (!key) return;
    for (const el of $$("#main [data-key], #main [data-cap]")) if ((el.dataset.key || el.dataset.cap) === key) el.classList.add("picked");
  }
  const spec = (view) => ({
    view, live: () => true, rootLabel: "Capabilities", summary, owns: (k) => isCap(k) || isDep(k),
    detail: (k) => (isDep(k) ? depNodes(k) : capNodes(k)),
    label: (k) => { if (!isDep(k)) return titleOf(k); const { a, b } = parseDep(k); return `${titleOf(a)} needs ${titleOf(b)}`; },
    focus: (k) => mark(k && (isCap(k) || isDep(k)) ? k : null),
  });
  DetailsPanel.register("capmap", spec("capmap"));
  DetailsPanel.register("capmatrix", spec("capmatrix"));
  return { render, matrix, enter, st, edges: EDGES, edgeKey: depKey, facts, releaseGroups };
})();
View("capmap", { label: "Capabilities", title: "Every capability, what it needs and what needs it", render: CapView.render, count: () => String(D.trace.capabilities.length) });
View("capmatrix", { label: "Dependency matrix", title: "Which capability needs which, across all of them", render: CapView.matrix });
