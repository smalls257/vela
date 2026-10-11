/* #selftest: the page checks itself, as a person would use it, and writes the report to the console and to
   <body data-selftest>. Search must rank exactly as `planner query search` does (the CLI's answers are embedded at
   build time); the two live-call paths are run for real and their clicks counted; every view is rendered and
   checked against the data; every light drawn must be attention.py's. Any failure line starts with FAIL. */
const SelfTest = (() => {
  // Every step renders synchronously, so the checks only yield to microtasks. They never wait on a timer or a
  // frame: under headless Chrome's --virtual-time-budget, timers stop firing once the page's animation loops run.
  const frames = () => Promise.resolve();
  const out = [];
  const ok = (cond, good, bad) => { out.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + out[out.length - 1]); };
  const presentStep = () => $("#overlay").classList.contains("present") && !$("#overlay").hidden ? $("#overlay").dataset.step : "";
  const buttonText = (b) => (b ? b.textContent.trim() : "none");

  /* A query that names two apps or parties a flow joins: this vault's version of "how does Coach talk to Brightwater". */
  function pairQuery() {
    for (const f of D.flows) for (const stp of f.steps) for (const m of stp.messages) {
      const c = CONTRACT[m.contract]; if (!c) continue;
      const a = titleOf(c.provider), b = titleOf(c.consumers[0]);
      if (a && b && a !== b) return { q: `how does ${b} talk to ${a}`.toLowerCase(), contract: c.id };
    }
    return null;
  }
  async function livePaths() {
    // Path 1: "how does a reader place a paper trade?" gets to the played flow, ready to present.
    // The trading vault's own question; any other vault asks after its first flow in the flow's own words.
    const q1 = FLOW[Search.type("how does a reader place a paper trade")[0]] ? "how does a reader place a paper trade" : D.flows[0] ? "how does " + E[D.flows[0].key].title.toLowerCase() : null;
    if (q1) {
      Flows.closePresent(); go("lights", { reset: true }); showView("map"); await frames();
      const keys = Search.type(q1);
      Search.pick(0); await frames();
      const key = keys[0], isFlow = !!FLOW[key];
      const btn = $("#present-btn");
      ok(isFlow && App.view === "flows" && Flows.st.key === key && !!btn, `path 1 "${q1}": search, Enter → the played flow ${key} (${titleOf(key)}), view ${App.view}, Present button ready`,
        `path 1 "${q1}": first result ${key} (${titleOf(key)}), view ${App.view}, present button ${!!btn}`);
      if (btn) { btn.click(); await frames(3); }
      ok(!!presentStep(), `path 1: 1 click on Present → presenting ${titleOf(key)} at step ${presentStep()}; clicks after the search: 1`, "path 1: Present did not open");
      Flows.closePresent();
    } else out.push("skip path 1: this vault has no flow pages");
    // Path 2: "how does Coach talk to Brightwater?" gets to the contract, and presenting from that step.
    const pq = APPS["APP-coach"] && D.map.parties.some((p) => p.title === "Brightwater") && D.flows.length ? { q: "how does coach talk to brightwater", contract: "CON-003" } : pairQuery();
    if (pq) {
      go("lights", { reset: true }); showView("map"); await frames();
      const keys = Search.type(pq.q);
      const first = $("#results .result"), group = first ? first.previousElementSibling && first.previousElementSibling.textContent : "";
      Search.pick(0); await frames(3);
      const key = keys[0];
      const btn = $$("#panel .present-btn")[0];
      ok(key === pq.contract && App.view === "map" && !!btn, `path 2 "${pq.q}": search, Enter → ${key} ${titleOf(key)} (group "${(group || "").split("·")[0].trim()}"), on the map, panel offers "${buttonText(btn)}"`,
        `path 2 "${pq.q}": first result ${key}, wanted ${pq.contract}; view ${App.view}; present button ${buttonText(btn)}`);
      if (btn) { btn.click(); await frames(3); }
      const wantStep = btn ? (buttonText(btn).match(/step (\d+)/) || [0, "1"])[1] : "?";
      ok(presentStep() === String(wantStep), `path 2: 1 click → presenting from step ${presentStep()}, the first step that uses ${key}; clicks after the search: 1`, `path 2: presenting at "${presentStep()}", wanted step ${wantStep}`);
      Flows.closePresent();
    } else out.push("skip path 2: no flow sends over a contract between two named ends");
  }
  async function thread() {
    const app = D.map.apps.find((a) => D.apps[a.key].questions.length);
    if (!app) { out.push("skip thread: no app is held by an open question"); return; }
    Nav.home(); go(app.key, { reset: true }); await frames();
    const q = D.apps[app.key].questions[0].id, owner = UNKNOWN[q].ownerKey ? "owner:" + UNKNOWN[q].ownerKey : null;
    const path = [app.key];
    const click = (k) => { const a = $(`#panel [data-ref="${CSS.escape(k)}"]`); if (a) { a.click(); path.push(k); return true; } return false; };
    click(q); if (owner) click(owner);
    const crumbs = $$("#panel .crumbs a, #panel .crumbs .cur").length;
    ok(path.length >= 2 && crumbs === path.length + 1, `thread ${path.join(" › ")}: crumbs ${crumbs} (Lights + ${path.length}), panel "${($("#panel h2") || {}).textContent}"`, `thread broke at ${path.join(" › ")}; crumbs ${crumbs}`);
    $("#panel .crumbs a").click(); await frames();
    ok(($("#panel h2") || {}).textContent === "What needs you", "the Lights crumb returns the panel to its home, the lights", "the Lights crumb did not return home");
  }
  async function views() {
    // Map, cockpit: one lamp per app, party, contract and flow, each lit exactly as attention.lights says.
    go("lights", { reset: true });
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; rerender(); await frames(3);
    const lamps = $$("#board g.hit:not([data-agg])");
    const want = D.nodes.length + D.map.contracts.filter((c) => c.consumers.some((k) => k !== c.provider && NODE[k]) && NODE[c.provider]).length + D.flows.length;
    const wrong = lamps.filter((g) => { const lv = D.lights[g.dataset.key] ? D.lights[g.dataset.key].level : "dark"; return !g.classList.contains(lv === "dark" ? "dark" : lv); });
    ok(lamps.length >= want - 1 && !wrong.length, `map, cockpit: ${lamps.length} lamps, each lit as attention.lights says; ${$$("#board g.lit").length} lit`, `map, cockpit: ${lamps.length} lamps (wanted ${want}); ${wrong.length} disagree with attention.lights: ${wrong.slice(0, 3).map((g) => g.dataset.key).join(", ")}`);
    ok($$("#panel .light-row").length === litSubjects().length + D.above.length, `panel home: ${litSubjects().length} lights, most urgent first, and ${D.above.length} held above the map`, "panel home lights do not match attention.ranked");
    ok(D.above.length === $$(".above .cap").length, `held above the map: ${D.above.length} shown of ${D.above.length}`, "the held-above strip drops some");
    if (D.nodes.length > 0) {
      go(D.nodes[0].key, { reset: true }); await frames();
      ok(!!$("#panel-mini .mini-ring"), `minimap: "you are here" ringed at ${titleOf(D.nodes[0].key)}`, "minimap: no you-are-here ring");
    } else {
      out.push("skip minimap: vault has no apps");
    }
    {  // a corridor routed through two coincident points used to draw as NaN, and Chrome logged an error for each
      const paths = $$("#panel-mini path"), nan = paths.filter((p) => (p.getAttribute("d") || "").includes("NaN"));
      ok(!nan.length, `minimap: ${paths.length} corridors drawn, none with NaN coordinates`, `minimap: ${nan.length} of ${paths.length} corridors have NaN coordinates, so they are not drawn`);
    }
    MapView.st.lens = "transit"; rerender(); await frames(3);
    ok(!D.flows.some((f) => f.segments.length) || $$("#board g.lane").length > 0, `map, line map: ${$$("#board g.lane").length} line segments, ${$$("#board g.station").length} stations, ${$$("#board g.train").length} trains`, "map, line map: no lines drawn");
    MapView.st.lens = "matrix"; rerender(); await frames();
    const matrixTable = $("table.dsm");
    if (matrixTable) {
      ok(!!matrixTable, `map, matrix: ${$$("table.dsm button.cell").length} cells, lit by the same lights`, "map, matrix: no table");
      // the frozen edges: scroll the board down and across, and the head row, the row names and the corner stay where they were
      const board = $("#board"), col = $("table.dsm th.col"), rowName = $("table.dsm tbody th.row"), corner = $("table.dsm th.corner");
      const before = [col.getBoundingClientRect().top, rowName.getBoundingClientRect().left, corner.getBoundingClientRect().top, corner.getBoundingClientRect().left];
      board.scrollTop = board.scrollHeight; board.scrollLeft = board.scrollWidth;
      const moved = { down: board.scrollTop, across: board.scrollLeft };
      const after = [col.getBoundingClientRect().top, rowName.getBoundingClientRect().left, corner.getBoundingClientRect().top, corner.getBoundingClientRect().left];
      const held = before.every((v, i) => Math.abs(v - after[i]) < 1.5);
      const cut = $$("table.dsm th.col a").every((a) => a.title === a.textContent);
      ok(held && cut, `matrix: ${moved.down || moved.across ? `scrolled ${moved.down} px down and ${moved.across} px across, the head, row names and corner stay put` : "it fits the board, so nothing scrolls"}; every column name carries its full name on hover`,
        `matrix frozen edges moved: ${before.map(Math.round)} → ${after.map(Math.round)}; names with a tooltip ${cut}`);
      board.scrollTop = 0; board.scrollLeft = 0;
    }
    MapView.st.lens = null; MapView.st.group = null; rerender(); await frames(2);
    out.push(`map opens on the ${MapView.lens()} lens, grouped ${MapView.group()}, for ${D.nodes.length} boxes`);
    // Flows: every flow plays; the scrubber has one tick per step; the rehearse drill scores a perfect attempt in full.
    for (const f of D.flows) {
      Flows.select(f.key, 0); await frames(2);
      const ticks = $$("#scrub .tick").length, pins = $$("#scrub .tick .q").length, wantPins = f.steps.reduce((n, x) => n + x.unknowns.length, 0);
      ok(App.view === "flows" && ticks === f.steps.length && pins === wantPins && !!$(".stage-canvas"), `flows, ${f.key}: played, ${ticks} steps on the scrubber, ${pins} ${pins === 1 ? "question" : "questions"} pinned at their steps`, `flows, ${f.key}: ${ticks} ticks for ${f.steps.length} steps, ${pins} pins for ${wantPins}`);
      const r = Rehearse.selfCheck(f.key);
      ok(r.got === r.of, `rehearse, ${f.key}: a perfect attempt scores ${r.got} of ${r.of}`, `rehearse, ${f.key}: a perfect attempt scored ${r.got} of ${r.of}`);
    }
    out.push(`clip export: ${FlowKit.clipFormat() ? FlowKit.clipFormat().mime : "not available in this browser"}`);
    // Who to ask: every open question is in a rack, or counted as folded; strip edges are attention.hold's.
    showView("asks"); await frames();
    const strips = $$(".strip:not(.resolved)"), open = D.asks.filter((u) => u.state === "open").length;
    const folded = $$(".later[data-later]").reduce((n, b) => n + (+((b.textContent.match(/\+ (\d+)/) || [0, 0])[1])), 0);
    const off = strips.filter((x) => x.dataset.level !== ASK[x.dataset.id].light.level);
    ok(strips.length + folded === open && !off.length, `who to ask: ${strips.length} strips shown and ${folded} folded, ${open} open in all, each edge lit by attention.hold`, `who to ask: ${strips.length} shown + ${folded} folded ≠ ${open} open; ${off.length} edges disagree`);
    if (open) {
      const u = D.asks.find((x) => x.state === "open"), before = JSON.stringify(Asks.marks());
      Asks.marks().moved[u.id] = "@someone-else";
      const lines = Asks.trayLines().map((l) => l.raw);
      delete Asks.marks().moved[u.id];
      ok(lines.some((l) => l === `${u.id}: - **Ask:** @someone-else`) && JSON.stringify(Asks.marks()) === before, `who to ask: moving ${u.id} proposes "- **Ask:** @someone-else" in the tray and writes nothing`, "who to ask: the tray did not propose the Ask line");
      const inferred = D.asks.filter((x) => x.ask.inferred).length;
      out.push(`who to ask: ${D.asks.filter((x) => x.ask.rule.startsWith("recorded")).length} racks from Ask lines, ${inferred} guessed from Owner lines and marked`);
    }
    showView("garden"); await frames();
    ok($$(".plot").length === Garden.trees.length, Garden.trees.length ? `why: ${Garden.trees.length} decisions in the bed, one on the sheet` : "why: no decision records its options, and the view says so", `why: ${$$(".plot").length} plots for ${Garden.trees.length} decisions`);
    showView("progress"); await frames();
    ok($$(".pages table.t tr.click").length >= D.progress.rows.length, `progress: ${D.progress.rows.length} apps on the ladder, ${$$(".due-chart .bar-r").length} due bars`, "progress: rows missing");
    showView("trace"); await frames();
    ok($$(".cap-card").length === D.trace.capabilities.length, `trace: ${D.trace.capabilities.length} capability cards, ${D.trace.gaps.length} gaps`, "trace: cards missing");
    out.push("assets: " + Assets.status);
  }
  /* ------------------------------------------------------------ the second pass: navigation, doors, scale, effects, releases */
  async function navigation() {
    const order = ["goals", "constraints", "context", "strategy", "capabilities", "releases", "apps", "flows", "concerns", "decisions", "unknowns", "glossary", "epics"];
    Nav.refresh();
    const shown = [...new Set($$("#side .side-link").map((b) => b.dataset.section))];
    ok(JSON.stringify(shown) === JSON.stringify(order), `sidebar: ${shown.length} sections in the vault's order, with What needs you and ${Roles.ROLES.length - 1} front doors above`, `sidebar order ${shown.join(",")}`);
    const kids = $$("#side .side-kid[data-section=apps]").length, flowKids = $$("#side .side-kid[data-section=flows]").length;
    ok((kids === D.map.apps.length || !Nav.st.expanded.has("apps")) && (flowKids === D.flows.length || !Nav.st.expanded.has("flows")), `sidebar lists each app (${kids}) and each flow (${flowKids})`, `sidebar lists ${kids} apps of ${D.map.apps.length}, ${flowKids} flows of ${D.flows.length}`);
    const bad = [], seen = [];
    for (const id of order) {
      Nav.open(id); await frames();
      const s = Nav.SECTIONS[id], pk = Nav.sectionPage();
      const reader = $("#panel .reader") || $("#main .reader");
      const visual = App.view !== "doc" ? !!$("#main").children.length : !!$("#main .reader");
      const links = reader ? $$("a[data-ref]", reader) : [], dead = links.filter((a) => !ent(a.dataset.ref) && !a.classList.contains("ref-dead"));
      const decision = id === "decisions" && $("#panel .open-page");  // the garden opens its first decision beside it
      if (s.page && ((!reader && !decision) || !visual || dead.length)) bad.push(`${id}: reader ${!!reader}, visual ${visual}, ${dead.length} dead links`);
      if (!s.page && !$("#main").textContent.trim()) bad.push(`${id}: no page and nothing says so`);
      const nulls = [$("#main"), $("#panel")].flatMap((root) => { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), found = []; while (w.nextNode()) if (w.currentNode.nodeValue.trim() === "null") found.push(w.currentNode); return found; });
      if (nulls.length) bad.push(`${id}: ${nulls.length} stray "null" text`);
      seen.push(`${id}→${App.view}${pk && App.root !== "lights" ? "+page" : ""}`);
    }
    ok(!bad.length, `section pages: each opens its visual with its page beside it, every link inside the explorer (${seen.join(", ")})`, "section pages: " + bad.join("; "));
    if (D.map.apps.length) {
      const app = D.map.apps[0].key;
      Nav.open("apps", app); await frames();
      const shownN = +($("#board") || { dataset: {} }).dataset.shown, want = 1 + new Set([...MapGroups.neighbours(app).uses.keys(), ...MapGroups.neighbours(app).usedBy.keys()]).size;
      ok(MapView.st.focus === app && shownN === want && App.root === "read:" + app, `Apps › ${titleOf(app)}: the map focused on it with its ${want - 1} direct neighbours only, its page in the panel`, `focus on ${app}: shown ${shownN}, wanted ${want}; root ${App.root}`);
      const btn = $("#panel .open-page") || null;
      go(app, { reset: true }); await frames();
      const open = $("#panel .open-page");
      if (open) open.click();
      await frames();
      ok(!!open && App.trail[App.trail.length - 1] === Reader.keyFor(app) && !!$("#panel .reader"), `"Open the page" on ${titleOf(app)} reads its page in the panel`, `"Open the page" did not open the reader (${!!btn})`);
    }
    if (D.flows.length) { Nav.open("flows", D.flows[0].key); await frames(); ok(App.view === "flows" && Flows.st.key === D.flows[0].key, `Flows › ${E[D.flows[0].key].title}: played`, "flow child did not play"); }
  }
  async function doors() {
    if (!D.map.apps.length) { out.push("skip front doors: vault has no apps"); return; }
    const lines = [];
    for (const [id] of Roles.ROLES.slice(1)) {
      Nav.role(id); await frames();
      const door = $(".door"), grid = $(".door-grid"), cards = $$(".door-card").length;
      const fits = door && door.scrollHeight <= door.clientHeight + 2, cut = $$(".door-card").filter((c) => c.scrollHeight > c.clientHeight + 2).length;
      lines.push(`${id} ${cards} cards${fits ? "" : " (overflows)"}${cut ? `, ${cut} scrolling inside` : ""}`);
      if (!door || !grid || cards < 3) { ok(false, "", `door ${id}: ${cards} cards`); return; }
    }
    ok(!lines.some((l) => l.includes("overflows")), `front doors: ${lines.join(", ")}, each on one screen`, `front doors: ${lines.join(", ")}`);
    Nav.role("eng"); await frames();
    ok(!!$(".door-pick .chip.on") || !D.map.apps.length, `engineering door: an app picked, its slice of ${(D.slices[Roles.st.app] || []).length} items from handoff.slice_of`, "engineering door has no app picked");
  }
  async function scale() {
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.focus = null;
    if (D.map.apps.some((a) => a.domain)) {
      MapView.st.group = "domain"; MapView.st.open.clear(); MapView.st.shut.clear(); rerender(); await frames();
      const groups = MapGroups.groups("domain"), board = $("#board"), closed = +board.dataset.closed;
      const wantClosed = D.map.apps.length > MapView.CLUSTER_PAST ? groups.length : 0;
      const wrong = $$("#board .cluster-lamp").filter((g) => { const gr = groups.find((x) => x.key === g.dataset.group); const w = gr.members.map(levelOf).sort((p, q) => rank(q) - rank(p))[0]; return g.dataset.level !== w; });
      ok(closed === wantClosed && !wrong.length, `group by domain: ${groups.length} clusters, ${closed} closed (${D.map.apps.length} apps), each closed one lit with its apps' worst light`, `domain: ${closed} closed, wanted ${wantClosed}; ${wrong.length} wrong lights`);
      const g0 = groups[0];
      if (closed) { const lampEl0 = $(`#board .cluster-lamp[data-group="${CSS.escape(g0.key)}"]`); lampEl0.dispatchEvent(new MouseEvent("click", { bubbles: true })); await frames();
        const inside = g0.members.filter((k) => $(`#board g.hit[data-key="${CSS.escape(k)}"]`)).length;
        ok(inside === g0.members.length, `a closed cluster opens in place: ${g0.label} shows its ${inside} apps`, `opening ${g0.label} showed ${inside} of ${g0.members.length}`); }
      for (const open of [false, true]) {
        MapGroups.all(open); rerender(); await frames();
        const bad = overlaps();
        ok(!bad.length, `group by domain, every cluster ${open ? "open" : "closed"}: ${$$(OVERLAP_PARTS).length} boxes and labels, no two overlap`, `group by domain (${open ? "open" : "closed"}): ${bad.length} overlaps, such as ${bad.slice(0, 3).join("; ")}`);
      }
      MapView.st.open.clear(); MapView.st.shut.clear();
    } else out.push("skip group by domain: no app page has a domain");
    MapView.st.group = "capability"; rerender(); await frames();
    const regions = MapGroups.groups("capability"), apps = D.nodes.filter((n) => n.kind === "app").map((n) => n.key);
    const once = apps.every((k) => regions.filter((r) => r.members.includes(k)).length === 1), ghosts = regions.reduce((n, r) => n + r.ghosts.length, 0);
    ok(once, `group by capability: ${regions.length} regions, every app in exactly one, ${plural(ghosts, "chip")} where it also belongs`, "an app is drawn in more than one region");
    // nothing sits on anything: every box, lamp, count, name, chip, tab and toggle, measured as drawn, closed and open
    for (const open of [false, true]) {
      MapGroups.all(open); rerender(); await frames();
      const bad = overlaps();
      ok(!bad.length, `group by capability, every region ${open ? "open" : "as it opens"}: ${$$(OVERLAP_PARTS).length} boxes and labels, no two overlap`,
        `group by capability (${open ? "open" : "as it opens"}): ${bad.length} overlaps, such as ${bad.slice(0, 3).join("; ")}`);
    }
    MapView.st.open.clear(); MapView.st.shut.clear();
    MapView.st.group = null; MapView.st.open.clear(); MapView.st.shut.clear(); rerender();
  }
  const OVERLAP_PARTS = "#board svg.grouped g.hit, #board svg.grouped .cluster-names text, #board svg.grouped .also-chip, #board svg.grouped .also-tab, #board svg.grouped .cluster-toggle";
  /* Pairs of drawn parts whose boxes intersect by more than a pixel, as "<a> on <b>". A part's own children are not parts. */
  function overlaps() {
    const parts = $$(OVERLAP_PARTS).filter((el) => !el.parentElement.closest(".also-chip, .also-tab, .cluster-toggle, g.hit")).map((el) => {
      const b = el.getBBox();
      return { el, b, name: el.dataset.key || el.textContent.trim().slice(0, 24) };
    });
    const out = [];
    for (let i = 0; i < parts.length; i++) for (let j = i + 1; j < parts.length; j++) {
      const a = parts[i].b, c = parts[j].b;
      if (a.x < c.x + c.width - 1 && c.x < a.x + a.width - 1 && a.y < c.y + c.height - 1 && c.y < a.y + a.height - 1) out.push(`${parts[i].name} on ${parts[j].name}`);
    }
    return out;
  }
  async function effects() {
    const was = FX.on;
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; FX.set(false); await frames();
    const halos = $$("#board .halo").length, plain = document.documentElement.classList.contains("plain");
    const lampsRight = $$("#board g.hit:not([data-agg])").every((g) => { const lv = D.lights[g.dataset.key] ? D.lights[g.dataset.key].level : "dark"; return g.classList.contains(lv === "dark" ? "dark" : lv); });
    let stored = null; try { stored = localStorage.getItem("explorer.effects"); } catch (e) { console.warn("[selftest] no storage:", e.message); }
    const anim = document.getAnimations ? document.getAnimations().filter((a) => a.playState === "running").length : 0;
    ok(plain && !halos && lampsRight && stored === "plain" && !anim && reducedMotion(), `effects Plain: no glow (${halos} halos), ${anim} running animations, every lamp still lit as attention.lights says, remembered as "${stored}"`, `Plain: class ${plain}, ${halos} halos, lamps right ${lampsRight}, stored ${stored}, ${anim} animations`);
    if (D.flows.length && D.flows[0].hops.length) {
      const r = Motion.trace(D.flows[0].key);
      ok(r.drawn > 0 && $$("#board .m-badge").length === r.drawn, `trace in Plain: ${E[D.flows[0].key].id}'s ${r.drawn} hops lit at once, each numbered`, `trace drew ${r.drawn}, ${$$("#board .m-badge").length} badges`);
    }
    FX.set(true); await frames();
    ok(!document.documentElement.classList.contains("plain") && $$("#board .halo").length === $$("#board g.hit.lit:not([data-agg])").length, `effects On again: ${$$("#board .halo").length} lit lamps glow`, "effects On did not restore the glow");
    const provider = D.map.apps.find((a) => D.map.contracts.some((c) => c.provider === a.key && c.consumers.some((k) => k !== a.key)));
    if (provider) {
      const want = new Set(D.map.contracts.filter((c) => c.provider === provider.key).flatMap((c) => c.consumers).filter((k) => k !== provider.key));
      const R = Motion.rings(provider.key), r1 = new Set(R.rings[0] || []);
      ok([...want].every((k) => r1.has(k)) && r1.size === want.size, `ripple from ${provider.title}: ring 1 is its ${want.size} consumers, ${plural(R.rings.length, "ring")} in all`, `ripple ring 1 ${[...r1].join(",")} ≠ ${[...want].join(",")}`);
    }
    FX.set(was);
    Motion.clear();
  }
  /* The panel's room: hide it and the main area widens, a pick brings it back, a drag stays between the minimum and
     60% of the window, the choice is in storage as a reload would read it, and the views that fit the main area
     (the map, the matrix's frozen edges) still hold after every change. */
  async function panelRoom() {
    const hidden0 = PanelSize.hidden, want0 = PanelSize.wanted;
    const mainW = () => $("#main").getBoundingClientRect().width, panelW = () => $("#panel").getBoundingClientRect().width;
    const stored = () => ({ hidden: Settings.read("explorer.panel.hidden"), width: Number(Settings.read("explorer.panel.width")) || null });
    // fit() draws at 0.15 of the drawing at the smallest, so a board narrower than that overflows by design
    const fitted = () => {
      const b = $("#board"), svg = b && $("svg.cockpit", b);
      if (!svg) return true;  // an empty vault draws no map
      const r = b.getBoundingClientRect(), v = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
      return (v.right <= r.right + 1 && v.bottom <= r.bottom + 1) || v.width / vb.width <= 0.151;
    };
    PanelSize.hide(false); PanelSize.setWidth(null, { now: true });
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; rerender(); await frames();
    const open = mainW(), openPanel = panelW();
    PanelSize.hide(true); await frames();
    ok($("#panel").offsetParent === null && mainW() > open + openPanel * 0.9 && !$("#panel-tab").hidden && stored().hidden === "1",
      `panel: hidden, the main area widens ${Math.round(open)} to ${Math.round(mainW())} px, the tab is on the edge, and the choice is stored`, `panel hide: main ${Math.round(open)} to ${Math.round(mainW())}, panel shown ${$("#panel").offsetParent !== null}, tab hidden ${$("#panel-tab").hidden}`);
    ok(fitted(), "panel: the map still fits its board with the panel hidden", "panel hidden: the map overflows its board");
    const pick = D.nodes[0] ? D.nodes[0].key : null;
    if (pick) { go(pick, { reset: true }); await frames(); ok($("#panel").offsetParent !== null && !PanelSize.hidden && stored().hidden === "0", `panel: picking ${titleOf(pick)} while hidden opens it again`, "panel: a pick did not reopen the hidden panel"); }
    else PanelSize.hide(false);
    const grip = $("#panel-grip");
    PanelSize.setWidth(10, { now: true });
    const low = Math.round(panelW());
    PanelSize.setWidth(100000, { now: true });
    const high = Math.round(panelW()), cap = PanelSize.max();
    ok(low === PanelSize.MIN && high === cap && +grip.getAttribute("aria-valuenow") === high && +grip.getAttribute("aria-valuemin") === PanelSize.MIN && +grip.getAttribute("aria-valuemax") === cap && grip.getAttribute("role") === "separator" && grip.getAttribute("aria-orientation") === "vertical",
      `panel: resize clamps to ${low} px at the least and ${high} px (60% of ${innerWidth}) at the most, and the handle reports both`, `panel resize: least ${low} (want ${PanelSize.MIN}), most ${high} (want ${cap}), aria-valuenow ${grip.getAttribute("aria-valuenow")}`);
    PanelSize.setWidth(PanelSize.MIN + 100, { now: true });
    grip.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true, cancelable: true }));
    const grown = Math.round(panelW());
    grip.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true }));
    const back = Math.round(panelW());
    ok(grown === PanelSize.MIN + 100 + PanelSize.STEP && back === PanelSize.MIN + 100, `panel: the handle's arrow keys move it ${PanelSize.STEP} px each way`, `panel arrows: ${PanelSize.MIN + 100} to ${grown} to ${back}`);
    const wide = Math.round(panelW());
    ok(stored().width === wide, `panel: width ${wide} px is in storage, so a reload reads it back`, `panel width in storage ${stored().width}, on screen ${wide}`);
    await frames();
    ok(fitted(), `panel: the map still fits its board at ${wide} px of panel`, "panel resized: the map overflows its board");
    MapView.st.lens = "matrix"; rerender(); await frames();
    const board = $("#board"), col = $("table.dsm th.col"), rowName = $("table.dsm tbody th.row"), corner = $("table.dsm th.corner");
    if (col && rowName && corner) {
      const at = () => [col.getBoundingClientRect().top, rowName.getBoundingClientRect().left, corner.getBoundingClientRect().top, corner.getBoundingClientRect().left];
      const before = at();
      board.scrollTop = board.scrollHeight; board.scrollLeft = board.scrollWidth;
      const after = at();
      ok(before.every((v, i) => Math.abs(v - after[i]) < 1.5), "panel: the matrix's frozen head, row names and corner still hold after the resize", `matrix frozen edges moved after a panel resize: ${before.map(Math.round)} to ${after.map(Math.round)}`);
      board.scrollTop = 0; board.scrollLeft = 0;
    }
    PanelSize.setWidth(null, { now: true });
    ok(stored().width === null && PanelSize.wanted === null, "panel: the default width comes back, and storage forgets the width", "panel default: width still stored");
    PanelSize.setWidth(want0, { now: true }); PanelSize.hide(hidden0);
    MapView.st.lens = null; MapView.st.group = null; Nav.home(); await frames();
  }
  async function releases() {
    const S = Releases.STATES;
    ok(D.releases.count ? S.length === D.releases.count + 1 : S.length === 2 && S[1].fromChange, D.releases.count ? `releases: Today and ${plural(D.releases.count, "release")}, from planner.releases` : "releases: none planned, so Today against the end state from each app's change, and the page says so", "release states wrong");
    if (!D.map.apps.length) { out.push("skip releases timeline and compare: vault has no apps"); return; }
    Nav.open("releases"); await frames();
    const bad = [];
    for (let j = 0; j < S.length; j++) {
      const stop = $(`.rel-stop[data-state="${j}"]`); if (stop) { stop.click(); await frames(); }
      for (const g of $$(".rl-map .rl-node")) { const k = g.dataset.key; if (APPS[k] && g.dataset.status !== (S[j].apps[k] || "exists")) bad.push(`${j}:${k}`); }
    }
    ok(!bad.length && (D.releases.count || !!$(".rel-none")), `releases timeline: ${S.length} stops, every app drawn with its status in each state`, `release map disagrees at ${bad.slice(0, 4).join(", ")}`);
    const listed = new Set($$(".rel-card .rc-reqs .ref-chip").map((a) => a.dataset.ref));
    const want = new Set(S.flatMap((x) => (x.rows || []).map((r) => r.requirement)).filter(Boolean));
    ok([...want].every((r) => listed.has(r)), `what each release changes: ${want.size} requirements listed and linked`, "a delivered requirement is missing from the list");
    Releases.st.compare = true; Releases.st.a = 0; Releases.st.b = S.length - 1; rerender(); await frames();
    ok($$(".rel-compare .rl-map").length === 2, `compare: Today beside ${S[S.length - 1].fromChange ? "the end state" : "R" + (S.length - 1)}, side by side`, "compare did not draw two maps");
    Releases.st.compare = false; Releases.st.at = 0;
  }
  /* What a real vault lacks (no domains, releases, requirement rows, flows, Ask lines) is said where the reader looks,
     with the planner step that writes it; and a flow of inferred arrows says so once. */
  async function emptyStates() {
    const has = (root, text) => $$(".empty-state", root).some((e) => e.dataset.empty === text);
    const doorHas = async (role, text) => { Nav.role(role); await frames(); return has($(".door"), text); };
    if (D.map.apps.length) {
      Nav.home(); MapView.st.lens = "cockpit"; MapView.st.focus = null; MapView.st.group = "none"; rerender(); await frames();
      for (const [id, key, writer] of [["domain", "domain", "/planner:boundary"], ["capability", "capability", "/planner:requirements"]]) {
        const btn = $(`#main button[data-group="${id}"]`), off = !D.grouping[key];
        ok(!!btn && btn.disabled === off && (!off || btn.title.includes(writer)), `group by ${id}: ${off ? `disabled, the tooltip names ${writer}` : "offered"}`, `group by ${id}: ${btn ? `disabled ${btn.disabled}` : "no button"}, title "${btn ? btn.title : ""}", wanted ${off ? "off" : "on"}`);
      }
      MapView.st.group = null; rerender();
    } else out.push("skip group buttons: vault has no apps");
    if (!D.releases.count) {
      Nav.open("releases"); await frames();
      ok(has($("#main"), "No releases recorded yet.") && /04b-releases\.md/.test($("#main").textContent) && (!D.nodes.length || !!$("#main .rel-grid")),
        "releases: the empty state names 04b-releases.md and the Today against end-state comparison renders under it", "releases: no empty state, or no comparison under it");
      if (D.map.apps.length) { MapView.st.lens = "releases"; showView("map"); rerender(); await frames(); ok(has($("#board"), "No releases recorded yet."), "map Releases lens: the same empty state above the comparison", "map Releases lens has no empty state"); MapView.st.lens = null; }
    } else out.push("skip releases empty state: the vault records releases");
    if (D.map.apps.length) {
      Nav.role("exec"); await frames();
      ok(D.releases.count || has($(".door"), "No releases recorded yet."), "exec door: release timeline says no releases are recorded", "exec door: no releases and no empty state");
      ok(D.releases.count || await doorHas("product", "No releases recorded yet."), "product door: what each release delivers names 04b-releases.md", "product door: no empty state for releases");
      if (!D.trace.requirements.length && D.trace.capabilities.length) ok(await doorHas("product", "No requirement rows yet."), "product door: the requirement cards name /planner:requirements and /planner:allocate", "product door: no empty state for requirements");
      if (!D.trace.epics.length) ok(await doorHas("qa", "No epics yet."), "QA door: criteria cards name /planner:epics", "QA door: no empty state for epics");
    }
    if (!D.trace.requirements.length) { showView("trace"); await frames(); ok(has($("#main"), "No requirement rows yet.") && /allocate/.test($("#main .empty-state").textContent), "trace: requirement level says no requirement rows exist and which steps write them", "trace: no empty state for missing requirement rows"); }
    if (!D.flows.length) {
      showView("flows"); await frames();
      ok(has($("#main"), "No flows yet.") && $("#main .es-writer").textContent.includes("/planner:boundary"), "flows view: 'No flows yet', written by /planner:boundary", "flows view: no empty state");
      Search.type("how does it work"); await frames();
      ok(has($("#results"), "No flows yet.") && !$("#results").hidden, "search 'how does ...': says there are no flows rather than return nothing", "search 'how does': nothing said about missing flows"); Search.type("");
    } else {
      const all = D.flows.filter((f) => f.steps.some((x) => x.messages.length) && f.steps.every((x) => x.messages.every((m) => m.direction === "inferred"))), some = D.flows.filter((f) => !all.includes(f));
      const caption = (f) => { Flows.select(f.key, -1); return $$("#caption .cap-inferred").length; };
      const wrong = [...all.filter((f) => caption(f) !== 1), ...some.filter((f) => caption(f) !== 0)];
      ok(!wrong.length, `flow player: ${all.length} flows with every direction inferred carry the caption once, ${some.length} others carry none`, `inferred caption wrong on ${wrong.map((f) => f.key).join(", ")}`);
      if (all.length) { Flows.present(all[0].key, 0); await frames(2); const n = $$("#overlay .pc-inferred").length; Flows.closePresent(); ok(n === 1, "present: the inferred-direction line shows once", `present: ${n} inferred-direction lines`); }
    }
    if (D.asks.some((u) => !u.ask.recorded)) {
      showView("asks"); await frames();
      const racks = $$(".bay-head .not-asked").length, unrecorded = new Set(D.asks.filter((u) => !u.ask.recorded).map((u) => u.ask.key)).size;
      ok(racks === unrecorded, `who to ask: ${plural(racks, "rack")} labelled as placed by owner, since their questions have no Ask line`, `who to ask: ${racks} labelled racks, wanted ${unrecorded}`);
    } else out.push("skip not-asked racks: every question has an Ask line");
    Nav.home(); go("lights", { reset: true });
  }
  /* Ask Claude. On a file the page asks nothing of the network and offers a prompt to copy; served, it streams an answer
     into the Ask view. The served half plays a fake helper through Ask's injectable fetch, so no server or model is needed. */
  const sseResponse = (events) => {
    const bytes = new TextEncoder().encode(events.map((e) => "data: " + JSON.stringify(e) + "\n\n").join("")), cut = Math.floor(bytes.length / 3);
    return new Response(new ReadableStream({ start(c) { c.enqueue(bytes.slice(0, cut)); c.enqueue(bytes.slice(cut, cut * 2)); c.enqueue(bytes.slice(cut * 2)); c.close(); } }), { status: 200 });
  };
  async function askChecks() {
    await Ask.ready;
    const real = Ask.snapshot(), realFetch = window.fetch, seen = [];
    const onFile = location.protocol === "file:";
    if (onFile) {
      window.fetch = (...a) => { seen.push(String(a[0])); return realFetch(...a); };
      Search.type("how does a reader place a paper trade");
      $("#q").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      const rowText = ($("#results .r-ask") || { textContent: "" }).textContent;
      window.fetch = realFetch;
      ok(Ask.st.mode === "file" && real.fetches === 0 && !seen.length && !Ask.served() && document.documentElement.dataset.ask === "file",
        "ask on a file: the helper is not looked for, no request is made, Enter asks nothing", `ask on a file: mode ${Ask.st.mode}, ${real.fetches} fetches at boot, ${seen.length} during, served ${Ask.served()}`);
      ok(/Copy as a Claude Code prompt/.test(rowText) && /\/planner:explore/.test(rowText) && !$("#results .ask-btn b").textContent.includes("Ask Claude"),
        "ask on a file: the box offers Copy as a Claude Code prompt and says to run /planner:explore, with no Ask button", `ask on a file: row says "${rowText}"`);
      const prompt = Ask.promptFor("What does the demo deliver?");
      ok(prompt.startsWith("What does the demo deliver?") && prompt.includes("[[ID]]") && prompt.includes("Never create, edit or delete"),
        "ask on a file: the copied prompt is the question plus the citation rules", `ask on a file: prompt "${prompt.slice(0, 80)}"`);
      Ask.open(); await frames();
      ok(App.view === "ask" && !!$("#main .ask-empty") && /Copy as a prompt/.test($("#main .ask-actions").textContent) && !$("#main .think") && !seen.length,
        "ask on a file: #ask says Claude is not reachable and offers only Copy as a prompt, with no request", `ask on a file: view ${App.view}, actions "${($("#main .ask-actions") || { textContent: "" }).textContent}", ${seen.length} requests`);
      Ask.back(); await frames();
    } else {
      ok(real.mode === "served" && real.fetches === 1 && document.documentElement.dataset.ask === "served",
        "ask when served: the page found its helper with one /health request", `ask when served: mode ${real.mode}, ${real.fetches} fetches, flag ${document.documentElement.dataset.ask}`);
    }
    // served, against a fake helper
    const known = Object.keys(E).find((k) => idOf(k)), id = idOf(known), calls = [];
    if (!known) { out.push("skip ask, fake helper: this vault holds no ID for an answer to cite"); return; }
    const other = Object.keys(E).find((k) => idOf(k) && k !== known) || known, otherId = idOf(other);
    const withToc = Object.keys(D.reader).find((k) => E[k] && E[k].path && D.reader[k].toc.some((t) => t.level === 2));
    const heading = withToc ? D.reader[withToc].toc.find((t) => t.level === 2).text : "";
    const SCRIPT_OPEN = "<scr" + "ipt>", SCRIPT_CLOSE = "<" + "/scr" + "ipt>";  // spelled apart: the page's own script must not contain a tag a test counts
    // the answer is streamed in pieces that cut through the Markdown: a table, a nested list, a code block, chips, and a payload
    const answer = (turn) => [
      "## What it delivers\n\n", `- It delivers [[${id}]]\n  - nested, from [[${id}]]\n    - deeper still\n- Bare ID ${otherId} in a bullet\n\n`,
      "| Thing | Where |\n|---|---|\n", `| Alpha | [[${id}]] |\n\n`, "```js\nconst x = 1 < 2;\n```\n\n",
      withToc ? `See [[${E[withToc].path}#${heading}]]. ` : "",
      // the forms Claude copies from the vault's own pages: a path without .md, a bare file name, a heading, a |label
      withToc ? `Also [[${E[withToc].path.replace(/\.md$/, "")}|the stem link]] and [[${E[withToc].path.replace(/\.md$/, "").split("/").pop()}#${heading}|the base link]]. ` : "",
      withToc ? `Then [[${E[withToc].path}|It stays the news app, and for the first release gains coach screens: lessons, the stock list, progress, paper trades and delayed prices, all drawn from what Coach sends]]. ` : "",
      "But [[ZZZ-999]] is unknown, `inline` code, **bold**, *italic*, [a link](https://example.com) and [bad](javascript:alert(1)).\n\n",
      SCRIPT_OPEN + "window.__askpayload = 1" + SCRIPT_CLOSE + " <img src=x onerror=\"window.__askpayload = 2\"> ![pic](https://example.com/p.png)", ` (turn ${turn}).`];
    const fake = async (url, init) => {
      calls.push({ url: String(url), body: init && init.body ? JSON.parse(init.body) : null });
      if (url === "/health") return new Response(JSON.stringify({ ok: true, vault: "fake", model: "haiku", models: {}, claude: true, maxQuestion: 2000 }), { status: 200 });
      const turn = calls.filter((c) => c.url === "/ask").length, model = calls[calls.length - 1].body.model === "sonnet" ? "claude-sonnet-5-5" : "claude-haiku-4-5-20251001";
      return sseResponse([{ type: "start", model }, { type: "tool", name: "Grep", target: "demo" },
        ...answer(turn).map((text) => ({ type: "delta", text })), { type: "done", cost: 0.0123, session_id: "sess-" + turn + "-abcdef", model }]);
    };
    await Ask.detect(fake, { protocol: "http:", hostname: "127.0.0.1" });
    ok(Ask.served() && calls.length === 1 && calls[0].url === "/health", "ask, fake helper: /health found it, once", `ask, fake helper: mode ${Ask.st.mode}, calls ${calls.map((c) => c.url)}`);
    Ask.st.cur = null;  // the reader's kept conversations are not touched: this one is new, and restore() puts theirs back
    go(known, { reset: true }); await frames();
    const from = Nav.where();
    Search.type("What does it deliver?");
    ok(/Ask Claude/.test(($("#results .ask-btn") || { textContent: "" }).textContent), "ask, fake helper: the box offers Ask Claude", "ask, fake helper: no Ask Claude row");
    $("#q").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await Ask.st.last;
    const turn1 = calls.find((c) => c.url === "/ask");
    ok(turn1 && turn1.body.question === "What does it deliver?" && turn1.body.context.item === id, `ask, fake helper: Enter sent the question with its context (${turn1 && turn1.body.context.item})`, `ask, fake helper: sent ${JSON.stringify(turn1)}`);
    ok(App.view === "ask" && !!$("#main .ask-view") && /^#ask&c=/.test(location.hash) && !$("#panel .ask-a"), "ask, fake helper: asking from the box opens the Ask view in the main area (#ask&c=...), not the panel", `ask, fake helper: view ${App.view}, hash ${location.hash}`);
    const a1 = $("#main .ask-a");
    const bullet = a1 && $$("li", a1).find((li) => li.textContent.includes("Bare ID"));
    ok(!!a1 && !!$("h2", a1) && !!$("table th", a1) && !!$("ul ul ul", a1) && !!$("pre code", a1) && $("pre code", a1).textContent.includes("1 < 2") && !!$("strong", a1) && !!$("em", a1),
      "ask, fake helper: the answer is Markdown: a heading, a table, a list nested three deep, a code block, bold and italic", `ask, fake helper: answer html "${a1 && a1.innerHTML.slice(0, 300)}"`);
    ok(a1 && $$(`.ref-chip[data-ref="${CSS.escape(known)}"]`, a1).length >= 3 && !!$("table .ref-chip", a1) && !!$("ul ul .ref-chip", a1),
      `ask, fake helper: ${id} cited with [[ ]] is a chip in a bullet, a nested bullet and a table cell`, "ask, fake helper: [[ID]] chips are missing from the list or the table");
    ok(!!bullet && !!$(`.ref-chip[data-ref="${CSS.escape(other)}"]`, bullet) && !$("code", bullet), `ask, fake helper: ${otherId}, written bare, is a chip too`, `ask, fake helper: bare ID in "${bullet && bullet.textContent}"`);
    const dead = a1 && $(".ask-unknown", a1);
    ok(!!dead && /ZZZ-999/.test(dead.textContent) && /not in this vault/.test(dead.textContent), "ask, fake helper: [[ZZZ-999]] is flagged as not in this vault", "ask, fake helper: the unknown ID is not flagged");
    if (withToc) {
      const unknown = $$(".ask-unknown", a1).map((c) => c.textContent);
      const labelled = ["the stem link", "the base link"].every((l) => $$(`.ref-chip[data-ref^="${CSS.escape(withToc)}"], .ref-chip[data-ref^="read:${CSS.escape(withToc)}"]`, a1).some((c) => c.textContent.includes(l)));
      ok(unknown.length === 1 && labelled, "ask, fake helper: Obsidian links ([[path|label]], [[file#heading|label]]) are chips showing their label, and only ZZZ-999 is flagged",
        `ask, fake helper: flagged ${JSON.stringify(unknown)}, labelled chips ${labelled}`);
    }
    if (withToc) {
      const prose = $$(".ask-prose-link", a1).find((l) => l.textContent.startsWith("It stays the news app"));
      ok(!!prose && (prose.getAttribute("data-ref") || "").includes(withToc) && !a1.textContent.includes("[["),
        "ask, fake helper: a citation whose |label is a sentence is a link in the prose, and no raw [[ ]] is left", `ask, fake helper: long label link ${!!prose}, raw brackets ${a1.textContent.includes("[[")}`);
    }
    const links = a1 ? $$("a[href]", a1) : [];
    ok(a1 && !$("script", a1) && !$("img", a1) && window.__askpayload === undefined && a1.textContent.includes(SCRIPT_OPEN + "window.__askpayload = 1" + SCRIPT_CLOSE) && a1.textContent.includes("<img src=x")
      && links.length === 1 && links[0].getAttribute("href") === "https://example.com" && links[0].target === "_blank" && /noopener/.test(links[0].rel) && a1.textContent.includes("bad") && a1.textContent.includes("pic")
      && a1.getAttribute("aria-live") === "polite" && a1.getAttribute("aria-busy") === "false",
      "ask, fake helper: a script tag, an img with onerror, an image and a javascript: link are inert (shown as text, or only their text kept); a web link opens in a new tab", `ask, fake helper: payload became "${a1 && a1.innerHTML.slice(-400)}"`);
    const meta = $("#main .ask-meta");
    ok(/Haiku/.test(meta.textContent) && meta.textContent.includes("$0.0123"), "ask, fake helper: the answer names its model and cost", `ask, fake helper: meta "${meta.textContent}"`);
    ok(/Asking about:/.test($("#main .ask-about").textContent) && /\S/.test($("#main .ask-about b").textContent), `ask, fake helper: the view says what it asked about (${$("#main .ask-about b").textContent})`, "ask: no Asking about line");
    // a citation opens in the right panel and the conversation stays where it is
    PanelSize.hide(true);
    $(`#main .ask-a .ref-chip[data-ref="${CSS.escape(known)}"]`).click(); await frames();
    ok(App.view === "ask" && !!$("#main .ask-a") && App.focus === known && !PanelSize.hidden && /\S/.test($("#panel .p-head h2").textContent) && $("#panel .p-head h2").textContent.includes(E[known].title),
      `ask, fake helper: clicking the ${id} chip opens it in the panel (a hidden panel comes back) while the conversation stays in the main area`, `ask: after the click view ${App.view}, focus ${App.focus}, panel hidden ${PanelSize.hidden}`);
    if (withToc) {
      $$(".ask-a .ref-chip", $("#main")).find((c) => (c.getAttribute("data-ref") || "").startsWith("read:" + withToc)).click(); await frames();
      ok(App.view === "ask" && !!$("#panel .reader") && $("#panel .p-head h2").textContent === E[withToc].title, `ask, fake helper: a [[path#heading]] citation opens that page in the panel's reader (${E[withToc].path})`, `ask: page citation left the panel at "${$("#panel .p-head h2") && $("#panel .p-head h2").textContent}"`);
    }
    ok(/Asking about:/.test($("#main .ask-about").textContent) && $("#main .ask-about b").textContent.includes(id), "ask, fake helper: after a citation is opened the next question is about it", `ask: about line "${$("#main .ask-about").textContent}"`);
    $("#main .ask-clear").click(); await frames();
    ok(/No context/.test($("#main .ask-about").textContent), "ask, fake helper: the reader can clear the context", "ask: clearing did not clear");
    // a follow-up resumes the session; Shift+Enter is a newline, Enter sends; Think harder sends sonnet
    const box = $("#main .ask-input");
    box.value = "And then?"; box.dispatchEvent(new Event("input"));
    box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", shiftKey: true, bubbles: true, cancelable: true }));
    ok(calls.filter((c) => c.url === "/ask").length === 1, "ask, fake helper: Shift+Enter in the follow-up sends nothing", "ask: Shift+Enter sent");
    $("#main .think").click();
    box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    await Ask.st.last;
    const turn2 = calls.filter((c) => c.url === "/ask")[1];
    ok(turn2 && turn2.body.conversation_id === "sess-1-abcdef" && turn2.body.model === "sonnet" && !turn2.body.context.item && $$("#main .ask-turn").length === 2,
      "ask, fake helper: the follow-up resumed the first session, on Sonnet, with the cleared context left out, in the same conversation", `ask, fake helper: follow-up ${JSON.stringify(turn2 && turn2.body)}`);
    ok(/Sonnet/.test($$("#main .ask-meta")[1].textContent), "ask, fake helper: the second answer says Sonnet", "ask: the second answer does not name Sonnet");
    const kept = Settings.read(`explorer.ask.${D.vaultId}`) || "";
    ok(kept.includes("What does it deliver?") && kept.includes("And then?") && Ask.hash() === "ask&c=" + Ask.st.cur.id, "ask, fake helper: the conversation is kept in this browser for this vault, and its deep link names it", `ask: kept "${kept.slice(0, 120)}", hash ${Ask.hash()}`);
    // the composer stays on screen, at 800 x 600 as at any size
    const composer = $("#main .ask-compose").getBoundingClientRect();
    ok(composer.top >= 0 && composer.bottom <= innerHeight + 1 && $("#main .ask-log").getBoundingClientRect().height > 60, `ask: the composer is on screen with the conversation above it (${innerWidth}x${innerHeight})`, `ask: composer ${Math.round(composer.top)}..${Math.round(composer.bottom)} in a ${innerHeight} px window`);
    // every theme and Plain: the answer, a chip, a flag, a table head and a link stay legible; Plain stops the waiting dots
    const was = Theme.id, fx = FX.on, bad = [], dots = [];
    for (const [t, plain] of [...Theme.LIST.map((x) => [x.id, false]), [was, true]]) {
      Theme.set(t); FX.set(!plain);
      const a = $("#main .ask-a"), bg = getComputedStyle($("#main")).backgroundColor, colour = (el) => getComputedStyle(el).color;
      if (!a || colour(a) === bg || !$(".ask-unknown", a) || colour($(".ask-unknown", a)) === bg || colour($("th", a)) === getComputedStyle($("th", a)).backgroundColor || colour($("a[href]", a)) === bg) bad.push(plain ? "plain" : t);
      const wait = h("span", { class: "ask-wait" }, "x"); a.append(wait); dots.push(getComputedStyle(wait, "::after").animationName); wait.remove();
    }
    Theme.set(was); FX.set(fx);
    ok(!bad.length, "ask: the conversation draws in every theme and Plain", `ask: unreadable or missing in ${bad.join(", ")}`);
    ok(dots[dots.length - 1] === "none" && dots.slice(0, -1).every((d) => d !== "none"), "ask: the waiting dots move with effects on and stand still in Plain", `ask: dot animations ${dots}`);
    // Esc leaves, back to where the reader was; the conversation is waiting when they return
    $("#main .ask-input").dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true })); await frames();
    ok(App.view !== "ask" && !$("#main .ask-view") && !/^#ask/.test(location.hash) && App.section === from.section && App.view === from.view, "ask: Esc leaves the Ask view and lands where the reader was", `ask: after Esc view ${App.view}, section ${App.section}, hash ${location.hash}`);
    Nav.refresh();
    $(".side-ask").click(); await frames();
    ok(App.view === "ask" && $$("#main .ask-turn").length === 2 && /Ask Claude/.test($(".side-ask").textContent), "ask: the sidebar's Ask Claude door brings the conversation back", `ask: sidebar door left view ${App.view}, ${$$("#main .ask-turn").length} turns`);
    $(".ask-back").click(); await frames();
    ok(App.view === from.view, "ask: the breadcrumb goes back too", `ask: breadcrumb left view ${App.view}`);
    Ask.open(); await frames();
    const before = Ask.count();
    $$("#main .page-actions .btn").find((b) => b.textContent === "New conversation").click(); await frames();
    ok(!$("#main .ask-turn") && /New conversation/.test($("#main h1").textContent) && Ask.hash() === "ask" && Ask.count() === before, "ask: New conversation starts empty and keeps the old one", `ask: new conversation left ${$$("#main .ask-turn").length} turns, hash ${Ask.hash()}`);
    // Markdown on its own: partial input holds back what would flicker, and nothing unsafe survives
    const textOf = (md, growing) => { const box = h("div", {}); box.append(Markdown.render(md, growing)); return box; };
    ok(!$("table", textOf("| a | b |", true)) && !$("table", textOf("Intro\n\n| a | b |\n", true)) && !!$("table", textOf("| a | b |\n|---|---|\n| 1 | 2 |", true)) && textOf("Some prose that is still arri", true).textContent.trim() === "Some prose that is still arri",
      "markdown: a growing answer holds back a table header until its rule arrives, a lone marker, and nothing else", "markdown: partial table or prose was not handled");
    const evil = textOf("[x](javascript:alert(1)) [y](java&#x73;cript:alert(2)) [z](data:text/html,hi) ![i](http://x.test/a.png) <b onclick=1>raw</b> <iframe src=//x></iframe> [q](//evil.test)");
    ok(!$("a[href]", evil) && !$("img,iframe,b", evil) && evil.textContent.includes("<b onclick=1>raw</b>") && ["x", "y", "z", "q"].every((t) => evil.textContent.includes(t)),
      "markdown: javascript:, entity-hidden, data: and protocol-relative links lose the link, images are text, raw HTML is escaped", `markdown: unsafe html survived: ${evil.innerHTML}`);
    Ask.restore(real);
    Nav.home(); go("lights", { reset: true });
  }
  async function run() {
    out.length = 0;
    const parity = Search.parity(), bad = parity.filter((p) => !p.same);
    out.push(bad.length ? `FAIL SEARCH PARITY ${bad.length} of ${parity.length}: ` + JSON.stringify(bad) : `ok SEARCH PARITY ${parity.length} of ${parity.length} queries rank exactly as planner query search`);
    try { await livePaths(); await thread(); await views(); await navigation(); await doors(); await scale(); await effects(); await panelRoom(); await releases(); await emptyStates(); await askChecks(); }
    catch (e) { out.push("FAIL the self-test threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    out.push(window.__errors.length ? "FAIL JS ERRORS: " + window.__errors.join(" | ") : "ok no JS errors");
    const fails = out.filter((l) => l.startsWith("FAIL")).length;
    out.unshift(fails ? `SELFTEST FAIL: ${fails} of ${out.length} checks failed` : `SELFTEST OK: ${out.length} checks passed`);
    console.log(out.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  }
  return { run };
})();

/* ------------------------------------------------------------ Inside this app (inside.js): its checks
   A block of its own after SelfTest, so it merges apart from the checks above: it wraps SelfTest.run, adds its lines
   after the rest, and recounts the report's head. For every app with a design and one without: each level draws
   from its source, nothing drawn sits on anything else, the problems count is the reader's, every tab renders;
   then the vault and the design both ways, the challenge lamp, the deep link, the doors, every theme and Plain. */
(() => {
  const base = SelfTest.run;
  const PARTS = "#inside-stage svg .in-node, #inside-stage svg .in-label, #inside-stage svg .in-head";
  /* Pairs of drawn boxes, labels and headings whose boxes intersect by more than a pixel. */
  function overlaps() {
    const parts = $$(PARTS).filter((el) => !el.parentElement.closest(".in-node, .in-label")).map((el) => ({ b: el.getBBox(), name: el.dataset.key || el.dataset.stub || el.dataset.label || el.textContent.trim().slice(0, 24) }));
    const out = [];
    for (let i = 0; i < parts.length; i++) for (let j = i + 1; j < parts.length; j++) {
      const a = parts[i].b, c = parts[j].b;
      if (a.x < c.x + c.width - 1 && c.x < a.x + a.width - 1 && a.y < c.y + c.height - 1 && c.y < a.y + a.height - 1) out.push(`${parts[i].name} on ${parts[j].name}`);
    }
    return { n: parts.length, bad: out };
  }
  const nulls = (root) => { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n = 0; while (w.nextNode()) if (w.currentNode.nodeValue.trim() === "null") n++; return n; };
  async function checks(ok, out) {
    const apps = D.map.apps.map((a) => a.key), loaded = apps.filter((k) => D.designs[k]), bare = apps.find((k) => !D.designs[k]);
    if (!apps.length) { out.push("skip inside, components: vault has no apps"); return; }
    if (!loaded.length) out.push("skip inside, components: no --design was given to this build");
    for (const k of [...loaded, bare].filter(Boolean)) {
      const d = D.designs[k], name = titleOf(k);
      Inside.open(k, "context");
      const nb = MapGroups.neighbours(k), want = 1 + new Set([...nb.uses.keys(), ...nb.usedBy.keys()]).size, shown = +(($("#inside-stage #board") || { dataset: {} }).dataset.shown);
      ok(shown === want && $(".inside-crumbs .cur").textContent === "Context", `inside ${name}, context: it and its ${want - 1} direct neighbours, as the map's Focus`, `inside ${name}, context: shown ${shown}, wanted ${want}`);
      Inside.open(k, "containers");
      const c = D.containers[k], boxes = $$("#inside-stage .in-box.container").length;
      if (c && c.rows.length) {
        const o = overlaps();
        ok(boxes === c.rows.length && !o.bad.length, `inside ${name}, containers: ${boxes} from its page's table, ${o.n} boxes and labels, no two overlap`, `inside ${name}, containers: ${boxes} of ${c.rows.length}; overlaps ${o.bad.slice(0, 3).join("; ")}`);
      } else ok(!!$("#inside-stage .inside-chip-card"), `inside ${name}, containers: its page has none, and the chip says so`, `inside ${name}, containers: no table and no chip`);
      Inside.open(k, "components");
      if (!d) {
        const say = ($("#inside-stage .inside-chip-card") || { textContent: "" }).textContent;
        ok(/design is not loaded/.test(say) && say.includes("--design"), `inside ${name}, components: no design, so the chip says how to load one with --design`, `inside ${name}, components: no design and no chip ("${say.slice(0, 60)}")`);
        continue;
      }
      const comps = $$("#inside-stage .in-box.component").length, stubs = $$("#inside-stage .in-stub").length, o = overlaps();
      ok(comps === d.components.length && stubs === d.stubs.length && !o.bad.length, `inside ${name}, components: ${comps} components and ${stubs} integration stubs, ${o.n} boxes and labels, no two overlap`,
        `inside ${name}, components: ${comps} of ${d.components.length}, ${stubs} of ${d.stubs.length} stubs; overlaps ${o.bad.slice(0, 3).join("; ")}`);
      {  // opens fitted: the whole drawing sits inside its holder, nothing cut off at the right or the bottom
        const holder = $("#inside-draw"), box = holder.getBoundingClientRect(), svg = $("svg", holder).getBoundingClientRect();
        ok(svg.right <= box.right + 1 && svg.bottom <= box.bottom + 1 && holder.scrollWidth <= holder.clientWidth + 1 && holder.scrollHeight <= holder.clientHeight + 1,
          `inside ${name}, components: opens fitted, the whole drawing in view (${Math.round(svg.width)} x ${Math.round(svg.height)} px in ${Math.round(box.width)} x ${Math.round(box.height)})`,
          `inside ${name}, components: the drawing is cut off: ${Math.round(svg.width)} x ${Math.round(svg.height)} px in ${Math.round(box.width)} x ${Math.round(box.height)}, scrolls ${holder.scrollWidth - holder.clientWidth} across and ${holder.scrollHeight - holder.clientHeight} down`);
        const toggle = $("#inside-stage .in-tabs-toggle"), beside = getComputedStyle($(".inside-l3")).gridTemplateColumns.split(" ").length > 1, area = (r) => r.width * r.height, wide = area($("#inside-draw").getBoundingClientRect());
        toggle.click();
        const hidden = $(".inside-l3").classList.contains("tabs-hidden") && !$(".inside-side").offsetParent, shown = $("#inside-draw").getBoundingClientRect(), wider = area(shown), refit = $("#inside-draw svg").getBoundingClientRect();
        toggle.click();
        ok(hidden && (wider > wide || !beside) && refit.right <= shown.right + 1, `inside ${name}: the tabs fold away (drawing ${Math.round(wide / 1000)} to ${Math.round(wider / 1000)} k px squared, refitted) and come back`, `inside ${name}: tabs toggle: hidden ${hidden}, area ${Math.round(wide)} to ${Math.round(wider)}, refit right edge ${Math.round(refit.right)}`);
      }
      const chip = $("#main .d-problems");
      ok(!!chip && +chip.dataset.problems === d.problems.length, `inside ${name}: the problems chip says ${d.problems.length}, the reader's count, never hidden`, `inside ${name}: problems chip ${chip ? chip.dataset.problems : "missing"}, wanted ${d.problems.length}`);
      if (chip) chip.click();
      const items = $$("#panel ol.in-problems li"), byLine = d.problems.slice().sort((p, q) => (p.line || 1e9) - (q.line || 1e9));
      ok(items.length === d.problems.length && items.every((li, i) => li.textContent.includes(byLine[i].message)), `inside ${name}: the chip opens ${plural(items.length, "problem")} in the panel, by line`, `inside ${name}: the panel lists ${items.length} of ${d.problems.length}`);
      const empty = [];
      for (const [t] of Inside.TABS) { Inside.st.tab = t; rerender(); const body = $("#inside-stage .inside-tab-body"); if (!body || !body.children.length || nulls(body)) empty.push(t); }
      ok(!empty.length, `inside ${name}: every section beside the drawing renders (${Inside.TABS.length} tabs)`, `inside ${name}: empty or "null" in ${empty.join(", ")}`);
      Inside.st.tab = "data"; rerender();
      if (d.data_model.parsed_from === "erDiagram") ok($$("#inside-stage .in-entity-box").length === d.data_model.entities.length, `inside ${name}: the data model drawn from its erDiagram, ${d.data_model.entities.length} entities and ${d.data_model.relationships.length} relationships`, "the data model's entities are not all drawn");
      if (d.data_model.parsed_from === "erDiagram") {  // all entities in view when the tab opens; "+" zooms to read
        const er = $("#inside-stage .in-er"), box = er.getBoundingClientRect(), out = $$("#inside-stage .in-entity-box").filter((g) => { const r = g.getBoundingClientRect(); return r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1 || r.bottom > box.bottom + 1; });
        ok(!out.length && er.dataset.zoom === "1.00", `inside ${name}: the data model opens fitted, all ${d.data_model.entities.length} entities in view`, `inside ${name}: ${out.length} entities outside the data model's frame: ${out.map((g) => g.dataset.entity).join(", ")}`);
        $$("#inside-stage .in-er-wrap .in-zoom button")[2].click();
        ok(+$("#inside-stage .in-er").dataset.zoom > 1, `inside ${name}: the data model zooms in to read`, `inside ${name}: the data model did not zoom`);
        delete Inside.st.zoom.er;
      }
      Inside.st.tab = "trace"; rerender();
      const owner = d.components.find((x) => (d.trace[x.name] || []).length);
      if (owner) {
        go(`inside:${k}|c|${encodeURIComponent(owner.name)}`, { reset: true });
        const ids = $$("#panel .p-sec ul.mini-list .in-id").length;
        ok(ids === d.trace[owner.name].length && (d.trace_source !== "inferred" || !!$("#panel .heuristic")), `inside ${name}: ${owner.name}'s panel lists the ${ids} vault IDs it owns, each with where it was found${d.trace_source === "inferred" ? ", marked inferred" : ""}`, `component panel lists ${ids} of ${d.trace[owner.name].length}`);
      }
    }
    // the vault and the design, both ways: owned, acknowledged and missed, each on the vault item's own panel
    const owned = Object.keys(Inside.OWNERS).find((id) => /^CAP-\d{3}\.FR\d+$/.test(id) && E[id]);
    if (owned) { go(owned, { reset: true }); ok($$("#panel .in-owner").some((x) => /Owned by/.test(x.textContent)), `reverse trace: ${owned}'s panel says "Owned by ${Inside.OWNERS[owned][0].component} (${titleOf(Inside.OWNERS[owned][0].app)} design)"`, `reverse trace: ${owned} shows no owner`); }
    for (const kind of ["ack", "missed"]) {
      const id = Object.keys(Inside.UNTRACED).find((x) => Inside.UNTRACED[x].some((u) => !!u.gap === (kind === "ack")) && (CONTRACT[x] || E[x] || /^EPC-\d{3}\.AC\d+$/.test(x)));
      if (!id) { out.push(`skip reverse trace, ${kind}: no such untraced target in these designs`); continue; }
      const epic = id.match(/^(EPC-\d{3})\.AC\d+$/);
      go(epic ? keyForId(epic[1]) : id, { reset: true });
      const row = $$(`#panel .in-owner.untraced.${kind}`)[0];
      ok(!!row && !!row.querySelector(kind === "ack" ? ".lamp.dark" : ".lamp.caution"), `reverse trace: ${id} untraced, ${kind === "ack" ? "grey, acknowledged by " + Inside.UNTRACED[id].find((u) => u.gap).gap : "amber, and no gap says so"}`, `reverse trace: ${id} shows no ${kind} row`);
    }
    // a design question's challenge lights the vault item it challenges, with its scenario
    for (const [id, list] of Object.entries(Inside.CHALLENGED)) {
      const k = keyForId(id), chipLamp = refChip(k).querySelector(".lamp");
      go(k, { reset: true });
      const sec = $$("#panel .in-challenge");
      ok(!!chipLamp && chipLamp.classList.contains("caution") && sec.length === list.length && (!list[0].scenario || sec[0].textContent.includes(list[0].scenario.slice(0, 30))),
        `challenge: ${id} lit "needs you" by ${list.map((c) => c.oq).join(", ")} in the ${titleOf(list[0].app)} design${list[0].scenario ? ", with its scenario" : ""}`, `challenge: ${id} lamp ${chipLamp ? chipLamp.className : "none"}, ${sec.length} sections`);
    }
    // the deep link, the crumbs, the doors, the sidebar and the map
    const k0 = loaded[0] || apps[0];
    Inside.open(k0, "components", { tab: "flows" });
    ok(location.hash.startsWith(`#inside=${encodeURIComponent(k0)}&level=components${loaded.length ? "&tab=flows" : ""}`), `deep link: ${location.hash.split("&selftest")[0]}`, `deep link: ${location.hash}`);
    $$(".inside-crumbs a").find((a) => a.dataset.level === "context").click();
    ok(Inside.st.level === "context" && App.view === "inside", "the crumbs step back up from components to context", `crumbs: at ${Inside.st.level}`);
    showView("progress");
    ok($$(".pages table.t .d-status").length === loaded.length, `progress: the stage ladder carries ${plural(loaded.length, "design")}' state`, `progress: ${$$(".pages table.t .d-status").length} design states for ${loaded.length}`);
    Roles.st.app = k0; Nav.role("eng");
    const entry = $(".door-card .in-door");
    ok(!!entry && $$("[data-inside]", entry).length === 3, `engineering door: an Inside entry for ${titleOf(k0)}, with its three levels`, "engineering door: no Inside entry");
    Nav.open("apps", k0);
    const listed = Nav.st.expanded.has("apps");  // past 12 apps the sidebar starts with its app list folded
    ok((!listed || !!$(`#side .side-inside[data-inside="${CSS.escape(k0)}"]`)) && !!$("#main .inside-btn"), `${listed ? "sidebar and " : ""}section page: ${titleOf(k0)} offers Inside this app`, "the app's sidebar entry or page has no Inside");
    const box = $(`#board g.hit[data-key="${CSS.escape(k0)}"]`);
    if (box) { box.dispatchEvent(new MouseEvent("dblclick", { bubbles: true })); ok(App.view === "inside" && Inside.st.level === "containers", `the map: double-clicking ${titleOf(k0)} goes inside, to its containers`, `double-click: view ${App.view}, level ${Inside.st.level}`); }
    // every theme and Plain: the drawing still lays out with nothing on anything, and Plain runs no animation
    const was = Theme.id, fx = FX.on, themed = [];
    for (const t of Theme.LIST) { Theme.set(t.id); Inside.open(k0, "components"); const o = overlaps(); if (o.bad.length || !$("#inside-stage")) themed.push(`${t.id}: ${o.bad.length} overlaps`); }
    Theme.set(was);
    FX.set(false); Inside.open(k0, "containers"); Inside.open(k0, "components");
    const anim = document.getAnimations ? document.getAnimations().filter((a) => a.playState === "running").length : 0;
    ok(!themed.length && !anim, `inside in every theme (${Theme.LIST.map((t) => t.label).join(", ")}) lays out cleanly; in Plain a level change runs ${anim} animations`, `inside themes: ${themed.join("; ")}; Plain animations ${anim}`);
    FX.set(fx);
  }
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await checks(ok, lines); } catch (e) { lines.push("FAIL the Inside checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the Inside checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
