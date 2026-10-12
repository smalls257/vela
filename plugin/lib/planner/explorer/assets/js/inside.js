/* Inside this app: the C4 drill-down, from the vault's boundary into the team's own design (DESIGN-INSIDE.md).

   - Context: the app in the middle, its contracts in and out, the outside parties: the map's Focus drawing.
   - Containers: the app page's main containers table, each container joined to the neighbours its contracts reach;
     the arrows between containers are read from the page's flowchart, best effort, and dashed.
   - Components: the team's tech design, given to build.py with --design. Each component is a box, Depends on is a
     labelled arrow, Exposes sits on the box's lower edge, and each Integration point is a stub out to the level 1
     neighbour it reaches. Beside it, the design's own sections, in tabs.
   - Build plan: the team's work breakdown beside the design (plan.js draws it; build.py --breakdown, or found beside the
     design). A requirement row or epic criterion says which story builds it, next to which component owns it.

   The vault and the design meet in both directions. A component's panel lists the vault IDs it owns, each with
   where it was found and, while the format records no trace, marked inferred. A requirement row, contract or epic
   criterion in the vault says which component owns it, or that none does: grey when a gap acknowledges it, amber
   when nobody has. A design question that challenges a vault item lights that item in the "needs you" lamp, with
   its scenario, until the vault records the challenge. This lamp is the design's, not attention.lights, and every
   place it shows says so; the map's lamps stay attention's alone.

   Nothing here fills a hole with a guess it does not name: what the reader could not read is a count on the
   design's chip, never hidden, opening the list with line numbers. With no design loaded, level 3 says how to load
   it, and levels 1 and 2 still draw from the vault.

   Deep link: #inside=APP-booking&level=components&tab=flows, or &level=plan. Double-click an app on the map to go inside it. */
