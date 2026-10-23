/* The map at scale: the cockpit grouped by domain or by business capability, and focus on one app.

   - Domain: one cluster per `domain:` on the app pages (CONVENTIONS, "Domains"), plus "No domain" and the outside
     parties. Past 12 apps every cluster starts closed. A closed cluster is one lamp: its apps' worst light, its
     counts, and a small lamp per app; it opens in place.
   - Capability: one region per capability an app carries a requirement of (allocation rows), or, with no
     allocation, that an epic listing the app delivers. An app with several is drawn once, in the region of the one
     it carries most of, with a "+2 capabilities" tab; each other region lists it in its "Also carried by" row.
     Hover the tab, or pick the app, and those regions light.
   - Focus: one app with its direct neighbors only.

   Pinned positions still hold inside a cluster: its apps are placed in the order of their pinned columns, then
   rows (pins.py), so an app keeps its place relative to its neighbors from build to build. Every lamp is
   attention.lights, through MapView.lamp. Contracts between two drawn boxes share one duct with one lamp.

   Nothing sits on anything else. Regions are sized to what they hold and packed on shelves with gutters; then every
   box, name, tab and toggle is an obstacle, and each duct's lamp takes the first point along its duct, outward from
   the middle, that touches none of them (place). A lamp that fits nowhere becomes a round count, placed the same
   way. #selftest checks that no two drawn boxes or labels intersect.

   Wires are orthogonal and routed around every box and region they do not join, through the gaps between regions
   (wires.js), so a long link never runs across another region. Showing cross-region links only for the picked app was
   the other way to cut the clutter; it hides how the apps connect until someone asks, and the routed map stays
   readable on the 24-app stress vault. #selftest checks that no wire runs through a box it does not join. */
