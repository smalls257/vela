/* Releases: the system before and after, from planner.releases. Today, then the state after each release,
   cumulative, with each app's status (exists, changes, new, absent) and each contract's (exists, new, absent), as
   releases.snapshots works them out from the requirements each release delivers. What a release touches is the apps
   and contracts that carry a share of what it delivers (allocation.carried). A vault with no releases says so and
   shows only today against the end state, from each app's change.

   One drawing serves the Releases section and the map's Releases lens: the pinned formation, with release status
   drawn in shape and ink only (solid, ringed, dashed), so the five lamp colours keep their one meaning. With effects
   on, moving between states morphs: apps arrive, change and fade, and contracts draw in. Plain switches at once. */
const Releases = (() => {
  const R = D.releases;
  const STATES = R.count ? R.states : [R.states[0], R.end];
  const st = { at: Math.min(STATES.length - 1, Math.max(0, +(HASH.get("state") || 0))), compare: HASH.has("compare"), a: 0, b: STATES.length - 1, playing: 0 };
  const short = (s) => (s.name.split(":")[0] || s.name).trim();
  const STATUS_WORD = { exists: "unchanged", changes: "changes", new: "new", absent: "not there" };
  /* The key: release status is drawn in shape and ink only (solid, heavy, dashed, dotted), so the lamp colours keep their one meaning. */
  const { bx, ln } = Legend;
  Legend.define("rel.new", [bx({ fill: "ink", stroke: "focus", w: 1.4, rx: 5 })], "Filled box: an app that is new in this state");
  Legend.define("rel.changes", [bx({ fill: "deck-3", stroke: "ink", w: 2.6, rx: 5 })], "Heavy outline: an app that is changing, or has changed");
  Legend.define("rel.exists", [bx({ fill: "deck-3", stroke: "rl-edge", w: 1.4, rx: 5 })], "Plain box: an app that stays as it is");
  Legend.define("rel.absent", [bx({ stroke: "ink-4", w: 1.4, rx: 5, dash: "3.5 3", opacity: 0.6 })], "Dashed, faded box: an app not there yet, or retired");
  Legend.define("rel.party", [bx({ fill: "rl-party", stroke: "rl-edge", w: 1.4, rx: 2, dash: "1.5 3" })], "Dotted outline: an outside party");
  Legend.define("rel.touched", [bx({ fill: "ink", width: 13, x: 10, y: 3.5, height: 9, rx: 4.5 }), { k: "text", t: "Δ", fill: "room", x: 16.5, y: 11, size: 8 }], "Tag (Δ or NEW): this release's work touches the app");
  Legend.define("rel.lamp", [bx({ fill: "caution", width: 8, height: 8, x: 13, y: 4, rx: 2 })], "Small coloured square: the app's light today, as on the map");
  Legend.define("rel.cor.exists", [ln({ stroke: "track", w: 3.5 })], "Grey line: a contract that already exists");
  Legend.define("rel.cor.new", [ln({ stroke: "rl-name", w: 3.5 })], "Bright line: a contract that appears in this state");
  Legend.define("rel.cor.through", [ln({ stroke: "focus", w: 4.5 })], "White line: a contract this release's work goes through");
  Legend.define("rel.cor.planned", [ln({ stroke: "siding", w: 3, dash: "1 6" })], "Dotted line: a contract still to come");
  const LOOKS = () => ({
    "rel.new": ".rl-node.s-new", "rel.changes": ".rl-node.s-changes", "rel.exists": ".rl-node.s-exists:not(.party)", "rel.absent": ".rl-node.s-absent", "rel.party": ".rl-node.party",
    "rel.touched": ".rl-node.touched", "rel.lamp": ".rl-lamp", "rel.cor.exists": ".rl-cor.s-exists:not(.through)", "rel.cor.new": ".rl-cor.s-new:not(.through)",
    "rel.cor.through": ".rl-cor.through", "rel.cor.planned": ".rl-cor.s-absent.planned:not(.through)",
  });
  let KEY = null, DRAWN = [];  // the key of the releases now on the page, and what each map in it (one, or two compared) really drew
  const refreshKey = () => { if (!KEY) return; KEY.seen.clear(); DRAWN = DRAWN.filter((m) => m.svg.isConnected); DRAWN.forEach((m) => m.looks.forEach((id) => KEY.saw(id))); KEY.paint(); };

  function appWord(i, k) {
    const now = STATES[i].apps[k] || "exists", prev = i > 0 ? STATES[i - 1].apps[k] || "exists" : null;
    if (STATES[i].fromChange) return { exists: "unchanged", changes: "changed", new: "new", absent: "retired" }[now];
    if (now === "absent") return prev === "exists" || prev === "changes" ? "gone" : later(i, k) ? "not built yet" : "not there";
    if (now === "new") return prev === "absent" ? "arrives" : "new";
    if (now === "changes") return (STATES[i].touched || []).includes(k) ? (prev === "exists" ? "starts to change" : "changes again") : "changed";
    return i === 0 ? "today" : "unchanged";
  }
  const later = (i, k) => STATES.slice(i + 1).some((s) => s.apps[k] && s.apps[k] !== "absent");
  function corridorStatus(cor, i) {
    const list = cor.contracts.map((c) => STATES[i].contracts[c] || "exists");
    return list.includes("exists") ? "exists" : list.includes("new") ? "new" : "absent";
  }

  /* ------------------------------------------------------------ the drawing */
  function drawMap(box, i, opts = {}) {
    const L = Geo.layout({ cw: 300, rh: 150 }), b = L.bounds, W = 172, H = 58;
    const left = b.x0 - 104, right = b.x1 + 104, top = b.y0 - 50, bottom = b.y1 + 36;  // room for the 172-wide boxes and their tags
    const svg = s("svg", { viewBox: `${left} ${top} ${right - left} ${bottom - top}`, class: "rl-map", role: "img", "aria-label": "The system in this state" }, box);
    const looks = new Set();
    MapView.fitSvg(svg, box, right - left, bottom - top, opts.max || 1.0);
    if (L.zoneY !== null) s("line", { x1: left, x2: right, y1: L.zoneY, y2: L.zoneY, class: "zone" }, svg);
    const gCor = s("g", {}, svg), gNodes = s("g", {}, svg);
    const cors = Object.values(L.corridors).map((cor) => {
      const d = Geo.roundedPath(Geo.route({ x: L.stations[cor.a].x, y: L.stations[cor.a].y }, { x: L.stations[cor.b].x, y: L.stations[cor.b].y }, cor.sideA), 30);
      const el = s("path", { d, class: "rl-cor", "data-contracts": cor.contracts.join(",") }, gCor);
      el.appendChild(document.createElementNS(SVGNS, "title")).textContent = cor.contracts.map((c) => `${c} ${CONTRACT[c].title}`).join("; ");
      return { cor, el };
    });
    const nodes = Object.values(L.stations).map((stn) => {
      const n = stn.node, g = s("g", { class: "rl-node", "data-key": n.key, tabindex: 0, role: "button" }, gNodes);
      g.style.transformOrigin = `${stn.x}px ${stn.y}px`;
      s("rect", { x: stn.x - W / 2, y: stn.y - H / 2, width: W, height: H, rx: n.kind === "app" ? 10 : 3, class: "rl-face" }, g);
      Icons.put(g, Icons.name(n.key), stn.x - W / 2 + 20, stn.y + 1, 18, "rl-glyph");
      s("text", { x: stn.x + 10, y: stn.y - 2, "text-anchor": "middle", class: "rl-name" }, g).textContent = shorten(n.title, 17);
      const sub = s("text", { x: stn.x + 10, y: stn.y + 16, "text-anchor": "middle", class: "rl-sub" }, g);
      const tag = s("g", { class: "rl-tag" }, g);
      s("rect", { x: stn.x + W / 2 - 40, y: stn.y - H / 2 - 9, width: 46, height: 18, rx: 9 }, tag);
      const tagText = s("text", { x: stn.x + W / 2 - 17, y: stn.y - H / 2 + 4, "text-anchor": "middle" }, tag);
      const lv = levelOf(n.key);
      if (lv !== "dark" && n.kind === "app") { s("rect", { x: stn.x - W / 2 + 8, y: stn.y - H / 2 + 8, width: 8, height: 8, rx: 2, fill: LIGHT[lv].colour, class: "rl-lamp" }, g)
        .appendChild(document.createElementNS(SVGNS, "title")).textContent = `${LIGHT[lv].word} today (attention.lights)`; looks.add("rel.lamp"); }
      g.addEventListener("click", () => go(n.key, { reset: true }));
      return { n, g, sub, tagText };
    });
    function set(j, animate) {
      const S = STATES[j], prev = j > 0 ? STATES[j - 1] : null, morph = animate && !reducedMotion();
      for (const id of [...looks]) if (id !== "rel.lamp") looks.delete(id);
      for (const { n, g, sub, tagText } of nodes) {
        const status = n.kind === "app" ? S.apps[n.key] || "exists" : "exists", word = n.kind === "app" ? appWord(j, n.key) : "outside party";
        const was = prev && n.kind === "app" ? prev.apps[n.key] || "exists" : status;
        const touched = (S.touched || []).includes(n.key);
        g.setAttribute("class", `rl-node s-${status}${touched ? " touched" : ""}${n.kind !== "app" ? " party" : ""}`);
        g.dataset.status = status;
        looks.add(n.kind !== "app" ? "rel.party" : "rel." + status);
        if (touched) looks.add("rel.touched");
        sub.textContent = word;
        tagText.textContent = word === "arrives" ? "NEW" : touched ? "Δ" : "";
        if (morph && was !== status) {
          if (status === "new" && was === "absent") g.animate([{ transform: "scale(.6)", opacity: 0 }, { transform: "scale(1.06)", opacity: 1, offset: 0.7 }, { transform: "scale(1)", opacity: 1 }], { duration: 700, easing: "ease-out" });
          else if (status === "absent") g.animate([{ opacity: 1 }, { opacity: 0.32 }], { duration: 700 });
        }
        if (morph && touched) g.querySelector(".rl-face").animate([{ strokeWidth: 6 }, { strokeWidth: 2.5 }], { duration: 900, easing: "ease-out" });
      }
      for (const { cor, el } of cors) {
        const status = corridorStatus(cor, j), was = prev ? corridorStatus(cor, j - 1) : status;
        const through = cor.contracts.some((c) => (S.through || []).includes(c));
        const planned = status === "absent" && cor.contracts.some((c) => STATES.slice(j + 1).some((x) => x.contracts[c] !== "absent"));
        el.setAttribute("class", `rl-cor s-${status}${through ? " through" : ""}${planned ? " planned" : ""}`);
        if (through) looks.add("rel.cor.through"); else if (status === "absent") { if (planned) looks.add("rel.cor.planned"); } else looks.add("rel.cor." + status);
        if (morph && was === "absent" && status !== "absent") { const len = el.getTotalLength(); el.animate([{ strokeDasharray: `${len}`, strokeDashoffset: len }, { strokeDasharray: `${len}`, strokeDashoffset: 0 }], { duration: 900, easing: "ease-in-out" }); }
      }
      svg.dataset.state = j;
      refreshKey();
    }
    const drawn = { svg, looks };
    DRAWN.push(drawn);
    set(i, false);
    return { set, svg };
  }

  /* ------------------------------------------------------------ what each release changes */
  function changes(j) {
    const S = STATES[j], P = STATES[j - 1] || STATES[0];
    const apps = Object.keys(S.apps);
    const arrive = apps.filter((k) => S.apps[k] === "new" && P.apps[k] === "absent");
    const gone = apps.filter((k) => S.apps[k] === "absent" && P.apps[k] !== "absent");
    const change = S.fromChange ? apps.filter((k) => S.apps[k] === "changes") : (S.touched || []).filter((k) => !arrive.includes(k));
    const appear = Object.keys(S.contracts).filter((c) => S.contracts[c] !== "absent" && P.contracts[c] === "absent");
    return { arrive, gone, change, appear };
  }
  function criteriaText(r) { return !r.criteria.length ? "all criteria" : `${r.criteria.map((n) => "AC" + n).join(", ")} of ${r.of}`; }
  function card(j, onPick) {
    const S = STATES[j], c = changes(j), cur = j === st.at;
    const row = (label, keys, chip) => keys.length ? h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, label), h("span", {}, keys.map(chip))) : null;
    return h("section", { class: "rel-card" + (cur ? " on" : ""), "data-state": j },
      h("button", { class: "rc-head", onclick: () => onPick(j) }, h("span", { class: "rc-n" }, S.fromChange ? "End" : `R${j}`), h("span", { class: "rc-t" }, S.fromChange ? "End state, from each app's change" : S.heading || S.name),
        h("span", { class: "rc-m" }, S.target ? day(S.target) + (S.target.slice(0, 4) !== D.today.slice(0, 4) ? " " + S.target.slice(0, 4) : "") : "", S.state ? h("span", { class: "pill" }, S.state) : null)),
      row("Arrive", c.arrive, (k) => refChip(k)), row("Change", c.change, (k) => refChip(k)), row("Retire", c.gone, (k) => refChip(k)), row("Contracts appear", c.appear, (k) => refChip(k)),
      S.rows ? h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, "Delivers"), h("ul", { class: "rc-reqs" }, S.rows.map((r) => h("li", {}, r.requirement ? refChip(r.requirement) : h("span", { class: "gap" }, "a row naming no requirement"),
        h("span", { class: "muted small" }, " " + criteriaText(r)), r.note ? h("div", { class: "muted small" }, r.note) : null)))) : null,
      !c.arrive.length && !c.change.length && !c.appear.length && !(S.rows || []).length ? h("div", { class: "muted small" }, "Nothing changes.") : null);
  }

  /* ------------------------------------------------------------ the timeline and the body */
  function timeline(onPick) {
    const bar = h("div", { class: "rel-timeline", role: "group", "aria-label": "States" });
    STATES.forEach((S, j) => bar.append(h("button", { class: "rel-stop" + (j === st.at ? " on" : "") + (j < st.at ? " past" : ""), "data-state": j, onclick: () => onPick(j), title: S.name },
      h("i"), h("b", {}, j === 0 ? "Today" : S.fromChange ? "End state" : `R${j}`), h("small", {}, j === 0 ? day(D.today) : S.target ? day(S.target) : S.fromChange ? "from change" : ""))));
    const range = h("input", { type: "range", min: 0, max: STATES.length - 1, step: 1, value: st.at, class: "rel-range", "aria-label": "Release" });
    range.addEventListener("input", () => onPick(+range.value));
    return h("div", { class: "rel-time" }, bar, range);
  }
  function body(box, opts = {}) {
    box.innerHTML = "";
    DRAWN = [];
    KEY = Legend.open("releases", { root: () => box, probes: LOOKS() });
    if (!R.count) box.append(emptyState("No releases recorded yet.", `They go in 04b-releases.md${R.page ? ", which lists none yet" : ""}. Until then this shows only today against the end state, worked out from each app's change and each contract's Change line.`, null, "inline rel-none"));
    if (!D.nodes.length) { box.append(emptyState("This vault has no apps yet.", "There is no system to show before and after.", "/planner:boundary")); return; }
    let map = null;
    const controls = h("div", { class: "rel-controls" });
    const pick = (j, animate = true) => {
      st.at = clamp(j, 0, STATES.length - 1);
      if (map) map.set(st.at, animate);
      $$(".rel-stop", box).forEach((b) => { b.classList.toggle("on", +b.dataset.state === st.at); b.classList.toggle("past", +b.dataset.state < st.at); });
      const r = $(".rel-range", box); if (r) r.value = st.at;
      $$(".rel-card", box).forEach((c) => c.classList.toggle("on", +c.dataset.state === st.at));
      const cardEl = $(`.rel-card[data-state="${st.at}"]`, box); if (cardEl && opts.scrollCards !== false) cardEl.scrollIntoView({ block: "nearest" });
      const cap = $(".rel-caption", box); if (cap) cap.textContent = caption(st.at);
      if (typeof Nav !== "undefined") Nav.syncHash();
    };
    const play = h("button", { class: "btn", onclick: () => playAll(pick, play), disabled: STATES.length < 2 ? true : null }, "▶ Play the releases");
    controls.append(timeline((j) => pick(j)), play,
      h("button", { class: "chip" + (st.compare ? " on" : ""), onclick: () => { st.compare = !st.compare; body(box, opts); } }, "Compare two states"));
    box.append(controls);
    if (st.compare) { const c = compare(); box.append(c); c.drawMaps(); return; }
    const grid = h("div", { class: "rel-grid" + (D.map.apps.length > 12 ? " big" : "") });  // past 12 apps the map takes the room
    const mapBox = h("div", { class: "rel-mapbox" });
    const side = h("div", { class: "rel-side" }, h("h3", {}, R.count ? "What each release changes" : "Today to the end state"));
    for (let j = 1; j < STATES.length; j++) side.append(card(j, (x) => pick(x)));
    grid.append(h("div", { class: "rel-left" }, h("div", { class: "rel-caption" }, caption(st.at)), mapBox, KEY.el()), side);
    box.append(grid);
    map = drawMap(mapBox, st.at, { max: opts.max || 1.0 });
    pick(st.at, false);
  }
  function caption(j) {
    const S = STATES[j];
    if (j === 0) return `Today, ${day(D.today)}: what exists before the initiative. ${Object.values(S.apps).filter((x) => x === "absent").length} of ${Object.keys(S.apps).length} apps are not built yet.`;
    const c = changes(j);
    return `${S.fromChange ? "The end state" : `After ${S.heading || S.name}`}: ${[c.arrive.length ? `${plural(c.arrive.length, "app")} ${c.arrive.length === 1 ? "arrives" : "arrive"}` : "", c.change.length ? `${plural(c.change.length, "app")} ${S.fromChange ? "changed" : "touched"}` : "", c.appear.length ? `${plural(c.appear.length, "contract")} ${c.appear.length === 1 ? "appears" : "appear"}` : "", c.gone.length ? `${c.gone.length} retired` : ""].filter(Boolean).join(", ") || "nothing new"}.`;
  }
  function playAll(pick, btn) {
    if (st.playing) { clearInterval(st.playing); st.playing = 0; btn.textContent = "▶ Play the releases"; return; }
    if (reducedMotion()) { pick(STATES.length - 1, false); return; }
    let j = 0; pick(0, false); btn.textContent = "❚❚ Pause";
    st.playing = setInterval(() => { j++; if (j >= STATES.length || !btn.isConnected) { clearInterval(st.playing); st.playing = 0; btn.textContent = "▶ Play the releases"; return; } pick(j); }, 1900);
  }
  function compare() {
    const wrap = h("div", { class: "rel-compare" });
    const select = (which) => h("select", { class: "rel-select", "aria-label": which === "a" ? "First state" : "Second state", onchange: (ev) => { st[which] = +ev.target.value; const box = wrap.parentNode; body(box); } },
      STATES.map((S, j) => h("option", { value: j, selected: st[which] === j ? true : null }, j === 0 ? "Today" : S.fromChange ? "End state" : `R${j} ${short(S) === S.name ? "" : ""}${S.heading ? S.heading.replace(/^[^:]*:\s*/, "") : S.name}`)));
    const pane = (which) => { const box = h("div", { class: "rel-pane" }); return { box, head: h("div", { class: "rel-pane-h" }, select(which)) }; };
    const A = pane("a"), B = pane("b");
    wrap.append(h("div", { class: "rel-two" }, h("div", {}, A.head, A.box), h("div", {}, B.head, B.box)));
    const diff = h("div", { class: "rel-diff" });
    const SA = STATES[st.a], SB = STATES[st.b];
    const apps = Object.keys(SB.apps).filter((k) => (SA.apps[k] || "exists") !== (SB.apps[k] || "exists"));
    const cons = Object.keys(SB.contracts).filter((c) => SA.contracts[c] !== SB.contracts[c]);
    const delivered = SB.delivers.filter((r) => !SA.delivers.includes(r));
    diff.append(h("h3", {}, `From ${st.a === 0 ? "Today" : SA.fromChange ? "the end state" : "R" + st.a} to ${st.b === 0 ? "Today" : SB.fromChange ? "the end state" : "R" + st.b}`),
      apps.length ? h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, "Apps"), h("span", {}, apps.map((k) => refChip(k, h("span", { class: "rid" }, `${STATUS_WORD[SA.apps[k] || "exists"]} → ${STATUS_WORD[SB.apps[k] || "exists"]}`))))) : h("div", { class: "muted small" }, "No app's status differs."),
      cons.length ? h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, "Contracts"), h("span", {}, cons.map((c) => refChip(c, h("span", { class: "rid" }, `${SA.contracts[c]} → ${SB.contracts[c]}`))))) : null,
      delivered.length ? h("div", { class: "rc-row" }, h("span", { class: "rc-l" }, "Delivered between"), h("span", {}, delivered.map((r) => refChip(r)))) : null);
    wrap.append(KEY.el(), diff);
    wrap.drawMaps = () => { drawMap(A.box, st.a, { max: 0.8 }); drawMap(B.box, st.b, { max: 0.8 }); };
    return wrap;
  }

  /* ------------------------------------------------------------ the view, the map lens, and lookups */
  function render(main) {
    const title = typeof Nav !== "undefined" ? Nav.title("Releases") : "Releases";
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, title),
      h("p", {}, R.count ? `${plural(R.count, "release")} planned on the releases page. Move along the timeline to see the system after each one; each release lists what it delivers.` : "Today and the end state.")),
      h("div", { class: "spacer" }), typeof Nav !== "undefined" ? Nav.pageActions() : null));
    const box = h("div", { class: "rel-body", id: "board" });
    main.append(box);
    body(box);
  }
  function mapLens(board) { board.classList.add("board-releases"); body(board, { max: 0.95, scrollCards: false }); }
  function deliveringRequirement(req) {
    const out = [];
    STATES.forEach((S, j) => (S.rows || []).forEach((r) => { if (r.requirement === req) out.push({ index: j, name: S.heading || S.name, criteria: criteriaText(r) }); }));
    return out;
  }
  function open(j) { st.at = clamp(j, 0, STATES.length - 1); st.compare = false; }
  return { render, mapLens, drawMap, deliveringRequirement, open, changes, STATES, st, appWord };
})();
View("releases", { label: "Releases", title: "The system before and after each release", render: Releases.render, count: () => String(D.releases.count) });
