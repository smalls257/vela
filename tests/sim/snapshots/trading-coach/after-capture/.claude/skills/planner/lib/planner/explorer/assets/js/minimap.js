/* The minimap: the formation, small, in the foot of the panel on every view, with "you are here".
   Same pinned positions and same lights as the big map, so the corner and the map never disagree. It keeps the
   map's orientation and is never rotated to the current page (Levine's you-are-here maps). "Here" is what the
   panel shows, or what the current view is about (the step being played, the strip being read). */
const Minimap = (() => {
  let L = null;
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
    if (!L) L = Geo.layout({ cw: 300, rh: 150 });
    const at = new Set(here());
    const pad = 70, padTop = 40, b = L.bounds;
    const vb = [b.x0 - pad, b.y0 - padTop, b.x1 - b.x0 + pad * 2, b.y1 - b.y0 + pad + padTop];
    box.innerHTML = "";
    pulses.length = 0;
    const label = at.size ? `You are here: ${[...at].filter((k) => NODE[k]).map(titleOf).join(", ") || [...at].join(", ")}` : "The whole map; pick something to see where it sits";
    box.append(h("div", { class: "mini-head" }, h("span", {}, "Map"), h("span", { class: "mini-here" }, label)));
    const root = s("svg", { viewBox: vb.join(" "), role: "img", "aria-label": label }, box);
    const defs = s("defs", {}, root);
    s("feGaussianBlur", { stdDeviation: 14 }, s("filter", { id: "mini-glow", x: "-80%", y: "-80%", width: "260%", height: "260%" }, defs));
    if (L.zoneY !== null) s("line", { x1: vb[0], x2: vb[0] + vb[2], y1: L.zoneY, y2: L.zoneY, stroke: Theme.c("rule-3"), "stroke-width": 3, "stroke-dasharray": "4 12" }, root);
    for (const cor of Object.values(L.corridors)) {
      const lv = cor.contracts.map(levelOf).sort((p, q) => rank(q) - rank(p))[0];
      const hot = cor.contracts.some((c) => at.has(c)) || (at.has(cor.a) && at.has(cor.b));
      const colour = hot ? Theme.c("focus") : lv !== "dark" ? LIGHT[lv].colour : Theme.c("track");
      s("path", { d: Geo.roundedPath(Geo.route({ x: L.stations[cor.a].x, y: L.stations[cor.a].y }, { x: L.stations[cor.b].x, y: L.stations[cor.b].y }, cor.sideA), 30),
        fill: "none", stroke: colour, "stroke-width": hot ? 12 : lv !== "dark" ? 8 : 6, "stroke-linecap": "round", opacity: hot ? 1 : 0.85 }, root);
    }
    for (const st of Object.values(L.stations)) {
      const light = lightOf(st.key), lv = light ? light.level : "dark", c = LIGHT[lv].colour;
      const w = st.outside ? 150 : 190, ht = 70;
      const g = s("g", { class: "mini-node", tabindex: 0, role: "link", "aria-label": `${st.node.title}: ${LIGHT[lv].word}` }, root);
      if (lv !== "dark" && glowOn()) {
        const glow = s("rect", { x: st.x - w / 2, y: st.y - ht / 2, width: w, height: ht, rx: 16, fill: c, filter: "url(#mini-glow)", opacity: 0.6 }, g);
        pulses.push({ el: glow, period: pulsePeriod(light.urgency), amp: 0.25 + 0.5 * light.urgency, phase: st.x * 7 });
      }
      s("rect", { x: st.x - w / 2, y: st.y - ht / 2, width: w, height: ht, rx: st.outside ? 4 : 16, fill: lv === "dark" ? LIGHT.dark.colour : c, stroke: Theme.c("face-edge"), "stroke-width": 4 }, g);
      if (at.has(st.key)) s("rect", { x: st.x - w / 2 - 16, y: st.y - ht / 2 - 16, width: w + 32, height: ht + 32, rx: 26, fill: "none", stroke: Theme.c("focus"), "stroke-width": 8, class: "mini-ring" }, g);
      const t = s("text", { x: st.x, y: st.y + 11, "text-anchor": "middle", fill: lv === "dark" ? (at.has(st.key) ? Theme.c("focus") : Theme.c("node-name")) : LIGHT[lv].ink, "font-size": st.outside ? 26 : 30, "font-weight": 600 }, g);
      t.textContent = shorten(st.node.title, st.outside ? 10 : 11);
      g.addEventListener("click", () => go(st.key, { reveal: App.view === "map" }));
      g.addEventListener("keydown", (e) => { if (e.key === "Enter") go(st.key, {}); });
    }
  }
  function breathe(now) {
    // calm: the minimap's glow holds still; the big map is where an overdue lamp breathes
    for (const p of pulses) if (!p.set) { p.el.setAttribute("opacity", "0.35"); p.set = true; }
    requestAnimationFrame(breathe);
  }
  requestAnimationFrame(breathe);
  return { refresh, here };
})();