const MapGroups = (() => {
  const W = 176, H = 66, GX = 206, GY = 92, PAD = 22, HEAD = 50, CW = 236, CH = 118, GAP = 70, CAP_GAP = 96, CHIP_H = 20, CHIP_GAP = 6;
  const st = MapView.st;
  const byPin = (a, b) => (NODE[a].col - NODE[b].col) || (NODE[a].row - NODE[b].row) || cmp(a, b);
  const worst = (levels) => levels.sort((p, q) => rank(q) - rank(p))[0] || "dark";
  /* What the grouped map and the focus drawing add to the cockpit's key (view-map.js has the rest). */
  const { bx } = Legend;
  Legend.define("cluster.open", [bx({ stroke: "rule", w: 1.4, rx: 5 })], "Faint frame: a group, with its apps drawn inside it");
  Legend.define("cluster.outside", [bx({ stroke: "ink-4", w: 1.4, rx: 5, dash: "3 3.5" })], "Dashed frame: the outside services, kept apart from our apps");
  Legend.define("cluster.closed", [bx({ fill: "unlit", stroke: "rule-3", w: 1.2, rx: 4 }), bx({ fill: "caution", x: 3, y: 4, width: 3, height: 8, rx: 1.5 })], "Card with a colored edge: a closed group, in its most urgent status; click to open");
  Legend.define("cluster.mini", [bx({ fill: "caution", x: 5, y: 6, width: 6, height: 4, rx: 1 }), bx({ fill: "unlit", x: 13, y: 6, width: 6, height: 4, rx: 1 }), bx({ fill: "warning", x: 21, y: 6, width: 6, height: 4, rx: 1 })], "Row of small marks: one per app in a closed group, each in its status color");
  Legend.define("cluster.also-tab", [bx({ fill: "deck-3", stroke: "rule-3", w: 1, height: 8, y: 4, rx: 4 }), { k: "text", t: "+2", fill: "ink-2", y: 11, size: 8 }], "Small tab above a box: the app delivers other capabilities too");
  Legend.define("cluster.also-chip", [bx({ fill: "deck-2", stroke: "rule-3", w: 1.2, dash: "3 2.5", height: 8, y: 4, rx: 4 })], "Dashed chip: an app drawn in another box that delivers this capability too");
  const LOOKS = {
    "cluster.open": ".cluster-frame:not(.outside)", "cluster.outside": ".cluster-frame.outside", "cluster.closed": "g.cluster-lamp", "cluster.mini": "rect.mini-lamp",
    "cluster.also-tab": "g.also-tab", "cluster.also-chip": "g.also-chip",
  };
  const LOOKS_FOCUS = { "picked": "g.hit.picked, path.duct.picked, .focus-center" };
  const PARTIES = "grp:outside";

  function groups(mode) {
    const apps = D.nodes.filter((n) => n.kind === "app").map((n) => n.key), partners = D.nodes.filter((n) => n.kind !== "app").map((n) => n.key);
    let out = [];
    if (mode === "domain") {
      const by = {};
      for (const k of apps) (by[D.domains[k] || "No domain"] = by[D.domains[k] || "No domain"] || []).push(k);
      out = Object.entries(by).map(([label, members]) => ({ key: "grp:" + label, label, members: members.sort(byPin), ghosts: [], sub: "domain" }));
      const meanCol = (g) => g.members.reduce((n, k) => n + NODE[k].col, 0) / g.members.length;
      out.sort((a, b) => (a.label === "No domain") - (b.label === "No domain") || meanCol(a) - meanCol(b) || cmp(a.label, b.label));
      for (const g of out) if (g.label === "No domain") g.label = `No business area yet (${plural(g.members.length, "app")})`;
    } else {
      const regions = {};
      const region = (cap) => regions[cap] || (regions[cap] = { key: "cap:" + cap, cap, label: cap, members: [], ghosts: [], sub: "capability" });
      for (const k of apps) {
        const caps = (D.appCaps[k] || { caps: [] }).caps;
        if (!caps.length) { region("").members.push(k); continue; }
        region(caps[0]).members.push(k);
        caps.slice(1).forEach((c) => region(c).ghosts.push(k));
      }
      out = Object.values(regions).map((g) => {
        const e = g.cap ? ent(keyForId(g.cap)) : null;
        return Object.assign(g, { label: g.cap ? (e && e.title) || g.cap : `No capability yet (${plural(g.members.length, "app")})`, page: e ? e.key : "", members: g.members.sort(byPin), ghosts: g.ghosts.sort(byPin) });
      }).sort((a, b) => (a.cap === "") - (b.cap === "") || cmp(a.cap, b.cap));
    }
    if (partners.length) out.push({ key: PARTIES, label: "Outside services", members: partners.sort(byPin), ghosts: [], sub: "outside", outside: true });
    return out;
  }
  const isOpen = (g) => st.open.has(g.key) || (!st.shut.has(g.key) && D.map.apps.length <= MapView.CLUSTER_PAST);
  function toggle(g) { if (isOpen(g)) { st.open.delete(g.key); st.shut.add(g.key); } else { st.shut.delete(g.key); st.open.add(g.key); } rerender(); }
  function all(open) { const gs = [...groups("domain"), ...groups("capability")]; gs.forEach((g) => { if (open) { st.open.add(g.key); st.shut.delete(g.key); } else { st.shut.add(g.key); st.open.delete(g.key); } }); }

  /* ------------------------------------------------------------ layout: clusters on shelves, apps inside in pin order */
  /* Text width for laying out before drawing, in the page's own face. */
  const measure = (() => {
    const ctx = document.createElement("canvas").getContext("2d");
    return (text, size, weight) => { ctx.font = `${weight || 400} ${size}px ${getComputedStyle(document.body).fontFamily}`; return ctx.measureText(text).width; };
  })();
  /* "Also carried by" chips, wrapped into lines no wider than the region. */
  /* A drawn element's own box, as an obstacle; the estimate stands in only if the page has not laid it out. */
  function drawnBox(el, estimate) {
    const b = el.getBBox ? el.getBBox() : null;
    return b && b.width ? { x: b.x, y: b.y, w: b.width, h: b.height } : estimate;
  }
  const CHIP_TEXT = { size: 12, weight: 500 };
  /* The chips, wrapped into rows no wider than the region. A name too long for one line takes two, so the chip grows; each row is as
     tall as its tallest chip (row.h), and `rows.h` is the whole stack. */
  function chipLines(keys, width) {
    const lines = [];
    let line = [], x = measure("Also in", 11.5, 500) + 10;
    const close = () => { line.h = Math.max(CHIP_H, ...line.map((c) => c.h)); lines.push(line); line = []; };
    for (const k of keys) {
      const f = LabelFit.fit(titleOf(k), width - 34, CHIP_TEXT), widest = Math.max(...f.lines.map((l) => LabelFit.width(l, f.size, 500)));
      const w = Math.min(width, widest + 34), h = f.lines.length > 1 ? Math.ceil(f.lines.length * f.lh + 8) : CHIP_H;
      if (line.length && x + w > width) { close(); x = 0; }
      line.push({ k, x, w, h }); x += w + CHIP_GAP;
    }
    if (line.length) close();
    lines.h = lines.reduce((n, l) => n + l.h + CHIP_GAP, 0);
    return lines;
  }
  /* What a cluster says about itself: its worst light and the counts. */
  function clusterSays(g) {
    const levels = g.members.map(levelOf), lv = worst(levels.slice()), lit = levels.filter((l) => l !== "dark").length;
    const counts = LEVELS.filter((l) => l !== "dark").map((l) => [l, levels.filter((x) => x === l).length]).filter(([, n]) => n);
    const what = g.outside ? plural(g.members.length, "outside service") : plural(g.members.length, "app");
    const say = `${what}${lit ? ", " + counts.map(([l, n]) => `${n} ${LIGHT[l].word.toLowerCase()}`).join(", ") : ", all decided"}${g.ghosts.length ? `; ${plural(g.ghosts.length, "app")} drawn elsewhere also ${g.ghosts.length === 1 ? "delivers" : "deliver"} it` : ""}`;
    return { lv, lit, counts, say };
  }
  const NAME_TEXT = { size: 15, weight: 600 }, TITLE_TEXT = { size: 17, weight: 600 }, SAY_TEXT = { size: 11.5 };
  /* True when two clusters ({x, y, w, h}, top left) come closer than `gap`. */
  const near = (a, b, gap) => a.x < b.x + b.w + gap && b.x < a.x + a.w + gap && a.y < b.y + b.h + gap && b.y < a.y + a.h + gap;
  function layout(list, aspect, mode) {
    // a cluster holds ducts between its own boxes, so its gutters leave room for a count on each
    const gap = mode === "capability" ? CAP_GAP : GAP, gx = W + 60, gy = H + 62;
    for (const g of list) {
      g.isOpen = isOpen(g);
      const n = g.members.length;
      if (!g.isOpen) {
        // closed, the title and the line under it wrap, and the lamp grows by the lines they take beyond one each
        g.w = CW;
        const says = clusterSays(g);
        g.titleFit = LabelFit.fit(g.label, g.w - 16 - (says.lv !== "dark" ? 38 : 20), TITLE_TEXT);
        g.sayFit = LabelFit.fit(says.say, g.w - 36, SAY_TEXT);
        g.h = CH + Math.ceil((g.titleFit.lines.length - 1) * g.titleFit.lh + (g.sayFit.lines.length - 1) * g.sayFit.lh);
        continue;
      }
      g.cols = n === 0 ? 0 : g.outside ? Math.min(n, 4) : n <= 2 ? n : Math.min(3, Math.ceil(Math.sqrt(n)));
      g.rows = n ? Math.ceil(n / g.cols) : 0;
      g.w = Math.max(CW, PAD * 2 + g.cols * gx - (gx - W));
      g.alsoLines = g.ghosts.length ? chipLines(g.ghosts, g.w - PAD * 2) : [];
      g.nameFit = LabelFit.fit(g.label, g.w - PAD * 2, NAME_TEXT);  // the name takes a second line before it is ever cut
      g.headExtra = Math.ceil((g.nameFit.lines.length - 1) * g.nameFit.lh);
      // room above the first row for the "+2 capabilities" tabs, which stand just above their boxes
      const tabs = mode === "capability" && g.members.some((k) => ((D.appCaps[k] || { caps: [] }).caps.length > 1));
      g.top = HEAD + g.headExtra + (g.alsoLines.length ? g.alsoLines.h + 12 : 0) + (tabs ? 16 : 0);
      g.h = g.top + (g.rows ? g.rows * gy - (gy - H) : 0) + PAD;
    }
    for (const g of list) g.gap = gap;  // a dropped cluster keeps this far from the others (place, below)
    // A cluster a reader placed stands where they put it (Layout.clusterAt: its top left, in cells of Layout.FRAME);
    // the others are shelved, below the placed ones when there are any.
    const placed = list.filter((g) => !g.outside && Layout.clusterAt(g.key)), shelved = list.filter((g) => !placed.includes(g));
    // Shelves: of every width that breaks the row at a cluster, keep the one whose drawing is largest on this board.
    const shelve = (limit) => {
      let x = 0, y = 0, rowH = 0, w = 0;
      for (const g of shelved) {
        if ((g.outside && x > 0) || (x > 0 && x + g.w > limit)) { x = 0; y += rowH + gap; rowH = 0; }
        g.x = x; g.y = y; x += g.w + gap; rowH = Math.max(rowH, g.h); w = Math.max(w, x - gap);
      }
      return { w, h: y + rowH };
    };
    if (shelved.length) {
      const want = aspect || 1.4, widest = Math.max(...shelved.map((g) => g.w)), total = shelved.reduce((n, g) => n + g.w + gap, 0);
      let best = widest, bestScale = 0;
      for (let limit = widest; limit <= total; limit += 40) {
        const b = shelve(limit), scale = Math.min(want / b.w, 1 / b.h);
        if (scale > bestScale * 1.0001) { bestScale = scale; best = limit; }
      }
      shelve(best);
    }
    if (placed.length) {
      for (const g of placed) { const [c, r] = Layout.clusterAt(g.key); g.x = c * Layout.FRAME.cw; g.y = r * Layout.FRAME.rh; }
      // Opening a cluster grows it, and it may then reach a neighbor: the later one (by its corner, top to bottom,
      // then left to right) is drawn pushed right until it is clear. Its pin is unchanged; the next drop pins it as drawn.
      const settled = [];
      for (const g of placed.slice().sort((a, b) => a.y - b.y || a.x - b.x || cmp(a.key, b.key))) {
        // a pixel of play: a dropped cluster stands half a pixel inside the gutter, and its pin is rounded to 0.4 px
        for (let o = settled.find((p) => near(g, p, gap - 1)); o; o = settled.find((p) => near(g, p, gap - 1))) g.x = o.x + o.w + gap;
        settled.push(g);
      }
      const left = Math.min(...placed.map((g) => g.x)), below = Math.max(...placed.map((g) => g.y + g.h)) + gap;
      for (const g of shelved) { g.x += left; g.y += below; }
    }
    const boxes = {};
    for (const g of list) {
      if (!g.isOpen) { boxes[g.key] = { x: g.x, y: g.y, w: g.w, h: g.h, group: g }; continue; }
      // column by column, in pinned order: the leftmost-pinned apps stand in the cluster's first column
      const inner = PAD + (g.w - PAD * 2 - (g.cols * gx - (gx - W))) / 2;
      g.members.forEach((k, i) => {
        const c = g.outside ? i % g.cols : Math.floor(i / g.rows), r = g.outside ? Math.floor(i / g.cols) : i % g.rows;
        boxes[k] = { x: g.x + inner + c * gx, y: g.y + g.top + r * gy, w: W, h: H, group: g };
      });
    }
    return boxes;
  }

  /* ------------------------------------------------------------ edges between whatever is drawn */
  function edgesBetween(vis) {
    const pairs = {};
    for (const c of D.map.contracts) for (const k of c.consumers) {
      const a = vis(c.provider), b = vis(k);
      if (!a || !b || a === b) continue;
      const key = a < b ? `${a}|${b}` : `${b}|${a}`;
      const p = pairs[key] || (pairs[key] = { a: key.split("|")[0], b: key.split("|")[1], contracts: [] });
      if (!p.contracts.includes(c.id)) p.contracts.push(c.id);
    }
    return Object.values(pairs);
  }
  function side(A, B) {
    const ax = A.x + A.w / 2, ay = A.y + A.h / 2, bx = B.x + B.w / 2, by = B.y + B.h / 2, dx = bx - ax, dy = by - ay;
    if (Math.abs(dx) > Math.abs(dy) * 0.9) return dx < 0 ? "L" : "R";
    return dy < 0 ? "U" : "D";
  }
  const opposite = { L: "R", R: "L", U: "D", D: "U" };
  function ports(edges, boxes) {
    const slots = {};
    for (const e of edges) {
      const A = boxes[e.a], B = boxes[e.b];
      e.sa = side(A, B); e.sb = side(B, A);
      if (e.sa !== opposite[e.sb]) e.sb = opposite[e.sa];
      (slots[e.a + e.sa] = slots[e.a + e.sa] || []).push([e, "a"]);
      (slots[e.b + e.sb] = slots[e.b + e.sb] || []).push([e, "b"]);
    }
    for (const [k, list] of Object.entries(slots)) {
      const [e0, end0] = list[0], key = end0 === "a" ? e0.a : e0.b, sd = end0 === "a" ? e0.sa : e0.sb, box = boxes[key];
      const other = ([e, end]) => boxes[end === "a" ? e.b : e.a];
      const vertical = sd === "L" || sd === "R";
      list.sort((p, q) => vertical ? other(p).y - other(q).y : other(p).x - other(q).x);
      list.forEach(([e, end], i) => {
        const t = (i + 1) / (list.length + 1);
        const p = vertical ? { x: box.x + (sd === "L" ? 0 : box.w), y: box.y + box.h * (0.25 + 0.5 * t) } : { x: box.x + box.w * (0.2 + 0.6 * t), y: box.y + (sd === "U" ? 0 : box.h) };
        if (end === "a") e.pa = p; else e.pb = p;
      });
    }
  }
  /* Each wire goes around everything drawn (wires.js). One with no way through keeps its straight route, and says so. */
  function routeAround(edges, boxes, list, world, obs) {
    const regionOf = {};
    for (const g of list) { regionOf[g.key] = g.key; for (const k of g.members) regionOf[k] = g.key; }
    const routes = Wires.route(edges, world, obs, list.map((g) => ({ key: g.key, x: g.x, y: g.y, w: g.w, h: g.h })), boxes, regionOf);
    edges.forEach((e, n) => {
      if (!routes[n]) { console.warn(`[map] no way around the boxes for the wire ${label(e.a)} to ${label(e.b)}; drawn straight`); return; }
      e.pts = routes[n].pts; e.sa = routes[n].sa; e.sb = routes[n].sb;
    });
  }
  /* ------------------------------------------------------------ placing a lamp where nothing else is */
  // outward from the middle in steps of 1/24 of the duct, so the lamp stays as central as the drawing allows
  const FRACTIONS = [0.5, ...Array.from({ length: 11 }, (_, i) => [(11 - i) / 24, (13 + i) / 24]).flat()];
  const hits = (a, b, m = 4) => a.x < b.x + b.w + m && b.x < a.x + a.w + m && a.y < b.y + b.h + m && b.y < a.y + a.h + m;
  function place(pts, w, ht, obs, prefer) {
    const total = Geo.length(pts);
    if (total < w + 24) return null;
    for (const f of prefer ? [prefer, ...FRACTIONS] : FRACTIONS) {
      const at = Geo.pointAt(pts, total * f), r = { x: at.x - w / 2, y: at.y - ht / 2, w, h: ht };
      if (!obs.some((o) => hits(o, r))) return { at, r };
    }
    return null;
  }
  /* The nearest free spot to a duct's middle, ring by ring out to 240: deterministic, and never on anything. */
  function beside(pts, w, ht, obs) {
    const mid = Geo.pointAt(pts, Geo.length(pts) / 2);
    for (let radius = 24; radius <= 240; radius += 12) {
      for (let k = 0; k < 24; k++) {
        const a = (k / 24) * 2 * Math.PI - Math.PI / 2, at = { x: mid.x + radius * Math.cos(a), y: mid.y + radius * Math.sin(a) };
        const r = { x: at.x - w / 2, y: at.y - ht / 2, w, h: ht };
        if (!obs.some((o) => hits(o, r))) return { at, r, leader: mid };
      }
    }
    return { at: mid, r: { x: mid.x - w / 2, y: mid.y - ht / 2, w, h: ht }, crowded: true };
  }
  function drawEdges(edges, gDucts, gLamps, obs) {
    obs = obs || [];
    for (const e of edges) {
      const pts = e.pts || Geo.route(e.pa, e.pb, e.sa), d = Geo.roundedPath(pts, 30);
      const lv = worst(e.contracts.map(levelOf));
      const duct = s("path", { d, class: "duct", "data-a": e.a, "data-b": e.b }, gDucts);
      s("path", { d, class: "duct-hi", transform: "translate(0,2.5)" }, gDucts);
      Legend.saw("link");
      if (lv !== "dark") { s("path", { d, class: "duct-lit", stroke: LIGHT[lv].color }, gDucts); Legend.saw("link.lit"); }
      Scene.edge(e.a, e.b, { pts, el: duct, contracts: e.contracts });
      const one = e.contracts.length === 1, lw = one ? 120 : 98;
      const ids = e.contracts.slice().sort();
      const bundle = `bundle:${ids.join(",")}|${label(e.a)}|${label(e.b)}`;
      const said = one ? CONTRACT[ids[0]].title : `${ids.length} contracts`, lh = MapView.contractSize(said, lw).h;
      const spot = place(pts, lw, lh, obs);
      if (!spot) {
        // no room for a lamp: a round count on the duct; failing that, the nearest free spot beside it, tied by a leader
        const round = place(pts, 30, 30, obs) || beside(pts, 30, 30, obs);
        if (round.leader) { s("path", { d: `M${round.leader.x},${round.leader.y}L${round.at.x},${round.at.y}`, class: "leader" }, gDucts); Legend.saw("link.leader"); }
        if (round.crowded) console.warn(`[map] no free place for the lamp of ${ids.join(", ")}; drawn where it overlaps`);
        obs.push(round.r);
        countBadge(gLamps, round.at, ids, lv, bundle, round.crowded);
        continue;
      }
      obs.push(spot.r);
      const at = spot.at;
      MapView.lamp(gLamps, { key: one ? ids[0] : ids[0], x: at.x - lw / 2, y: at.y - lh / 2, w: lw, h: lh, rx: 3, kind: "contract",
        label: said, title: ids.map((id) => `${CONTRACT[id].title} (${id})`).join("; "),
        level: lv, onpick: () => go(one ? ids[0] : bundle, { reset: true }) });
    }
  }

  const label = (k) => (k.startsWith("grp:") ? k.slice(4) : k.startsWith("cap:") ? k.slice(4) || "No capability" : titleOf(k));
  /* On a short duct a lamp would cover the boxes, so the contracts there are a round count in their worst light. */
  function countBadge(g, at, ids, lv, bundle, crowded) {
    Legend.saw("kind.count"); Legend.saw("lamp." + lv);
    const grp = s("g", { class: `hit count-badge ${lv === "dark" ? "dark" : "lit " + lv}`, "data-key": ids[0], "data-agg": "1", "data-crowded": crowded ? "1" : null }, g);
    s("circle", { cx: at.x, cy: at.y, r: 14, fill: lv === "dark" ? LIGHT.dark.color : LIGHT[lv].color, stroke: Theme.c("face-edge"), "stroke-width": 2, class: "face" }, grp);
    s("text", { x: at.x, y: at.y + 4.5, "text-anchor": "middle", class: "lamp-text" }, grp).textContent = ids.length;
    s("title", {}, grp).textContent = ids.map((id) => `${CONTRACT[id].title} (${id})`).join("; ");
    Nodes.wire(grp, { label: `${plural(ids.length, "contract")}: ${ids.map((id) => CONTRACT[id].title).join(", ")}`, key: ids.length === 1 ? ids[0] : bundle });
  }

  /* ------------------------------------------------------------ moving a cluster */
  /* A cluster stands where it is dropped, as a box does. Drag it anywhere, or focus it and press an arrow key (a
     quarter of a cell; with Shift, a whole cell). A drop that would bring it within its gutter of another cluster
     lands at the nearest clear point on the line it was dragged along (Layout.along), and the status line says so.
     Every cluster drawn is pinned as it stands (`grp:` pins, layout.js), so the others stay put. Wires and lamps are
     routed again when it lands, not while it is held: routing around every box is too much work for each frame. */
  const ARROWS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  function movable(el, g, list, root) {
    if (g.outside) return;
    el.setAttribute("data-movable", "1");
    el.setAttribute("aria-keyshortcuts", "ArrowLeft ArrowRight ArrowUp ArrowDown Shift+ArrowLeft Shift+ArrowRight Shift+ArrowUp Shift+ArrowDown");
    el.addEventListener("pointerdown", (e) => startMove(e, g, list, root));
  }
  /* Where `g` lands when its top left moves by (dx, dy) px: { x, y, hit, past } (top left), or null. */
  function landing(g, list, dx, dy) {
    const mid = (o) => ({ x: o.x + o.w / 2, y: o.y + o.h / 2 }), from = mid(g);
    const others = list.filter((o) => o !== g).map((o) => ({ ...mid(o), w: o.w, h: o.h, key: o.label }));
    // half a pixel inside the gutter: shelved clusters stand exactly a gutter apart, and the one being moved must not
    // count as already too close to its neighbor where it starts
    const got = Layout.along(from, { x: from.x + dx, y: from.y + dy }, g.w, g.h, others, g.gap - 0.5);
    return got && { x: got.at.x - g.w / 2, y: got.at.y - g.h / 2, hit: got.hit, past: got.t > 1 };
  }
  function placeCluster(g, list, land) {
    if (!land) { Layout.say(`${g.label} stays where it is: there is no clear place on that line.`); return; }
    const F = Layout.FRAME, spots = list.filter((o) => !o.outside).map((o) => ({ key: o.key, at: o === g ? [land.x / F.cw, land.y / F.rh] : [o.x / F.cw, o.y / F.rh] }));
    const said = land.hit ? `${g.label} would have come too close to ${land.hit}, so it ${land.past ? "went just past" : "stopped just short of"} it. ` : "";
    Layout.placeClusters(spots, `${said}${g.label} moved. `);
  }
  function arrowMove(e, g, list) {
    const d = ARROWS[e.key];
    if (!d || g.outside || e.altKey || e.ctrlKey || e.metaKey) return;
    e.preventDefault();
    const by = e.shiftKey ? 1 : Layout.STEP;
    placeCluster(g, list, landing(g, list, d[0] * by * Layout.FRAME.cw, d[1] * by * Layout.FRAME.rh));
    const again = $(`#board [data-group="${CSS.escape(g.key)}"] .cluster-toggle, #board g.cluster-lamp[data-group="${CSS.escape(g.key)}"]`);
    if (again) again.focus();
  }
  function startMove(ev, g, list, root) {
    if (ev.button !== 0 || ev.isPrimary === false) return;
    const origin = { x: ev.clientX, y: ev.clientY };
    const toSvg = (e) => { const pt = root.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; return pt.matrixTransform(root.getScreenCTM().inverse()); };
    const from = toSvg(ev);
    let started = false, ghost = null, mark = null, latest = ev;
    // the cluster's outline follows the pointer; a dashed one shows where it will land when that is not under the pointer
    const paint = () => {
      const p = toSvg(latest), land = landing(g, list, p.x - from.x, p.y - from.y);
      ghost.setAttribute("x", g.x + p.x - from.x); ghost.setAttribute("y", g.y + p.y - from.y);
      const show = land && land.hit;
      mark.setAttribute("visibility", show ? "visible" : "hidden");
      if (show) { mark.setAttribute("x", land.x); mark.setAttribute("y", land.y); }
    };
    const finish = () => {
      removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); removeEventListener("keydown", onKey, true);
      if (ghost) ghost.remove();
      if (mark) mark.remove();
      $("#board").classList.remove("moving");
    };
    const onMove = (e) => {
      latest = e;
      if (!started) {
        if (Math.hypot(e.clientX - origin.x, e.clientY - origin.y) < 5) return;
        started = true; hideTip(); $("#board").classList.add("moving");
        ghost = s("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 14, class: "drag-ghost" }, root);
        mark = s("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 14, class: "drag-ghost landing", visibility: "hidden" }, root);
      }
      paint();
    };
    const onUp = (e) => {
      finish();
      if (!started) return;
      const p = toSvg(e);
      MapView.markDrop();
      placeCluster(g, list, landing(g, list, p.x - from.x, p.y - from.y));
    };
    const onKey = (e) => { if (e.key === "Escape" && started) { e.stopPropagation(); finish(); } };
    addEventListener("pointermove", onMove); addEventListener("pointerup", onUp); addEventListener("keydown", onKey, true);
  }

  /* ------------------------------------------------------------ the grouped cockpit */
  function grouped(board, mode) {
    const r = board.getBoundingClientRect(), list = groups(mode), boxes = layout(list, r.height ? r.width / r.height : 1.4, mode);
    const gOf = {};
    for (const g of list) for (const k of g.members) gOf[k] = g;
    const vis = (k) => { const g = gOf[k]; if (!g) return null; return g.isOpen ? k : g.key; };
    const keys = Object.keys(boxes);
    const x0 = Math.min(...keys.map((k) => boxes[k].x), ...list.map((g) => g.x)) - 60, y0 = Math.min(...list.map((g) => g.y)) - 30;
    const x1 = Math.max(...list.map((g) => g.x + g.w)) + 60, y1 = Math.max(...list.map((g) => g.y + g.h)) + 30;
    const root = s("svg", { viewBox: `${x0} ${y0} ${x1 - x0} ${y1 - y0}`, class: "cockpit grouped", role: "img", "aria-label": mode === "domain" ? "Apps grouped by domain" : "Apps grouped by capability" }, board);
    MapView.fitSvg(root, board, x1 - x0, y1 - y0, 1.05);
    defs(root);
    const gFrames = s("g", {}, root), gDucts = s("g", {}, root), gMotion = s("g", { class: "m-layer" }, root), gLamps = s("g", {}, root), gNodes = s("g", {}, root), gTop = s("g", { class: "m-top" }, root);
    Scene.reset(root, gMotion, vis, gTop);
    const gNames = s("g", { class: "cluster-names" }, root);  // above the ducts, so a duct never crosses a cluster's name
    const obs = [];  // everything drawn so far that a lamp must not sit on
    for (const g of list) frame(g, gFrames, gNodes, mode, gNames, obs, list, root);
    for (const [k, b] of Object.entries(boxes)) {
      if (b.group && !b.group.isOpen) continue;
      obs.push(b);
      const n = NODE[k], light = lightOf(k);
      const sub = n.kind !== "app" ? "outside service" : !light || light.level === "dark" ? "decided" : MapView.shortWhy(light);
      const el = MapView.lamp(gNodes, { key: k, x: b.x, y: b.y, w: b.w, h: b.h, rx: n.kind !== "app" ? 2 : 10, label: n.title, sub, kind: n.kind, clip: n.kind !== "app", emblem: Assets.emblem(k), icon: Icons.name(k) });
      Scene.node(k, { x: b.x, y: b.y, w: b.w, h: b.h, el });
      if (mode === "capability") alsoTab(gNames, k, b, obs);
    }
    const edges = edgesBetween(vis);
    ports(edges, boxes);
    routeAround(edges, boxes, list, { x0, y0, x1, y1 }, obs);
    drawEdges(edges, gDucts, gLamps, obs);
    MapView.startBreathing();
    board.dataset.groups = list.length;
    board.dataset.closed = list.filter((g) => !g.isOpen).length;
    Pan.attach(board, { key: "grouped-" + mode, svg: () => $("svg.cockpit.grouped", board) });
  }
  function defs(root) {
    const d = s("defs", {}, root);
    s("feGaussianBlur", { stdDeviation: 11 }, s("filter", { id: "ck-glow", x: "-60%", y: "-120%", width: "220%", height: "340%" }, d));
    const lens = s("linearGradient", { id: "ck-lens", x1: 0, y1: 0, x2: 0, y2: 1 }, d);
    s("stop", { offset: "0", "stop-color": Theme.c("face-hi") }, lens); s("stop", { offset: "1", "stop-color": Theme.c("face-lo") }, lens);
  }
  /* A cluster has no page of its own: its panel entry says what it stands for, app by app. */
  function groupNote(g, say) {
    return Nodes.note({ diagram: "Map", name: g.label, kind: g.outside ? "Group of outside services" : "Group of apps", text: say + ".", stands: g.members, relates: g.page ? [g.page] : [] });
  }
  /* A cluster: open, a frame with its apps inside; closed, one lamp with its counts and a small lamp per app. */
  function frame(g, gFrames, gNodes, mode, gNames, obs, list, root) {
    const { lv, counts, say } = clusterSays(g);
    if (g.isOpen) {
      const grp = s("g", { class: "cluster open", "data-group": g.key }, gFrames);
      s("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 14, class: "cluster-frame" + (g.outside ? " outside" : ""), "data-cap": g.cap || null }, grp);
      Legend.saw(g.outside ? "cluster.outside" : "cluster.open");
      // the name wraps to a second line before it is cut; the counts stand at the right of its last line when they fit there
      const subText = g.w >= 300 && counts.length ? counts.map(([l, n]) => `${n} ${LIGHT[l].word.toLowerCase()}`).join(" · ") : "";
      const subW = subText ? measure(subText, 12) + 14 : 0, nf = g.nameFit;
      const t = LabelFit.put(gNames, { x: g.x + PAD, y: g.y + 30, class: "cluster-name" }, g.label, g.w - PAD * 2, NAME_TEXT);
      s("title", {}, t).textContent = g.label;
      obs.push(drawnBox(t, { x: g.x + PAD, y: g.y + 14, w: Math.max(...nf.lines.map((l) => LabelFit.width(l, nf.size, 600))), h: 22 + g.headExtra }));
      if (subText && LabelFit.width(nf.lines[nf.lines.length - 1], nf.size, 600) + subW <= g.w - PAD * 2) {
        const sub = s("text", { x: g.x + g.w - PAD, y: g.y + 30 + g.headExtra, "text-anchor": "end", class: "cluster-sub" }, gNames);
        sub.textContent = subText;
        obs.push(drawnBox(sub, { x: g.x + g.w - PAD - subW + 14, y: g.y + 16 + g.headExtra, w: subW - 14, h: 20 }));
      }
      if (g.alsoLines.length) alsoRow(g, gNames, obs);
      if (lv !== "dark") s("rect", { x: g.x, y: g.y + 12, width: 3, height: 26, rx: 1.5, fill: LIGHT[lv].color }, grp);
      const close = s("g", { class: "cluster-toggle", tabindex: 0, role: "button", "aria-label": `Close ${g.label}` }, grp);
      s("rect", { x: g.x + g.w / 2 - 34, y: g.y + g.h - 11, width: 68, height: 20, rx: 10 }, close);
      obs.push({ x: g.x + g.w / 2 - 34, y: g.y + g.h - 11, w: 68, h: 20 });
      s("text", { x: g.x + g.w / 2, y: g.y + g.h + 3, "text-anchor": "middle" }, close).textContent = "Close ▴";
      close.addEventListener("click", () => { if (!MapView.justDropped()) toggle(g); });
      close.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(g); } else arrowMove(e, g, list); });
      Nodes.wire(t, { label: g.label, ...(g.page ? { key: g.page } : { note: groupNote(g, say) }), guard: () => !MapView.justDropped() });
      for (const handle of [grp, t]) movable(handle, g, list, root);
      return;
    }
    // Closed, a cluster stays a dark panel: its worst light is the band on its edge and the lamp by its name, and
    // each app keeps its own small lamp, so the cluster says which of its apps is lit without shouting it.
    obs.push({ x: g.x, y: g.y, w: g.w, h: g.h });
    Legend.saw("cluster.closed"); Legend.saw("lamp." + lv);
    const el = s("g", { class: `hit cluster-lamp ${lv === "dark" ? "dark" : "lit " + lv}`, "data-key": g.key, "data-group": g.key, "data-level": lv }, gNodes);
    s("rect", { x: g.x, y: g.y + 2, width: g.w, height: g.h, rx: 14, fill: Theme.c("face-drop") }, el);
    s("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 14, fill: "url(#ck-lens)", stroke: Theme.c("face-edge"), "stroke-width": 2, class: "face" }, el);
    if (lv !== "dark") {
      s("rect", { x: g.x + 1, y: g.y + 14, width: 5, height: g.h - 28, rx: 2.5, fill: LIGHT[lv].color, class: "band" }, el);
      s("circle", { cx: g.x + 24, cy: g.y + 30, r: 6, fill: LIGHT[lv].color, class: "dot" }, el);
    }
    // wrapped to the card by measure, so a title never runs past its card onto a neighbor, and never ends in "…"
    const tx = g.x + (lv !== "dark" ? 38 : 20), tf = g.titleFit;
    LabelFit.put(el, { x: tx, y: g.y + 36, class: "cluster-title" }, g.label, g.w - 16 - (tx - g.x), TITLE_TEXT);
    LabelFit.put(el, { x: g.x + 20, y: g.y + 60 + Math.ceil((tf.lines.length - 1) * tf.lh), class: "node-sub" }, say, g.w - 36, SAY_TEXT);
    s("title", {}, el).textContent = `${g.label}: ${say}`;
    // opening it in place also puts what it stands for in the panel, so the panel never lags a cluster the reader just picked
    Nodes.wire(el, { label: g.label, aria: `${g.label}: ${say}. Open it in place.`, open: () => { go(groupNote(g, say), { reset: true }); toggle(g); }, guard: () => !MapView.justDropped() });
    el.addEventListener("keydown", (e) => { if (e.key !== "Enter" && e.key !== " ") arrowMove(e, g, list); });
    movable(el, g, list, root);
    // one small lamp per app, so a closed cluster still shows which of its apps is lit
    const per = Math.min(g.members.length, 12), mw = Math.min(16, (g.w - 40) / per - 4);
    g.members.slice(0, per).forEach((k, i) => {
      const l = levelOf(k);
      // each app's glyph stands over its lamp, so a closed cluster still says what is inside it
      if (mw >= 12) Icons.put(el, Icons.name(k), g.x + 20 + i * (mw + 4) + mw / 2, g.y + g.h - 40, Math.min(14, mw), "mini-glyph");
      Legend.saw("cluster.mini");
      const tiny = s("rect", { x: g.x + 20 + i * (mw + 4), y: g.y + g.h - 26, width: mw, height: 8, rx: 2, fill: l === "dark" ? Theme.c("mini-dark") : LIGHT[l].color, class: "mini-lamp", "data-key": k }, el);
      tiny.appendChild(document.createElementNS(SVGNS, "title")).textContent = `${titleOf(k)}: ${LIGHT[l].word}`;
      // a part inside a focusable cluster: the cluster's panel lists the same apps for the keyboard
      Nodes.wire(tiny, { label: `${titleOf(k)}: ${LIGHT[l].word}`, key: k, nested: true, stop: true });
      tiny.addEventListener("pointerdown", (e) => e.stopPropagation());
    });
    s("text", { x: g.x + g.w - 18, y: g.y + g.h - 18, "text-anchor": "end", class: "node-sub open-hint" }, el).textContent = "Open ▾";
    Scene.node(g.key, { x: g.x, y: g.y, w: g.w, h: g.h, el });
  }
  /* A region's apps drawn elsewhere: one row of small chips under its name, part of the region's own size. */
  function alsoRow(g, gNames, obs) {
    const y0 = g.y + HEAD - 6;
    s("text", { x: g.x + PAD, y: y0 + g.headExtra + 14, class: "also-label" }, gNames).textContent = "Also in";
    let top = y0 + g.headExtra;
    g.alsoLines.forEach((line) => { line.forEach(({ k, x, w, h }) => {
      const cx = g.x + PAD + x, cy = top;
      Legend.saw("cluster.also-chip");
      const chip = s("g", { class: "also-chip", "data-key": k }, gNames);
      s("rect", { x: cx, y: cy, width: w, height: h, rx: Math.min(h, CHIP_H) / 2 }, chip);
      Icons.put(chip, Icons.name(k), cx + 12, cy + h / 2, 12, "also-glyph");
      const f = LabelFit.fit(titleOf(k), g.w - PAD * 2 - 34, CHIP_TEXT);
      LabelFit.put(chip, { x: cx + 22, y: cy + h / 2 - (f.lines.length - 1) * f.lh / 2 + 0.35 * f.size }, titleOf(k), g.w - PAD * 2 - 34, CHIP_TEXT);
      const home = (D.appCaps[k] || { caps: [""] }).caps[0];
      s("title", {}, chip).textContent = `${titleOf(k)} carries this capability too; it is drawn in ${home}`;
      obs.push({ x: cx, y: cy, w, h });
      const pick = () => { go(k, { reset: true }); const real = $(`#board g.hit[data-key="${CSS.escape(k)}"]`); if (real && !reducedMotion()) real.animate([{ opacity: 0.4 }, { opacity: 1 }], { duration: 500, iterations: 2 }); };
      Nodes.wire(chip, { label: titleOf(k), aria: `${titleOf(k)}, drawn in another region`, role: "link", open: pick });
    }); top += line.h + CHIP_GAP; });
    obs.push({ x: g.x + PAD, y: y0 + g.headExtra, w: measure("Also in", 11.5, 500), h: CHIP_H });
  }
  /* "+2 capabilities" on an app that carries more than its region's: hover it to light the other regions. */
  function alsoTab(gNames, k, b, obs) {
    const caps = (D.appCaps[k] || { caps: [] }).caps;
    if (caps.length < 2) return;
    const text = `+${plural(caps.length - 1, "capability", "capabilities")}`, w = measure(text, 11, 600) + 16;
    Legend.saw("cluster.also-tab");
    const tab = s("g", { class: "also-tab", "data-key": k }, gNames);
    s("rect", { x: b.x + b.w - w - 6, y: b.y - 22, width: w, height: 18, rx: 9 }, tab);
    s("text", { x: b.x + b.w - w / 2 - 6, y: b.y - 9, "text-anchor": "middle" }, tab).textContent = text;
    s("title", {}, tab).textContent = `${titleOf(k)} also delivers ${caps.slice(1).map((c) => (ent(keyForId(c)) ? ent(keyForId(c)).title : c)).join("; ")}`;
    obs.push({ x: b.x + b.w - w - 6, y: b.y - 22, w, h: 18 });
    tab.addEventListener("mouseenter", () => lightAlso(k, true));
    tab.addEventListener("mouseleave", () => lightAlso(App.focus === k ? k : null, true));
    Nodes.wire(tab, { label: `${titleOf(k)} also delivers ${caps.slice(1).map((c) => (ent(keyForId(c)) ? ent(keyForId(c)).title : c)).join(", ")}`, key: k });
  }
  function lightAlso(k) {
    const caps = new Set(k ? (D.appCaps[k] || { caps: [] }).caps.slice(1) : []);
    $$("#board .cluster-frame[data-cap]").forEach((f) => f.classList.toggle("also-on", caps.has(f.dataset.cap)));
    $$("#board .also-chip").forEach((c) => c.classList.toggle("also-on", c.dataset.key === k));
  }

  /* ------------------------------------------------------------ focus: one app and its direct neighbors */
  function neighbors(key) {
    const uses = new Map(), usedBy = new Map();
    for (const c of D.map.contracts) {
      if (c.consumers.includes(key) && c.provider !== key && NODE[c.provider]) (uses.get(c.provider) || uses.set(c.provider, []).get(c.provider)).push(c.id);
      if (c.provider === key) for (const k of c.consumers) if (k !== key && NODE[k]) (usedBy.get(k) || usedBy.set(k, []).get(k)).push(c.id);
    }
    return { uses, usedBy };
  }
  /* onCenter: what picking the app in the middle does besides open it in the panel (Inside this app goes in a level). */
  function focus(board, key, onCenter) {
    if (!NODE[key]) { board.append(emptyState("That app isn't on the map.")); return; }
    const { uses, usedBy } = neighbors(key);
    const left = [...usedBy.keys()].filter((k) => NODE[k].kind === "app" && !uses.has(k)).sort(byPin);
    const both = [...usedBy.keys()].filter((k) => uses.has(k)).sort(byPin);
    const right = [...uses.keys()].filter((k) => NODE[k].kind === "app" && !usedBy.has(k)).sort(byPin);
    const below = [...new Set([...uses.keys(), ...usedBy.keys()])].filter((k) => NODE[k].kind !== "app" && !both.includes(k)).sort(byPin);
    const boxes = { [key]: { x: -W / 2, y: -H / 2 } };
    const column = (list, x) => list.forEach((k, i) => { boxes[k] = { x: x - W / 2, y: (i - (list.length - 1) / 2) * (GY + 18) - H / 2 }; });
    column(left, -470); column(right, 470);
    both.forEach((k, i) => { boxes[k] = { x: -W / 2 + (i - (both.length - 1) / 2) * (GX + 20), y: -H / 2 - 190 }; });
    below.forEach((k, i) => { boxes[k] = { x: -W / 2 + (i - (below.length - 1) / 2) * (GX + 20), y: -H / 2 + 220 }; });
    Object.values(boxes).forEach((b) => { b.w = W; b.h = H; });
    const xs = Object.values(boxes).flatMap((b) => [b.x, b.x + W]), ys = Object.values(boxes).flatMap((b) => [b.y, b.y + H]);
    const x0 = Math.min(...xs) - 120, x1 = Math.max(...xs) + 120, y0 = Math.min(...ys) - 70, y1 = Math.max(...ys) + 60;
    const root = s("svg", { viewBox: `${x0} ${y0} ${x1 - x0} ${y1 - y0}`, class: "cockpit focus", role: "img", "aria-label": `${titleOf(key)} and the apps it connects to directly` }, board);
    MapView.fitSvg(root, board, x1 - x0, y1 - y0, 1.1);
    Pan.attach(board, { key: "focus", svg: () => $("svg.cockpit.focus", board) });
    defs(root);
    const gDucts = s("g", {}, root), gMotion = s("g", { class: "m-layer" }, root), gLamps = s("g", {}, root), gNodes = s("g", {}, root), gTop = s("g", { class: "m-top" }, root);
    Scene.reset(root, gMotion, (k) => (boxes[k] ? k : null), gTop);
    const label = (x, y, text, anchor) => { s("text", { x, y, "text-anchor": anchor || "middle", class: "zone-text" }, gDucts).textContent = text; };
    if (left.length) label(-470, Math.min(...left.map((k) => boxes[k].y)) - 18, "Uses it");
    if (right.length) label(470, Math.min(...right.map((k) => boxes[k].y)) - 18, "It uses");
    if (both.length) label(0, Math.min(...both.map((k) => boxes[k].y)) - 18, "Both ways");
    if (below.length) label(0, Math.min(...below.map((k) => boxes[k].y)) - 18, "Outside services");
    for (const [k, b] of Object.entries(boxes)) {
      const n = NODE[k], light = lightOf(k);
      const sub = n.kind !== "app" ? "outside service" : !light || light.level === "dark" ? "decided" : MapView.shortWhy(light);
      const el = MapView.lamp(gNodes, { key: k, x: b.x, y: b.y, w: W, h: H, rx: n.kind !== "app" ? 2 : 10, label: n.title, sub, kind: n.kind, clip: n.kind !== "app", emblem: Assets.emblem(k), icon: Icons.name(k),
        onpick: k === key ? (onCenter ? () => { go(k, { reset: true }); onCenter(el); } : null) : () => go(k, { reset: true }) });
      if (k === key) { el.classList.add("focus-center"); Legend.saw("picked", "White outline: the app in focus, and what you pick"); }
      Scene.node(k, { x: b.x, y: b.y, w: W, h: H, el });
    }
    // each neighbor's contracts as a bank of lamps on its one duct, as on the cockpit
    for (const k of Object.keys(boxes)) {
      if (k === key) continue;
      const ids = [...new Set([...(uses.get(k) || []), ...(usedBy.get(k) || [])])].sort();
      const A = boxes[key], B = boxes[k], c = { x: 0, y: 0 }, o = { x: B.x + W / 2, y: B.y + H / 2 };
      const sd = Math.abs(o.x) > Math.abs(o.y) ? (o.x < 0 ? "L" : "R") : (o.y < 0 ? "U" : "D");
      const pa = { L: { x: A.x, y: c.y }, R: { x: A.x + W, y: c.y }, U: { x: c.x, y: A.y }, D: { x: c.x, y: A.y + H } }[sd];
      const pb = { L: { x: B.x + W, y: o.y }, R: { x: B.x, y: o.y }, U: { x: o.x, y: B.y + H }, D: { x: o.x, y: B.y } }[sd];
      const pts = Geo.route(pa, pb, sd), d = Geo.roundedPath(pts, 34), lv = worst(ids.map(levelOf));
      const duct = s("path", { d, class: "duct" }, gDucts);
      Legend.saw("link");
      if (lv !== "dark") { s("path", { d, class: "duct-lit", stroke: LIGHT[lv].color }, gDucts); Legend.saw("link.lit"); }
      Scene.edge(key, k, { pts, el: duct, contracts: ids });
      const at = Geo.pointAt(pts, Geo.length(pts) * 0.55);
      const tall = ids.map((id) => MapView.contractSize(CONTRACT[id].title, 120).h);
      let stack = at.y - (tall.reduce((n, x) => n + x, 0) + (ids.length - 1) * 5) / 2;
      ids.forEach((id, i) => { const y = stack; stack += tall[i] + 5; MapView.lamp(gLamps, { key: id, x: at.x - 60, y, w: 120, h: tall[i], rx: 3, label: CONTRACT[id].title, kind: "contract", title: `${id} ${CONTRACT[id].title}` }); });
    }
    const hidden = D.nodes.length - Object.keys(boxes).length;
    // the view's intro already says what this board is; the note only speaks when something is left off it
    if (hidden) board.append(h("div", { class: "focus-note" }, `${plural(hidden, "box", "boxes")} with no contract to ${titleOf(key)} ${hidden === 1 ? "isn't" : "aren't"} drawn.`));
    MapView.startBreathing();
    board.dataset.shown = Object.keys(boxes).length;
  }
  function highlight(key) {
    const board = $("#board"); if (!board) return;
    const anchors = new Set(key ? mapAnchors(key) : []);
    if (key && CONTRACT[key]) { anchors.add(CONTRACT[key].provider); CONTRACT[key].consumers.forEach((k) => anchors.add(k)); }
    $$("g.hit", board).forEach((g) => g.classList.toggle("picked", anchors.has(g.dataset.key) || g.dataset.key === key));
    lightAlso(key && APPS[key] ? key : null);
  }
  return { grouped, focus, groups, highlight, all, neighbors, isOpen, place, beside, drawnBox, LOOKS, LOOKS_FOCUS };
})();
