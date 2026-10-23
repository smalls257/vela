/* Motion on the map, on demand. Nothing moves until you pick something.
   - Trace: pick a flow or a contract and its path lights hop by hop: each hop is a step of the flow page (or the
     contract's provider to each consumer), numbered where it lands.
   - Trains are the line map's own motion (view-map.js).
   With effects off (Plain) the same path is shown at once, numbered, with nothing moving.

   Every map drawing registers what it drew in a Scene: each node's box and each edge's points, plus how a key is
   drawn (an app inside a collapsed cluster is drawn as its cluster). The trace only reads the Scene. */
const Scene = (() => {
  let st = null;
  function reset(svg, layer, resolve, top) { st = { svg, layer, top: top || layer, nodes: {}, edges: {}, resolve: resolve || ((k) => k) }; }
  const pair = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);
  function node(key, box) { if (st) st.nodes[key] = box; }
  function edge(a, b, e) { if (st) st.edges[pair(a, b)] = Object.assign({ a, b }, e); }
  function vis(key) { if (!st) return null; const k = st.resolve(key); return st.nodes[k] ? k : null; }
  function edgeOf(a, b) { return st ? st.edges[pair(a, b)] || null : null; }
  return { reset, node, edge, vis, edgeOf, get live() { return !!(st && st.svg.isConnected); }, get st() { return st; } };
})();

const Motion = (() => {
  const HOP_MS = 650;
  let timers = [], active = null;
  function clear() {
    timers.forEach(clearTimeout); timers = [];
    active = null;
    const S = Scene.st;
    if (!S || !S.svg.isConnected) return;
    S.layer.innerHTML = "";
    S.svg.classList.remove("tracing");
    $$(".tr-on", S.svg).forEach((n) => n.classList.remove("tr-on"));
    const legend = $("#motion-legend"); if (legend) legend.remove();
  }
  const later = (ms, fn) => { if (reducedMotion() || ms <= 0) fn(); else timers.push(setTimeout(fn, ms)); };
  function badge(x, y, text) {
    const g = s("g", { class: "m-badge" }, Scene.st.top);
    s("circle", { cx: x, cy: y, r: 13 }, g);
    s("text", { x, y: y + 4.5, "text-anchor": "middle" }, g).textContent = text;
    return g;
  }
  function legend(text) {
    const board = $("#board"); if (!board) return;
    const old = $("#motion-legend"); if (old) old.remove();
    board.append(h("div", { class: "motion-legend", id: "motion-legend" }, h("span", {}, text), h("button", { class: "linkish", onclick: clear }, "Clear")));
  }

  /* Where a path, walked back from its end, leaves the box it ends in: the badge sits there, on the box's edge. */
  function exitPoint(pts, box) {
    const inside = (p) => p.x > box.x - 2 && p.x < box.x + box.w + 2 && p.y > box.y - 2 && p.y < box.y + box.h + 2;
    const back = pts.slice().reverse(), total = Geo.length(back);
    for (let d = 0; d <= total; d += 4) { const p = Geo.pointAt(back, d); if (!inside(p)) return p; }
    return back[back.length - 1];
  }

  /* ------------------------------------------------------------ trace */
  function hopsOf(key) {
    // a flow's hops are its steps' messages, sender to receiver, as the played flow draws them; an inferred
    // direction (the step names no sender) is drawn dashed and the legend says so
    if (FLOW[key]) return FLOW[key].steps.flatMap((st) => st.messages.map((m) => ({ from: m.from, to: m.to, step: st.n, contract: m.contract, inferred: m.direction === "inferred" })));
    const c = CONTRACT[key];
    if (c) return c.consumers.filter((k) => k !== c.provider).map((k) => ({ from: c.provider, to: k, step: 1, contract: key }));
    return [];
  }
  function trace(key) {
    clear();
    const S = Scene.st;
    if (!S || !S.svg.isConnected) return { hops: 0, drawn: 0 };
    const hops = hopsOf(key), color = FLOW[key] ? Geo.flowColor(Geo.FLOW_ORDER[key]) : Theme.c("focus");
    active = { kind: "trace", key };
    S.svg.classList.add("tracing");
    let drawn = 0, n = 0, inside = 0;
    const seen = new Set();
    for (const hop of hops) {
      const a = Scene.vis(hop.from), b = Scene.vis(hop.to);
      if (!a || !b) continue;
      if (a === b) { inside++; continue; }  // both ends inside one collapsed cluster
      const e = Scene.edgeOf(a, b);
      if (!e) continue;
      const pts = e.a === a ? e.pts : e.pts.slice().reverse(), at = n++;
      const tag = `${a}>${b}>${hop.step}`;
      if (seen.has(tag)) continue;
      seen.add(tag); drawn++;
      later(at * HOP_MS, () => {
        if (!Scene.live || !active) return;
        const path = s("path", { d: Geo.roundedPath(pts, 26), class: "tr-path" + (hop.inferred ? " inferred" : ""), stroke: color }, S.layer);
        if (!reducedMotion() && hop.inferred) path.animate([{ opacity: 0 }, { opacity: 0.95 }], { duration: HOP_MS * 0.9, fill: "forwards" });
        else if (!reducedMotion()) { const len = path.getTotalLength(); path.style.strokeDasharray = len; path.style.strokeDashoffset = len; path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: HOP_MS * 0.9, fill: "forwards", easing: "ease-in-out" }); }
        [a, b].forEach((k) => S.nodes[k].el.classList.add("tr-on"));
        if (e.el) e.el.classList.add("tr-on");
        const at2 = exitPoint(pts, S.nodes[b]);
        badge(at2.x, at2.y, hop.step);
      });
    }
    const guessed = hops.filter((x) => x.inferred).length;
    legend(FLOW[key] ? `Tracing ${E[key].title}: ${plural(drawn, "step")}, in order.${guessed ? " Dashed ones don't say who sends, so the arrow follows the contract." : ""}${inside ? ` ${plural(inside, "step")} ${inside === 1 ? "stays" : "stay"} inside a closed group.` : ""}`
      : `Tracing ${titleOf(key)}: from ${titleOf(CONTRACT[key].provider)} to ${plural(drawn, "consumer")}.`);
    return { hops: hops.length, drawn, inside };
  }

  /* Picking a flow or a contract draws its path; picking anything else draws nothing. */
  function onPick(key) {
    if (!Scene.live) return null;
    if (FLOW[key] || CONTRACT[key]) return trace(key);
    return null;
  }
  return { trace, clear, onPick, hopsOf, get active() { return active; } };
})();
