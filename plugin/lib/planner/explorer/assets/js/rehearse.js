/* Rehearse this flow: rebuild it from memory, then reveal the real one over yours. Getting it wrong first and then
   seeing the real flow fixes it better than reading it twice (the testing effect). Drag the apps into lanes, plug a
   contract from the lane that sends to the lane that receives, step by step, then reveal. Scoring aligns the attempt
   with the record and keeps both orders; a direction the record only infers counts either way. Ported from
   prototypes/gallery/flows/rehearse.html. Tries are kept in this browser's storage, nowhere else. */
const Rehearse = (() => {
  const ROW_H = 60, ROW_TOP = 46;
  const lanes = D.lanes, laneOf = (id) => lanes[LANE_INDEX[id]];
  const st = { key: null, slots: [], steps: [], carry: null, pointer: { x: 0, y: 0 }, revealed: null };
  const wire = { sag: 40, v: 0, lastX: 0 };
  const plucks = {};
  let root = null, drag = null, raf = 0;
  const flow = () => FlowKit.flowOf(st.key);
  const storeKey = (id) => `rehearse:${D.vaultId}:${id}`;
  const tries = (id) => Settings.readJson(storeKey(id), [], "your rehearsal tries");
  const q = (sel) => root.querySelector(sel);

  /* The contracts on the tray: the flow's own, and the others that join its apps, so the tray does not give the answer away. */
  function cables() {
    const f = flow(), touched = FlowKit.touchedLanes(f), own = new Set(f.steps.flatMap((x) => x.messages.map((m) => m.contract)));
    const near = D.map.contracts.filter((c) => own.has(c.id) || touched.has(c.provider) || c.consumers.some((k) => touched.has(k)));
    return near.sort((a, b) => cmp(a.id, b.id)).slice(0, Math.max(14, own.size));
  }
  function open(key) {
    if (!FLOW[key]) return;
    st.key = key;
    root = $("#overlay"); root.hidden = false; root.className = "rehearse"; root.innerHTML = "";
    const e = E[key];
    root.append(
      h("header", { class: "rh-bar" }, h("div", {}, h("div", { class: "pt-kicker" }, `${e.id}, from memory`), h("h1", {}, `Rehearse: ${e.title}`)),
        h("span", { class: "spacer" }),
        h("button", { class: "btn", onclick: () => { close(); Flows.select(key, -1); } }, "Watch it played"),
        h("button", { class: "btn", onclick: close }, "Close (Esc)")),
      h("main", { class: "rh-main" }, h("div", { class: "rh-board", id: "rh-board" }, h("div", { class: "rh-rail", id: "rh-rail" }), s("svg", { class: "rh-overlay", id: "rh-svg" }), h("div", { class: "rh-rows", id: "rh-rows" })),
        h("aside", { class: "rh-side", id: "rh-side" })),
      h("footer", { class: "rh-tray" }, h("h3", {}, "Apps and partners"), h("div", { class: "shelf", id: "rh-tiles" }), h("h3", {}, "Contracts"), h("div", { class: "shelf", id: "rh-cables" })));
    reset(false);
    new ResizeObserver(() => root && root.classList.contains("rehearse") && renderBoard()).observe(q("#rh-board"));
    cancelAnimationFrame(raf); raf = requestAnimationFrame(swing);
  }
  Assets.onReady(() => { if (root && root.classList.contains("rehearse")) renderAll(); });
  function close() { if (!root || !root.classList.contains("rehearse")) return; root.hidden = true; root.className = ""; root.innerHTML = ""; cancelAnimationFrame(raf); root = null; }
  function reset(keepLanes) {
    st.steps = []; st.carry = null; st.revealed = null;
    if (!keepLanes) st.slots = lanes.map(() => null);
    renderAll();
  }
  function emblem(lane) {
    const url = Assets.emblem(lane.name), color = FlowKit.laneColor(lane.id);
    if (url) return `<span class="em" style="background:${color}"><img alt="" src="${url}"></span>`;
    return `<span class="em ${lane.kind}" style="background:${color};border-color:${color};color:${lane.kind === "partner" ? color : Theme.c("room")}">${esc(lane.name[0])}</span>`;
  }
  const tileHtml = (lane, extra = "") => `<div class="tile ${extra}" data-lane="${esc(lane.id)}" tabindex="0" title="${esc(lane.name)}">${emblem(lane)}<span>${esc(lane.name)}<small>${lane.kind === "app" ? "app" : "outside party"}</small></span></div>`;
  function railGeom() {
    const rail = q("#rh-rail"), board = q("#rh-board"), rb = board.getBoundingClientRect();
    const slots = [...rail.children].map((el) => { const r = el.getBoundingClientRect(); return { x: r.left - rb.left + board.scrollLeft + r.width / 2, w: r.width, top: r.top - rb.top + board.scrollTop, bottom: r.bottom - rb.top + board.scrollTop }; });
    return { slots, railBottom: slots.length ? slots[0].bottom : 60, width: board.scrollWidth };
  }
  const laneX = (id, g) => { const i = st.slots.indexOf(id); return i === -1 ? null : g.slots[i].x; };
  function laneAt(cx, cy) {
    const board = q("#rh-board"), rb = board.getBoundingClientRect();
    if (cx < rb.left || cx > rb.right || cy < rb.top || cy > rb.bottom) return null;
    const g = railGeom(), x = cx - rb.left + board.scrollLeft;
    let best = null, bd = Infinity;
    g.slots.forEach((sl, i) => { const d = Math.abs(sl.x - x); if (st.slots[i] && d < bd && d < sl.w * 0.55) { bd = d; best = st.slots[i]; } });
    return best;
  }
  function renderAll() { if (!root) return; renderRail(); renderTray(); renderBoard(); renderSide(); }
  function renderRail() {
    const rail = q("#rh-rail"), real = FlowKit.touchedLanes(flow());
    rail.style.gridTemplateColumns = `repeat(${lanes.length}, minmax(0, 1fr))`;
    rail.innerHTML = st.slots.map((id, i) => {
      if (!id) {
        const missed = st.revealed && st.revealed.ghostLanes[i];
        if (missed) return `<div class="slot missed" data-slot="${i}">${tileHtml(laneOf(missed), "missed-tile")}</div>`;
        return `<div class="slot" data-slot="${i}">${i === 0 && !st.slots.some(Boolean) ? "Drop an app here" : ""}</div>`;
      }
      return `<div class="slot filled" data-slot="${i}">${tileHtml(laneOf(id), st.revealed && !real.has(id) ? "extra" : "")}</div>`;
    }).join("");
  }
  function renderTray() {
    q("#rh-tiles").innerHTML = lanes.map((l) => tileHtml(l, st.slots.includes(l.id) ? "used" : "")).join("");
    q("#rh-cables").innerHTML = cables().map((c) => `<div class="cable" data-contract="${esc(c.id)}" tabindex="0" title="${esc(c.title)}">
        <svg viewBox="0 0 26 18"><rect x="1" y="5" width="7" height="8" rx="2" fill="currentColor"/><path d="M8 9c5 0 5 6 10 6" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round"/><rect x="18" y="11" width="7" height="7" rx="2" fill="currentColor"/></svg>
        <b>${esc(c.id)}</b><i>${esc(c.title)}</i></div>`).join("") + `<div class="cable" data-self="1" tabindex="0" title="A step that stays inside one app">
        <svg viewBox="0 0 26 18"><path d="M6 4c14 0 14 10 0 10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round"/><path d="M9 11l-4 3 4 3" stroke="currentColor" stroke-width="2" fill="none"/></svg><b class="self">Inside one app</b></div>`;
  }
  const el = (tag, attrs, parent) => s(tag, attrs, parent);
  function stringPath(x, y0, y1, amp) {
    if (!amp) return `M${x},${y0} L${x},${y1}`;
    const pts = [];
    for (let j = 0; j <= 30; j++) { const y = y0 + ((y1 - y0) * j) / 30; pts.push(`${j ? "L" : "M"}${x + amp * Math.sin((Math.PI * j) / 30)},${y}`); }
    return pts.join(" ");
  }
  const rowY = (i, g) => g.railBottom + ROW_TOP + i * ROW_H;
  function renderBoard() {
    if (!root) return;
    const svg = q("#rh-svg"), g = railGeom(), hit = q("#rh-rows");
    const rows = st.revealed ? st.revealed.pairs.length : st.steps.length;
    const height = Math.max(q("#rh-board").clientHeight - 30, g.railBottom + ROW_TOP + (rows + (st.carry ? 1 : 0)) * ROW_H + 40);
    svg.setAttribute("width", g.width); svg.setAttribute("height", height); svg.style.width = g.width + "px"; svg.style.height = height + "px";
    svg.innerHTML = ""; hit.innerHTML = ""; hit.style.height = height + "px";
    const strings = el("g", {}, svg);
    st.slots.forEach((id, i) => {
      const lane = id || (st.revealed && st.revealed.ghostLanes[i]);
      if (!lane) return;
      const sl = g.slots[i];
      const p = el("path", { class: "string", d: stringPath(sl.x, sl.bottom + 2, height - 10, 0), stroke: FlowKit.laneColor(lane), "stroke-opacity": id ? 0.55 : 0.3, "stroke-dasharray": id ? "" : "4 5", "data-lane": lane }, strings);
      p.dataset.x = sl.x; p.dataset.y0 = sl.bottom + 2; p.dataset.y1 = height - 10;
    });
    if (!st.revealed && !st.steps.length && !st.carry) {
      hit.append(h("div", { class: "empty-hint", style: `top:${g.railBottom + 26}px`, html: st.slots.some(Boolean)
        ? "<b>Now the steps, in order.</b><br>Drag a contract from the tray onto the lane that sends, then click the lane that receives. A step that stays inside one app uses the loop."
        : "<b>First, the apps.</b><br>Drag each app or partner this flow touches into a lane, left to right. Leave out the ones it does not touch." }));
    }
    if (st.revealed) { renderReveal(svg, g); return; }
    st.steps.forEach((step, i) => drawAttemptRow(svg, g, step, rowY(i, g), i));
    st.steps.forEach((step, i) => {
      hit.append(h("div", { class: "row-hover", style: `top:${rowY(i, g) - 25}px`, html: `<div class="row-tools">
        <button data-act="up" data-i="${i}" aria-label="Move step ${i + 1} up" ${i === 0 ? "disabled" : ""}>↑</button>
        <button data-act="down" data-i="${i}" aria-label="Move step ${i + 1} down" ${i === st.steps.length - 1 ? "disabled" : ""}>↓</button>
        <button data-act="del" data-i="${i}" aria-label="Remove step ${i + 1}">×</button></div>` }));
    });
    if (st.carry) drawCarry(svg, g);
  }
  function numberBadge(svg, n, y) { const gN = el("g", { class: "num" }, svg); el("circle", { cx: 32, cy: y, r: 11 }, gN); el("text", { x: 32, y: y + 0.5 }, gN).textContent = n; }
  function chipLabel(svg, x, y, con, opts = {}) {
    const gC = el("g", { class: "chiplabel" + (opts.cls ? " " + opts.cls : "") }, svg);
    const t = el("text", { x: 0, y: 0 }, gC);
    t.innerHTML = `${esc(con.id)}<tspan class="n" dx="6">${esc(shorten(con.title, 28))}</tspan>`;
    const w = t.getBBox().width + 18, ht = 19;
    gC.insertBefore(el("rect", { x: x - w / 2, y: y - ht - 6, width: w, height: ht, rx: ht / 2 }), t);
    t.setAttribute("x", x - w / 2 + 8); t.setAttribute("y", y - 6 - ht / 2 + 4);
    return gC;
  }
  function arrowShape(svg, x1, x2, y, color, { head = "filled", dash = "", cls = "arrow" } = {}) {
    const dir = Math.sign(x2 - x1) || 1, a = x1 + dir * 5, b = x2 - dir * 6, gA = el("g", {}, svg);
    el("path", { class: cls, d: `M${a},${y} L${b},${y}`, stroke: color, "stroke-dasharray": dash }, gA);
    const hx = b + dir * 2, d = `M${hx - dir * 9},${y - 5.6} L${hx},${y} L${hx - dir * 9},${y + 5.6}`;
    if (head === "filled") el("path", { d: d + " Z", fill: color }, gA); else el("path", { d, fill: "none", stroke: color, "stroke-width": 1.8 }, gA);
    return gA;
  }
  function loopShape(svg, x, y, color, dash = "") {
    const gL = el("g", {}, svg);
    el("path", { d: `M${x + 4},${y - 11} C${x + 36},${y - 17} ${x + 36},${y + 17} ${x + 6},${y + 11}`, fill: "none", stroke: color, "stroke-width": 2.2, "stroke-dasharray": dash }, gL);
    el("path", { d: `M${x + 12},${y + 6} L${x + 5},${y + 11} L${x + 12},${y + 16}`, fill: "none", stroke: color, "stroke-width": 2 }, gL);
    return gL;
  }
  function drawAttemptRow(svg, g, step, y, i) {
    numberBadge(svg, i + 1, y);
    if (step.self) { const x = laneX(step.self, g); if (x !== null) loopShape(svg, x, y, FlowKit.laneColor(step.self)); return; }
    const x1 = laneX(step.from, g), x2 = laneX(step.to, g);
    if (x1 === null || x2 === null) return;
    arrowShape(svg, x1, x2, y, FlowKit.laneColor(step.from));
    chipLabel(svg, (x1 + x2) / 2, y, CONTRACT[step.contract]);
  }
  function drawCarry(svg, g) {
    const board = q("#rh-board"), rb = board.getBoundingClientRect();
    const px = st.pointer.x - rb.left + board.scrollLeft, py = st.pointer.y - rb.top + board.scrollTop, y = rowY(st.steps.length, g);
    if (!st.carry.from) return;
    const x1 = laneX(st.carry.from, g), mx = (x1 + px) / 2, my = (y + py) / 2 + wire.sag, d = `M${x1},${y} Q${mx},${my} ${px},${py}`;
    el("path", { class: "wire-outer", d }, svg); el("path", { class: "wire-inner", d }, svg);
    el("rect", { class: "plug", x: x1 - 7, y: y - 7, width: 14, height: 14, rx: 3 }, svg);
    el("rect", { class: "plug", x: px - 6, y: py - 6, width: 12, height: 12, rx: 3 }, svg);
    numberBadge(svg, st.steps.length + 1, y);
    const target = laneAt(st.pointer.x, st.pointer.y);
    if (target && target !== st.carry.from) el("circle", { cx: laneX(target, g), cy: y, r: 9, fill: "none", stroke: FlowKit.laneColor(target), "stroke-width": 2 }, svg);
  }
  function swing() {
    if (!root || !root.classList.contains("rehearse")) return;
    if (st.carry && st.carry.from) {
      const dx = st.pointer.x - wire.lastX; wire.lastX = st.pointer.x;
      wire.v += (40 - wire.sag) * 0.12 - Math.abs(dx) * 0.25; wire.v *= 0.82; wire.sag = clamp(wire.sag + wire.v, -10, 90);
      renderBoard();
    }
    const now = performance.now();
    root.querySelectorAll(".string").forEach((p) => {
      const t0 = plucks[p.dataset.lane]; if (!t0) return;
      const dt = (now - t0) / 1000, amp = reducedMotion() || dt > 1.4 ? 0 : 7 * Math.exp(-dt / 0.33) * Math.sin(2 * Math.PI * 7 * dt);
      p.setAttribute("d", stringPath(+p.dataset.x, +p.dataset.y0, +p.dataset.y1, amp));
    });
    raf = requestAnimationFrame(swing);
  }
  const pluck = (id) => { plucks[id] = performance.now(); };

  function renderSide() {
    const f = flow(), side = q("#rh-side");
    if (st.revealed) { side.innerHTML = resultHtml(); bindResult(); return; }
    const lanesDone = st.slots.some(Boolean), stepsDone = st.steps.length > 0, hist = tries(f.id);
    side.innerHTML = `<p class="lede">Rebuild it before you look. Getting it wrong first and then seeing the real flow fixes it better than reading it twice.</p>
      <ol class="how"><li class="${lanesDone ? "done" : ""}">Put the apps and partners this flow touches into lanes.</li>
        <li class="${stepsDone ? "done" : ""}">Plug contracts between lanes, one step at a time, in order.</li><li>Reveal the real flow over yours.</li></ol>
      <button class="reveal" id="rh-reveal" ${stepsDone ? "" : "disabled"}>Reveal the real flow<span>${plural(st.steps.length, "step")} so far</span></button>
      <div class="row-actions"><button class="btn" id="rh-undo" ${stepsDone ? "" : "disabled"}>Undo last step</button><button class="btn" id="rh-clear">Start over</button></div>
      ${hist.length ? `<div class="hist-row"><div class="history">${hist.slice(-8).map((x) => `<i style="height:${Math.max(4, (x.got / Math.max(1, x.of)) * 34)}px" title="${x.got} of ${x.of}"></i>`).join("")}</div><span>Your tries on this flow. Last: ${hist[hist.length - 1].got} of ${hist[hist.length - 1].of}.</span></div>` : ""}
      <details class="kbd"><summary>Add a step with the keyboard</summary><form id="rh-form">
        <select name="from" aria-label="From">${st.slots.filter(Boolean).map((id) => `<option value="${esc(id)}">${esc(laneOf(id).name)}</option>`).join("")}</select>
        <select name="what" aria-label="Over">${cables().map((c) => `<option value="${esc(c.id)}">over ${esc(c.id)} ${esc(c.title)}</option>`).join("")}<option value="self">inside the app</option></select>
        <select name="to" aria-label="To">${st.slots.filter(Boolean).map((id) => `<option value="${esc(id)}">to ${esc(laneOf(id).name)}</option>`).join("")}</select>
        <button class="btn">Add the step</button></form></details>`;
    q("#rh-reveal").onclick = reveal;
    q("#rh-undo").onclick = () => { st.steps.pop(); renderAll(); };
    q("#rh-clear").onclick = () => reset(false);
    q("#rh-form").onsubmit = (e) => {
      e.preventDefault();
      const fd = new FormData(e.target), from = fd.get("from"), to = fd.get("to"), what = fd.get("what");
      if (!from) return toast("Put an app into a lane first.");
      if (what === "self") addStep({ self: from });
      else if (from === to) toast("A contract joins two different lanes. Pick another receiver, or use inside the app.");
      else addStep({ from, to, contract: what });
    };
  }

  /* ---------- drag and drop ---------- */
  const inside = (elm, e) => { const r = elm.getBoundingClientRect(); return e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom; };
  const moveGhost = (e) => { drag.ghost.style.left = e.clientX - drag.dx + "px"; drag.ghost.style.top = e.clientY - drag.dy + "px"; };
  document.addEventListener("pointerdown", (e) => {
    if (!root || !root.classList.contains("rehearse") || st.revealed) return;
    const tile = e.target.closest(".rehearse .tile"), cable = e.target.closest(".rehearse .cable");
    if (tile && !tile.classList.contains("used")) {
      e.preventDefault();
      const r = tile.getBoundingClientRect(), ghost = tile.cloneNode(true);
      ghost.classList.add("ghost"); ghost.style.width = r.width + "px"; root.appendChild(ghost);
      const fromSlot = tile.closest(".slot") ? +tile.closest(".slot").dataset.slot : null;
      drag = { kind: "tile", lane: tile.dataset.lane, ghost, dx: e.clientX - r.left, dy: e.clientY - r.top, fromSlot };
      if (fromSlot !== null) tile.style.opacity = 0.2;
      moveGhost(e);
    } else if (cable) {
      e.preventDefault();
      if (!st.slots.some(Boolean)) { cable.classList.add("shake"); setTimeout(() => cable.classList.remove("shake"), 400); return toast("Put the apps into lanes first, then plug contracts between them."); }
      st.carry = cable.dataset.self ? { self: true } : { contract: cable.dataset.contract };
      root.querySelectorAll(".cable").forEach((c) => c.classList.toggle("carrying", c === cable));
      const ghost = h("div", { class: "tile ghost cable-ghost", html: cable.dataset.self ? "Inside one app" : `<b>${esc(cable.dataset.contract)}</b>` });
      root.appendChild(ghost);
      drag = { kind: "cable", ghost, dx: 20, dy: 19 };
      moveGhost(e);
    } else if (st.carry && st.carry.from && e.target.closest("#rh-board")) plugReceiver(e);
  });
  document.addEventListener("pointermove", (e) => {
    if (!root || !root.classList.contains("rehearse")) return;
    st.pointer = { x: e.clientX, y: e.clientY };
    if (drag) { moveGhost(e); if (drag.kind === "tile") root.querySelectorAll(".slot").forEach((sl) => sl.classList.toggle("hot", inside(sl, e))); }
  });
  document.addEventListener("pointerup", (e) => {
    if (!drag) return;
    const d = drag; drag = null; d.ghost.remove();
    if (!root) return;
    root.querySelectorAll(".slot").forEach((sl) => sl.classList.remove("hot"));
    if (d.kind === "tile") dropTile(d, e); else dropCable(e);
  });
  function dropTile(d, e) {
    const slot = [...root.querySelectorAll(".slot")].find((sl) => inside(sl, e));
    if (slot) {
      const i = +slot.dataset.slot, prev = st.slots[i];
      if (d.fromSlot !== null) st.slots[d.fromSlot] = prev && prev !== d.lane ? prev : null;
      st.slots[i] = d.lane;
      renderAll();
      const placed = q("#rh-rail").children[i].querySelector(".tile");
      if (placed) placed.classList.add("snap");
      requestAnimationFrame(() => pluck(d.lane));
      Sound.click(d.lane);
      if (d.fromSlot === null) Assets.theme(laneOf(d.lane).name);
    } else if (d.fromSlot !== null && e.target.closest(".rh-tray, .rh-side")) {
      const lane = st.slots[d.fromSlot], before = st.steps.length;
      st.slots[d.fromSlot] = null;
      st.steps = st.steps.filter((x) => x.self !== lane && x.from !== lane && x.to !== lane);
      if (st.steps.length < before) toast(`Removed ${plural(before - st.steps.length, "step")} that used ${laneOf(lane).name}.`);
      renderAll();
    } else renderAll();
  }
  function dropCable(e) {
    const lane = laneAt(e.clientX, e.clientY);
    if (!lane) {
      if (e.target.closest(".cable")) { toast(st.carry.self ? "Click the app the step happens in." : "Click the lane that sends."); st.carry.awaitFrom = true; renderBoard(); return; }
      cancelCarry(); return;
    }
    plugSender(lane);
  }
  function plugSender(lane) {
    if (st.carry.self) { addStep({ self: lane }); return; }
    st.carry.from = lane; wire.sag = 70; wire.v = 0; wire.lastX = st.pointer.x;
    pluck(lane); Sound.click(lane); renderBoard();
  }
  function plugReceiver(e) {
    const lane = laneAt(e.clientX, e.clientY);
    if (!lane) return;
    if (lane === st.carry.from) { toast("A contract joins two different lanes. Click the lane that receives."); return; }
    addStep({ from: st.carry.from, to: lane, contract: st.carry.contract });
  }
  document.addEventListener("click", (e) => {
    if (!root || !root.classList.contains("rehearse")) return;
    if (st.carry && st.carry.awaitFrom && !st.carry.from && e.target.closest("#rh-board")) { const lane = laneAt(e.clientX, e.clientY); if (lane) plugSender(lane); }
    const act = e.target.closest(".rehearse [data-act]");
    if (act) {
      const i = +act.dataset.i;
      if (act.dataset.act === "del") st.steps.splice(i, 1);
      if (act.dataset.act === "up" && i > 0) [st.steps[i - 1], st.steps[i]] = [st.steps[i], st.steps[i - 1]];
      if (act.dataset.act === "down" && i < st.steps.length - 1) [st.steps[i + 1], st.steps[i]] = [st.steps[i], st.steps[i + 1]];
      renderAll();
    }
  });
  function addStep(step) {
    st.steps.push(step); st.carry = null;
    root.querySelectorAll(".cable").forEach((c) => c.classList.remove("carrying"));
    const target = step.self || step.to;
    pluck(target); Sound.click(target); renderAll();
  }
  function cancelCarry() { st.carry = null; root.querySelectorAll(".cable").forEach((c) => c.classList.remove("carrying")); renderBoard(); }
  addEventListener("keydown", (e) => {
    if (!root || !root.classList.contains("rehearse")) return;
    if (e.key === "Escape") { if (st.carry) cancelCarry(); else close(); }
  });

  /* ---------- reveal: align the attempt with the real flow ---------- */
  function realUnits(f) {
    const out = [];
    f.steps.forEach((x) => {
      if (x.messages.length) x.messages.forEach((m) => out.push({ kind: "msg", from: m.from, to: m.to, contract: m.contract, direction: m.direction, n: x.n, short: x.short }));
      else if (x.self) out.push({ kind: "self", lane: x.self, n: x.n, short: x.short });
      else out.push({ kind: "context", n: x.n, short: x.short, ref: x.ref });
    });
    return out;
  }
  function judge(a, r) {
    if (r.kind === "context") return [0, null];
    if (a.self || r.kind === "self") {
      if (a.self && r.kind === "self") return a.self === r.lane ? [3, "right"] : [1, "near", `It happens inside ${laneOf(r.lane).name}.`];
      return [0, null];
    }
    if (a.contract === r.contract) {
      if (a.from === r.from && a.to === r.to) return [3, "right"];
      if (a.from === r.to && a.to === r.from) return r.direction === "inferred" ? [3, "right", "The vault does not say which way this goes, so either way counts."] : [2, "near", `Reversed: ${laneOf(r.from).name} sends to ${laneOf(r.to).name}.`];
      return [1, "near", `Right contract, between ${laneOf(r.from).name} and ${laneOf(r.to).name}.`];
    }
    const same = (a.from === r.from && a.to === r.to) || (a.from === r.to && a.to === r.from);
    return same ? [1, "near", `Right lanes, but over ${r.contract} ${CONTRACT[r.contract].title}.`] : [0, null];
  }
  /* Global alignment that keeps both orders: steps recalled in the wrong order lose credit for the order. */
  function align(att, real) {
    const n = att.length, m = real.length, S = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
    for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) { const [sc] = judge(att[i - 1], real[j - 1]); S[i][j] = Math.max(S[i - 1][j], S[i][j - 1], sc > 0 ? S[i - 1][j - 1] + sc : -1); }
    const pairs = []; let i = n, j = m;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0) { const [sc, verdict, note] = judge(att[i - 1], real[j - 1]); if (sc > 0 && S[i][j] === S[i - 1][j - 1] + sc) { pairs.push({ a: att[i - 1], r: real[j - 1], verdict, note }); i--; j--; continue; } }
      if (j > 0 && (i === 0 || S[i][j] === S[i][j - 1])) { const r = real[j - 1]; pairs.push({ a: null, r, verdict: r.kind === "context" ? "context" : "missed" }); j--; }
      else { pairs.push({ a: att[i - 1], r: null, verdict: "extra" }); i--; }
    }
    return pairs.reverse();
  }
  function reveal() {
    const f = flow(), real = realUnits(f), touched = FlowKit.touchedLanes(f), pairs = align(st.steps, real);
    const ghostLanes = lanes.map(() => null);
    const missingLanes = [...touched].filter((id) => !st.slots.includes(id)).sort((a, b) => LANE_INDEX[a] - LANE_INDEX[b]);
    missingLanes.forEach((id) => { let best = -1, bd = Infinity; st.slots.forEach((x, i) => { if (!x && !ghostLanes[i]) { const d = Math.abs(i - LANE_INDEX[id]); if (d < bd) { bd = d; best = i; } } }); if (best !== -1) ghostLanes[best] = id; });
    const scored = real.filter((r) => r.kind !== "context").length;
    const got = pairs.filter((p) => p.verdict === "right").length + 0.5 * pairs.filter((p) => p.verdict === "near").length;
    st.revealed = { pairs, ghostLanes, missingLanes, scored, got, extraLanes: st.slots.filter((id) => id && !touched.has(id)) };
    const hist = tries(f.id); hist.push({ at: new Date().toISOString(), got, of: scored });
    if (!st.noStore) try { localStorage.setItem(storeKey(f.id), JSON.stringify(hist.slice(-20))); } catch (e) { console.warn("[rehearse] this browser would not keep the try:", e.message); }
    renderAll(); playReveal();
  }
  const realLaneX = (id, g) => { const i = st.slots.indexOf(id); if (i !== -1) return g.slots[i].x; const j = st.revealed.ghostLanes.indexOf(id); return j === -1 ? null : g.slots[j].x; };
  function renderReveal(svg, g) {
    const R = st.revealed; R.rowEls = [];
    R.pairs.forEach((p, i) => {
      const y = rowY(i, g), gRow = el("g", { opacity: i < (R.shown || 0) || R.done ? 1 : 0 }, svg);
      R.rowEls.push({ g: gRow, y, p });
      if (p.a) {
        const gA = el("g", { class: p.verdict === "extra" ? "struck" : "" }, gRow);
        if (p.a.self) { const x = laneX(p.a.self, g); if (x !== null) loopShape(gA, x, y, FlowKit.laneColor(p.a.self)); }
        else { const x1 = laneX(p.a.from, g), x2 = laneX(p.a.to, g); arrowShape(gA, x1, x2, y, p.verdict === "right" ? FlowKit.laneColor(p.a.from) : Theme.c("ink-4")); if (p.verdict !== "right") chipLabel(gA, (x1 + x2) / 2, y + 30, CONTRACT[p.a.contract], { cls: "struck" }); }
      }
      if (p.r && p.r.kind === "msg") {
        const x1 = realLaneX(p.r.from, g), x2 = realLaneX(p.r.to, g);
        if (x1 !== null && x2 !== null) {
          if (p.verdict !== "right") arrowShape(gRow, x1, x2, y, Theme.c("ink"), { head: p.r.direction === "stated" ? "filled" : "open", dash: "3 5", cls: "real" });
          chipLabel(gRow, (x1 + x2) / 2, y, CONTRACT[p.r.contract]);
          p.pulse = { dot: el("circle", { class: "real-pulse", cx: x1, cy: y, r: 4.5, opacity: 0 }, gRow), x1, x2 };
        }
      } else if (p.r && p.r.kind === "self") {
        const x = realLaneX(p.r.lane, g); if (x !== null && p.verdict !== "right") loopShape(gRow, x, y, Theme.c("ink"), "3 4");
      } else if (p.r && p.r.kind === "context") {
        const xs = [...FlowKit.touchedLanes(flow())].map((id) => realLaneX(id, g)).filter((x) => x !== null);
        const x0 = (xs.length ? Math.min(...xs) : 80) - 60, x1 = (xs.length ? Math.max(...xs) : 400) + 60;
        el("rect", { x: x0, y: y - 15, width: x1 - x0, height: 30, rx: 8, fill: "none", stroke: Theme.c("rule-3"), "stroke-dasharray": "4 4" }, gRow);
        el("text", { x: (x0 + x1) / 2, y: y + 5, "text-anchor": "middle", class: "ctx-text" }, gRow).textContent = p.r.ref ? `Step ${p.r.n} repeats ${E[p.r.ref].id}; not scored` : shorten(p.r.short, 90);
      }
      numberBadge(gRow, p.r ? p.r.n : "+", y);
      if (p.verdict && p.verdict !== "context") {
        const label = { right: "Right", near: "Nearly", missed: "Missed", extra: "Not in the flow" }[p.verdict];
        const gS = el("g", { class: "stamp-wrap v-" + p.verdict }, gRow), t = el("text", { x: 0, y: 0 }, gS);
        t.textContent = label;
        const w = t.getComputedTextLength() + 18, sx = g.width - 40;
        gS.insertBefore(el("rect", { x: sx - w, y: y - 11, width: w, height: 22, rx: 11 }), t);
        t.setAttribute("x", sx - w + 9); t.setAttribute("y", y + 4);
        p.stamp = gS;
      }
    });
    if (R.done) R.rowEls.forEach((r) => r.g.setAttribute("opacity", 1));
  }
  function playReveal() {
    const R = st.revealed, STEP = reducedMotion() ? 0 : 0.75;
    R.pairs.forEach((p, i) => setTimeout(() => {
      if (st.revealed !== R || !R.rowEls) return;
      const row = R.rowEls[i]; if (!row) return;
      R.shown = i + 1; row.g.setAttribute("opacity", 1); row.g.classList.add("fade-in");
      if (p.pulse && !reducedMotion()) {
        const { dot, x1, x2 } = p.pulse, start = performance.now(); dot.setAttribute("opacity", 1);
        (function run() { const k = Math.min(1, (performance.now() - start) / 450); dot.setAttribute("cx", x1 + (x2 - x1) * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(run); else dot.setAttribute("opacity", 0); })();
        pluck(p.r.to);
      }
      if (p.stamp) setTimeout(() => { p.stamp.classList.add("stamp"); Sound.verdict(p.verdict === "right" ? "right" : p.verdict === "near" ? "near" : "miss"); }, STEP * 600);
      if (i === R.pairs.length - 1) setTimeout(() => { R.done = true; if (R.got === R.scored) Sound.chime(); }, STEP * 1000);
    }, i * STEP * 1000));
  }
  function resultHtml() {
    const R = st.revealed, f = flow();
    const by = (v) => R.pairs.filter((p) => p.verdict === v);
    const frac = R.scored ? R.got / R.scored : 0, Cc = 2 * Math.PI * 38, got = Number.isInteger(R.got) ? R.got : R.got.toFixed(1);
    const line = (p) => {
      const link = p.r && p.r.kind === "msg" ? `${laneOf(p.r.from).name} to ${laneOf(p.r.to).name} over ${p.r.contract} ${CONTRACT[p.r.contract].title}.` : p.r && p.r.kind === "self" ? `Inside ${laneOf(p.r.lane).name}.` : "";
      const what = p.r ? `<span class="t">Step ${p.r.n}. ${esc(p.r.short)}<small>${esc(link)}${p.note ? " " + esc(p.note) : ""}</small></span>`
        : `<span class="t">${p.a.self ? `Inside ${esc(laneOf(p.a.self).name)}` : `${esc(laneOf(p.a.from).name)} to ${esc(laneOf(p.a.to).name)} over ${esc(p.a.contract)}`}<small>The real flow has no step like this.</small></span>`;
      return `<li><span class="v ${p.verdict}">${{ right: "Right", near: "Nearly", missed: "Missed", extra: "Extra" }[p.verdict]}</span>${what}</li>`;
    };
    return `<div class="score"><svg viewBox="0 0 92 92"><circle cx="46" cy="46" r="38" fill="none" stroke="var(--rule)" stroke-width="7"/>
        <circle cx="46" cy="46" r="38" fill="none" stroke="var(--ink)" stroke-width="7" stroke-linecap="round" transform="rotate(-90 46 46)" stroke-dasharray="${Cc}" stroke-dashoffset="${R.done ? Cc * (1 - frac) : Cc}" id="rh-ring" data-to="${Cc * (1 - frac)}" style="transition: stroke-dashoffset ${R.pairs.length * 0.75}s cubic-bezier(.2,.8,.2,1)"></circle></svg>
        <div><div class="big">${got} of ${R.scored}</div><div class="of">steps recalled, in order${by("near").length ? "; nearly counts half" : ""}</div></div></div>
      ${R.missingLanes.length || R.extraLanes.length ? `<p class="lede">${R.missingLanes.length ? `You left out ${R.missingLanes.map((id) => esc(laneOf(id).name)).join(" and ")}; it now sits in a dashed lane. ` : ""}${R.extraLanes.length ? `${R.extraLanes.map((id) => esc(laneOf(id).name)).join(" and ")} ${R.extraLanes.length > 1 ? "are" : "is"} not in this flow.` : ""}</p>` : ""}
      <ul class="verdicts">${[...by("missed"), ...by("near"), ...by("extra"), ...by("right")].map(line).join("")}</ul>
      <button class="reveal" id="rh-again">Try again<span>from empty lanes</span></button>
      <div class="row-actions"><button class="btn" id="rh-again-lanes">Try again, keep my lanes</button></div>`;
  }
  function bindResult() {
    const ring = q("#rh-ring");
    if (ring) requestAnimationFrame(() => requestAnimationFrame(() => { ring.style.strokeDashoffset = ring.dataset.to; }));
    q("#rh-again").onclick = () => reset(false);
    q("#rh-again-lanes").onclick = () => { const keep = st.slots.map((id, i) => id || (st.revealed && st.revealed.ghostLanes[i]) || null); reset(true); st.slots = keep; renderAll(); };
  }
  /* For the self-test: fill the lanes and steps from the record, then reveal; a perfect attempt must score full marks. */
  function selfCheck(key) {
    open(key); st.noStore = true;
    const f = flow(), touched = [...FlowKit.touchedLanes(f)].sort((a, b) => LANE_INDEX[a] - LANE_INDEX[b]);
    touched.forEach((id, i) => { st.slots[i] = id; });
    st.steps = realUnits(f).filter((u) => u.kind !== "context").map((u) => (u.kind === "self" ? { self: u.lane } : { from: u.from, to: u.to, contract: u.contract }));
    renderAll(); reveal();
    const out = { got: st.revealed.got, of: st.revealed.scored };
    st.noStore = false; close();
    return out;
  }
  return { open, close, selfCheck };
})();
