/* The map. Four lenses on one pinned formation:
   - Cockpit (default): a dark panel, calm grey where all is well, a lamp lit only where attention.lights says the
     lead is needed. Lit lamps glow steadily; only an overdue one breathes. It can group the apps by domain
     (collapsible clusters) or by business capability (regions), and focus on one app with its direct neighbours
     (mapgroups.js). Picking something runs the chosen motion, trace or ripple (motion.js).
   - Line map: flows are lines and apps are stations. With the Trains motion, a train runs each flow's journey.
   - Matrix: who provides (rows) to whom (columns). Past about 20 boxes or 30 lines a node-link drawing stops
     helping (Ghoniem et al. 2004), so the matrix takes over there unless the apps have domains to cluster by.
   - Releases: the system before and after each release (releases.js). */
const MapView = (() => {
  const SCALE_NODES = 20, SCALE_LINES = 30, CLUSTER_PAST = 12;
  const st = { lens: null, group: null, focus: null, open: new Set(), shut: new Set(), line: null, running: true };
  const lines = () => D.map.contracts.reduce((n, c) => n + c.consumers.filter((k) => k !== c.provider).length, 0);
  const big = () => D.nodes.length > SCALE_NODES || lines() > SCALE_LINES;
  const hasDomains = () => D.grouping.domain;
  const hasCapabilities = () => D.grouping.capability;
  const manyApps = () => D.map.apps.length > CLUSTER_PAST;
  const lens = () => st.lens || (big() && !hasDomains() ? "matrix" : "cockpit");
  const GROUP_OFF = { domain: "No app page names a domain yet; /planner:boundary records one when you name it",
    capability: "No app carries capability requirements or epics yet; /planner:requirements and /planner:allocate write the requirements, /planner:epics the epics" };
  const groupOff = (id) => (id === "domain" && !hasDomains()) || (id === "capability" && !hasCapabilities());
  const group = () => { const g = st.group || (App.section === "capabilities" ? "capability" : manyApps() && hasDomains() ? "domain" : "none"); return groupOff(g) ? "none" : g; };
  let pulses = [], trains = [], gPulses = null, LAY = null, stripEl = null;
  const LEDE = {
    cockpit: "Every app, outside party and contract, where they always sit. Grey is settled; a lamp is lit only where something needs you.",
    domain: "Apps grouped by the domain on their page. A closed cluster shows its apps' worst light and its counts; open it in place.",
    capability: "Capabilities as regions, with the apps that carry their requirements inside. An app in several is drawn once, with a tab saying how many more; the others list it under \"Also carried by\".",
    focus: "One app and its direct neighbours only: who uses it on the left, what it uses on the right, outside parties below.",
    transit: "Each flow is a line and each app a station; contracts are the track. Pick a line to read its steps.",
    matrix: "Who provides (rows) to whom (columns). Each cell is lit as its contracts are lit; a cell above the diagonal runs backwards, from an app further right to one further left.",
    releases: "The system today and after each release, worked out from the requirements each one delivers.",
  };

  function render(main) {
    pulses = []; trains = [];
    if (typeof Motion !== "undefined") Motion.clear();
    const mode = lens() === "cockpit" ? (st.focus ? "focus" : group() === "none" ? "cockpit" : group()) : lens();
    const title = typeof Nav !== "undefined" ? Nav.title("Map") : "Map";
    const head = h("div", { class: "view-head" },
      h("div", {}, h("h1", {}, st.focus && lens() === "cockpit" ? `Focus: ${titleOf(st.focus)}` : title), h("p", { class: "lede", title: LEDE[mode] }, LEDE[mode])),
      h("div", { class: "spacer" }),
      typeof Nav !== "undefined" ? Nav.pageActions() : null);
    main.append(head);
    const tools = toolbar();
    if (tools) main.append(tools);  // Element.append writes a null as the text "null"
    if (D.above.length) main.append(above());
    main.append(countLine());
    if (App.section === "capabilities" && !hasCapabilities()) main.append(emptyState("No capability requirements recorded yet.", "No app carries one, and no epic lists an app against a capability, so there is nothing to group the apps by.", "/planner:requirements", "inline"));
    const board = h("div", { class: "board board-" + (lens() === "cockpit" && mode !== "cockpit" ? "cockpit board-" + mode : lens()), id: "board" });
    // The matrix's key sits beside (or, in a narrow window, under) the scrolling board and not inside it, so nothing
    // after the table adds scroll room and pushes the frozen head and row names out with the table's edge.
    const stage = lens() === "matrix" ? h("div", { class: "matrix-stage" }, board) : null;
    main.append(stage || board);
    if (!D.nodes.length) { board.append(emptyState("This vault has no apps yet.", "There is no map to draw.", "/planner:boundary")); return; }
    if (lens() === "matrix") { const m = matrix(); board.append(m.table); stage.append(m.key); }
    else if (lens() === "releases") Releases.mapLens(board);
    else if (lens() === "transit") { transit(board); highlight(App.focus); }
    else {
      if (mode === "focus") MapGroups.focus(board, st.focus);
      else if (mode === "domain" || mode === "capability") MapGroups.grouped(board, mode);
      else cockpit(board);
      highlight(App.focus);  // the board is in the page, so it has its size now
    }
  }
  /* The second row: grouping, focus and motion, for the lenses they apply to. */
  function toolbar() {
    const bar = h("div", { class: "map-tools" });
    bar.append(h("div", { class: "seg small", role: "group", "aria-label": "Lens" }, [["cockpit", "Cockpit"], ["transit", "Line map"], ["matrix", "Matrix"], ["releases", "Releases"]].map(([id, label]) =>
      h("button", { "aria-pressed": String(lens() === id), "data-lens": id, onclick: () => { st.lens = id; if (id === "transit" && FX.motion !== "trains") FX.setMotion("trains"); if (id === "cockpit" && FX.motion === "trains") FX.setMotion("trace"); rerender(); } }, label))));
    if (lens() === "cockpit") {
      bar.append(h("span", { class: "tool-label sep" }, "Group"), h("div", { class: "seg small", role: "group", "aria-label": "Group the apps" },
        [["none", "None"], ["domain", "Domain"], ["capability", "Capability"]].map(([id, label]) => h("button", { "aria-pressed": String(!st.focus && group() === id), "data-group": id,
          disabled: groupOff(id) ? true : null, title: groupOff(id) ? GROUP_OFF[id] : "",
          onclick: () => { st.group = id; st.focus = null; rerender(); } }, label))));
      if (!st.focus && group() !== "none") bar.append(h("button", { class: "chip", onclick: () => { MapGroups.all(true); rerender(); } }, "Open all"), h("button", { class: "chip", onclick: () => { MapGroups.all(false); rerender(); } }, "Close all"));
      const app = st.focus || (App.focus && APPS[App.focus] ? App.focus : null);
      if (st.focus) bar.append(h("button", { class: "chip on", onclick: () => { st.focus = null; rerender(); } }, `Leave focus on ${titleOf(st.focus)}`));
      else bar.append(h("button", { class: "chip", disabled: app ? null : true, title: app ? "" : "Pick an app first", onclick: () => { st.focus = app; rerender(); } }, app ? `Focus on ${titleOf(app)}` : "Focus on an app"));
    }
    if (lens() === "cockpit" || lens() === "transit") {
      const say = FX.MOTIONS.find(([id]) => id === FX.motion)[2];
      bar.append(h("span", { class: "tool-unit" }, h("span", { class: "tool-label sep" }, "Motion"), h("div", { class: "seg small", role: "group", "aria-label": "Motion" },
        FX.MOTIONS.map(([id, label, say]) => h("button", { "aria-pressed": String(FX.motion === id), "data-motion": id, title: say,
          onclick: () => { FX.setMotion(id); st.lens = id === "trains" ? "transit" : "cockpit"; rerender(); } }, label))),
        h("span", { class: "tool-hint" }, FX.on ? say : say.replace(/ hop by hop| ring by ring/, "") + "; Plain shows it at once")));
      if (lens() === "transit" && FX.motion === "trains" && FX.on) bar.append(h("button", { class: "chip", onclick: (ev) => { st.running = !st.running; ev.currentTarget.textContent = st.running ? "Pause trains" : "Run trains"; } }, st.running ? "Pause trains" : "Run trains"));
    }
    if (lens() === "cockpit" && !st.focus) bar.append(Layout.tools(group() === "none" ? "box" : "cluster"));
    return bar.childNodes.length ? bar : null;
  }

  /* ------------------------------------------------------------ held above the map, and the count line */
  function above() {
    const box = h("div", { class: "above" });
    if (!D.above.length) { box.append(h("span", { class: "above-label" }, "Nothing is held above the map: no open question holds the strategy, a goal or another question.")); return box; }
    box.append(h("span", { class: "above-label" }, "Held above the map"));
    for (const a of D.above) {
      const u = ASK[a.unknown], lvl = u ? u.light.level : "caution";
      box.append(h("button", { class: "cap lit " + lvl, "data-ref": a.unknown, title: `${a.unknown} holds ${a.title}${u ? ": " + u.question : ""}` },
        h("b", {}, a.unknown), h("span", {}, shorten(a.title, 22)), h("i", {}, day(a.ask_by))));
    }
    return box;
  }
  function countLine() {
    const apps = D.map.apps.length, litApps = D.map.apps.filter((a) => levelOf(a.key) !== "dark").length;
    const cons = D.map.contracts.length, litCons = D.map.contracts.filter((c) => levelOf(c.id) !== "dark").length;
    const quiet = D.map.parties.filter((p) => !NODE[p.key]).length;
    const notes = [];
    if (quiet) notes.push(`${plural(quiet, "outside party", "outside parties")} with no contract ${quiet === 1 ? "is" : "are"} not drawn: ${D.map.parties.filter((p) => !NODE[p.key]).map((p) => p.title).join(", ")}`);
    if (lens() === "cockpit" && !st.lens && big() && hasDomains() && group() === "domain") notes.push(`${plural(D.nodes.length, "box", "boxes")} is past what one drawing carries, so the apps open grouped by domain, ${manyApps() ? "each cluster closed" : "every cluster open"}; the matrix shows the full picture`);
    if (lens() === "matrix" && !st.lens) notes.push(`${plural(D.nodes.length, "box", "boxes")} and ${plural(lines(), "line")} is past what a drawing carries, so the matrix opens first; the cockpit and line map keep every app in the same place`);
    if (lens() === "transit") { const idle = D.map.contracts.filter((c) => !flowsFor(c.id).length).length; if (idle) notes.push(`${plural(idle, "contract")} no flow runs over ${idle === 1 ? "is" : "are"} drawn as dotted siding`); }
    if (!D.above.length) notes.unshift("Nothing is held above the map");
    return h("div", { class: "countline", title: `${litApps} of ${plural(apps, "app")} and ${litCons} of ${plural(cons, "contract")} lit. ${notes.join(". ")}` }, h("b", {}, `${litApps} of ${plural(apps, "app")}`), " and ", h("b", {}, `${litCons} of ${plural(cons, "contract")}`), " lit. ",
      notes.length ? h("span", { class: "hidden-note" }, notes.join(". ") + ".") : "Nothing hidden.");
  }

  /* ------------------------------------------------------------ cockpit */
  function fitSvg(root, board, w, ht, maxScale) {
    const fit = () => {
      if (!root.isConnected) { removeEventListener("resize", fit); return; }
      const r = board.getBoundingClientRect(), k = Math.max(0.15, Math.min(maxScale, (r.width - 24) / w, (r.height - 12) / ht));
      root.setAttribute("width", Math.round(w * k)); root.setAttribute("height", Math.round(ht * k));
    };
    fit();
    // one listener per board: a drag redraws the cockpit every frame and must not leave a listener behind each time
    if (board.__fit) removeEventListener("resize", board.__fit);
    board.__fit = fit; addEventListener("resize", fit);
  }
  const COCKPIT = { cw: 380, rh: 128, bandGap: 104 }, BOX_W = 176, BOX_H = 66;
  let seenView = null;  // the cockpit's frame before a drag: a drag keeps it, so the board does not rescale under the pointer
  /* Nothing sits on anything: the boxes are laid out from their cells (pins keep them a column apart), and each
     duct's lamps stand together as one bank at the first point along the duct, from its quieter end outward, that
     touches no box, caption or earlier bank (MapGroups.place). #selftest checks that no two parts intersect. */
  function cockpit(board) {
    const L = LAY = Geo.layout(COCKPIT);
    const W = BOX_W, H = BOX_H, b = L.bounds, dragging = !!Layout.live;
    let left = b.x0 - 150, right = b.x1 + W / 2 + 140, top = b.y0 - 56, flowsY = b.y1 + 92;
    if (dragging && seenView) { left = Math.min(left, seenView.left); right = Math.max(right, seenView.right); top = Math.min(top, seenView.top); flowsY = Math.max(flowsY, seenView.flowsY); }
    if (!dragging) seenView = { left, right, top, flowsY };
    const bottom = flowsY + (D.flows.length ? 70 : 0);
    const root = s("svg", { viewBox: `${left} ${top} ${right - left} ${bottom - top}`, class: "cockpit", role: "img", "aria-label": "System panel" }, board);
    fitSvg(root, board, right - left, bottom - top, 1.12);
    const defs = s("defs", {}, root);
    s("feGaussianBlur", { stdDeviation: 11 }, s("filter", { id: "ck-glow", x: "-60%", y: "-120%", width: "220%", height: "340%" }, defs));
    const lens = s("linearGradient", { id: "ck-lens", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    s("stop", { offset: "0", "stop-color": Theme.c("face-hi") }, lens); s("stop", { offset: "1", "stop-color": Theme.c("face-lo") }, lens);
    const gDucts = s("g", {}, root), gMotion = s("g", { class: "m-layer" }, root), gLamps = s("g", {}, root), gNodes = s("g", {}, root), gTop = s("g", { class: "m-top" }, root);
    Scene.reset(root, gMotion, (k) => k, gTop);
    const taken = Object.values(L.stations).map((stn) => ({ x: stn.x - W / 2, y: stn.y - H / 2, w: W, h: H }));  // what a lamp bank must stay clear of
    if (L.zoneY !== null) {
      s("line", { x1: left, x2: right, y1: L.zoneY, y2: L.zoneY, class: "zone" }, gDucts);
      for (const [text, y] of [["Our apps", L.zoneY - 12], ["Outside parties", L.zoneY + 24]]) {
        const caption = s("text", { x: right - 20, y, "text-anchor": "end", class: "zone-text" }, gDucts);
        caption.textContent = text;
        taken.push(MapGroups.drawnBox(caption, { x: right - 130, y: y - 14, w: 110, h: 18 }));
      }
    }
    if (dragging && Layout.live.spot) {
      const at = Geo.pointOf(COCKPIT, Layout.live.spot[0], Layout.live.spot[1], NODE[Layout.live.key].kind !== "app");
      s("rect", { x: at.x - W / 2, y: at.y - H / 2, width: W, height: H, rx: 10, class: "drag-ghost" }, gDucts);
    }
    for (const cor of Object.values(L.corridors)) {
      const A = L.stations[cor.a], B = L.stations[cor.b];
      const pts = Geo.route({ x: A.x, y: A.y }, { x: B.x, y: B.y }, cor.sideA), d = Geo.roundedPath(pts, 34);
      const lv = cor.contracts.map(levelOf).sort((p, q) => rank(q) - rank(p))[0];
      const duct = s("path", { d, class: "duct", "data-corridor": cor.key }, gDucts);
      Scene.edge(cor.a, cor.b, { pts, el: duct, contracts: cor.contracts });
      s("path", { d, class: "duct-hi", transform: "translate(0,2.5)" }, gDucts);
      if (lv !== "dark") s("path", { d, class: "duct-lit", stroke: LIGHT[lv].colour, "data-corridor": cor.key }, gDucts);
      // The contract lamps sit as one bank on the duct, nearer the quieter end, clear of the boxes and of every other bank.
      const busy = (x) => Object.values(x.ports).reduce((n, l) => n + l.length, 0);
      const path = busy(A) >= busy(B) ? pts : pts.slice().reverse();
      const lw = 84, lh = 22, gap = 5, bankH = cor.contracts.length * lh + (cor.contracts.length - 1) * gap;
      const spot = MapGroups.place(path, lw, bankH, taken, 0.58) || MapGroups.beside(path, lw, bankH, taken);
      if (spot.leader) s("path", { d: `M${spot.leader.x},${spot.leader.y}L${spot.at.x},${spot.at.y}`, class: "leader" }, gDucts);
      if (spot.crowded) console.warn(`[map] no free place for the lamps of ${cor.contracts.join(", ")}; drawn where they overlap`);
      taken.push(spot.r);
      cor.contracts.forEach((cid, i) => {
        const y = spot.at.y + (i - (cor.contracts.length - 1) / 2) * (lh + gap);
        lamp(gLamps, { key: cid, x: spot.at.x - lw / 2, y: y - lh / 2, w: lw, h: lh, rx: 3, label: cid, kind: "contract", title: `${cid} ${CONTRACT[cid].title}` });
      });
    }
    for (const stn of Object.values(L.stations)) {
      const n = stn.node, light = lightOf(n.key);
      const sub = n.kind !== "app" ? (n.external ? "outside provider" : "outside party") : !light || light.level === "dark" ? "settled" : shortWhy(light);
      const said = n.external && EXTERNAL[n.key] ? EXTERNAL[n.key].said : n.title;  // the contract's own words, on hover
      const el = lamp(gNodes, { key: n.key, x: stn.x - W / 2, y: stn.y - H / 2, w: W, h: H, rx: n.kind !== "app" ? 2 : 10, label: n.title, title: said, sub, kind: n.kind, clip: n.kind !== "app", emblem: Assets.emblem(n.title), icon: Icons.name(n.key) });
      Scene.node(n.key, { x: stn.x - W / 2, y: stn.y - H / 2, w: W, h: H, el });
      movable(el, n.key, board);
      if (dragging && Layout.live.key === n.key) el.classList.add("dragging");
    }
    if (D.flows.length) {
      const fw = Math.min(260, (right - left - 80) / D.flows.length - 16), fh = 50, gx = 16;
      const totalW = D.flows.length * fw + (D.flows.length - 1) * gx, x0 = (b.x0 + b.x1) / 2 - totalW / 2;
      s("text", { x: x0, y: flowsY - 14, class: "engrave" }, gNodes).textContent = "Flow pages";
      D.flows.forEach((f, i) => {
        const light = lightOf(f.key);
        lamp(gNodes, { key: f.key, x: x0 + i * (fw + gx), y: flowsY, w: fw, h: fh, rx: 6, label: E[f.key].title, kind: "flow", small: true,
          sub: `${E[f.key].id}, ${!light || light.level === "dark" ? "settled" : light.reasons.some((r) => r.kind === "stale") ? "page out of date" : shortWhy(light)}` });
      });
    }
    breathe.start();
  }
  /* ------------------------------------------------------------ moving a box */
  /* Drag a box to another cell, or focus it and press an arrow key. While it is held the cockpit, the minimap and the
     ducts are drawn with it where the pointer is, and a dashed outline shows the free cell it will settle in; on
     release it takes that cell, or stays where it was when no free cell is near. Escape lets go without moving it. */
  // the release of a drag is followed by a click on whatever is under the pointer; a pick within this long of a drop is that click
  let droppedAt = -1e9;
  const markDrop = () => { droppedAt = Date.now(); };
  const justDropped = () => Date.now() - droppedAt < 350;
  const ARROWS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  function movable(el, key, board) {
    el.setAttribute("data-movable", "1");
    el.setAttribute("aria-keyshortcuts", "ArrowLeft ArrowRight ArrowUp ArrowDown");
    el.addEventListener("pointerdown", (e) => startMove(e, key, board));
    el.addEventListener("keydown", (e) => {
      const d = ARROWS[e.key];
      if (!d || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      Layout.step(key, d[0], d[1]);
      rerender();
      refocus(key);
    });
  }
  const refocus = (key) => { const again = $(`#board g.hit[data-key="${CSS.escape(key)}"]`); if (again) again.focus(); };
  function redrawCockpit(board) {
    pulses = [];
    if (typeof Motion !== "undefined") Motion.clear();
    board.replaceChildren();
    cockpit(board);
    Minimap.refresh();
  }
  function startMove(ev, key, board) {
    if (ev.button !== 0 || ev.isPrimary === false) return;
    const outside = NODE[key].kind !== "app", origin = { x: ev.clientX, y: ev.clientY };
    const cellOf = (e) => {
      const root = $("svg.cockpit", board), pt = root.createSVGPoint();
      pt.x = e.clientX; pt.y = e.clientY;
      const p = pt.matrixTransform(root.getScreenCTM().inverse());
      return Geo.cellAt(COCKPIT, p.x, p.y, outside);
    };
    const from = cellOf(ev), grab = { col: NODE[key].col - from.col, row: NODE[key].row - from.row };
    let started = false, frame = 0, latest = ev;
    const paint = () => {
      frame = 0;
      const c = cellOf(latest);
      Layout.drag(key, Math.max(0, c.col + grab.col), Math.max(0, c.row + grab.row));
      redrawCockpit(board);
    };
    const onMove = (e) => {
      latest = e;
      if (!started) {
        if (Math.hypot(e.clientX - origin.x, e.clientY - origin.y) < 5) return;
        started = true; hideTip(); board.classList.add("moving");
      }
      if (!frame) frame = requestAnimationFrame(paint);
    };
    const finish = () => {
      removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); removeEventListener("keydown", onKey, true);
      if (frame) cancelAnimationFrame(frame);
      board.classList.remove("moving");
    };
    const onUp = (e) => {
      finish();
      if (!started) return;
      latest = e; paint();
      markDrop();
      Layout.drop(key);
      rerender();
      refocus(key);
    };
    const onKey = (e) => {
      if (e.key !== "Escape" || !started) return;
      e.stopPropagation(); finish(); Layout.endDrag(); rerender(); refocus(key);
    };
    addEventListener("pointermove", onMove); addEventListener("pointerup", onUp); addEventListener("keydown", onKey, true);
  }
  function shortWhy(light) {
    const held = light.reasons.filter((r) => r.kind === "held");
    if (light.level === "override") return "overridden";
    if (light.level === "unexamined") return "never examined";
    if (light.level === "pending") return "◷ pending approval";
    const qs = [...new Set(held.map((r) => r.unknown))];
    if (qs.length) {
      const dates = qs.map((id) => ASK[id] && ASK[id].askBy).filter(isDate).sort();
      return `${plural(qs.length, "question")}${dates.length ? ", " + day(dates[0]) : ""}`;
    }
    const state = light.reasons.find((r) => r.kind === "state");
    if (light.reasons.some((r) => r.kind === "stale")) return "page out of date";
    return state ? state.text : LIGHT[light.level].word;
  }
  function lamp(g, o) {
    // o.level draws a lamp for something attention.py does not light itself, a cluster or a shared duct: its worst light
    const light = o.level ? { level: o.level, urgency: 0.3, reasons: [] } : lightOf(o.key), level = light ? light.level : "dark", isLit = level !== "dark", colour = LIGHT[level].colour;
    // Pending approval is a ring, not a lit face: a reader's decision is not an alarm, and it must not read as one.
    const ringed = level === "pending", glows = isLit && glowOn() && !ringed;
    const grp = s("g", { class: `hit ${isLit ? "lit " + level : "dark"}`, tabindex: 0, role: "button", "data-key": o.key, "data-agg": o.level ? "1" : null,
      "aria-label": o.aria || `${o.title || o.label}: ${light ? LIGHT[level].word : "no light of its own"}. ${o.sub || ""}` }, g);
    const shape = (attrs) => o.clip ? s("path", { d: clipped(o.x, o.y, o.w, o.h, 12), ...attrs }, grp) : s("rect", { x: o.x, y: o.y, width: o.w, height: o.h, rx: o.rx, ...attrs }, grp);
    if (glows) {
      const halo = shape({ fill: colour, filter: "url(#ck-glow)", opacity: 0.32, class: "halo" });
      pulses.push({ el: halo, level, urgency: light.urgency, period: pulsePeriod(light.urgency), phase: (hash(o.key) % 1000) * 5, lastPeak: null, key: o.key });
    }
    shape({ fill: Theme.c("face-drop"), transform: "translate(0,2)" });
    const face = shape({ fill: isLit && !ringed ? colour : "url(#ck-lens)", stroke: Theme.c("face-edge"), "stroke-width": 2, class: "face" });
    if (glows) pulses[pulses.length - 1].shade = shape({ fill: "url(#ck-lens)", opacity: 0, class: "shade", "pointer-events": "none" });
    const cx = o.x + o.w / 2;
    if (o.kind === "contract") s("text", { x: cx, y: o.y + o.h / 2 + 4, "text-anchor": "middle", class: "lamp-text" }, grp).textContent = o.label;
    else {
      // A generated emblem wins; otherwise the page's own glyph (icons.js), so every box carries a picture.
      let tx = cx, room = o.small ? 30 : 22;
      if (o.emblem) { s("image", { href: o.emblem, x: o.x + 10, y: o.y + o.h / 2 - 15, width: 30, height: 30, class: "emblem" }, grp); tx = cx + 16; room = 18; }
      else if (o.icon) { Icons.put(grp, o.icon, o.x + 21, o.y + o.h / 2, 21, "node-glyph"); tx = cx + 13; room = 20; }
      const t = s("text", { x: tx, y: o.y + (o.sub ? o.h / 2 - 3 : o.h / 2 + 5), "text-anchor": "middle", class: "node-name" }, grp);
      t.textContent = shorten(o.label, room);
      if (o.small) t.style.fontSize = "13.5px";
      else if ((o.icon || o.emblem) && o.label.length > 15) t.style.fontSize = o.label.length > 18 ? "13px" : "14px";
      if (o.kind === "cluster") { t.setAttribute("y", o.y + 40); t.style.fontSize = "17px"; }
      if (o.sub) s("text", { x: tx, y: o.kind === "cluster" ? o.y + 62 : o.y + o.h / 2 + 15, "text-anchor": "middle", class: "node-sub" }, grp).textContent = shorten(o.sub, o.kind === "cluster" ? 40 : 34);
    }
    s("title", {}, grp).textContent = `${o.title || o.label}: ${light ? LIGHT[level].word : "outside party, no light of its own"}`;
    const pick = o.onpick || (() => { go(o.key, { reset: true }); if (o.kind === "app" || o.kind === "partner") Assets.theme(o.label); });
    grp.addEventListener("click", () => { if (!justDropped()) pick(); });
    grp.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    grp.addEventListener("mousemove", (e) => showTip(e, `<b>${esc(o.title || o.label)}</b>${light ? esc(LIGHT[level].word) + (light.reasons[0] ? ": " + esc(reasonText(light.reasons[0])) : "") : "No light of its own"}`));
    grp.addEventListener("mouseleave", hideTip);
    return grp;
  }
  const clipped = (x, y, w, ht, c) => `M${x + c},${y}H${x + w - c}L${x + w},${y + c}V${y + ht - c}L${x + w - c},${y + ht}H${x + c}L${x},${y + ht - c}V${y + c}Z`;
  const breathe = (() => {
    let running = false;
    function frame(now) {
      if (!pulses.length || !pulses[0].el.isConnected) { running = false; return; }
      // Calm by default: a lit lamp glows steadily, and only an overdue one breathes, slowly.
      const still = reducedMotion();
      for (const p of pulses) {
        const breathes = !still && p.level === "warning";
        const x = (now + p.phase) / (p.period * 1.6), wave = breathes ? 0.5 - 0.5 * Math.cos(2 * Math.PI * x) : 0.5;
        p.el.setAttribute("opacity", (0.14 + 0.3 * wave).toFixed(3));
        if (p.shade) p.shade.setAttribute("opacity", breathes ? (0.18 * (1 - wave)).toFixed(3) : "0");
        const peak = Math.floor(x + 0.5);
        if (breathes && p.lastPeak !== null && peak !== p.lastPeak && App.view === "map") Sound.breath(p.level, p.urgency, p.key);
        p.lastPeak = peak;
      }
      requestAnimationFrame(frame);
    }
    return { start() { if (!running) { running = true; requestAnimationFrame(frame); } } };
  })();

  /* ------------------------------------------------------------ line map */
  function transit(board) {
    const L = LAY = Geo.layout({ cw: 300, rh: 150 });
    legend(board);
    const area = h("div", { class: "transit-area" });
    board.append(area);
    const b = L.bounds, left = b.x0 - 200, right = b.x1 + 210, top = b.y0 - 110, bottom = b.y1 + 110;
    const map = s("svg", { viewBox: `${left} ${top} ${right - left} ${bottom - top}`, class: "transit", role: "img", "aria-label": "Line map of the flows" }, area);
    fitSvg(map, area, right - left, bottom - top, 1.25);
    const defs = s("defs", {}, map);
    const hatch = s("pattern", { id: "works-hatch", width: 8, height: 8, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
    s("rect", { width: 8, height: 8, fill: LIGHT.caution.colour }, hatch); s("rect", { width: 4, height: 8, fill: Theme.c("face-drop") }, hatch);
    if (L.zoneY !== null) {
      s("rect", { x: left - 4000, y: L.zoneY, width: right - left + 8000, height: bottom - L.zoneY + 4000, fill: Theme.c("duct"), opacity: 0.18 }, map);
      s("line", { x1: left - 4000, x2: right + 4000, y1: L.zoneY, y2: L.zoneY, stroke: Theme.c("rule-3"), "stroke-width": 1.5, "stroke-dasharray": "2 6" }, map);
      s("text", { x: right - 18, y: L.zoneY - 12, "text-anchor": "end", class: "zone-text" }, map).textContent = "Our apps";
      s("text", { x: right - 18, y: L.zoneY + 24, "text-anchor": "end", class: "zone-text" }, map).textContent = "Outside the fare zone: partners";
    }
    const gTrack = s("g", {}, map), gLabels = s("g", {}, map), gStations = s("g", {}, map), gWorks = s("g", {}, map);
    gPulses = s("g", {}, map);
    const gTrains = s("g", {}, map);
    for (const cor of Object.values(L.corridors)) {
      if (!cor.flows.length) s("path", { d: Geo.roundedPath(cor.centre), fill: "none", stroke: Theme.c("siding"), "stroke-width": 3, "stroke-dasharray": "1 7", "stroke-linecap": "round", "data-corridor": cor.key }, gTrack);
      for (const fid of cor.flows) {
        const colour = Geo.flowColour(Geo.FLOW_ORDER[fid]), d = Geo.roundedPath(cor.lanes[fid]);
        const g = s("g", { "data-flow": fid, class: "lane" }, gTrack);
        s("path", { d, fill: "none", stroke: colour, "stroke-width": Geo.LINE_W, "stroke-linecap": "round" }, g);
        if (["assumption", "inkling", ""].includes(E[fid].state || "")) s("path", { d, fill: "none", stroke: Theme.c("room"), "stroke-width": 2.2, "stroke-linecap": "round" }, g);
        const hit = s("path", { d, fill: "none", stroke: "transparent", "stroke-width": 16, class: "line-hit" }, g);
        hit.addEventListener("click", () => selectLine(fid));
        hit.addEventListener("mousemove", (e) => showTip(e, `<b>${esc(E[fid].title)}</b>${esc(E[fid].id)}, ${esc(E[fid].state || "no state")}. Click to follow it.`));
        hit.addEventListener("mouseleave", hideTip);
      }
    }
    for (const stn of Object.values(L.stations)) station(stn, L, gStations);
    // Nothing sits on anything: each track label takes the first spot along its corridor, either side, that touches no
    // station, name, caption or label before it; the works markers then do the same around all of them.
    const taken = $$("g.station, .zone-text", map).map((el) => { const b = el.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; });
    for (const cor of Object.values(L.corridors)) trackLabel(cor, L, gLabels, taken);
    works(L, gWorks);
    if (FX.motion === "trains" && FX.on) buildTrains(L, gTrains);
    stripEl = h("div", { class: "line-strip" });
    board.append(stripEl);
    if (st.line) selectLine(st.line);
    trainLoop.start();
  }
  // where along a track a label or marker may stand, from near its quieter end outward in steps of a twentieth
  const SWEEP = [0.66, 0.5, 0.8, 0.34, ...Array.from({ length: 19 }, (_, i) => (i + 1) / 20)];
  const bumps = (r, list) => list.some((o) => o.x < r.x + r.w && r.x < o.x + o.w && o.y < r.y + r.h && r.y < o.y + o.h);
  function trackLabel(cor, L, g, taken) {
    const ids = cor.contracts, short = ids.map((id, i) => (i === 0 ? id : id.replace(/^CON-/, ""))).join(", ");
    const A = L.stations[cor.a], B = L.stations[cor.b];
    const busy = (x) => Object.values(x.ports).reduce((n, l) => n + l.length, 0);
    const pts = busy(A) >= busy(B) ? cor.centre : cor.centre.slice().reverse();
    const lit = ids.some((id) => levelOf(id) !== "dark");
    const t = s("text", { class: "track-label" + (lit ? " lit" : ""), "data-corridor": cor.key }, g);
    t.textContent = short;
    t.addEventListener("click", () => go(ids[0], { reset: true }));
    t.addEventListener("mousemove", (e) => showTip(e, ids.map((id) => `<b>${esc(id)} ${esc(CONTRACT[id].title)}</b>${esc(CONTRACT[id].state || "no state")}, ${esc(LIGHT[levelOf(id)].word.toLowerCase())}`).join("")));
    t.addEventListener("mouseleave", hideTip);
    const total = Geo.length(pts), off = cor.width / 2 + 10;
    const spot = (f, flip) => {
      const at = Geo.pointAt(pts, total * f);
      let nx = -Math.sin(at.angle), ny = Math.cos(at.angle);
      if (ny > 0 || (Math.abs(ny) < 0.01 && nx < 0)) { nx = -nx; ny = -ny; }
      if (flip) { nx = -nx; ny = -ny; }
      const vertical = Math.abs(Math.cos(at.angle)) < 0.01;
      let x = at.x + nx * off, y = at.y + ny * off, anchor = "middle";
      if (vertical) { x = at.x + (flip ? -off : off); y = at.y + 4; anchor = flip ? "end" : "start"; } else if (Math.abs(ny) < 0.99) anchor = nx < 0 ? "end" : "start";
      return { x, y, anchor };
    };
    const tries = SWEEP.flatMap((f) => [spot(f, false), spot(f, true)]);
    const place = (sp) => { t.setAttribute("x", sp.x); t.setAttribute("y", sp.y); t.setAttribute("text-anchor", sp.anchor); const b = t.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
    let box = null;
    for (const sp of tries) { box = place(sp); if (!bumps(box, taken)) break; box = null; }
    if (!box) { box = place(tries[0]); console.warn(`[map] no free place for the label of ${ids.join(", ")}; drawn where it overlaps`); }
    taken.push(box);
  }
  function station(stn, L, g) {
    const n = stn.node, w = stn.w, ht = stn.h;
    const grp = s("g", { class: "station", tabindex: 0, role: "button", "aria-label": `${n.title}. Open details.`, "data-key": n.key }, g);
    if (n.kind !== "app") {
      s("rect", { x: stn.x - w / 2 - 2, y: stn.y - ht / 2 - 2, width: w + 4, height: ht + 4, rx: 7, fill: Theme.c("room"), stroke: Theme.c("ink-3"), "stroke-width": 3.5, class: "ring" }, grp);
      s("rect", { x: stn.x - w / 2 + 4, y: stn.y - ht / 2 + 4, width: w - 8, height: ht - 8, rx: 3, fill: "none", stroke: Theme.c("ink-3"), "stroke-width": 1.5 }, grp);
    } else s("rect", { x: stn.x - w / 2, y: stn.y - ht / 2, width: w, height: ht, rx: Math.min(w, ht) / 2, fill: Theme.c("room"), stroke: Theme.c("ink"), "stroke-width": stn.lines.size > 1 ? 4 : 3.5, class: "ring" }, grp);
    const em = Assets.emblem(n.title);
    if (em) { const size = Math.max(16, Math.min(w, ht) - 9); s("image", { href: em, x: stn.x - size / 2, y: stn.y - size / 2, width: size, height: size, class: "emblem" }, grp); }
    const free = ["L", "R", "U", "D"].filter((sd) => !stn.ports[sd].length);
    const cols = Object.values(L.stations).filter((x) => !x.outside).map((x) => x.node.col);
    const prefer = n.kind !== "app" ? ["D", "R", "L", "U"] : n.col === Math.min(...cols) ? ["L", "U", "D", "R"] : ["R", "D", "U", "L"];
    const sideFree = prefer.find((sd) => free.includes(sd)) || "D";
    stn.labelSide = sideFree;
    let x = stn.x, y = stn.y, anchor = "middle";
    if (sideFree === "L") { x = stn.x - w / 2 - 14; anchor = "end"; y = stn.y + 2; }
    if (sideFree === "R") { x = stn.x + w / 2 + 14; anchor = "start"; y = stn.y + 2; }
    if (sideFree === "U") y = stn.y - ht / 2 - 30;
    if (sideFree === "D") y = stn.y + ht / 2 + 24;
    const name = s("text", { x, y, "text-anchor": anchor, class: "station-name" }, grp);
    name.textContent = shorten(n.title, 26);  // a longer name would run into the next station's; the full one is the hover title
    s("title", {}, grp).textContent = n.external && EXTERNAL[n.key] ? EXTERNAL[n.key].said : n.title;
    const lv = levelOf(n.key);
    s("text", { x, y: y + 18, "text-anchor": anchor, class: "station-sub" + (lv !== "dark" ? " " + lv : "") }, grp).textContent =
      n.kind !== "app" ? "outside party" : lv !== "dark" ? LIGHT[lv].word.toLowerCase() : (APPS[n.key].change || "change not recorded");
    const open = () => { go(n.key, { reset: true }); Assets.theme(n.title); };
    grp.addEventListener("click", open);
    grp.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
  }
  /* Engineering works: open questions on the track or station they hold up, from each question's Blocks line. Each
     marker takes the first of its candidate spots that touches no station, name or track label, or marker before it. */
  function works(L, g) {
    const markers = [];
    const taken = $$("g.station, .track-label", g.ownerSVGElement).map((el) => { const b = el.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; });
    const area = (m) => ({ x: m.at.x - 15, y: m.at.y + m.off - 18, w: 46, h: 44 });  // the marker as drawn: board, legs, count
    const clear = (r) => !taken.some((o) => o.x < r.x + r.w && r.x < o.x + o.w && o.y < r.y + r.h && r.y < o.y + o.h);
    const choose = (key, held, spots) => {
      const m = spots.find((sp) => clear(area(sp))) || spots[0];
      if (!clear(area(m))) console.warn(`[map] no free place for the works marker on ${key}; drawn where it overlaps`);
      taken.push(area(m));
      markers.push({ held, key, at: m.at, off: m.off });
    };
    for (const cor of Object.values(L.corridors)) {
      const held = [...new Set(cor.contracts.flatMap((cid) => D.blockedBy[cid] || []))];
      const len = Geo.length(cor.centre);
      if (held.length) choose(cor.contracts[0], held, [0.34, 0.5, ...SWEEP].flatMap((f) => [1, -2.2].map((side) => ({ at: Geo.pointAt(cor.centre, len * f), off: side * (cor.width / 2 + 22) }))));
    }
    for (const stn of Object.values(L.stations)) {
      const held = (D.apps[stn.key] || { questions: [] }).questions.map((q) => q.id);
      if (!held.length) continue;
      const up = { x: stn.x - 4, y: stn.y - stn.h / 2 - 26 }, down = { x: stn.x - 4, y: stn.y + stn.h / 2 + 46 };
      const spots = (stn.labelSide !== "U" && !stn.ports.U.length ? [up, down] : [down, up]).concat([{ x: stn.x - 70, y: stn.y }, { x: stn.x + 70, y: stn.y }, { x: stn.x - 70, y: stn.y - 40 }, { x: stn.x + 70, y: stn.y - 40 }, { x: stn.x - 70, y: stn.y + 40 }, { x: stn.x + 70, y: stn.y + 40 }]);
      choose(stn.key, held, spots.map((at) => ({ at, off: 0 })));
    }
    for (const m of markers) {
      const x = m.at.x - 15, y = m.at.y + m.off - 9;
      const worst = m.held.map(unknownLevel).sort((p, q) => rank(q) - rank(p))[0];
      const grp = s("g", { class: "works", tabindex: 0, role: "button", "aria-label": `Works: ${plural(m.held.length, "open question")}` }, g);
      s("line", { x1: x + 4, y1: y + 16, x2: x + 4, y2: y + 23, stroke: Theme.c("ink-3"), "stroke-width": 2 }, grp);
      s("line", { x1: x + 26, y1: y + 16, x2: x + 26, y2: y + 23, stroke: Theme.c("ink-3"), "stroke-width": 2 }, grp);
      s("rect", { x, y, width: 30, height: 16, rx: 2, fill: "url(#works-hatch)", stroke: Theme.c("face-drop"), "stroke-width": 1.5 }, grp);
      s("circle", { cx: x + 34, cy: y, r: 9, fill: LIGHT[worst] ? LIGHT[worst].colour : LIGHT.caution.colour }, grp);
      s("text", { x: x + 34, y: y + 4, "text-anchor": "middle", fill: LIGHT[worst] ? LIGHT[worst].ink : LIGHT.caution.ink, "font-size": 11.5, "font-weight": 700 }, grp).textContent = m.held.length;
      grp.addEventListener("click", (e) => { e.stopPropagation(); go(m.key, { reset: true }); });
      grp.addEventListener("mousemove", (e) => showTip(e, m.held.map((u) => `<b>${esc(u)} ${esc(E[u] ? E[u].title : "")}</b>ask by ${esc(day(ASK[u].askBy))}`).join("")));
      grp.addEventListener("mouseleave", hideTip);
    }
  }
  function legend(board) {
    const box = h("div", { class: "line-legend" }, h("h3", {}, "Lines"));
    D.flows.forEach((f, i) => {
      const hollow = ["assumption", "inkling", ""].includes(E[f.key].state || "");
      box.append(h("button", { class: "line-btn", "aria-pressed": String(st.line === f.key), "data-flow": f.key, onclick: () => selectLine(st.line === f.key ? null : f.key) },
        h("span", { class: "swatch" + (hollow ? " hollow" : ""), style: `--c:${Geo.flowColour(i)}` }),
        h("span", {}, E[f.key].title, h("small", {}, `${E[f.key].id}, ${E[f.key].state || "no state"}`))));
    });
    if (!D.flows.length) box.append(h("p", { class: "muted" }, "No flow pages, so no lines."));
    box.append(h("div", { class: "line-keys" },
      h("span", {}, h("i", { class: "k-hollow" }), "hollow: not decided yet"), h("span", {}, h("i", { class: "k-works" }), "works: open questions hold it"),
      h("span", {}, h("i", { class: "k-siding" }), "dotted: no flow runs on it")));
    board.append(box);
  }
  function selectLine(fid) {
    st.line = fid;
    const board = $("#board"); if (!board) return;
    $$(".line-btn", board).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.flow === fid)));
    const uses = new Set(), usesCor = new Set();
    if (fid && LAY) for (const cor of Object.values(LAY.corridors)) if (cor.flows.includes(fid)) { usesCor.add(cor.key); uses.add(cor.a); uses.add(cor.b); }
    $$("g.lane", board).forEach((g) => g.setAttribute("class", "lane " + (!fid || g.dataset.flow === fid ? "on" : "dim")));
    $$("[data-corridor]", board).forEach((n) => n.classList.toggle("dim", !!fid && !usesCor.has(n.dataset.corridor)));
    $$("g.station", board).forEach((g) => g.classList.toggle("dim", !!fid && !uses.has(g.dataset.key)));
    $$("g.works", board).forEach((g) => g.classList.toggle("dim", !!fid));
    for (const t of trains) t.el.classList.toggle("dim", !!fid && t.flow !== fid);
    if (!stripEl) return;
    if (!fid) { stripEl.classList.remove("open"); return; }
    const f = FLOW[fid], i = Geo.FLOW_ORDER[fid];
    stripEl.style.setProperty("--c", Geo.flowColour(i));
    stripEl.innerHTML = "";
    stripEl.append(h("header", {}, h("b", {}, E[fid].title), h("span", {}, `${E[fid].id}, ${plural(f.steps.length, "step")}`),
      h("span", { class: "spacer" }), h("button", { class: "btn", onclick: () => { showView("flows"); Flows.select(fid, -1); } }, "Play it"),
      h("button", { class: "btn primary", onclick: () => Flows.present(fid, 0) }, "▶ Present"), h("button", { class: "btn", onclick: () => selectLine(null) }, "Close")),
      h("ol", {}, f.steps.map((stp) => h("li", { "data-step": stp.n, class: stp.contracts.length ? "" : "unlinked" },
        h("b", {}, `Step ${stp.n}${stp.contracts.length ? ", " + stp.contracts.join(", ") : ""}`), h("span", { class: "text" }, stp.short)))));
    stripEl.classList.add("open");
    go(fid, { reset: true });
  }
  function buildTrains(L, g) {
    const SPEED = 150, DWELL = 650;
    for (const f of D.flows) {
      if (!f.hops.length) continue;
      const legs = []; let prevEnd = null;
      for (const hop of f.hops) {
        const key = hop.from < hop.to ? `${hop.from}|${hop.to}` : `${hop.to}|${hop.from}`, cor = L.corridors[key];
        if (!cor || !cor.lanes[f.key]) continue;
        let pts = cor.lanes[f.key];
        if (cor.a !== hop.from) pts = pts.slice().reverse();
        if (prevEnd) { const cross = [prevEnd, pts[0]], len = Geo.length(cross); if (len > 1) legs.push({ pts: cross, dur: (len / SPEED) * 1000, step: hop.step }); }
        legs.push({ pts, dur: (Geo.length(pts) / SPEED) * 1000, step: hop.step });
        legs.push({ dwell: true, at: pts[pts.length - 1], dur: DWELL, step: hop.step, station: hop.to, angle: Geo.pointAt(pts, Geo.length(pts) - 1).angle });
        prevEnd = pts[pts.length - 1];
      }
      if (!legs.length) continue;
      legs.push({ dwell: true, at: prevEnd, dur: 1800, step: null, angle: 0 });
      const total = legs.reduce((n, l) => n + l.dur, 0), order = Geo.FLOW_ORDER[f.key];
      const el = s("g", { class: "train", "data-flow": f.key }, g);
      s("rect", { x: -13, y: -6, width: 26, height: 12, rx: 5, fill: Geo.flowColour(order), stroke: Theme.c("room"), "stroke-width": 2 }, el);
      s("rect", { x: -8, y: -2.5, width: 5, height: 5, rx: 1, fill: Theme.c("room"), opacity: 0.8 }, el);
      s("rect", { x: 1, y: -2.5, width: 5, height: 5, rx: 1, fill: Theme.c("room"), opacity: 0.8 }, el);
      trains.push({ flow: f.key, order, el, legs, total, offset: (order * 1700) % total, L });
    }
  }
  const trainLoop = (() => {
    let clock = 0, last = 0, running = false, shownStep;
    function place(t) {
      let local = (clock + t.offset) % t.total;
      for (const leg of t.legs) {
        if (local <= leg.dur) {
          if (leg !== t.leg) { t.leg = leg; if (leg.station && st.running) arrive(t, leg); }
          const p = leg.dwell ? { x: leg.at.x, y: leg.at.y, angle: leg.angle } : Geo.pointAt(leg.pts, (local / leg.dur) * Geo.length(leg.pts));
          t.el.setAttribute("transform", `translate(${p.x.toFixed(1)},${p.y.toFixed(1)}) rotate(${((p.angle * 180) / Math.PI).toFixed(1)})`);
          if (st.line === t.flow && leg.step !== shownStep && stripEl) { shownStep = leg.step; $$("li", stripEl).forEach((li) => li.classList.toggle("now", +li.dataset.step === leg.step)); }
          return;
        }
        local -= leg.dur;
      }
    }
    function arrive(t, leg) {
      const stn = t.L.stations[leg.station];
      if (!stn || reducedMotion() || (st.line && st.line !== t.flow)) return;
      const ring = s("rect", { x: stn.x - stn.w / 2, y: stn.y - stn.h / 2, width: stn.w, height: stn.h, rx: Math.min(stn.w, stn.h) / 2, fill: "none", stroke: Geo.flowColour(t.order), "stroke-width": 3, class: "arrival" }, gPulses);
      ring.style.transformOrigin = `${stn.x}px ${stn.y}px`;
      setTimeout(() => ring.remove(), 1100);
      Sound.arrival(t.order);
    }
    function frame(now) {
      if (!trains.length || !trains[0].el.isConnected) { running = false; return; }
      const dt = last ? Math.min(64, now - last) : 0; last = now;
      if (st.running && !reducedMotion()) clock += dt;
      trains.forEach(place);
      requestAnimationFrame(frame);
    }
    return { start() { trains.forEach(place); if (!running && trains.length) { running = true; last = 0; requestAnimationFrame(frame); } } };
  })();

  /* ------------------------------------------------------------ matrix */
  function matrix() {
    const byPin = (a, b) => (NODE[a].col - NODE[b].col) || (NODE[a].row - NODE[b].row) || cmp(a, b);
    const apps = D.nodes.filter((n) => n.kind === "app").map((n) => n.key).sort(byPin);
    const partners = D.nodes.filter((n) => n.kind !== "app").map((n) => n.key).sort(byPin);
    const order = Object.fromEntries(apps.map((k, i) => [k, i]));
    const cells = {};
    for (const c of D.map.contracts) for (const k of c.consumers) {
      if (k === c.provider || !(k in order)) continue;
      (cells[`${c.provider}|${k}`] = cells[`${c.provider}|${k}`] || []).push(c);
    }
    const n = apps.length, size = n <= 3 ? 96 : n <= 9 ? 70 : 46, small = size < 60;
    const focus = new Set(App.focus ? mapAnchors(App.focus) : []);
    // Column names stand at 45 degrees, read bottom-left to top-right, cut at NAME_W with the full name on hover. The
    // header row and the row names stay put while the board scrolls (map.css), so a cell far down or far right
    // still says whose it is. The head is as tall as the longest name it shows needs.
    const NAME_W = 168, longest = Math.min(NAME_W, Math.max(...apps.map((k) => titleOf(k).length * 7.4), 40));
    const table = h("table", { class: "dsm angled" + (small ? " small" : ""), style: `--cell:${size}px;--head:${Math.round(longest * 0.72 + 26)}px;--name-w:${NAME_W}px` });
    const thead = h("thead", {}, h("tr", {}, h("th", { class: "corner" }, "provides ↓", h("br"), "uses →"),
      // each name leans over its right-hand neighbours, so a column sits above the next one and its backdrop never hides it
      apps.map((k, i) => h("th", { class: "col" + (focus.has(k) ? " sel" : ""), "data-c": k, style: `z-index:${4 + n - i}` }, h("a", { "data-ref": k, title: titleOf(k) }, h("span", {}, titleOf(k)))))));
    const tbody = h("tbody");
    table.append(thead, tbody);
    const row = (p, isPartner) => h("tr", {}, h("th", { class: "row" + (focus.has(p) ? " sel" : ""), "data-r": p }, h("a", { "data-ref": p, title: titleOf(p) }, titleOf(p)), h("small", {}, isPartner ? "outside party" : (APPS[p].change || ""))),
      apps.map((k) => {
        if (k === p) return h("td", { class: "diag", "data-r": p, "data-c": k }, small ? "" : titleOf(k));
        const list = cells[`${p}|${k}`], upper = !isPartner && order[p] < order[k];
        if (!list) return h("td", { class: upper ? "upper" : "", "data-r": p, "data-c": k });
        const lv = list.map((c) => levelOf(c.id)).sort((x, y) => rank(y) - rank(x))[0];
        const held = [...new Set(list.flatMap((c) => D.blockedBy[c.id] || []))];
        const ids = list.map((c) => c.id), sel = focus.has(p) || focus.has(k) || ids.some((id) => focus.has(id));
        const btn = h("button", { class: `cell ${lv}${upper ? " backwards" : ""}`, "aria-label": `${titleOf(p)} provides ${ids.join(", ")} to ${titleOf(k)}: ${LIGHT[lv].word}`,
          onclick: () => go(ids.length > 1 ? `bundle:${ids.join(",")}|${k}` : ids[0], { reset: true }),
          onmouseenter: (e) => showTip(e, list.map((c) => `<b>${esc(c.id)} ${esc(c.title)}</b>${esc(c.state || "no state")}, ${esc(LIGHT[levelOf(c.id)].word.toLowerCase())}`).join("")), onmouseleave: hideTip },
          ids.slice(0, 3).map((id) => h("span", {}, small ? id.replace(/^CON-/, "") : id)), ids.length > 3 ? h("span", { class: "more" }, `+${ids.length - 3}`) : null);
        return h("td", { class: (upper ? "upper" : "") + (sel ? " sel" : ""), "data-r": p, "data-c": k }, btn, held.length ? h("span", { class: "holds " + held.map(unknownLevel).sort((x, y) => rank(y) - rank(x))[0] }, held.length) : null);
      }));
    apps.forEach((k) => tbody.append(row(k, false)));
    if (partners.length) { tbody.append(h("tr", { class: "grouprow" }, h("th", { class: "group" }, "Outside parties"), apps.map(() => h("td")))); partners.forEach((k) => tbody.append(row(k, true))); }
    const backwards = Object.keys(cells).filter((k) => { const [p, c] = k.split("|"); return p in order && order[p] < order[c]; });
    const coupled = Object.keys(cells).filter((k) => { const [p, c] = k.split("|"); return p < c && cells[`${c}|${p}`]; });
    const roomy = !matchMedia("(max-width: 1100px)").matches;
    return { table: h("div", { class: "matrix-wrap" }, h("div", { class: "grid-wrap" }, table)), key:
      h("details", { class: "matrix-side", open: roomy ? "" : null }, h("summary", {}, "Reading it, and the flows"), h("h3", {}, "Reading it"),
        h("ul", { class: "matrix-key" }, LEVELS.map((l) => h("li", {}, h("i", { class: "cell-sw " + l }), LIGHT[l].word + (l === "dark" ? ": settled" : ""))),
          h("li", {}, h("i", { class: "cell-sw upper-sw" }), "above the diagonal: runs backwards"), h("li", {}, h("i", { class: "holds-sw" }, "2"), "open questions holding the cell")),
        h("p", { class: "p-note" }, `${plural(D.map.contracts.length, "contract")}; ${plural(backwards.length, "cell")} ${backwards.length === 1 ? "runs" : "run"} backwards.`,
          coupled.length ? ` ${coupled.slice(0, 3).map((k) => k.split("|").map(titleOf).join(" and ")).join("; ")}${coupled.length > 3 ? ` and ${plural(coupled.length - 3, "other pair")}` : ""} provide to each other, so they cannot be designed apart.` : ""),
        h("h3", {}, "Flows"), D.flows.map((f, i) => h("button", { class: "line-btn", onmouseenter: () => flowCells(f.key, i, true), onmouseleave: () => flowCells(f.key, i, false), onclick: () => go(f.key, { reset: true, reveal: true }) },
          h("span", { class: "swatch", style: `--c:${Geo.flowColour(i)}` }), h("span", {}, E[f.key].title, h("small", {}, E[f.key].id))))) };
  }
  function flowCells(fid, i, on) {
    const used = new Set(FLOW[fid].steps.flatMap((stp) => stp.contracts));
    $$("table.dsm td").forEach((td) => {
      const btn = td.querySelector("button.cell"); if (!btn) return;
      const ids = btn.getAttribute("aria-label").match(/CON-[\w-]+|[A-Z]+-C\d+/g) || [];
      td.classList.toggle("flowlit", on && ids.some((id) => used.has(id)));
      td.style.setProperty("--fc", Geo.flowColour(i));
    });
  }

  /* ------------------------------------------------------------ picking from anywhere */
  function highlight(key) {
    const board = $("#board"); if (!board) return;
    const anchors = new Set(key ? mapAnchors(key) : []);
    if (key && CONTRACT[key]) { anchors.add(CONTRACT[key].provider); CONTRACT[key].consumers.forEach((k) => anchors.add(k)); }
    $$("g.hit, g.station", board).forEach((g) => g.classList.toggle("picked", anchors.has(g.dataset.key) || g.dataset.key === key));
    if (lens() === "cockpit" && LAY) {
      const cors = new Set(Object.values(LAY.corridors).filter((c) => (key && c.contracts.includes(key)) || (anchors.size > 1 && anchors.has(c.a) && anchors.has(c.b) && FLOW[key])).map((c) => c.key));
      $$("path.duct", board).forEach((p) => p.classList.toggle("picked", cors.has(p.dataset.corridor)));
    }
    if (lens() === "matrix" && key) { const cur = $(".grid-wrap"); if (cur) { const w = $("#board"), top = w.scrollTop, left = w.scrollLeft; rerender(); Object.assign($("#board"), { scrollTop: top, scrollLeft: left }); } }
    if (key && lens() === "cockpit" && typeof Motion !== "undefined") { if (st.focus || group() !== "none") MapGroups.highlight(key); Motion.onPick(key); }
    const bar = $(".map-tools"), fresh = toolbar();
    if (bar && fresh) bar.replaceWith(fresh);  // "Focus on <the app you picked>"
  }
  function here() { return App.focus ? mapAnchors(App.focus) : []; }
  return { render, highlight, here, lens, group, st, lamp, fitSvg, shortWhy, startBreathing: () => breathe.start(), big, COCKPIT, markDrop, justDropped, resetPulses: () => { pulses = []; }, CLUSTER_PAST };
})();
View("map", { label: "Map", title: "The system: apps, contracts, and what needs you", render: MapView.render, highlight: MapView.highlight,
  count: () => `${D.map.apps.length}·${D.map.contracts.length}`, lamp: () => { const top = litSubjects()[0]; return top ? top.light.level : null; } });
