/* Wires between the boxes of a grouped map, routed around everything instead of straight across it.

   A wire used to run the shortest octilinear way between its two boxes, which crossed other regions and passed a
   hand's breadth from boxes it has nothing to do with. Here the board is a grid of small cells. A box, a region's
   name, a tab, a toggle (every obstacle the map has drawn) blocks the cells it covers and a margin around them, so
   a wire never touches one it does not connect. A wire leaves its box by any side and arrives by any side, and the
   cheapest way there is found with A*: each step costs 1, a bend costs more so a wire runs straight where it can,
   crossing a region that is neither its own nor its target's costs a lot so it goes by the gaps between regions,
   and a cell another wire already uses costs a little more so parallel wires take parallel tracks instead of
   one pile. Wires are routed shortest first, so the long ones bend around the short ones.

   Pure: rectangles in, polylines out. A wire with no way through (a box walled in) is returned as null for the
   caller to draw straight and say so; it is never dropped. #selftest checks that no wire runs through a box. */
const Wires = (() => {
  const STEP = 12, MARGIN = 8, BEND = 9, OTHER_REGION = 30, SHARED = 6, CROSSED = 3;
  const DIRS = [{ x: 1, y: 0 }, { x: 0, y: 1 }, { x: -1, y: 0 }, { x: 0, y: -1 }];  // right, down, left, up
  const SIDES = ["R", "D", "L", "U"];  // the side a wire leaves by when it heads off in DIRS[i]

  /* A binary min-heap of [priority, payload], the only data structure the search needs. */
  function heap() {
    const a = [];
    const up = (i) => { while (i > 0) { const p = (i - 1) >> 1; if (a[p][0] <= a[i][0]) break; [a[p], a[i]] = [a[i], a[p]]; i = p; } };
    const down = (i) => { for (;;) { let m = i; const l = 2 * i + 1, r = l + 1; if (l < a.length && a[l][0] < a[m][0]) m = l; if (r < a.length && a[r][0] < a[m][0]) m = r; if (m === i) return; [a[m], a[i]] = [a[i], a[m]]; i = m; } };
    return { push(item) { a.push(item); up(a.length - 1); }, pop() { const top = a[0], last = a.pop(); if (a.length) { a[0] = last; down(0); } return top; }, get size() { return a.length; } };
  }

  /* world: {x0, y0, x1, y1} the board; blocks: [{x, y, w, h}] every obstacle; regions: [{key, x, y, w, h}];
     boxes: {key: {x, y, w, h}} the things wires join; regionOf: {key: region key}.
     edges: [{a, b}] box keys. Returns [[points] | null], in the edges' order. */
  function route(edges, world, blocks, regions, boxes, regionOf) {
    const cols = Math.ceil((world.x1 - world.x0) / STEP), rows = Math.ceil((world.y1 - world.y0) / STEP);
    const blocked = new Uint8Array(cols * rows), region = new Uint8Array(cols * rows), used = new Uint8Array(cols * rows);  // used: 1 across, 2 down, 3 both
    const cellX = (i) => world.x0 + (i + 0.5) * STEP, cellY = (j) => world.y0 + (j + 0.5) * STEP;
    const colOf = (x) => Math.floor((x - world.x0) / STEP), rowOf = (y) => Math.floor((y - world.y0) / STEP);
    const fill = (grid, r, m, value) => {
      for (let j = Math.max(0, rowOf(r.y - m)); j <= Math.min(rows - 1, rowOf(r.y + r.h + m)); j++)
        for (let i = Math.max(0, colOf(r.x - m)); i <= Math.min(cols - 1, colOf(r.x + r.w + m)); i++) grid[j * cols + i] = value;
    };
    const regionIndex = {};
    regions.forEach((r, n) => { regionIndex[r.key] = n + 1; fill(region, r, 0, n + 1); });
    for (const b of blocks) fill(blocked, b, MARGIN, 1);

    /* The cells a wire may start or end in: the first free cell outside a side of its box, within the side's middle.
       A door remembers the way a wire heads when it leaves through it (d), which is the way it must not arrive. */
    const doors = (box) => {
      const out = [];
      SIDES.forEach((side, d) => {
        const dir = DIRS[d], horizontal = dir.x !== 0;
        const lo = horizontal ? box.y + box.h * 0.2 : box.x + box.w * 0.15, hi = horizontal ? box.y + box.h * 0.8 : box.x + box.w * 0.85;
        const edge = horizontal ? (dir.x > 0 ? box.x + box.w : box.x) : (dir.y > 0 ? box.y + box.h : box.y);
        const first = (horizontal ? colOf : rowOf)(edge + (dir.x + dir.y) * MARGIN) + dir.x + dir.y;
        for (let k = horizontal ? rowOf(lo) : colOf(lo); k <= (horizontal ? rowOf(hi) : colOf(hi)); k++) {
          for (let out_ = 0; out_ < 2; out_++) {  // the cell beside the margin, else the next one out
            const i = horizontal ? first + (dir.x + dir.y) * out_ : k, j = horizontal ? k : first + (dir.x + dir.y) * out_;
            if (i < 0 || j < 0 || i >= cols || j >= rows || blocked[j * cols + i]) continue;
            out.push({ i, j, d, side });
            break;
          }
        }
      });
      return out;
    };
    const stateOf = (i, j, d) => (j * cols + i) * 4 + d;

    const result = new Array(edges.length).fill(null);
    const order = edges.map((e, n) => n).sort((p, q) => apart(boxes[edges[p].a], boxes[edges[p].b]) - apart(boxes[edges[q].a], boxes[edges[q].b]));
    for (const n of order) {
      const e = edges[n], from = boxes[e.a], to = boxes[e.b];
      const way = search(doors(from), doors(to), regionIndex[regionOf[e.a]] || 0, regionIndex[regionOf[e.b]] || 0);
      if (!way) continue;
      mark(way.cells);
      result[n] = polyline(way, from, to);
    }
    return result;

    function apart(a, b) { return Math.abs(a.x + a.w / 2 - b.x - b.w / 2) + Math.abs(a.y + a.h / 2 - b.y - b.h / 2); }

    /* A* from every start door to every end door. A state is a cell and the way the wire is heading in it; an
       arrival that is not heading into the box pays one more bend, so it is queued as a finish at its true cost
       and the search ends when a finish is the cheapest thing left. */
    function search(starts, ends, regionA, regionB) {
      if (!starts.length || !ends.length) return null;
      const startAt = new Map(starts.map((s) => [stateOf(s.i, s.j, s.d), s]));
      const endAt = new Map(ends.map((t) => [t.j * cols + t.i, t]));
      const near = (i, j) => { let m = Infinity; for (const t of ends) m = Math.min(m, Math.abs(t.i - i) + Math.abs(t.j - j)); return m; };
      const best = new Map(), parent = new Map(), open = heap();
      for (const [id, s] of startAt) { best.set(id, 0); parent.set(id, -1); open.push([near(s.i, s.j), id, 0, false]); }
      while (open.size) {
        const [, id, g, finished] = open.pop();
        if (finished) return unwind(id);
        if (g > best.get(id)) continue;
        const cell = id >> 2, d = id & 3, i = cell % cols, j = (cell - i) / cols, door = endAt.get(cell);
        if (door) { const total = g + (d === (door.d + 2) % 4 ? 0 : BEND); open.push([total, id, total, true]); }
        for (let nd = 0; nd < 4; nd++) {
          if (nd === (d + 2) % 4) continue;
          const ni = i + DIRS[nd].x, nj = j + DIRS[nd].y;
          if (ni < 0 || nj < 0 || ni >= cols || nj >= rows || blocked[nj * cols + ni]) continue;
          const c = nj * cols + ni, across = DIRS[nd].x !== 0 ? 1 : 2;
          let step = 1 + (nd !== d ? BEND : 0);
          if (region[c] && region[c] !== regionA && region[c] !== regionB) step += OTHER_REGION;
          if (used[c]) step += used[c] & across ? SHARED : CROSSED;
          const nid = c * 4 + nd, ng = g + step;
          if (!best.has(nid) || ng < best.get(nid)) { best.set(nid, ng); parent.set(nid, id); open.push([ng + near(ni, nj), nid, ng, false]); }
        }
      }
      return null;
      function unwind(last) {
        const cells = [];
        for (let at = last; at !== -1; at = parent.get(at)) cells.push({ i: (at >> 2) % cols, j: Math.floor((at >> 2) / cols), d: at & 3 });
        cells.reverse();
        const first = cells[0];
        return { cells, start: startAt.get(stateOf(first.i, first.j, first.d)), end: endAt.get(cells[cells.length - 1].j * cols + cells[cells.length - 1].i) };
      }
    }
    function mark(cells) {
      cells.forEach((c, k) => { used[c.j * cols + c.i] |= cells[k + 1] ? (cells[k + 1].j === c.j ? 1 : 2) : (c.d % 2 === 0 ? 1 : 2); });
    }
    /* From the box's side to the first cell, through the cells' corners, to the other box's side. */
    function polyline(way, from, to) {
      const pts = way.cells.map((c) => ({ x: cellX(c.i), y: cellY(c.j) }));
      const turns = (k) => (pts[k].x - pts[k - 1].x) * (pts[k + 1].y - pts[k].y) !== (pts[k].y - pts[k - 1].y) * (pts[k + 1].x - pts[k].x);
      const corners = pts.filter((p, k) => k === 0 || k === pts.length - 1 || turns(k));
      const onSide = (box, side, p) => (side === "R" ? { x: box.x + box.w, y: p.y } : side === "L" ? { x: box.x, y: p.y } : side === "D" ? { x: p.x, y: box.y + box.h } : { x: p.x, y: box.y });
      return { pts: [onSide(from, way.start.side, corners[0]), ...corners, onSide(to, way.end.side, corners[corners.length - 1])], sa: way.start.side, sb: way.end.side };
    }
  }
  return { route };
})();
