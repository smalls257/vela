/* The flow kit: one canvas renderer for a played flow, and the clip recorder.

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
  const laneName = (id) => { const l = lanes[LANE_INDEX[id]]; return l ? l.full || l.name : titleOf(id); };
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
  const UNRECORDED = "Who sends to whom isn't recorded.";
  const INFERRED_NOTE = "The flow page doesn't say who sends each step, so the arrows are a guess. Say who sends in the step text.";
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
    return [{ kind: "note", unrecorded: !!step.unrecorded }];
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

  /* ---------- text: nothing in the canvas is cut. Words wrap, a row grows to hold them, and the canvas grows (scrolling) to hold the rows.
     A font shrinks with the window only down to FLOOR pixels; after that the text wraps instead of shrinking further. */
  const FLOOR = 11;
  const px = (base, k) => Math.max(FLOOR, base * k);
  const MEASURE = document.createElement("canvas").getContext("2d");
  const FONT = {
    say: (k) => `400 ${px(12.5, k)}px ${SERIF}`, chip: (k) => `600 ${px(11.5, k)}px ${UI}`, chipId: (k) => `400 ${px(10, k)}px ${UI}`,
    guess: (k) => `italic 400 ${px(10.5, k)}px ${SERIF}`, lane: (base, k) => `600 ${px(base, k)}px ${UI}`,
  };
  const leading = (k, base = 12.5) => Math.round(px(base, k) * 1.3);
  const SAY_PREFIX = /^[^:→]{1,80}(?:→|->)[^:]{1,80}:\s+/;
  const plainShort = (step) => step.short.replace(SAY_PREFIX, "").replace(/\s*…$/, "").replace(/\.$/, "");
  /* What a step says in the flow's own words, whole: the step's text without its sender-to-receiver prefix and without "over <contract>". */
  const stepSays = (step) => step.says || plainShort(step);
  /* The words under an arrow. A call says what the step does; the answer coming back says its own words when the flow page gives them
     ("... and gets a reading token"), and otherwise names the contract it travels over. */
  function sayOf(step, u) {
    const m = u.msg;
    if (u.kind === "reply" && m.kind !== "answer") return m.answer || (CONTRACT[m.contract] ? `replies over ${CONTRACT[m.contract].title}` : "replies");
    return m.says || stepSays(step);
  }
  /* The caption for present mode and clips: the step's short text, or its whole sentence when the short one was cut at a clause. */
  const captionOf = (step) => (/…$/.test(step.short) && step.says ? step.says.charAt(0).toUpperCase() + step.says.slice(1) + "." : step.short);

  function layout(flow, box) {
    let k = box.s ?? 1, G = layoutAt(flow, box, k);
    // A frame that cannot scroll (a clip, present mode) shrinks the scale until the rows fit, down to where the text hits its floor and the canvas grows instead.
    while (box.fit && G.needH > box.h && k > 0.5) { k *= 0.94; G = layoutAt(flow, box, k); }
    return G;
  }
  /* A lane the plan does not know (a gap) says so under its name: it is drawn, never dropped, and never passed off as an app. */
  function laneLabel(lane, width, on, k) {
    const base = laneLabelOf(lane, width, on, k);
    if (!lane.gap) return base;
    const lines = [...base.lines, NOT_IN_PLAN];
    return { ...base, lines, h: Math.max(base.h, lines.length * leading(k, 12) + 14 * k) };
  }
  const NOT_IN_PLAN = "not in the plan";
  function laneLabelOf(lane, width, on, k) {
    const name = lane.full || lane.name;
    const room = Math.max(40 * k, width - 40 * k);
    for (const base of [14, 12]) { MEASURE.font = FONT.lane(base, k); if (MEASURE.measureText(name).width <= room) return { font: FONT.lane(base, k), lines: [name], h: 32 * k, width }; }
    MEASURE.font = FONT.lane(12, k);
    // A narrow column still keeps whole words: the pill may be wider than its column rather than break a word.
    const lines = wrap(MEASURE, name, Math.max(room, ...name.split(/\s+/).map((t) => MEASURE.measureText(t).width)));
    return { font: FONT.lane(12, k), lines, h: Math.max(32 * k, lines.length * leading(k, 12) + 14 * k), width };
  }
  // The pill names the contract; its ID follows in small type only when there is room (names, not codes). A name wider than the arrow wraps inside the pill.
  function chipOf(con, room, k) {
    MEASURE.font = FONT.chipId(k); const idW = MEASURE.measureText(con.id).width;
    MEASURE.font = FONT.chip(k);
    const whole = MEASURE.measureText(con.title).width, inner = Math.max(50 * k, room - 16 * k);
    const withId = whole + idW + 6 * k <= inner, lines = whole <= inner ? [con.title] : wrap(MEASURE, con.title, inner);
    const textW = Math.max(...lines.map((t) => MEASURE.measureText(t).width));
    const lh = leading(k, 11.5);
    return { con, lines, withId, idW, lh, textW, w: textW + (withId ? idW + 6 * k : 0) + 16 * k, h: Math.max(19 * k, lines.length * lh + 7 * k) };
  }
  /* The height a row needs: `up` above its arrow (the pill) and `down` below it (the words). Rows are measured, then stacked, so a long
     sentence makes its own row taller instead of being cut to fit a row that was sized before anyone read it. */
  function measureRow(r, flow, G) {
    const { u } = r, k = G.s, step = flow.steps[r.si], lh = leading(k);
    if (u.kind === "msg" || u.kind === "reply") {
      const x1 = G.laneX[LANE_INDEX[u.from]], x2 = G.laneX[LANE_INDEX[u.to]];
      if (x1 === undefined || x2 === undefined) { r.up = r.down = 14 * k; r.lines = []; return; }
      const reach = Math.abs(x2 - x1);
      MEASURE.font = FONT.say(k);
      r.lines = wrap(MEASURE, sayOf(step, u), Math.max(70 * k, reach - 24 * k)); r.lh = lh;
      r.chip = u.kind === "msg" && !r.noChip && CONTRACT[u.msg.contract] ? chipOf(CONTRACT[u.msg.contract], Math.max(60 * k, reach - 34 * k), k) : null;
      r.guessed = u.kind === "msg" && u.msg.direction !== "stated";
      r.noContract = u.kind === "msg" && !u.msg.contract;  // a recorded pair that names no contract: a plain arrow, said so under its words
      r.up = (r.chip ? r.chip.h + 6 * k : 0) + 8 * k;
      r.down = 8 * k + r.lines.length * lh + (r.guessed || r.noContract ? leading(k, 10.5) + 2 * k : 0) + 5 * k;
    } else if (u.kind === "self") {
      const X = G.laneX[LANE_INDEX[u.lane]], lw = 34 * k;
      r.room = Math.max(80 * k, Math.min(G.colW * 1.8, G.x + G.w - (X + lw + 8 * k) - 8 * k));
      MEASURE.font = FONT.say(k); r.lines = wrap(MEASURE, stepSays(step), r.room - 12 * k); r.lh = lh;
      r.up = r.down = Math.max(14 * k, (r.lines.length * lh + 12 * k) / 2);
    } else {
      const xs = [...G.touched].map((id) => G.laneX[LANE_INDEX[id]]).filter((x) => x !== undefined);
      r.x0 = xs.length ? Math.min(...xs) - G.colW * 0.32 : G.x + G.gutter; r.x1 = xs.length ? Math.max(...xs) + G.colW * 0.32 : G.x + G.w - 10;
      const ref = u.ref && FLOW[u.ref];
      MEASURE.font = FONT.say(k); r.lines = wrap(MEASURE, ref ? `Repeats “${E[u.ref].title}”` : stepSays(step), Math.max(80 * k, r.x1 - r.x0 - 24 * k)); r.lh = lh;
      r.marker = !ref && u.unrecorded ? UNRECORDED : "";  // several lanes and no recorded pair: said on the band, never drawn as an arrow
      if (r.marker) { MEASURE.font = FONT.guess(k); r.markerLines = wrap(MEASURE, r.marker, Math.max(80 * k, r.x1 - r.x0 - 24 * k)); }
      r.bh = Math.max(26 * k, (r.lines.length + (r.markerLines ? r.markerLines.length : 0)) * lh + 12 * k); r.up = r.down = r.bh / 2 + 4 * k;
    }
  }
  function layoutAt(flow, box, k) {
    const { x, y, w, h: ht } = box;
    const gutter = 46 * k, bottomPad = 10 * k;
    const touched = touchedLanes(flow);
    // Only the lanes this flow's steps touch are drawn, in the map's order, and they share the whole width. Any other lane is not drawn at all.
    const weight = lanes.map((l) => (touched.has(l.id) ? 1 : 0));
    const unit = (w - gutter) / Math.max(1, weight.reduce((a, b) => a + b, 0));
    let acc = x + gutter;
    const laneX = weight.map((wt) => { const c = acc + (wt * unit) / 2; acc += wt * unit; return c; });
    const names = lanes.map((l, i) => laneLabel(l, weight[i] * unit, touched.has(l.id), k));
    const headerH = 12 * k + Math.max(32 * k, ...names.map((n) => n.h)), top = y + headerH + 18 * k;
    const rows = [];
    flow.steps.forEach((step, si) => unitsOf(step).forEach((u, ui) => rows.push({ si, ui, u })));
    // One pill per call and answer: an arrow that answers the arrow just above it, over the same contract between the
    // same two lanes, carries no second pill (two pills for one exchange overlapped where rows are close).
    rows.forEach((r, i) => {
      const before = rows[i - 1];
      if (r.u.kind !== "msg" || !before || !before.u.msg) return;
      const same = before.u.msg.contract === r.u.msg.contract && new Set([before.u.from, before.u.to, r.u.from, r.u.to]).size === 2;
      if (same) r.noChip = true;
    });
    const G = { x, y, w, s: k, gutter, headerH, colW: unit, laneX, rows, top, touched, flow, names };
    rows.forEach((r) => measureRow(r, flow, G));
    const stepGap = 12 * k, rowGap = 4 * k;
    const gapBefore = (r, i) => (i === 0 ? 0 : r.si !== rows[i - 1].si ? stepGap : rowGap);
    const natural = rows.reduce((sum, r, i) => sum + gapBefore(r, i) + r.up + r.down, 0);
    G.needH = top - y + natural + bottomPad + 6 * k;
    // Spare height is shared out between rows, up to a calm spacing; a taller flow than the stage keeps its natural height and the canvas scrolls.
    const spare = Math.max(0, Math.min(ht - G.needH, rows.length * 24 * k)), pad = rows.length ? spare / rows.length : 0;
    let cy = top;
    rows.forEach((r, i) => { cy += gapBefore(r, i); r.y = cy + pad / 2 + r.up; cy += r.up + r.down + pad; });
    G.h = Math.max(ht, G.needH + spare); G.bottom = y + G.h - bottomPad;
    return G;
  }

  const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  function rr(ctx, x, y, w, ht, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + ht, r); ctx.arcTo(x + w, y + ht, x, y + ht, r); ctx.arcTo(x, y + ht, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
  // Greedy wrap; a single word wider than the line is broken by letters, so no text is ever left out.
  function wrap(ctx, text, maxW) {
    const out = []; let line = "";
    for (let w of text.split(/\s+/).filter(Boolean)) {
      while (ctx.measureText(w).width > maxW && w.length > 1) {
        let n = w.length - 1;
        while (n > 1 && ctx.measureText(w.slice(0, n)).width > maxW) n--;
        if (line) { out.push(line); line = ""; }
        out.push(w.slice(0, n)); w = w.slice(n);
      }
      const t = line ? line + " " + w : w;
      if (ctx.measureText(t).width > maxW && line) { out.push(line); line = w; } else line = t;
    }
    if (line) out.push(line);
    return out;
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
    const absent = (lane) => !G.touched.has(lane.id);
    lanes.forEach((lane, i) => {
      if (absent(lane)) return;
      const X = G.laneX[i], y0 = G.y + G.headerH + 4 * k, y1 = G.bottom;
      let amp = 0, dt = 0;
      if (!still) for (const { u, t1, t0 } of curTiming) {
        const hitLane = u.kind === "self" ? u.lane : u.to, ta = u.kind === "self" ? t0 + Dt * 0.45 : t1;
        if (hitLane === lane.id && tau >= ta && tau < ta + 1.6) { dt = tau - ta; amp = 5.5 * k * Math.exp(-dt / 0.38); }
      }
      ctx.strokeStyle = hexA(laneColor(lane.id), 0.45); ctx.lineWidth = 1.6 * k;
      ctx.setLineDash(lane.gap ? [6 * k, 5 * k] : []);
      ctx.beginPath();
      for (let j = 0; j <= 40; j++) { const yy = y0 + ((y1 - y0) * j) / 40, off = amp * Math.sin((Math.PI * j) / 40) * Math.sin(2 * Math.PI * 7 * dt); j ? ctx.lineTo(X + off, yy) : ctx.moveTo(X + off, yy); }
      ctx.stroke(); ctx.setLineDash([]);
    });
    lanes.forEach((lane, i) => {
      if (absent(lane)) return;
      const X = G.laneX[i];
      if (st.seen) st.seen.add("flow.lane");
      const lab = G.names[i];
      ctx.save();
      // A name too long for one line wraps (layout measured it), so the pill grows taller before the name is ever cut.
      ctx.font = lab.font;
      const lines = lab.lines, lhL = leading(k, 12), tw = Math.max(...lines.map((t) => ctx.measureText(t).width));
      const bw = tw + 40 * k, bh = lab.h, bx = X - bw / 2, by = G.y + 6 * k;
      let glow = 0;
      for (const { u, t1, t0 } of curTiming) { const hitLane = u.kind === "self" ? u.lane : u.to, ta = u.kind === "self" ? t0 : t1; if (hitLane === lane.id && tau >= ta) glow = Math.max(glow, Math.exp(-(tau - ta) / 0.7)); }
      if (hl && hl.has(lane.id)) glow = Math.max(glow, 0.7);
      if (glow > 0.02 && (glowOn() || st.recording)) { ctx.shadowColor = hexA(laneColor(lane.id), 0.75 * glow); ctx.shadowBlur = 24 * k * glow; }
      rr(ctx, bx, by, bw, bh, bh / 2); ctx.fillStyle = C.deck2; ctx.fill(); ctx.shadowBlur = 0;
      ctx.strokeStyle = hexA(laneColor(lane.id), 0.45 + 0.5 * glow); ctx.lineWidth = (hl && hl.has(lane.id) ? 2 : 1) * k;
      ctx.setLineDash(lane.gap ? [5 * k, 4 * k] : []); ctx.stroke(); ctx.setLineDash([]);
      const dx = bx + 16 * k, dy = by + bh / 2, img = st.images !== false && emblemImg[lane.id];
      if (img && img.complete && img.naturalWidth) { ctx.save(); ctx.beginPath(); ctx.arc(dx, dy, 9 * k, 0, 7); ctx.clip(); ctx.drawImage(img, dx - 9 * k, dy - 9 * k, 18 * k, 18 * k); ctx.restore(); }
      // no emblem: the lane's own glyph, in the lane's color, so the color still says which lane it is
      else Icons.stroke(ctx, Icons.name(lane.id), dx, dy, 15 * k, laneColor(lane.id));
      ctx.fillStyle = C.ink; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      lines.forEach((t, j) => { say(ctx, st, t, dx + 12 * k, dy + (j - (lines.length - 1) / 2) * lhL + 0.5 * k); });
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
  // Every string the canvas draws goes through here, so a test can read back exactly what was drawn (st.drawn) and see that nothing was cut.
  function say(ctx, st, text, x, y) { if (st.drawn) st.drawn.push(text); ctx.fillText(text, x, y); }
  // Wrapped words, each line on a faint backing so a lane's vertical line passing behind never strikes through a letter.
  function drawLines(ctx, st, lines, cx, top, lh, align, ink) {
    ctx.textBaseline = "middle"; ctx.textAlign = align;
    lines.forEach((t, j) => {
      const tw = ctx.measureText(t).width, bx = align === "center" ? cx - tw / 2 : cx;
      ctx.fillStyle = hexA(C.room, 0.8); ctx.fillRect(bx - 3, top + j * lh, tw + 6, lh);
      ctx.fillStyle = ink; say(ctx, st, t, cx, top + j * lh + lh / 2);
    });
  }
  function drawUnit(ctx, G, r, step, phase, p, st, hits) {
    const k = G.s, u = r.u, y = r.y, ink = phase === "future" ? hexA(C.ink, 0.35) : phase === "now" ? C.ink : C.ink2;
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
      const mid = (x1 + x2) / 2;
      if (r.chip) {
        const { con, lines, withId, idW, lh } = r.chip, cw = r.chip.w, ch = r.chip.h, cx = mid - cw / 2, cy = y - ch - 6 * k;
        const lv = levelOf(con.id);
        if (st.seen) { st.seen.add("flow.chip"); if (lv !== "dark" && phase !== "future") st.seen.add("lamp." + lv); }
        ctx.globalAlpha = phase === "future" ? 0.4 : 1;
        rr(ctx, cx, cy, cw, ch, Math.min(ch / 2, 11 * k)); ctx.fillStyle = C.deck; ctx.fill();
        ctx.strokeStyle = step.differs ? amber(phase) : lv !== "dark" && phase !== "future" ? hexA(lampLine(lv), 0.8) : phase === "now" ? hexA(laneColor(u.from), 0.7) : C.rule;
        ctx.lineWidth = (step.differs ? 1.8 : 1) * k; ctx.stroke();
        ctx.textBaseline = "middle"; ctx.textAlign = "left";
        ctx.font = FONT.chip(k); ctx.fillStyle = lv !== "dark" ? lampText(lv) : C.ink;
        lines.forEach((t, j) => say(ctx, st, t, cx + 8 * k, cy + 3.5 * k + lh * (j + 0.5) + 0.5 * k));
        if (withId) { ctx.font = FONT.chipId(k); ctx.fillStyle = C.muted; say(ctx, st, con.id, cx + 8 * k + r.chip.textW + 6 * k, cy + 3.5 * k + lh * 0.5 + 0.5 * k); }
        ctx.globalAlpha = 1;
        hits.push({ type: "contract", id: con.id, si: r.si, x: cx, y: cy, w: cw, h: ch });
      }
      // What the arrow does, in the step's own words, under its line.
      ctx.globalAlpha = phase === "now" && p < 1 ? 0.35 + 0.65 * e : 1;
      ctx.font = FONT.say(k);
      drawLines(ctx, st, r.lines, mid, y + 9 * k, r.lh, "center", ink);
      if (r.guessed && phase === "now" && p >= 1 && st.labels !== false) {
        ctx.font = FONT.guess(k); ctx.fillStyle = C.heuristic; ctx.textAlign = "center"; ctx.textBaseline = "top";
        say(ctx, st, "direction guessed", mid, y + 9 * k + r.lines.length * r.lh + 2 * k);
      }
      if (r.noContract && phase !== "future" && st.labels !== false) {
        ctx.font = FONT.guess(k); ctx.fillStyle = C.muted; ctx.textAlign = "center"; ctx.textBaseline = "top";
        say(ctx, st, "no contract named", mid, y + 9 * k + r.lines.length * r.lh + 2 * k);
      }
      ctx.globalAlpha = 1;
      hits.push({ type: "row", si: r.si, line: y, x: Math.min(x1, x2), y: y - r.up, w: Math.abs(x2 - x1), h: r.up + r.down });
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
      ctx.font = FONT.say(k); ctx.textAlign = "left";
      const tw = Math.max(...r.lines.map((t) => ctx.measureText(t).width), 0), boxH = r.lines.length * r.lh + 10 * k;
      rr(ctx, X + lw + 2 * k, y - boxH / 2, tw + 12 * k, boxH, 6 * k); ctx.fillStyle = hexA(C.room, 0.9); ctx.fill();
      ctx.fillStyle = ink; ctx.textBaseline = "middle";
      r.lines.forEach((t, j) => say(ctx, st, t, X + lw + 8 * k, y - boxH / 2 + 5 * k + (j + 0.5) * r.lh));
      hits.push({ type: "row", si: r.si, x: X - 10 * k, y: y - r.up, w: lw + tw + 20 * k, h: r.up + r.down });
    } else {
      if (st.seen) st.seen.add("flow.band");
      const { x0, x1, bh } = r;
      ctx.globalAlpha = phase === "future" ? 0.4 : 1;
      rr(ctx, x0, y - bh / 2, x1 - x0, bh, 8 * k); ctx.fillStyle = phase === "now" ? hexA(C.deck2, 0.95) : hexA(C.deck, 0.7); ctx.fill();
      ctx.setLineDash([4 * k, 4 * k]); ctx.strokeStyle = step.differs ? amber(phase) : phase === "now" ? C.ink2 : C.rule; ctx.lineWidth = (step.differs ? 1.6 : 1) * k; ctx.stroke(); ctx.setLineDash([]);
      if (step.differs && st.seen) st.seen.add("flow.differs");
      const ref = u.ref && FLOW[u.ref];
      ctx.font = FONT.say(k); ctx.textBaseline = "middle"; ctx.textAlign = "center"; ctx.fillStyle = C.ink;
      const more = r.markerLines || [], top = y - (r.lines.length + more.length) * r.lh / 2;
      r.lines.forEach((t, j) => say(ctx, st, t, (x0 + x1) / 2, top + (j + 0.5) * r.lh));
      ctx.font = FONT.guess(k); ctx.fillStyle = C.heuristic;
      more.forEach((t, j) => say(ctx, st, t, (x0 + x1) / 2, top + (r.lines.length + j + 0.5) * r.lh));
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
    ctx.fillText(`${flow.state ? stateWord(flow.state) : "Nobody has given this flow a state yet"} · ${D.title}`, 96 * k, 250 * k);
    ctx.fillStyle = C.ink; ctx.font = `400 ${64 * k * Math.min(b, 1.3)}px ${SERIF}`;
    const lines = wrap(ctx, flow.title, 680 * k);
    lines.forEach((l, i) => ctx.fillText(l, 92 * k, 330 * k + i * 72 * k));
    let yy = 330 * k + lines.length * 72 * k + 8 * k, xx = 96 * k;
    ctx.font = `500 ${21 * k * b}px ${UI}`;
    touched.forEach((id) => {
      const name = laneName(id);
      if (xx > 96 * k && xx + ctx.measureText(name).width > W * 0.6) { xx = 96 * k; yy += 34 * k * b; }  // a name that would run off the card goes on the next line
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
      ctx.fillStyle = C.ink; ctx.font = `600 ${24 * k}px ${UI}`; ctx.fillText(E[id] ? E[id].title : id, 128 * k, y);  // a slide for an audience: the name, not the code
      ctx.font = `400 ${21 * k}px ${SERIF}`; ctx.fillStyle = C.ink2;
      const lines = wrap(ctx, q.question || "", 1000 * k).slice(0, 3);
      lines.forEach((l, i) => ctx.fillText(l, 128 * k, y + 36 * k + i * 29 * k));
      ctx.font = `500 ${18 * k}px ${UI}`; ctx.fillStyle = color;
      ctx.fillText(`Ask ${q.ask.name}${q.ask.inferred ? " (our guess at who)" : ""} by ${day(q.askBy)}`, 128 * k, y + 36 * k + lines.length * 29 * k + 8 * k);
      y += 36 * k + lines.length * 29 * k + 64 * k;
    });
    if (open.length > 3) { ctx.fillStyle = C.muted; ctx.font = `400 ${20 * k}px ${UI}`; ctx.fillText(`And ${open.length - 3} more in the plan.`, 128 * k, y); y += 44 * k; }
    if (settled.length) {
      ctx.fillStyle = C.muted; ctx.font = `400 ${19 * k}px ${UI}`;
      wrap(ctx, `Answered since the flow was written: ${settled.map((id) => (E[id] ? E[id].title : id)).join(", ")}.`, 1080 * k).forEach((l, i) => ctx.fillText(l, 96 * k, Math.max(y + 10 * k, 600 * k) + i * 28 * k));
    }
    ctx.globalAlpha = 1;
  }
  // The step's words under the diagram, at the largest size that fits two lines, then as many lines as it takes at the smallest.
  function captionLines(ctx, step, W, k) {
    let size = 29, lines;
    do { ctx.font = `400 ${size * k}px ${SERIF}`; lines = wrap(ctx, captionOf(step), W - 128 * k); size -= 2; } while (lines.length > 2 && size > 20);
    return { lines, size: size + 2 };
  }
  function drawCaption(ctx, flow, si, W, H, bandTop, cap, st = {}) {
    const k = W / 1280, step = flow.steps[si], { lines, size } = cap || captionLines(ctx, step, W, k);
    ctx.fillStyle = C.deck; ctx.fillRect(0, bandTop, W, H - bandTop);
    ctx.fillStyle = C.rule; ctx.fillRect(0, bandTop, W, 1 * k);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = C.muted; ctx.font = `500 ${17 * k}px ${UI}`;
    say(ctx, st, `Step ${step.n} of ${flow.steps.length} · ${flow.title}`, 64 * k, bandTop + 40 * k);
    ctx.font = `400 ${size * k}px ${SERIF}`; ctx.fillStyle = C.ink;
    lines.forEach((l, i) => say(ctx, st, l, 64 * k, bandTop + 80 * k + i * (size + 10) * k));
  }
  function drawClipFrame(ctx, flow, T, W = CLIP.W, H = CLIP.H, opts = {}) {
    const plan = clipPlan(flow), k = W / 1280;
    ctx.save();
    if (T < CLIP.title) { drawTitleCard(ctx, flow, T, W, H); ctx.restore(); return { phase: "title" }; }
    const tSteps = T - CLIP.title, j = Math.floor(tSteps / plan.stepDur);
    if (j >= flow.steps.length) { drawEndCard(ctx, flow, T - CLIP.title - plan.stepDur * flow.steps.length, W, H); ctx.restore(); return { phase: "end" }; }
    background(ctx, W, H);
    ctx.font = `400 ${29 * k}px ${SERIF}`;
    const cap = captionLines(ctx, flow.steps[j], W, k), band = H - Math.max(150 * k, (84 + cap.lines.length * (cap.size + 10)) * k);
    // A clip cannot scroll: the diagram shrinks to fit the words (to the text floor), never the words to fit the diagram.
    const G = layout(flow, { x: 40 * k, y: 26 * k, w: W - 80 * k, h: band - 40 * k, s: k * 1.05, fit: true });
    drawScene(ctx, G, { cur: j, tau: tSteps - j * plan.stepDur, clock: T, D: plan.D, images: opts.images, recording: true, drawn: opts.drawn });
    drawCaption(ctx, flow, j, W, H, band, cap, opts);
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
     timestamp, so a slow frame drops a frame rather than shifting the content. Failure raises; it never returns an empty file. */
  async function recordClip(flow, { onProgress } = {}) {
    const fmt = clipFormat();
    if (!fmt) throw new Error("This browser can't record video. Try Chrome.");
    const canvas = document.createElement("canvas");
    canvas.width = CLIP.W; canvas.height = CLIP.H;
    canvas.style.cssText = "position:fixed;left:-9999px;top:0;width:640px;height:360px";
    document.body.appendChild(canvas);
    const ctx = canvas.getContext("2d"), plan = clipPlan(flow);
    drawClipFrame(ctx, flow, 0, CLIP.W, CLIP.H, { images: false });
    const stream = canvas.captureStream(30);
    const rec = new MediaRecorder(stream, { mimeType: fmt.mime, videoBitsPerSecond: 4_000_000 }), chunks = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const done = new Promise((res, rej) => { rec.onstop = res; rec.onerror = (e) => rej(e.error || new Error("recording failed")); });
    rec.start(250);
    const t0 = performance.now();
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
    stream.getTracks().forEach((t) => t.stop());
    canvas.remove();
    if (!chunks.length) throw new Error("The recording came out empty; try again.");
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
  Legend.define("flow.future", [ln({ stroke: "ink-4", w: 1.8, dash: "2 4.5" })], "Dotted line: a step that hasn't played yet");
  Legend.define("flow.chip", [bx({ fill: "deck", stroke: "ink-3", w: 1.2, rx: 4, y: 4, height: 8 })], "Pill on an arrow: the contract used, outlined in its status color");
  Legend.define("flow.pin", [{ k: "dot", fill: "caution", r: 4.5 }], "Glowing dot at a step: an open question about this step, in its status color");
  Legend.define("flow.pin.settled", [{ k: "dot", fill: "room", stroke: "ink-3", w: 1.3, r: 5 }, { k: "text", t: "✓", fill: "ink-3", y: 11, size: 8 }], "Ring with a check mark: a question about this step that's been answered");
  Legend.define("flow.lane", [bx({ fill: "deck-2", stroke: "ink-3", w: 1.2, rx: 4.5, y: 3.5, height: 9 }), { k: "dot", fill: "ink-2", x: 9, r: 2 }], "Pill at the top: one app or outside service, in its own color");
  Legend.define("flow.differs", [ln({ stroke: "caution", w: 2.2, head: "fill" }), bx({ stroke: "caution", w: 1.4, rx: 4, x: 9, y: 1, width: 14, height: 5 })], "Amber: differs from the happy path, on the branch chosen in Show");
  Legend.define("flow.stepno", [{ k: "dot", fill: "ink", r: 5.5 }, { k: "text", t: "2", fill: "room", y: 11, size: 8 }], "Numbered circle at the left: a step; the one playing is filled");
  const LOOK_ORDER = ["flow.stated", "flow.inferred", "flow.reply", "flow.self", "flow.band", "flow.future", "flow.chip", ...Legend.LAMPS.map((lv) => "lamp." + lv), "flow.pin", "flow.pin.settled", "flow.lane", "flow.stepno", "flow.differs"];
  function census(flow) {
    const seen = new Set(), canvas = document.createElement("canvas");
    canvas.width = 1040; canvas.height = 700;
    const ctx = canvas.getContext("2d"), G = layout(flow, { x: 0, y: 6, w: 1032, h: 694, s: 1 });
    for (let cur = 0; cur <= flow.steps.length; cur++) drawScene(ctx, G, { cur, tau: 99, clock: 0, D: 0.8, seen, images: false });
    return seen;
  }
  /* Test hook: every string the stage draws for a flow in a window `W` wide, step by step, as {text, layout}. The self-test reads it back to check
     that every arrow's words are on the canvas whole and that none was cut with an ellipsis. */
  function drawnText(flow, W, H = 700) {
    const canvas = document.createElement("canvas"), drawn = [];
    canvas.width = W; canvas.height = Math.max(H, 4000);
    const ctx = canvas.getContext("2d"), G = layout(flow, { x: 0, y: 6, w: W - 8, h: H - 6, s: clamp(W / 1040, 0.8, 1.2) });
    for (let cur = 0; cur <= flow.steps.length; cur++) drawScene(ctx, G, { cur, tau: 99, clock: 0, D: 0.8, images: false, drawn });
    return { drawn, G };
  }
  function drawnClip(flow) {
    const canvas = document.createElement("canvas"), drawn = [], plan = clipPlan(flow);
    canvas.width = CLIP.W; canvas.height = CLIP.H;
    const ctx = canvas.getContext("2d");
    flow.steps.forEach((_, j) => drawClipFrame(ctx, flow, CLIP.title + plan.stepDur * (j + 0.9), CLIP.W, CLIP.H, { images: false, drawn }));
    return drawn;
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
    for (const { u } of units) if (u.kind === "msg" && CONTRACT[u.msg.contract]) { out.add("flow.chip"); const lv = levelOf(u.msg.contract); if (lv !== "dark") out.add("lamp." + lv); }
    for (const step of flow.steps) for (const pin of step.unknowns) {
      if (!ASK[pin.id]) continue;
      const lv = unknownLevel(pin.id);
      if (lv === "resolved" || lv === "dark") out.add("flow.pin.settled"); else { out.add("flow.pin"); out.add("lamp." + lv); }
    }
    out.add("flow.lane");
    if (flow.steps.length) out.add("flow.stepno");
    if (flow.steps.some((step) => step.differs && unitsOf(step).some((u) => u.kind !== "ref"))) out.add("flow.differs");
    return out;
  }
  const flowProbes = (keyOf) => Object.fromEntries(LOOK_ORDER.map((id) => [id, () => expected(flowOf(keyOf())).has(id)]));
  return { census, drawnText, drawnClip, sayOf, stepSays, captionOf, expected, flowProbes, PALETTE, C, UI, SERIF, laneColor, laneName, flowOf, inferredNote, unitsOf, openPins, flowQuestions, touchedLanes, stepTiming, travelTime, layout, drawScene,
    drawClipFrame, clipPlan, clipFormat, recordClip, download, hexA, markerColor, CLIP };
})();