const Inside = (() => {
  const DES = D.designs || {}, CONT = D.containers || {};
  const LEVELS = [["context", "Context"], ["containers", "Containers"], ["components", "Components"], ["plan", "Build plan"]];
  const TABS = [["trace", "Trace"], ["data", "Data model"], ["api", "API contracts"], ["flows", "Key flows"], ["stack", "Tech stack"], ["nfrs", "NFRs"],
    ["constraints", "Constraints"], ["risks", "Risks"], ["adrs", "ADRs"], ["ops", "Operations"], ["glossary", "Glossary"]];
  const st = { app: "", level: "context", tab: "trace", step: {}, playing: null, zoom: {} };
  const VAULT_ID = /\b(?:CAP-\d{3}(?:\.FR\d+(?:@APP-[a-z0-9-]+)?)?|EPC-\d{3}(?:\.AC\d+)?|CON-\d{3}|UNK-\d{3}|FLO-\d{3}|CST-\d+|INI-\d{3}|APP-[a-z0-9-]+|R-\d{2}|PTY-\d{2,3}|SV-\d{2,3})\b/g;
  const appTitle = (k) => titleOf(k);
  const design = (k) => DES[k] || null;
  const base = (id) => id.split("@")[0];
  const appOfId = (id) => (APP_BY_ID[id] ? APP_BY_ID[id].key : null);
  const keyOfApp = (x) => (APPS[x] ? x : appOfId(x));
  /* Where a vault ID the design cites opens: an allocated row at its requirement, a criterion at its epic (when the
     epic has that many), the initiative at the home; null when the vault holds no such thing. */
  function vaultKey(id) {
    const ac = id.match(/^(EPC-\d{3})\.AC(\d+)$/);
    if (ac) { const k = keyForId(ac[1]); return ent(k) && +ac[2] <= (D.epicCriteria[k] || []).length ? k : null; }
    if (id === D.initiative) return "lights";
    const k = keyForId(base(id));
    return ent(k) ? k : null;
  }

  /* ------------------------------------------------------------ the vault and the design, both ways */
  const OWNERS = {}, UNTRACED = {}, CHALLENGED = {};
  for (const [app, d] of Object.entries(DES)) {
    for (const [component, list] of Object.entries(d.trace)) for (const e of list) for (const k of new Set([e.id, base(e.id)])) (OWNERS[k] = OWNERS[k] || []).push({ app, component, via: e.via, id: e.id });
    for (const t of d.resolved.untraced) for (const k of new Set([t, base(t)])) (UNTRACED[k] = UNTRACED[k] || []).push({ app, id: t, gap: d.resolved.acknowledged[t] || null });
    for (const c of d.challenges) if (!c.recorded) (CHALLENGED[c.id] = CHALLENGED[c.id] || []).push(Object.assign({ app }, c));
  }
  /* The vault item a design question challenges, lit "needs you" until the vault records it. */
  const challenge = (key) => { const e = ent(key); return (e && e.id && CHALLENGED[e.id]) || CHALLENGED[key] || null; };
  const designWord = (app) => `${appTitle(app)} design`;
  const sourceWord = (d) => (d.trace_source === "recorded" ? "recorded in the design's Trace table" : "inferred from where the ID appears in the design");

  /* ------------------------------------------------------------ keys: inside:<app>[|kind|name] */
  const key = (app, kind, name) => "inside:" + app + (kind ? `|${kind}|${encodeURIComponent(name)}` : "");
  function parse(k) { const [app, kind, name] = k.slice(7).split("|"); return { app, kind: kind || "", name: name ? decodeURIComponent(name) : "" }; }
  function entOf(k) {
    const p = parse(k), d = design(p.app);
    if (!APPS[p.app]) return null;
    const title = !p.kind ? designWord(p.app) : p.kind === "problems" ? `What the ${designWord(p.app)} could not read` : p.kind === "adr" ? (d && (d.adrs.find((a) => a.id === p.name) || {}).adr_title ? `${p.name} ${(d.adrs.find((a) => a.id === p.name) || {}).adr_title}` : p.name) : p.name;
    return { key: k, kind: "inside", title, id: "" };
  }

  /* ------------------------------------------------------------ going in, and back out */
  function open(app, level, opts = {}) {
    const k = keyOfApp(app);
    if (!k) { toast(`${app} is not an app in this vault`); return; }
    const deeper = LEVELS.findIndex(([l]) => l === level) > LEVELS.findIndex(([l]) => l === st.level);
    const was = App.view === "inside" && st.app === k ? st.level : null;
    st.app = k; st.level = LEVELS.some(([l]) => l === level) ? level : "context";
    if (opts.tab) st.tab = opts.tab;
    App.section = "apps"; Nav.st.child = k; MapView.st.focus = null;
    App.view = "inside"; App.focus = k;
    App.root = st.level === "components" && design(k) ? key(k) : Reader.keyFor(k) || "lights";
    if (!opts.keepTrail) App.trail = [];
    Nav.syncHash(); rerender(); Panel.render();
    if (!opts.still) zoom(opts.from || null, was === null ? true : deeper);
  }
  /* Effects On: the new level grows out of what was picked, or the old one recedes. Plain: it is simply there. */
  function zoom(fromRect, inward) {
    const stage = $("#inside-stage");
    if (!stage || reducedMotion()) return;
    const r = stage.getBoundingClientRect(), f = fromRect || { left: r.left + r.width / 2 - 60, top: r.top + r.height / 2 - 30, width: 120, height: 60 };
    stage.style.transformOrigin = `${f.left + f.width / 2 - r.left}px ${f.top + f.height / 2 - r.top}px`;
    const from = inward ? `scale(${clamp(f.width / r.width, 0.12, 0.6).toFixed(3)})` : "scale(1.7)";
    stage.animate([{ transform: from, opacity: 0.15 }, { transform: "scale(1)", opacity: 1 }], { duration: 460, easing: "cubic-bezier(.2,.8,.2,1)" });
  }
  const hash = () => `inside=${encodeURIComponent(st.app)}&level=${st.level}${st.level === "components" && st.tab !== "trace" ? "&tab=" + st.tab : ""}`;
  function boot() {
    const k = keyOfApp(HASH.get("inside"));
    if (!k) { console.warn(`[inside] #inside=${HASH.get("inside")} is not an app in this vault; opening the home`); return false; }
    open(k, HASH.get("level") || "context", { tab: TABS.some(([t]) => t === HASH.get("tab")) ? HASH.get("tab") : null, still: true });
    return true;
  }

  /* ------------------------------------------------------------ the view */
  function render(main) {
    const app = st.app && APPS[st.app] ? st.app : (D.map.apps[0] || {}).key;
    if (!app) { main.append(emptyState("This vault has no apps yet.", "There is nothing to go inside.", "/planner:boundary")); return; }
    st.app = app;
    const d = design(app);
    MapView.resetPulses(); if (typeof Motion !== "undefined") Motion.clear();
    main.append(h("div", { class: "view-head inside-head" },
      h("div", {}, h("div", { class: "kicker" }, "Inside this app"),
        h("h1", {}, Icons.forKey(app, "p-glyph"), appTitle(app)), crumbs()),
      h("div", { class: "spacer" }),
      h("div", { class: "page-actions" }, d && st.level !== "plan" ? statusPill(app) : null, d && st.level !== "plan" ? problemsChip(app) : null,  // the plan level has its own bar of status and problems
        st.level === "plan" ? null : designLink(d, Icons.el("docs")),
        h("button", { class: "btn", onclick: () => Nav.open("apps", app) }, "Back to the map"))));
    const stage = h("div", { class: "inside-stage inside-" + st.level, id: "inside-stage", "data-level": st.level, "data-app": app });
    main.append(stage);
    ({ context, containers, components, plan: (box, a) => Plan.render(box, a) })[st.level](stage, app, d);
  }
  function crumbs() {
    const at = LEVELS.findIndex(([l]) => l === st.level);
    return h("nav", { class: "inside-crumbs", "aria-label": "Levels" }, LEVELS.map(([l, word], i) => [
      i ? h("span", { class: "sep" }, "›") : null,
      i === at ? h("span", { class: "cur", "aria-current": "page" }, word)
        : h("a", { "data-level": l, title: i < at ? `Step back up to ${word.toLowerCase()}` : `Go in to ${word.toLowerCase()}`, onclick: (ev) => open(st.app, l, { from: ev.currentTarget.getBoundingClientRect() }) }, word)]));
  }
  /* The team's design doc, reached by the relative href the build computed from the page's own folder; none when
     the build could not make one without naming the builder's home folder. */
  function designLink(d, icon = null, where = "") {
    if (!d || !d.href) return null;
    return h("a", { class: "btn quiet", href: encodeURI(d.href), target: "_blank", title: d.file + where }, icon, "Open the design doc");
  }
  function statusPill(app) {
    const d = design(app), fm = d.frontmatter, gaps = fm.gaps.map((g) => g.id).filter(Boolean);
    return h("span", { class: "d-status " + (fm.status || "unknown"), title: `The team's design is ${fm.status || "of no known status"}${gaps.length ? ", with " + gaps.join(", ") : ""}; last session ${fm.last_session || "not recorded"}` },
      fm.status === "complete-with-gaps" ? `complete with gaps` : fm.status || "status not read", gaps.length ? h("b", {}, " " + gaps.join(" ")) : null);
  }
  /* The count of what the reader could not read: always shown, opening the list with line numbers. */
  function problemsChip(app, opts = {}) {
    const d = design(app), n = d.problems.length, un = d.resolved.unresolved.length;
    return h("button", { class: "chip d-problems" + (n || un ? " some" : ""), "data-problems": n, title: "What this page could not read in the design, with line numbers",
      onclick: (ev) => { ev.stopPropagation(); go(key(app, "problems", "all"), { reset: !opts.keep }); } },
      Icons.el(n || un ? "audit" : "consent"), n ? `${plural(n, "thing")} this page could not read` : "read with no problems", un ? h("span", { class: "ct" }, ` · ${un} not in the vault`) : null);
  }
  function chipCard(icon, title, body, action) {
    return h("div", { class: "inside-chip-card" }, h("div", { class: "icc-ico" }, Icons.el(icon)), h("div", {}, h("b", {}, title), body ? h("div", { class: "muted" }, body) : null, action || null));
  }

  /* ------------------------------------------------------------ level 1: the context, as the map's Focus */
  function context(stage, app) {
    const board = h("div", { class: "board board-cockpit board-focus", id: "board" });
    stage.append(board);
    MapGroups.focus(board, app);
    const centre = $(`#board g.hit[data-key="${CSS.escape(app)}"]`);
    if (centre) {
      centre.classList.add("inside-door");
      centre.addEventListener("click", () => open(app, "containers", { from: centre.getBoundingClientRect() }));
      centre.appendChild(document.createElementNS(SVGNS, "title")).textContent = `${appTitle(app)}: click to go inside, to its containers`;
    }
    stage.append(h("div", { class: "inside-hint" }, `Click ${appTitle(app)} to go in to its containers. Double-click a neighbour to go inside it instead.`));
  }

  /* ------------------------------------------------------------ text measured before drawing, and fitted */
  const MONO = "mono";
  const measure = (() => {
    const ctx = document.createElement("canvas").getContext("2d");
    const face = (f) => (f === MONO ? getComputedStyle(document.documentElement).getPropertyValue("--mono") : getComputedStyle(document.body).fontFamily);
    return (text, size, weight, family) => { ctx.font = `${weight || 400} ${size}px ${face(family)}`; return ctx.measureText(text).width; };
  })();
  function fit(text, width, size, weight, family) {
    let t = String(text || "");
    if (measure(t, size, weight, family) <= width) return t;
    while (t.length > 2 && measure(t + "…", size, weight, family) > width) t = t.slice(0, -1);
    return t.trimEnd() + "…";
  }

  /* ------------------------------------------------------------ a layered drawing, left to right
     Sugiyama's method, kept small and deterministic: cycles broken in document order, each node at the end of its
     longest path, a waypoint for every column a long arrow crosses (so it runs between boxes, never through one),
     three sweeps of barycentre ordering, then each column pulled towards its neighbours without two boxes ever
     closer than the gap. Stubs (side "in" or "out") take the first and last columns.

     It lays out left to right; top to bottom is the same layout on swapped sizes, transposed. With dir "auto" it
     takes whichever of the two draws larger in the room it has (o.fit), so a long chain of dependencies stands up
     and a wide fan lies down. */
  function layered(nodes, edges, o) {
    const run = (dir) => {
      const ns = nodes.map((n) => Object.assign({}, n, dir === "TB" ? { w: n.h, h: n.w, portH: null } : {})), es = edges.map((e) => Object.assign({}, e));
      const lay = layeredLR(ns, es, dir === "TB" ? Object.assign({}, o, { gapX: o.gapTB || 64, gapY: o.gapYTB || 30 }) : o);
      lay.dir = dir;
      if (dir === "TB") {
        const T = (q) => ({ x: q.y, y: q.x });
        for (const b of Object.values(lay.box)) Object.assign(b, { x: b.y, y: b.x, w: b.h, h: b.w }, { node: Object.assign(b.node, { w: b.node.h, h: b.node.w }) });
        lay.paths.forEach((q) => { q.pts = q.pts.map(T); });
      }
      const bb = boundsOf(Object.values(lay.box));
      lay.scale = o.fit ? Math.min((o.fit.w - 60) / (bb.x1 - bb.x0 + 120), (o.fit.h - 60) / (bb.y1 - bb.y0 + 140)) : 1;
      return lay;
    };
    if (o.dir !== "auto") return run(o.dir || "LR");
    const lr = run("LR"), tb = run("TB");
    return tb.scale > lr.scale * 1.08 ? tb : lr;
  }
  function layeredLR(nodes, edges, o) {
    const GX = o.gapX, GY = o.gapY, byId = {};
    nodes.forEach((n, i) => { n.i = i; byId[n.id] = n; });
    const free = nodes.filter((n) => !n.side), es = edges.filter((e) => byId[e.from] && byId[e.to] && e.from !== e.to);
    const inner = es.filter((e) => !byId[e.from].side && !byId[e.to].side);
    const outOf = {}; free.forEach((n) => { outOf[n.id] = []; });
    inner.forEach((e) => outOf[e.from].push(e));
    const seen = {};
    const visit = (id) => { seen[id] = 1; for (const e of outOf[id]) { if (seen[e.to] === 1) e.back = true; else if (!seen[e.to]) visit(e.to); } seen[id] = 2; };
    const hasIn = new Set(inner.map((e) => e.to));
    [...free.filter((n) => !hasIn.has(n.id)), ...free].forEach((n) => { if (!seen[n.id]) visit(n.id); });
    const layer = {};
    free.forEach((n) => { layer[n.id] = 0; });
    const fwd = inner.map((e) => (e.back ? [e.to, e.from] : [e.from, e.to]));
    for (let k = 0; k < free.length; k++) for (const [a, b] of fwd) layer[b] = Math.max(layer[b], layer[a] + 1);
    const lead = nodes.some((n) => n.side === "in") ? 1 : 0, top = Math.max(0, ...free.map((n) => layer[n.id])) + lead;
    for (const n of nodes) layer[n.id] = n.side === "in" ? 0 : n.side === "out" ? top + 1 : layer[n.id] + lead;
    // chains: each edge as a run of ids, one per column, waypoints between
    const chains = es.map((e, ei) => {
      const [a, b] = e.back ? [e.to, e.from] : [e.from, e.to], ids = [a];
      for (let L = layer[a] + 1; L < layer[b]; L++) { const id = `~${ei}~${L}`; byId[id] = { id, dummy: true, w: 0, h: 10, i: byId[a].i + 0.5 }; layer[id] = L; ids.push(id); }
      ids.push(b);
      return { e, ids, a, b };
    });
    const cols = [];
    for (const id of Object.keys(layer)) (cols[layer[id]] = cols[layer[id]] || []).push(id);
    for (let L = 0; L < cols.length; L++) cols[L] = (cols[L] || []).sort((p, q) => byId[p].i - byId[q].i || cmp(p, q));
    const up = {}, down = {};
    for (const c of chains) for (let j = 1; j < c.ids.length; j++) { (down[c.ids[j - 1]] = down[c.ids[j - 1]] || []).push(c.ids[j]); (up[c.ids[j]] = up[c.ids[j]] || []).push(c.ids[j - 1]); }
    const pos = {};
    const index = () => cols.forEach((col) => col.forEach((id, i) => { pos[id] = i; }));
    index();
    for (let sweep = 0; sweep < 6; sweep++) {
      const ls = sweep % 2 ? [...cols.keys()].reverse() : [...cols.keys()];
      for (const L of ls) {
        const nb = sweep % 2 ? down : up;
        const bary = (id) => { const xs = (nb[id] || []).map((x) => pos[x]); return xs.length ? xs.reduce((p, q) => p + q, 0) / xs.length : pos[id]; };
        cols[L] = cols[L].slice().sort((p, q) => bary(p) - bary(q) || pos[p] - pos[q]);
        cols[L].forEach((id, i) => { pos[id] = i; });
      }
    }
    // x: one column per layer, as wide as its widest box
    const colW = cols.map((col) => Math.max(o.minColW || 40, ...col.map((id) => byId[id].w))), colX = [];
    colW.forEach((w, L) => { colX[L] = L ? colX[L - 1] + colW[L - 1] + GX : 0; });
    const cy = {};
    const sep = (a, b) => byId[a].h / 2 + byId[b].h / 2 + (byId[a].dummy || byId[b].dummy ? GY / 2 : GY);
    cols.forEach((col) => { let y = 0; col.forEach((id, i) => { if (i) y += sep(col[i - 1], id); cy[id] = y; }); const mid = y / 2; col.forEach((id) => { cy[id] -= mid; }); });
    // y: each column pulled towards the mean of its neighbours, never closer than the gap (forward and back, averaged)
    for (let pass = 0; pass < 4; pass++) {
      const ls = pass % 2 ? [...cols.keys()].reverse() : [...cols.keys()];
      for (const L of ls) {
        const col = cols[L], want = col.map((id) => { const ys = [...(up[id] || []), ...(down[id] || [])].map((x) => cy[x]); return ys.length ? ys.reduce((p, q) => p + q, 0) / ys.length : cy[id]; });
        const f = want.slice(), b = want.slice();
        for (let i = 1; i < col.length; i++) f[i] = Math.max(f[i], f[i - 1] + sep(col[i - 1], col[i]));
        for (let i = col.length - 2; i >= 0; i--) b[i] = Math.min(b[i], b[i + 1] - sep(col[i], col[i + 1]));
        col.forEach((id, i) => { cy[id] = (f[i] + b[i]) / 2; });
      }
    }
    const box = {};
    for (const [id, n] of Object.entries(byId)) if (layer[id] !== undefined) box[id] = { x: colX[layer[id]] + (colW[layer[id]] - n.w) / 2, y: cy[id] - n.h / 2, w: n.w, h: n.h, L: layer[id], node: n };
    // ports: the arrows meeting one side of a box spread along it, in the order of where they come from
    const ports = {};
    const portFor = (id, side, other) => (ports[id + side] = ports[id + side] || []).push(other);
    for (const c of chains) { portFor(c.ids[0], "R", c); portFor(c.ids[c.ids.length - 1], "L", c); }
    const at = {};
    for (const [k, list] of Object.entries(ports)) {
      const id = k.slice(0, -1), side = k.slice(-1), b = box[id], ph = b.node.portH || b.h;
      const far = (c) => cy[side === "R" ? c.ids[1] : c.ids[c.ids.length - 2]];
      list.sort((p, q) => far(p) - far(q)).forEach((c, i) => { at[(side === "R" ? "a" : "b") + chains.indexOf(c)] = { x: side === "R" ? b.x + b.w : b.x, y: b.y + (ph * (i + 1)) / (list.length + 1) }; });
    }
    const paths = chains.map((c, ci) => {
      const pts = [at["a" + ci]];
      for (const id of c.ids.slice(1, -1)) { const L = layer[id]; pts.push({ x: colX[L], y: cy[id] }, { x: colX[L] + colW[L], y: cy[id] }); }
      pts.push(at["b" + ci]);
      const out = [pts[0]];
      for (let j = 1; j < pts.length; j++) { const seg = Math.abs(pts[j].y - pts[j - 1].y) < 0.5 ? [pts[j - 1], pts[j]] : Geo.route(pts[j - 1], pts[j], "R"); out.push(...seg.slice(1)); }
      return { e: c.e, pts: c.e.back ? out.reverse() : out };
    });
    const gaps = colX.slice(0, -1).map((x, L) => [x + colW[L], colX[L + 1]]);
    return { box: Object.fromEntries(Object.entries(box).filter(([, b]) => !b.node.dummy)), paths, gaps, colX, colW };
  }
  /* A label's place on its arrow: in a gap between columns, on nothing already drawn; else just above or below. */
  const hits = (a, b, m = 3) => a.x < b.x + b.w + m && b.x < a.x + a.w + m && a.y < b.y + b.h + m && b.y < a.y + a.h + m;
  function placeLabel(pts, w, ht, obs, gaps, dir) {
    const inGap = (r) => gaps.some(([a, b]) => (dir === "TB" ? r.y >= a + 3 && r.y + r.h <= b - 3 : r.x >= a + 4 && r.x + r.w <= b - 4));
    const total = Geo.length(pts);
    // outward from the middle in steps of 1/48 of the arrow, so the label stays as central as the drawing allows
    for (let k = 0; k <= 46; k++) {
      const f = 0.5 + (k % 2 ? -1 : 1) * Math.ceil(k / 2) / 48, p = Geo.pointAt(pts, total * f);
      for (const d of [0, -1, 1]) {
        const r = dir === "TB" ? { x: p.x - w / 2 + d * (w / 2 + 6), y: p.y - ht / 2, w, h: ht } : { x: p.x - w / 2, y: p.y - ht / 2 + d * (ht + 2), w, h: ht };
        if (inGap(r) && !obs.some((x) => hits(x, r, 7))) return r;
      }
    }
    return null;
  }
  function defsFor(svg) {
    const d = s("defs", {}, svg);
    s("feGaussianBlur", { stdDeviation: 11 }, s("filter", { id: "ck-glow", x: "-60%", y: "-120%", width: "220%", height: "340%" }, d));
    const lens = s("linearGradient", { id: "ck-lens", x1: 0, y1: 0, x2: 0, y2: 1 }, d);
    s("stop", { offset: "0", "stop-color": Theme.c("face-hi") }, lens); s("stop", { offset: "1", "stop-color": Theme.c("face-lo") }, lens);
    for (const [id, cls] of [["in-arrow", "in-arrowhead"], ["in-arrow-soft", "in-arrowhead soft"]]) {
      const m = s("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, d);
      s("path", { d: "M0,0L10,5L0,10z", class: cls }, m);
    }
  }
  /* Draws a layout: arrows first, then their labels where nothing else is, then the boxes, each by its own drawer. */
  function drawLayout(svg, lay, drawers, extraObs) {
    const gEdges = s("g", { class: "in-edges" }, svg), gLabels = s("g", { class: "in-labels" }, svg), gNodes = s("g", { class: "in-nodes" }, svg);
    const obs = Object.values(lay.box).map((b) => ({ x: b.x, y: b.y, w: b.w, h: b.h })).concat(extraObs || []);
    let hidden = 0;
    for (const p of lay.paths) {
      const e = p.e;
      const pts = p.pts.filter((q, i) => !i || Math.hypot(q.x - p.pts[i - 1].x, q.y - p.pts[i - 1].y) > 0.5);  // a bend needs two distinct points
      s("path", { d: Geo.roundedPath(pts, 18), class: "in-edge" + (e.soft ? " soft" : "") + (e.lit ? " lit " + e.lit : ""), "marker-end": `url(#${e.soft ? "in-arrow-soft" : "in-arrow"})`, "data-from": e.from, "data-to": e.to }, gEdges)
        .appendChild(document.createElementNS(SVGNS, "title")).textContent = e.title || `${e.fromName || e.from} → ${e.toName || e.to}${e.label ? ": " + e.label : ""}`;
      if (!e.label) continue;
      const text = fit(e.label, 168, 11.5, 500, MONO), w = measure(text, 11.5, 500, MONO) + 14, r = placeLabel(pts, w, 20, obs, lay.gaps, lay.dir);
      if (!r) { hidden++; continue; }
      obs.push(r);
      const g = s("g", { class: "in-label" + (e.onpick ? " pick" : "") + (e.lit ? " lit " + e.lit : ""), "data-label": e.label }, gLabels);
      s("rect", { x: r.x, y: r.y, width: r.w, height: r.h, rx: 4 }, g);
      s("text", { x: r.x + r.w / 2, y: r.y + 14, "text-anchor": "middle" }, g).textContent = text;
      s("title", {}, g).textContent = e.title || e.label;
      if (e.onpick) g.addEventListener("click", e.onpick);
    }
    for (const [id, b] of Object.entries(lay.box)) (drawers[b.node.kind] || (() => null))(gNodes, b, id);
    return { obs, hidden };
  }
  const MIN_SCALE = 0.72;  // below this a box's name is under 10px; the drawing scrolls instead, unless the reader zooms out
  const READ_SCALE = 1, READ_FITS = 0.85;  // a drawing that fits whole at READ_FITS or more opens whole; a bigger one opens at READ_SCALE
  /* Sizes a drawing to its holder and gives it the reader's zoom controls.
     Containers open as before: fitted, but never under MIN_SCALE. The components and the data model open at a size
     a reader can read (names at 14px), scrolled to `focus`, the box the page is about, with a minimap of the whole
     drawing beside the controls; they only open whole when the whole is already readable. "Whole" always fits it.
     opts: key (where the zoom is remembered), open ("read" for the two above), focus (a rect in drawing
     coordinates), frame (the element that carries the controls and the minimap; the holder's parent by default). */
  const unplaced = [];  // drawings built before their holder was in the page, sized by placeDrawings() once it is
  function placeDrawings() {
    for (const d of unplaced.splice(0)) if (d.svg.isConnected) d.place();
  }
  function sized(svg, holder, bounds, pad, opts = {}) {
    const x0 = bounds.x0 - pad, y0 = bounds.y0 - pad, w = bounds.x1 - bounds.x0 + pad * 2, ht = bounds.y1 - bounds.y0 + pad * 2;
    const zkey = opts.key || st.level, frame = opts.frame || holder.parentElement;
    svg.setAttribute("viewBox", `${x0.toFixed(1)} ${y0.toFixed(1)} ${w.toFixed(1)} ${ht.toFixed(1)}`);
    const whole = () => { const r = holder.getBoundingClientRect(); return r.width ? Math.min(1.15, (r.width - 28) / w, (r.height - 16) / ht) : READ_SCALE; };
    const opening = () => { const k = whole(); return opts.open === "read" ? (k >= READ_FITS ? k : READ_SCALE) : Math.max(MIN_SCALE, k); };
    const scaleOf = () => { const z = st.zoom[zkey]; return z === "whole" ? whole() : typeof z === "number" ? z : opening(); };
    // where a point of the drawing sits, in the holder's scrolled content; the holder centres a drawing that fits
    const at = (x, y) => { const r = svg.getBoundingClientRect(), b = holder.getBoundingClientRect(), k = +holder.dataset.scale;
      return { x: r.left - b.left + holder.scrollLeft + (x - x0) * k, y: r.top - b.top + holder.scrollTop + (y - y0) * k }; };
    const centreOn = (x, y) => { const p = at(x, y); holder.scrollLeft = p.x - holder.clientWidth / 2; holder.scrollTop = p.y - holder.clientHeight / 2; };
    const centreNow = () => { const k = +holder.dataset.scale; return { x: x0 + (holder.scrollLeft + holder.clientWidth / 2 - at(x0, y0).x) / k, y: y0 + (holder.scrollTop + holder.clientHeight / 2 - at(x0, y0).y) / k }; };
    const mini = opts.open === "read" ? minimap(svg, holder, { x0, y0, w, ht }) : null;
    const apply = () => {
      const k = scaleOf();
      svg.setAttribute("width", Math.round(w * k)); svg.setAttribute("height", Math.round(ht * k));
      holder.dataset.scale = k.toFixed(2);
      if (mini) mini.update();
    };
    const showFocus = () => { if (opts.focus) centreOn(opts.focus.x + opts.focus.w / 2, opts.focus.y + opts.focus.h / 2); };
    let placed = false;  // the first time the drawing is in the page: size it, then show the box the page is about
    const place = () => { placed = true; apply(); showFocus(); };
    const fitIt = (ev) => {
      if (!svg.isConnected) { if (placed || ev instanceof Event) { observer.disconnect(); removeEventListener("resize", fitIt); } return; }
      if (!placed) { place(); return; }
      const keep = centreNow();
      apply(); centreOn(keep.x, keep.y);
    };
    const observer = new ResizeObserver(fitIt);
    observer.observe(holder);
    addEventListener("resize", fitIt);  // the tabs fold away and say so with a resize
    apply();
    if (svg.isConnected) place(); else unplaced.push({ svg, place });
    const set = (z) => {
      const keep = centreNow();
      st.zoom[zkey] = z; apply();
      if (z === null && opts.focus) showFocus(); else if (z !== "whole") centreOn(keep.x, keep.y);
    };
    const now = () => +holder.dataset.scale;
    // the controls sit on the frame around the holder, not in it: inside a scrolling holder they took a column of room
    frame.append(h("div", { class: "in-zoom", role: "group", "aria-label": "Zoom" },
      h("button", { title: "Zoom out", onclick: () => set(Math.max(0.3, now() / 1.25)) }, "−"),
      h("button", { title: "The whole drawing in view", onclick: () => set("whole") }, "Whole"),
      h("button", { title: opts.open === "read" ? "Reading size, centred on the main box" : "Reading size: names at 10px or more, scrolling if it must", onclick: () => set(null) }, "Read"),
      h("button", { title: "Zoom in", onclick: () => set(Math.min(2, now() * 1.25)) }, "+")));
    if (mini) frame.append(mini.el);
  }
  /* The whole drawing, small, with the part in view lit; click or drag to move there. It shows only while the
     drawing is bigger than its holder, so a drawing that fits has nothing to navigate. */
  function minimap(svg, holder, v) {
    const MAX = 150, k = Math.min(MAX / v.w, MAX / v.ht);
    // only the shapes, under classes of their own, so nothing in the minimap answers to the drawing's selectors
    const copy = s("svg", { viewBox: svg.getAttribute("viewBox"), class: "in-mini-svg", width: Math.round(v.w * k), height: Math.round(v.ht * k), "aria-hidden": "true" });
    for (const [selector, cls] of [[".in-frame", "mini-frame"], [".in-edge", "mini-wire"], [".in-box-face, .in-stub-face", "mini-box"]]) {
      for (const shape of svg.querySelectorAll(selector)) {
        const flat = shape.cloneNode(false);
        flat.removeAttribute("marker-end"); flat.removeAttribute("data-from"); flat.removeAttribute("data-to");
        flat.setAttribute("class", cls); copy.append(flat);
      }
    }
    const view = s("rect", { class: "in-mini-view", rx: 2 }, copy);
    const el = h("div", { class: "in-mini", role: "group", "aria-label": "Where you are in the drawing. Click or drag to move." }, copy);
    function update() {
      const r = svg.getBoundingClientRect(), b = holder.getBoundingClientRect(), sc = +holder.dataset.scale || 1;
      const over = r.width > b.width + 1 || r.height > b.height + 1;
      el.hidden = !over;
      if (!over) return;
      const l = Math.max(b.left, r.left), t = Math.max(b.top, r.top), rt = Math.min(b.right, r.right), bt = Math.min(b.bottom, r.bottom);
      view.setAttribute("x", (v.x0 + (l - r.left) / sc).toFixed(1)); view.setAttribute("y", (v.y0 + (t - r.top) / sc).toFixed(1));
      view.setAttribute("width", ((rt - l) / sc).toFixed(1)); view.setAttribute("height", ((bt - t) / sc).toFixed(1));
    }
    const jump = (ev) => {
      const m = copy.getBoundingClientRect(), r = svg.getBoundingClientRect(), b = holder.getBoundingClientRect(), sc = +holder.dataset.scale || 1;
      const px = r.left + ((ev.clientX - m.left) / k) * sc, py = r.top + ((ev.clientY - m.top) / k) * sc;
      holder.scrollLeft += px - (b.left + b.width / 2); holder.scrollTop += py - (b.top + b.height / 2);
    };
    el.addEventListener("pointerdown", (ev) => { el.setPointerCapture(ev.pointerId); jump(ev); });
    el.addEventListener("pointermove", (ev) => { if (el.hasPointerCapture(ev.pointerId)) jump(ev); });
    holder.addEventListener("scroll", update, { passive: true });
    return { el, update };
  }
  const boundsOf = (rects) => ({ x0: Math.min(...rects.map((r) => r.x)), y0: Math.min(...rects.map((r) => r.y)), x1: Math.max(...rects.map((r) => r.x + r.w)), y1: Math.max(...rects.map((r) => r.y + r.h)) });

  /* A vault box (app or party) as the map draws it, with its own lamp and icon. */
  function vaultBox(g, b, k, sub) {
    const n = NODE[k];
    const el = MapView.lamp(g, { key: k, x: b.x, y: b.y, w: b.w, h: b.h, rx: n && n.kind !== "app" ? 2 : 10, label: titleOf(k), sub: sub || (n && n.kind !== "app" ? "outside party" : "app"), kind: n ? n.kind : "partner", clip: !!n && n.kind !== "app", icon: Icons.name(k) });
    el.classList.add("in-node", "in-vault");
    return el;
  }
  function frameAround(g, rects, label, sub) {
    const b = boundsOf(rects), pad = 26, x = b.x0 - pad, y = b.y0 - pad - 30, w = b.x1 - b.x0 + pad * 2, ht = b.y1 - b.y0 + pad * 2 + 30;
    s("rect", { x, y, width: w, height: ht, rx: 16, class: "in-frame" }, g);
    const t = s("text", { x: x + 16, y: y + 22, class: "in-frame-name in-head" }, g); t.textContent = fit(label, w - 32, 13.5, 600);
    if (sub) s("title", {}, t).textContent = sub;
    return { x, y, w, h: ht, name: { x: x + 16, y: y + 8, w: measure(t.textContent, 13.5, 600), h: 18 } };
  }
  function columnHeads(g, lay, side, text) {
    const rects = Object.values(lay.box).filter((b) => b.node.side === side);
    if (!rects.length) return null;
    const b = boundsOf(rects), w = measure(text, 12, 600);
    if (lay.dir === "TB") {  // a row of stubs: its name to the left of the row
      s("text", { x: b.x0 - 14, y: (b.y0 + b.y1) / 2 + 4, "text-anchor": "end", class: "zone-text in-head" }, g).textContent = text;
      return { x: b.x0 - 14 - w, y: (b.y0 + b.y1) / 2 - 9, w, h: 18 };
    }
    const x = (b.x0 + b.x1) / 2;
    s("text", { x, y: b.y0 - 16, "text-anchor": "middle", class: "zone-text in-head" }, g).textContent = text;
    return { x: x - w / 2, y: b.y0 - 30, w, h: 18 };
  }

  /* ------------------------------------------------------------ level 2: the main containers, from the vault */
  function containers(stage, app) {
    const c = CONT[app], pk = Reader.keyFor(app);
    if (!c || !c.rows.length) {
      stage.append(chipCard("layers", `${appTitle(app)}'s page has no main containers table.`, "An app's main containers are co-designed by its senior and the solution lead, and written on its page as a Container | Job table (c4: container). Nothing else in the vault says what is inside it.",
        h("div", { class: "p-actions" }, pk ? h("button", { class: "btn", onclick: () => go(pk, {}) }, "Open the app page") : null, h("button", { class: "btn", onclick: () => open(app, "components") }, "Components, from the team's design"))));
      return;
    }
    const holder = h("div", { class: "inside-draw", id: "inside-draw" });
    stage.append(h("div", { class: "inside-frame" }, holder), h("div", { class: "inside-hint" }, `From "${c.heading}" on ${appTitle(app)}'s page: ${plural(c.rows.length, "container")}. Arrows to and from other apps follow the contracts each row serves or uses; `,
      c.edges.length ? h("span", { class: "heuristic" }, "dashed arrows between containers are read from the page's own diagram") : "the page's diagram draws no arrow between containers", ". Click a container for its row; Components is the team's own design."));
    const nodes = c.rows.map((r) => ({ id: "k:" + r.name, kind: "container", w: 214, h: 72, row: r }));
    const edges = [], stub = {};
    const addStub = (k, side) => { const id = `v:${side}:${k}`; if (!stub[id]) { stub[id] = true; nodes.push({ id, kind: "vault", side, w: 176, h: 62, vkey: k }); } return id; };
    for (const r of c.rows) {
      // a contract it serves comes from its consumers, and from its provider when that is outside (a webhook kept here)
      for (const cid of r.serves) { const con = CONTRACT[cid]; if (!con) continue; for (const k of [...con.consumers, con.provider].filter((x) => x !== app && NODE[x])) edges.push({ from: addStub(k, "in"), to: "k:" + r.name, cid }); }
      for (const cid of r.uses) { const con = CONTRACT[cid]; if (!con || con.provider === app || !NODE[con.provider]) continue; edges.push({ from: "k:" + r.name, to: addStub(con.provider, "out"), cid }); }
    }
    const merged = {};
    for (const e of edges) { const m = merged[e.from + ">" + e.to] = merged[e.from + ">" + e.to] || { from: e.from, to: e.to, ids: [] }; if (!m.ids.includes(e.cid)) m.ids.push(e.cid); }
    const all = Object.values(merged).map((m) => ({ from: m.from, to: m.to, label: m.ids.join(", "), title: m.ids.map((id) => `${id} ${CONTRACT[id].title}`).join("; "), lit: worstOf(m.ids), onpick: () => go(m.ids.length > 1 ? `bundle:${m.ids.join(",")}|${m.to.startsWith("v:") ? m.to.split(":").slice(2).join(":") : app}` : m.ids[0], { reset: true }) }));
    for (const e of c.edges) all.push({ from: "k:" + e.from, to: "k:" + e.to, soft: true, label: e.label, title: `${e.from} → ${e.to}, from the page's diagram (best effort)` });
    const room = holder.getBoundingClientRect();
    const lay = layered(nodes, all, { gapX: 150, gapY: 26, minColW: 176, dir: "auto", fit: { w: room.width, h: room.height } });
    const svg = s("svg", { class: "inside-svg cockpit containers", role: "img", "aria-label": `${appTitle(app)}'s main containers` }, holder);
    defsFor(svg);
    const gFrame = s("g", {}, svg);
    const inner = Object.values(lay.box).filter((b) => b.node.kind === "container");
    const fr = frameAround(gFrame, inner, `${appTitle(app)}: main containers`, `From its page: ${c.heading}, line ${c.line}`);
    const heads = [columnHeads(gFrame, lay, "in", "Uses it"), columnHeads(gFrame, lay, "out", "It uses")].filter(Boolean);
    drawLayout(svg, lay, {
      container: (g, b) => {
        const r = b.node.row, grp = s("g", { class: "in-node in-box container", tabindex: 0, role: "button", "data-key": key(app, "ct", r.name), "aria-label": `${r.name}: ${r.job}` }, g);
        s("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 10, class: "in-box-face" }, grp);
        Icons.put(grp, glyphFor(r.name), b.x + 20, b.y + 22, 18, "node-glyph");
        s("text", { x: b.x + 36, y: b.y + 27, class: "in-box-name" }, grp).textContent = fit(r.name, b.w - 46, 14, 600);
        s("text", { x: b.x + 14, y: b.y + 48, class: "in-box-sub" }, grp).textContent = fit(r.job, b.w - 24, 11.5);
        s("text", { x: b.x + 14, y: b.y + 63, class: "in-box-meta" }, grp).textContent = fit([r.state, r.proposedBy ? "by " + r.proposedBy : ""].filter(Boolean).join(" · "), b.w - 24, 10.5);
        s("title", {}, grp).textContent = `${r.name}: ${r.job}`;
        pick(grp, key(app, "ct", r.name));
      },
      vault: (g, b) => vaultBox(g, b, b.node.vkey),
    }, [fr.name, ...heads]);
    sized(svg, holder, boundsOf([...Object.values(lay.box), fr, ...heads]), 24);
    MapView.startBreathing();
  }
  const worstOf = (ids) => { const lv = ids.map(levelOf).sort((p, q) => rank(q) - rank(p))[0]; return lv && lv !== "dark" ? lv : ""; };
  function pick(el, k) {
    const go1 = () => go(k, { reset: true });
    el.addEventListener("click", go1);
    el.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go1(); } });
  }
  /* A component's glyph, by the words in its name: the built-in set, never a colour of its own. */
  const GLYPHS = [[/api|gateway|endpoint/i, "gateway"], [/store|repositor|cache|database|db\b/i, "database"], [/publish|event|bus|consumer|queue/i, "messaging"],
    [/adapter|reader|client|sender/i, "nodes"], [/check|guard|auth|caller/i, "lock"], [/engine|rule|calculat|pric/i, "layers"], [/render|template|page/i, "docs"],
    [/hold|keeper|timer|schedul|expir/i, "schedule"], [/lifecycle|state|machine/i, "hexagon"], [/suppress|filter/i, "fraud"], [/ui|app|desktop|kiosk|screen/i, "web"]];
  const glyphFor = (name) => (GLYPHS.find(([re]) => re.test(name)) || [null, "cube"])[1];

  /* ------------------------------------------------------------ level 3: the team's design */
  function components(stage, app, d) {
    if (!d) {
      stage.append(chipCard("docs", `The ${appTitle(app)} team's design is not loaded.`, h("span", {}, "Build with ", h("code", {}, `--design ${D.map.apps.find((a) => a.key === app).id}=<team repo>/docs/tech-design/<slug>.md`), ", or set ", h("code", {}, "design:"), " on the app's page (or ", h("code", {}, "designs:"), " in .planner.yaml) to its path, and the build finds it. The tech-design-grill skill writes it in the team's own repository. Context and Containers still draw from the vault."),
        h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => open(app, "containers") }, "Containers, from the vault"), linkChips(app))));
      stage.dataset.design = "none";
      return;
    }
    stage.dataset.design = d.frontmatter.status || "unknown";
    const wrap = h("div", { class: "inside-l3" }), holder = h("div", { class: "inside-draw", id: "inside-draw" }), side = h("div", { class: "inside-side" });
    const toggle = h("button", { class: "btn quiet in-tabs-toggle", "aria-expanded": String(!st.tabsHidden), onclick: () => {
      st.tabsHidden = !st.tabsHidden;
      wrap.classList.toggle("tabs-hidden", st.tabsHidden);
      toggle.setAttribute("aria-expanded", String(!st.tabsHidden)); toggle.textContent = st.tabsHidden ? "Show the tabs" : "Hide the tabs";
      dispatchEvent(new Event("resize"));  // the drawing refits to the room it now has
    } }, st.tabsHidden ? "Show the tabs" : "Hide the tabs");
    wrap.classList.toggle("tabs-hidden", !!st.tabsHidden);
    wrap.append(h("div", { class: "inside-left" }, h("div", { class: "inside-tools" }, toggle), h("div", { class: "inside-frame" }, holder), componentsNote(app, d)), side);  // the toggle sits above the drawing, never on a box
    stage.append(wrap);
    drawComponents(holder, app, d);
    side.append(tabs(app, d));
    placeDrawings();
  }
  function componentsNote(app, d) {
    const missing = d.problems.some((p) => p.section === "Integration points" && /missing section/.test(p.message));
    return h("div", { class: "inside-hint" }, `${plural(d.components.length, "component")} from ${d.path.split("/").slice(-1)[0]}. Arrows are each Depends on, labelled with what the other offers on its Exposes line; `,
      missing ? h("span", { class: "gap" }, "the design has no Integration points section, so no stub is drawn for it. ") : "stubs at the sides are its Integration points, joined where the design cites their contract. ",
      h("span", { class: "heuristic" }, d.trace_source === "recorded" ? "Owned IDs are recorded in its Trace table." : "Owned IDs are inferred from where each ID appears; the format records no trace."));
  }
  function drawComponents(holder, app, d) {
    const comps = d.components, affects = {};
    for (const oq of d.open_questions) for (const c of comps) if (new RegExp(`\\b${c.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i").test(oq.affects)) (affects[c.name] = affects[c.name] || []).push(oq.id);
    const nodes = comps.map((c) => ({ id: "c:" + c.name, kind: "component", w: 206, h: 86, portH: 62, c }));
    const edges = d.depends.map((e) => ({ from: "c:" + e.from, to: "c:" + e.to, label: e.label, fromName: e.from, toName: e.to,
      title: e.label ? `${e.from} depends on ${e.to}: ${e.label} (from ${e.labelFrom})` : `${e.from} depends on ${e.to}; ${e.to}'s Exposes line names nothing it offers ${e.from}` }));
    const loose = [];
    d.stubs.forEach((x, i) => {
      const side = x.direction === "in" ? "in" : "out", id = "s:" + i;
      nodes.push({ id, kind: "stub", side, w: 168, h: 56, stub: x });
      const label = x.contracts.join(", ");
      const title = `${x.system}${x.protocol ? ", " + x.protocol : ""}${x.auth ? ", " + x.auth : ""}: ${x.component ? `meets ${x.component} (${x.how})` : x.how}`;
      if (!x.component) { loose.push({ id, side, title }); return; }
      const lit = worstOf(x.contracts.filter((c) => CONTRACT[c]));
      const onpick = x.contracts[0] && CONTRACT[x.contracts[0]] ? () => go(x.contracts[0], { reset: true }) : null;
      edges.push(side === "in" ? { from: id, to: "c:" + x.component, label, title, lit, onpick } : { from: "c:" + x.component, to: id, label, title, lit, onpick });
    });
    const room = holder.getBoundingClientRect();
    const lay = layered(nodes, edges, { gapX: 170, gapY: 30, gapTB: 70, gapYTB: 26, minColW: 170, dir: "auto", fit: { w: room.width, h: room.height } });
    const svg = s("svg", { class: "inside-svg cockpit components", role: "img", "aria-label": `${appTitle(app)}'s components, from the team's design` }, holder);
    defsFor(svg);
    const gFrame = s("g", {}, svg);
    const inner = Object.values(lay.box).filter((b) => b.node.kind === "component");
    const fr = frameAround(gFrame, inner, `${appTitle(app)}: components`, `From the team's design: ${d.file}`);
    const heads = [columnHeads(gFrame, lay, "in", "In: integration points"), columnHeads(gFrame, lay, "out", "Out: integration points")].filter(Boolean);
    // a stub no component meets is tied to the app's own edge, dashed, and says so on hover
    for (const l of loose) {
      const b = lay.box[l.id], tb = lay.dir === "TB", inward = l.side === "in";
      const a = tb ? { x: b.x + b.w / 2, y: inward ? b.y + b.h : fr.y + fr.h } : { x: inward ? b.x + b.w : fr.x + fr.w, y: b.y + b.h / 2 };
      const z = tb ? { x: a.x, y: inward ? fr.y : b.y } : { x: inward ? fr.x : b.x, y: a.y };
      s("path", { d: `M${a.x},${a.y}L${z.x},${z.y}`, class: "in-edge loose", "marker-end": "url(#in-arrow-soft)" }, gFrame)
        .appendChild(document.createElementNS(SVGNS, "title")).textContent = l.title;
    }
    const owned = (name) => (d.trace[name] || []).length;
    const drawn = drawLayout(svg, lay, {
      component: (g, b) => {
        const c = b.node.c, k = key(app, "c", c.name), grp = s("g", { class: "in-node in-box component", tabindex: 0, role: "button", "data-key": k, "aria-label": `${c.name}: ${c.responsibility}` }, g);
        const LIP = 24, tb = lay.dir === "TB", y = tb ? b.y + LIP : b.y, faceH = b.h - LIP;
        const exposes = c.exposes && c.exposes.trim(), lip = exposes ? "exposes " + exposes : "no Exposes line";
        s("rect", { x: b.x + 10, y: tb ? b.y : b.y + faceH - 1, width: b.w - 20, height: LIP + 1, rx: 5, class: "in-lip" + (exposes ? "" : " missing") }, grp);
        s("text", { x: b.x + 18, y: tb ? b.y + 16 : b.y + b.h - 8, class: "in-lip-text" + (exposes ? "" : " missing") }, grp).textContent = fit(lip, b.w - 36, 10.5, 500, exposes ? MONO : null);
        s("rect", { x: b.x, y, width: b.w, height: faceH, rx: 10, class: "in-box-face" }, grp);
        Icons.put(grp, glyphFor(c.name), b.x + 20, y + 22, 18, "node-glyph");
        const n = owned(c.name), badge = n ? `${n}` : "";
        s("text", { x: b.x + 36, y: y + 27, class: "in-box-name" }, grp).textContent = fit(c.name, b.w - 50 - (badge ? 30 : 0) - (affects[c.name] ? 18 : 0), 14, 600);
        if (badge) {
          const w = measure(badge, 10.5, 600) + 12;
          s("rect", { x: b.x + b.w - w - 8, y: y + 10, width: w, height: 16, rx: 8, class: "in-owns" }, grp);
          s("text", { x: b.x + b.w - w / 2 - 8, y: y + 22, "text-anchor": "middle", class: "in-owns-text" }, grp).textContent = badge;
        }
        if (affects[c.name]) s("circle", { cx: b.x + b.w - (badge ? measure(badge, 10.5, 600) + 30 : 16), cy: y + 18, r: 5, class: "in-oq" }, grp)
          .appendChild(document.createElementNS(SVGNS, "title")).textContent = `${affects[c.name].join(", ")} affects it`;
        s("text", { x: b.x + 14, y: y + 48, class: "in-box-sub" }, grp).textContent = fit(c.responsibility, b.w - 24, 11.5);
        s("title", {}, grp).textContent = `${c.name}: ${c.responsibility}${n ? `\nOwns ${plural(n, "vault ID")}` : ""}\n${lip}`;
        pick(grp, k);
      },
      stub: (g, b) => {
        const x = b.node.stub, nk = x.nodes.find((k) => NODE[k]), grp = s("g", { class: "in-node in-stub", tabindex: 0, role: "button", "data-stub": x.system, "aria-label": `${x.system}, ${x.direction || "out"}` }, g);
        s("path", { d: `M${b.x + 8},${b.y}H${b.x + b.w - 8}L${b.x + b.w},${b.y + 8}V${b.y + b.h - 8}L${b.x + b.w - 8},${b.y + b.h}H${b.x + 8}L${b.x},${b.y + b.h - 8}V${b.y + 8}Z`, class: "in-stub-face" + (x.component ? "" : " loose") }, grp);
        Icons.put(grp, nk ? Icons.name(nk) : "partner", b.x + 20, b.y + 20, 17, "node-glyph");
        s("text", { x: b.x + 36, y: b.y + 25, class: "in-box-name small" }, grp).textContent = fit(x.system, b.w - 44, 13, 600);
        const names = x.nodes.filter((k) => NODE[k]).map(titleOf);
        s("text", { x: b.x + 12, y: b.y + 45, class: "in-box-sub" }, grp).textContent = fit(names.length ? names.join(", ") : x.protocol || "not on the map", b.w - 22, 11);
        s("title", {}, grp).textContent = `${x.system}${x.protocol ? ": " + x.protocol : ""}${names.length ? "\nOn the map: " + names.join(", ") : ""}\n${x.component ? `Meets ${x.component}: ${x.how}` : x.how}`;
        const target = nk || x.contracts.find((c) => CONTRACT[c]);
        if (target) pick(grp, target);
        grp.addEventListener("dblclick", (ev) => { if (nk && APPS[nk]) { ev.stopPropagation(); open(nk, "context", { from: grp.getBoundingClientRect() }); } });
      },
    }, [fr.name, ...heads]);
    holder.dataset.hiddenLabels = drawn.hidden;
    if (drawn.hidden) console.warn(`[inside] ${drawn.hidden} arrow labels found no free room and show on hover only`);
    // the box the page is about is the component most things meet: the most Depends on and integration points, the first listed on a tie
    const meets = {};
    for (const e of edges) for (const id of [e.from, e.to]) meets[id] = (meets[id] || 0) + 1;
    const main = comps.map((c) => lay.box["c:" + c.name]).filter(Boolean).sort((a, b) => (meets[b.node.id] || 0) - (meets[a.node.id] || 0))[0];
    sized(svg, holder, boundsOf([...Object.values(lay.box), fr, ...heads]), 24, { open: "read", key: "components", focus: main });
  }

  /* ------------------------------------------------------------ beside level 3: the design's sections */
  function tabs(app, d) {
    const box = h("div", { class: "inside-tabs" });
    const bar = h("div", { class: "seg small wrap", role: "tablist", "aria-label": "The design's sections" }, TABS.map(([id, word]) =>
      h("button", { role: "tab", "aria-pressed": String(st.tab === id), "data-tab": id, onclick: () => { st.tab = id; Nav.syncHash(); const fresh = tabs(app, d); box.replaceWith(fresh); placeDrawings(); } }, word, count(d, id))));
    const body = h("div", { class: "inside-tab-body", "data-tab": st.tab });
    body.append(...[].concat(({ trace: traceTab, data: dataTab, api: apiTab, flows: flowsTab, stack: tableTab("tech_stack", ["layer", "choice", "rationale"]), nfrs: tableTab("nfrs", ["concern", "target", "how_enforced"]),
      constraints: tableTab("constraints", ["id", "constraint", "source", "impact"]), risks: tableTab("risks", ["id", "risk", "severity", "mitigation"]), adrs: adrTab, ops: opsTab, glossary: glossaryTab })[st.tab](app, d)).filter(Boolean));
    box.append(bar, body);
    return box;
  }
  function count(d, id) {
    const n = { data: d.data_model.entities.length, api: d.api.length, flows: d.flows.length + d.diagrams.length, stack: d.tech_stack.length, nfrs: d.nfrs.length, constraints: d.constraints.length,
      risks: d.risks.length, adrs: d.adrs.length, glossary: d.context ? d.context.glossary.length : 0, trace: Object.values(d.trace).reduce((p, l) => p + l.length, 0) }[id];
    return n ? h("span", { class: "ct" }, " " + n) : null;
  }
  /* Design text, with every vault ID it names a link into the vault, and `code` as code. */
  function prose(text, cls) {
    const out = h("span", { class: cls || "" });
    for (const part of String(text || "").split(/(`[^`]+`)/)) {
      if (/^`[^`]+`$/.test(part)) { out.append(h("code", {}, part.slice(1, -1))); continue; }
      let last = 0;
      const plainPart = part.replace(/\*\*/g, "");
      for (const m of plainPart.matchAll(VAULT_ID)) {
        out.append(plainPart.slice(last, m.index));
        const k = vaultKey(m[0]);
        out.append(k ? h("a", { class: "vid", "data-ref": k, title: titleOf(k) }, m[0]) : h("span", { class: "vid dead", title: "not in this vault" }, m[0]));
        last = m.index + m[0].length;
      }
      out.append(plainPart.slice(last));
    }
    return out;
  }
  const card = (title, ...kids) => h("section", { class: "in-card" }, title ? h("h3", {}, title) : null, ...kids.flat().filter(Boolean));
  const raw = (text, title) => (text ? h("details", { class: "in-raw" }, h("summary", {}, title || "The design's own text"), h("pre", {}, text)) : null);
  const best = (text) => h("p", { class: "heuristic small" }, text);

  function traceTab(app, d) {
    const r = d.resolved, ownedIds = new Set(Object.values(d.trace).flat().map((e) => e.id));
    const out = [best(`Who owns each vault ID: ${sourceWord(d)}.`)];
    out.push(card("Owned, by component", d.components.map((c) => {
      const list = d.trace[c.name] || [];
      return h("div", { class: "in-own" }, h("a", { class: "in-own-name", onclick: () => go(key(app, "c", c.name), { reset: true }) }, c.name), h("span", { class: "ct muted" }, ` ${list.length}`),
        h("div", {}, list.length ? list.map((e) => idChip(e.id, e.via.join(", "))) : h("span", { class: "p-empty-line" }, "cites no trace target")));
    }), (d.trace.Operations || []).length ? h("div", { class: "in-own" }, h("b", {}, "Operations"), h("div", {}, d.trace.Operations.map((e) => idChip(e.id, e.via.join(", "))))) : null));
    const ack = r.untraced.filter((t) => r.acknowledged[t]), missed = r.untraced.filter((t) => !r.acknowledged[t]);
    out.push(card(`Untraced: ${r.untraced.length} of ${d.targets.length} targets`, missed.length ? h("div", { class: "in-untraced missed" }, h("div", { class: "in-sub" }, lampEl("caution"), `Missed: no component owns ${missed.length === 1 ? "it" : "them"}, and no gap says so`), missed.map((t) => idChip(t))) : null,
      ack.length ? h("div", { class: "in-untraced ack" }, h("div", { class: "in-sub" }, lampEl("dark"), "Acknowledged by a gap"), ack.map((t) => idChip(t, r.acknowledged[t]))) : null,
      !r.untraced.length ? h("div", { class: "p-empty-line" }, "Every trace target the vault gives this app is owned by a component.") : null,
      best("Targets are what a vault-mode design must trace: the app's allocated requirement rows, every contract it provides or consumes, and the criteria of each epic that lists it.")));
    const mentioned = Object.entries(d.mentions).filter(([id]) => !ownedIds.has(id) && !r.untraced.includes(id) && id !== d.appId && id !== D.initiative);
    if (mentioned.length) out.push(card("Mentioned, not owned", mentioned.map(([id, where]) => idChip(id, where.join(", ")))));
    if (r.unresolved.length) out.push(card("Cited, but not in the vault", r.unresolved.map((u) => h("div", { class: "gap" }, lampEl("caution"), " ", h("b", {}, u.id), ` in ${u.where.replace("trace:", "the trace of ").replace("challenge:", "the challenge in ")}`))));
    return out;
  }
  function idChip(id, note) {
    const k = vaultKey(id);
    return h("a", { class: "ref-chip in-id" + (k ? "" : " ref-dead"), "data-ref": k, title: k ? `${titleOf(k)}${note ? " · " + note : ""}` : "not in this vault" }, h("span", { class: "rid" }, id), note ? h("span", { class: "in-via" }, note) : null);
  }
  function dataTab(app, d) {
    const m = d.data_model, out = [];
    if (m.parsed_from === "erDiagram") {
      out.push(best("Entities and relationships from the design's erDiagram."), erDiagram(m));
    } else if (m.entities.length) {
      out.push(best(`No erDiagram, so these are read from its ${m.parsed_from}: best effort, no relationships.`),
        card(null, m.entities.map((x) => h("div", { class: "in-entity" }, h("b", {}, x.name), x.text ? h("div", {}, prose(x.text)) : null))));
    } else out.push(card(null, h("div", { class: "p-empty-line" }, m.raw ? "The data model is free text this page cannot draw; it is below as written." : "The design has no data model section.")));
    if (m.stores.length) out.push(card("Persistence", m.stores.map((x) => h("div", {}, prose(x)))));
    out.push(raw(m.raw, "The data model as written"));
    return out;
  }
  const CARD = { "||": "1", "|o": "0..1", "o|": "0..1", "}o": "0..n", "o{": "0..n", "}|": "1..n", "|{": "1..n" };
  const cardinality = (c) => `${CARD[c.slice(0, 2)] || "?"} to ${CARD[c.slice(-2)] || "?"}`;
  /* The data model's entities, drawn at a size the fields can be read at, scrolled to the entity most things relate to,
     with a minimap; "Whole" puts every entity in view. */
  function erDiagram(m) {
    const holder = h("div", { class: "in-er" }), wrap = h("div", { class: "in-er-wrap" }, holder);
    const nodes = m.entities.map((x) => ({ id: "e:" + x.name, kind: "entity", w: 190, h: 30 + Math.max(1, x.fields.length) * 17, x }));
    const edges = m.relationships.map((r) => ({ from: "e:" + r.from, to: "e:" + r.to, label: `${r.label} · ${cardinality(r.cardinality)}`, title: `${r.from} ${r.label} ${r.to}: ${cardinality(r.cardinality)} (${r.cardinality})` }));
    const lay = layered(nodes, edges, { gapX: 150, gapY: 18, minColW: 150, gapTB: 60, gapYTB: 18, dir: "auto", fit: { w: 320, h: 420 } });
    const svg = s("svg", { class: "inside-svg er", role: "img", "aria-label": "Data model" }, holder);
    defsFor(svg);
    drawLayout(svg, lay, {
      entity: (g, b) => {
        const x = b.node.x, grp = s("g", { class: "in-node in-entity-box", "data-entity": x.name }, g);
        s("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 6, class: "in-box-face" }, grp);
        s("rect", { x: b.x, y: b.y, width: b.w, height: 24, rx: 6, class: "in-entity-head" }, grp);
        s("text", { x: b.x + 10, y: b.y + 16, class: "in-box-name small" }, grp).textContent = fit(x.name, b.w - 20, 12.5, 600);
        x.fields.forEach((f, i) => {
          s("text", { x: b.x + 10, y: b.y + 40 + i * 17, class: "in-field" }, grp).textContent = fit(`${f.name} ${f.type}`, b.w - 50, 11);
          if (f.keys.length) s("text", { x: b.x + b.w - 8, y: b.y + 40 + i * 17, "text-anchor": "end", class: "in-field-key" }, grp).textContent = f.keys.join(" ");
        });
      },
    });
    const related = {};
    for (const e of edges) for (const id of [e.from, e.to]) related[id] = (related[id] || 0) + 1;
    const main = Object.values(lay.box).sort((a, b) => (related[b.node.id] || 0) - (related[a.node.id] || 0))[0];
    sized(svg, holder, boundsOf(Object.values(lay.box)), 14, { open: "read", key: "er", focus: main, frame: wrap });
    return wrap;
  }
  function apiTab(app, d) {
    if (!d.api.length) return [card(null, h("div", { class: "p-empty-line" }, "The design has no ### <Component> public surface under API contracts."))];
    return d.api.map((a) => card(null, h("h3", {}, a.component_found ? h("a", { onclick: () => go(key(app, "c", a.component), { reset: true }) }, a.heading) : h("span", { class: "gap" }, a.heading, " (names no component)")),
      a.operations.length ? h("ul", { class: "in-ops" }, a.operations.map((op) => h("li", {}, prose(op)))) : h("div", { class: "p-empty-line" }, "No operations listed."), raw(a.raw, "As written")));
  }
  function tableTab(field, cols) {
    return (app, d) => {
      const rows = d[field];
      if (!rows.length) return [card(null, h("div", { class: "p-empty-line" }, `The design has no ${field.replace("_", " ")} table.`))];
      return [h("table", { class: "t in-table" }, h("tr", {}, cols.map((c) => h("th", {}, c.replace(/_/g, " ")))),
        rows.map((r) => h("tr", {}, cols.map((c) => h("td", {}, c === "severity" && r[c] ? h("span", { class: "pill" }, r[c]) : prose(r[c] || ""))))))];
    };
  }
  function adrTab(app, d) {
    if (!d.adrs.length) return [card(null, h("div", { class: "p-empty-line" }, "The design lists no ADRs."))];
    return [best("The team's ADRs, keyed by this design: ADR-0001 here is not the vault's ADR-0001."),
      h("ul", { class: "mini-list" }, d.adrs.map((a) => h("li", {}, a.found ? h("a", { class: "in-adr", onclick: () => go(key(app, "adr", a.id), { reset: true }) }, h("b", {}, a.id), " ", a.adr_title || a.title)
        : h("span", { class: "gap" }, h("b", {}, a.id), ` ${a.title}: its file ${a.href} is not there`), a.status ? h("span", { class: "pill" }, a.status) : null)))];
  }
  function opsTab(app, d) {
    const o = d.operations, rows = [["Deploy", o.deploy], ["Monitor", o.monitor], ["Scale", o.scale], ...Object.entries(o.other || {})];
    return [best("IDs named here are mentioned, not owned: the format has no component for running the service."),
      card(null, h("div", { class: "facts" }, rows.flatMap(([label, v]) => [h("div", { class: "fl" }, label), v ? h("div", {}, prose(v)) : h("div", { class: "gap" }, `no ${label} line`)])))];
  }
  function glossaryTab(app, d) {
    if (!d.context) return [card(null, h("div", { class: "p-empty-line" }, "No CONTEXT.md beside the design, so no glossary."))];
    return [card(null, d.context.glossary.map((g) => h("div", { class: "in-term" }, h("b", {}, g.term), h("div", {}, prose(g.definition)), g.not_to_be_confused_with ? h("div", { class: "muted small" }, "Not to be confused with: ", prose(g.not_to_be_confused_with)) : null)))];
  }

  /* Key flows: each sequence diagram drawn from its mermaid source, stepped through; other diagrams as source.
     The explorer's flow player plays vault lanes only, so a design's flow is drawn here; one the design ties to a
     vault flow (FLO-nnn in its title) can be played there too. */
  function flowsTab(app, d) {
    const all = [...d.flows.map((f) => ({ ...f, from: "Key flows" })), ...d.diagrams.map((f) => ({ ...f, from: "Supporting diagrams" }))];
    if (!all.length) return [card(null, h("div", { class: "p-empty-line" }, "The design draws no flow."))];
    return all.map((f, i) => {
      const flo = (f.title || "").match(/\bFLO-\d{3}\b/), fk = flo ? keyForId(flo[0]) : null;
      const head = h("h3", {}, f.title || `${f.from}, line ${f.line}`, fk && FLOW[fk] ? h("button", { class: "btn tiny", onclick: () => go(fk, { reveal: true }) }, `▶ Play ${flo[0]} in the vault`) : null);
      if (f.kind !== "sequenceDiagram") return card(null, head, h("div", { class: "muted small" }, `${f.kind || "a diagram"}, shown as its source`), h("pre", { class: "in-src" }, f.mermaid));
      return card(null, head, sequence(app, d, f, `${app}:${i}`));
    });
  }
  const SEQ_MSG = /^\s*([^\s:>-][^:>]*?)\s*(-->>|->>|-->|->|--x|-x|--\)|-\))\s*[+-]?\s*([^:]+?)\s*:\s*(.*)$/;
  const SEQ_NOTE = /^\s*note\s+(?:over|left of|right of)\s+([^:]+?)\s*:\s*(.*)$/i;
  function parseSequence(text) {
    const parts = [], steps = [], seen = new Set();
    const add = (id, name) => { if (!seen.has(id)) { seen.add(id); parts.push({ id, name: name || id }); } };
    for (const line of text.split("\n").slice(1)) {
      const p = line.match(/^\s*(?:participant|actor)\s+(\S+)(?:\s+as\s+(.+?))?\s*$/);
      if (p) { add(p[1], p[2]); continue; }
      const m = line.match(SEQ_MSG);
      if (m) { add(m[1].trim()); add(m[3].trim()); steps.push({ kind: m[2].startsWith("--") ? "reply" : "send", from: m[1].trim(), to: m[3].trim(), text: m[4].trim() }); continue; }
      const n = line.match(SEQ_NOTE);
      if (n) { const over = n[1].split(",").map((x) => x.trim()); over.forEach((x) => add(x)); steps.push({ kind: "note", over, text: n[2].trim() }); continue; }
      const block = line.match(/^\s*(loop|alt|opt|else|par|critical|break)\b\s*(.*)$/);
      if (block) steps.push({ kind: "block", text: `${block[1]} ${block[2]}`.trim() });
    }
    return { parts, steps };
  }
  function sequence(app, d, f, id) {
    const seq = parseSequence(f.mermaid), n = seq.steps.length;
    const box = h("div", { class: "in-seq", "data-seq": id });
    if (st.step[id] === undefined) st.step[id] = 0;
    const comp = (name) => d.components.find((c) => c.name.toLowerCase() === name.toLowerCase());
    const node = (name) => D.nodes.find((x) => x.title.toLowerCase() === name.toLowerCase());
    function draw() {
      box.innerHTML = "";
      const cur = st.step[id], LW = 128, RH = 30, top = 42, W = seq.parts.length * LW, H = top + n * RH + 16;
      const x = (pid) => seq.parts.findIndex((p) => p.id === pid) * LW + LW / 2;
      const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "inside-svg seq", role: "img", "aria-label": f.title || "sequence" });
      defsFor(svg);
      seq.parts.forEach((p) => {
        const cx = x(p.id), c = comp(p.name), v = node(p.name);
        s("line", { x1: cx, x2: cx, y1: top - 6, y2: H - 6, class: "seq-lane" }, svg);
        const g = s("g", { class: "seq-head" + (c || v ? " pick" : "") }, svg);
        s("rect", { x: cx - LW / 2 + 6, y: 4, width: LW - 12, height: 28, rx: 6 }, g);
        if (v) Icons.put(g, Icons.name(v.key), cx - LW / 2 + 18, 18, 13, "node-glyph");
        s("text", { x: cx + (v ? 6 : 0), y: 22, "text-anchor": "middle" }, g).textContent = fit(p.name, LW - (v ? 34 : 20), 11.5, 600);
        s("title", {}, g).textContent = p.name + (c ? ": a component of this design" : v ? ": on the vault's map" : "");
        if (c) g.addEventListener("click", () => go(key(app, "c", c.name), { reset: true }));
        else if (v) g.addEventListener("click", () => go(v.key, { reset: true }));
      });
      seq.steps.forEach((stp, i) => {
        const y = top + i * RH + RH / 2 + 4, on = i === cur, cls = "seq-step" + (on ? " on" : i > cur ? " later" : "");
        const g = s("g", { class: cls, "data-i": i }, svg);
        if (stp.kind === "note" || stp.kind === "block") {
          const xs = (stp.over || seq.parts.map((p) => p.id)).map(x), x0 = Math.min(...xs) - LW / 2 + 10, x1 = Math.max(...xs) + LW / 2 - 10;
          s("rect", { x: x0, y: y - 11, width: x1 - x0, height: 20, rx: 4, class: stp.kind === "note" ? "seq-note" : "seq-block" }, g);
          s("text", { x: (x0 + x1) / 2, y: y + 3, "text-anchor": "middle", class: "seq-text" }, g).textContent = fit(stp.text, x1 - x0 - 12, 11);
        } else if (stp.from === stp.to) {
          const cx = x(stp.from);
          s("path", { d: `M${cx},${y - 8}h26v14h-24`, class: "seq-msg" + (stp.kind === "reply" ? " reply" : ""), "marker-end": "url(#in-arrow)" }, g);
          s("text", { x: cx + 32, y: y + 3, class: "seq-text" }, g).textContent = fit(stp.text, LW + 40, 11);
        } else {
          const x0 = x(stp.from), x1 = x(stp.to), dir = Math.sign(x1 - x0);
          s("line", { x1: x0, x2: x1 - dir * 3, y1: y + 4, y2: y + 4, class: "seq-msg" + (stp.kind === "reply" ? " reply" : ""), "marker-end": "url(#in-arrow)" }, g);
          s("text", { x: (x0 + x1) / 2, y: y - 1, "text-anchor": "middle", class: "seq-text" }, g).textContent = fit(stp.text, Math.abs(x1 - x0) - 10, 11);
        }
        s("title", {}, g).textContent = `${i + 1}. ${describe(stp, seq)}`;
        g.addEventListener("click", () => { st.step[id] = i; draw(); });
      });
      const ctl = h("div", { class: "seq-ctl" },
        h("button", { class: "btn tiny", disabled: cur <= 0 ? true : null, onclick: () => { st.step[id] = Math.max(0, cur - 1); draw(); } }, "‹ Back"),
        h("span", { class: "muted small", "aria-live": "polite" }, n ? `Step ${cur + 1} of ${n}` : "No steps read"),
        h("button", { class: "btn tiny", disabled: cur >= n - 1 ? true : null, onclick: () => { st.step[id] = Math.min(n - 1, cur + 1); draw(); } }, "Next ›"),
        FX.on && n > 1 ? h("button", { class: "btn tiny", onclick: () => play(id, n, draw) }, st.playing === id ? "Pause" : "▶ Play") : null);
      svg.style.width = W + "px";
      box.append(h("div", { class: "in-scroll" }, svg), ctl, n ? h("div", { class: "seq-now" }, `${cur + 1}. `, prose(describe(seq.steps[cur], seq))) : null);
    }
    draw();
    return box;
  }
  const describe = (stp, seq) => {
    const name = (id) => ((seq.parts.find((p) => p.id === id) || {}).name || id);
    return stp.kind === "note" ? `Note over ${stp.over.map(name).join(" and ")}: ${stp.text}` : stp.kind === "block" ? stp.text : `${name(stp.from)} ${stp.kind === "reply" ? "answers" : "→"} ${name(stp.to)}: ${stp.text}`;
  };
  let timer = 0;
  function play(id, n, draw) {
    clearInterval(timer);
    if (st.playing === id) { st.playing = null; draw(); return; }
    st.playing = id; if (st.step[id] >= n - 1) st.step[id] = 0; draw();
    timer = setInterval(() => {
      if (!document.querySelector(`[data-seq="${CSS.escape(id)}"]`) || reducedMotion()) { clearInterval(timer); st.playing = null; return; }
      if (st.step[id] >= n - 1) { clearInterval(timer); st.playing = null; draw(); return; }
      st.step[id]++; draw();
    }, 1100);
  }

  /* ------------------------------------------------------------ the panel: the design, its parts, its problems */
  function panel(k) {
    const p = parse(k), d = design(p.app);
    if (!APPS[p.app]) return [h("div", { class: "p-empty" }, `Nothing here is called ${k}.`)];
    if (!d && p.kind !== "ct") return [h("div", { class: "p-empty" }, `The ${appTitle(p.app)} team's design is not loaded.`)];
    if (p.kind === "c") return componentPanel(p.app, d, p.name);
    if (p.kind === "ct") return containerPanel(p.app, p.name);
    if (p.kind === "adr") return adrPanel(p.app, d, p.name);
    if (p.kind === "problems") return problemsPanel(p.app, d);
    return designPanel(p.app, d);
  }
  const phead = (kind, title, ...rest) => h("div", { class: "p-head" }, h("div", { class: "kind" }, kind), h("h2", {}, title), ...rest.filter(Boolean));
  const sec = (title, n, ...kids) => Panel.section(title, n, ...kids);
  function designPanel(app, d) {
    const fm = d.frontmatter;
    return [phead(`Team design · ${d.path.split("/").slice(-1)[0]}`, d.title || designWord(app), h("div", { class: "p-meta" }, statusPill(app), problemsChip(app, { keep: true })),
      h("div", { class: "p-actions" }, designLink(d), linkChips(app))),
    h("div", { class: "p-body" },
      d.overview.text ? h("div", { class: "prose-text in-prose" }, prose(d.overview.text)) : null,
      sec("Boundaries", null, h("div", { class: "facts" }, h("div", { class: "fl" }, "Inside"), h("div", {}, prose(d.boundaries.inside || "not written")), h("div", { class: "fl" }, "Outside"), h("div", {}, prose(d.boundaries.outside || "not written")))),
      sec("Gaps", fm.gaps.length, fm.gaps.map((g) => h("div", { class: "in-gap" }, h("b", {}, g.id || "a gap"), " ", prose(g.what || ""), h("div", { class: "ml-sub" }, [g.acknowledged_by ? `acknowledged by ${g.acknowledged_by}` : "acknowledged by nobody", g.why ? `; why: ${g.why}` : "; no why", g.revisit ? `; revisit ${g.revisit}` : "; no revisit"].join(""))))),
      sec("Deferred", fm.deferred.length, fm.deferred.map((x) => h("div", { class: "in-gap" }, h("b", {}, x.id), " ", x.section || "", ": ", prose(x.reason || "")))),
      sec("Open questions", d.open_questions.length, d.open_questions.map((q) => h("div", { class: "in-gap" }, q.challenges.length ? lampEl("caution", "Challenges a vault item: needs you") : null, " ", h("b", {}, q.id), " ", q.title,
        q.challenges.length ? h("div", {}, "Challenges ", q.challenges.map((id) => idChip(id))) : null, q.other.Scenario ? h("div", { class: "ml-sub" }, "Scenario: ", prose(q.other.Scenario)) : null,
        q.affects_ids.length ? h("div", { class: "ml-sub" }, "Affects ", q.affects_ids.map((id) => idChip(id))) : null))),
      sec("The vault it answers to", null, h("div", { class: "p-note" }, d.vault.app ? `${d.vault.app}, ${d.vault.commits.length ? "at " + d.vault.commits.join(" and ") : "at no commit it names"}` : "No vault prereq: a requirements-mode design.",
        d.vault.source === "inferred" ? h("span", { class: "heuristic" }, " Inferred from the prereq path and the citations; the format has no vault: field.") : null)),
      sec("Trace", null, h("div", { class: "p-note" }, `${plural(d.targets.length, "target")} the vault gives it; ${d.targets.length - d.resolved.untraced.length} owned, ${Object.keys(d.resolved.acknowledged).length} acknowledged by a gap, ${d.resolved.untraced.length - Object.keys(d.resolved.acknowledged).length} missed. Owners are ${sourceWord(d)}.`),
        h("button", { class: "btn tiny", onclick: () => { st.tab = "trace"; open(app, "components", { keepTrail: true }); } }, "The trace, by component")))];
  }
  function componentPanel(app, d, name) {
    const c = d.components.find((x) => x.name === name);
    if (!c) return [h("div", { class: "p-empty" }, `The ${designWord(app)} has no component called ${name}.`)];
    const list = d.trace[name] || [], api = d.api.find((a) => a.component.toLowerCase() === name.toLowerCase());
    const oqs = d.open_questions.filter((q) => new RegExp(`\\b${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i").test(q.affects));
    return [phead(`Component · ${designWord(app)}`, name, h("div", { class: "p-meta" }, h("span", { class: "pill" }, `line ${c.line}`), oqs.length ? levelPill("caution", `${oqs.map((q) => q.id).join(", ")} affects it`) : null), linkChips(app),
      h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => open(app, "components", { keepTrail: true }) }, "Show it inside"), designLink(d, null, `, line ${c.line}`))),
    h("div", { class: "p-body" },
      h("div", { class: "big-q" }, prose(c.responsibility || "No Responsibility line.")),
      sec("Vault IDs it owns", list.length, list.length ? h("ul", { class: "mini-list" }, list.map((e) => h("li", {}, idChip(e.id), h("div", { class: "ml-sub" }, `found in ${e.via.join(", ")}`, d.trace_source === "inferred" ? h("span", { class: "heuristic" }, " · inferred") : null))))
        : h("div", { class: "p-empty-line" }, "It cites no trace target."), list.length && d.trace_source === "inferred" ? h("div", { class: "p-note heuristic" }, "Inferred: the format records no trace, so an ID cited in passing reads as owned.") : null),
      sec("Its bullets", null, h("div", { class: "facts" }, [["Owns", c.owns], ["Depends on", c.depends_on], ["Exposes", c.exposes], ["Container", c.container], ...Object.entries(c.other)].flatMap(([l, v]) =>
        [h("div", { class: "fl" }, l), v ? h("div", {}, prose(v)) : h("div", { class: l === "Container" ? "muted" : "gap" }, l === "Container" ? "not named (the format has no Container bullet)" : `no ${l} line`)]))),
      c.depends_on_components.length || c.depends_on_other.length ? sec("Depends on", null, c.depends_on_components.map((x) => h("a", { class: "ref-chip", onclick: () => go(key(app, "c", x), {}) }, x)), c.depends_on_other.map((x) => h("span", { class: "ref-chip ref-dead", title: "neither a component nor an integration point" }, x))) : null,
      api ? sec("Public surface", api.operations.length, h("ul", { class: "in-ops" }, api.operations.map((op) => h("li", {}, prose(op))))) : null,
      oqs.length ? sec("Open questions on it", oqs.length, oqs.map((q) => h("div", {}, h("b", {}, q.id), " ", q.title))) : null)];
  }
  function containerPanel(app, name) {
    const c = CONT[app], r = c && c.rows.find((x) => x.name === name), d = design(app);
    if (!r) return [h("div", { class: "p-empty" }, `${appTitle(app)}'s page has no container called ${name}.`)];
    const same = d ? d.components.filter((x) => x.name.toLowerCase() === name.toLowerCase()) : [];
    const pk = Reader.keyFor(app);
    return [phead(`Main container · ${appTitle(app)}`, name, h("div", { class: "p-meta" }, statePill(r.state), r.proposedBy ? h("span", { class: "pill" }, "proposed by " + r.proposedBy) : null),
      h("div", { class: "p-actions" }, pk ? h("button", { class: "btn", onclick: () => go(pk, {}) }, "Open the page") : null)),
    h("div", { class: "p-body" }, h("div", { class: "big-q" }, r.job),
      sec("Serves", r.serves.length, r.serves.map((id) => refChip(id))), sec("Uses", r.uses.length, r.uses.map((id) => refChip(id))),
      sec("Components in it", null, same.length ? same.map((x) => h("a", { class: "ref-chip", onclick: () => go(key(app, "c", x.name), {}) }, x.name, h("span", { class: "rid" }, "same name"))) : null,
        h("div", { class: "p-note heuristic" }, d ? "The format has no component-to-container link, so only a component of the same name is shown." : "No team design is loaded.")),
      h("div", { class: "p-note" }, `From the row on line ${r.line} of the app page.`))];
  }
  function adrPanel(app, d, id) {
    const a = d.adrs.find((x) => x.id === id);
    if (!a) return [h("div", { class: "p-empty" }, `The ${designWord(app)} lists no ${id}.`)];
    return [phead(`Team ADR · ${designWord(app)}`, `${a.id}: ${a.adr_title || a.title}`, h("div", { class: "p-meta" }, statePill(a.status), a.date ? h("span", { class: "pill" }, a.date) : null),
      h("div", { class: "p-note" }, `${a.file || a.href}; keyed by the design, so it is not the vault's ${a.id}.`)),
    h("div", { class: "p-body" }, !a.found ? h("div", { class: "gap" }, `Its file ${a.href} is not there.`) : null,
      sec("Context", null, a.context ? h("div", { class: "prose-text in-prose" }, prose(a.context)) : null), sec("Decision", null, a.decision ? h("div", { class: "prose-text in-prose" }, prose(a.decision)) : null),
      sec("Alternatives considered", (a.alternatives || []).length, (a.alternatives || []).map((x) => h("div", { class: "in-gap" }, h("b", {}, x.option), " ", prose(x.why_not)))),
      sec("Consequences", null, Object.keys(a.consequences || {}).length ? h("div", { class: "facts" }, Object.entries(a.consequences).flatMap(([l, v]) => [h("div", { class: "fl" }, l), h("div", {}, prose(v))])) : null))];
  }
  function problemsPanel(app, d) {
    const byLine = d.problems.slice().sort((p, q) => (p.line || 1e9) - (q.line || 1e9));
    return [phead(`Team design · ${d.path.split("/").slice(-1)[0]}`, `What this page could not read`, h("p", { class: "p-lede" }, d.problems.length ? `${plural(d.problems.length, "thing")} in the ${designWord(app)} could not be read as the format says. Each is shown as it is; none is filled with a guess.` : "Every part of the design read as the format says.")),
    h("div", { class: "p-body" }, sec("Could not read", d.problems.length, d.problems.length ? h("ol", { class: "in-problems" }, byLine.map((p) => h("li", { "data-line": p.line || "" }, h("span", { class: "in-line" }, p.line ? `line ${p.line}` : "no line"), h("b", {}, p.section), " ", p.message))) : null),
      sec("Cited, but not in the vault", d.resolved.unresolved.length, d.resolved.unresolved.map((u) => h("div", { class: "gap" }, h("b", {}, u.id), ` in ${u.where.replace("trace:", "the trace of ").replace("challenge:", "the challenge in ")}`))))];
  }

  /* ------------------------------------------------------------ what the rest of the page asks of it */
  /* A vault item's owners in each design, or that none owns it: for a requirement, contract or epic criterion. */
  function ownedBy(id, opts = {}) {
    const owners = OWNERS[id] || [], untraced = UNTRACED[id] || [], built = builtBy(id, opts);
    if (!owners.length && !untraced.length && !built.length) return opts.inline ? null : (Object.keys(DES).length ? sec("Inside the teams' designs", null, h("div", { class: "p-empty-line" }, "No loaded design traces it.")) : null);
    const rows = [
      ...owners.map((o) => h("div", { class: "in-owner" }, "Owned by ", h("a", { onclick: () => go(key(o.app, "c", o.component), {}) }, o.component), ` (${designWord(o.app)})`,
        opts.inline ? null : h("span", { class: "ml-sub" }, ` found in ${o.via.join(", ")}${DES[o.app].trace_source === "inferred" ? ", inferred" : ""}`))),
      ...untraced.filter((u) => !owners.some((o) => o.app === u.app)).map((u) => h("div", { class: "in-owner untraced " + (u.gap ? "ack" : "missed"), title: u.gap ? `${u.gap} in the ${designWord(u.app)} acknowledges it` : `No component of the ${designWord(u.app)} owns it, and no gap says so` },
        lampEl(u.gap ? "dark" : "caution"), ` Untraced in the ${designWord(u.app)}`, u.gap ? `, acknowledged by ${u.gap}` : ", and no gap says so")),
      ...built];
    return opts.inline ? h("div", { class: "in-owners inline" }, rows) : sec("Inside the teams' designs", null, rows, owners.length || untraced.length ? h("div", { class: "p-note heuristic" }, "Owners are inferred where a design records no Trace table.") : null);
  }
  /* The other half of the trace: which story of a team's build plan builds the item ("Built by S-03 (Booking plan)"). */
  function builtBy(id, opts) {
    return Plan.built(id).map((b) => h("div", { class: "in-owner built", "data-built": b.story }, "Built by ", h("a", { onclick: () => Plan.reveal(b.app, b.story) }, b.story),
      ` (${Plan.planWord(b.app)})`, opts.inline ? null : h("span", { class: "ml-sub" }, ` ${b.name}`)));
  }
  function challengeSection(k) {
    const list = challenge(k);
    if (!list) return null;
    return sec("Challenged by a team's design", list.length, list.map((c) => h("div", { class: "in-challenge" }, lampEl("caution", "Needs you: challenged by a team's design"), " ",
      h("a", { onclick: () => go(key(c.app, "", ""), {}) }, `${c.oq} in the ${designWord(c.app)}`), `: ${c.title}`, c.scenario ? h("div", { class: "ml-sub" }, "Scenario: ", prose(c.scenario)) : null,
      c.affects.length ? h("div", { class: "ml-sub" }, "Affects ", c.affects.map((id) => idChip(id))) : null)),
    h("div", { class: "p-note" }, "This lamp is the design's, not attention.lights: it stays lit until the vault records the challenge (/planner:challenge)."));
  }
  function homeSection() {
    const all = Object.values(CHALLENGED).flat();
    if (!all.length) return null;
    return sec("Challenged by a team's design", all.length, h("p", { class: "p-note" }, "A senior's design question that challenges the vault. Lit by the design, not by attention.lights, until the vault records the challenge."),
      h("ul", { class: "lights" }, all.map((c) => h("li", {}, h("button", { class: "challenge-row", "data-ref": keyForId(c.id) }, lampEl("caution"),
        h("span", {}, h("span", { class: "what" }, `${c.id} challenged by ${c.oq}`), h("span", { class: "why" }, `${appTitle(c.app)} design: ${c.title}${c.scenario ? " " + shorten(c.scenario, 110) : ""}`)))))));
  }
  /* The design's state, for the stage ladder and the Engineering door. */
  function statusCell(app) {
    const d = design(app);
    if (!d) return h("div", { class: "small" }, h("span", { class: "muted" }, "not loaded "), h("a", { class: "small", onclick: (ev) => { ev.stopPropagation(); open(app, "context"); } }, "Inside ›"));
    return h("div", { class: "in-status-cell" }, statusPill(app), h("div", {}, problemsChip(app)), h("a", { class: "small", onclick: (ev) => { ev.stopPropagation(); open(app, "components"); } }, "Inside ›"));
  }
  function doorEntry(app) {
    const d = design(app);
    return h("div", { class: "in-door" }, h("h3", {}, "Inside"), h("div", { class: "in-door-row" }, d ? statusPill(app) : h("span", { class: "muted small" }, "the team's design is not loaded"), d ? problemsChip(app) : null),
      h("div", { class: "in-door-row", "data-readiness": Plan.readiness(app).id }, Plan.readinessPill(app), h("span", { class: "muted small" }, Plan.readiness(app).counts)),
      h("div", { class: "in-door-row" }, LEVELS.map(([l, word]) => h("button", { class: "chip", "data-inside": l, onclick: () => open(app, l) }, word))));
  }
  function sideEntry(app) {
    return h("button", { class: "side-kid side-inside", "data-inside": app, onclick: () => open(app, design(app) ? "components" : "containers"), title: "Inside this app: context, containers, components and build plan" }, h("span", { class: "side-label" }, "Inside this app ›"));
  }
  function highlight(k) {
    $$("#inside-stage [data-key]").forEach((g) => g.classList.toggle("picked", g.dataset.key === k));
    if (st.level === "context") MapGroups.highlight(k);
  }

  // Double-click an app on the map, or one beside it on the context level, to go inside it.
  document.addEventListener("dblclick", (ev) => {
    const g = ev.target.closest("#board g.hit[data-key]");
    if (!g || !APPS[g.dataset.key] || !["map", "inside"].includes(App.view)) return;
    ev.preventDefault();
    open(g.dataset.key, App.view === "map" ? "containers" : "context", { from: g.getBoundingClientRect() });
  });

  const designKey = () => (st.app && design(st.app) ? key(st.app) : "");
  /* What plan.js draws with: the layout and drawing helpers above, and the chips that link into the vault. */
  const kit = { layered, drawLayout, defsFor, sized, placeDrawings, boundsOf, fit, idChip, prose, chipCard, open, key };
  return { open, boot, hash, render, kit, designKey, highlight, panel, ent: entOf, ownedBy, challenge, challengeSection, homeSection, statusCell, doorEntry, sideEntry, statusPill, problemsChip,
    layered, parseSequence, st, LEVELS, TABS, OWNERS, UNTRACED, CHALLENGED };
})();
View("inside", { label: "Inside", title: "Inside this app: context, containers, components and build plan", render: Inside.render, highlight: Inside.highlight });
