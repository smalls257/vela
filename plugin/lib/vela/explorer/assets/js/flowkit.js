/* The flow kit: one canvas renderer for a played flow, and the clip recorder. Ported from
   prototypes/gallery/flows/common.js.

   One renderer draws the live stage, present mode and the saved clip, so the three cannot drift apart. The renderer
   is a pure function of (flow, step, time in step): a clip is deterministic because every frame is computed from
   its timestamp, not from accumulated animation state. Lanes keep the map's left-to-right order (pins.py), and a
   lane the flow does not touch keeps its place at half width, so every flow shares one stage. */
const FlowKit = (() => {
  // Ten hues per theme (--lanes in themes.css) that stay apart on the room and away from the lamp colors. The
  // palette is read when a frame is drawn, so the stage, present mode and a clip all follow the theme.
  const C = {};
  let PALETTE = [], paletteOf = null;
  function readPalette() {
    if (paletteOf === Theme.id) return;
    paletteOf = Theme.id;
    PALETTE = Theme.list("lanes");
    Object.assign(C, { room: Theme.c("room"), deck: Theme.c("deck"), deck2: Theme.c("deck-2"), ink: Theme.c("ink"), ink2: Theme.c("ink-2"),
      muted: Theme.c("ink-3"), rule: Theme.c("rule-3"), settled: Theme.c("ink-3"), heuristic: Theme.c("heuristic-ink") });
  }
  readPalette();
  const UI = getComputedStyle(document.documentElement).getPropertyValue("--ui") || "system-ui, sans-serif";
  const SERIF = getComputedStyle(document.documentElement).getPropertyValue("--serif") || "Georgia, serif";
  const lanes = D.lanes;
  const laneColor = (id) => { readPalette(); return PALETTE[(LANE_INDEX[id] ?? 0) % PALETTE.length]; };
  const laneName = (id) => (lanes[LANE_INDEX[id]] || { name: titleOf(id) }).name;
  const emblemImg = {};
  Assets.onReady(() => { for (const l of lanes) { const url = Assets.emblem(l.id); if (url) { const img = new Image(); img.src = url; emblemImg[l.id] = img; } } });

  /* The record's view of a flow, shaped for playing; or, when a branch is chosen in the header's Show picker, that
     branch's steps (branches.js), so one diagram draws both. */
  function flowOf(key) {
    const branch = typeof Branches !== "undefined" ? Branches.flowFor(key) : null;
    if (branch) return branch;
    const f = FLOW[key], e = E[key];
    return { key, id: e.id, title: e.title, state: e.state || "", steps: f.steps, unknowns: f.unknowns };
  }
  /* A flow whose steps never say who sends: every arrow is drawn from the contract's provider. On a call an arrow
     reads as fact, so such a flow carries one line saying so (a flow with some named senders is labeled per arrow). */
  const INFERRED_NOTE = "Arrow directions are guessed from who provides each contract";
  function inferredNote(key) {
    const msgs = FLOW[key].steps.flatMap((stp) => stp.messages);
    return msgs.length && msgs.every((m) => m.direction === "inferred") ? INFERRED_NOTE : "";
  }
  function unitsOf(step) {
    if (step.messages.length) {
      const out = [];
      step.messages.forEach((m, mi) => {
        if (m.kind === "answer") { out.push({ kind: "reply", mi, from: m.from, to: m.to, msg: m }); return; }  // an answer drawn later than its call
        out.push({ kind: "msg", mi, from: m.from, to: m.to, msg: m }); if (m.kind === "request") out.push({ kind: "reply", mi, from: m.to, to: m.from, msg: m });
      });
      return out;
    }
    if (step.self && LANE_INDEX[step.self] !== undefined) return [{ kind: "self", lane: step.self }];
    if (step.ref) return [{ kind: "ref", ref: step.ref }];
    return [{ kind: "note" }];
  }
  const openPins = (step) => step.unknowns.filter((p) => ASK[p.id] && ASK[p.id].state === "open");
  function flowQuestions(flow) {
    const ids = new Set(flow.unknowns);
    flow.steps.forEach((st) => st.unknowns.forEach((p) => ids.add(p.id)));
    return [...ids].filter((id) => ASK[id]);
  }
  function touchedLanes(flow) {
    const set = new Set();
    flow.steps.forEach((st) => { st.messages.forEach((m) => { set.add(m.from); set.add(m.to); }); if (st.self) set.add(st.self); });
    return set;
  }
  const stepTiming = (step, Dt) => unitsOf(step).map((u, j) => ({ u, t0: j * Dt, t1: (j + 1) * Dt }));
  const travelTime = (step, Dt) => unitsOf(step).length * Dt;
  // On a light room (a theme that rings its lamps) a lamp's color is a fill, not ink: words take the lamp's text
  // form, and the white override draws its line in its ring color, so CON-003 stays readable on white.
  const ringed = () => Theme.c("lamp-edge") !== "transparent";
  const lampText = (lv) => (ringed() ? Theme.c(lv + "-text") : LIGHT[lv].color);
  const lampLine = (lv) => (ringed() && lv === "override" ? Theme.c("override-edge") : LIGHT[lv].color);
  const markerColor = (id) => { const lv = unknownLevel(id); return lv === "resolved" || lv === "dark" ? null : LIGHT[lv].color; };

  function layout(flow, box) {
    const { x, y, w, h: ht } = box, k = box.s ?? 1;
    const gutter = 46 * k, headerH = 44 * k, top = y + headerH + 18 * k, bottom = y + ht - 10 * k;
    const touched = touchedLanes(flow);
    // Untouched lanes keep their place but narrow; past ten lanes they narrow to a mark, so the touched ones get the room.
    const idle = lanes.length > 10 ? 0.22 : 0.5;
    const weight = lanes.map((l) => (touched.has(l.id) ? 1 : idle));
    const unit = (w - gutter) / Math.max(1, weight.reduce((a, b) => a + b, 0));
    let acc = x + gutter;
    const laneX = weight.map((wt) => { const c = acc + (wt * unit) / 2; acc += wt * unit; return c; });
    const rows = [];
    flow.steps.forEach((step, si) => unitsOf(step).forEach((u, ui) => rows.push({ si, ui, u })));
    const gaps = Math.max(0, flow.steps.length - 1);
    const rowH = Math.min(66 * k, (bottom - top) / Math.max(1, rows.length + gaps * 0.35));
    let cy = top + rowH * 0.5, prev = -1;
    for (const r of rows) { if (prev !== -1 && r.si !== prev) cy += rowH * 0.35; r.y = cy; cy += rowH; prev = r.si; }
    // One pill per call and answer: an arrow that answers the arrow just above it, over the same contract between the
    // same two lanes, carries no second pill (two pills for one exchange overlapped where rows are close).
    rows.forEach((r, i) => {
      const before = rows[i - 1];
      if (r.u.kind !== "msg" || !before || !before.u.msg) return;
      const same = before.u.msg.contract === r.u.msg.contract && new Set([before.u.from, before.u.to, r.u.from, r.u.to]).size === 2;
      if (same) r.noChip = true;
    });
    return { x, y, w, h: ht, s: k, gutter, headerH, colW: unit, idle, laneX, rows, rowH, top, bottom, touched, flow };
  }

  const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  function rr(ctx, x, y, w, ht, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + ht, r); ctx.arcTo(x + w, y + ht, x, y + ht, r); ctx.arcTo(x, y + ht, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
  function wrap(ctx, text, maxW) {
    const words = text.split(/\s+/), out = []; let line = "";
    for (const w of words) { const t = line ? line + " " + w : w; if (ctx.measureText(t).width > maxW && line) { out.push(line); line = w; } else line = t; }
    if (line) out.push(line);
    return out;
  }
  function fitText(ctx, text, maxW) {
    if (ctx.measureText(text).width <= maxW) return text;
    let t = text;
    while (t.length > 1 && ctx.measureText(t + "…").width > maxW) t = t.slice(0, -1);
    return t.trimEnd() + "…";
  }
  function arrowHead(ctx, x, y, dir, size, filled, color) {
    ctx.beginPath(); ctx.moveTo(x - dir * size, y - size * 0.62); ctx.lineTo(x, y); ctx.lineTo(x - dir * size, y + size * 0.62);
    if (filled) { ctx.closePath(); ctx.fillStyle = color; ctx.fill(); } else { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1.4, size * 0.16); ctx.stroke(); }
  }

  /* st.cur: the step being played (-1 before the first, steps.length when all have played); st.tau: seconds
     since it started; st.clock: seconds, for the breathing of open markers; st.D: seconds per message. */
  function drawScene(ctx, G, st) {
    const { s: k, flow } = G, Dt = st.D ?? 0.8, hits = [], cur = st.cur, tau = st.tau ?? 99, still = reducedMotion() && !st.recording;
    const curTiming = flow.steps[cur] ? stepTiming(flow.steps[cur], Dt) : [];
    const hl = st.highlight ? new Set(st.highlight) : null;
    lanes.forEach((lane, i) => {
      const X = G.laneX[i], y0 = G.y + G.headerH + 4 * k, y1 = G.bottom;
      let amp = 0, dt = 0;
      if (!still) for (const { u, t1, t0 } of curTiming) {
        const hitLane = u.kind === "self" ? u.lane : u.to, ta = u.kind === "self" ? t0 + Dt * 0.45 : t1;
        if (hitLane === lane.id && tau >= ta && tau < ta + 1.6) { dt = tau - ta; amp = 5.5 * k * Math.exp(-dt / 0.38); }
      }
      const on = G.touched.has(lane.id);
      ctx.strokeStyle = hexA(laneColor(lane.id), on ? 0.45 : 0.14); ctx.lineWidth = on ? 1.6 * k : 1 * k;
      ctx.beginPath();
      for (let j = 0; j <= 40; j++) { const yy = y0 + ((y1 - y0) * j) / 40, off = amp * Math.sin((Math.PI * j) / 40) * Math.sin(2 * Math.PI * 7 * dt); j ? ctx.lineTo(X + off, yy) : ctx.moveTo(X + off, yy); }
      ctx.stroke();
    });
    lanes.forEach((lane, i) => {
      const X = G.laneX[i], on = G.touched.has(lane.id), width = on ? G.colW : G.colW * G.idle;
      if (st.seen) { st.seen.add("flow.lane"); if (!on) st.seen.add("flow.lane.idle"); }
      ctx.save(); ctx.globalAlpha = on ? 1 : 0.4;
      if (!on && width < 64 * k) {  // too narrow for a name: a mark in its place, the name on hover
        ctx.beginPath(); ctx.arc(X, G.y + 22 * k, 4 * k, 0, 7);
        if (lane.kind === "partner") { ctx.strokeStyle = laneColor(lane.id); ctx.lineWidth = 1.5 * k; ctx.stroke(); } else { ctx.fillStyle = laneColor(lane.id); ctx.fill(); }
        ctx.restore();
        hits.push({ type: "lane", id: lane.id, x: X - width / 2, y: G.y + 6 * k, w: width, h: 32 * k });
        return;
      }
      const room = width - 40 * k;
      ctx.font = `600 ${14 * k}px ${UI}`;
      if (ctx.measureText(lane.name).width > room) ctx.font = `600 ${12 * k}px ${UI}`;
      // A name too long for one line wraps to two before it is ever cut.
      let lines = [lane.name];
      if (ctx.measureText(lane.name).width > room && lane.name.includes(" ")) {
        const words = lane.name.split(" "); let best = 1, bestW = Infinity;
        for (let j = 1; j < words.length; j++) { const w = Math.max(ctx.measureText(words.slice(0, j).join(" ")).width, ctx.measureText(words.slice(j).join(" ")).width); if (w < bestW) { bestW = w; best = j; } }
        lines = [words.slice(0, best).join(" "), words.slice(best).join(" ")];
        if (Math.max(...lines.map((t) => ctx.measureText(t).width)) > room) ctx.font = `600 ${11 * k}px ${UI}`;
      }
      lines = lines.map((t) => fitText(ctx, t, Math.max(30 * k, room)));
      const label = lines[0], tw = Math.max(...lines.map((t) => ctx.measureText(t).width));
      const bw = Math.min(width - 8 * k, tw + 40 * k), bh = (lines.length > 1 ? 40 : 32) * k, bx = X - bw / 2, by = G.y + 6 * k - (lines.length > 1 ? 4 * k : 0);
      let glow = 0;
      for (const { u, t1, t0 } of curTiming) { const hitLane = u.kind === "self" ? u.lane : u.to, ta = u.kind === "self" ? t0 : t1; if (hitLane === lane.id && tau >= ta) glow = Math.max(glow, Math.exp(-(tau - ta) / 0.7)); }
      if (hl && hl.has(lane.id)) glow = Math.max(glow, 0.7);
      if (glow > 0.02 && (glowOn() || st.recording)) { ctx.shadowColor = hexA(laneColor(lane.id), 0.75 * glow); ctx.shadowBlur = 24 * k * glow; }
      rr(ctx, bx, by, bw, bh, bh / 2); ctx.fillStyle = C.deck2; ctx.fill(); ctx.shadowBlur = 0;
      ctx.strokeStyle = hexA(laneColor(lane.id), 0.45 + 0.5 * glow); ctx.lineWidth = (hl && hl.has(lane.id) ? 2 : 1) * k; ctx.stroke();
      const dx = bx + 16 * k, dy = by + bh / 2, img = st.images !== false && emblemImg[lane.id];
      if (img && img.complete && img.naturalWidth) { ctx.save(); ctx.beginPath(); ctx.arc(dx, dy, 9 * k, 0, 7); ctx.clip(); ctx.drawImage(img, dx - 9 * k, dy - 9 * k, 18 * k, 18 * k); ctx.restore(); }
      // no emblem: the lane's own glyph, in the lane's color, so the color still says which lane it is
      else Icons.stroke(ctx, Icons.name(lane.id), dx, dy, 15 * k, laneColor(lane.id));
      ctx.fillStyle = C.ink; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      if (lines.length > 1) { ctx.fillText(lines[0], dx + 12 * k, dy - 7 * k); ctx.fillText(lines[1], dx + 12 * k, dy + 8 * k); }
      else ctx.fillText(label, dx + 12 * k, dy + 0.5 * k);
      ctx.restore();
      hits.push({ type: "lane", id: lane.id, x: bx, y: by, w: bw, h: bh });
    });
    const firstRow = {};
    G.rows.forEach((r) => { if (!(r.si in firstRow)) firstRow[r.si] = r; });
    for (const r of G.rows) {
      const step = flow.steps[r.si], phase = r.si < cur ? "past" : r.si === cur ? "now" : "future";
      const timing = phase === "now" ? curTiming[r.ui] : null;
      const p = phase === "past" ? 1 : phase === "future" ? 0 : clamp((tau - timing.t0) / (timing.t1 - timing.t0), 0, 1);
      drawUnit(ctx, G, r, step, phase, p, st, hits);
    }
    for (const [si, r] of Object.entries(firstRow)) {
      if (st.seen) st.seen.add("flow.stepno");
      const i = +si, cx = G.x + G.gutter * 0.42, cy = r.y, rad = 11 * k;
      ctx.beginPath(); ctx.arc(cx, cy, rad, 0, 7);
      if (i === cur) { ctx.fillStyle = C.ink; ctx.fill(); } else { ctx.fillStyle = C.deck; ctx.fill(); ctx.strokeStyle = i < cur ? C.ink2 : C.rule; ctx.lineWidth = 1 * k; ctx.stroke(); }
      ctx.fillStyle = i === cur ? C.room : i < cur ? C.ink : C.muted;
      ctx.font = `600 ${11.5 * k}px ${UI}`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(String(flow.steps[i].n), cx, cy + 0.5 * k);
      hits.push({ type: "step", si: i, x: cx - rad, y: cy - rad, w: rad * 2, h: rad * 2 });
    }
    for (const [si, r] of Object.entries(firstRow)) drawMarkers(ctx, G, +si, r, st, hits);
    return hits;
  }
  // A step that leaves the happy path (a branch chosen in the Show picker) is drawn in amber, whatever its lane.
  const amber = (phase) => hexA(Theme.c("caution"), phase === "future" ? 0.45 : phase === "past" ? 0.8 : 1);
  function unitColor(phase, laneId, a = 1) {
    if (phase === "now") return hexA(laneColor(laneId), a);
    if (phase === "past") return hexA(C.ink, 0.5 * a);
    return hexA(C.ink, 0.14 * a);
  }
  function drawUnit(ctx, G, r, step, phase, p, st, hits) {
    const k = G.s, u = r.u, y = r.y;
    if (u.kind === "msg" || u.kind === "reply") {
      const x1 = G.laneX[LANE_INDEX[u.from]], x2 = G.laneX[LANE_INDEX[u.to]];
      if (x1 === undefined || x2 === undefined) return;
      const dir = Math.sign(x2 - x1) || 1, a = x1 + dir * 5 * k, b = x2 - dir * 6 * k, e = ease(p);
      const head = phase === "future" ? b : a + (b - a) * e, col = step.differs ? amber(phase) : unitColor(phase, u.from);
      if (step.differs && st.seen) st.seen.add("flow.differs");
      ctx.lineCap = "round";
      ctx.setLineDash(u.kind === "reply" ? [5 * k, 5 * k] : phase === "future" ? [2 * k, 5 * k] : []);
      ctx.strokeStyle = col; ctx.lineWidth = (phase === "now" ? 2.4 : 1.6) * k;
      ctx.beginPath(); ctx.moveTo(a, y); ctx.lineTo(phase === "future" ? b : head, y); ctx.stroke(); ctx.setLineDash([]);
      const stated = u.kind === "msg" && u.msg.direction === "stated";
      if (st.seen) { st.seen.add(u.kind === "reply" ? "flow.reply" : stated ? "flow.stated" : "flow.inferred"); if (u.kind === "msg" && phase === "future") st.seen.add("flow.future"); }
      if (phase !== "now" || p >= 1) arrowHead(ctx, b + dir * 2 * k, y, dir, 9 * k, stated, col);
      if (phase === "now" && p > 0 && p < 1) {
        const tail = Math.max(0, e - 0.18), tx = a + (b - a) * tail;
        const grad = ctx.createLinearGradient(tx, y, head, y);
        grad.addColorStop(0, hexA(laneColor(u.from), 0)); grad.addColorStop(1, hexA(laneColor(u.from), 0.95));
        ctx.strokeStyle = grad; ctx.lineWidth = 5 * k; ctx.beginPath(); ctx.moveTo(tx, y); ctx.lineTo(head, y); ctx.stroke();
        const glow = ctx.createRadialGradient(head, y, 0, head, y, 18 * k);
        glow.addColorStop(0, hexA(laneColor(u.from), 0.7)); glow.addColorStop(1, hexA(laneColor(u.from), 0));
        ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(head, y, 18 * k, 0, 7); ctx.fill();
        ctx.fillStyle = C.ink; ctx.beginPath(); ctx.arc(head, y, 4.5 * k, 0, 7); ctx.fill();
      }
      // Where rows sit close (a long flow on a short stage) the pill rides on its arrow instead of above it, and where even that
      // would touch the next row it is left out: the caption and the panel still name the contract. Pills never overlap.
      if (u.kind === "msg" && !r.noChip && G.rowH >= 21 * k) {
        // the pill names the contract; its ID follows in small type only when there is room (names, not codes)
        const con = CONTRACT[u.msg.contract], mid = (x1 + x2) / 2, span = Math.abs(x2 - x1) - 34 * k;
        ctx.font = `400 ${10 * k}px ${UI}`;
        const idW = ctx.measureText(con.id).width;
        ctx.font = `600 ${11.5 * k}px ${UI}`;
        const whole = ctx.measureText(con.title).width, withId = whole + idW + 6 * k <= span - 16 * k;
        const name = fitText(ctx, con.title, Math.max(24 * k, span - 16 * k));
        const nameW = ctx.measureText(name).width;
        const cw = nameW + (withId ? idW + 6 * k : 0) + 16 * k, ch = 19 * k, cx = mid - cw / 2, cy = G.rowH >= 31 * k ? y - ch - 6 * k : y - ch / 2;
        const lv = levelOf(con.id);
        if (st.seen) { st.seen.add("flow.chip"); if (lv !== "dark" && phase !== "future") st.seen.add("lamp." + lv); }
        ctx.globalAlpha = phase === "future" ? 0.4 : 1;
        rr(ctx, cx, cy, cw, ch, ch / 2); ctx.fillStyle = C.deck; ctx.fill();
        ctx.strokeStyle = step.differs ? amber(phase) : lv !== "dark" && phase !== "future" ? hexA(lampLine(lv), 0.8) : phase === "now" ? hexA(laneColor(u.from), 0.7) : C.rule;
        ctx.lineWidth = (step.differs ? 1.8 : 1) * k; ctx.stroke();
        ctx.textBaseline = "middle"; ctx.textAlign = "left";
        ctx.font = `600 ${11.5 * k}px ${UI}`; ctx.fillStyle = lv !== "dark" ? lampText(lv) : C.ink; ctx.fillText(name, cx + 8 * k, cy + ch / 2 + 0.5 * k);
        if (withId) { ctx.font = `400 ${10 * k}px ${UI}`; ctx.fillStyle = C.muted; ctx.fillText(con.id, cx + 8 * k + nameW + 6 * k, cy + ch / 2 + 0.5 * k); }
        ctx.globalAlpha = 1;
        hits.push({ type: "contract", id: con.id, si: r.si, x: cx, y: cy, w: cw, h: ch });
        if (!stated && phase === "now" && p >= 1 && st.labels !== false) {
          ctx.font = `italic 400 ${10.5 * k}px ${SERIF}`; ctx.fillStyle = C.heuristic; ctx.textAlign = "center"; ctx.textBaseline = "top";
          ctx.fillText("direction guessed", mid, y + 6 * k);
        }
      }
      hits.push({ type: "row", si: r.si, x: Math.min(x1, x2), y: y - 14 * k, w: Math.abs(x2 - x1), h: 28 * k });
    } else if (u.kind === "self") {
      const X = G.laneX[LANE_INDEX[u.lane]], col = step.differs ? amber(phase) : unitColor(phase, u.lane), lw = 34 * k, lh = 11 * k;
      if (step.differs && st.seen) st.seen.add("flow.differs");
      if (st.seen) { st.seen.add("flow.self"); if (phase === "future") st.seen.add("flow.future"); }
      ctx.strokeStyle = col; ctx.lineWidth = (phase === "now" ? 2.2 : 1.5) * k;
      ctx.setLineDash(phase === "future" ? [2 * k, 4 * k] : []);
      ctx.beginPath(); ctx.moveTo(X + 4 * k, y - lh); ctx.bezierCurveTo(X + lw, y - lh * 1.5, X + lw, y + lh * 1.5, X + 6 * k, y + lh); ctx.stroke(); ctx.setLineDash([]);
      arrowHead(ctx, X + 5 * k, y + lh * 0.95, -1, 7 * k, true, col);
      if (phase === "now" && !reducedMotion()) {
        ctx.strokeStyle = hexA(laneColor(u.lane), 0.6 * (1 - p)); ctx.lineWidth = 2 * k; ctx.beginPath(); ctx.arc(X, y, 6 * k + p * 22 * k, 0, 7); ctx.stroke();
      }
      ctx.fillStyle = phase === "future" ? hexA(C.ink, 0.3) : phase === "now" ? C.ink : C.ink2;
      ctx.font = `400 ${12.5 * k}px ${SERIF}`; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      const room = Math.min(G.colW * 1.8, G.x + G.w - (X + lw + 8 * k) - 8 * k);
      if (room > 60 * k) {
        const t = fitText(ctx, step.short.replace(/\.$/, ""), room), tw = ctx.measureText(t).width, fill = ctx.fillStyle;
        rr(ctx, X + lw + 2 * k, y - 11 * k, tw + 12 * k, 22 * k, 6 * k); ctx.fillStyle = hexA(C.room, 0.9); ctx.fill();
        ctx.fillStyle = fill; ctx.fillText(t, X + lw + 8 * k, y + 0.5 * k);
      }
      hits.push({ type: "row", si: r.si, x: X - 10 * k, y: y - 14 * k, w: lw + room, h: 28 * k });
    } else {
      if (st.seen) st.seen.add("flow.band");
      const xs = [...G.touched].map((id) => G.laneX[LANE_INDEX[id]]).filter((x) => x !== undefined);
      const x0 = xs.length ? Math.min(...xs) - G.colW * 0.32 : G.x + G.gutter, x1 = xs.length ? Math.max(...xs) + G.colW * 0.32 : G.x + G.w - 10, bh = Math.min(G.rowH * 0.66, 32 * k);
      ctx.globalAlpha = phase === "future" ? 0.4 : 1;
      rr(ctx, x0, y - bh / 2, x1 - x0, bh, 8 * k); ctx.fillStyle = phase === "now" ? hexA(C.deck2, 0.95) : hexA(C.deck, 0.7); ctx.fill();
      ctx.setLineDash([4 * k, 4 * k]); ctx.strokeStyle = step.differs ? amber(phase) : phase === "now" ? C.ink2 : C.rule; ctx.lineWidth = (step.differs ? 1.6 : 1) * k; ctx.stroke(); ctx.setLineDash([]);
      if (step.differs && st.seen) st.seen.add("flow.differs");
      const ref = u.ref && FLOW[u.ref];
      ctx.font = `400 ${12.5 * k}px ${SERIF}`; ctx.fillStyle = C.ink; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(fitText(ctx, ref ? `Repeats “${E[u.ref].title}” (${E[u.ref].id})` : step.short, x1 - x0 - 24 * k), (x0 + x1) / 2, y + 0.5 * k);
      ctx.globalAlpha = 1;
      hits.push({ type: ref ? "ref" : "row", id: ref && u.ref, si: r.si, x: x0, y: y - bh / 2, w: x1 - x0, h: bh });
    }
  }
  function markerPoint(G, r) {
    const u = r.u, k = G.s;
    if (u.kind === "msg") { const x1 = G.laneX[LANE_INDEX[u.from]], x2 = G.laneX[LANE_INDEX[u.to]]; return { x: x1 + (x2 - x1) * 0.78, y: r.y }; }
    if (u.kind === "self") return { x: G.laneX[LANE_INDEX[u.lane]] + 46 * k, y: r.y - 13 * k };
    const xs = [...G.touched].map((id) => G.laneX[LANE_INDEX[id]]).filter((x) => x !== undefined);
    return { x: (xs.length ? Math.max(...xs) : G.x + G.w - 60) + G.colW * 0.32, y: r.y };
  }
  function drawMarkers(ctx, G, si, r, st, hits) {
    const step = G.flow.steps[si], k = G.s;
    if (!step.unknowns.length) return;
    const base = markerPoint(G, r);
    step.unknowns.forEach((pin, j) => {
      if (!ASK[pin.id]) return;
      const x = base.x + j * 17 * k, y = base.y, color = markerColor(pin.id);
      if (st.seen) { st.seen.add(color ? "flow.pin" : "flow.pin.settled"); if (color) st.seen.add("lamp." + unknownLevel(pin.id)); }
      if (color) {
        const breath = reducedMotion() && !st.recording ? 0.6 : 0.5 + 0.5 * Math.sin((st.clock || 0) * 2.4);
        if (glowOn() || st.recording) {
          const R = (11 + 6 * breath) * k, g = ctx.createRadialGradient(x, y, 0, x, y, R);
          g.addColorStop(0, hexA(color, 0.55)); g.addColorStop(1, hexA(color, 0));
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, R, 0, 7); ctx.fill();
        }
        ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 5.5 * k, 0, 7); ctx.fill();
        ctx.strokeStyle = C.room; ctx.lineWidth = 1.5 * k; ctx.stroke();
      } else {
        ctx.fillStyle = C.room; ctx.beginPath(); ctx.arc(x, y, 6 * k, 0, 7); ctx.fill();
        ctx.strokeStyle = C.settled; ctx.lineWidth = 1.3 * k; ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x - 2.6 * k, y + 0.2 * k); ctx.lineTo(x - 0.6 * k, y + 2.2 * k); ctx.lineTo(x + 2.8 * k, y - 2 * k); ctx.stroke();
      }
      hits.push({ type: "unknown", id: pin.id, si, x: x - 10 * k, y: y - 10 * k, w: 20 * k, h: 20 * k });
    });
  }

  /* ---------- the clip: title card, steps with captions, end card ---------- */
  const CLIP = { W: 1280, H: 720, title: 2.4, end: 3.4, maxSteps: 14 };
  function clipPlan(flow) {
    const stepDur = Math.min(2.2, CLIP.maxSteps / Math.max(1, flow.steps.length));
    return { stepDur, D: Math.min(0.7, (stepDur * 0.62) / Math.max(1, ...flow.steps.map((st) => unitsOf(st).length))), total: CLIP.title + stepDur * flow.steps.length + CLIP.end };
  }
  function background(ctx, W, H) {
    readPalette();
    ctx.fillStyle = C.room; ctx.fillRect(0, 0, W, H);
    const g = ctx.createRadialGradient(W * 0.35, H * 0.2, 0, W * 0.35, H * 0.2, W * 0.8);
    g.addColorStop(0, "rgba(255,255,255,.05)"); g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  function drawTitleCard(ctx, flow, T, W, H) {
    const k = W / 1280, b = W < 1000 ? 1.8 : 1;
    background(ctx, W, H);
    const touched = [...touchedLanes(flow)].sort((a, c) => LANE_INDEX[a] - LANE_INDEX[c]);
    touched.forEach((id, j) => {
      const X = W * 0.66 + j * 60 * k, dt = T - 0.25 - j * 0.22, amp = dt > 0 ? 9 * k * Math.exp(-dt / 0.45) : 0;
      ctx.strokeStyle = hexA(laneColor(id), 0.65); ctx.lineWidth = 2.2 * k; ctx.beginPath();
      for (let q = 0; q <= 40; q++) { const yy = H * 0.16 + (H * 0.68 * q) / 40, off = amp * Math.sin((Math.PI * q) / 40) * Math.sin(2 * Math.PI * 6 * Math.max(0, dt)); q ? ctx.lineTo(X + off, yy) : ctx.moveTo(X + off, yy); }
      ctx.stroke();
    });
    ctx.globalAlpha = clamp(T / 0.4, 0, 1); ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    ctx.fillStyle = C.muted; ctx.font = `500 ${22 * k * b}px ${UI}`;
    ctx.fillText(`${flow.state ? stateWord(flow.state) : "Status not recorded"} · ${D.title}`, 96 * k, 250 * k);
    ctx.fillStyle = C.ink; ctx.font = `400 ${64 * k * Math.min(b, 1.3)}px ${SERIF}`;
    const lines = wrap(ctx, flow.title, 680 * k);
    lines.forEach((l, i) => ctx.fillText(l, 92 * k, 330 * k + i * 72 * k));
    let yy = 330 * k + lines.length * 72 * k + 8 * k, xx = 96 * k;
    ctx.font = `500 ${21 * k * b}px ${UI}`;
    touched.forEach((id) => {
      const name = laneName(id);
      if (xx + ctx.measureText(name).width > W * 0.6) return;
      ctx.fillStyle = laneColor(id); ctx.beginPath(); ctx.arc(xx + 6 * k * b, yy - 7 * k * b, 6 * k * b, 0, 7); ctx.fill();
      ctx.fillStyle = C.ink2; ctx.fillText(name, xx + 18 * k * b, yy); xx += ctx.measureText(name).width + 40 * k * b;
    });
    const open = flowQuestions(flow).filter((id) => ASK[id].state === "open").length;
    ctx.fillStyle = C.muted; ctx.font = `400 ${20 * k * b}px ${UI}`;
    ctx.fillText(`${plural(flow.steps.length, "step")}. ${open ? plural(open, "open question") : "No open questions"}.`, 96 * k, yy + 44 * k * b);
    ctx.globalAlpha = 1;
  }
  function drawEndCard(ctx, flow, T, W, H) {
    const k = W / 1280;
    background(ctx, W, H);
    ctx.globalAlpha = clamp(T / 0.35, 0, 1);
    const qs = flowQuestions(flow), open = qs.filter((id) => ASK[id].state === "open"), settled = qs.filter((id) => ASK[id].state !== "open");
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = C.ink; ctx.font = `400 ${46 * k}px ${SERIF}`;
    ctx.fillText(open.length ? "Still open on this flow" : "Nothing open on this flow", 96 * k, 170 * k);
    let y = 240 * k;
    open.slice(0, 3).forEach((id) => {
      const q = ASK[id], color = markerColor(id) || C.muted;
      ctx.fillStyle = color; ctx.beginPath(); ctx.arc(104 * k, y - 8 * k, 8 * k, 0, 7); ctx.fill();
      ctx.fillStyle = C.ink; ctx.font = `600 ${24 * k}px ${UI}`; ctx.fillText(`${id} ${E[id] ? E[id].title : ""}`, 128 * k, y);
      ctx.font = `400 ${21 * k}px ${SERIF}`; ctx.fillStyle = C.ink2;
      const lines = wrap(ctx, q.question || "", 1000 * k).slice(0, 3);
      lines.forEach((l, i) => ctx.fillText(l, 128 * k, y + 36 * k + i * 29 * k));
      ctx.font = `500 ${18 * k}px ${UI}`; ctx.fillStyle = color;
      ctx.fillText(`Ask ${q.ask.name}${q.ask.inferred ? " (a guess)" : ""} by ${day(q.askBy)}`, 128 * k, y + 36 * k + lines.length * 29 * k + 8 * k);
      y += 36 * k + lines.length * 29 * k + 64 * k;
    });
    if (open.length > 3) { ctx.fillStyle = C.muted; ctx.font = `400 ${20 * k}px ${UI}`; ctx.fillText(`And ${open.length - 3} more in the plan.`, 128 * k, y); y += 44 * k; }
    if (settled.length) {
      ctx.fillStyle = C.muted; ctx.font = `400 ${19 * k}px ${UI}`;
      wrap(ctx, `Answered since the flow was written: ${settled.map((id) => (E[id] ? E[id].title : id)).join(", ")}.`, 1080 * k).forEach((l, i) => ctx.fillText(l, 96 * k, Math.max(y + 10 * k, 600 * k) + i * 28 * k));
    }
    ctx.globalAlpha = 1;
  }
  function drawCaption(ctx, flow, si, W, H, bandTop) {
    const k = W / 1280, step = flow.steps[si];
    ctx.fillStyle = C.deck; ctx.fillRect(0, bandTop, W, H - bandTop);
    ctx.fillStyle = C.rule; ctx.fillRect(0, bandTop, W, 1 * k);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = C.muted; ctx.font = `500 ${17 * k}px ${UI}`;
    ctx.fillText(`Step ${step.n} of ${flow.steps.length} · ${flow.title}`, 64 * k, bandTop + 40 * k);
    let size = 29, lines;
    do { ctx.font = `400 ${size * k}px ${SERIF}`; lines = wrap(ctx, step.short, W - 128 * k); size -= 2; } while (lines.length > 2 && size > 20);
    ctx.fillStyle = C.ink;
    lines.slice(0, 2).forEach((l, i) => ctx.fillText(l, 64 * k, bandTop + 80 * k + i * (size + 10) * k));
  }
  function drawClipFrame(ctx, flow, T, W = CLIP.W, H = CLIP.H, opts = {}) {
    const plan = clipPlan(flow), k = W / 1280;
    ctx.save();
    if (T < CLIP.title) { drawTitleCard(ctx, flow, T, W, H); ctx.restore(); return { phase: "title" }; }
    const tSteps = T - CLIP.title, j = Math.floor(tSteps / plan.stepDur);
    if (j >= flow.steps.length) { drawEndCard(ctx, flow, T - CLIP.title - plan.stepDur * flow.steps.length, W, H); ctx.restore(); return { phase: "end" }; }
    background(ctx, W, H);
    const band = H - 150 * k;
    const G = layout(flow, { x: 40 * k, y: 26 * k, w: W - 80 * k, h: band - 40 * k, s: k * 1.05 });
    drawScene(ctx, G, { cur: j, tau: tSteps - j * plan.stepDur, clock: T, D: plan.D, images: opts.images, recording: true });
    drawCaption(ctx, flow, j, W, H, band);
    ctx.restore();
    return { phase: "step", k: j };
  }
  function clipFormat() {
    const MR = window.MediaRecorder;
    if (!MR) return null;
    const options = [["video/mp4;codecs=avc1.42E01E", "mp4"], ["video/mp4", "mp4"], ["video/webm;codecs=vp9", "webm"], ["video/webm;codecs=vp8", "webm"], ["video/webm", "webm"]];
    const found = options.find(([m]) => MR.isTypeSupported(m));
    return found ? { mime: found[0], ext: found[1] } : null;
  }
  const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  /* Renders the clip in real time on a 1280 by 720 canvas and records it. Each frame is drawn from its own
     timestamp, so a slow frame drops a frame rather than shifting the content. With sound on, the motif is
     scheduled up front on the audio clock and recorded with it. Failure raises; it never returns an empty file. */
  async function recordClip(flow, { onProgress } = {}) {
    const fmt = clipFormat();
    if (!fmt) throw new Error("This browser cannot record video (no MediaRecorder with an MP4 or WebM type).");
    const canvas = document.createElement("canvas");
    canvas.width = CLIP.W; canvas.height = CLIP.H;
    canvas.style.cssText = "position:fixed;left:-9999px;top:0;width:640px;height:360px";
    document.body.appendChild(canvas);
    const ctx = canvas.getContext("2d"), plan = clipPlan(flow);
    drawClipFrame(ctx, flow, 0, CLIP.W, CLIP.H, { images: false });
    const stream = canvas.captureStream(30);
    let audioDest = null;
    if (Sound.enabled && Sound.ensure()) { audioDest = Sound.ctx.createMediaStreamDestination(); Sound.comp.connect(audioDest); audioDest.stream.getAudioTracks().forEach((t) => stream.addTrack(t)); }
    const rec = new MediaRecorder(stream, { mimeType: fmt.mime, videoBitsPerSecond: 4_000_000 }), chunks = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const done = new Promise((res, rej) => { rec.onstop = res; rec.onerror = (e) => rej(e.error || new Error("recording failed")); });
    rec.start(250);
    const t0 = performance.now();
    if (audioDest) { const base = Sound.ctx.currentTime + 0.03; flow.steps.forEach((step, j) => Sound.playStep(step, plan.D, { at: base + CLIP.title + j * plan.stepDur })); }
    await new Promise((resolve) => {
      function frame() {
        const T = (performance.now() - t0) / 1000;
        drawClipFrame(ctx, flow, Math.min(T, plan.total), CLIP.W, CLIP.H, { images: false });
        if (onProgress) onProgress(Math.min(1, T / plan.total), T);
        if (T >= plan.total) resolve(); else requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });
    rec.stop();
    await done;
    if (audioDest) Sound.comp.disconnect(audioDest);
    stream.getTracks().forEach((t) => t.stop());
    canvas.remove();
    if (!chunks.length) throw new Error("The recorder produced no data.");
    const blob = new Blob(chunks, { type: fmt.mime.split(";")[0] });
    return { blob, ext: fmt.ext, mime: fmt.mime, seconds: plan.total, name: `${slug(flow.title)}.${fmt.ext}` };
  }
  function download(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  /* ------------------------------------------------------------ the key
     The canvas has no elements to look at, so the key is made two ways that must agree. census() draws the flow on a
     scratch canvas, once at each step, and collects the looks the drawing code really used. expected() works the same
     looks out from the flow's data alone; the self-test compares the key to that. */
  const { ln, bx } = Legend;
  Legend.define("flow.stated", [ln({ stroke: "ink-2", w: 1.8, head: "fill" })], "Solid arrow: the step says who sends");
  Legend.define("flow.inferred", [ln({ stroke: "ink-2", w: 1.8, head: "open" })], "Open arrowhead: who sends is guessed from who provides the contract");
  Legend.define("flow.reply", [ln({ stroke: "ink-2", w: 1.8, head: "open", dash: "4 3" })], "Dashed arrow: the answer coming back");
  Legend.define("flow.self", [bx({ stroke: "ink-2", w: 1.8, x: 9, y: 3, width: 14, height: 10, rx: 5 })], "Loop on one column: an app doing this step on its own");
  Legend.define("flow.band", [bx({ stroke: "ink-3", w: 1.2, dash: "3 3", rx: 4, y: 3.5, height: 9 })], "Dashed band: a step with no sender, a note, or a repeat of another flow");
  Legend.define("flow.future", [ln({ stroke: "ink-4", w: 1.8, dash: "2 4.5" })], "Dotted line: a step that has not been played yet");
  Legend.define("flow.chip", [bx({ fill: "deck", stroke: "ink-3", w: 1.2, rx: 4, y: 4, height: 8 })], "Pill on an arrow: the contract used, outlined in its status color");
  Legend.define("flow.pin", [{ k: "dot", fill: "caution", r: 4.5 }], "Glowing dot at a step: an open question about this step, in its status color");
  Legend.define("flow.pin.settled", [{ k: "dot", fill: "room", stroke: "ink-3", w: 1.3, r: 5 }, { k: "text", t: "✓", fill: "ink-3", y: 11, size: 8 }], "Ring with a tick: a question about this step that has been answered");
  Legend.define("flow.lane", [bx({ fill: "deck-2", stroke: "ink-3", w: 1.2, rx: 4.5, y: 3.5, height: 9 }), { k: "dot", fill: "ink-2", x: 9, r: 2 }], "Pill at the top: one app or outside service, in its own color");
  Legend.define("flow.lane.idle", [bx({ fill: "deck-2", stroke: "ink-3", w: 1.2, rx: 4.5, y: 3.5, height: 9, opacity: 0.4 })], "Faded pill: this app or service takes no part in the flow");
  Legend.define("flow.differs", [ln({ stroke: "caution", w: 2.2, head: "fill" }), bx({ stroke: "caution", w: 1.4, rx: 4, x: 9, y: 1, width: 14, height: 5 })], "Amber: differs from the happy path, on the branch chosen in Show");
  Legend.define("flow.stepno", [{ k: "dot", fill: "ink", r: 5.5 }, { k: "text", t: "2", fill: "room", y: 11, size: 8 }], "Numbered circle at the left: a step; the one playing is filled");
  const LOOK_ORDER = ["flow.stated", "flow.inferred", "flow.reply", "flow.self", "flow.band", "flow.future", "flow.chip", ...Legend.LAMPS.map((lv) => "lamp." + lv), "flow.pin", "flow.pin.settled", "flow.lane", "flow.lane.idle", "flow.stepno", "flow.differs"];
  function census(flow) {
    const seen = new Set(), canvas = document.createElement("canvas");
    canvas.width = 1040; canvas.height = 700;
    const ctx = canvas.getContext("2d"), G = layout(flow, { x: 0, y: 6, w: 1032, h: 694, s: 1 });
    for (let cur = 0; cur <= flow.steps.length; cur++) drawScene(ctx, G, { cur, tau: 99, clock: 0, D: 0.8, seen, images: false });
    return seen;
  }
  function expected(flow) {
    const out = new Set(), units = flow.steps.flatMap((step, si) => unitsOf(step).map((u) => ({ u, si })));
    const has = (f) => units.some(f);
    if (has(({ u }) => u.kind === "msg" && u.msg.direction === "stated")) out.add("flow.stated");
    if (has(({ u }) => u.kind === "msg" && u.msg.direction !== "stated")) out.add("flow.inferred");
    if (has(({ u }) => u.kind === "reply")) out.add("flow.reply");
    if (has(({ u }) => u.kind === "self")) out.add("flow.self");
    if (has(({ u }) => u.kind === "ref" || u.kind === "note")) out.add("flow.band");
    if (has(({ u, si }) => si >= 1 && (u.kind === "msg" || u.kind === "self"))) out.add("flow.future");
    for (const { u } of units) if (u.kind === "msg") { out.add("flow.chip"); const lv = levelOf(u.msg.contract); if (lv !== "dark") out.add("lamp." + lv); }
    for (const step of flow.steps) for (const pin of step.unknowns) {
      if (!ASK[pin.id]) continue;
      const lv = unknownLevel(pin.id);
      if (lv === "resolved" || lv === "dark") out.add("flow.pin.settled"); else { out.add("flow.pin"); out.add("lamp." + lv); }
    }
    out.add("flow.lane"); if (lanes.some((l) => !touchedLanes(flow).has(l.id))) out.add("flow.lane.idle");
    if (flow.steps.length) out.add("flow.stepno");
    if (flow.steps.some((step) => step.differs && unitsOf(step).some((u) => u.kind !== "ref"))) out.add("flow.differs");
    return out;
  }
  const flowProbes = (keyOf) => Object.fromEntries(LOOK_ORDER.map((id) => [id, () => expected(flowOf(keyOf())).has(id)]));
  return { census, expected, flowProbes, PALETTE, C, UI, SERIF, laneColor, laneName, flowOf, inferredNote, unitsOf, openPins, flowQuestions, touchedLanes, stepTiming, travelTime, layout, drawScene,
    drawClipFrame, clipPlan, clipFormat, recordClip, download, hexA, markerColor, CLIP };
})();
