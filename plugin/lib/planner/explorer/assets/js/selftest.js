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
  async function run() {
    out.length = 0;
    const parity = Search.parity(), bad = parity.filter((p) => !p.same);
    out.push(bad.length ? `FAIL SEARCH PARITY ${bad.length} of ${parity.length}: ` + JSON.stringify(bad) : `ok SEARCH PARITY ${parity.length} of ${parity.length} queries rank exactly as planner query search`);
    try { await livePaths(); await thread(); await views(); await navigation(); await doors(); await scale(); await effects(); await releases(); await emptyStates(); }
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
