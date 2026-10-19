/* The minimap: the formation, small, in the foot of the panel on every view, with "you are here".
   Same pinned positions and same lights as the big map, so the corner and the map never disagree. It keeps the
   map's orientation and is never rotated to the current page (Levine's you-are-here maps). "Here" is what the
   panel shows, or what the current view is about (the step being played, the strip being read). */
const Minimap = (() => {
  Legend.define("mini.party", [{ k: "clip", fill: "unlit", stroke: "rule-3", w: 1.4 }], "Clipped corners: an outside service");
  Legend.define("mini.link", [Legend.ln({ stroke: "track", w: 3 })], "Gray line: a connection between two boxes");
  Legend.define("mini.link.lit", [Legend.ln({ stroke: "caution", w: 3.5 })], "Colored line: a connection with a contract that needs you, in its most urgent color");
  Legend.define("mini.link.hot", [Legend.ln({ stroke: "focus", w: 4.5 })], "White line: a connection to what you picked");
  Legend.define("mini.here", [Legend.bx({ stroke: "focus", w: 2.4, rx: 6 })], "White ring: what the panel is showing now");
  const MINI = Layout.FRAME;  // the cockpit's frame, the one the overlap rule measures in: a box clear on the big map is clear here
  const pulses = [];
  function here() {
    const v = viewDef(App.view);
    const own = v && v.here ? v.here() : null;
    if (own && own.length) return own;
    return App.focus ? mapAnchors(App.focus) : [];
  }
  function refresh() {
    const box = $("#panel-mini");
    if (!box) return;
    if (!D.nodes.length) { box.innerHTML = ""; return; }
    const L = Geo.layout(MINI);  // drawn afresh each time: a box held by the pointer, or moved, is where it now stands
    const at = new Set(here());
    const pad = 70, padTop = 40, b = L.bounds;
    const vb = [b.x0 - pad, b.y0 - padTop, b.x1 - b.x0 + pad * 2, b.y1 - b.y0 + pad + padTop];
    box.innerHTML = "";
    pulses.length = 0;
    const label = at.size ? `You are here: ${[...at].filter((k) => NODE[k]).map(titleOf).join(", ") || [...at].join(", ")}` : "The whole map; pick something to see where it sits";
    const lg = Legend.open("minimap", { root: () => box, open: false, quiet: true, probes: { ...Legend.lampProbes((lv) => `g.mini-node[data-level="${lv}"]`), "mini.party": 'g.mini-node[data-kind="party"]',
      "mini.link": "path.mini-link:not(.lit):not(.hot)", "mini.link.lit": "path.mini-link.lit", "mini.link.hot": "path.mini-link.hot", "mini.here": ".mini-ring" } });
    box.append(h("div", { class: "mini-head" }, h("span", {}, "Overview"), h("span", { class: "mini-here" }, label)));
    const root = s("svg", { viewBox: vb.join(" "), role: "img", "aria-label": label }, box);
    const defs = s("defs", {}, root);
    s("feGaussianBlur", { stdDeviation: 14 }, s("filter", { id: "mini-glow", x: "-80%", y: "-80%", width: "260%", height: "260%" }, defs));
    if (L.zoneY !== null) s("line", { x1: vb[0], x2: vb[0] + vb[2], y1: L.zoneY, y2: L.zoneY, stroke: Theme.c("rule-3"), "stroke-width": 3, "stroke-dasharray": "4 12" }, root);
    for (const cor of Object.values(L.corridors)) {
      const lv = cor.contracts.map(levelOf).sort((p, q) => rank(q) - rank(p))[0];
      const hot = cor.contracts.some((c) => at.has(c)) || (at.has(cor.a) && at.has(cor.b));
      const color = hot ? Theme.c("focus") : lv !== "dark" ? LIGHT[lv].color : Theme.c("track");
      lg.saw(hot ? "mini.link.hot" : lv !== "dark" ? "mini.link.lit" : "mini.link");
      s("path", { d: Geo.roundedPath(Geo.route({ x: L.stations[cor.a].x, y: L.stations[cor.a].y }, { x: L.stations[cor.b].x, y: L.stations[cor.b].y }, cor.sideA), 30),
        class: "mini-link" + (hot ? " hot" : lv !== "dark" ? " lit" : ""), fill: "none", stroke: color, "stroke-width": hot ? 12 : lv !== "dark" ? 8 : 6, "stroke-linecap": "round", opacity: hot ? 1 : 0.85 }, root);
    }
    for (const st of Object.values(L.stations)) {
      const light = lightOf(st.key), lv = light ? light.level : "dark", c = LIGHT[lv].color;
      const w = st.outside ? 150 : 190, ht = 70;
      const g = s("g", { class: "mini-node", "data-level": lv, "data-kind": st.outside ? "party" : "app", }, root);
      lg.saw("lamp." + lv); if (st.outside) lg.saw("mini.party");
      if (lv !== "dark" && glowOn()) {
        const glow = s("rect", { x: st.x - w / 2, y: st.y - ht / 2, width: w, height: ht, rx: 16, fill: c, filter: "url(#mini-glow)", opacity: 0.6 }, g);
        pulses.push({ el: glow, period: pulsePeriod(light.urgency), amp: 0.25 + 0.5 * light.urgency, phase: st.x * 7 });
      }
      s("rect", { x: st.x - w / 2, y: st.y - ht / 2, width: w, height: ht, rx: st.outside ? 4 : 16, fill: lv === "dark" ? LIGHT.dark.color : c, stroke: Theme.c("face-edge"), "stroke-width": 4 }, g);
      if (at.has(st.key)) lg.saw("mini.here");
      if (at.has(st.key)) s("rect", { x: st.x - w / 2 - 16, y: st.y - ht / 2 - 16, width: w + 32, height: ht + 32, rx: 26, fill: "none", stroke: Theme.c("focus"), "stroke-width": 8, class: "mini-ring" }, g);
      const t = s("text", { x: st.x, y: st.y + 11, "text-anchor": "middle", fill: lv === "dark" ? (at.has(st.key) ? Theme.c("focus") : Theme.c("node-name")) : LIGHT[lv].ink, "font-size": st.outside ? 26 : 30, "font-weight": 600 }, g);
      t.textContent = shorten(st.node.title, st.outside ? 10 : 11);
      Nodes.wire(g, { label: `${st.node.title}: ${LIGHT[lv].word}`, role: "link", open: () => go(st.key, { reveal: App.view === "map" }) });
    }
    lg.paint();
  }
  function breathe(now) {
    // calm: the minimap's glow holds still; the big map is where an overdue lamp breathes
    for (const p of pulses) if (!p.set) { p.el.setAttribute("opacity", "0.35"); p.set = true; }
    requestAnimationFrame(breathe);
  }
  requestAnimationFrame(breathe);
  return { refresh, here };
})();
