/* The formation: where every station sits and how track runs between them, from the pinned cells (pins.py).

   The cockpit, the line map and the minimap all draw from this one function, so an app is in the same place on all
   three, and its lane in a played flow follows the same left-to-right order. A position never comes from a force
   layout or the screen size: cells are pinned and only scaled here. Track is octilinear (horizontal, vertical, 45°).
   A position may fall between cells (a reader drops a box where they like, layout.js); nothing here rounds it, and a
   route between two boxes nearly in line runs straight. The cockpit, the minimap and the releases view scale by
   Layout.FRAME, the frame the overlap rule measures in; the line map keeps its own, wider spacing.
   A station with several corridors on one side becomes an interchange bar with one port per corridor, so lines fan
   out instead of piling onto one point. Ported from prototypes/gallery/maps/shared/geometry.js. */
const Geo = (() => {
  const LINE_W = 6, LINE_GAP = 8.5, PORT_GAP = 16, MIN_SIDE = 26, NEAR_LEVEL = 8;
  // Flow line colours per theme (--lines in themes.css), kept apart from the lamp colours; past the sixth a line is
  // grey and told apart by its label.
  const flowColour = (i) => Theme.list("lines")[i] || Theme.c("line-grey");
  const FLOW_ORDER = Object.fromEntries(D.flows.map((f, i) => [f.key, i]));

  const DEFAULTS = { cw: 290, rh: 150, padX: 120, padY: 120, bandGap: 70 };
  /* Where a (possibly fractional) cell is drawn, and the cell under a point: how a dragged box is placed and dropped. */
  function pointOf(opts, col, row, outside) {
    const o = Object.assign({}, DEFAULTS, opts || {});
    return { x: o.padX + col * o.cw, y: o.padY + row * o.rh + (outside ? o.bandGap : 0) };
  }
  function cellAt(opts, x, y, outside) {
    const o = Object.assign({}, DEFAULTS, opts || {});
    return { col: (x - o.padX) / o.cw, row: (y - o.padY - (outside ? o.bandGap : 0)) / o.rh };
  }
  function layout(opts) {
    const o = Object.assign({}, DEFAULTS, opts || {});
    const stations = {};
    for (const n of D.nodes) {
      const outside = n.kind !== "app";
      stations[n.key] = { key: n.key, node: n, outside, x: o.padX + n.col * o.cw, y: o.padY + n.row * o.rh + (outside ? o.bandGap : 0),
        ports: { L: [], R: [], U: [], D: [] }, lines: new Set() };
    }
    const corridors = {};
    const pairKey = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);
    for (const c of D.map.contracts) for (const consumer of c.consumers) {
      if (consumer === c.provider || !stations[consumer] || !stations[c.provider]) continue;
      const k = pairKey(c.provider, consumer), [a, b] = k.split("|");
      corridors[k] = corridors[k] || { key: k, a, b, contracts: [], flows: [] };
      if (!corridors[k].contracts.includes(c.id)) corridors[k].contracts.push(c.id);
    }
    for (const f of D.flows) for (const sg of f.segments || []) {
      const k = pairKey(sg.a, sg.b);
      if (corridors[k] && !corridors[k].flows.includes(f.key)) corridors[k].flows.push(f.key);
    }
    for (const cor of Object.values(corridors)) {
      cor.flows.sort((p, q) => FLOW_ORDER[p] - FLOW_ORDER[q]);
      cor.width = Math.max(1, cor.flows.length) * LINE_GAP;
      for (const f of cor.flows) { stations[cor.a].lines.add(f); stations[cor.b].lines.add(f); }
    }
    const side = (from, to) => {
      const dx = to.x - from.x, dy = to.y - from.y;
      if (Math.abs(dx) > Math.abs(dy) * 0.6) return dx < 0 ? "L" : "R";
      return dy < 0 ? "U" : "D";
    };
    for (const cor of Object.values(corridors)) {
      const A = stations[cor.a], B = stations[cor.b];
      cor.sideA = side(A, B); cor.sideB = side(B, A);
      A.ports[cor.sideA].push(cor); B.ports[cor.sideB].push(cor);
    }
    for (const st of Object.values(stations)) {
      const span = (list) => list.reduce((acc, c) => acc + c.width, 0) + Math.max(0, list.length - 1) * PORT_GAP;
      st.h = Math.max(MIN_SIDE, span(st.ports.L) + 14, span(st.ports.R) + 14);
      st.w = Math.max(MIN_SIDE, span(st.ports.U) + 14, span(st.ports.D) + 14);
      for (const sd of ["L", "R", "U", "D"]) {
        const list = st.ports[sd], vertical = sd === "L" || sd === "R";
        const other = (c) => stations[c.a === st.key ? c.b : c.a];
        list.sort((p, q) => (vertical ? other(p).y - other(q).y || other(p).x - other(q).x : other(p).x - other(q).x || other(p).y - other(q).y));
        let cursor = -span(list) / 2;
        for (const c of list) {
          const mid = cursor + c.width / 2;
          cursor += c.width + PORT_GAP;
          const p = vertical ? { x: st.x + (sd === "L" ? -st.w / 2 : st.w / 2), y: st.y + mid } : { x: st.x + mid, y: st.y + (sd === "U" ? -st.h / 2 : st.h / 2) };
          if (c.a === st.key) c.portA = p; else c.portB = p;
        }
      }
    }
    for (const cor of Object.values(corridors)) {
      cor.path = route(cor.portA, cor.portB, cor.sideA);
      cor.lanes = {};
      const n = cor.flows.length;
      cor.flows.forEach((fid, i) => { cor.lanes[fid] = offsetPolyline(cor.path, (i - (n - 1) / 2) * LINE_GAP); });
      cor.centre = cor.path;
    }
    const xs = Object.values(stations).flatMap((st) => [st.x - st.w / 2, st.x + st.w / 2]);
    const ys = Object.values(stations).flatMap((st) => [st.y - st.h / 2, st.y + st.h / 2]);
    const bounds = xs.length ? { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) } : { x0: 0, x1: 100, y0: 0, y1: 100 };
    // The line between our apps and the outside parties is drawn only where it divides them: a reader may now drop a
    // party anywhere clear of the boxes, and a line with a party on the wrong side of it would say something false.
    const all = Object.values(stations), appYs = all.filter((st) => !st.outside).map((st) => st.y), partyYs = all.filter((st) => st.outside).map((st) => st.y);
    const lowApp = Math.max(o.padY, ...appYs), highParty = Math.min(...partyYs);
    const zoneY = partyYs.length && highParty - lowApp >= o.rh ? (lowApp + highParty) / 2 + 10 : null;
    return { stations, corridors, bounds, zoneY };
  }

  /* Octilinear route between two ports: horizontal, 45°, horizontal leaving sideways; vertical, 45°, vertical leaving up or down.
     When the two ports sit on an exact diagonal the straight runs are zero long; those coincident points are dropped,
     because roundedPath divides by each segment's length and a zero one turns the whole path into NaN. */
  function route(A, B, sideA) {
    return withoutCoincident(octilinear(A, B, sideA));
  }
  function withoutCoincident(pts) {
    return pts.filter((p, i) => i === 0 || Math.hypot(p.x - pts[i - 1].x, p.y - pts[i - 1].y) > 0.01);
  }
  function octilinear(A, B, sideA) {
    const dx = B.x - A.x, dy = B.y - A.y, adx = Math.abs(dx), ady = Math.abs(dy);
    const sx = Math.sign(dx) || 1, sy = Math.sign(dy) || 1;
    // nearly in line: one straight run. Whole cells put ports exactly level; a box dropped between cells can stand a
    // few pixels off, and a 45° jog that short reads as a kink, not as a bend.
    if (ady < NEAR_LEVEL || adx < NEAR_LEVEL) return [A, B];
    if (sideA === "L" || sideA === "R") {
      if (adx >= ady) { const hh = (adx - ady) / 2; return [A, { x: A.x + sx * hh, y: A.y }, { x: B.x - sx * hh, y: B.y }, B]; }
      const d = adx / 2; return [A, { x: A.x + sx * d, y: A.y + sy * d }, { x: B.x - sx * d, y: B.y - sy * d }, B];
    }
    if (ady >= adx) { const v = (ady - adx) / 2; return [A, { x: A.x, y: A.y + sy * v }, { x: B.x, y: B.y - sy * v }, B]; }
    const d = ady / 2; return [A, { x: A.x + sx * d, y: A.y + sy * d }, { x: B.x - sx * d, y: B.y - sy * d }, B];
  }
  function offsetPolyline(pts, d) {
    if (!d) return pts.map((p) => ({ ...p }));
    const n = pts.length, out = [];
    const norm = (a, b) => { const dx = b.x - a.x, dy = b.y - a.y, l = Math.hypot(dx, dy) || 1; return { x: -dy / l, y: dx / l }; };
    for (let i = 0; i < n; i++) {
      if (i === 0 || i === n - 1) { const nn = i === 0 ? norm(pts[0], pts[1]) : norm(pts[n - 2], pts[n - 1]); out.push({ x: pts[i].x + nn.x * d, y: pts[i].y + nn.y * d }); continue; }
      const n1 = norm(pts[i - 1], pts[i]), n2 = norm(pts[i], pts[i + 1]);
      const mx = n1.x + n2.x, my = n1.y + n2.y, ml = Math.hypot(mx, my) || 1, cos = (n1.x * mx + n1.y * my) / ml;
      const k = d / (cos || 1);
      out.push({ x: pts[i].x + (mx / ml) * k, y: pts[i].y + (my / ml) * k });
    }
    return out;
  }
  /* SVG path with tight curves at each bend, as on Beck's map. */
  function roundedPath(pts, r = 22) {
    if (pts.length < 3) return `M${pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join("L")}`;
    let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const p0 = pts[i - 1], p1 = pts[i], p2 = pts[i + 1];
      const l1 = Math.hypot(p1.x - p0.x, p1.y - p0.y), l2 = Math.hypot(p2.x - p1.x, p2.y - p1.y), rr = Math.min(r, l1 / 2, l2 / 2);
      const a = { x: p1.x - ((p1.x - p0.x) / l1) * rr, y: p1.y - ((p1.y - p0.y) / l1) * rr };
      const b = { x: p1.x + ((p2.x - p1.x) / l2) * rr, y: p1.y + ((p2.y - p1.y) / l2) * rr };
      d += `L${a.x.toFixed(1)},${a.y.toFixed(1)}Q${p1.x.toFixed(1)},${p1.y.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}`;
    }
    const last = pts[pts.length - 1];
    return d + `L${last.x.toFixed(1)},${last.y.toFixed(1)}`;
  }
  function length(pts) { let t = 0; for (let i = 1; i < pts.length; i++) t += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); return t; }
  function pointAt(pts, dist) {
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i], l = Math.hypot(b.x - a.x, b.y - a.y);
      if (dist <= l || i === pts.length - 1) { const t = l ? clamp(dist / l, 0, 1) : 0; return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, angle: Math.atan2(b.y - a.y, b.x - a.x) }; }
      dist -= l;
    }
    return { x: pts[0].x, y: pts[0].y, angle: 0 };
  }
  return { layout, pointOf, cellAt, route, roundedPath, offsetPolyline, length, pointAt, LINE_W, flowColour, FLOW_ORDER };
})();
