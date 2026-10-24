/* The map. Four lenses on one pinned formation:
   - Cockpit (default): a dark panel, calm gray where all is well, a lamp lit only where attention.lights says the
     lead is needed. Lit lamps glow steadily; only an overdue one breathes. It can group the apps by domain
     (collapsible clusters) or by business capability (regions), and focus on one app with its direct neighbors
     (mapgroups.js). Picking a flow or a contract draws its path (motion.js).
   - Line map: flows are lines and apps are stations. With the Trains motion, a train runs each flow's journey.
   - Matrix: who provides (rows) to whom (columns). Past about 20 boxes or 30 lines a node-link drawing stops
     helping (Ghoniem et al. 2004), so the matrix takes over there unless the apps have domains to cluster by.
   - Releases: the system before and after each release (releases.js). */
const MapView = (() => {
  const SCALE_NODES = 20, SCALE_LINES = 30, CLUSTER_PAST = 12;
  const st = { lens: null, group: null, focus: null, open: new Set(), shut: new Set(), line: null, running: true, animate: true };
  let linePicker = null;  // the Lines key's flow picker, redrawn when a line is picked on the map
  const lines = () => D.map.contracts.reduce((n, c) => n + c.consumers.filter((k) => k !== c.provider).length, 0);
  const big = () => D.nodes.length > SCALE_NODES || lines() > SCALE_LINES;
  const hasDomains = () => D.grouping.domain;
  const hasCapabilities = () => D.grouping.capability;
  const manyApps = () => D.map.apps.length > CLUSTER_PAST;
  const lens = () => st.lens || (big() && !hasDomains() ? "matrix" : "cockpit");
  const GROUP_OFF = { domain: "No app has a business area yet, so there is nothing to group by",
    capability: "No app has requirements or epics tied to a capability yet, so there is nothing to group by" };
  const groupOff = (id) => (id === "domain" && !hasDomains()) || (id === "capability" && !hasCapabilities());
  const group = () => { const g = st.group || (manyApps() && hasDomains() ? "domain" : "none"); return groupOff(g) ? "none" : g; };
  let pulses = [], trains = [], gPulses = null, LAY = null, stripEl = null;
  const LEDE = {
    cockpit: "The apps and the contracts between them. Pick one to see what it's waiting on.",
    home: "Most of what's waiting is held up by an open question. Pick a box to see what's blocking it.",
    domain: "Apps grouped by business area. Click a group to open it.",
    capability: "Each capability with the apps that deliver it. Pick one to see what's still open on it.",
    focus: "Who uses this app and what it relies on. Pick a contract to see what's agreed.",
    transit: "Each flow is a colored line through the apps it passes; contracts are what the line runs over. Pick a flow to read its steps.",
    matrix: "Read across: each row is an app, and the cells show what it provides to the apps along the top. Pick a cell to see the contracts.",
    releases: "How the system changes with each release. Move along the timeline to see it.",
  };

  /* ------------------------------------------------------------ the key: what each look on the map means */
  const { ln, bx } = Legend;
  const KIND_LOOK = { app: "kind.app", partner: "kind.party", contract: "kind.contract", flow: "kind.flow" };
  Legend.define("kind.app", [bx({ fill: "unlit", stroke: "rule-3", rx: 6, w: 1.4 })], "Rounded box: one of our apps");
  Legend.define("kind.party", [{ k: "clip", fill: "unlit", stroke: "rule-3", w: 1.4 }], "Cut corners: a service outside the plan");
  Legend.define("kind.contract", [bx({ fill: "unlit", stroke: "rule-3", y: 4.5, height: 7, rx: 2, w: 1.2 })], "Small label: a contract, what two apps have agreed to pass each other");
  Legend.define("kind.count", [{ k: "dot", fill: "unlit", stroke: "rule-3", r: 6, w: 1.4 }, { k: "text", t: "3", fill: "ink-2", y: 11 }], "Round number: that many contracts on one short line");
  Legend.define("kind.flow", [bx({ fill: "unlit", stroke: "rule-3", y: 3.5, height: 9, rx: 2, w: 1.2 })], "Card in the Flows row: one flow, click it to play");
  Legend.define("link", [ln({ stroke: "duct", w: 4.5 })], "Dark line: a connection between two boxes; its contracts are labeled on it");
  Legend.define("link.lit", [ln({ stroke: "caution", w: 2, dash: "1.5 4.5" })], "Dotted color on a line: the most urgent status among its contracts");
  Legend.define("link.leader", [ln({ stroke: "ink-4", w: 1.2, dash: "2 3" })], "Thin dotted line: ties a contract label to its line");
  Legend.define("lane", [ln({ stroke: "line-gray", w: 4 })], "Colored line: one flow, each in its own color");
  Legend.define("lane.hollow", [ln({ stroke: "line-gray", w: 4.5 }), ln({ stroke: "room", w: 1.6 })], "Hollow line: the flow is not decided yet");
  Legend.define("siding", [ln({ stroke: "siding", w: 3, dash: "1 6" })], "Dotted gray line: no flow uses this contract");
  Legend.define("works", [bx({ stroke: "caution", dash: "3 2", w: 2, width: 19, y: 5, height: 8, rx: 1.5 }), { k: "dot", fill: "caution", x: 27, y: 4.5, r: 4.5 }], "Striped badge with a number: open questions blocking it, in the color of the most urgent");
  Legend.define("station.app", [bx({ fill: "room", stroke: "ink", w: 2.4, rx: 7 })], "Round-ended box: one of our apps, its status in words under the name");
  Legend.define("station.party", [bx({ fill: "room", stroke: "ink-3", w: 2.4, rx: 3 }), bx({ stroke: "ink-3", w: 1, x: 6, y: 5.5, width: 22, height: 5, rx: 1 })], "Double frame: an outside service");
  Legend.define("lit.words", [{ k: "text", t: "Aa", fill: "caution-text", size: 12 }], "Colored words: this is waiting; the words say why");
  Legend.define("dim", [bx({ fill: "unlit", opacity: 0.25, stroke: "rule-3", w: 1 })], "Faded: not on the flow you picked");
  Legend.define("train", [bx({ fill: "line-gray", stroke: "room", x: 8, y: 4.5, width: 18, height: 7, rx: 3.5, w: 1.4 })], "Small moving marker: runs along the flow, step by step");
  Legend.define("matrix.upper", [bx({ fill: "cell-upper", stroke: "cell-upper-edge", w: 1 })], "Shaded cell: this app depends on one further down the list, so the build order loops back");
  Legend.define("matrix.backwards", [bx({ fill: "unlit", w: 1 }), { k: "text", t: "◤", x: 9, y: 9, fill: "ink", size: 10 }], "Corner mark: this contract points backwards, to an app listed earlier");
  Legend.define("matrix.holds", [bx({ fill: "unlit", stroke: "rule-3", w: 1, width: 20 }), { k: "dot", fill: "caution", x: 26, y: 4, r: 4.5 }, { k: "text", t: "2", fill: "caution-ink", x: 26, y: 7, size: 7 }], "Number badge: open questions blocking the cell's contracts");
  Legend.define("matrix.diag", [bx({ fill: "deck-3", stroke: "rule-3", w: 1 })], "Dark cell with a name: the app itself (empty)");
  const COCKPIT_LOOKS = () => ({
    ...Legend.lampProbes((lv) => (lv === "dark" ? "g.hit.dark" : `g.hit.lit.${lv}`)),
    "kind.app": 'g.hit[data-kind="app"]', "kind.party": 'g.hit[data-kind="partner"]', "kind.contract": 'g.hit[data-kind="contract"]:not(.count-badge)',
    "kind.count": "g.count-badge", "kind.flow": 'g.hit[data-kind="flow"]',
    "link": "path.duct", "link.lit": "path.duct-lit", "link.leader": "path.leader", "picked": "g.hit.picked, path.duct.picked",
  });
  const LINE_LOOKS = () => ({
    "lane": "g.lane", "lane.hollow": "g.lane path.hollow", "siding": "path.siding", "works": "g.works",
    "station.app": "g.station.app", "station.party": "g.station.party", "lit.words": ".station-sub.warning, .station-sub.caution, .station-sub.unexamined, .track-label.lit",
    "picked": "g.station.picked", "dim": ".dim", "train": "g.train",
  });
  const MATRIX_LOOKS = () => ({
    ...Legend.lampProbes((lv) => `button.cell.${lv}`),
    "matrix.upper": "td.upper", "matrix.backwards": "button.cell.backwards", "matrix.holds": ".holds", "matrix.diag": "td.diag", "picked": "td.sel",
  });
  let KEY = null;  // the key of the map now on the page; picking something or choosing a line updates it
  const keyName = (mode) => ({ cockpit: "map-cockpit", focus: "map-focus", domain: "map-grouped", capability: "map-grouped", transit: "map-lines", matrix: "map-matrix" })[mode];
  const keyLooks = (mode) => (mode === "transit" ? LINE_LOOKS() : mode === "matrix" ? MATRIX_LOOKS()
    : mode === "domain" || mode === "capability" ? { ...COCKPIT_LOOKS(), ...MapGroups.LOOKS } : mode === "focus" ? { ...COCKPIT_LOOKS(), ...MapGroups.LOOKS_FOCUS } : COCKPIT_LOOKS());
  /* Draws with the key listening: what the drawing really uses is what the key lists. A drag redraws every frame, so the
     key starts empty each time and is only repainted when its list changed. */
  function drawn(draw) {
    KEY.seen.clear();
    KEY.within(draw);
    KEY.paint();
  }

  function render(main) {
    pulses = []; trains = [];
    if (typeof Motion !== "undefined") Motion.clear();
    const mode = lens() === "cockpit" ? (st.focus ? "focus" : group() === "none" ? "cockpit" : group()) : lens();
    const title = typeof Nav !== "undefined" ? Nav.title("Map") : "Map";
    // On the home page the work queue sits beside the map, so the map keeps its height; elsewhere the map has the column to itself.
    const queued = App.section === "home" && typeof Queue !== "undefined";
    const lede = LEDE[queued && mode === "cockpit" ? "home" : mode];
    const head = h("div", { class: "view-head" },
      h("div", {}, h("h1", {}, st.focus && lens() === "cockpit" ? `${titleOf(st.focus)} and its neighbors` : title), h("p", { class: "lede", title: lede }, lede, typeof Nav !== "undefined" ? Nav.ledeLink() : null)),
      h("div", { class: "spacer" }));
    main.append(head);
    const col = queued ? h("div", { class: "home-map" }) : main;
    const board = h("div", { class: "board board-" + (lens() === "cockpit" && mode !== "cockpit" ? "cockpit board-" + mode : lens()), id: "board" });
    wireEmptySpace(board);
    // The matrix's key sits beside (or, in a narrow window, under) the scrolling board and not inside it, so nothing
    // after the table adds scroll room and pushes the frozen head and row names out with the table's edge.
    const stage = lens() === "matrix" ? h("div", { class: "matrix-stage" }, board) : null;
    KEY = lens() === "releases" ? null : Legend.open(keyName(mode), { root: () => $("#board"), probes: keyLooks(mode) });
    // The view, grouping, focus and layout controls ride on the diagram's own bar (menus.js), under the title and lede.
    col.append(Menus.frame(diagramBar(), stage || board));
    if (queued) { const width = main.clientWidth; main.append(h("div", { class: "home-wrap" }, h("div", { class: "home-stage" + (Queue.folded(width) ? " stacked" : "") }, Queue.card(width), col))); }
    if (!D.nodes.length) { board.append(emptyState("No apps yet.", "The map fills in once a session names them.", "/vela:boundary")); return; }
    if (lens() === "releases") { Releases.mapLens(board); return; }  // the releases drawing keeps its own key
    if (lens() === "matrix") drawn(() => { const m = matrix(); board.append(m.table); stage.append(m.key); });
    else if (lens() === "transit") { drawn(() => transit(board)); highlight(App.focus); }
    else {
      if (mode === "focus") drawn(() => MapGroups.focus(board, st.focus));
      else if (mode === "domain" || mode === "capability") drawn(() => MapGroups.grouped(board, mode));
      else drawn(() => cockpit(board));
      highlight(App.focus);  // the board is in the page, so it has its size now
    }
  }
  /* The bar on the diagram: View and Group menus on the left, the focus button and the ... menu on the right, and
     the line that says what picking does between them. */
  const LENSES = [["cockpit", "System map", "every app, and what connects them"], ["transit", "Contracts only", "each flow drawn as a line along the contracts it usess"],
    ["matrix", "Dependencies", "who provides to whom, as a table"], ["releases", "Before and after", "the system before and after each release"]];
  const GROUPS = [["none", "None", "one box for each app"], ["domain", "Business area", "apps gathered by the business area they belong to"], ["capability", "Capability", "apps gathered by the capability they deliver"]];
  // a refinement inside the map (a view, a grouping) replaces the address rather than adding to the history
  const refine = () => { if (typeof Nav !== "undefined") Nav.syncHash({ replace: true }); rerender(); };
  function viewItems() {
    const onMap = App.view === "map", animating = onMap && lens() === "transit" && st.animate;
    const items = LENSES.map(([id, label, say]) => ({ id, label, say, checked: onMap && lens() === id, run: () => { st.lens = id; if (onMap) refine(); else showView("map"); } }));
    items.push({ separator: true }, { id: "animate", label: "Moving markers", say: FX.on ? "a marker runs along each flow on the contract lines" : "off while this browser asks for less motion", checkbox: true, checked: animating, disabled: !FX.on, why: "This browser asks for less motion, so nothing moves.",
      run: () => { st.animate = onMap && lens() === "transit" ? !st.animate : true; st.lens = "transit"; if (onMap) refine(); else showView("map"); } });
    return items;
  }
  function groupMenu() {
    const label = (id) => GROUPS.find(([g]) => g === id)[1];
    return Menus.menu({ id: "group", label: "Group", current: label(group()), title: "Group the apps by business area or capability",
      items: () => GROUPS.map(([id, name, say]) => ({ id, label: name, say, checked: !st.focus && group() === id, disabled: groupOff(id), why: GROUP_OFF[id], run: () => { st.group = id; st.focus = null; refine(); } })) });
  }
  function focusButton() {
    if (lens() !== "cockpit") return null;
    const app = st.focus || (App.focus && APPS[App.focus] ? App.focus : null);
    const say = st.focus ? "Back to the whole map" : "Show one app and its neighbors";
    return h("button", { class: "dmenu-btn icon", id: "focus-btn", type: "button", "aria-pressed": String(!!st.focus), "aria-disabled": st.focus || app ? null : "true", "aria-label": say,
      title: st.focus ? say : app ? `Show ${titleOf(app)} and its neighbors` : `${say}: pick an app on the map first`,
      onclick: () => { if (st.focus) { st.focus = null; refine(); } else if (app) { st.focus = app; refine(); } else toast("Pick an app on the map first, then show it with its neighbors."); } },
      Menus.icon("focus"), st.focus ? h("span", {}, "Back to the whole map") : null);
  }
  function moreItems() {
    const grouped = lens() === "cockpit" && !st.focus && group() !== "none";
    return [...(lens() === "cockpit" && !st.focus ? Layout.menuItems() : []),
      grouped ? { id: "open-all", label: "Open all groups", run: () => { MapGroups.all(true); rerender(); } } : null,
      grouped ? { id: "close-all", label: "Close all groups", run: () => { MapGroups.all(false); rerender(); } } : null];
  }
  function diagramBar() {
    const cockpit = lens() === "cockpit";
    return { left: [Nav.viewMenu(), cockpit ? groupMenu() : null], right: [Menus.noteButton(mapNotes()), Menus.keyButton(KEY), focusButton(), Nav.moreMenu(moreItems)],
      say: [cockpit ? h("span", { class: "dia-hint" }, "Pick a contract or a flow to see its path.") : null, cockpit && !st.focus ? Layout.sayEl(group() === "none" ? "box" : "cluster") : null] };
  }

  /* ------------------------------------------------------------ the notes */
  /* What the diagram has to say about itself, as sentences for the "i" in its bar (they once sat above it and pushed it down). */
  function mapNotes() {
    const apps = D.map.apps.length, litApps = D.map.apps.filter((a) => levelOf(a.key) !== "dark").length;
    const cons = D.map.contracts.length, litCons = D.map.contracts.filter((c) => levelOf(c.id) !== "dark").length;
    const quiet = D.map.parties.filter((p) => !NODE[p.key]).length;
    const notes = [];
    if (quiet) { const names = D.map.parties.filter((p) => !NODE[p.key]).map((p) => p.title); notes.push(`${names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1] : names[0]} ${quiet === 1 ? "isn't" : "aren't"} on the map because nothing connects to ${quiet === 1 ? "it" : "them"} yet`); }
    if (lens() === "cockpit" && !st.lens && big() && hasDomains() && group() === "domain") notes.push(`Too many apps to draw at once (${D.nodes.length}), so they are grouped by business area, ${manyApps() ? "each group closed" : "every group open"}; Dependencies shows them all`);
    if (lens() === "matrix" && !st.lens) notes.push(`There are too many apps to draw clearly (${D.nodes.length}, with ${plural(lines(), "connection")}), so this opens as a table. The system map still has them all`);
    if (lens() === "transit") { const idle = D.map.contracts.filter((c) => !flowsFor(c.id).length).length; if (idle) notes.push(`${plural(idle, "contract")} ${idle === 1 ? "isn't" : "aren't"} used by any flow yet, so nothing tests ${idle === 1 ? "it" : "them"} end to end`); }
    // Home already counts what is waiting once, on the top bar's lamp; a second "waiting" here, counted in apps and
    // contracts, disagreed with it (label sweep). Off Home the line says what is settled instead.
    const settled = App.section === "home" ? "" : !apps ? ""
      : litApps === apps && litCons === cons ? "Nothing is decided yet on any app or contract."
      : !litApps && !litCons ? "Every app and contract is decided."
      : `${apps - litApps} of ${plural(apps, "app")} and ${cons - litCons} of ${plural(cons, "contract")} are decided.`;
    return [settled, ...notes.map((t) => t + ".")].filter(Boolean);
  }

  /* ------------------------------------------------------------ cockpit */
  /* The drawing's viewport is the whole container, so zooming in or panning shows content wherever the container has room
     and nothing is cut at the drawing's own bounds. The scale is still the one that fits the content (never past maxScale);
     the viewBox is the content's box grown around its middle to the container's shape. */
  function fitSvg(root, board, w, ht, maxScale) {
    const [cx0, cy0, cw, ch] = root.getAttribute("viewBox").split(/\s+/).map(Number);
    const fit = () => {
      if (!root.isConnected) { removeEventListener("resize", fit); return; }
      const cs = getComputedStyle(board), pad = (a, b) => (parseFloat(cs[a]) || 0) + (parseFloat(cs[b]) || 0);
      const iw = Math.max(40, board.clientWidth - pad("paddingLeft", "paddingRight")), ih = Math.max(40, board.clientHeight - pad("paddingTop", "paddingBottom"));
      const k = Math.max(0.15, Math.min(maxScale, (iw - 24) / w, (ih - 12) / ht)), vw = iw / k, vh = ih / k;
      root.setAttribute("width", Math.round(iw)); root.setAttribute("height", Math.round(ih));
      Pan.rebase(root, `${cx0 + cw / 2 - vw / 2} ${cy0 + ch / 2 - vh / 2} ${vw} ${vh}`);
    };
    fit();
    // one listener per board: a drag redraws the cockpit every frame and must not leave a listener behind each time
    if (board.__fit) removeEventListener("resize", board.__fit);
    board.__fit = fit; addEventListener("resize", fit);
  }
  const FLOW_CARD_MIN = 240;
  const COCKPIT = Layout.FRAME, BOX_W = 176, BOX_H = 66;  // the frame the overlap rule measures in (pins.FRAME); a box no bigger than pins.BOX
  let seenView = null;  // the cockpit's frame before a drag: a drag keeps it, so the board does not rescale under the pointer
  /* Nothing sits on anything: the boxes are drawn where they are pinned (pins keep them pins.GAP apart), and each
     duct's lamps stand together as one bank at the first point along the duct, from its quieter end outward, that
     touches no box, caption or earlier bank (MapGroups.place). #selftest checks that no two parts intersect. */
  function cockpit(board) {
    const L = LAY = Geo.layout(COCKPIT), liveFlows = D.flows;
    const W = BOX_W, H = BOX_H, b = L.bounds, dragging = !!Layout.live;
    let left = b.x0 - 150, right = b.x1 + W / 2 + 140, top = b.y0 - 56, flowsY = b.y1 + 92;
    if (dragging && seenView) { left = Math.min(left, seenView.left); right = Math.max(right, seenView.right); top = Math.min(top, seenView.top); flowsY = Math.max(flowsY, seenView.flowsY); }
    if (!dragging) seenView = { left, right, top, flowsY };
    const flowCols = Math.max(1, Math.min(liveFlows.length, Math.floor((right - left - 80 + 16) / (FLOW_CARD_MIN + 16))));  // a long list wraps into rows rather than shrinking past reading
    const flowRows = Math.ceil(liveFlows.length / flowCols);
    const bottom = flowsY + (liveFlows.length ? 70 + (flowRows - 1) * 66 : 0);
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
      for (const [text, y] of [["Our apps", L.zoneY - 12], ["Outside services", L.zoneY + 24]]) {
        const caption = s("text", { x: right - 20, y, "text-anchor": "end", class: "zone-text" }, gDucts);
        caption.textContent = text;
        taken.push(MapGroups.drawnBox(caption, { x: right - 130, y: y - 14, w: 110, h: 18 }));
      }
    }
    // while held, a dashed outline shows where the box will stand when let go, if that is not under the pointer
    const land = dragging && Layout.live.land;
    if (land && land.hit) {
      const at = Geo.pointOf(COCKPIT, land.spot[0], land.spot[1], NODE[Layout.live.key].kind !== "app");
      s("rect", { x: at.x - W / 2, y: at.y - H / 2, width: W, height: H, rx: 10, class: "drag-ghost" }, gDucts);
    }
    for (const cor of Object.values(L.corridors)) {
      const A = L.stations[cor.a], B = L.stations[cor.b];
      const pts = Geo.route({ x: A.x, y: A.y }, { x: B.x, y: B.y }, cor.sideA), d = Geo.roundedPath(pts, 34);
      const lv = cor.contracts.map(levelOf).sort((p, q) => rank(q) - rank(p))[0];
      const duct = s("path", { d, class: "duct", "data-corridor": cor.key }, gDucts);
      Scene.edge(cor.a, cor.b, { pts, el: duct, contracts: cor.contracts });
      s("path", { d, class: "duct-hi", transform: "translate(0,2.5)" }, gDucts);
      Legend.saw("link");
      if (lv !== "dark") { s("path", { d, class: "duct-lit", stroke: LIGHT[lv].color, "data-corridor": cor.key }, gDucts); Legend.saw("link.lit"); }
      // The contract lamps sit as one bank on the duct, nearer the quieter end, clear of the boxes and of every other bank.
      const busy = (x) => Object.values(x.ports).reduce((n, l) => n + l.length, 0);
      const path = busy(A) >= busy(B) ? pts : pts.slice().reverse();
      const lw = 120, gap = 5, tall = cor.contracts.map((cid) => contractSize(CONTRACT[cid].title, lw).h), bankH = tall.reduce((n, x) => n + x, 0) + (cor.contracts.length - 1) * gap;
      const spot = MapGroups.place(path, lw, bankH, taken, 0.58) || MapGroups.beside(path, lw, bankH, taken);
      if (spot.leader) { s("path", { d: `M${spot.leader.x},${spot.leader.y}L${spot.at.x},${spot.at.y}`, class: "leader" }, gDucts); Legend.saw("link.leader"); }
      if (spot.crowded) console.warn(`[map] no free place for the lamps of ${cor.contracts.join(", ")}; drawn where they overlap`);
      taken.push(spot.r);
      let stack = spot.at.y - bankH / 2;
      cor.contracts.forEach((cid, i) => {
        const y = stack + tall[i] / 2; stack += tall[i] + gap;
        lamp(gLamps, { key: cid, x: spot.at.x - lw / 2, y: y - tall[i] / 2, w: lw, h: tall[i], rx: 3, label: CONTRACT[cid].title, kind: "contract", title: `${CONTRACT[cid].title} (${cid})` });
      });
    }
    for (const stn of Object.values(L.stations)) {
      const n = stn.node, light = lightOf(n.key);
      const sub = n.kind !== "app" ? "outside service" : !light || light.level === "dark" ? "decided" : shortWhy(light);
      const said = n.external && EXTERNAL[n.key] ? EXTERNAL[n.key].said : n.title;  // the contract's own words, on hover
      const el = lamp(gNodes, { key: n.key, x: stn.x - W / 2, y: stn.y - H / 2, w: W, h: H, rx: n.kind !== "app" ? 2 : 10, label: n.title, title: said, sub, kind: n.kind, clip: n.kind !== "app", emblem: Assets.emblem(n.key), icon: Icons.name(n.key) });
      Scene.node(n.key, { x: stn.x - W / 2, y: stn.y - H / 2, w: W, h: H, el });
      movable(el, n.key, board);
      if (dragging && Layout.live.key === n.key) el.classList.add("dragging");
    }
    if (liveFlows.length) {
      const gx = 16, fh = 50, fw = Math.min(260, (right - left - 80 - (flowCols - 1) * gx) / flowCols);
      const x0 = (b.x0 + b.x1) / 2 - (flowCols * fw + (flowCols - 1) * gx) / 2;
      s("text", { x: x0, y: flowsY - 14, class: "engrave" }, gNodes).textContent = "Flows";
      liveFlows.forEach((f, i) => {
        const light = lightOf(f.key);
        lamp(gNodes, { key: f.key, x: x0 + (i % flowCols) * (fw + gx), y: flowsY + Math.floor(i / flowCols) * (fh + 16), w: fw, h: fh, rx: 6, label: E[f.key].title, kind: "flow", small: true,
          sub: !light || light.level === "dark" ? "decided" : light.reasons.some((r) => r.kind === "stale") ? "needs a fresh read" : shortWhy(light), title: `${E[f.key].title} (${E[f.key].id})` });
      });
    }
    Pan.attach(board, { key: "cockpit", svg: () => $("svg.cockpit", board) });  // drag the background to pan (pan.js)
    breathe.start();
  }
  /* ------------------------------------------------------------ moving a box */
  /* Drag a box anywhere, or focus it and press an arrow key (a quarter of a cell; with Shift, a whole cell). While it
     is held the cockpit, the minimap and the ducts are drawn with it where the pointer is; on release it stays exactly
     there. Where that would cover another box, a dashed outline shows the nearest clear point on the line it is being
     dragged along, and the box lands there; the status line says so. Escape lets go without moving it. */
  // the release of a drag is followed by a click on whatever is under the pointer; a pick within this long of a drop is that click
  let droppedAt = -1e9;
  const markDrop = () => { droppedAt = Date.now(); };
  const clearDrop = () => { droppedAt = -1e9; };  // the selftest clicks in the same instant a drag check just ended
  const justDropped = () => Date.now() - droppedAt < 350;
  const ARROWS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  function movable(el, key, board) {
    el.setAttribute("data-movable", "1");
    el.setAttribute("aria-keyshortcuts", "ArrowLeft ArrowRight ArrowUp ArrowDown Shift+ArrowLeft Shift+ArrowRight Shift+ArrowUp Shift+ArrowDown");
    el.addEventListener("pointerdown", (e) => startMove(e, key, board));
    el.addEventListener("keydown", (e) => {
      const d = ARROWS[e.key];
      if (!d || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      Layout.step(key, d[0], d[1], e.shiftKey);
      rerender();
      refocus(key);
    });
  }
  const refocus = (key) => { const again = $(`#board g.hit[data-key="${CSS.escape(key)}"]`); if (again) again.focus(); };
  function redrawCockpit(board) {
    pulses = [];
    if (typeof Motion !== "undefined") Motion.clear();
    board.replaceChildren();
    drawn(() => cockpit(board));
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
    if (light.level === "unexamined") return LIGHT.unexamined.word.toLowerCase();
    if (light.level === "pending") return "◷ pending approval";
    const qs = [...new Set(held.map((r) => r.unknown))];
    if (qs.length) {
      const dates = qs.map((id) => ASK[id] && ASK[id].askBy).filter(isDate).sort();
      return `${plural(qs.length, "question")}${dates.length ? ", due " + day(dates[0]) : ""}`;
    }
    const state = light.reasons.find((r) => r.kind === "state");
    if (light.reasons.some((r) => r.kind === "stale")) return "needs a fresh read";
    return state ? state.text : LIGHT[light.level].word;
  }
  /* What a lamp says, fitted before it is drawn so its box can grow to hold the words (see LabelFit): a contract lamp is one line
     or two; a box has its name and, under it, what is waiting on it, each wrapped to the room beside its picture. */
  const CONTRACT_TEXT = { size: 11.5, weight: 700 };
  const contractSize = (label, w) => { const f = LabelFit.fit(label, w - 14, CONTRACT_TEXT); return { h: Math.max(22, Math.ceil(f.lines.length * f.lh + 8)), f }; };
  function lampText(o, lit) {
    if (o.kind === "contract") { const c = contractSize(o.label, o.w); return { f: c.f, need: c.h, tx: o.x + o.w / 2 }; }
    const left = o.x + (o.emblem ? 44 : o.icon ? 38 : 12), right = o.x + o.w - 12, room = right - left, base = o.small ? 13.5 : 15.5, weight = lit ? 700 : 500;
    // two lines at the full size if the box has the height; smaller (to the floor) before the box is made taller
    for (let z = base; ; z -= 0.5) {
      const f = LabelFit.fit(o.label, room, { size: z, floor: z, weight }), sf = o.sub ? LabelFit.fit(o.sub, room, { size: 11.5 }) : null;
      const total = f.lines.length * f.lh + (sf ? 4 + sf.lines.length * sf.lh : 0);
      if ((f.lines.length <= 2 && total + 10 <= o.h) || z <= LabelFit.FLOOR) return { f, sf, room, size: z, tx: (left + right) / 2, total, need: Math.ceil(total + 10) };
    }
  }
  function lamp(g, o) {
    // o.level draws a lamp for something attention.py does not light itself, a cluster or a shared duct: its worst light
    const light = o.level ? { level: o.level, urgency: 0.3, reasons: [] } : lightOf(o.key), level = light ? light.level : "dark", isLit = level !== "dark", color = LIGHT[level].color;
    const words = lampText(o, isLit);
    if (words.need > o.h) o = { ...o, y: o.y - (words.need - o.h) / 2, h: words.need };  // the box grows to hold its words; nothing is cut
    // Pending approval is a ring, not a lit face: a reader's decision is not an alarm, and it must not read as one.
    const ringed = level === "pending", glows = isLit && glowOn() && !ringed;
    Legend.saw("lamp." + level); Legend.saw(KIND_LOOK[o.kind]);
    const grp = s("g", { class: `hit ${isLit ? "lit " + level : "dark"}`, "data-key": o.key, "data-kind": o.kind || null, "data-agg": o.level ? "1" : null }, g);
    const shape = (attrs) => o.clip ? s("path", { d: clipped(o.x, o.y, o.w, o.h, 12), ...attrs }, grp) : s("rect", { x: o.x, y: o.y, width: o.w, height: o.h, rx: o.rx, ...attrs }, grp);
    if (glows) {
      const halo = shape({ fill: color, filter: "url(#ck-glow)", opacity: 0.32, class: "halo" });
      pulses.push({ el: halo, level, urgency: light.urgency, period: pulsePeriod(light.urgency), phase: (hash(o.key) % 1000) * 5, key: o.key });
    }
    shape({ fill: Theme.c("face-drop"), transform: "translate(0,2)" });
    const face = shape({ fill: isLit && !ringed ? color : "url(#ck-lens)", stroke: Theme.c("face-edge"), "stroke-width": 2, class: "face" });
    if (glows) pulses[pulses.length - 1].shade = shape({ fill: "url(#ck-lens)", opacity: 0, class: "shade", "pointer-events": "none" });
    const { f, sf, tx } = words, cy = o.y + o.h / 2;
    if (o.kind === "contract") LabelFit.put(grp, { x: tx, y: cy - (f.lines.length - 1) * f.lh / 2 + 0.35 * f.size, "text-anchor": "middle", class: "lamp-text" }, o.label, o.w - 14, CONTRACT_TEXT);
    else {
      // A generated emblem wins; otherwise the page's own glyph (icons.js), so every box carries a picture.
      if (o.emblem) s("image", { href: o.emblem, x: o.x + 10, y: cy - 15, width: 30, height: 30, class: "emblem" }, grp);
      else if (o.icon) Icons.put(grp, o.icon, o.x + 21, cy, 21, "node-glyph");
      const top = cy - words.total / 2, room = words.room;
      LabelFit.put(grp, { x: tx, y: top + 0.92 * f.size, "text-anchor": "middle", class: "node-name" }, o.label, room, { size: words.size, floor: words.size, weight: isLit ? 700 : 500 });
      if (o.sub) LabelFit.put(grp, { x: tx, y: top + f.lines.length * f.lh + 4 + 0.82 * sf.size, "text-anchor": "middle", class: "node-sub" }, o.sub, room, { size: 11.5 });
    }
    s("title", {}, grp).textContent = light ? `${o.title || o.label}: ${LIGHT[level].word}` : `${o.title || o.label} (outside service). Its status shows on the contracts that connect to it.`;
    const pick = o.onpick || (() => DetailsPanel.toggle(o.key, { reset: true }));
    Nodes.wire(grp, { label: o.title || o.label || o.key, aria: o.aria || `${o.title || o.label}: ${light ? LIGHT[level].word : "outside service, no status of its own"}. ${o.sub || ""}`, open: pick, guard: () => !justDropped() });
    grp.addEventListener("mousemove", (e) => showTip(e, `<b>${esc(o.title || o.label)}</b>${light ? esc(LIGHT[level].word) + (light.reasons[0] ? ": " + esc(reasonText(light.reasons[0])) : "") : "Outside service: its status shows on the contracts that connect to it"}`));
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
    s("rect", { width: 8, height: 8, fill: LIGHT.caution.color }, hatch); s("rect", { width: 4, height: 8, fill: Theme.c("face-drop") }, hatch);
    if (L.zoneY !== null) {
      s("rect", { x: left - 4000, y: L.zoneY, width: right - left + 8000, height: bottom - L.zoneY + 4000, fill: Theme.c("duct"), opacity: 0.18 }, map);
      s("line", { x1: left - 4000, x2: right + 4000, y1: L.zoneY, y2: L.zoneY, stroke: Theme.c("rule-3"), "stroke-width": 1.5, "stroke-dasharray": "2 6" }, map);
      s("text", { x: right - 18, y: L.zoneY - 12, "text-anchor": "end", class: "zone-text" }, map).textContent = "Our apps";
      s("text", { x: right - 18, y: L.zoneY + 24, "text-anchor": "end", class: "zone-text" }, map).textContent = "Outside services";
    }
    const gTrack = s("g", {}, map), gLabels = s("g", {}, map), gStations = s("g", {}, map), gWorks = s("g", {}, map);
    gPulses = s("g", {}, map);
    const gTrains = s("g", {}, map);
    for (const cor of Object.values(L.corridors)) {
      if (!cor.flows.length) { s("path", { d: Geo.roundedPath(cor.center), class: "siding", fill: "none", stroke: Theme.c("siding"), "stroke-width": 3, "stroke-dasharray": "1 7", "stroke-linecap": "round", "data-corridor": cor.key }, gTrack); Legend.saw("siding"); }
      for (const fid of cor.flows) {
        const color = Geo.flowColor(Geo.FLOW_ORDER[fid]), d = Geo.roundedPath(cor.lanes[fid]);
        const g = s("g", { "data-flow": fid, class: "lane" }, gTrack);
        s("path", { d, fill: "none", stroke: color, "stroke-width": Geo.LINE_W, "stroke-linecap": "round" }, g);
        Legend.saw("lane");
        if (["assumption", "inkling", ""].includes(E[fid].state || "")) { s("path", { d, class: "hollow", fill: "none", stroke: Theme.c("room"), "stroke-width": 2.2, "stroke-linecap": "round" }, g); Legend.saw("lane.hollow"); }
        const hit = s("path", { d, fill: "none", stroke: "transparent", "stroke-width": 16, class: "line-hit" }, g);
        Nodes.wire(hit, { label: `${E[fid].title}, a flow line on the map`, open: () => { if (st.line === fid && DetailsPanel.isPicked(fid)) { selectLine(null); DetailsPanel.clear(); } else selectLine(fid); } });  // selectLine opens the flow in the panel too; the picked line, pressed again, closes
        hit.addEventListener("mousemove", (e) => showTip(e, `<b>${esc(E[fid].title)}</b>${esc(E[fid].state ? stateWord(E[fid].state) : "No status written down yet")}. Click to follow it.`));
        hit.addEventListener("mouseleave", hideTip);
      }
    }
    const names = [];  // the station names placed so far, which a later name keeps clear of
    for (const stn of Object.values(L.stations)) station(stn, L, gStations, names);
    // Nothing sits on anything: each track label takes the first spot along its corridor, either side, that touches no
    // station, name, caption or label before it; the works markers then do the same around all of them.
    const taken = $$("g.station, .zone-text", map).map((el) => { const b = el.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; });
    for (const cor of Object.values(L.corridors)) trackLabel(cor, L, gLabels, taken);
    works(L, gWorks);
    if (st.animate && FX.on) buildTrains(L, gTrains);
    stripEl = h("div", { class: "line-strip" });
    board.append(stripEl);
    if (st.line) selectLine(st.line);
    Pan.attach(area, { key: "transit", svg: () => $("svg.transit", area) });
    trainLoop.start();
  }
  // where along a track a label or marker may stand, from near its quieter end outward in steps of a twentieth
  const SWEEP = [0.66, 0.5, 0.8, 0.34, ...Array.from({ length: 19 }, (_, i) => (i + 1) / 20)];
  const bumps = (r, list) => list.some((o) => o.x < r.x + r.w && r.x < o.x + o.w && o.y < r.y + r.h && r.y < o.y + o.h);
  function trackLabel(cor, L, g, taken) {
    const ids = cor.contracts, said = ids.length > 1 ? `${CONTRACT[ids[0]].title} +${ids.length - 1}` : CONTRACT[ids[0]].title;
    const A = L.stations[cor.a], B = L.stations[cor.b];
    const busy = (x) => Object.values(x.ports).reduce((n, l) => n + l.length, 0);
    const pts = busy(A) >= busy(B) ? cor.center : cor.center.slice().reverse();
    const lit = ids.some((id) => levelOf(id) !== "dark");
    const t = LabelFit.put(g, { class: "track-label" + (lit ? " lit" : ""), "data-corridor": cor.key }, said, 200, { size: 12.5 });
    if (lit) Legend.saw("lit.words");
    Nodes.wire(t, { label: ids.length > 1 ? `${ids.length} contracts: ${ids.map((id) => CONTRACT[id].title).join(", ")}` : CONTRACT[ids[0]].title, key: ids.length > 1 ? `bundle:${ids.join(",")}|${titleOf(cor.b)}` : ids[0] });
    t.addEventListener("mousemove", (e) => showTip(e, ids.map((id) => `<b>${esc(CONTRACT[id].title)}</b>${esc(stateWord(CONTRACT[id].state) || "No status written down yet")}, ${esc(LIGHT[levelOf(id)].word.toLowerCase())}`).join("")));
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
    const place = (sp) => { LabelFit.place(t, sp.x, sp.y, sp.anchor); const b = t.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
    let box = null;
    for (const sp of tries) { box = place(sp); if (!bumps(box, taken)) break; box = null; }
    if (!box) { box = place(tries[0]); console.warn(`[map] no free place for the label of ${ids.join(", ")}; drawn where it overlaps`); }
    taken.push(box);
  }
  function station(stn, L, g, names) {
    const n = stn.node, w = stn.w, ht = stn.h;
    const grp = s("g", { class: "station " + (n.kind !== "app" ? "party" : "app"), "data-key": n.key }, g);
    Legend.saw(n.kind !== "app" ? "station.party" : "station.app");
    if (n.kind !== "app") {
      s("rect", { x: stn.x - w / 2 - 2, y: stn.y - ht / 2 - 2, width: w + 4, height: ht + 4, rx: 7, fill: Theme.c("room"), stroke: Theme.c("ink-3"), "stroke-width": 3.5, class: "ring" }, grp);
      s("rect", { x: stn.x - w / 2 + 4, y: stn.y - ht / 2 + 4, width: w - 8, height: ht - 8, rx: 3, fill: "none", stroke: Theme.c("ink-3"), "stroke-width": 1.5 }, grp);
    } else s("rect", { x: stn.x - w / 2, y: stn.y - ht / 2, width: w, height: ht, rx: Math.min(w, ht) / 2, fill: Theme.c("room"), stroke: Theme.c("ink"), "stroke-width": stn.lines.size > 1 ? 4 : 3.5, class: "ring" }, grp);
    const em = Assets.emblem(n.key);
    if (em) { const size = Math.max(16, Math.min(w, ht) - 9); s("image", { href: em, x: stn.x - size / 2, y: stn.y - size / 2, width: size, height: size, class: "emblem" }, grp); }
    const free = ["L", "R", "U", "D"].filter((sd) => !stn.ports[sd].length);
    const cols = Object.values(L.stations).filter((x) => !x.outside).map((x) => x.node.col);
    // the leftmost apps name themselves on the left: within half a column of the leftmost, since a box may stand between cells
    const prefer = n.kind !== "app" ? ["D", "R", "L", "U"] : n.col - Math.min(...cols) < 0.5 ? ["L", "U", "D", "R"] : ["R", "D", "U", "L"];
    const sides = prefer.filter((sd) => free.includes(sd));
    const name = LabelFit.put(grp, { class: "station-name" }, n.title, 170, { size: 17, weight: 600 });  // a long name wraps to a second line, so it never runs into the next station's
    s("title", {}, grp).textContent = n.external && EXTERNAL[n.key] ? EXTERNAL[n.key].said : n.title;
    const lv = levelOf(n.key);
    if (["warning", "caution", "unexamined"].includes(lv)) Legend.saw("lit.words");
    const sub = s("text", { class: "station-sub" + (lv !== "dark" ? " " + lv : "") }, grp);
    sub.textContent = n.kind !== "app" ? "outside service" : lv !== "dark" ? LIGHT[lv].word.toLowerCase() : (APPS[n.key].change ? stateWord(APPS[n.key].change).toLowerCase() : "change not recorded");
    // The name takes the first free side whose words touch no other station and no name placed before it: boxes
    // dropped between cells can stand closer than a column, and a name on the near side would run into the neighbor.
    const put = (side) => {
      let x = stn.x, y = stn.y, anchor = "middle";
      const extra = (name.__lines.lines.length - 1) * name.__lines.lh;  // a name of two lines pushes what is under it down
      if (side === "L") { x = stn.x - w / 2 - 14; anchor = "end"; y = stn.y + 2 - extra / 2; }
      if (side === "R") { x = stn.x + w / 2 + 14; anchor = "start"; y = stn.y + 2 - extra / 2; }
      if (side === "U") y = stn.y - ht / 2 - 30 - extra;
      if (side === "D") y = stn.y + ht / 2 + 24;
      for (const [t, dy] of [[name, 0], [sub, 18 + extra]]) LabelFit.place(t, x, y + dy, anchor);
      const a = name.getBBox(), b = sub.getBBox(), x0 = Math.min(a.x, b.x), y0 = Math.min(a.y, b.y);
      return { x: x0, y: y0, w: Math.max(a.x + a.width, b.x + b.width) - x0, h: Math.max(a.y + a.height, b.y + b.height) - y0 };
    };
    const others = Object.values(L.stations).filter((o) => o.key !== n.key).map((o) => ({ x: o.x - o.w / 2 - 2, y: o.y - o.h / 2 - 2, w: o.w + 4, h: o.h + 4 }));
    const blocked = (r) => bumps(r, others) || bumps(r, names);
    let side = sides.find((sd) => !blocked(put(sd)));
    if (!side) {
      side = sides[0] || "D";
      if (sides.length > 1) console.warn(`[map] no side of ${n.title} has room for its name on the line map; drawn where it overlaps`);
    }
    stn.labelSide = side;
    names.push(put(side));
    const open = () => DetailsPanel.toggle(n.key, { reset: true });
    Nodes.wire(grp, { label: n.title, aria: `${n.title}. Open details.`, open });
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
      const len = Geo.length(cor.center);
      if (held.length) choose(cor.contracts[0], held, [0.34, 0.5, ...SWEEP].flatMap((f) => [1, -2.2].map((side) => ({ at: Geo.pointAt(cor.center, len * f), off: side * (cor.width / 2 + 22) }))));
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
      const grp = s("g", { class: "works" }, g);
      Legend.saw("works");
      s("line", { x1: x + 4, y1: y + 16, x2: x + 4, y2: y + 23, stroke: Theme.c("ink-3"), "stroke-width": 2 }, grp);
      s("line", { x1: x + 26, y1: y + 16, x2: x + 26, y2: y + 23, stroke: Theme.c("ink-3"), "stroke-width": 2 }, grp);
      s("rect", { x, y, width: 30, height: 16, rx: 2, fill: "url(#works-hatch)", stroke: Theme.c("face-drop"), "stroke-width": 1.5 }, grp);
      s("circle", { cx: x + 34, cy: y, r: 9, fill: LIGHT[worst] ? LIGHT[worst].color : LIGHT.caution.color }, grp);
      s("text", { x: x + 34, y: y + 4, "text-anchor": "middle", fill: LIGHT[worst] ? LIGHT[worst].ink : LIGHT.caution.ink, "font-size": 11.5, "font-weight": 700 }, grp).textContent = m.held.length;
      Nodes.wire(grp, { label: `Blocking ${titleOf(m.key)}: ${plural(m.held.length, "open question")}`, key: m.key, stop: true });
      grp.addEventListener("mousemove", (e) => showTip(e, m.held.map((u) => `<b>${esc(E[u] ? E[u].title : u)}</b>answer needed by ${esc(day(ASK[u].askBy))}`).join("")));
      grp.addEventListener("mouseleave", hideTip);
    }
  }
  function legend(board) {
    const box = h("div", { class: "line-legend" }, h("h3", {}, "Flows"));
    if (D.flows.length) {
      linePicker = FlowPicker.make({ current: () => st.line, onPick: (key) => selectLine(key), none: "All flows", label: "Show flow",
        swatch: (key) => Geo.flowColor(Geo.FLOW_ORDER[key]) });
      box.append(linePicker);
    }
    if (!D.flows.length) box.append(h("p", { class: "muted" }, "No flows written yet, so there are no lines to draw."));
    board.append(box);
  }
  function selectLine(fid) {
    st.line = fid;
    const board = $("#board"); if (!board) return;
    if (linePicker) linePicker.refresh();
    const uses = new Set(), usesCor = new Set();
    if (fid && LAY) for (const cor of Object.values(LAY.corridors)) if (cor.flows.includes(fid)) { usesCor.add(cor.key); uses.add(cor.a); uses.add(cor.b); }
    $$("g.lane", board).forEach((g) => g.setAttribute("class", "lane " + (!fid || g.dataset.flow === fid ? "on" : "dim")));
    $$("[data-corridor]", board).forEach((n) => n.classList.toggle("dim", !!fid && !usesCor.has(n.dataset.corridor)));
    $$("g.station", board).forEach((g) => g.classList.toggle("dim", !!fid && !uses.has(g.dataset.key)));
    $$("g.works", board).forEach((g) => g.classList.toggle("dim", !!fid));
    for (const t of trains) t.el.classList.toggle("dim", !!fid && t.flow !== fid);
    if (KEY) { KEY.set("dim", !!$(".dim", board)); KEY.paint(); }
    if (!stripEl) return;
    if (!fid) { stripEl.classList.remove("open"); return; }
    const f = FLOW[fid], i = Geo.FLOW_ORDER[fid];
    stripEl.style.setProperty("--c", Geo.flowColor(i));
    stripEl.innerHTML = "";
    stripEl.append(h("header", {}, h("b", {}, E[fid].title), h("span", {}, idTag(E[fid].id), ` ${plural(f.steps.length, "step")}`),
      h("span", { class: "spacer" }), h("button", { class: "btn", onclick: () => { showView("flows"); Flows.select(fid, -1); } }, "Step through"),
      h("button", { class: "btn primary", onclick: () => Flows.present(fid, 0) }, "▶ Present"), h("button", { class: "btn", onclick: () => selectLine(null) }, "Close")),
      h("ol", {}, f.steps.map((stp) => h("li", { "data-step": stp.n, class: stp.contracts.length ? "" : "unlinked" },
        h("b", { title: stp.contracts.join(", ") || null }, `Step ${stp.n}${stp.contracts.length ? ", over " + stp.contracts.map((id) => (CONTRACT[id] ? CONTRACT[id].title : id)).join(", ") : ""}`), h("span", { class: "text" }, stp.short)))));
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
      Legend.saw("train");
      s("rect", { x: -13, y: -6, width: 26, height: 12, rx: 5, fill: Geo.flowColor(order), stroke: Theme.c("room"), "stroke-width": 2 }, el);
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
      const ring = s("rect", { x: stn.x - stn.w / 2, y: stn.y - stn.h / 2, width: stn.w, height: stn.h, rx: Math.min(stn.w, stn.h) / 2, fill: "none", stroke: Geo.flowColor(t.order), "stroke-width": 3, class: "arrival" }, gPulses);
      ring.style.transformOrigin = `${stn.x}px ${stn.y}px`;
      setTimeout(() => ring.remove(), 1100);
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
    // Column names stand at 45 degrees, read bottom-left to top-right, the head as tall as the longest whole name needs. The
    // header row and the row names stay put while the board scrolls (map.css), so a cell far down or far right
    // still says whose it is. The head is as tall as the longest name it shows needs.
    const longest = Math.ceil(Math.max(...apps.map((k) => LabelFit.width(titleOf(k), 13)), 40)) + 4, NAME_W = longest;
    const table = h("table", { class: "dsm angled" + (small ? " small" : ""), style: `--cell:${size}px;--head:${Math.round(longest * 0.72 + 26)}px;--name-w:${NAME_W}px` });
    const thead = h("thead", {}, h("tr", {}, h("th", { class: "corner" }, "rows provide", h("br"), "to columns"),
      // each name leans over its right-hand neighbors, so a column sits above the next one and its backdrop never hides it
      apps.map((k, i) => h("th", { class: "col" + (focus.has(k) ? " sel" : ""), "data-c": k, style: `z-index:${4 + n - i}` }, h("a", { "data-ref": k, title: titleOf(k) }, h("span", {}, titleOf(k)))))));
    const tbody = h("tbody");
    table.append(thead, tbody);
    const row = (p, isPartner) => h("tr", {}, h("th", { class: "row" + (focus.has(p) ? " sel" : ""), "data-r": p }, h("a", { "data-ref": p, title: titleOf(p) }, titleOf(p)), h("small", {}, isPartner ? "outside service" : stateWord(APPS[p].change) || "")),
      apps.map((k) => {
        if (k === p) { Legend.saw("matrix.diag"); return h("td", { class: "diag", "data-r": p, "data-c": k }, small ? "" : titleOf(k)); }
        const list = cells[`${p}|${k}`], upper = !isPartner && order[p] < order[k];
        if (upper) Legend.saw("matrix.upper");
        if (!list) return h("td", { class: upper ? "upper" : "", "data-r": p, "data-c": k });
        const lv = list.map((c) => levelOf(c.id)).sort((x, y) => rank(y) - rank(x))[0];
        const held = [...new Set(list.flatMap((c) => D.blockedBy[c.id] || []))];
        const ids = list.map((c) => c.id), sel = focus.has(p) || focus.has(k) || ids.some((id) => focus.has(id));
        Legend.saw("lamp." + lv);
        if (upper) Legend.saw("matrix.backwards");
        if (held.length) Legend.saw("matrix.holds");
        if (sel) Legend.saw("picked");
        const btn = h("button", { class: `cell ${lv}${upper ? " backwards" : ""}`, "aria-label": `${titleOf(p)} provides ${ids.map((id) => CONTRACT[id].title).join(", ")} to ${titleOf(k)}: ${LIGHT[lv].word}`,
          onclick: () => go(ids.length > 1 ? `bundle:${ids.join(",")}|${k}` : ids[0], { reset: true }),
          onmouseenter: (e) => showTip(e, list.map((c) => `<b>${esc(c.title)}</b>${esc(stateWord(c.state) || "No status written down yet")}, ${esc(LIGHT[levelOf(c.id)].word.toLowerCase())}`).join("")), onmouseleave: hideTip },
          ids.length === 1 ? h("span", { title: ids[0] }, CONTRACT[ids[0]].title) : h("span", { title: ids.map((id) => CONTRACT[id].title).join(", ") }, small ? `${ids.length}×` : `${ids.length} contracts`));
        return h("td", { class: (upper ? "upper" : "") + (sel ? " sel" : ""), "data-r": p, "data-c": k }, btn, held.length ? h("span", { class: "holds " + held.map(unknownLevel).sort((x, y) => rank(y) - rank(x))[0] }, held.length) : null);
      }));
    apps.forEach((k) => tbody.append(row(k, false)));
    if (partners.length) { tbody.append(h("tr", { class: "grouprow" }, h("th", { class: "group" }, "Outside services"), apps.map(() => h("td")))); partners.forEach((k) => tbody.append(row(k, true))); }
    const backwards = Object.keys(cells).filter((k) => { const [p, c] = k.split("|"); return p in order && order[p] < order[c]; });
    const coupled = Object.keys(cells).filter((k) => { const [p, c] = k.split("|"); return p < c && cells[`${c}|${p}`]; });
    const roomy = !matchMedia("(max-width: 1100px)").matches;
    return { table: h("div", { class: "matrix-wrap" }, h("div", { class: "grid-wrap" }, table)), key:
      h("details", { class: "matrix-side", open: roomy ? "" : null }, h("summary", {}, "The counts, and the flows"), h("h3", {}, "Counts"),
        // the pair that has to be designed together is the line that matters, so it leads; the counts follow
        h("p", { class: "p-note" }, coupled.length ? `${coupled.slice(0, 3).map((k) => k.split("|").map(titleOf).join(" and ")).join("; ")}${coupled.length > 3 ? ` and ${plural(coupled.length - 3, "other pair")}` : ""} depend on each other, so design them together. ` : "",
          `${plural(D.map.contracts.length, "contract")}; ${backwards.length ? `${backwards.length} ${backwards.length === 1 ? "points" : "point"} backwards, to an app listed earlier` : "none points backwards"}.`),
        h("h3", {}, "Flows"), D.flows.map((f, i) => h("button", { class: "line-btn", onmouseenter: () => flowCells(f.key, i, true), onmouseleave: () => flowCells(f.key, i, false), onclick: () => go(f.key, { reset: true, reveal: true }) },
          h("span", { class: "swatch", style: `--c:${Geo.flowColor(i)}` }), h("span", {}, E[f.key].title, h("small", { class: "id-tag" }, E[f.key].id))))) };
  }
  function flowCells(fid, i, on) {
    const used = new Set(FLOW[fid].steps.flatMap((stp) => stp.contracts));
    $$("table.dsm td").forEach((td) => {
      const btn = td.querySelector("button.cell"); if (!btn) return;
      const ids = btn.getAttribute("aria-label").match(/CON-[\w-]+|[A-Z]+-C\d+/g) || [];
      td.classList.toggle("flowlit", on && ids.some((id) => used.has(id)));
      td.style.setProperty("--fc", Geo.flowColor(i));
    });
  }

  /* ------------------------------------------------------------ picking from anywhere */
  function highlight(key) {
    const board = $("#board"); if (!board) return;
    const anchors = new Set(key ? mapAnchors(key) : []);
    if (key && CONTRACT[key]) { anchors.add(CONTRACT[key].provider); CONTRACT[key].consumers.forEach((k) => anchors.add(k)); }
    // a question or a person holds up what its Blocks lines name: those apps, and the contracts between them, light too
    const holds = key && (UNKNOWN[key] || PlanDetails.whoOf(key)) ? PlanDetails.held(key) : null;
    if (holds) { holds.apps.forEach((k) => anchors.add(k)); holds.contracts.forEach((k) => anchors.add(k)); }
    $$("g.hit, g.station", board).forEach((g) => g.classList.toggle("picked", anchors.has(g.dataset.key) || g.dataset.key === key));
    if (lens() === "cockpit" && LAY) {
      const cors = new Set(Object.values(LAY.corridors).filter((c) => (key && c.contracts.includes(key)) || (holds && c.contracts.some((x) => holds.contracts.has(x))) || (anchors.size > 1 && anchors.has(c.a) && anchors.has(c.b) && FLOW[key])).map((c) => c.key));
      $$("path.duct", board).forEach((p) => p.classList.toggle("picked", cors.has(p.dataset.corridor)));
    }
    if (lens() === "matrix" && key) { const cur = $(".grid-wrap"); if (cur) { const w = $("#board"), top = w.scrollTop, left = w.scrollLeft; rerender(); Object.assign($("#board"), { scrollTop: top, scrollLeft: left }); } }
    if (key && lens() === "cockpit" && typeof Motion !== "undefined") { if (st.focus || group() !== "none") MapGroups.highlight(key); Motion.onPick(key); }
    if (!key && typeof Motion !== "undefined" && Motion.active) Motion.clear();  // nothing picked, nothing traced: the trace goes with its pick
    if (KEY && KEY.host && KEY.host.isConnected && lens() !== "matrix") { KEY.set("picked", !!$("g.hit.picked, path.duct.picked, g.station.picked, .focus-center", board), mode() === "focus" ? "White outline: the app in focus, and what you pick" : null); KEY.paint(); }
    const focusBtn = $("#focus-btn"), fresh = focusButton();
    if (focusBtn && fresh) focusBtn.replaceWith(fresh);  // "Show <the app you picked> and its neighbors"
  }
  /* Empty space on the map goes back to the page's summary, as in a design; a drag that panned the map does not. */
  function wireEmptySpace(board) {
    let down = null;
    board.addEventListener("pointerdown", (ev) => { down = { x: ev.clientX, y: ev.clientY }; });
    board.addEventListener("click", (ev) => {
      if (ev.target.closest("[data-node], button, a, summary, input, select, .dmenu, .legend, td, th")) return;
      if (down && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 4) return;
      DetailsPanel.clear();
    });
  }
  DetailsPanel.register("map", {
    view: "map", live: () => D.nodes.length > 0,
    rootLabel: () => (App.section === "home" ? "What's waiting" : "The map"),
    summary: () => {
      return [...Panel.homeNodes({ queue: false }), PlanDetails.aboutSection()].filter(Boolean);
    },
    owns: PlanDetails.owns, detail: (k) => PlanDetails.detail(k, "map"), label: PlanDetails.label, open: (k) => PlanDetails.openFor(k, "map"),
    waiting: (k) => PlanDetails.waitingTab(k, "queue"), waitingCount: () => PlanDetails.waitingCount("queue"), focus: (k) => highlight(k || ""),
  });
  const mode = () => (lens() === "cockpit" ? (st.focus ? "focus" : group() === "none" ? "cockpit" : group()) : lens());
  function here() { return App.focus ? mapAnchors(App.focus) : []; }
  return { LOOKS: { cockpit: COCKPIT_LOOKS, focus: () => ({ ...COCKPIT_LOOKS(), ...MapGroups.LOOKS_FOCUS }) }, render, highlight, here, lens, group, viewItems, st, lamp, contractSize, fitSvg, shortWhy, startBreathing: () => breathe.start(), big, COCKPIT, markDrop, clearDrop, justDropped, resetPulses: () => { pulses = []; }, CLUSTER_PAST };
})();
View("map", { label: "Map", title: "The apps, the contracts between them, and what's waiting", render: MapView.render, highlight: MapView.highlight,
  count: () => `${D.map.apps.length}·${D.map.contracts.length}`, lamp: () => { const top = litSubjects()[0]; return top ? top.light.level : null; } });
