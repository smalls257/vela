/* #selftest: the page checks itself, as a person would use it, and writes the report to the console and to
   <body data-selftest>. Search must rank exactly as `vela query search` does (the CLI's answers are embedded at
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

  /* A query that names two apps or parties a flow joins, such as "how does Booking talk to Pricing". */
  function pairQuery() {
    for (const f of D.flows) for (const stp of f.steps) for (const m of stp.messages) {
      const c = CONTRACT[m.contract]; if (!c) continue;
      const a = titleOf(c.provider), b = titleOf(c.consumers[0]);
      // Several contracts can join the same pair, in either direction (one to check, one to record; one each way); the
      // words cannot tell them apart, so any of them is right.
      const pair = new Set([c.provider, c.consumers[0]]);
      const joins = (o) => o.provider !== o.consumers[0] && pair.has(o.provider) && (o.consumers || []).some((x) => x !== o.provider && pair.has(x));
      if (a && b && a !== b) return { q: `how does ${b} talk to ${a}`.toLowerCase(), contracts: Object.values(CONTRACT).filter(joins).map((o) => o.id) };
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
    // Path 2: "how does <one app> talk to <another>?" gets to the contract, and presenting from that step.
    const pq = pairQuery();
    if (pq) {
      go("lights", { reset: true }); showView("map"); await frames();
      const keys = Search.type(pq.q);
      const first = $("#results .result"), group = first ? first.previousElementSibling && first.previousElementSibling.textContent : "";
      Search.pick(0); await frames(3);
      const key = keys[0];
      const btn = $$("#panel .present-btn")[0];
      ok(pq.contracts.includes(key) && App.view === "map" && !!btn, `path 2 "${pq.q}": search, Enter → ${key} ${titleOf(key)} (group "${(group || "").split("·")[0].trim()}"), on the map, panel offers "${buttonText(btn)}"`,
        `path 2 "${pq.q}": first result ${key}, wanted ${pq.contracts.join(" or ")}; view ${App.view}; present button ${buttonText(btn)}`);
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
    ok(($("#panel h2") || {}).textContent === "What's waiting", "the Lights crumb returns the panel to its home, the lights", "the Lights crumb did not return home");
  }
  async function views() {
    // Map, cockpit: one lamp per app, party, contract and flow, each lit exactly as attention.lights says.
    go("lights", { reset: true });
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; rerender(); await frames(3);
    const lamps = $$("#board g.hit:not([data-agg])");
    const want = D.nodes.length + D.map.contracts.filter((c) => c.consumers.some((k) => k !== c.provider && NODE[k]) && NODE[c.provider]).length + D.flows.length;
    const wrong = lamps.filter((g) => { const lv = D.lights[g.dataset.key] ? D.lights[g.dataset.key].level : "dark"; return !g.classList.contains(lv === "dark" ? "dark" : lv); });
    ok(lamps.length >= want - 1 && !wrong.length, `map, cockpit: ${lamps.length} lamps, each lit as attention.lights says; ${$$("#board g.lit").length} lit`, `map, cockpit: ${lamps.length} lamps (wanted ${want}); ${wrong.length} disagree with attention.lights: ${wrong.slice(0, 3).map((g) => g.dataset.key).join(", ")}`);
    await queueChecks();
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
    await flowPicker(ok);
    await tracerMarks(ok);
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
    await decisionChecks();
    showView("progress"); await frames();
    ok($$(".pages table.t tr.click").length >= D.progress.rows.length, `progress: ${D.progress.rows.length} apps on the ladder, ${$$(".due-chart .bar-r").length} due bars`, "progress: rows missing");
    showView("trace"); await frames();
    ok($$(".cap-card").length === D.trace.capabilities.length, `trace: ${D.trace.capabilities.length} capability cards, ${D.trace.gaps.length} gaps`, "trace: cards missing");
    out.push("assets: " + Assets.status);
    if (Assets.R) {
      // The built-in art is generic: a box wears the emblem of its icon kind, so an emblem never depends on what an app is called.
      const boxes = Object.keys(D.icons || {}), kinds = new Set(Assets.R.slots().filter((id) => id.startsWith("emblem.")).map((id) => id.slice(7)));
      const wrong = boxes.filter((k) => kinds.has(Icons.name(k)) !== !!Assets.emblem(k));
      ok(!wrong.length, `assets: ${boxes.filter((k) => Assets.emblem(k)).length} of ${boxes.length} boxes wear the emblem of their icon kind`, `assets: emblem by kind wrong for ${wrong.slice(0, 3).join(", ")}`);
    }
  }
  /* ------------------------------------------------------------ the second pass: navigation, doors, scale, effects, releases */
  async function navigation() {
    // A tooltip never outlives the element that showed it: a click that swaps the page removes the element under the
    // pointer, so its mouseleave never comes (the user saw tips stay after clicking through to another page).
    {
      const host = h("span", {}, "tip host"); document.body.append(host);
      const at = { currentTarget: host, target: host, clientX: 40, clientY: 40 };
      showTip(at, "<b>a tip</b>"); host.remove();
      document.dispatchEvent(new MouseEvent("mousemove", { clientX: 41, clientY: 41, bubbles: true }));
      const goneAfterRemove = !$("#tip").classList.contains("on");
      document.body.append(host); showTip(at, "<b>a tip</b>");
      host.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
      const goneAfterClick = !$("#tip").classList.contains("on");
      showTip(at, "<b>a tip</b>"); dispatchEvent(new HashChangeEvent("hashchange"));
      const goneAfterHash = !$("#tip").classList.contains("on");
      host.remove(); hideTip();
      ok(goneAfterRemove && goneAfterClick && goneAfterHash, "tooltip: it hides when its element goes, on any click and on a page change",
        `tooltip stayed: after its element went ${!goneAfterRemove}, after a click ${!goneAfterClick}, after a page change ${!goneAfterHash}`);
    }
    const order = ["goals", "constraints", "context", "strategy", "capabilities", "releases", "slices", "apps", "flows", "concerns", "decisions", "unknowns", "glossary", "epics"];
    Nav.refresh();
    const shown = [...new Set($$("#side .side-link").map((b) => b.dataset.section))];
    const sideOrder = [...order.filter((id) => !["constraints", "context", "strategy", "glossary"].includes(id)), "constraints", "context", "strategy", "glossary"];  // the text-first pages sit last, under Read
    ok(JSON.stringify(shown.filter((x) => x)) === JSON.stringify(sideOrder), `sidebar: ${shown.length} sections in the vault's order, the text pages folded under Read, with What's waiting and ${Roles.ROLES.length - 1} front doors above`, `sidebar order ${shown.join(",")}`);
    const kids = $$("#side .side-kid[data-section=apps]").length, flowKids = $$("#side .side-kid[data-section=flows]").length;
    ok((kids === D.map.apps.length || !Nav.st.expanded.has("apps")) && (flowKids === D.flows.length || !Nav.st.expanded.has("flows")), `sidebar lists each app (${kids}) and each flow (${flowKids})`, `sidebar lists ${kids} apps of ${D.map.apps.length}, ${flowKids} flows of ${D.flows.length}`);
    const bad = [], seen = [];
    for (const id of order) {
      Nav.open(id); await frames();
      const s = Nav.SECTIONS[id], pk = Nav.sectionPage();
      const reader = $("#panel .reader") || $("#main .reader");
      const visual = App.view !== "doc" ? !!$("#main").children.length : !!$("#main .reader");
      const links = reader ? $$("a[data-ref]", reader) : [], dead = links.filter((a) => !ent(a.dataset.ref) && !a.classList.contains("ref-dead"));
      const decision = id === "decisions" && $("#panel .open-page");  // a decision picked in the log opens its page beside it
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
      const shownN = +($("#board") || { dataset: {} }).dataset.shown, want = 1 + new Set([...MapGroups.neighbors(app).uses.keys(), ...MapGroups.neighbors(app).usedBy.keys()]).size;
      ok(MapView.st.focus === app && shownN === want && App.root === "read:" + app, `Apps › ${titleOf(app)}: the map focused on it with its ${want - 1} direct neighbors only, its page in the panel`, `focus on ${app}: shown ${shownN}, wanted ${want}; root ${App.root}`);
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
      // a door taller than the window scrolls as a whole; a card is never cut to make it fit
      const scrolls = door && (door.scrollHeight <= door.clientHeight + 2 || /auto|scroll/.test(getComputedStyle(door).overflowY));
      const cut = $$(".door-card").filter((c) => c.scrollHeight > c.clientHeight + 2 && /hidden|clip/.test(getComputedStyle(c).overflowY)).length;
      lines.push(`${id} ${cards} cards${scrolls ? "" : " (overflows)"}${cut ? `, ${cut} cut` : ""}`);
      if (!door || !grid || cards < 3) { ok(false, "", `door ${id}: ${cards} cards`); return; }
    }
    ok(!lines.some((l) => l.includes("overflows") || l.includes(" cut")), `front doors: ${lines.join(", ")}, each card whole, the door scrolling when they are taller than the window`, `front doors: ${lines.join(", ")}`);
    Nav.role("eng"); await frames();
    ok(!!$(".door-pick .chip.on") || !D.map.apps.length, `engineering door: an app picked, its handoff list of ${(D.handoffList[Roles.st.app] || []).length} items from handoff.handoff_list`, "engineering door has no app picked");
  }
  /* The flow picker: it lists every flow once, groups only above ten, filters by name, and takes the keyboard. The
     grouping is also checked on made-up flows, so a vault with three flows still proves the rule at twelve. */
  async function flowPicker(ok) {
    const fake = (n, over) => ({ key: "F" + n, id: "FLO-" + n, title: "Flow " + String(n).padStart(2, "0"), level: "dark", steps: 3, open: 0, caps: [], guessed: false, domain: "", ...over });
    const ten = Array.from({ length: 10 }, (_, i) => fake(i, { caps: ["Cap A"] })), twelve = [...ten, fake(10, { caps: ["Cap B", "Cap A"] }), fake(11, { domain: "Pay" })];
    const flat = FlowPicker.arrange(ten, ""), grouped = FlowPicker.arrange(twelve, "");
    ok(!flat.grouped && flat.groups.length === 1 && grouped.grouped, `flow picker: ten flows are one flat list, twelve are grouped (${grouped.groups.map((g) => g.heading.name + " " + g.items.length).join(", ")})`, "flow picker: the ten-flow boundary is wrong");
    ok(grouped.groups.flatMap((g) => g.items).length === 12 && new Set(grouped.groups.flatMap((g) => g.items.map((e) => e.key))).size === 12, "flow picker: twelve flows, each under exactly one heading", "flow picker: a flow is missing or listed twice");
    const first = grouped.groups.find((g) => g.heading.name === "Cap A"), second = FlowPicker.arrange(twelve, "flow 10").groups;
    ok(first && first.items.length === 10 && grouped.groups[grouped.groups.length - 1].heading.kind === "domain", "flow picker: a flow serving two capabilities sits under its first, and a flow with only a domain follows the capabilities", "flow picker: grouping order is wrong");
    const mixed = FlowPicker.arrange([...twelve.slice(0, 11), fake(11, { caps: ["Cap B"], guessed: true })], "");
    ok(mixed.groups.some((g) => g.heading.kind === "guessed" && g.heading.name === "Cap B"), "flow picker: a capability guessed from the steps is its own group, marked as a guess", "flow picker: a guessed capability is grouped with the recorded ones");
    const urgentFirst = FlowPicker.arrange([...ten.slice(0, 10), fake(10, { caps: ["Cap A"], level: "warning" })], "").groups[0].items[0];
    ok(urgentFirst.key === "F10" && second.length === 1 && second[0].items.length === 1, "flow picker: inside a group the most urgent lamp is first, and typing narrows the list", "flow picker: urgency order or filtering is wrong");
    if (!D.flows.length) return;
    Flows.select(D.flows[0].key, -1); await frames(2);
    const wrap = $(".flow-picker"), trigger = $(".fp-trigger", wrap), input = $(".fp-input", wrap);
    ok(!!wrap && !$("nav.tracks") && trigger.getAttribute("aria-haspopup") === "listbox" && trigger.textContent.includes(E[D.flows[0].key].title) && $("#present-btn") && $("#clip-btn"),
      `flow picker: the Flows view shows one button naming "${E[D.flows[0].key].title}", with Rehearse, Save clip and Present beside it`, `flow picker: the flow strip is still there, or the button does not name the flow (picker ${!!wrap}, tracks ${!!$("nav.tracks")}, text "${wrap && wrap.textContent}", present ${!!$("#present-btn")}, clip ${!!$("#clip-btn")})`);
    trigger.click(); await frames();
    const optsOf = () => $$(".fp-opt", wrap), keysOf = () => optsOf().map((o) => o.dataset.flow);
    const listed = keysOf(), groups = $$(".fp-group", wrap);
    ok(listed.length === D.flows.length && new Set(listed).size === D.flows.length && D.flows.every((f) => listed.includes(f.key)) && !wrap.querySelector(".fp-pop").hidden,
      `flow picker: opens with all ${D.flows.length} flows, each once`, `flow picker: lists ${listed.length} of ${D.flows.length} flows`);
    ok((D.flows.length > FlowPicker.TEN_FLOWS) === (groups.length > 0), `flow picker: ${groups.length ? `${groups.length} headings, ${$$(".fp-head", wrap).map((x) => x.textContent).join("; ")}` : "no headings at ten or fewer"}`, "flow picker: headings do not match the ten-flow rule");
    ok(input.getAttribute("role") === "combobox" && $("#" + input.getAttribute("aria-activedescendant")) && $("#" + input.getAttribute("aria-activedescendant")).getAttribute("role") === "option" && $(".fp-list", wrap).getAttribute("role") === "listbox",
      "flow picker: a combobox over a listbox, aria-activedescendant names a real option", "flow picker: the ARIA wiring is missing");
    const word = E[D.flows[0].key].title.split(/\s+/).pop();
    input.value = word; input.dispatchEvent(new Event("input")); await frames();
    const kept = keysOf();
    ok(kept.includes(D.flows[0].key) && kept.every((k) => E[k].title.toLowerCase().includes(word.toLowerCase()) || E[k].id.toLowerCase().includes(word.toLowerCase()) || (FLOW[k].capabilities || []).some((c) => E[c] && E[c].title.toLowerCase().includes(word.toLowerCase())) || (FLOW[k].domain || "").toLowerCase().includes(word.toLowerCase())),
      `flow picker: typing "${word}" keeps ${kept.length} of ${D.flows.length}`, `flow picker: typing "${word}" kept ${kept.join(", ")}`);
    input.value = "zzqx no such flow"; input.dispatchEvent(new Event("input")); await frames();
    ok(!optsOf().length && !!$(".fp-empty", wrap), "flow picker: a query nothing matches says so", "flow picker: no empty message");
    input.value = ""; input.dispatchEvent(new Event("input")); await frames();
    const key = (k) => input.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
    const at = optsOf().findIndex((o) => o.id === input.getAttribute("aria-activedescendant")), want = optsOf()[(at + 1) % optsOf().length].dataset.flow;
    key("ArrowDown"); await frames();
    ok(optsOf().findIndex((o) => o.id === input.getAttribute("aria-activedescendant")) === (at + 1) % optsOf().length, "flow picker: the down arrow moves to the next option", "flow picker: the down arrow did not move");
    key("Enter"); await frames(2); await new Promise((r) => setTimeout(r, 0));
    const trigger2 = $(".flow-picker .fp-trigger"), wrap2 = $(".flow-picker");
    ok(Flows.st.key === want && location.hash.startsWith(`#flows&open=${encodeURIComponent(want)}`) && wrap2.querySelector(".fp-pop").hidden && document.activeElement === trigger2 && trigger2.textContent.includes(E[want].title),
      `flow picker: Enter chose ${want}, the hash follows (${location.hash.split("&selftest")[0]}), the list closed and focus came back to the button`, `flow picker: Enter left ${Flows.st.key} (wanted ${want}), hash ${location.hash}`);
    trigger2.click(); await frames(); wrap2.querySelector(".fp-input").dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true })); await frames();
    ok(wrap2.querySelector(".fp-pop").hidden && document.activeElement === trigger2, "flow picker: Escape closes the list and keeps your place", "flow picker: Escape left the list open");
    Flows.select(D.flows[0].key, -1); await frames(2);
  }
  /* Release one's tracer on the flow views and the Releases lens: the tag sits on exactly the tracer flows and nowhere else,
     the releases line names them and what is left out, and a vault that records no tracer shows nothing of it. */
  async function tracerMarks(ok) {
    if (!D.flows.length) return;
    const orig = D.releases.tracer, keys = D.flows.map((f) => f.key), idOf = (k) => E[k].id;
    const pickerTags = async () => {
      Flows.select(keys[0], -1); await frames(2);
      $(".flow-picker .fp-trigger").click(); await frames();
      const got = $$(".flow-picker .fp-opt").filter((o) => o.querySelector(".tracer-tag")).map((o) => o.dataset.flow);
      const small = $$(".flow-picker .fp-opt .tracer-tag").every((t) => t.getAttribute("title") && t.textContent === "first slice");
      $(".flow-picker .fp-trigger").click(); await frames();
      return { got, small };
    };
    const pageTags = async () => {
      const got = [];
      showView("map"); await frames();  // the page is drawn afresh, since the tracer changed under the one already showing
      for (const k of keys) { Flows.select(k, -1); await frames(2); if ($(".flows-head .tracer-tag")) got.push(`${k}:${$(".flows-head .tracer-place").textContent.trim()}`); }
      return got;
    };
    const check = async (label, t) => {
      D.releases.tracer = t;
      const want = t ? t.flows : [];
      const pk = await pickerTags(), pg = await pageTags();
      ok(pk.got.length === want.length && pk.got.every((k) => want.includes(idOf(k))) && pk.small, `tracer, ${label}: the picker tags ${want.join(", ") || "no flow"}, each with a tooltip`, `tracer, ${label}: the picker tags ${pk.got.map(idOf).join(", ") || "nothing"}, wanted ${want.join(", ") || "nothing"}`);
      const wantPg = keys.filter((k) => want.includes(idOf(k))).map((k) => `${k}:first slice flow ${want.indexOf(idOf(k)) + 1} of ${want.length}`);
      ok(JSON.stringify(pg) === JSON.stringify(wantPg), `tracer, ${label}: each tracer flow's page shows the tag and its place${wantPg.length ? ` (${wantPg.map((x) => x.split(":")[1]).join("; ")})` : ", none here"}`, `tracer, ${label}: flow pages show ${pg.join("; ") || "nothing"}, wanted ${wantPg.join("; ") || "nothing"}`);
      if (!D.releases.count || !D.map.apps.length) return;
      Nav.open("releases"); await frames(2);
      const line = $("[data-tracer-line]");
      if (!want.length) { ok(!line && !$(".tracer-tag"), `tracer, ${label}: the Releases lens shows nothing of a tracer`, `tracer, ${label}: a tracer line shows with none recorded`); return; }
      const text = line ? line.textContent : "";
      ok(!!line && !!line.closest('.rel-card[data-state="1"]') && want.every((id) => text.includes(E[keys.find((k) => idOf(k) === id)].title)) && (!t.words || text.includes(t.words)) && t.notIn.every((x) => text.includes(x.text)) && text.includes("left out") === !!t.notIn.length,
        `tracer, ${label}: release one's card carries the line naming the flows, the thin version and what is left out`, `tracer, ${label}: the line reads "${text}"`);
    };
    await check("none recorded", null);
    await check("two flows, one item left out", { given: true, flows: [idOf(keys[keys.length - 1]), idOf(keys[0])].filter((v, i, a) => a.indexOf(v) === i), words: "a thin path", none: "", notIn: [{ text: "Big thing (CAP-009.FR1): waits on approval", ids: ["CAP-009.FR1"], reason: "waits on approval" }] });
    await check("one flow, nothing left out", { given: true, flows: [idOf(keys[0])], words: "", none: "", notIn: [] });
    if (orig) await check("as recorded", orig);
    D.releases.tracer = orig;
    Nav.home(); await frames();
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
      MapView.st.open.clear(); MapView.st.shut.clear(); rerender(); await frames();
      const through = wiresThroughBoxes();
      ok(!through.length, `group by domain, as it opens: ${$$("#board svg.grouped path.duct[data-a]").length} wires, none through a box it does not join`, `group by domain: ${through.length} wires through a box, such as ${through.slice(0, 3).join("; ")}`);
    } else out.push("skip group by domain: no app page has a domain");
    MapView.st.group = "capability"; rerender(); await frames();
    const regions = MapGroups.groups("capability"), apps = D.nodes.filter((n) => n.kind === "app").map((n) => n.key);
    const once = apps.every((k) => regions.filter((r) => r.members.includes(k)).length === 1), ghosts = regions.reduce((n, r) => n + r.ghosts.length, 0);
    ok(once, `group by capability: ${regions.length} regions, every app in exactly one, ${plural(ghosts, "chip")} where it also belongs`, "an app is drawn in more than one region");
    // nothing sits on anything: every box, lamp, count, name, chip, tab and toggle, measured as drawn, closed and open
    // and no wire runs through a box it does not join, as the map opens and with every region closed or open
    MapView.st.open.clear(); MapView.st.shut.clear(); rerender(); await frames();
    {
      const through = wiresThroughBoxes();
      ok(!through.length, `group by capability, as it opens: ${$$("#board svg.grouped path.duct[data-a]").length} wires, none through a box it does not join`,
        `group by capability, as it opens: ${through.length} wires through a box, such as ${through.slice(0, 3).join("; ")}`);
    }
    for (const open of [false, true]) {
      MapGroups.all(open); rerender(); await frames();
      const bad = overlaps(), through = wiresThroughBoxes();
      ok(!bad.length, `group by capability, every region ${open ? "open" : "closed"}: ${$$(OVERLAP_PARTS).length} boxes and labels, no two overlap`,
        `group by capability (${open ? "open" : "closed"}): ${bad.length} overlaps, such as ${bad.slice(0, 3).join("; ")}`);
      ok(!through.length, `group by capability, every region ${open ? "open" : "closed"}: ${$$("#board svg.grouped path.duct[data-a]").length} wires, none through a box it does not join`,
        `group by capability (${open ? "open" : "closed"}): ${through.length} wires through a box, such as ${through.slice(0, 3).join("; ")}`);
    }
    MapView.st.open.clear(); MapView.st.shut.clear();
    MapView.st.group = null; MapView.st.open.clear(); MapView.st.shut.clear(); rerender();
  }
  /* The wires of the grouped map that run through (or within 6 px of) a box they do not join, as "<a> to <b> through <box>",
     sampled every 4 px along the path as drawn. The boxes are the ones the scene holds: apps in open regions, closed regions. */
  function wiresThroughBoxes() {
    const out = [], boxes = Scene.st ? Object.entries(Scene.st.nodes) : [];  // an empty vault has no board
    for (const wire of $$("#board svg.grouped path.duct[data-a]")) {
      const len = wire.getTotalLength(), hit = new Set();
      for (let at = 0; at <= len; at += 4) {
        const p = wire.getPointAtLength(at);
        for (const [key, b] of boxes) if (key !== wire.dataset.a && key !== wire.dataset.b && p.x > b.x - 6 && p.x < b.x + b.w + 6 && p.y > b.y - 6 && p.y < b.y + b.h + 6) hit.add(key);
      }
      for (const key of hit) out.push(`${wire.dataset.a} to ${wire.dataset.b} through ${key}`);
    }
    return out;
  }
  const OVERLAP_PARTS = "#board svg.grouped g.hit, #board svg.grouped .cluster-names text, #board svg.grouped .also-chip, #board svg.grouped .also-tab, #board svg.grouped .cluster-toggle";
  // the ungrouped cockpit, the line map and the minimap: every box, lamp bank, caption, name, works marker and station
  const COCKPIT = "#board svg.cockpit:not(.grouped):not(.focus)", TRANSIT = "#board svg.transit", MINI = "#panel-mini svg";
  const COCKPIT_PARTS = `${COCKPIT} g.hit, ${COCKPIT} .zone-text, ${COCKPIT} .engrave`;
  const TRANSIT_PARTS = `${TRANSIT} g.station, ${TRANSIT} .track-label, ${TRANSIT} g.works, ${TRANSIT} .zone-text`;
  const MINI_PARTS = `${MINI} g.mini-node`;
  /* Pairs of drawn parts whose boxes intersect by more than a pixel, as "<a> on <b>". A part's own children are not parts. */
  function overlaps(selector = OVERLAP_PARTS) {
    const parts = $$(selector).filter((el) => !el.parentElement.closest(".also-chip, .also-tab, .cluster-toggle, g.hit, g.station, g.mini-node, g.works")).map((el) => {
      const b = el.getBBox();
      return { el, b, name: el.dataset.key || el.getAttribute("aria-label") || el.textContent.trim().slice(0, 24) };
    });
    const out = [];
    for (let i = 0; i < parts.length; i++) for (let j = i + 1; j < parts.length; j++) {
      const a = parts[i].b, c = parts[j].b;
      if (a.x < c.x + c.width - 1 && c.x < a.x + a.width - 1 && a.y < c.y + c.height - 1 && c.y < a.y + a.height - 1) out.push(`${parts[i].name} on ${parts[j].name}`);
    }
    return out;
  }
  /* The ungrouped cockpit, the line map and the minimap, in every theme, in Plain, with nothing on anything. */
  async function ungrouped() {
    if (!D.nodes.length) { out.push("skip ungrouped map: this vault has no apps"); return; }
    const was = { theme: Theme.id, fx: FX.on, lens: MapView.st.lens, group: MapView.st.group };
    const measure = async (name, lens, parts) => {
      Nav.home(); MapView.st.lens = lens; MapView.st.group = "none"; MapView.st.focus = null; rerender(); await frames();
      const bad = overlaps(parts), n = $$(parts).length;
      ok(!bad.length, `${name}: ${n} boxes, lamps and captions, no two overlap`, `${name}: ${bad.length} overlaps, such as ${bad.slice(0, 4).join("; ")}`);
    };
    await measure("ungrouped cockpit", "cockpit", COCKPIT_PARTS);
    // Past what one drawing carries (MapView.big) the line map is not the lens that opens, and its works markers and
    // track labels have no free spot on a 60-contract map; the cockpit and the minimap are checked at every size.
    const lineMapFits = !MapView.big();
    if (lineMapFits) await measure("line map", "transit", TRANSIT_PARTS);
    else out.push(`skip line map overlaps: ${plural(D.nodes.length, "box", "boxes")} is past what a node-link drawing carries, so the matrix opens first`);
    await measure("minimap", "cockpit", MINI_PARTS);
    MapView.st.lens = "cockpit"; rerender(); await frames();
    const spilled = $$(`${COCKPIT} g.hit`).filter((g) => { const face = g.querySelector(".face").getBBox(); return $$("text", g).some((x) => { const b = x.getBBox(); return b.x < face.x - 1 || b.x + b.width > face.x + face.width + 1; }); }).map((g) => g.dataset.key);
    ok(!spilled.length, "ungrouped cockpit: every name and lamp label stays inside its own box", `ungrouped cockpit: text runs past its box in ${spilled.slice(0, 4).join(", ")}`);
    const problems = [];
    for (const th of Theme.LIST) {
      Theme.set(th.id);
      for (const [lens, parts] of [["cockpit", COCKPIT_PARTS], ["transit", TRANSIT_PARTS], ["cockpit", MINI_PARTS]].filter(([lens]) => lens !== "transit" || lineMapFits)) {
        MapView.st.lens = lens; MapView.st.group = "none"; rerender(); await frames();
        const bad = overlaps(parts);
        if (bad.length) problems.push(`${th.id} ${lens}: ${bad.slice(0, 2).join("; ")}`);
      }
    }
    FX.set(false);
    for (const [lens, parts] of [["cockpit", COCKPIT_PARTS], ["transit", TRANSIT_PARTS], ["cockpit", MINI_PARTS]].filter(([lens]) => lens !== "transit" || lineMapFits)) {
      MapView.st.lens = lens; rerender(); await frames();
      const bad = overlaps(parts);
      if (bad.length) problems.push(`Plain ${lens}: ${bad.slice(0, 2).join("; ")}`);
    }
    FX.set(was.fx); Theme.set(was.theme);
    ok(!problems.length, `ungrouped cockpit, line map and minimap: no two parts overlap in any of ${plural(Theme.LIST.length, "theme")} or in Plain`, `overlaps in ${problems.slice(0, 3).join(" | ")}`);
    MapView.st.lens = was.lens; MapView.st.group = was.group; rerender(); await frames();
  }
  const flush = async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); };  // a saved move is a chain of awaited fetches
  const pointer = (type, x, y) => new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, buttons: type === "pointerup" ? 0 : 1, isPrimary: true, pointerId: 7 });
  /* Moving boxes: the rule, a drag, a drop on an occupied cell, the arrow keys, saving, resetting, Plain, clusters. */
  async function moves() {
    const nodes = D.nodes.slice();
    if (nodes.length < 2) { out.push("skip moving boxes: fewer than two boxes on the map"); return; }
    const layoutWas = Layout.snapshot(), askWas = Ask.snapshot(), fxWas = FX.on, posts = [];
    const fake = async (url, init) => {
      if (url === "/health") return { ok: true, status: 200, json: async () => ({ ok: true, vault: "selftest", model: "haiku", models: {}, claude: false, maxQuestion: 2000 }) };
      if (url === "/pins" && init) { const sent = JSON.parse(init.body); posts.push(sent); return { ok: true, status: 200, json: async () => ({ saved: Object.keys(sent.pins).length, pins: sent.pins }) }; }
      return { ok: false, status: 404, json: async () => ({ error: `nothing at ${url}` }) };
    };
    Layout.net.fetch = fake;
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; rerender(); await frames();
    const original = Object.fromEntries(nodes.map((n) => [n.key, [n.col, n.row]]));
    const mover = nodes.find((n) => n.kind === "app") || nodes[0], other = nodes.find((n) => n.key !== mover.key);
    const farCol = Math.max(...nodes.map((n) => n.col)) + 2, outside = mover.kind !== "app";

    // the rule: pins.check_move's own cases, with its answers, against this page's copy; then the rule on this vault
    const cases = (D.pins.cases || []).map((c) => ({ ...c, page: Layout.verdict(c.pins, c.kinds) }));
    const differ = cases.filter((c) => !!c.page !== !!c.says);
    ok(cases.length >= 8 && !differ.length, `the page's overlap rule gives pins.check_move's answer in all ${cases.length} of its cases`,
      cases.length ? `the page and pins.check_move differ on ${differ.map((c) => `${c.name} (page "${c.page}", pins "${c.says}")`).join("; ")}` : "this selftest build carries no pins.MOVE_CASES");
    const drawnSizes = [...$$(`${COCKPIT} g.hit[data-movable] rect.face`), ...$$(`${MINI} g.mini-node > rect:not(.mini-ring)`)].map((r) => [+r.getAttribute("width"), +r.getAttribute("height")]);
    const tooBig = drawnSizes.filter(([w, ht]) => w > Layout.BOX.w + 0.5 || ht > Layout.BOX.h + 0.5);
    ok(MapView.COCKPIT === Layout.FRAME && drawnSizes.length > 0 && !tooBig.length, `the cockpit and the minimap draw in the rule's frame, every box within pins.BOX (${Layout.BOX.w} by ${Layout.BOX.h})`,
      `frame shared ${MapView.COCKPIT === Layout.FRAME}; ${drawnSizes.length} boxes measured, larger than pins.BOX: ${tooBig.slice(0, 3).map((x) => x.join("x")).join(", ")}`);
    // the cell at which the mover would be drawn right on top of `other`: a party is drawn a band below its row
    const band = (n) => (n.kind === "app" ? 0 : MapView.COCKPIT.bandGap / MapView.COCKPIT.rh);
    const onOther = [other.col, Layout.tidy(other.row + band(other) - band(mover))];
    const taken = Layout.blocker(mover.key, onOther[0], onOther[1]), free = Layout.blocker(mover.key, farCol, mover.row);
    const short = Layout.landing(mover.key, Layout.cell(mover.key), onOther);
    const party = nodes.find((n) => n.kind !== "app");
    const partyHigh = party ? Layout.blocker(party.key, farCol + 3, 0) : "";
    ok(!!taken && !free && !!short && short.hit === other.key && !Layout.blocker(mover.key, short.spot[0], short.spot[1]) && !partyHigh && Layout.check(Layout.cells()) === "",
      `moving a box: another box's place is refused ("${taken}"), a clear one is not, a move onto ${titleOf(other.key)} stops at ${short ? short.spot.join(",") : "none"}, clear of it, and an outside party may stand above the apps`,
      `moving a box: taken "${taken}", free "${free}", landing ${JSON.stringify(short)}, party above the apps "${partyHigh}", layout "${Layout.check(Layout.cells())}"`);

    // a drag, as a pointer would do it, to a clear point beyond the last column, between cells
    const cockpitRoot = () => $("#board svg.cockpit");
    const clientOf = (col, row, isOutside) => { const svg = cockpitRoot(), pt = svg.createSVGPoint(), at = Geo.pointOf(MapView.COCKPIT, col, row, isOutside); pt.x = at.x; pt.y = at.y; const c = pt.matrixTransform(svg.getScreenCTM()); return { x: c.x, y: c.y }; };
    const boxOf = (key) => $(`#board g.hit[data-key="${CSS.escape(key)}"]`);
    const dragTo = (key, col, row) => {
      const r = boxOf(key).getBoundingClientRect(), goal = clientOf(col, row, NODE[key].kind !== "app");
      boxOf(key).dispatchEvent(pointer("pointerdown", r.x + r.width / 2, r.y + r.height / 2));
      window.dispatchEvent(pointer("pointermove", r.x + r.width / 2 + 12, r.y + r.height / 2 + 12));
      window.dispatchEvent(pointer("pointermove", goal.x, goal.y));
      window.dispatchEvent(pointer("pointerup", goal.x, goal.y));
    };
    // a pointer lands on a whole screen pixel, so "exactly there" is to within a pixel of the frame
    const near = (got, want) => Math.abs(got[0] - want[0]) * MapView.COCKPIT.cw < 2 && Math.abs(got[1] - want[1]) * MapView.COCKPIT.rh < 2;
    const focusBefore = App.focus, goal = [farCol + 0.37, mover.row + 0.21];
    dragTo(mover.key, goal[0], goal[1]);
    boxOf(mover.key).dispatchEvent(new MouseEvent("click", { bubbles: true }));  // the click that follows a release must not open the page
    await flush();
    const now = [NODE[mover.key].col, NODE[mover.key].row];
    const mini = $$(`${MINI} g.mini-node`).map((g) => ({ label: g.getAttribute("aria-label"), x: g.getBBox().x }));
    const rightmost = mini.sort((a, b) => b.x - a.x)[0];
    ok(near(now, goal) && !Number.isInteger(now[0]) && Layout.moved() && App.focus === focusBefore && !!rightmost && rightmost.label.startsWith(titleOf(mover.key)),
      `dragging ${titleOf(mover.key)} to column ${(goal[0] + 1).toFixed(2)}, row ${(goal[1] + 1).toFixed(2)}: it stays exactly there, between cells, on the cockpit and the minimap, and the release opened nothing`,
      `dragging ${titleOf(mover.key)}: at ${now}, wanted ${goal}; moved ${Layout.moved()}; focus ${App.focus}; minimap rightmost ${rightmost && rightmost.label}`);
    const bad = [...overlaps(COCKPIT_PARTS), ...overlaps(MINI_PARTS)];
    ok(!bad.length && Layout.check(Layout.cells()) === "", "after the drag: nothing overlaps on the cockpit or the minimap", `after the drag: ${bad.slice(0, 3).join("; ") || Layout.check(Layout.cells())}`);
    MapView.st.lens = "transit"; rerender(); await frames();
    const badLine = !MapView.big() && $(TRANSIT) ? overlaps(TRANSIT_PARTS) : [];  // past MapView.big the line map is not drawn to fit, as in ungrouped()
    MapView.st.lens = "cockpit"; rerender(); await frames();
    ok(!badLine.length, "after the drag: the line map draws the box between cells with nothing on anything", `line map after the drag: ${badLine.slice(0, 3).join("; ")}`);

    // where the move went: this browser, or the vault by POST /pins
    const served = Layout.canSave();
    if (served) {
      ok(posts.length >= 1 && JSON.stringify(posts[posts.length - 1].pins[mover.key]) === JSON.stringify(now) && /Layout saved to the plan/.test(Layout.note), "served: the drop is POSTed to /pins and the page says Layout saved to the plan", `served: ${posts.length} POSTs, note "${Layout.note}"`);
    } else {
      const kept = JSON.parse(Settings.read(`explorer.layout.${D.vaultId}`) || "{}").pins || {};
      ok(JSON.stringify(kept[mover.key]) === JSON.stringify(now) && !posts.length && !!$('[data-layout="copy"]') && !!$('[data-layout="download"]'), "on a file: the move is kept in this browser under the vault's id, nothing is posted, and Copy layout and Download pins are offered", `on a file: kept ${JSON.stringify(kept)}, ${posts.length} POSTs`);
      let copied = "";
      Layout.setCopy(async (text) => { copied = text; });
      await Layout.copy(); Layout.setCopy(null);
      let json = null; try { json = JSON.parse(copied); } catch (e) { console.warn("[selftest] copied layout is not JSON:", e.message); }
      ok(!!json && JSON.stringify(json[mover.key]) === JSON.stringify(now) && copied.endsWith("\n"), "Copy layout gives the pins file's JSON, with the move between cells in it", `Copy layout gave "${copied.slice(0, 60)}"`);
    }

    // a drop on another box lands at the nearest clear point along the drag, and the status line says so
    dragTo(mover.key, onOther[0], onOther[1]);
    await flush();
    const settled = [NODE[mover.key].col, NODE[mover.key].row], bad2 = [...overlaps(COCKPIT_PARTS), ...overlaps(MINI_PARTS)];
    const told = ($("#layout-say") || { textContent: "" }).textContent;
    ok(!near(settled, onOther) && Layout.check(Layout.cells()) === "" && !bad2.length && /would have overlapped .*(stopped just short of|went just past) it/.test(told),
      `dropping ${titleOf(mover.key)} on ${titleOf(other.key)}: it lands clear of it on the line it was dragged along (${settled.join(",")}), and the page says so`, `drop on a box: at ${settled}, said "${told}", ${Layout.check(Layout.cells())} ${bad2.slice(0, 3).join("; ")}`);

    // the keyboard: an arrow key moves the focused box a quarter of a cell, Shift and an arrow a whole cell
    dragTo(mover.key, farCol, mover.row); await flush();
    const before = Layout.cell(mover.key).slice();
    boxOf(mover.key).dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true }));
    await flush();
    const arrived = Layout.cell(mover.key).slice(), focused = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.key : "";
    ok(arrived[0] === Layout.tidy(before[0] + Layout.STEP) && arrived[1] === before[1] && focused === mover.key && /moved to column/.test(($("#layout-say") || { textContent: "" }).textContent),
      `arrow key: ${titleOf(mover.key)} moves a quarter of a cell right and keeps the focus, and the page says where`, `arrow key: ${before} to ${arrived}, focus on ${focused}, said "${($("#layout-say") || { textContent: "" }).textContent}"`);
    boxOf(mover.key).dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", shiftKey: true, bubbles: true, cancelable: true }));
    await flush();
    const whole = Layout.cell(mover.key).slice();
    ok(whole[0] === Layout.tidy(arrived[0] + 1) && whole[1] === arrived[1], "Shift and an arrow key move the box a whole cell", `Shift+ArrowRight: ${arrived} to ${whole}`);
    const help = ($(".layout-tools") || { title: "" }).title + " " + ($("#layout-say") || { textContent: "" }).textContent;
    ok(/quarter of a cell/.test(help) && /Shift/.test(help), "the layout's key help says an arrow key moves a quarter of a cell and Shift a whole one", `layout help: "${help.slice(0, 160)}"`);

    // the edge of the board: a move past it stops at the edge; once there, it is refused and said
    Layout.moveToward(mover.key, [Layout.cell(mover.key)[0], -5]); await flush();
    const top = Layout.cell(mover.key).slice();
    const off = Layout.moveToward(mover.key, [top[0], -1]);
    ok(top[1] === 0 && !off.ok && /off the board/.test(Layout.note), "a move past the top stops at the edge, and one more is refused, and the page says why", `at ${top} after a move past the top; then ${JSON.stringify(off)}, said "${Layout.note}"`);
    // Plain: the same drag, with no animation running
    FX.set(false); await frames();
    dragTo(mover.key, farCol + 1, mover.row); await flush();
    const anim = document.getAnimations ? document.getAnimations().filter((a) => a.playState === "running").length : 0;
    ok(near([NODE[mover.key].col, NODE[mover.key].row], [farCol + 1, mover.row]) && !$$("#board .halo").length && !anim, `Plain: dragging works with no glow and ${anim} running animations`, `Plain: at ${NODE[mover.key].col}, ${$$("#board .halo").length} halos, ${anim} animations`);
    FX.set(fxWas);

    // a cluster of the grouped map moves with the arrow key, stays where it is put, and the others stay put
    const ways = [];
    if (D.map.apps.some((a) => a.domain)) ways.push("domain");
    ways.push("capability");
    for (const way of ways) {
      MapView.st.group = way; MapView.st.open.clear(); MapView.st.shut.clear(); rerender(); await frames();
      const list = MapGroups.groups(way).filter((g) => !g.outside);
      if (list.length < 2) { out.push(`skip moving a ${way} cluster: fewer than two clusters`); continue; }
      const at = (key) => { const el = $(`#board [data-group="${CSS.escape(key)}"]`); const b = el.getBBox(); return [b.x, b.y]; };
      const was = Object.fromEntries(list.map((g) => [g.key, at(g.key)])), first = list[0].key;
      const handle = $(`#board [data-group="${CSS.escape(first)}"] .cluster-toggle, #board g.cluster-lamp[data-group="${CSS.escape(first)}"]`);
      handle.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", shiftKey: true, bubbles: true, cancelable: true }));
      await flush(); await frames();
      const after = Object.fromEntries(list.map((g) => [g.key, at(g.key)])), said = Layout.note;
      const movedBy = after[first][1] - was[first][1], stayed = list.filter((g) => g.key !== first).every((g) => Math.hypot(after[g.key][0] - was[g.key][0], after[g.key][1] - was[g.key][1]) < 1);
      const clash = overlaps();
      ok(!!Layout.clusterAt(first) && (Math.abs(movedBy - MapView.COCKPIT.rh) < 1 || /stopped just short|went just past/.test(said)) && stayed && !clash.length,
        `a ${way} cluster moves a whole row down with Shift and the arrow key (or stops short of a neighbor and says so), the others stay where they were, and nothing overlaps`,
        `${way} cluster: moved ${movedBy.toFixed(1)} px down, said "${said}", others stayed ${stayed}; ${clash.slice(0, 3).join("; ")}`);
    }
    MapView.st.group = "none"; MapView.st.open.clear(); MapView.st.shut.clear(); rerender(); await frames();

    // Reset layout: every box back where the vault's pins have it, and the browser's memory emptied
    posts.length = 0;
    await openMenuAt("more");
    const reset = $('[data-layout="reset"]');
    ok(!!reset && reset.getAttribute("aria-disabled") !== "true", "Reset layout is offered once a box has moved", "Reset layout is missing or disabled after moves");
    reset.click(); await flush();
    const back = nodes.every((n) => NODE[n.key].col === original[n.key][0] && NODE[n.key].row === original[n.key][1]);
    const left = served ? "{}" : JSON.stringify((JSON.parse(Settings.read(`explorer.layout.${D.vaultId}`) || "{}").pins) || {});
    ok(back && (served || left === "{}") && !Layout.moved(), "Reset layout puts every box back where the vault's pins have it, and forgets the moves", `Reset: boxes back ${back}, kept moves ${left}, still moved ${Layout.moved()}`);

    // a reader's page, served: moves stay in this browser unless sent on
    if (!served) {
      await Ask.detect(fake, { protocol: "http:", hostname: "127.0.0.1" });
      Layout.net.fetch = fake; posts.length = 0;
      Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; rerender(); await frames();
      const role = D.role, key = mover.key, spot = [farCol + 0.5, mover.row];
      D.role = "owner";  // a reader's page is the other case, below
      Layout.move(key, spot); await flush();
      ok(posts.length === 1 && JSON.stringify(posts[0].pins[key]) === JSON.stringify(spot) && posts[0].kinds[key] === Layout.KIND(key) && /Layout saved to the plan/.test(Layout.note),
        "served, as the owner: a move is POSTed to /pins with the boxes' kinds, and the page says Layout saved to the plan", `served move: ${posts.length} POSTs, note "${Layout.note}"`);
      D.role = "reader"; posts.length = 0;
      const was = Layout.cell(key).slice(), reading = !Layout.canSave();
      Layout.move(key, [was[0] + 1, was[1]]); await flush();
      D.role = role;
      ok(reading && !posts.length, "served, as a reader: a move is not POSTed; it stays in this browser", `reader move posted ${posts.length}, canSave ${!reading}`);
    }
    Ask.restore(askWas);
    Layout.restore(layoutWas);
    Layout.net.fetch = (...a) => fetch(...a);
    FX.set(fxWas);
    MapView.st.group = null; rerender(); await frames();
  }
  /* Drag to pan (pan.js): the background pans, a box still moves, a click still selects, and every map drawing has it. */
  async function panning() {
    if (!D.nodes.length) { out.push("skip drag to pan: this vault has no apps"); return; }
    const press = (el, x, y, type = "mouse") => el.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, buttons: 1, isPrimary: true, pointerId: 9, pointerType: type }));
    const glide = (x, y) => window.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, cancelable: true, clientX: x, clientY: y, buttons: 1, isPrimary: true, pointerId: 9, pointerType: "mouse" }));
    const lift = (x, y) => window.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, isPrimary: true, pointerId: 9, pointerType: "mouse" }));
    const layoutWas = Layout.snapshot();
    Pan.reset();
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; rerender(); await frames();
    const board = () => $("#board"), root = () => $("#board svg.cockpit"), vb = () => root().getAttribute("viewBox").split(/\s+/).map(Number);
    const holders = { cockpit: !!(board() && board().classList.contains("pannable")) };
    // a press on the background, then a drag: the drawing moves with the pointer, and the click on release opens nothing
    const r = root().getBoundingClientRect(), x = r.left + 4, y = r.top + 4, before = vb(), pansBefore = Pan.pans, focusBefore = App.focus;
    const k = before[2] / r.width;
    let picked = 0;
    const spy = () => { picked++; };
    root().addEventListener("click", spy);
    press(root(), x, y); glide(x + 3, y + 2); glide(x + 80, y + 50); lift(x + 80, y + 50);
    root().dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, clientX: x + 80, clientY: y + 50 }));
    root().removeEventListener("click", spy);
    const after = vb(), moved = [after[0] - before[0], after[1] - before[1]];
    ok(Pan.pans === pansBefore + 1 && Math.abs(moved[0] + 80 * k) < 1 && Math.abs(moved[1] + 50 * k) < 1 && after[2] === before[2] && !picked && App.focus === focusBefore,
      "drag to pan: a drag on the cockpit's background moves the drawing with the pointer, and the release opens nothing",
      `drag to pan: viewBox moved ${moved.map((v) => v.toFixed(1))}, wanted ${[-80 * k, -50 * k].map((v) => v.toFixed(1))}; pans ${Pan.pans - pansBefore}; release clicks ${picked}; focus ${App.focus}`);
    rerender(); await frames();
    const kept = vb();
    ok(Math.abs(kept[0] - after[0]) < 1 && Math.abs(kept[1] - after[1]) < 1 && !overlaps(COCKPIT_PARTS).length, "drag to pan: the pan holds when the cockpit is drawn again, with nothing on anything",
      `drag to pan: after a redraw the viewBox starts at ${kept.slice(0, 2)}, the pan left it at ${after.slice(0, 2)}`);
    root().dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
    const back = vb();
    ok(Math.abs(back[0] - before[0]) < 0.5 && Math.abs(back[1] - before[1]) < 0.5, "drag to pan: a double click on the background puts the drawing back", `after a double click the viewBox starts at ${back.slice(0, 2)}, it began at ${before.slice(0, 2)}`);
    // a press without movement is a click, not a pan; a touch is left to the browser; a press on a box moves the box
    const p0 = Pan.pans;
    press(root(), x, y); lift(x, y);
    press(root(), x, y, "touch"); glide(x + 60, y + 60); lift(x + 60, y + 60);
    const box = $("#board svg.cockpit g.hit[data-movable]"), key = box.dataset.key, cell0 = Layout.cell(key).slice(), br = box.getBoundingClientRect();
    press(box, br.x + br.width / 2, br.y + br.height / 2); glide(br.x + br.width / 2 + 3, br.y + br.height / 2 + 3); glide(br.x + br.width / 2 + 40, br.y + br.height / 2 + 30); lift(br.x + br.width / 2 + 40, br.y + br.height / 2 + 30);
    await flush();
    const cell1 = Layout.cell(key);
    ok(Pan.pans === p0 && JSON.stringify(cell1) !== JSON.stringify(cell0) && Math.abs(vb()[0] - before[0]) < 0.5,
      "drag to pan: a click on the background, a touch drag and a drag on a box do not pan; the box moves instead",
      `drag to pan: ${Pan.pans - p0} pans; box ${titleOf(key)} at ${cell0} then ${cell1}`);
    Layout.restore(layoutWas); rerender(); await frames();
    // where the drawing scrolls, a pan scrolls it
    const room = h("div", { style: "position:fixed;left:0;top:0;width:200px;height:120px;overflow:auto;z-index:99" }), big = s("svg", { width: 900, height: 700, viewBox: "0 0 900 700" }, room);
    document.body.append(room);
    Pan.attach(room, { key: "selftest-scroll", svg: () => big, scrollOnly: true });
    press(big, 100, 60); glide(96, 58); glide(40, 20); lift(40, 20);
    const scrolled = [room.scrollLeft, room.scrollTop], unchanged = big.getAttribute("viewBox");
    room.remove();
    ok(scrolled[0] === 60 && scrolled[1] === 40 && unchanged === "0 0 900 700", "drag to pan: where a drawing scrolls in its holder, a drag on it scrolls the holder by the distance dragged", `drag to pan: scrolled ${scrolled}, viewBox ${unchanged}`);
    // every map drawing can be panned
    MapView.st.lens = "transit"; rerender(); await frames();
    holders.line = !$("#board svg.transit") || !!$("#board svg.transit").closest(".pannable");
    if (D.map.apps.some((a) => a.domain)) { MapView.st.lens = "cockpit"; MapView.st.group = "domain"; rerender(); await frames(); holders.grouped = !!$("#board svg.cockpit.grouped").closest(".pannable"); }
    MapView.st.lens = null; MapView.st.group = null; rerender(); await frames();
    const without = Object.entries(holders).filter(([, v]) => !v).map(([k]) => k);
    ok(!without.length, `drag to pan: the ${Object.keys(holders).join(", ")} drawings can be panned`, `drag to pan: not pannable: ${without.join(", ")}`);
    Pan.reset();
  }
  /* Menus on the diagram are real menus: the item is found where a person finds it, by opening its button first. */
  const menuButton = (id) => $(`[data-dmenu="${id}"] .dmenu-btn`);
  const menuItem = (menu, item) => $(`[data-dmenu="${menu}"] [data-item="${item}"]`);
  const openMenuAt = async (id) => { menuButton(id).click(); await frames(); return $(`[data-dmenu="${id}"] .dmenu-pop`); };
  async function effects() {
    const was = FX.on;
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; FX.set(false); await frames();
    const halos = $$("#board .halo").length, plain = document.documentElement.classList.contains("plain");
    const lampsRight = $$("#board g.hit:not([data-agg])").every((g) => { const lv = D.lights[g.dataset.key] ? D.lights[g.dataset.key].level : "dark"; return g.classList.contains(lv === "dark" ? "dark" : lv); });
    const anim = document.getAnimations ? document.getAnimations().filter((a) => a.playState === "running").length : 0;
    ok(plain && !halos && lampsRight && !anim && reducedMotion(), `effects Plain: no glow (${halos} halos), ${anim} running animations, every lamp still lit as attention.lights says`, `Plain: class ${plain}, ${halos} halos, lamps right ${lampsRight}, ${anim} animations`);
    if (D.flows.length && D.flows[0].hops.length) {
      const r = Motion.trace(D.flows[0].key);
      ok(r.drawn > 0 && $$("#board .m-badge").length === r.drawn, `trace in Plain: ${E[D.flows[0].key].id}'s ${r.drawn} hops lit at once, each numbered`, `trace drew ${r.drawn}, ${$$("#board .m-badge").length} badges`);
    }
    FX.set(true); await frames();
    ok(!document.documentElement.classList.contains("plain") && $$("#board .halo").length === $$("#board g.hit.lit:not(.pending):not([data-agg])").length, `effects On again: ${$$("#board .halo").length} lit lamps glow (a pending approval is a ring, with no halo)`, "effects On did not restore the glow");
    FX.set(was);
    Motion.clear();
  }
  /* The controls ride on the diagram as menus (menus.js): switching views, the keys a menu has, closing, the narrow
     window, and the things that are gone (sound, the Animation switch, Impact and its ripple). */
  async function diagramMenus() {
    const was = { lens: MapView.st.lens, group: MapView.st.group, focus: MapView.st.focus };
    const key = (k, target = document.activeElement) => target.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
    const roleOf = () => document.activeElement.getAttribute("role");
    const within = (el) => { const r = el.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1; };
    Menus.close();
    Nav.open("apps"); MapView.st.lens = null; MapView.st.focus = null; MapView.st.group = "none"; showView("map"); await frames();
    const btn = menuButton("view"), head = $("#main .view-head");
    ok(!!btn && btn.getAttribute("aria-haspopup") === "menu" && btn.getAttribute("aria-expanded") === "false" && head.nextElementSibling === $("#main .dia") && !$("#main .map-tools") && !$$("#main .seg").length,
      "diagram menus: the apps map starts right under its title and lede, with a View menu on the diagram and no row of toggles above it", "diagram menus: the map still has a row of toggles, or the diagram is not right under the lede");
    ok(!!menuButton("group") && !!menuButton("more") && !!$("#focus-btn") && $$("[data-dmenu=view] [role=menuitemradio]").length >= 4,
      "diagram menus: View (four views and Progress), Group, the focus button and the more menu are all there", "diagram menus: a menu or the focus button is missing");
    btn.focus(); key("ArrowDown", btn);
    const pop = $("[data-dmenu=view] .dmenu-pop");
    ok(!pop.hidden && pop.getAttribute("role") === "menu" && btn.getAttribute("aria-expanded") === "true" && roleOf() === "menuitemradio" && document.activeElement.getAttribute("aria-checked") === "true" && within(pop),
      "diagram menus: Down opens the View menu on the chosen view, as a menu with radio items, inside the window", "diagram menus: Down did not open the menu on the chosen item");
    const first = document.activeElement;
    key("ArrowDown"); const second = document.activeElement; key("ArrowUp");
    ok(second !== first && document.activeElement === first, "diagram menus: Down and Up move between the items", "diagram menus: arrows did not move");
    key("End"); const last = document.activeElement; key("Home");
    ok(last !== first && document.activeElement === first, "diagram menus: End and Home jump to the last and first items", "diagram menus: Home and End did not jump");
    key("Escape");
    ok(pop.hidden && btn.getAttribute("aria-expanded") === "false" && document.activeElement === btn, "diagram menus: Escape closes the menu and gives the focus back to its button", "diagram menus: Escape left the menu open or lost the focus");
    const moreFirst = await openMenuAt("more"), groupPop = await openMenuAt("group");
    ok(within(groupPop) && moreFirst.hidden, `diagram menus: the Group menu opens inside the window (${innerWidth} px) and closes the more menu`, "diagram menus: the Group menu runs off the window");
    const morePop = await openMenuAt("more");
    ok(within(morePop) && !!$("[data-item=open-page]", morePop) === !!Nav.sectionPage(), "diagram menus: the more menu opens inside the window and lists Open the page when the section has a page", "diagram menus: the more menu runs off the window");
    Menus.close();
    btn.click(); await frames();
    document.body.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    ok(pop.hidden && btn.getAttribute("aria-expanded") === "false", "diagram menus: a click outside closes the menu", "diagram menus: a click outside left it open");
    btn.click(); menuButton("group").click(); await frames();
    ok(pop.hidden && !$("[data-dmenu=group] .dmenu-pop").hidden, "diagram menus: opening one menu closes the other", "diagram menus: two menus open at once");
    Menus.close();
      const room = Math.max(document.documentElement.scrollWidth - document.documentElement.clientWidth, 0);
      ok(room <= 1, `diagram menus: the page does not scroll sideways at ${innerWidth} px`, `diagram menus: ${room} px of sideways scroll at ${innerWidth} px`);
    // choosing a view from the menu changes the view and the address
    const transit = menuItem("view", "transit");
    transit.click(); await frames();
    ok(MapView.lens() === "transit" && (!D.nodes.length || !!$("#board g.station")) && /lens=transit/.test(location.hash) && menuButton("view").textContent.includes("Contracts only") && !menuButton("group"),
      "diagram menus: picking Contracts only draws the line map, says so on the button, drops the Group menu and puts lens=transit in the address", `diagram menus: lens ${MapView.lens()}, hash ${location.hash}`);
    const animate = menuItem("view", "animate");
    ok(!!animate && animate.getAttribute("role") === "menuitemcheckbox", "diagram menus: Moving markers is a checkbox item in the View menu", "diagram menus: no Moving markers checkbox");
    menuItem("view", "cockpit").click(); await frames();
    menuItem("group", "none").click(); await frames();
    const progress = menuItem("view", "progress");
    if (progress) {
      progress.click(); await frames();
      ok(App.view === "progress" && !!menuButton("view") && menuItem("view", "progress").getAttribute("aria-checked") === "true", "diagram menus: Progress is in the same View menu and the menu is still there once it shows", "diagram menus: Progress lost the View menu");
      menuItem("view", "cockpit").click(); await frames();
      ok(App.view === "map" && MapView.lens() === "cockpit", "diagram menus: from Progress, System map returns to the map", `diagram menus: view ${App.view}`);
    }
    for (const g of [["domain", "domain"], ["capability", "capability"]]) {
      const it = menuItem("group", g[0]);
      if (it && it.getAttribute("aria-disabled") !== "true") { it.click(); await frames(); ok(MapView.group() === g[1] && /group=/.test(location.hash) && menuItem("group", g[0]).getAttribute("aria-checked") === "true", `diagram menus: Group by ${g[0]} groups the map and the address says so`, `diagram menus: group ${MapView.group()}, hash ${location.hash}`); }
    }
    MapView.st.group = "none"; rerender(); await frames();
    // flows: the pickers and the buttons are on the diagram
    if (D.flows.length) {
      showView("flows"); await frames();
      const dia = $("#main .dia");
      ok(!!dia && !!$(".flow-picker", dia) && !!$("#present-btn", dia) && !!menuItem("more", "rehearse") && !!menuItem("more", "clip") && !$("#main .flows-head ~ .flow-actions"),
        "diagram menus: the Flow picker, Present, and Rehearse and Save as video (in the more menu) are on the flow diagram", "diagram menus: a flows control is not on the diagram");
    }
    // asks: Due within is a menu on the board
    if (D.asks.length) {
      showView("asks"); await frames();
      const due = menuItem("due", "30");
      ok(!!due && !$("#main [aria-label='Due within']") && !!$("#main .dia #asks-wrap"), "diagram menus: Due within is a menu on the board of who to ask", "diagram menus: Due within is not on the board");
      if (due) { due.click(); await frames(); ok(Asks.st.days === 30 && menuItem("due", "30").getAttribute("aria-checked") === "true", "diagram menus: picking 30 days shows the questions due in a month", `diagram menus: days ${Asks.st.days}`); Asks.st.days = null; }
    }
    // the Key is a "?" on the diagram, not three open copies of itself
    if (D.map.apps.length) {
      Nav.open("apps"); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; showView("map"); await frames();
      const keyBtn = menuButton("key"), keyPop = $("[data-dmenu=key] .dmenu-pop");
      ok(!!keyBtn && keyPop.hidden && !$$("#main .legend").some((l) => !l.closest(".dmenu-pop")) && !$$("#panel .legend").length,
        "diagram menus: the Key is a ? on the diagram's bar, closed until asked for, and the panel carries no second copy", "diagram menus: the Key is still open on the page or in the panel");
      keyBtn.click(); await frames();
      ok(!keyPop.hidden && keyBtn.getAttribute("aria-expanded") === "true" && within(keyPop) && $$("li", keyPop).length > 0, "diagram menus: the ? opens the Key inside the window, with its entries", "diagram menus: the ? did not open the Key");
      key("Escape", keyPop); await frames();
      ok(keyPop.hidden && document.activeElement === keyBtn, "diagram menus: Escape closes the Key and gives the focus back to the ?", "diagram menus: Escape left the Key open");
    }
    if (D.flows.length) {
      showView("flows"); Flows.st.cur = -1; rerender(); await frames();
      const noPresent = !$$("#main .flow-actions, #main .flows-head ~ .flow-actions").length;
      ok(!$$("#main ol.cap-steps").length && !$("#main .flow-nodes") === false && !$$(".flow-nodes .fn-group b").some((b) => b.textContent === "Steps") && noPresent && !!$("#present-btn"),
        "diagram menus: a flow's steps are written once under the diagram (the current step), not again as a list, and Present is its one button", "diagram menus: a flow's steps are listed twice under the diagram, or Present is missing");
      ok(!!$("[data-dmenu=more] [data-item=rehearse]") && !!$("[data-dmenu=more] [data-item=clip]"), "diagram menus: Rehearse and Save as video are in the flow's menu", "diagram menus: Rehearse or Save as video is missing from the flow menu");
    }
    for (const role of ["product", "eng"]) {
      Nav.role(role); await frames();
      ok(!$$("#main .btn").some((b) => /Present/.test(b.textContent)), `diagram menus: the ${role} door has no Present button on each flow row`, `diagram menus: the ${role} door still has a Present button on a row`);
    }
    // what is gone
    const gone = [typeof Sound === "undefined", !$("#sound"), !$("#fx"), typeof Nav.ripple === "undefined", typeof Motion.ripple === "undefined", typeof FX.setMotion === "undefined", !document.querySelector("[data-motion]")];
    Nav.home(); await frames();
    const app0 = D.map.apps[0];
    if (app0) { go(app0.key, { reset: true }); await frames(); }
    ok(gone.every(Boolean) && !$$("#panel button, #main button").some((b) => /^Impact/.test(b.textContent.trim())),
      "diagram menus: no sound button, no Animation switch, no Impact mode and no ripple are left on the page", `diagram menus: leftovers ${gone.map(Number).join("")}`);
    MapView.st.lens = was.lens; MapView.st.group = was.group; MapView.st.focus = was.focus;
    Menus.close();
  }
  /* The panel's room: hide it and the main area widens, a pick brings it back, a drag stays between the minimum and
     60% of the window, the choice is in storage as a reload would read it, and the views that fit the main area
     (the map, the matrix's frozen edges) still hold after every change. */
  async function panelRoom() {
    if (isCompact()) { out.push("skip the panel room: under " + COMPACT_BELOW + " px it is a slide-over, checked by the compact group"); return; }
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
  /* The sections bar's room, the same rule as the panel's (one EdgeSize serves both): the menu button hides it and the
     main area widens, the handle's drag and arrow keys stay between the minimum and a third of the window, both choices
     are in storage as a reload reads them, and the page never scrolls sideways at the window it was opened in. */
  async function sideRoom() {
    if (isCompact()) { out.push("skip the sections bar room: under " + COMPACT_BELOW + " px it is a slide-over, checked by the compact group"); return; }
    const hidden0 = SideSize.hidden, want0 = SideSize.wanted;
    const mainW = () => $("#main").getBoundingClientRect().width, sideW = () => $("#side").getBoundingClientRect().width;
    const stored = () => ({ hidden: Settings.read("explorer.side"), width: Number(Settings.read("explorer.side.width")) || null });
    const sideways = () => Math.max(document.documentElement.scrollWidth - document.documentElement.clientWidth, document.body.scrollWidth - document.body.clientWidth, $("#main").scrollWidth - $("#main").clientWidth);
    const fitted = () => {
      const b = $("#board"), svg = b && $("svg.cockpit", b);
      if (!svg) return true;
      const r = b.getBoundingClientRect(), v = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
      return (v.right <= r.right + 1 && v.bottom <= r.bottom + 1) || v.width / vb.width <= 0.151;
    };
    SideSize.hide(false); SideSize.setWidth(null, { now: true });
    Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; rerender(); await frames();
    const open = mainW(), openSide = sideW(), toggle = $("#side-toggle"), grip = $("#side-grip");
    toggle.click(); await frames();
    ok(SideSize.hidden && $("#side").offsetParent === null && grip.hidden && mainW() > open + openSide * 0.9 && toggle.getAttribute("aria-expanded") === "false" && stored().hidden === "true",
      `sections bar: the menu button hides it, the main area widens ${Math.round(open)} to ${Math.round(mainW())} px, and the choice is stored`,
      `sections bar hide: main ${Math.round(open)} to ${Math.round(mainW())}, bar shown ${$("#side").offsetParent !== null}, stored ${stored().hidden}`);
    ok(fitted() && sideways() <= 1, "sections bar hidden: the map still fits its board and nothing scrolls sideways", `sections bar hidden: fitted ${fitted()}, sideways ${sideways()} px`);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "[", bubbles: true, cancelable: true })); await frames();
    ok(!SideSize.hidden && $("#side").offsetParent !== null && !grip.hidden && toggle.getAttribute("aria-expanded") === "true" && stored().hidden === "false",
      "sections bar: [ shows it again, and the choice is stored", `sections bar [: hidden ${SideSize.hidden}, stored ${stored().hidden}`);
    SideSize.setWidth(10, { now: true });
    const low = Math.round(sideW());
    SideSize.setWidth(100000, { now: true });
    const high = Math.round(sideW()), cap = SideSize.max();
    ok(low === SideSize.MIN && high === cap && +grip.getAttribute("aria-valuenow") === high && +grip.getAttribute("aria-valuemin") === SideSize.MIN && +grip.getAttribute("aria-valuemax") === cap && grip.getAttribute("role") === "separator" && grip.tabIndex === 0,
      `sections bar: resize clamps to ${low} px at the least and ${high} px (a third of ${innerWidth}) at the most, and the handle, in the tab order, reports both`,
      `sections bar resize: least ${low} (want ${SideSize.MIN}), most ${high} (want ${cap}), aria-valuenow ${grip.getAttribute("aria-valuenow")}`);
    SideSize.setWidth(SideSize.MIN + 20, { now: true });
    grip.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true }));
    const grown = Math.round(sideW());
    grip.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true, cancelable: true }));
    const back = Math.round(sideW());
    ok(grown === SideSize.MIN + 20 + SideSize.STEP && back === SideSize.MIN + 20, `sections bar: the handle's arrow keys move it ${SideSize.STEP} px each way`, `sections bar arrows: ${SideSize.MIN + 20} to ${grown} to ${back}`);
    // a drag: the bar's right edge follows the pointer, and where the drag ends is what is remembered
    const left = $("#side").getBoundingClientRect().left, target = Math.min(SideSize.max(), SideSize.MIN + 60), pid = 7;
    grip.setPointerCapture = () => {}; grip.releasePointerCapture = () => {}; grip.hasPointerCapture = () => false;  // a synthetic pointer has nothing to capture
    grip.dispatchEvent(new PointerEvent("pointerdown", { pointerId: pid, button: 0, clientX: left + sideW(), bubbles: true, cancelable: true }));
    grip.dispatchEvent(new PointerEvent("pointermove", { pointerId: pid, clientX: left + target, bubbles: true }));
    grip.dispatchEvent(new PointerEvent("pointerup", { pointerId: pid, clientX: left + target, bubbles: true }));
    delete grip.setPointerCapture; delete grip.releasePointerCapture; delete grip.hasPointerCapture;
    await frames();
    const dragged = Math.round(sideW());
    ok(dragged === target && stored().width === target && !document.body.classList.contains("side-dragging"), `sections bar: a drag to ${target} px sets the width and stores it, so a reload reads it back`, `sections bar drag: ${dragged} px on screen, ${stored().width} stored, want ${target}`);
    ok(fitted() && sideways() <= 1, `sections bar at ${dragged} px: the main area refits, the map fits its board and nothing scrolls sideways at ${innerWidth} px`, `sections bar resized: fitted ${fitted()}, sideways ${sideways()} px`);
    SideSize.setWidth(null, { now: true });
    ok(stored().width === null && SideSize.wanted === null, "sections bar: the default width comes back, and storage forgets the width", "sections bar default: width still stored");
    SideSize.setWidth(want0, { now: true }); SideSize.hide(hidden0);
    MapView.st.lens = null; MapView.st.group = null; Nav.home(); await frames();
  }
  /* The Slices view: a table whose rows are buttons that fold open by click, Enter and Space, and whose names open the
     panel without folding the row; a Path of the same slices; the layout kept in this browser; search and filter chips
     that narrow both layouts the same way, ride in the address bar and come back from it, and an empty result that says
     so with a way out. */
  async function sliceChecks() {
    const L = Slices.LIST, KEYL = Slices.LAYOUT_KEY, was = Settings.read(KEYL);
    if (!L.length) { out.push("skip slices view: vault has no slices"); return; }
    const sideways = () => Math.max(document.documentElement.scrollWidth - document.documentElement.clientWidth, $("#main").scrollWidth - $("#main").clientWidth, ($(".sl-body") || $("#main")).scrollWidth - ($(".sl-body") || $("#main")).clientWidth);
    const layout = (id) => { $(`[data-dmenu="view"] [data-layout="${id}"]`).click(); };
    const layoutIs = (id) => $(`[data-dmenu="view"] [data-layout="${id}"]`).getAttribute("aria-checked") === "true";
    Slices.clear(); Slices.st.open = new Set(); Slices.st.layout = null; Settings.write(KEYL, "table"); Nav.open("slices"); await frames();
    let rows = $$(".sl-tr");
    ok(rows.length === L.length && rows.every((r) => r.getAttribute("role") === "button" && r.tabIndex === 0 && r.getAttribute("aria-expanded") === "false" && $(".sl-name[data-node]", r)),
      `slices table: ${rows.length} rows, one per slice, each a button in the tab order, folded, with its name wired to the panel`, `slices table: ${rows.length} rows for ${L.length} slices`);
    const r0 = rows[0], more = () => document.getElementById(r0.getAttribute("aria-controls"));
    r0.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true })); await frames();
    const openEnter = r0.getAttribute("aria-expanded") === "true" && !more().hidden && $$(".sl-line", more()).length > 0;
    r0.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true })); await frames();
    const foldSpace = r0.getAttribute("aria-expanded") === "false" && more().hidden;
    $(".sl-c-status", r0).click(); await frames();
    const openClick = r0.getAttribute("aria-expanded") === "true" && !more().hidden;
    const labels = $$(".sl-l", more()).map((l) => l.textContent);
    ok(openEnter && foldSpace && openClick && ["Flows", "Contracts it uses", "Journey", "Quick flow check"].every((w) => labels.includes(w)),
      `slices table: Enter opens a row, Space folds it, a click opens it, and the open row shows ${labels.join(", ")}`, `slices table: Enter ${openEnter}, Space ${foldSpace}, click ${openClick}, lines ${labels.join(", ")}`);
    go("lights", { reset: true }); await frames();
    $(".sl-name", r0).click(); await frames();
    ok(App.focus === (L[0].key || App.focus) && r0.getAttribute("aria-expanded") === "true" && $("#panel h2") && $("#panel h2").textContent.trim() === (L[0].key ? E[L[0].key].title : L[0].name),
      `slices table: a slice's name opens it in the panel ("${L[0].name}") and leaves the row as it was`, `slices table: the name opened "${$("#panel h2") && $("#panel h2").textContent}", row ${r0.getAttribute("aria-expanded")}`);
    $$(".sl-tr[aria-expanded=false]").forEach((r) => r.click()); await frames();
    ok(sideways() <= 1, `slices table, every row open: nothing scrolls sideways at ${innerWidth} px`, `slices table open: scrolls sideways by ${sideways()} px at ${innerWidth} px`);
    // Path, and the layout kept
    layout("path"); await frames();
    const nodes = $$(".sl-node");
    ok(nodes.length === L.length && nodes.every((n) => n.hasAttribute("data-node")) && Settings.read(KEYL) === "path" && layoutIs("path") && !$('.legend[data-legend="slices"]').hidden,
      `slices path: ${nodes.length} boxes, each opening the panel, with its key, and the layout is kept in this browser`, `slices path: ${nodes.length} boxes for ${L.length}, stored ${Settings.read(KEYL)}`);
    const wantArrows = L.reduce((n, x) => n + x.after.filter((k) => L.some((y) => y.slice === k)).length, 0);
    ok($$(".sl-path-arrows path.sl-after").length === wantArrows, `slices path: ${wantArrows} arrows, one for each "comes after"`, `slices path: ${$$(".sl-path-arrows path.sl-after").length} arrows, want ${wantArrows}`);
    ok(sideways() <= 1, `slices path: nothing scrolls sideways at ${innerWidth} px`, `slices path: scrolls sideways by ${sideways()} px`);
    Nav.open("slices"); await frames();
    ok(!!$(".sl-path") && layoutIs("path"), "slices: drawn again, the path is still the layout", "slices: the layout was not kept");
    // a plan of a few slices opens without search and filters; the ... menu brings them (a plan of Slices.FILTERS_FROM or more always has them)
    Slices.st.filters = false; Nav.open("slices"); await frames();
    const few = L.length < Slices.FILTERS_FROM, bare = !$(".sl-find") && !$(".sl-fgroup");
    if (few) {
      const more = $('[data-dmenu="more"] .dmenu-btn'); more.click(); await frames();
      const item = $('[data-dmenu="more"] [data-item="filters"]'), had = !!item;
      if (item) { item.click(); await frames(); }
      ok(bare && had && !!$(".sl-find") && !!$(".sl-fgroup"), `slices: ${L.length} slices (under ${Slices.FILTERS_FROM}) open with no search or filter rows; the ... menu's Search and filter brings them`, `slices: bare ${bare}, menu item ${had}, filters after ${!!$(".sl-find")}`);
    } else ok(!bare, `slices: ${L.length} slices show search and filters at once`, "slices: a big plan has no filters");
    // a filter narrows both layouts the same way, and the address bar carries it
    const counts = {};
    for (const x of L) { const s = x.status || "not planned yet"; counts[s] = (counts[s] || 0) + 1; }
    const [pick, n] = Object.entries(counts).sort((a, b) => a[1] - b[1])[0];
    $(`.sl-fgroup[data-group=status] [data-value="${CSS.escape(pick)}"]`).click(); await frames();
    const hashed = location.hash, inPath = $$(".sl-node").length;
    layout("table"); await frames();
    const inTable = $$(".sl-tr").length, chipCount = +$(`.sl-fgroup[data-group=status] [data-value="${CSS.escape(pick)}"] .ct`).textContent;
    ok(inPath === n && inTable === n && chipCount === n && hashed.includes("sl-status=" + encodeURIComponent(pick)),
      `slices filter: status ${pick} shows ${n} in the path and in the table, its chip says ${chipCount}, and the address bar has it`, `slices filter ${pick}: path ${inPath}, table ${inTable}, chip ${chipCount}, want ${n}; hash ${hashed}`);
    const link = location.hash;
    Slices.clear(); await frames();
    const cleared = $$(".sl-tr").length === L.length && !/sl-/.test(location.hash);
    history.replaceState(null, "", link); Nav.followHash(); await frames();
    ok(cleared && Slices.st.status.has(pick) && $$(".sl-tr").length === n && $(`.sl-fgroup[data-group=status] [data-value="${CSS.escape(pick)}"]`).getAttribute("aria-pressed") === "true",
      `slices filter: the link ${link} opens the same ${n} again, with the chip pressed`, `slices link: cleared ${cleared}, back to ${$$(".sl-tr").length} rows, status ${[...Slices.st.status]}`);
    // search, the empty answer, and Waiting only
    Slices.clear(); await frames();
    const f = L.find((x) => x.flows.some((fl) => fl.key && E[fl.key])), find = $(".sl-find");
    if (f) {
      const word = E[f.flows.find((fl) => fl.key && E[fl.key]).key].title;
      find.value = word; find.dispatchEvent(new Event("input", { bubbles: true })); await frames();
      ok($$(".sl-tr").some((r) => r.dataset.slice === f.slice) && location.hash.includes("sl-find="), `slices search: "${word}", a flow's name, finds the slice that proves it`, `slices search "${word}": rows ${$$(".sl-tr").map((r) => r.dataset.slice)}`);
    }
    find.value = "no slice says this"; find.dispatchEvent(new Event("input", { bubbles: true })); await frames();
    const empty = $(".sl-empty"), clearBtn = empty && [...empty.querySelectorAll("button")].find((b) => b.textContent === "Clear filters");
    ok(!!empty && /No slice matches the words "no slice says this"/.test(empty.textContent) && !!clearBtn, "slices search: nothing found says so in words, with a Clear filters button", `slices empty: ${empty ? empty.textContent : "no message"}`);
    if (clearBtn) { clearBtn.click(); await frames(); }
    ok($$(".sl-tr").length === L.length && $(".sl-find").value === "", "slices: Clear filters shows every slice again", `slices clear: ${$$(".sl-tr").length} rows`);
    const late = L.filter((x) => x.overdue).length, needs = $(".sl-fgroup[data-group=needs] button");
    needs.click(); await frames();
    ok(+$(".ct", $(".sl-fgroup[data-group=needs] button")).textContent === late && (late ? $$(".sl-tr").length === late && $$(".sl-tr .sl-due").length === late : needs.disabled && $$(".sl-tr").length === L.length),
      `slices: Waiting only shows the ${late} with a journey past its due date`, `slices waiting: ${$$(".sl-tr").length} rows, want ${late}`);
    Slices.clear(); Slices.st.open = new Set(); Slices.st.layout = null; Slices.st.filters = false;
    if (was === null) localStorage.removeItem(KEYL); else Settings.write(KEYL, was);
    Nav.home(); go("lights", { reset: true }); await frames();
  }
  async function releases() {
    const S = Releases.STATES;
    ok(D.releases.count ? S.length === D.releases.count + 1 : S.length === 2 && S[1].fromChange, D.releases.count ? `releases: Today and ${plural(D.releases.count, "release")}, from vela.releases` : "releases: none planned, so Today against the end state from each app's change, and the page says so", "release states wrong");
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
     with vela step that writes it; and a flow of inferred arrows says so once. */
  /* A vault that gains a vault_id keeps what the browser saved under its old id (E18), against a fake store. */
  /* Keys the page owns must leave fields and controls alone (E34, E35). */
  /* The page's Content-Security-Policy stops an inline handler from vault text (E38). */
  async function policy() {
    window.__cspRan = false;
    const holder = h("div");
    document.body.append(holder);
    holder.innerHTML = '<img alt="" src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAACAkQBADs=" onload="window.__cspRan = true">';
    const probe = holder.firstChild;
    await new Promise((resolve) => { if (probe.complete) resolve(); else { probe.addEventListener("load", resolve); probe.addEventListener("error", resolve); } });
    holder.remove();
    ok(!!document.querySelector('meta[http-equiv="Content-Security-Policy"]') && window.__cspRan === false, "policy: the page carries a Content-Security-Policy and an inline handler in vault text does not run", `policy: meta present ${!!document.querySelector('meta[http-equiv="Content-Security-Policy"]')}, injected onload ran ${window.__cspRan}`);
  }
  /* Browser Back and a pasted link move the page (E33). Needs a real address bar, so it runs on a file or a served page alike. */
  async function history_() {
    const changed = (act) => new Promise((resolve) => { addEventListener("hashchange", resolve, { once: true }); act(); });
    Nav.home(); Nav.open("decisions", ""); Nav.open("unknowns", "");
    const before = App.section;
    await changed(() => history.back());
    const back = App.section;
    await changed(() => { location.hash = "#s=goals"; });
    const pasted = App.section;
    await changed(() => history.back());
    ok(before === "unknowns" && back === "decisions" && pasted === "goals", "history: Back returns to the section the lead came from, and a pasted #s= link opens that section",
      `history: before ${before}, after Back ${back} (wanted decisions), after a pasted link ${pasted} (wanted goals)`);
    Nav.home();
  }
  /* The search box is a combobox a screen reader can follow (E22). */
  function searchAria() {
    const q = $("#q"), word = (Object.values(E).map((e) => (e.title || "").split(/\s+/).find((w) => /^[A-Za-z]{4,}$/.test(w))).find(Boolean)) || "vault";
    Search.type(word);
    const opts = $$("#results [role=option]"), on = opts.find((o) => o.getAttribute("aria-selected") === "true");
    if (!opts.length) out.push(`skip search combobox: "${word}" finds nothing in this vault`);
    else ok(q.getAttribute("role") === "combobox" && q.getAttribute("aria-controls") === "results" && q.getAttribute("aria-expanded") === "true" && !!on && q.getAttribute("aria-activedescendant") === on.id && opts.every((o) => o.id),
      "search: the box is a combobox; the open list is expanded, every result has an id and the highlighted one is the active descendant", `search: role ${q.getAttribute("role")}, expanded ${q.getAttribute("aria-expanded")}, ${opts.length} options, selected ${on && on.id}, active ${q.getAttribute("aria-activedescendant")}`);
    Search.type("zzqqxx nothingmatches");
    const said = $("#results-status").textContent;
    ok(!!said && !$("#results [role=option]") && !q.getAttribute("aria-activedescendant"), "search: a search that finds nothing is said aloud, with no active descendant", `search: status "${said}"`);
    q.value = ""; Search.type(""); 
    ok(q.getAttribute("aria-expanded") === "false" && $("#results-status").textContent === "", "search: an emptied box collapses and goes quiet", `search: expanded ${q.getAttribute("aria-expanded")}`);
  }
  function keyboard() {
    const press = (target, key) => { const ev = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }); target.dispatchEvent(ev); return ev; };
    const box = h("textarea"), button = h("button", {}, "Next step");
    document.body.append(box, button);
    box.focus(); press(box, "/");
    const stayed = document.activeElement === box;
    const view = App.view; if (D.flows.length) showView("flows");  // the player's keys only act in the flows view
    button.focus(); const space = press(button, " "), arrow = press(button, "ArrowRight");
    showView(view);
    document.body.focus(); press(document.body, "/");
    const toSearch = document.activeElement === $("#q");
    box.remove(); button.remove(); $("#q").blur();
    ok(stayed && toSearch, "keys: / types a slash in a text field and jumps to search from anywhere else", `keys: / stayed in the field ${stayed}, reached search from the page ${toSearch}`);
    ok(!space.defaultPrevented && !arrow.defaultPrevented, "keys: Space and the arrows are left to a focused button, so Next and Play can be pressed", `keys: Space prevented ${space.defaultPrevented}, arrow prevented ${arrow.defaultPrevented}`);
  }
  /* A saved value that will not parse is kept and reported, not replaced by an empty one (E31). */
  function corruptState() {
    const key = "explorer.selftest.corrupt", warn = console.warn; let said = "";
    console.warn = (m) => { said = String(m); };
    Settings.write(key, "{not json");
    const got = Settings.readJson(key, { fresh: true }, "the selftest's marks");
    console.warn = warn;
    const kept = Settings.read(key + ".unreadable"), note = $("#toast").textContent;
    localStorage.removeItem(key); localStorage.removeItem(key + ".unreadable");
    ok(got.fresh === true && kept === "{not json" && /cannot be read/.test(said) && /Could not read/.test(note), "saved state: a value that will not parse is kept under .unreadable, logged, and the page says so", `saved state: got ${JSON.stringify(got)}, kept ${kept}, log "${said}", note "${note}"`);
  }
  function savedState() {
    const data = { "asks:old1": "board", "explorer.layout.old1": "layout", "explorer.ask.old1": "chats", "rehearse:old1:FLO-001": "tries", "asks:other": "x", "asks:new1": "kept" };
    const fake = { get length() { return Object.keys(data).length; }, key: (i) => Object.keys(data)[i], getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; } };
    const copied = migrateSaved("old1", "new1", fake);
    ok(data["explorer.layout.new1"] === "layout" && data["explorer.ask.new1"] === "chats" && data["rehearse:new1:FLO-001"] === "tries" && data["asks:new1"] === "kept" && data["asks:other"] === "x" && data["asks:old1"] === "board",
      "saved state: marks, layout, conversations and rehearsals move to a new vault id once; what is already there is kept; the old copy stays", `saved state: ${JSON.stringify(data)}`);
    ok(copied.length === 3 && !migrateSaved("old1", "old1", fake).length, "saved state: only the keys that were missing are copied, and the same id moves nothing", `saved state: copied ${copied.length}`);
  }
  async function emptyStates() {
    const has = (root, text) => $$(".empty-state", root).some((e) => e.dataset.empty === text);
    const doorHas = async (role, text) => { Nav.role(role); await frames(); return has($(".door"), text); };
    if (D.map.apps.length) {
      Nav.home(); MapView.st.lens = "cockpit"; MapView.st.focus = null; MapView.st.group = "none"; rerender(); await frames();
      for (const [id, key, writer] of [["domain", "domain", "/vela:boundary"], ["capability", "capability", "/vela:requirements"]]) {
        await openMenuAt("group");
        const btn = menuItem("group", id), off = !D.grouping[key], disabled = !!btn && btn.getAttribute("aria-disabled") === "true";
        ok(!!btn && disabled === off && (!off || /nothing to group by/.test(btn.title)), `group by ${id}: ${off ? "disabled, the tooltip says there is nothing to group by yet" : "offered"}`, `group by ${id}: ${btn ? `disabled ${disabled}` : "no item"}, title "${btn ? btn.title : ""}", wanted ${off ? "off" : "on"}`);
      }
      MapView.st.group = null; rerender();
    } else out.push("skip group buttons: vault has no apps");
    if (!D.releases.count) {
      Nav.open("releases"); await frames();
      ok(has($("#main"), "No releases yet, so this shows today against where every app ends up.") && !/04b-releases\.md/.test($("#main").textContent) && (!D.nodes.length || !!$("#main .rel-grid")),
        "releases: the empty state says none are recorded, names no file, and the Today against end-state comparison renders under it", "releases: no empty state, or no comparison under it");
      if (D.map.apps.length) { MapView.st.lens = "releases"; showView("map"); rerender(); await frames(); ok(has($("#board"), "No releases yet, so this shows today against where every app ends up."), "map Releases lens: the same empty state above the comparison", "map Releases lens has no empty state"); MapView.st.lens = null; }
    } else out.push("skip releases empty state: the vault records releases");
    if (D.map.apps.length) {
      Nav.role("exec"); await frames();
      ok(!!$(".door [data-to='releases']") && !$(".door .mini-time"), "exec door: the release timeline is one link away (Releases carries it and its empty state), not drawn again here", "exec door: no link to Releases, or the timeline is drawn here again");
      ok(D.releases.count || await doorHas("product", "No releases yet."), "product door: what each release delivers names 04b-releases.md", "product door: no empty state for releases");
      if (!D.trace.requirements.length && D.trace.capabilities.length) ok(await doorHas("product", "No requirements written yet, so none is assigned to an app."), "product door: the requirement cards name /vela:requirements and /vela:allocate", "product door: no empty state for requirements");
      if (!D.trace.epics.length) ok(await doorHas("qa", "No epics yet."), "QA door: criteria cards name /vela:epics", "QA door: no empty state for epics");
    }
    if (!D.trace.requirements.length) { showView("trace"); await frames(); ok(has($("#main"), "No requirements yet, so each capability goes straight to its epics.") && /allocate/.test($("#main .empty-state").textContent), "trace: requirement level says no requirements are written and which steps write them", "trace: no empty state for missing requirement rows"); }
    if (!D.flows.length) {
      showView("flows"); await frames();
      ok(has($("#main"), "No flows yet.") && $("#main .es-writer").textContent.includes("the boundary session"), "flows view: 'No flows yet', written in the boundary session", "flows view: no empty state");
      Search.type("how does it work"); await frames();
      ok(has($("#results"), "No flows yet, so a \"how does…\" question has nothing to answer it.") && !$("#results").hidden, "search 'how does ...': says there are no flows rather than return nothing", "search 'how does': nothing said about missing flows"); Search.type("");
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
      ok(racks === unrecorded, `who to ask: ${plural(racks, "rack")} labeled as placed by owner, since their questions have no Ask line`, `who to ask: ${racks} labeled racks, wanted ${unrecorded}`);
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
      ok(!$("#results .r-ask") && !rowText && !/Claude/.test($("#results").textContent),
        "ask on a file: the results have no Claude row at all, so no dead end sits first", `ask on a file: row says "${rowText}"`);
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
      // every file link the served page offers reaches its file through the helper (a design outside the vault offers none)
      const hrefs = [...Object.values(E).filter((e) => e.path).slice(0, 4).map((e) => openHref("", e.path)), ...Object.values(D.designs).map((d) => openHref(d.href, d.vaultPath)).filter(Boolean)];
      const missed = [];
      for (const href of hrefs) { const res = await realFetch(href); if (!res.ok) missed.push(`${href} ${res.status}`); }
      ok(hrefs.length > 0 && !missed.length, `served: ${plural(hrefs.length, "Open the file link")} each reach their file through the helper`, `served: Open-the-file links that reach nothing: ${missed.join(", ") || "none offered"}`);
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
      "| Thing | Where |\n|---|---|\n", `| Alpha | [[${id}]] |\n| Beta | [[${id}|a labeled link]] in a cell |\n\n`, "```js\nconst x = 1 < 2;\n```\n\n",
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
    const rows = a1 ? $$("table tr", a1) : [];
    ok(rows.length >= 3 && rows.every((r) => r.children.length === 2) && /a labeled link/.test(rows[2].textContent),
      "ask, fake helper: a table row's [[ID|label]] keeps its pipe: the row has 2 cells, not 3", `ask, fake helper: table cells per row ${rows.map((r) => r.children.length)}`);
    const dead = a1 && $(".ask-unknown", a1);
    ok(!!dead && /ZZZ-999/.test(dead.textContent) && /not in this vault/.test(dead.textContent), "ask, fake helper: [[ZZZ-999]] is flagged as not in this vault", "ask, fake helper: the unknown ID is not flagged");
    if (withToc) {
      const unknown = $$(".ask-unknown", a1).map((c) => c.textContent);
      const labeled = ["the stem link", "the base link"].every((l) => $$(`.ref-chip[data-ref^="${CSS.escape(withToc)}"], .ref-chip[data-ref^="read:${CSS.escape(withToc)}"]`, a1).some((c) => c.textContent.includes(l)));
      ok(unknown.length === 1 && labeled, "ask, fake helper: Obsidian links ([[path|label]], [[file#heading|label]]) are chips showing their label, and only ZZZ-999 is flagged",
        `ask, fake helper: flagged ${JSON.stringify(unknown)}, labeled chips ${labeled}`);
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
      const a = $("#main .ask-a"), bg = getComputedStyle($("#main")).backgroundColor, color = (el) => getComputedStyle(el).color;
      if (!a || color(a) === bg || !$(".ask-unknown", a) || color($(".ask-unknown", a)) === bg || color($("th", a)) === getComputedStyle($("th", a)).backgroundColor || color($("a[href]", a)) === bg) bad.push(plain ? "plain" : t);
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
  /* The work queue beside the map, and the panel that complements it. The queue is a short ranked list of the open
     questions that hold something up, in plain words; the panel lists the lit things on the map, not the same
     questions again, and carries the queue itself only where the queue is not on the page. */
  async function queueChecks() {
    const q = Queue.items(), top = Math.min(Queue.TOP, q.length), rows = () => $$(".home-stage .q-row");
    const ranked = q.every((x, i) => !i || rank(q[i - 1].level) > rank(x.level) || (q[i - 1].level === x.level && q[i - 1].urgency >= x.urgency));
    ok(ranked && q.every((x) => x.level === ASK[x.id].light.level), `queue: ${q.length} open questions that hold something, in attention's order (level, then urgency), each lamp the question's own light`, "queue: the order or a lamp is not attention's");
    const held = new Set([...D.above.map((a) => a.unknown), ...Object.values(D.blockedBy).flat()].filter((u) => isOpen(ASK[u])));
    ok(held.size === q.length && [...held].every((u) => q.some((x) => x.id === u)), `queue: every open question that holds something is listed once (${held.size}), not once per thing it holds (${D.above.length} held above the map)`, `queue: ${q.length} listed for ${held.size} holding questions`);
    ok(rows().length === top && rows().every((r) => !/^[A-Z]+-\d+/.test($(".q-title", r).textContent) && !/\b(UNK|CAP|EPC|CON|APP)-\d/.test(r.textContent) && r.title === ASK[r.dataset.ref].question && r.dataset.ref),
      `queue: the top ${top} show in plain words, with what each holds up and who to ask; the tooltip is the question, the ID rides in data-ref only`, "queue: a row shows an ID or its tooltip isn't the question");
    ok(rows().every((r) => /^Blocks /.test($(".q-sub", r).textContent) && /^Ask: /.test($(".q-ask", r).textContent) && $(".q-when b", r).textContent.trim()), "queue: each row says what it holds up, who to ask and by when", "queue: a row lacks what it holds, who to ask or when");
    ok(rows().every((r, i) => $(".lamp", r).classList.contains(q[i].level)) && $$(".home-stage .q-row .lamp").length === rows().length, "queue: a small lamp, not a painted row, carries the level", "queue: a row's lamp is not its level");
    const card = $(".q-card"), map = $(".home-map"), a = card.getBoundingClientRect(), b = map.getBoundingClientRect();
    const apart = a.right <= b.left + 1 || a.bottom <= b.top + 1;  // beside the map, or folded above it
    const bar = $(".home-map .dia-bar"), tb = bar && bar.getBoundingClientRect(), board = $(".home-map #board");
    ok(!!bar && !!board && tb.bottom <= board.getBoundingClientRect().top + 1 && !$(".home-tools") && !!$("[data-dmenu=view]", bar), "queue: the map's menus sit on the top of the map itself, with no row of toggles above the waiting card", "queue: the map's menus are not on the map");
    ok(apart && b.height > 150, `queue: the card and the map do not overlap, and the map keeps ${Math.round(b.height)} px of height (${innerWidth}x${innerHeight})`, `queue: card ${Math.round(a.left)}..${Math.round(a.right)} x ${Math.round(a.top)}..${Math.round(a.bottom)} meets the map ${Math.round(b.left)}..${Math.round(b.right)} x ${Math.round(b.top)}..${Math.round(b.bottom)}`);
    if (q.length > Queue.TOP) {
      $(".q-more").click(); await frames();
      const groups = $$(".home-stage .q-group"), sum = groups.reduce((n, g) => n + (+$(".ct", g).textContent), 0);
      ok(rows().length === q.length && sum === q.length && groups.every((g) => $$(".q-row", g).length === +$(".ct", g).textContent), `queue: Show all ${q.length} groups them by what they hold (${groups.map((g) => $("h4", g).firstChild.textContent).join(", ")}), counts adding up`, `queue: ${rows().length} rows in ${groups.length} groups, counts ${sum}, wanted ${q.length}`);
      $(".q-more").click(); await frames();
      ok(rows().length === top, `queue: Show the top ${Queue.TOP} folds it back to ${top}`, "queue: the list did not fold back");
    }
    if (q.length) {
      rows()[0].click(); await frames();
      ok(App.focus === q[0].id && $("#panel h2").textContent === q[0].title && rows()[0].classList.contains("on"), `queue: picking "${q[0].title}" opens it in the panel and marks the row`, `queue: focus ${App.focus}, panel "${$("#panel h2").textContent}"`);
    }
    go("lights", { reset: true }); await frames();
    const lit = litSubjects();
    ok($$("#panel .q-row").length === 0 && $$("#panel .light-row").length === lit.length, `panel home: ${lit.length} lit things on the map, and none of the ${q.length} queued questions repeated beside the queue`, `panel home: ${$$("#panel .q-row").length} queue rows and ${$$("#panel .light-row").length} lit rows beside the queue`);
    Nav.open("goals"); go("lights", { reset: true }); await frames();
    ok($$("#panel .q-row").length === top, `panel home, away from the home page: carries the queue (${top} of ${q.length}) because the page does not`, `panel home on Goals: ${$$("#panel .q-row").length} queue rows`);
    const need = Queue.needsYou(), counts = Queue.counts(), masters = Object.fromEntries($$("#masters .master").map((m) => [m.className.split(" ").find((c) => LEVELS.includes(c)), +$("b", m).textContent]));
    ok(masters.caution === need.n && (masters.warning || 0) === need.late && Object.entries(masters).every(([lv, n]) => lv === "caution" || n === counts[lv]),
      `top bar: ${need.n} waiting, ${need.late} of them overdue; ${Object.entries(masters).filter(([lv]) => lv !== "caution" && lv !== "warning").map(([lv, n]) => `${n} ${lv}`).join(", ") || "nothing else lit"}`, `top bar ${JSON.stringify(masters)} against needs-you ${JSON.stringify(need)}`);
    // "waiting" is shown as a number once on Home, in the top bar (label sweep: the same 21 showed four times). The
    // side door shows only the overdue part, the waiting card says what to start with, and the panel doesn't repeat either.
    Nav.home(); go("lights", { reset: true }); await frames();
    const door = $(".side-home .side-n"), qcount = $(".q-card .q-count"), lede = $("#panel .p-lede"), says = Queue.needsYouSays();
    const homeText = [$("#main"), $("#side"), $("#panel")].map((x) => (x ? x.textContent : "")).join(" ");
    ok((need.late ? door && +door.textContent === need.late : !door) && (!need.n || (qcount && qcount.textContent === Queue.startWith())) && (!need.n || !homeText.includes(says)) && !(lede && /\d+ waiting/.test(lede.textContent)),
      `waiting: ${need.n} in the top bar only; the side door shows ${need.late ? need.late + " overdue" : "no number"}, the waiting card says "${Queue.startWith()}", and the panel doesn't repeat the count`,
      `waiting: side door ${door && door.textContent} (want ${need.late || "none"}), card "${qcount && qcount.textContent}", panel "${lede && lede.textContent.slice(0, 80)}", "${says}" ${homeText.includes(says) ? "repeated on the page" : "not repeated"}`);
    Nav.home(); go("lights", { reset: true }); await frames();
  }

  /* The decision log: a table that sorts and filters, and a decision record per row. */
  async function decisionChecks() {
    showView("decisions"); await frames();
    const all = Decisions.trees.length, base = Decisions.entries.filter((e) => !e.bare), rows = () => $$(".dl-row");
    if (!all) { ok(!!$("#main .empty-state"), "decisions: no decision records its options, and the view says so", "decisions: nothing listed and no empty state"); return; }
    ok(rows().length === base.length && $$(".dl-name").every((n) => n.textContent.trim()), `decisions: ${base.length} in the log, each with a plain name${Decisions.entries.length > base.length ? `; ${Decisions.entries.length - base.length} decided pages with no options are kept behind a filter` : ""}`, `decisions: ${rows().length} rows for ${base.length} decisions`);
    ok(viewDef("decisions").alias === "garden", "decisions: the old #garden route still lands here", "decisions: the #garden alias is gone");
    const cells = rows().slice(0, 3).every((r) => { const rs = $$(".dl-c", r).map((c) => c.getBoundingClientRect()); return rs.every((x, i) => rs.every((y, j) => i >= j || x.right <= y.left + 1 || y.right <= x.left + 1 || x.bottom <= y.top + 1 || y.bottom <= x.top + 1)); });
    ok(cells, "decisions: the cells of a row do not overlap", "decisions: cells of a row overlap");
    const states = Decisions.STATES.filter(([id]) => base.some((e) => e.state === id));
    for (const [id, word] of states.slice(0, 2)) {
      $(`[data-state="${id}"]`).click(); await frames();
      const want = base.filter((e) => e.state === id).length;
      ok(rows().length === want && rows().every((r) => $(".dl-state .pill", r).textContent.includes(word)), `decisions: filtering to ${word} shows ${want}`, `decisions: ${word} filter shows ${rows().length}, wanted ${want}`);
      $(`[data-state="${id}"]`).click(); await frames();
    }
    $('[data-sort="name"]').click(); await frames();
    const names = $$(".dl-name").map((n) => n.textContent.trim().toLowerCase()), sorted = names.slice().sort((x, y) => cmp(x, y));
    ok(JSON.stringify(names) === JSON.stringify(sorted) && $('[data-sort="name"]').getAttribute("aria-sort") === "ascending", "decisions: sorting by Decision puts the names in order, and the header says so", `decisions: sort by name gave ${names.slice(0, 3).join(" | ")}`);
    $('[data-sort="name"]').click(); await frames();
    ok($('[data-sort="name"]').getAttribute("aria-sort") === "descending" && $$(".dl-name")[0].textContent.trim().toLowerCase() === sorted[sorted.length - 1], "decisions: the same header again reverses it", "decisions: the second click did not reverse the order");
    $('[data-sort="state"]').click(); await frames();
    const first = base[0], word = first.name.split(/\s+/).find((w) => w.length > 3) || first.name;
    const find = $(".dl-find"); find.value = word; find.dispatchEvent(new Event("input")); await frames();
    ok(rows().length >= 1 && rows().length <= base.length && document.activeElement !== null, `decisions: finding "${word}" leaves ${rows().length} of ${base.length}`, `decisions: search for "${word}" left ${rows().length}`);
    find.value = "zzzz-no-such-decision"; find.dispatchEvent(new Event("input")); await frames();
    ok(!rows().length && !!$(".dl-none"), "decisions: a search that matches nothing says so and offers to clear the filters", "decisions: an empty search shows nothing and says nothing");
    find.value = ""; find.dispatchEvent(new Event("input")); await frames();
    const pick = Decisions.visible()[0];
    rows()[0].click(); await frames();
    const rec = $(".dl-detail"), chosen = rec && $$(".dl-options .chosen", rec).length, turned = rec ? $$(".dl-options .rejected", rec).length : -1;
    ok(!!rec && $("h2", rec).textContent === pick.name && chosen === 1 && turned === pick.rejected.length, `decisions: opening "${pick.name}" shows its record with the choice and ${turned} option${turned === 1 ? "" : "s"} turned down, each with its reason`, `decisions: record ${!!rec}, chosen ${chosen}, turned down ${turned} of ${pick.rejected.length}`);
    ok(["Context", "Options considered", "Decision", "Consequences", "History"].every((s) => $$(".dl-sec h3", rec).some((x) => x.textContent === s) || (s === "Context" && !pick.t.carriedBy[0].text)), "decisions: the record has its context, options, decision, consequences and history", "decisions: a section of the record is missing");
    const lr = $(".dl-listwrap"), dr = rec.getBoundingClientRect(), ls = lr.getBoundingClientRect(), hidden = getComputedStyle(lr).display === "none";
    ok(hidden || ls.right <= dr.left + 1, "decisions: the list and the record sit side by side or the record takes the room, never over one another", `decisions: list ${Math.round(ls.left)}..${Math.round(ls.right)} meets the record from ${Math.round(dr.left)}`);
    const adr = base.find((e) => e.t.adr);
    if (adr) { Decisions.select(""); Decisions.showFor(adr.t.adr.key); await frames(); ok($(".dl-detail h2").textContent === adr.name, `decisions: a link to ${adr.t.adr.id} opens its record, ${adr.name}`, `decisions: ${adr.t.adr.id} opened "${($(".dl-detail h2") || { textContent: "nothing" }).textContent}"`); }
    Decisions.select(""); await frames();
    $('[data-mode="timeline"]').click(); await frames();
    const tl = $$(".dl-tl");
    ok(tl.length === Decisions.visible().length && !$$(".dl-row").length, `decisions: the timeline lists the same ${tl.length}, by month`, `decisions: timeline ${tl.length} of ${Decisions.visible().length}`);
    $('[data-mode="log"]').click(); await frames();
    ok(!$$("#main svg.sheet").length, "decisions: no drawing stands in for the data", "decisions: a sheet drawing is still there");
  }
  /* Plain names in prose: a bare ID the vault holds reads as its name with the ID in the tooltip, and a Trace line is
     one folded row of name chips. Both are read from the pages this vault ships; a vault with neither says so. */
  async function plainNames() {
    const boxes = Object.keys(D.reader).map((k) => h("div", { html: D.reader[k].html }));
    const named = boxes.flatMap((b) => $$("a.idname", b)), rows = boxes.flatMap((b) => $$("details.r-trace", b));
    if (!named.length) out.push("skip plain names: no page here writes a bare ID the vault holds");
    else {
      const bad = named.filter((a) => { const id = a.getAttribute("title"), label = [...a.childNodes].filter((n) => !(n.classList && n.classList.contains("idsuf"))).map((n) => n.textContent).join("").trim(); return !id || !label || label === id || !ent(a.dataset.ref); });
      ok(!bad.length, `plain names: ${named.length} bare IDs in prose read as their names, the ID in the tooltip`, `plain names: ${bad.length} of ${named.length} bare IDs lost their name or tooltip, first ${bad[0] && bad[0].outerHTML}`);
      const host = h("div", {}, named.slice(0, 1).map((a) => a.cloneNode(true))); document.body.append(host);
      const suffix = $(".idsuf", host), shown = suffix && getComputedStyle(suffix).display !== "none";
      host.remove();
      ok(!!suffix && !shown, "plain names: the muted ID suffix stays hidden until hover", "plain names: the ID suffix shows without hover");
    }
    // A question's state pill beside its link: a real space between them, so copied text reads "made (resolved)" and
    // never "madeopen"; and no "open" pill in running prose, where open is the default and only noise.
    const pills = boxes.flatMap((b) => $$(".ustate", b));
    if (!pills.length) out.push("skip state pills: no page here links a question with a state worth flagging");
    else {
      const glued = pills.filter((p) => { const prev = p.previousSibling; return !(prev && prev.nodeType === 3 && /\s$/.test(prev.nodeValue)); });
      const labeled = pills.filter((p) => !p.getAttribute("aria-label") || !/^\(.*\)$/.test(p.textContent));
      ok(!glued.length && !labeled.length, `state pills: ${pills.length} pills, each set off from its link by a space, with an accessible label and parentheses that copy`, `state pills: ${glued.length} glued to the link (first ${glued[0] && glued[0].parentNode.textContent.slice(0, 60)}), ${labeled.length} unlabeled`);
    }
    const proseOpen = boxes.flatMap((b) => $$("p .ustate.us-open, blockquote .ustate.us-open, h1 .ustate.us-open, h2 .ustate.us-open, h3 .ustate.us-open", b)).filter((p) => !p.closest("li, td, th"));
    ok(!proseOpen.length, "state pills: no 'open' pill in running prose", `state pills: ${proseOpen.length} 'open' pills in prose, first after ${proseOpen[0] && proseOpen[0].previousElementSibling && proseOpen[0].previousElementSibling.textContent}`);
    if (!rows.length) out.push("skip trace rows: no page here carries a Trace line");
    else {
      const bad = rows.filter((r) => !$("summary", r) || !$$("a.chip", r).length || $$("a.chip", r).some((a) => !ent(a.dataset.ref) || /^[A-Z]+-\d+/.test(a.textContent.trim())));
      ok(!bad.length && rows.every((r) => !r.open), `trace rows: ${rows.length} Trace lines are folded rows of name chips`, `trace rows: ${bad.length} rows lack a summary, a chip, or show an ID as a chip name`);
    }
  }
  async function run() {
    out.length = 0;
    const parity = Search.parity(), bad = parity.filter((p) => !p.same);
    out.push(bad.length ? `FAIL SEARCH PARITY ${bad.length} of ${parity.length}: ` + JSON.stringify(bad) : `ok SEARCH PARITY ${parity.length} of ${parity.length} queries rank exactly as vela query search`);
    try { await livePaths(); await thread(); await views(); await navigation(); await doors(); await scale(); await ungrouped(); await moves(); await panning(); await effects(); await diagramMenus(); await panelRoom(); await sideRoom(); await sliceChecks(); await releases(); savedState(); corruptState(); keyboard(); searchAria(); await history_(); await policy(); await emptyStates(); await askChecks(); await plainNames(); }
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
      const nb = MapGroups.neighbors(k), want = 1 + new Set([...nb.uses.keys(), ...nb.usedBy.keys()]).size, shown = +(($("#inside-stage #board") || { dataset: {} }).dataset.shown);
      ok(shown === want && $(".inside-crumbs .cur").textContent === "Context", `inside ${name}, context: it and its ${want - 1} direct neighbors, as the map's Focus`, `inside ${name}, context: shown ${shown}, wanted ${want}`);
      Inside.open(k, "containers");
      const c = D.containers[k], boxes = $$("#inside-stage .in-box.container").length;
      if (c && c.rows.length) {
        const o = overlaps();
        ok(boxes === c.rows.length && !o.bad.length, `inside ${name}, containers: ${boxes} from its page's table, ${o.n} boxes and labels, no two overlap`, `inside ${name}, containers: ${boxes} of ${c.rows.length}; overlaps ${o.bad.slice(0, 3).join("; ")}`);
      } else ok(!!$("#inside-stage .inside-chip-card"), `inside ${name}, containers: its page has none, and the chip says so`, `inside ${name}, containers: no table and no chip`);
      Inside.open(k, "components");
      if (!d) {
        const say = ($("#inside-stage .inside-chip-card") || { textContent: "" }).textContent;
        ok(/hasn't shared a design yet/.test(say) && say.includes("--design"), `inside ${name}, components: no design, so the chip says how to load one with --design`, `inside ${name}, components: no design and no chip ("${say.slice(0, 60)}")`);
        continue;
      }
      if (d.summary && d.summary.text) {  // a summary-first design (/vela:design) opens its panel on the summary, then the walking skeleton
        const body = h("div", {}, ...Inside.panel(Inside.designKey())), first = $(".p-body > *", body), skel = [...$$(".p-body *", body)].some((x) => x.textContent.trim() === "Walking skeleton");
        const wantSkel = !!(d.walking_skeleton && Object.keys(d.walking_skeleton.fields || {}).length);
        ok(!!first && first.classList.contains("in-summary") && skel === wantSkel, `inside ${name}: the design panel opens on its summary${wantSkel ? ", with the walking skeleton below" : ""}`,
          `inside ${name}: the design panel opens on ${first ? first.className : "nothing"}; walking skeleton shown ${skel}, wanted ${wantSkel}`);
      }
      const comps = $$("#inside-stage .in-box.component").length, stubs = $$("#inside-stage .in-stub").length, o = overlaps();
      ok(comps === d.components.length && stubs === d.stubs.length && !o.bad.length, `inside ${name}, components: ${comps} components and ${stubs} integration stubs, ${o.n} boxes and labels, no two overlap`,
        `inside ${name}, components: ${comps} of ${d.components.length}, ${stubs} of ${d.stubs.length} stubs; overlaps ${o.bad.slice(0, 3).join("; ")}`);
      {  // drag to pan (pan.js): the drawing's background scrolls its holder
        const holder = $("#inside-draw"), svg = $("svg", holder), was = [holder.scrollLeft, holder.scrollTop], r = svg.getBoundingClientRect();
        const can = holder.scrollWidth > holder.clientWidth + 1, ev = (type, x, y) => new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, buttons: 1, isPrimary: true, pointerId: 11, pointerType: "mouse" });
        // drag toward the side with room: a holder scrolled to its right end only moves when dragged rightward
        const dx = holder.scrollLeft > 0 ? 40 : -40, at = [r.left + 2, r.top + 2];
        svg.dispatchEvent(ev("pointerdown", at[0], at[1])); window.dispatchEvent(ev("pointermove", at[0] + Math.sign(dx) * 6, at[1])); window.dispatchEvent(ev("pointermove", at[0] + dx, at[1])); window.dispatchEvent(ev("pointerup", at[0] + dx, at[1]));
        const went = Math.abs(holder.scrollLeft - was[0]);
        holder.scrollLeft = was[0]; holder.scrollTop = was[1];
        ok(holder.classList.contains("pannable") && (!can || went > 0), `inside ${name}, components: the drawing can be panned by dragging its background${can ? ` (it scrolled ${went} px)` : ""}`, `inside ${name}, components: pannable ${holder.classList.contains("pannable")}, scrolled ${went} px of a possible ${holder.scrollWidth - holder.clientWidth}`);
      }
      {  // opens at a size a reader can read, with the whole in a minimap; "Whole" fits all of it, and the tabs fold away
        const holder = $("#inside-draw"), box = holder.getBoundingClientRect(), svg = $("svg", holder).getBoundingClientRect(), scale = +holder.dataset.scale;
        const spills = svg.width > box.width + 1 || svg.height > box.height + 1;  // the minimap's own test: the drawing is bigger than its room
        const mini = $("#inside-stage .in-mini"), view = mini && $(".in-mini-view", mini), shown = $$("#inside-stage .in-box.component").filter((g) => { const r = g.getBoundingClientRect(); return r.left >= box.left - 1 && r.right <= box.right + 1 && r.top >= box.top - 1 && r.bottom <= box.bottom + 1; });
        ok(scale >= 0.85 && shown.length > 0 && (!spills || (mini && !mini.hidden && view && +view.getAttribute("width") > 0)),
          `inside ${name}, components: opens at reading size (${scale.toFixed(2)}), ${shown.length} of ${comps} components in view${spills ? ", the whole in the minimap" : ", all of it in view"}`,
          `inside ${name}, components: opens at ${scale.toFixed(2)} with ${shown.length} components in view; the drawing ${spills ? "spills" : "fits"} and the minimap is ${mini ? (mini.hidden ? "hidden" : "shown") : "missing"}`);
        const zoom = $$("#inside-stage .inside-frame .in-zoom button");
        zoom[1].click();
        const whole = $("svg", holder).getBoundingClientRect(), now = holder.getBoundingClientRect();
        ok(whole.right <= now.right + 1 && whole.bottom <= now.bottom + 1 && holder.scrollWidth <= holder.clientWidth + 1 && holder.scrollHeight <= holder.clientHeight + 1 && (!mini || mini.hidden),
          `inside ${name}, components: "Whole" puts the whole drawing in view (${Math.round(whole.width)} x ${Math.round(whole.height)} px in ${Math.round(now.width)} x ${Math.round(now.height)})`,
          `inside ${name}, components: "Whole" leaves the drawing cut off: ${Math.round(whole.width)} x ${Math.round(whole.height)} px in ${Math.round(now.width)} x ${Math.round(now.height)}`);
        zoom[2].click();
        ok(+holder.dataset.scale >= 0.85, `inside ${name}, components: "Read" returns to reading size`, `inside ${name}, components: "Read" left the scale at ${holder.dataset.scale}`);
        delete Inside.st.zoom.components;
        const toggle = $("#inside-stage .in-tabs-toggle"), beside = getComputedStyle($(".inside-l3")).gridTemplateColumns.split(" ").length > 1, area = (r) => r.width * r.height, wide = area($("#inside-draw").getBoundingClientRect());
        toggle.click();
        const hidden = $(".inside-l3").classList.contains("tabs-hidden") && !$(".inside-side").offsetParent, wider = area($("#inside-draw").getBoundingClientRect());
        toggle.click();
        ok(hidden && (wider > wide || !beside), `inside ${name}: the tabs fold away (drawing ${Math.round(wide / 1000)} to ${Math.round(wider / 1000)} k px squared) and come back`, `inside ${name}: tabs toggle: hidden ${hidden}, area ${Math.round(wide)} to ${Math.round(wider)}`);
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
      if (d.data_model.parsed_from === "erDiagram") {  // opens at reading size on the main entity; "Whole" puts every entity in view
        const er = $("#inside-stage .in-er"), buttons = $$("#inside-stage .in-er-wrap .in-zoom button"), within = (g, box) => { const r = g.getBoundingClientRect(); return r.left >= box.left - 1 && r.right <= box.right + 1 && r.top >= box.top - 1 && r.bottom <= box.bottom + 1; };
        const here = $$("#inside-stage .in-entity-box").filter((g) => within(g, er.getBoundingClientRect())), mini = $("#inside-stage .in-er-wrap .in-mini");
        const drawn = $("svg", er).getBoundingClientRect(), room = er.getBoundingClientRect(), spills = drawn.width > room.width + 1 || drawn.height > room.height + 1;
        ok(+er.dataset.scale >= 0.85 && here.length > 0 && (!spills || (mini && !mini.hidden)), `inside ${name}: the data model opens at reading size (${er.dataset.scale}), ${here.length} of ${d.data_model.entities.length} entities in view${spills ? ", the whole in the minimap" : ""}`,
          `inside ${name}: the data model opens at ${er.dataset.scale} with ${here.length} entities in view, minimap ${mini ? (mini.hidden ? "hidden" : "shown") : "missing"}`);
        buttons[1].click();
        const out = $$("#inside-stage .in-entity-box").filter((g) => !within(g, er.getBoundingClientRect()));
        ok(!out.length, `inside ${name}: "Whole" puts all ${d.data_model.entities.length} entities in view`, `inside ${name}: ${out.length} entities outside the data model's frame after "Whole": ${out.map((g) => g.dataset.entity).join(", ")}`);
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
    if (owned) { go(owned, { reset: true }); ok($$("#panel .in-owner").some((x) => /Delivered by/.test(x.textContent)), `reverse trace: ${owned}'s panel says "Delivered by ${Inside.OWNERS[owned][0].component} (${titleOf(Inside.OWNERS[owned][0].app)} design)"`, `reverse trace: ${owned} shows no owner`); }
    for (const kind of ["ack", "missed"]) {
      const id = Object.keys(Inside.UNTRACED).find((x) => Inside.UNTRACED[x].some((u) => !!u.gap === (kind === "ack")) && (CONTRACT[x] || E[x] || /^EPC-\d{3}\.AC\d+$/.test(x)));
      if (!id) { out.push(`skip reverse trace, ${kind}: no such untraced target in these designs`); continue; }
      const epic = id.match(/^(EPC-\d{3})\.AC\d+$/);
      go(epic ? keyForId(epic[1]) : id, { reset: true });
      const row = $$(`#panel .in-owner.untraced.${kind}`)[0];
      ok(!!row && !!row.querySelector(kind === "ack" ? ".lamp.dark" : ".lamp.caution"), `reverse trace: ${id} untraced, ${kind === "ack" ? "gray, acknowledged by " + Inside.UNTRACED[id].find((u) => u.gap).gap : "amber, and no gap says so"}`, `reverse trace: ${id} shows no ${kind} row`);
    }
    // a design question's challenge lights the vault item it challenges, with its scenario
    for (const id of Object.keys(Inside.CHALLENGED)) {
      const k = keyForId(Inside.challengeHome(id)), list = Inside.challenge(k);
      // a constraint row (CST-010) is a line in a page, not a page: the home list names it, no item page can light
      if (!ent(k)) { out.push(`skip challenge: ${id} has no page or item of its own to light`); continue; }
      const chipLamp = refChip(k).querySelector(".lamp");
      go(k, { reset: true });
      const sec = $$("#panel .in-challenge");
      ok(!!chipLamp && chipLamp.classList.contains("caution") && sec.length === list.length && (!list[0].scenario || sec[0].textContent.includes(list[0].scenario.slice(0, 30))),
        `challenge: ${id} lit "waiting" by ${list.map((c) => c.oq).join(", ")} in the ${titleOf(list[0].app)} design${list[0].scenario ? ", with its scenario" : ""}`, `challenge: ${id} lamp ${chipLamp ? chipLamp.className : "none"}, ${sec.length} sections`);
    }
    await planChecks(ok, out, apps);
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
    ok(!!entry && $$("[data-inside]", entry).length === 4 && !!$("[data-readiness]", entry), `engineering door: an Inside entry for ${titleOf(k0)}, with its four levels and its plan readiness`, "engineering door: no Inside entry");
    Nav.open("apps", k0);
    const listed = Nav.st.expanded.has("apps");  // past 12 apps the sidebar starts with its app list folded
    ok((!listed || !!$(`#side .side-inside[data-inside="${CSS.escape(k0)}"]`)) && !!$(`#main [data-dmenu="more"] [data-item="inside"]`), `${listed ? "sidebar and " : ""}section page: ${titleOf(k0)} offers Inside this app`, "the app's sidebar entry or page has no Inside");
    const box = $(`#board g.hit[data-key="${CSS.escape(k0)}"]`);
    if (box) { box.dispatchEvent(new MouseEvent("dblclick", { bubbles: true })); ok(App.view === "inside" && Inside.st.level === "containers", `the map: double-clicking ${titleOf(k0)} goes inside, to its containers`, `double-click: view ${App.view}, level ${Inside.st.level}`); }
    // every theme and Plain: the drawing still lays out with nothing on anything, and Plain runs no animation
    const was = Theme.id, fx = FX.on, themed = [];
    const planned0 = apps.find((k) => (D.plans || {})[k]);
    for (const t of Theme.LIST) {
      Theme.set(t.id); Inside.open(k0, "components");
      let o = overlaps();
      if (planned0) { Inside.open(planned0, "plan"); const q = overlaps(); o = { bad: [...o.bad, ...q.bad] }; }
      if (o.bad.length || !$("#inside-stage")) themed.push(`${t.id}: ${o.bad.length} overlaps (${o.bad.slice(0, 3).join(", ")})`);
    }
    Theme.set(was);
    FX.set(false); Inside.open(k0, "containers"); Inside.open(k0, "components");
    const anim = document.getAnimations ? document.getAnimations().filter((a) => a.playState === "running").length : 0;
    ok(!themed.length && !anim, `inside in every theme (${Theme.LIST.map((t) => t.label).join(", ")}) lays out cleanly; in Plain a level change runs ${anim} animations`, `inside themes: ${themed.join("; ")}; Plain animations ${anim}`);
    FX.set(fx);
  }
  /* The build plan (plan.js): level 4 draws from the plan, the dependency view has nothing on anything, every trace chip
     resolves or is dead for the reason the build gave, a lit card wears its question's lamp, the copy is the CSV the
     tool writes, and the vault item says which story builds it. */
  async function planChecks(ok, out, apps) {
    const planned = apps.filter((k) => (D.plans || {})[k]), bare = apps.find((k) => !(D.plans || {})[k]);
    if (!planned.length) out.push("skip inside, build plan: no work breakdown was found for this build");
    for (const k of planned) {
      const p = D.plans[k], name = titleOf(k);
      Inside.open(k, "plan");
      const crumb = $(".inside-crumbs .cur");
      ok(!!crumb && crumb.textContent === "Build plan", `inside ${name}, build plan: crumbs end at Build plan`, `inside ${name}, build plan: crumbs read "${crumb ? crumb.textContent : "none"}"`);
      ok(location.hash.includes(`level=plan`), `deep link: ${location.hash.split("&selftest")[0]}`, `deep link: ${location.hash}`);
      planProblemsChecks(ok, k, p, name);
      planLayoutChecks(ok, k, p, name);
      const tasked0 = p.stories.filter((x) => x.tasks.length);
      if (tasked0.length > 2 && !p.stories.some((x) => x.tracer)) {  // the build marks none here, so mark two for a moment to see the tracer group
        const marked = tasked0.slice(0, 2);
        marked.forEach((x) => { x.tracer = true; }); Inside.open(k, "plan");
        planLayoutChecks(ok, k, p, name + ", with a tracer marked");
        marked.forEach((x) => { delete x.tracer; }); Inside.open(k, "plan");
      }
      const o = overlaps(), nodes = $$("#plan-dag .plan-node").length;
      ok(nodes === p.stories.length && !o.bad.length, `inside ${name}, dependency view: ${nodes} stories, ${o.n} boxes and labels, no two overlap`, `inside ${name}, dependency view: ${nodes} of ${p.stories.length}; overlaps ${o.bad.slice(0, 3).join("; ")}`);
      const arrows = $$("#plan-dag path.in-edge").length, want = p.stories.reduce((n, x) => n + x.blockers.length, 0);
      ok(arrows === want, `inside ${name}, dependency view: ${arrows} arrows, one for each Blocked by`, `inside ${name}, dependency view: ${arrows} arrows for ${want} blockers`);
      {
        const dag = $("#plan-dag"), box = $("#plan-dag svg").getBoundingClientRect(), room = dag.getBoundingClientRect();
        ok(dag.scrollWidth <= dag.clientWidth + 1 && box.width <= room.width + 1 && getComputedStyle(dag).overflowX !== "auto",
          `inside ${name}, dependency view: fits the width (${Math.round(box.width)} px in ${Math.round(room.width)} px), no sideways scroll, ${Math.round(box.height)} px tall`,
          `inside ${name}, dependency view: scrolls sideways (drawing ${Math.round(box.width)} px, room ${Math.round(room.width)} px, scroll width ${dag.scrollWidth})`);
      }
      ok($("#plan-dag").classList.contains("pannable"), `inside ${name}, dependency view: dragging its background pans (scrolls) the page`, `inside ${name}, dependency view: #plan-dag is not pannable`);
      const hits = $$("#plan-dag .plan-hit"), unnamed = hits.filter((n) => !n.getAttribute("aria-label") || n.getAttribute("role") !== "button" || n.tabIndex !== 0);
      ok(hits.length === $$("#plan-dag g.in-node").length && hits.length >= p.stories.length && !unnamed.length,
        `inside ${name}, dependency view: all ${hits.length} nodes can be focused and have a name`, `inside ${name}, dependency view: ${$$("#plan-dag g.in-node").length - hits.length} nodes cannot be clicked, ${unnamed.length} have no name`);
      const dull = [], kinds = new Set();
      for (const n of hits) {
        n.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        const head = $("#panel h2"), body = $("#panel").textContent.trim(), label = n.getAttribute("aria-label");
        kinds.add(n.dataset.story ? "story" : n.dataset.blocker);
        if (!head || !head.textContent.trim() || body.length < 40 || (n.dataset.story && !head.textContent.includes(n.dataset.story))) dull.push(label);
      }
      ok(!dull.length, `inside ${name}, dependency view: clicking any of its ${hits.length} nodes (${[...kinds].join(", ")}) fills the panel`, `inside ${name}, dependency view: the panel stayed empty for ${dull.slice(0, 4).join("; ")}`);
      hits.length && hits[0].dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      go("lights", { reset: true });
      const empty = $$("#inside-stage .plan-cov tr.empty").length, want0 = p.coverage.targets.concat(p.coverage.components).filter((r) => !r.stories.length).length;
      ok(empty === want0 && (!empty || !!$("#inside-stage .plan-sum.bad")), `inside ${name}, build plan: coverage lights its ${plural(empty, "empty row")}`, `inside ${name}, build plan: ${empty} empty rows lit, ${want0} computed`);
      const comp = $("#inside-stage .plan-comp[data-component]");
      if (comp) {
        const want1 = comp.dataset.component; comp.click();
        ok(Inside.st.level === "components" && !!$(`#panel h2`) && $("#panel h2").textContent.includes(want1), `inside ${name}, build plan: a component chip jumps to ${want1} in the components`, `inside ${name}, build plan: the chip left level ${Inside.st.level}`);
        Inside.open(k, "plan");
      }
      let copied = null;
      const was = Plan.sink.write;
      Plan.sink.write = async (text) => { copied = text; };
      $("#inside-stage .plan-copy").click();
      await new Promise((r) => setTimeout(r, 30));
      Plan.sink.write = was;
      ok(copied === p.csv && copied.split("\r\n").length - 1 === p.totals.built + p.totals.tasks + 1,
        `inside ${name}, build plan: "Copy as Jira CSV" hands over the build's CSV, ${p.totals.built + p.totals.tasks} rows (stories it builds, and their tasks) and a header`, `inside ${name}, build plan: copied ${copied === null ? "nothing" : copied.length + " characters, not the CSV"}`);
      const built = Object.keys(Plan_BUILT_KEYS(k)).find((id) => E[id]);
      if (built) { go(built, { reset: true }); ok($$("#panel .in-owner.built").some((x) => /Built by .*S-\d+/.test(x.textContent)), `reverse trace: ${built}'s panel says "Built by ${Plan.built(built)[0].story} (${Plan.planWord(k)})"`, `reverse trace: ${built} shows no Built by`); }
    }
    if (bare) {
      Inside.open(bare, "plan");
      const say = ($("#inside-stage .inside-chip-card") || { textContent: "" }).textContent;
      ok(/No build plan yet\./.test(say) && say.includes("docs/plan/<slug>-breakdown.md"), `inside ${titleOf(bare)}, build plan: none, so the chip says what writes one`, `inside ${titleOf(bare)}, build plan: no empty-state chip`);
    }
  }
  /* The build order in each of its three layouts (List, Cards, Path): every layout holds one element per story in the
     order the groups give, wears the badges and the lamp, resolves its trace chips, and shows no size chip; the toggle
     switches between them, remembers the choice, and the page never scrolls sideways. */
  function planLayoutChecks(ok, k, p, name) {
    const hasTracer = p.stories.some((x) => x.tracer), tasked = p.stories.filter((x) => x.tasks.length), isT = (x) => hasTracer && x.tracer;
    const want = [...tasked.filter(isT), ...tasked.filter((x) => !isT(x)), ...p.stories.filter((x) => !x.tasks.length)].map((x) => x.id);
    const flagged = p.stories.filter((x) => x.openNotes.length || x.conflicts.length);
    const lit = p.stories.filter((x) => x.blockers.some((b) => b.kind === "question" && isOpen(UNKNOWN[b.ref])));
    const buttons = $$("#inside-stage .plan-seg button");
    ok(buttons.map((b) => b.dataset.layout).join() === "list,cards,path" && buttons.map((b) => b.textContent).join() === "List,Cards,Path",
      `inside ${name}, build plan: a toggle offers List, Cards and Path`, `inside ${name}, build plan: toggle reads ${buttons.map((b) => b.textContent).join()}`);
    for (const layout of ["list", "cards", "path"]) {
      const btn = $(`#inside-stage .plan-seg [data-layout="${layout}"]`);
      if (!btn) { ok(false, "", `inside ${name}, build plan: no ${layout} button`); continue; }
      btn.click();
      const cards = $$("#inside-stage .plan-card"), host = $("#inside-stage .plan-layout");
      ok(!!host && host.dataset.layout === layout && $(`#inside-stage .plan-seg [data-layout="${layout}"]`).getAttribute("aria-pressed") === "true" && $$("#inside-stage .plan-seg [aria-pressed=true]").length === 1,
        `inside ${name}, build plan: the toggle switches to ${layout}`, `inside ${name}, build plan: the toggle left ${host ? host.dataset.layout : "no layout"} for ${layout}`);
      ok(cards.length === p.stories.length && cards.every((c, i) => c.dataset.story === want[i]),
        `inside ${name}, build plan (${layout}): ${cards.length} stories, the tracer first when there is one, then build order, then not now`, `inside ${name}, build plan (${layout}): ${cards.map((c) => c.dataset.story).join(" ")} not ${want.join(" ")}`);
      const groups = $$("#inside-stage .plan-group").map((g) => g.dataset.group).join();
      ok(groups === (hasTracer ? "tracer,then" : "order") + (p.stories.some((x) => !x.tasks.length) ? ",notnow" : ""), `inside ${name}, build plan (${layout}): the groups read ${groups}`, `inside ${name}, build plan (${layout}): groups were ${groups}`);
      ok(flagged.every((x) => { const c = $(`#inside-stage .plan-card[data-story="${x.id}"]`); return $$(".plan-badge[data-flag=open]", c).length === (x.openNotes.length ? 1 : 0) && $$(".plan-badge[data-flag=conflict]", c).length === x.conflicts.length; })
        && $$("#inside-stage .plan-badge").length === flagged.reduce((n, x) => n + (x.openNotes.length ? 1 : 0) + x.conflicts.length, 0),
        `inside ${name}, build plan (${layout}): ${plural(flagged.length, "story", "stories")} wear a labeled badge for each open note and conflict`, `inside ${name}, build plan (${layout}): badges do not match the notes of ${flagged.map((x) => x.id).join(", ")}`);
      ok(lit.every((x) => { const c = $(`#inside-stage .plan-card[data-story="${x.id}"]`); return c.className.includes("lit ") && !!$(".lamp", c); }),
        `inside ${name}, build plan (${layout}): ${plural(lit.length, "story", "stories")} blocked by an open vault question wear that question's lamp`, `inside ${name}, build plan (${layout}): a story blocked by an open question is not lit`);
      const dead = $$("#inside-stage .plan-traces .ref-chip.ref-dead").length;
      ok(dead === p.unresolved.length && $$("#inside-stage .plan-traces .ref-chip:not(.ref-dead)").every((c) => !!c.dataset.ref && !!ent(c.dataset.ref)),
        `inside ${name}, build plan (${layout}): every trace chip resolves into the vault (${dead} named by the build as not in it)`, `inside ${name}, build plan (${layout}): ${dead} dead chips, the build names ${p.unresolved.length}`);
      const row = tasked.length ? $(`#inside-stage .plan-card[data-story="${tasked[0].id}"]`) : null, waits = row ? $(".plan-waits", row) || $(`#inside-stage .plan-pane[data-pane="${tasked[0].id}"] .plan-waits`) : null, listed = $$("#inside-stage .plan-task").length;
      ok(!tasked.length || (!!waits && /^(Waits on: |Can start now)/.test(waits.textContent) && !$(".ref-chip", waits) && listed === p.stories.reduce((n, x) => n + x.tasks.length, 0)),
        `inside ${name}, build plan (${layout}): each story says what it waits on in words, and all ${p.stories.reduce((n, x) => n + x.tasks.length, 0)} tasks are listed, deferred ones under Not now`, `inside ${name}, build plan (${layout}): waits "${waits ? waits.textContent : "missing"}", ${listed} tasks listed of ${p.stories.reduce((n, x) => n + x.tasks.length, 0)}`);
      const sizes = $$("#plan-page .plan-size, #plan-page .plan-total, #plan-page .plan-by-size, #plan-page [data-kpi=points]").length, text = $("#plan-page").textContent;
      ok(!sizes && !/\b[SML] ?\+ ?[SML]\b/.test(text), `inside ${name}, build plan (${layout}): no size chip anywhere`, `inside ${name}, build plan (${layout}): ${sizes} size chips or a size run in the text`);
      const page = $("#plan-page"), wide = Math.max(document.documentElement.scrollWidth - document.documentElement.clientWidth, page.scrollWidth - page.clientWidth);
      ok(wide <= 1, `inside ${name}, build plan (${layout}): nothing scrolls sideways at ${innerWidth}px`, `inside ${name}, build plan (${layout}): the page is ${wide}px wider than the window`);
    }
    const pathBtn = $("#inside-stage .plan-seg [data-layout=path]");
    if (pathBtn) pathBtn.click();
    Inside.open(k, "plan");
    const kept = $("#inside-stage .plan-layout");
    ok(!!kept && kept.dataset.layout === "path" && Settings.read("explorer.plan.layout") === "path", `inside ${name}, build plan: the layout chosen is kept in this browser`, `inside ${name}, build plan: layout came back ${kept ? kept.dataset.layout : "none"}, saved ${Settings.read("explorer.plan.layout")}`);
    const listBtn = $("#inside-stage .plan-seg [data-layout=list]");
    if (listBtn) listBtn.click();
  }
  /* What the page could not read of the plan is a count that opens a list, and the list starts closed and is never the
     first thing on the page. With none to show, a line is added for the check and taken away again. */
  function planProblemsChecks(ok, k, p, name) {
    const added = !p.problems.length;
    if (added) { p.problems.push("selftest: a line this page could not read"); Inside.open(k, "plan"); }
    const list = $("#inside-stage #plan-problems"), chip = $("#inside-stage .d-problems"), first = $("#plan-page").firstElementChild;
    ok(!!list && list.hidden && !!chip && +chip.dataset.problems === p.problems.length && chip.getAttribute("aria-expanded") === "false" && /couldn't be read: show$/.test(chip.textContent) && first !== list,
      `inside ${name}, build plan: ${plural(p.problems.length, "unreadable line")} counted on the chip, the list collapsed and not the first thing on the page`, `inside ${name}, build plan: list ${list ? (list.hidden ? "hidden" : "OPEN") : "missing"}, chip "${chip ? chip.textContent : "missing"}"`);
    if (chip) {
      chip.click();
      ok(!list.hidden && list.querySelectorAll("li").length === p.problems.length + p.unresolved.length && /: hide$/.test(chip.textContent), `inside ${name}, build plan: the chip opens the list`, `inside ${name}, build plan: the chip did not open the list`);
    }
    if (added) { p.problems.pop(); Inside.open(k, "plan"); }
  }
  const Plan_BUILT_KEYS = (app) => Object.fromEntries(D.plans[app].stories.flatMap((x) => x.traces.map((t) => [t.split("@")[0], 1])));
  /* Reader drafts, pending approval and freshness: the build's data drawn as the spec says, and the file:// page
     touching nothing. Synthetic rows stand in where this vault has no draft, so every build checks the drawing. */
  async function draftChecks(ok) {
    const frames = () => Promise.resolve();
    const want = D.role === "reader" && D.draft && (D.draft.count > 0 || (D.draft.conflicts || []).length > 0 || D.draft.problem), badge = $("#draft-badge");
    ok(!!badge === !!want && (!want || badge.textContent === Drafts.heading()),
      want ? `draft badge: "${Drafts.heading()}" in the top bar of this reader's page` : `draft badge: none for role ${D.role} with no changes`,
      `draft badge: role ${D.role}, draft ${D.draft ? D.draft.count : "none"}, badge "${badge ? badge.textContent : "none"}"`);
    const evil = "<img src=x onerror=\"window.__draftpayload = 1\"> & <b>bold</b>";
    const block = Drafts.diffBlock([["hunk", "@@ -1 +1 @@"], ["del", "old line"], ["add", evil], ["ctx", "same"]]);
    ok(!block.querySelector("img, b, script") && $$(".tx", block)[2].textContent === evil && $$(".sym", block).map((x) => x.textContent).join("") === "-+ " && !window.__draftpayload,
      "drafts view: a diff line is escaped text, and additions and removals carry a + and - symbol as well as a color", `drafts view: markup in a line became elements (${block.innerHTML.slice(0, 120)})`);
    const sample = { path: "p.md", mine: "p.mine.md", kind: "both-edited", why: "You and the owner changed the same lines.", ranges: [[2, 3]], binary: false,
      lines: [["del", "the owner's line"], ["add", evil]], added: 1, removed: 1, title: "P", key: "" };
    const cc = Drafts.conflictCard(sample);
    ok($(".dstate.conflict", cc) && $(".dstate.conflict", cc).textContent === "Conflict" && cc.open && !cc.querySelector("img, script, .tx b") && $("code", cc).textContent === "p.mine.md" && /lines 2-3/.test(cc.textContent) && !window.__draftpayload,
      "drafts view: a conflict card says Conflict in words, names the saved file and the lines, and draws the lines as text", `drafts view: conflict card ${cc.outerHTML.slice(0, 160)}`);
    const wasTheme = Theme.id, unseen = [];
    for (const t of Theme.LIST) {
      Theme.set(t.id);
      const holder = h("div", { class: "d-view" }, Drafts.conflictCard(sample));
      $("#main").append(holder);
      const pill = $(".dstate.conflict", holder), look = getComputedStyle(pill);
      if (!pill.textContent || look.color === getComputedStyle($("#main")).backgroundColor || look.boxShadow === "none") unseen.push(t.id);
      holder.remove();
    }
    Theme.set(wasTheme);
    ok(!unseen.length, `drafts view: the Conflict badge shows its word, ink and ring in every theme (${Theme.LIST.map((t) => t.label).join(", ")})`, `drafts view: the Conflict badge is not drawn in ${unseen.join(", ")}`);
    const waiting = (D.draft && D.draft.conflicts) || [];
    if (want && waiting.length) {
      Drafts.open(); await frames();
      const first = $("#main .d-sec"), cards = $$("#main .dpage.conflict"), badgeNow = $("#draft-badge");
      ok(!!first && first.id === "conflicts" && cards.length === waiting.length && cards.every((c) => /Conflict/.test($(".dstate", c).textContent)) && !!badgeNow && /conflict/.test(badgeNow.textContent) && badgeNow.textContent === Drafts.heading(),
        `drafts view: ${plural(cards.length, "conflict")} listed before every other change, and the draft badge counts them`, `drafts view: first section ${first ? first.id : "none"}, ${cards.length} conflict cards for ${waiting.length}, badge "${badgeNow ? badgeNow.textContent : "none"}"`);
      Nav.home(); await frames();
    }
    if (want && D.draft.count) {
      Drafts.open(); await frames();
      const cards = $$("#main .dpage:not(.conflict)"), rows = cards.map((c) => $$(".dl", c).length), expect = D.draft.pages.map((p) => p.lines.length);
      ok(location.hash.startsWith("#drafts") && cards.length === D.draft.pages.length && rows.every((n, i) => n === expect[i]) && /changed/.test($("#main h1").textContent),
        `drafts view: #drafts lists ${plural(cards.length, "changed page")} with ${rows.reduce((a, b) => a + b, 0)} diff lines, each page linked`, `drafts view: hash ${location.hash}, ${cards.length} cards for ${D.draft.pages.length}, rows ${rows} vs ${expect}`);
      const hint = $("#propose-hint");
      ok(!!hint && /\/vela:propose/.test(hint.textContent) && !!hint.querySelector("code") && /Nothing is sent from this page/.test(hint.textContent),
        "drafts view: a hint names /vela:propose as the way to send the changes, and says the page sends nothing", `drafts view: hint ${hint ? hint.textContent : "missing"}`);
      Nav.home(); await frames();
    }
    ok(rank("pending") < rank("caution") && rank("pending") > rank("unexamined") && rank("pending") > rank("dark"),
      "pending approval ranks below an overdue or held question and above never examined, overridden and settled", `pending approval rank: ${LEVELS.join(" > ")}`);
    const pill = pendingPill({ by: "@sam", date: "2026-10-18" }), lamp = lampEl("pending");
    ok(/Pending approval/.test(pill.textContent) && /@sam/.test(pill.title) && lamp.classList.contains("pending") && /Pending approval/.test(lamp.title),
      "pending approval: a ring lamp and a pill with the words, never color alone", `pending approval: pill "${pill.textContent}", lamp ${lamp.className}`);
    for (const m of D.pending.slice(0, 3)) {
      const light = lightOf(m.key);
      go(m.key, { reset: true }); await frames();
      ok(!!E[m.key] && !!E[m.key].pending && !!light && rank(light.level) >= rank("pending") && !!$("#panel .pill.pending") && /Pending approval/.test($("#panel .pill.pending").textContent),
        `pending approval: ${m.subject} (${m.by}, ${m.date}) is lit "${light && light.level}" with a pending-approval pill in its panel`, `pending approval: ${m.subject} light ${light && light.level}, pill ${!!$("#panel .pill.pending")}`);
    }
    if (D.pending.length) {
      go("lights", { reset: true }); await frames();
      ok(!!$("#pending-chip") && ($$("#panel .light-row .lamp.pending").length >= 1 || D.pending.every((m) => lightOf(m.key) && lightOf(m.key).level !== "pending")),
        `pending approval: the header chip counts ${D.pending.length} and What's waiting includes them`, "pending approval: no chip or no pending row in What's waiting");
    } else ok(!$("#pending-chip"), "pending approval: no chip when nothing is pending", "pending approval: a chip with nothing pending");
    // freshness: the banner follows the stamped report, shown only when something changed
    const newer = { role: "reader", state: "newer", latest: { date: "2026-10-20", commit: "4d1e8a0" }, have: {}, checked_at: "2026-10-18T09:12:00" };
    const owner = { role: "owner", state: "newer", behind: 2, ahead: 0, uncommitted: 1, checked_at: "2026-10-18T09:12:00" };
    ok(/^There's a newer copy from 20 Oct 2026\. Reload the page to get it/.test(Freshness.words(newer)) && /your drafts carry over/.test(Freshness.words(newer))
      && Freshness.words({ ...newer, state: "current" }) === "" && Freshness.words({ ...newer, state: "unreachable" }) === "" && Freshness.words(null) === ""
      && Freshness.words(owner) === "2 updates on the shared copy aren't in yours yet; 1 changed file isn't shared yet." && Freshness.words({ ...owner, behind: 0, uncommitted: 0, state: "current" }) === "",
      "freshness: the banner words say a newer copy was published, or updates not pulled and changes not shared, and nothing otherwise", "freshness: Freshness.words gave " + JSON.stringify([Freshness.words(newer), Freshness.words(owner)]));
    const kept = { report: Freshness.st.report, live: Freshness.st.live };
    ok($("#fresh").hidden === !Freshness.words(Freshness.st.report), `freshness: this page's banner is ${$("#fresh").hidden ? "hidden" : "shown"} to match its stamp`, "freshness: the banner does not match the stamped report");
    Freshness.st.report = newer; Freshness.st.live = false; Freshness.render();
    const shown = !$("#fresh").hidden && /from 18 Oct, 9:12, when the page was built/.test($("#fresh").textContent);
    Freshness.st.report = { ...newer, state: "current" }; Freshness.render();
    const hidden = $("#fresh").hidden;
    Freshness.st.report = kept.report; Freshness.st.live = kept.live; Freshness.render();
    ok(shown && hidden, "freshness: a stamped newer copy shows the banner with its build time; a current stamp hides it", `freshness: shown ${shown}, hidden ${hidden}`);
    // a file asks nothing; a served page asks /freshness once and shows what it hears
    const calls = [], fake = async (url) => { calls.push(String(url)); return new Response(JSON.stringify(newer), { status: 200 }); };
    if (location.protocol === "file:") {
      const was = Freshness.st.fetches, restore = Freshness.use(fake, () => location.protocol === "http:" || location.protocol === "https:");
      const asked = await Freshness.poll("selftest");
      restore();
      ok(was === 0 && !asked && !calls.length && Freshness.st.fetches === was, "freshness on a file: no request at load, none when asked to poll", `freshness on a file: ${was} fetches at load, poll asked ${asked}, ${calls.length} requests`);
    } else {
      ok(Freshness.st.fetches <= 1, "freshness when served: at most one /freshness request at load", `freshness when served: ${Freshness.st.fetches} requests at load`);
    }
    const restore = Freshness.use(fake, () => true), count = Freshness.st.fetches;
    const live = { report: Freshness.st.report, live: Freshness.st.live };
    await Freshness.poll("selftest");
    const polled = calls.length === 1 && calls[0] === "/freshness" && Freshness.st.fetches === count + 1 && !$("#fresh").hidden && Freshness.st.live;
    Freshness.st.report = live.report; Freshness.st.live = live.live; Freshness.st.fetches = count; restore(); Freshness.render();
    ok(polled, "freshness when served: a poll asks /freshness once and shows the banner from the answer", `freshness when served: calls ${calls}, banner hidden ${$("#fresh").hidden}`);
    // E39: after a failed check the banner stops saying "checked just now" in its visible text
    const broken = Freshness.use(async () => new Response("{}", { status: 503 }), () => true), saved = { report: Freshness.st.report, live: Freshness.st.live, error: Freshness.st.error };
    Freshness.st.report = newer; Freshness.st.live = true; Freshness.st.last = 0;
    const warn = console.warn; console.warn = () => {};
    await Freshness.poll("selftest");
    console.warn = warn;
    const said = $("#fresh").textContent;
    Object.assign(Freshness.st, saved); broken(); Freshness.render();
    ok(/couldn't check just now; this is from 18 Oct, 9:12/.test(said) && !/checked just now/.test(said), "freshness: after a failed live check the banner says it could not check, and when it was built", `freshness: after a failed check the banner says "${said}"`);
  }
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await checks(ok, lines); } catch (e) { lines.push("FAIL the Inside checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    try { await draftChecks(ok); } catch (e) { lines.push("FAIL the draft, pending and freshness checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the Inside checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();

/* ------------------------------------------------------------ Text fits its box (the label sensor)
   A small label (a pill, chip, badge, button, tab, table heading) is sized by its text, so it is the first thing to
   spill when the box around it is narrow or its text is long: the text runs past its own edge, or the label sticks out
   past the box it sits in. Nothing else sees this, because the page still renders and every other check still passes.
   textFits(root) lists each such label with the words in it and its class, and the checks below sweep every view the
   page has, in every theme and in Plain, at the window the page was opened in. A label that cuts itself short with an
   ellipsis on purpose is fine; one that scrolls its own row is too. */
const TextFit = (() => {
  const KINDS = [".pill", ".chip", ".ref-chip", "[class*=badge]", ".d-status", ".dstate", ".dl-tag", ".dl-stage", ".fp-status", ".plan-kpi", ".kpi-label",
    ".kpi-num", "button", ".btn", ".tab", "[role=tab]", ".seg button", "th", ".in-status-cell", ".ask-about-tag", ".holdbox .tag"].join(", ");
  const px = (v) => parseFloat(v) || 0;
  const scrolls = (cs) => /auto|scroll/.test(cs.overflowX);
  const clips = (cs) => /hidden|clip/.test(cs.overflowX) || /hidden|clip/.test(cs.overflowY);
  const words = (el) => (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
  const classOf = (el) => (typeof el.className === "string" ? el.className : "").trim();
  const where = (el) => { const p = el.parentElement; return p ? p.tagName.toLowerCase() + (classOf(p) ? "." + classOf(p).split(/\s+/)[0] : "") : ""; };
  function visible(el) {
    if (!el.getClientRects().length || el.closest("[hidden], svg")) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== "hidden" && cs.display !== "none" && cs.position !== "fixed" && px(cs.opacity) !== 0;
  }
  /* The box a label's parent offers its children: the parent's rectangle less its border and padding. */
  function contentBox(p) {
    const r = p.getBoundingClientRect(), cs = getComputedStyle(p);
    return { left: r.left + px(cs.borderLeftWidth) + px(cs.paddingLeft), right: r.right - px(cs.borderRightWidth) - px(cs.paddingRight) };
  }
  /* A label that hands its text to an inner span which cuts itself short with an ellipsis (the angled matrix headings) has chosen to. */
  const ellipsized = (el) => [...el.querySelectorAll("*")].find((c) => { const k = getComputedStyle(c); return k.textOverflow === "ellipsis" && clips(k); });
  function problem(el) {
    // a label that wraps across lines has one rectangle per line: its bounding box is the union, wider than any line
    const cs = getComputedStyle(el), lines = [...el.getClientRects()].filter((q) => q.width > 0), r = { left: Math.min(...lines.map((q) => q.left)), right: Math.max(...lines.map((q) => q.right)) };
    if (!lines.length || (!words(el) && !el.querySelector("svg, img"))) return "";
    const ellipsis = (cs.textOverflow === "ellipsis" && clips(cs)) || !!ellipsized(el);
    if (el.clientWidth > 0 && !ellipsis && !scrolls(cs) && el.scrollWidth > el.clientWidth + 1) return `its text runs ${el.scrollWidth - el.clientWidth}px past its own edge`;
    if (cs.position === "absolute") return "";
    let p = el.parentElement;
    while (p && getComputedStyle(p).display === "contents") p = p.parentElement;
    if (p && p !== document.body && !/^(TR|TABLE|THEAD|TBODY)$/.test(p.tagName)) {
      const pcs = getComputedStyle(p), box = contentBox(p);
      if (!scrolls(pcs) && p.getBoundingClientRect().width > 0 && (r.right > box.right + 1 || r.left < box.left - 1)) {
        return `it sticks out ${Math.round(Math.max(r.right - box.right, box.left - r.left))}px past ${where(el)}`;
      }
    }
    for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {  // an ancestor that clips shows it cut off
      const acs = getComputedStyle(a);
      if (scrolls(acs)) break;
      if (clips(acs) && a.clientWidth > 0) {
        const ar = a.getBoundingClientRect();
        if (r.right > ar.right + 1 || r.left < ar.left - 1) return `${a.tagName.toLowerCase()}.${classOf(a).split(/\s+/)[0]} clips it by ${Math.round(Math.max(r.right - ar.right, ar.left - r.left))}px`;
      }
    }
    return "";
  }
  /* Text anywhere, not only the listed label kinds: an element that holds text of its own must stay inside the nearest
     box drawn around it (a border, a background or an inset outline), unless that box scrolls. A list of kinds always
     misses one (the Progress page's state cards were not on it). */
  const ownText = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  function drawnBox(el) {
    for (let a = el.parentElement, hops = 0; a && a !== document.body && hops < 6; a = a.parentElement, hops++) {
      const cs = getComputedStyle(a);
      // a scrolling box, a deliberate cut with an ellipsis (its full text on hover), or a rotated label is not an overflow
      if (scrolls(cs) || (cs.textOverflow === "ellipsis" && clips(cs)) || (cs.transform && cs.transform !== "none")) return null;
      const bg = cs.backgroundColor, framed = px(cs.borderRightWidth) > 0 || px(cs.borderLeftWidth) > 0 || /inset/.test(cs.boxShadow);
      if (framed || (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg))) return a;
    }
    return null;
  }
  function boxFit(el) {
    const box = drawnBox(el);
    if (!box) return "";
    const b = contentBox(box), lines = [...el.getClientRects()].filter((q) => q.width > 0);
    if (!lines.length) return "";
    const right = Math.max(...lines.map((q) => q.right)), left = Math.min(...lines.map((q) => q.left));
    return right > b.right + 1 || left < b.left - 1 ? `its text runs ${Math.round(Math.max(right - b.right, b.left - left))}px outside ${box.tagName.toLowerCase()}.${classOf(box).split(/\s+/)[0]}` : "";
  }
  /* Every visible small label under root that does not fit, each as { text, cls, why }. */
  function textFits(root = document) {
    const bad = [];
    for (const el of root.querySelectorAll("body *:not(svg *):not(script):not(style)")) {
      const ecs = getComputedStyle(el);
      if (el.matches(KINDS) || !ownText(el) || !visible(el) || ecs.position === "absolute" || (ecs.transform && ecs.transform !== "none")) continue;
      const why = boxFit(el);
      if (why) bad.push({ text: words(el), cls: classOf(el) || el.tagName.toLowerCase(), why });
    }
    for (const el of root.querySelectorAll(KINDS)) {
      if (!visible(el)) continue;
      const why = problem(el);
      if (why) bad.push({ text: words(el), cls: classOf(el) || el.tagName.toLowerCase(), why });
    }
    return bad;
  }
  /* Prose cut off mid-sentence. A box that hides what overflows it, with words under the cut, loses text without a word
     said: the reader sees a sentence end at "It". Allowed: a line-clamp or ellipsis (the cut shows), a box that scrolls,
     and a box with a "Show more" button beside it (the text is one click away). The page shell and drawings are not prose. */
  const SHELL = new Set(["HTML", "BODY", "MAIN"]);
  const hasMore = (el) => { for (let a = el; a && a !== document.body; a = a.parentElement) if (a.querySelector(":scope > [data-more]")) return true; return false; };
  const ellipsizedStyle = (cs) => (cs.webkitLineClamp && cs.webkitLineClamp !== "none") || cs.textOverflow === "ellipsis";
  /* Words inside a line-clamped or ellipsized child end in an ellipsis where the cut falls, so they are not lost. */
  const underEllipsis = (n, el) => { for (let a = n.parentElement; a && a !== el; a = a.parentElement) if (ellipsizedStyle(getComputedStyle(a))) return true; return false; };
  function cutWords(el) {
    const box = el.getBoundingClientRect(), walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      if (!n.nodeValue.trim() || (n.parentElement && n.parentElement.closest("svg, [hidden], .sr-only, script, style")) || underEllipsis(n, el)) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      for (const q of r.getClientRects()) if (q.height > 0 && q.bottom > box.bottom + 2) return n.nodeValue.trim().slice(0, 40);
    }
    return "";
  }
  function clippedText(root = document) {
    const bad = [];
    for (const el of root.querySelectorAll("*")) {
      if (SHELL.has(el.tagName) || el.id === "main" || el instanceof SVGElement || el.scrollHeight <= el.clientHeight + 2 || !el.clientHeight) continue;
      const cs = getComputedStyle(el);
      if (!/hidden|clip/.test(cs.overflowY) || /scroll|auto/.test(cs.overflowY) || cs.display === "none" || !visible(el)) continue;
      if (ellipsizedStyle(cs) || hasMore(el)) continue;
      const lost = cutWords(el);
      if (lost) bad.push({ text: lost, cls: classOf(el) || el.tagName.toLowerCase(), why: "cuts its text off at the bottom with no ellipsis and no Show more" });
    }
    return bad;
  }
  /* A label a person reads first, as plain words: never a bare ID, never an ID in front of the name. The ID may ride in a
     small .id-tag, in the tooltip, or in the second line. Drawn nodes (the map's boxes) carry their label in the first <text>. */
  const ID_FIRST = /^[A-Z][A-Z0-9]{1,6}-[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*(?:\s|$|[:,])/;
  const ID_ALONE = /^[A-Z][A-Z0-9]{1,6}-\d{1,4}(?:\.[A-Z0-9]+)*$/;
  const LABELS = "h1, h2, h3, h4, .q-title, .light-row .what, .door-list li > a, .door-list li > button.linkish, .door-card header h2, .p-head h2, .dl-name";
  const wordsOf = (el) => { const c = el.cloneNode(true); c.querySelectorAll(".id-tag, .idsuf, .sr-only, .lamp, .slice-k").forEach((x) => x.remove()); return (c.textContent || "").replace(/\s+/g, " ").trim(); };
  const named = (id) => { const e = ent(keyForId(id)); return !!(e && e.title && e.title !== id); };
  function bareLabels(root = document) {
    const bad = [];
    for (const el of root.querySelectorAll(LABELS)) {
      if (!visible(el)) continue;
      const t = wordsOf(el);
      if (ID_ALONE.test(t) && !named(t)) continue;  // a code the vault holds no name for stays as the page wrote it
      if (ID_FIRST.test(t) || ID_ALONE.test(t)) bad.push({ text: t.slice(0, 40), cls: classOf(el) || el.tagName.toLowerCase(), why: "is a code where a name belongs" });
    }
    for (const g of root.querySelectorAll("svg [data-key]")) {
      const first = g.querySelector("text");
      if (!first || !first.getClientRects().length) continue;
      const t = (first.textContent || "").trim();
      if (ID_ALONE.test(t) || ID_FIRST.test(t)) bad.push({ text: t.slice(0, 40), cls: "node label", why: "is a code where a name belongs" });
    }
    return bad;
  }
  /* Reader text names things; it never says where they are kept (the wording rule: no file paths or commit hashes in
     reader text). A folder path, a file name or a commit hash in the panel's own words, a view's head, or a tooltip
     there is builder text that leaked through. Words someone wrote, shown as written (a plan page, .r-text; a page's
     prose, .prose-text; a team design's text, .authored), a reader's drafts (.dpage), which edit files by name, and
     web addresses are theirs, so they are left out. */
  const PATH_WORDS = /(?:^|[\s("'“`])(?:[\w.-]+\/)+[\w.-]*\.(?:md|ya?ml|json|html)\b|(?:^|[\s("'“`])[\w-]+\/(?=[\s"'”`.,;:)]|$)|\b[\w-]+\.(?:md|ya?ml|json)\b/;
  const HASH_WORDS = /\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b/;
  const BUILDER_ROOTS = "#panel, .view-head, #built";
  const leftOut = (el) => !!el.closest(".r-text, .prose-text, .authored, .dpage, script, style, [hidden], .sr-only");
  function builderWords(root = document) {
    const bad = [], seen = new Set();
    const flag = (text, el, where) => {
      const said = text.replace(/\b(?:https?|file):\/\/\S+/g, "");
      const m = said.match(PATH_WORDS) || said.match(HASH_WORDS);
      if (!m || seen.has(text)) return;
      seen.add(text);
      bad.push({ text: text.trim().slice(0, 50), cls: (classOf(el) || el.tagName.toLowerCase()) + where, why: `shows "${m[0].trim()}", a file path or commit hash, in reader text` });
    };
    const hosts = root.matches && root.matches(BUILDER_ROOTS) ? [root] : [...root.querySelectorAll(BUILDER_ROOTS)];
    for (const host of hosts) {
      const walk = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
      for (let n = walk.nextNode(); n; n = walk.nextNode()) {
        const el = n.parentElement;
        if (!el || !n.nodeValue.trim() || leftOut(el) || !visible(el)) continue;
        flag(n.nodeValue, el, "");
      }
      for (const el of [host, ...host.querySelectorAll("[title], [aria-label]")]) {
        if (leftOut(el)) continue;
        for (const attr of ["title", "aria-label"]) if (el.getAttribute(attr)) flag(el.getAttribute(attr), el, ` (${attr})`);
      }
    }
    return bad;
  }
  return { textFits, clippedText, bareLabels, builderWords, KINDS };
})();

/* ------------------------------------------------------------ The voice gate: codes in reader text, a count said twice, two counts for one thing
   Three sensors over the text a reader sees, swept with TextFit's views. Each exists for one failure the label sweep
   (2026-10-16) found by eye and no check saw:
   - leaks(root): builder plumbing in reader text, by say.LEAD_PATTERNS (the one copy, carried in the selftest build as
     D.leadPatterns), less item IDs, which ride in a small tag on purpose. Words someone wrote are theirs and left out.
   - repeats(root): the same count sentence twice on one screen ("21 waiting: 18 open questions blocking work..." on the
     banner and in the panel beside it). A count said once is information; said twice it is a second thing to hold.
   - quantities(): every element marked data-quantity="<name>" data-n="<n>" must give the one source's number for that
     name, and every view must agree (E60: the Managers door said 27 open questions, the top bar 21, the Exec door 0
     proposed beside the log's 1). A view that shows a shared count marks it; the sources are Queue.needsYou and D.counts. */
const VoiceGate = (() => {
  const SKIP = ".r-text, .prose-text, .authored, .dpage, .id-tag, .idsuf, .dl-trace, code, pre, script, style, svg, [hidden], .sr-only, .tour, #selftest-out";
  const ROOTS = "header.top, #side, #main, #panel";
  const patterns = () => Object.entries(D.leadPatterns || {}).map(([kind, src]) => [kind, new RegExp(src)]);
  const shown = (el) => !!el && !el.closest(SKIP) && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  function textNodes(root) {
    const out = [], hosts = root.matches && root.matches(ROOTS) ? [root] : [...root.querySelectorAll(ROOTS)];
    for (const host of hosts) {
      const walk = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
      for (let n = walk.nextNode(); n; n = walk.nextNode()) if (n.nodeValue.trim() && shown(n.parentElement)) out.push(n);
    }
    return out;
  }
  function leaks(root = document) {
    const bad = [], seen = new Set(), list = patterns();
    for (const n of textNodes(root)) {
      const text = n.nodeValue.replace(/\b(?:https?|file):\/\/\S+/g, "");
      for (const [kind, re] of list) {
        const m = text.match(re);
        if (!m || seen.has(kind + m[0])) continue;
        seen.add(kind + m[0]);
        bad.push({ text: text.trim().slice(0, 60), kind, hit: m[0] });
        break;
      }
    }
    return bad;
  }
  /* A block's own words, joined across its inline children, so "18 questions block work." is one sentence however it is marked up. */
  const BLOCK = /^(block|flex|grid|list-item|table-cell|table-caption|flow-root)/;
  function blockOf(el) { for (let a = el; a && a !== document.body; a = a.parentElement) if (BLOCK.test(getComputedStyle(a).display)) return a; return document.body; }
  /* A count sentence says how many of something there are: "18 questions block work", "21 waiting". A date, a time
     or a name with a number in it ("the 7:30 digest") is not a count. Rows of a list or table say the same words about
     different things by design, so a row is not compared with its siblings. */
  const COUNT = /\b\d+ (?:[a-z-]+ ){0,2}?(?:questions?|things?|items?|decisions?|apps?|contracts?|flows?|steps?|stor(?:y|ies)|points?|pages?|requirements?|criteri(?:on|a)|releases?|slices?|epics?|risks?|concerns?|options?|people|persons?|teams?|waiting|overdue|of the plan)\b/i;
  const isCount = (s) => COUNT.test(s) && s.split(/\s+/).length >= 3;
  const ROW = "li, tr, [role=row], [data-row], .light-row, .q-row";  // data-row: a card in a list of cards
  function sentences(root = document) {
    const blocks = new Map();
    for (const n of textNodes(root)) { if (n.parentElement.closest(ROW)) continue; const b = blockOf(n.parentElement); blocks.set(b, (blocks.get(b) || "") + n.nodeValue); }
    const out = [];
    for (const text of blocks.values()) for (const s of text.replace(/\s+/g, " ").trim().split(/(?<=[.!?])\s+(?=[A-Z0-9])/)) if (isCount(s)) out.push(s.replace(/[.!?]+$/, ""));
    return out;
  }
  function repeats(root = document) {
    const seen = new Map();
    for (const s of sentences(root)) seen.set(s, (seen.get(s) || 0) + 1);
    return [...seen].filter(([, n]) => n > 1).map(([s, n]) => ({ text: s.slice(0, 90), n }));
  }
  /* The one source for each shared quantity. A name not here is a typo, and fails like a wrong number. */
  function sources() {
    const need = Queue.needsYou(), counts = Queue.counts(), out = { needsYou: need.n, "needsYou.questions": need.questions, overdue: need.late, unreviewed: counts.unexamined || 0, openQuestions: D.counts.openQuestions };
    for (const [state, n] of Object.entries(D.counts.decisions)) out["decisions." + state] = n;
    return out;
  }
  function quantities(root = document) {
    const want = sources(), bad = [];
    for (const el of root.querySelectorAll("[data-quantity]")) {
      if (!el.getClientRects().length) continue;
      const name = el.dataset.quantity, n = +el.dataset.n;
      if (!(name in want)) bad.push({ name, n, why: "names no known quantity" });
      else if (n !== want[name]) bad.push({ name, n, why: `says ${n}, the source says ${want[name]}` });
      else if (!String(el.textContent).includes(String(n))) bad.push({ name, n, why: `is marked ${n} but reads "${el.textContent.trim().slice(0, 40)}"` });
    }
    return bad;
  }
  /* Across views: the numbers each view gave for each quantity, so two views that disagree are named together. */
  const given = new Map();
  function record(view, root = document) {
    for (const el of root.querySelectorAll("[data-quantity]")) {
      if (!el.getClientRects().length) continue;
      const m = given.get(el.dataset.quantity) || new Map();
      m.set(+el.dataset.n, (m.get(+el.dataset.n) || []).concat(view)); given.set(el.dataset.quantity, m);
    }
  }
  function disagreements() { return [...given].filter(([, m]) => m.size > 1).map(([name, m]) => `${name}: ${[...m].map(([n, views]) => `${n} in ${views.slice(0, 3).join(", ")}`).join(" vs ")}`); }
  return { leaks, repeats, sentences, quantities, record, disagreements, given, sources };
})();

(() => {
  const base = SelfTest.run;
  const found = new Map();  // "text (class)" -> { view, why, more }: the first view a label failed in, and how many others it failed in
  const voice = { on: false, leaks: new Map(), repeats: new Map(), quantities: new Map() };  // the words don't change with the theme: read once
  const keep = (map, id, view, why) => { const seen = map.get(id); if (seen) seen.more++; else map.set(id, { view, why, more: 0 }); };
  const note = (view, root) => {
    for (const b of [...TextFit.textFits(root || document), ...TextFit.clippedText(root || document), ...TextFit.bareLabels(root || document),
      ...TextFit.builderWords(root || document)]) {
      const id = `"${b.text}" (${b.cls})`, seen = found.get(id);
      if (seen) seen.more++; else found.set(id, { view, why: b.why, more: 0 });
    }
    if (voice.on) {
      for (const b of VoiceGate.leaks(root || document)) keep(voice.leaks, `"${b.text}"`, view, `shows ${b.kind} "${b.hit}"`);
      for (const b of VoiceGate.repeats(root || document)) keep(voice.repeats, `"${b.text}"`, view, `said ${b.n} times on one screen`);
      for (const b of VoiceGate.quantities(root || document)) keep(voice.quantities, `${b.name}`, view, b.why);
      VoiceGate.record(view, root || document);
    }
  };
  /* Every view the page has, drawn once; each is swept for labels that do not fit. */
  async function sweep() {
    const apps = D.map.apps.map((a) => a.key);
    Nav.home(); MapView.st.group = "none";
    for (const lens of ["cockpit", "transit", "matrix"]) { MapView.st.lens = lens; rerender(); note(`map, ${lens}`); }
    MapView.st.group = "domain"; MapView.st.lens = "cockpit"; rerender(); note("map, grouped by domain");
    MapView.st.lens = null; MapView.st.group = null; rerender();
    for (const s of D.sections) {
      Nav.open(s.id); note(`section ${s.label}`);
      for (const child of (s.children || []).slice(0, s.id === "apps" ? 99 : 3)) { Nav.open(s.id, child); note(`${s.label} > ${titleOf(child)}`); }
    }
    for (const view of ["asks", "progress", "trace", "decisions", "releases", "slices", "flows"]) { showView(view); note(`view ${view}`); }
    if (D.slicePlan.list.length) {  // the table with every row open, and the path, without touching the reader's kept layout
      const all = D.slicePlan.list.map((x) => x.slice);
      Slices.st.layout = "table"; Slices.st.open = new Set(all); showView("slices"); note("slices, every row open");
      Slices.st.layout = "path"; Slices.st.open = new Set(); showView("slices"); note("slices, path");
      Slices.st.layout = null;
    }
    for (const f of D.flows) { Flows.select(f.key, 0); note(`flow ${f.key}`); }
    for (const id of ["lead", "exec", "product", "qa", "mgr"]) { Nav.role(id); note(`door ${id}`); }
    for (const k of apps) { Roles.st.app = k; Nav.role("eng"); note(`door eng, ${titleOf(k)}`); }
    Nav.home();
    for (const k of apps) {
      for (const level of ["context", "containers", "components", "plan"]) {
        Inside.open(k, level); note(`${titleOf(k)}, inside ${level}`);
        for (const box of $$("#inside-stage .in-node[data-key]").slice(0, 12)) { box.dispatchEvent(new MouseEvent("click", { bubbles: true })); note(`${titleOf(k)}, ${level}, panel for ${box.dataset.key.split(":").slice(-1)[0]}`); }
        Inside.open(k, level);
        if (level === "plan" && D.plans && D.plans[k]) for (const layout of ["list", "cards", "path"]) {
          const btn = $(`#inside-stage .plan-seg [data-layout="${layout}"]`);
          if (btn) { btn.click(); note(`${titleOf(k)}, build plan as ${layout}`); }
        }
      }
      if (D.designs[k]) for (const [tab] of Inside.TABS) { Inside.open(k, "components", { tab }); note(`${titleOf(k)}, design tab ${tab}`); }
      Inside.open(k, "containers");
      const page = Nav.pageBeside();
      for (const [name, root] of [["The design", Inside.designKey()], ["The page", page ? "read:" + page : ""], ["What's waiting", "lights"]]) {
        if (root) { App.root = root; App.trail = []; Panel.render(); note(`${titleOf(k)}, panel tab ${name}`); }
      }
      go(k, { reset: true }); note(`panel, app ${titleOf(k)}`);
    }
    const contract = D.map.contracts[0], unknown = D.asks[0];
    if (contract) { go(contract.id || contract.key, { reset: true }); note("panel, a contract"); }
    if (unknown) { go(unknown.id, { reset: true }); note("panel, an unknown"); }
    if (D.flows[0]) { go(D.flows[0].key, { reset: true }); note("panel, a flow"); }
  }
  /* The sensor must see what it is for: a nowrap pill in a 90 px box sticks out, the same pill allowed to wrap does not. */
  function sensorSeesOverflow(ok) {
    const box = h("div", { style: "width:90px;display:flex;position:absolute;left:0;top:0" }), long = "a status that is far too long for this box";
    const out = h("span", { class: "pill", style: "white-space:nowrap;flex:none" }, long), wrapped = h("span", { class: "pill" }, long);
    box.append(out); $("#main").append(box);
    const seen = TextFit.textFits(box).length;
    box.replaceChildren(wrapped);
    const fine = TextFit.textFits(box).length;
    box.remove();
    ok(seen === 1 && fine === 0, "text fits: the sensor flags a pill that sticks out of its box and passes the same pill when it may wrap", `text fits: the sensor saw ${seen} of 1 planted overflows and ${fine} false alarms`);
  }
  /* The two newer sensors must see what they are for. Prose in a short hidden-overflow box is cut mid-sentence; the same box
     with a Show more beside it, or with a line-clamp, is not. A heading that opens with a code is a code where a name
     belongs; the name with the code in a small tag is not. */
  function sensorSeesCutProseAndCodes(ok) {
    const words = "The agent keeps who agreed and what access was granted, and it answers the consent check on every read of the calendar. ".repeat(3);
    const host = h("div", { style: "position:absolute;left:0;top:0;width:260px" }), box = (extra, ...kids) => h("div", { style: "height:36px;overflow:hidden;" + (extra || "") }, h("p", {}, words), ...kids);
    const cut = box(), withMore = h("div", {}, box(), h("button", { "data-more": "" }, "Show more")), clamped = box("-webkit-line-clamp:2;display:-webkit-box;-webkit-box-orient:vertical");
    host.append(cut, withMore, clamped); $("#main").append(host);
    const seen = TextFit.clippedText(host).length;
    host.replaceChildren(withMore); const more = TextFit.clippedText(host).length;
    host.replaceChildren(clamped); const clamp = TextFit.clippedText(host).length;
    host.replaceChildren(cut); const alone = TextFit.clippedText(host).length;
    host.replaceChildren(h("h3", {}, "CON-001 Consent check"), h("h3", {}, "Consent check", h("span", { class: "id-tag" }, "CON-001")));
    const codes = TextFit.bareLabels(host).map((b) => b.text);
    host.remove();
    ok(alone === 1 && more === 0 && clamp === 0 && seen === 1, "text fits: the sensor flags prose cut with no ellipsis and passes it with a Show more or a line-clamp", `text fits: the cut-prose sensor saw ${alone} of 1 cut, ${more} with Show more, ${clamp} clamped, ${seen} in the mixed set`);
    ok(codes.length === 1 && codes[0] === "CON-001 Consent check", "text fits: the sensor flags a title that is a code and passes the name with the code in a small tag", `text fits: the code sensor flagged ${JSON.stringify(codes)}`);
  }
  /* The path sensor must see what it is for: a path in a view head's words and a commit in its tooltip are flagged; the
     plan's own page text (.r-text), plain words, a date and "and/or" are not. */
  function sensorSeesBuilderWords(ok) {
    const host = h("div", { class: "view-head", style: "position:absolute;left:0;top:0" },
      h("span", {}, "Page 06-runtime/06-flows.md"), h("span", { title: "Built from commit 6495b67" }, "Built 12 Oct."),
      h("span", {}, "Flow pages live in flows/ and runtime pages in apps/."),
      h("article", { class: "r-text" }, h("p", {}, "The page lives in 06-runtime/flows/FLO-001.md.")),
      h("span", { title: "Open the page, as it is written" }, "Read it on 2026-10-12, calendar and/or transcripts."));
    $("#main").append(host);
    const seen = TextFit.builderWords(host).map((b) => b.text);
    host.remove();
    ok(seen.length === 3 && seen.every((t) => !t.includes("calendar") && !t.includes("FLO-001")),
      "reader text: the sensor flags a file path, a folder and a commit hash, and passes plain words and the plan's own page text",
      `reader text: the path sensor flagged ${JSON.stringify(seen)}`);
  }
  /* The voice sensors must see what they are for: a check code, a flag and an ISO date in reader text are flagged, the same
     words in the plan's own page text and an ID in its small tag are not; a count sentence said twice is flagged, once is
     not, and a date is not a count; a marked count that disagrees with its source, or names nothing, is flagged. */
  function sensorSeesVoice(ok) {
    const host = h("div", { id: "main-probe", style: "position:absolute;left:0;top:0;width:600px" });
    const panel = $("#panel");
    host.append(h("p", {}, "Set aside by E316."), h("p", {}, "Answer due 2026-11-06."), h("p", {}, "Run it with --force."), h("p", { class: "r-text" }, "E316 and 2026-11-06 as the page wrote them."),
      h("p", {}, "Digest as client record", h("span", { class: "id-tag" }, "UNK-064")));
    panel.append(host);
    const mine = (b) => host.textContent.includes(b.text.slice(0, 16));
    const leaks = VoiceGate.leaks(panel).filter(mine).map((b) => b.kind);
    host.replaceChildren(h("p", {}, "18 questions block work. The first is due 29 Oct."), h("p", {}, "18 questions block work."), h("p", {}, "Due 29 Oct 2026 for the product owner."), h("p", {}, "Due 29 Oct 2026 for the product owner."));
    const twice = VoiceGate.repeats(panel).filter(mine).map((b) => b.text);
    const want = VoiceGate.sources();
    host.replaceChildren(h("b", { "data-quantity": "openQuestions", "data-n": want.openQuestions + 1 }, String(want.openQuestions + 1)), h("b", { "data-quantity": "openQuestion", "data-n": 1 }, "1"),
      h("b", { "data-quantity": "openQuestions", "data-n": want.openQuestions }, String(want.openQuestions)));
    const wrong = VoiceGate.quantities(host).map((b) => b.name);
    host.remove();
    ok(leaks.includes("check code") && leaks.includes("flag") && leaks.includes("ISO date") && leaks.length === 3,
      "voice: the leak sensor flags a check code, a flag and an ISO date in reader text, and passes the page's own words and an ID in its tag", `voice: the leak sensor flagged ${JSON.stringify(leaks)}`);
    ok(twice.length === 1 && twice[0] === "18 questions block work", "voice: the repeat sensor flags a count sentence said twice on one screen, and passes a date said twice", `voice: the repeat sensor flagged ${JSON.stringify(twice)}`);
    ok(wrong.length === 2 && wrong.includes("openQuestions") && wrong.includes("openQuestion"), "voice: the count sensor flags a marked count that disagrees with its source and one that names no quantity", `voice: the count sensor flagged ${JSON.stringify(wrong)}`);
  }
  async function checks(ok) {
    sensorSeesOverflow(ok);
    sensorSeesCutProseAndCodes(ok);
    sensorSeesBuilderWords(ok);
    sensorSeesVoice(ok);
    if (!D.map.apps.length) return;
    const was = Theme.id, fx = FX.on, themes = [...Theme.LIST.map((t) => [t.id, t.label, true]), [was, "Plain", false]];
    for (const [id, label, motion] of themes) {
      found.clear(); Theme.set(id); FX.set(motion);
      voice.on = id === themes[0][0] && motion;
      try { await sweep(); } catch (e) { found.set(`the sweep threw: ${e.message} ${(e.stack || "").split("\n")[1]}`, { view: "sweep", why: "", more: 0 }); }
      if (voice.on) {
        const said = (map) => [...map].map(([id, f]) => `${f.view}: ${id} ${f.why}${f.more ? ` (and in ${plural(f.more, "other view")})` : ""}`);
        const leaks = said(voice.leaks), twice = said(voice.repeats), counts = [...said(voice.quantities), ...VoiceGate.disagreements()];
        ok(!leaks.length, "voice: no view shows a check code, gate, command, flag, file path, branch, session name, ISO date, handle or commit hash in reader text (say.LEAD_PATTERNS)",
          `voice: ${plural(leaks.length, "leak")} in reader text: ${leaks.slice(0, 12).join(" | ")}`);
        ok(!twice.length, "voice: no view says the same count sentence twice", `voice: ${plural(twice.length, "count sentence")} said twice on one screen: ${twice.slice(0, 10).join(" | ")}`);
        ok(!counts.length && VoiceGate.given.size >= 3, `voice: every view gives the same number for the same quantity (${[...VoiceGate.given.keys()].join(", ")}), each the one source's`,
          `voice: counts that disagree: ${counts.slice(0, 10).join(" | ")}${VoiceGate.given.size < 3 ? `; only ${VoiceGate.given.size} quantities were marked anywhere` : ""}`);
        voice.on = false;
      }
      const list = [...found].map(([id, f]) => `${f.view}: ${id} ${f.why}${f.more ? ` (and in ${plural(f.more, "other view")})` : ""}`);
      ok(!list.length, `text fits: in ${label}, no label in any view runs past its box, no prose is cut off without a Show more, no title is a bare ID (window ${innerWidth}x${innerHeight})`,
        `text fits in ${label} at ${innerWidth}x${innerHeight}: ${list.length} problems, ${list.slice(0, 14).join(" | ")}`);
    }
    Theme.set(was); FX.set(fx);
  }
  SelfTest.textFits = TextFit.textFits;
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await checks(ok); } catch (e) { lines.push("FAIL the text-fit checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the text-fit checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();

/* ------------------------------------------------------------ Every diagram node opens the panel (E44)
   The standing rule: every node of every diagram is clickable and opens more about it in the right-hand panel, and works
   from the keyboard. Nodes.wire (core.js) is the one way a node is drawn; this sweep is its sensor. For each diagram the
   page draws it renders the diagram afresh for every node (a click can redraw the page), clears the panel, clicks the
   node, and fails when the panel does not show a heading and a body that were not there before; then the same with the
   Enter key. It also lists any node-shaped element that was drawn without going through the helper. A failure names the
   diagram and the node's words. */
(() => {
  const base = SelfTest.run;
  const frames = () => Promise.resolve();
  const NODE_SHAPES = ".hit, g.station, g.works, .also-chip, .also-tab, .mini-lamp, .rl-node, path.rl-cor, .in-node, .seq-head, .seq-step, .in-label.pick, .bar-r, .mini-node, .line-hit, .track-label, .cluster-name";
  const panelNow = () => {
    const b = $("#panel-body"), head = b && $(".p-head h2", b), body = b && $(".p-body, .reader", b);
    return { text: b ? b.textContent.trim() : "", head: head ? head.textContent.trim() : "", body: body ? body.textContent.trim() : "", empty: !!(b && $(".p-empty", b)) };
  };
  const fresh = (before, after) => !!after.head && !!after.body && !after.empty && after.text !== before.text;
  const press = (el, how) => el.dispatchEvent(how === "click" ? new MouseEvent("click", { bubbles: true, cancelable: true }) : new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
  const words = (el) => (el.getAttribute("data-node") || el.getAttribute("aria-label") || el.textContent || el.getAttribute("class") || "").replace(/\s+/g, " ").trim().slice(0, 60);

  /* The diagrams: how to draw each one, and the element that holds it. */
  function diagrams() {
    const apps = D.map.apps.map((a) => a.key), list = [];
    const map = (name, lens, group, extra) => list.push({ name, root: "#board", show: () => { Nav.home(); MapView.st.lens = lens; MapView.st.group = group; MapView.st.focus = null; if (extra) extra(); rerender(); } });
    map("map, cockpit", "cockpit", "none");
    if (apps.length) map("map, one app and its neighbors", "cockpit", "none", () => { MapView.st.focus = apps[0]; });
    map("map, grouped by domain, clusters closed", "cockpit", "domain", () => MapGroups.all(false));
    map("map, grouped by domain, clusters open", "cockpit", "domain", () => MapGroups.all(true));
    map("map, grouped by capability, clusters open", "cockpit", "capability", () => MapGroups.all(true));
    map("map, line map", "transit", "none");
    list.push({ name: "releases", root: "#main", show: () => { Releases.st.compare = false; Releases.st.at = 0; Nav.open("releases"); } });
    if (D.slicePlan.list.length) {
      list.push({ name: "slices, table, every row open", root: "#main", show: () => { Slices.st.layout = "table"; Slices.st.open = new Set(D.slicePlan.list.map((x) => x.slice)); Nav.open("slices"); } });
      list.push({ name: "slices, path", root: "#main", show: () => { Slices.st.layout = "path"; Slices.st.open = new Set(); Nav.open("slices"); } });
    }
    D.flows.slice(0, 4).forEach((f) => list.push({ name: `flow ${f.key}`, root: "#main", show: () => Flows.select(f.key, -1) }));
    list.push({ name: "progress, open questions by week", root: "#main", show: () => showView("progress") });
    list.push({ name: "the minimap", root: "#panel-mini", show: () => { Nav.home(); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; rerender(); } });
    // the inside levels are the same code for every app, so a big vault sweeps the apps with a design or a plan first, at most six
    const inside = [...apps.filter((k) => D.designs[k] || (D.plans || {})[k]), ...apps.filter((k) => !D.designs[k] && !(D.plans || {})[k])].slice(0, 6);
    for (const k of inside) {
      const d = D.designs[k], p = (D.plans || {})[k], name = titleOf(k);
      list.push({ name: `inside ${name}, context`, root: "#inside-stage", show: () => Inside.open(k, "context") });
      list.push({ name: `inside ${name}, containers`, root: "#inside-stage", show: () => Inside.open(k, "containers") });
      if (d) {
        list.push({ name: `inside ${name}, components`, root: "#inside-stage", show: () => Inside.open(k, "components", { tab: "trace" }) });
        list.push({ name: `inside ${name}, data model`, root: "#inside-stage", show: () => Inside.open(k, "components", { tab: "data" }) });
        list.push({ name: `inside ${name}, key flows`, root: "#inside-stage", show: () => Inside.open(k, "components", { tab: "flows" }) });
      }
      if (p) list.push({ name: `inside ${name}, build plan`, root: "#inside-stage", show: () => Inside.open(k, "plan") });
    }
    return list;
  }
  async function sweepOne(d, ok) {
    MapView.clearDrop();
    d.show(); await frames();
    const root = $(d.root);
    if (!root) { ok(false, "", `node sweep, ${d.name}: the diagram's holder ${d.root} is not on the page`); return; }
    const nodes = $$("[data-node]", root), loose = $$(NODE_SHAPES, root).filter((el) => !el.hasAttribute("data-node") && !el.closest("[data-node]") && !el.closest(".in-mini, #panel-mini .mini-head"));
    const bad = [], badAt = new Set();
    const named = nodes.filter((el) => el.getAttribute("aria-label") || el.textContent.trim());
    let live = $$("[data-node]", $(d.root));  // drawn again only when a click redrew the page: drawing is what costs the time
    // every node of a diagram of ordinary size; a drawing of hundreds (the synthetic 24-app vault) is walked at an even stride, 60 nodes, so the page's check stays quick
    const MAX = 60, picks = nodes.length <= MAX ? nodes.map((_, i) => i) : Array.from({ length: MAX }, (_, j) => Math.floor((j * nodes.length) / MAX));
    for (const i of picks) {
      for (const how of ["click", "Enter"]) {
        if (!live[i] || !live[i].isConnected) { d.show(); await frames(); live = $$("[data-node]", $(d.root)); }
        const el = live[i];
        if (!el) { bad.push(`${how}: node ${i + 1} is gone after a redraw`); continue; }
        if (how === "Enter" && el.getAttribute("tabindex") === "-1") continue;  // a small part inside a focusable parent: the parent is the keyboard's way in
        const label = words(el);
        go("lights", { reset: true });
        const before = panelNow();
        press(el, how);
        await frames();
        if (!fresh(before, panelNow())) { bad.push(`${how} on "${label}"`); badAt.add(i); }
      }
    }
    ok(!bad.length && named.length === nodes.length, `node sweep, ${d.name}: ${plural(nodes.length, "node")}${picks.length < nodes.length ? ` (${picks.length} of them, at an even stride)` : ""}, each opens the panel by click and by Enter`,
      `node sweep, ${d.name}: the panel stayed empty or unchanged for ${badAt.size} of ${plural(nodes.length, "node")}: ${bad.slice(0, 6).join("; ")}${named.length !== nodes.length ? `; ${nodes.length - named.length} have no name` : ""}`);
    ok(!loose.length, `node sweep, ${d.name}: every node-shaped element was drawn through Nodes.wire`,
      `node sweep, ${d.name}: ${plural(loose.length, "node")} drawn without Nodes.wire, so with no click target or name: ${loose.slice(0, 6).map(words).join("; ")}`);
  }
  async function checks(ok, out) {
    if (!D.map.apps.length) { out.push("skip node sweep: vault has no apps"); return; }
    const list = diagrams(), seen = new Set();
    for (const d of list) {
      d.show(); await frames();
      const key = d.root + "|" + $$("[data-node]", $(d.root) || document.body).map((n) => n.getAttribute("data-node")).join("\u0001");
      if (seen.has(key)) { out.push(`skip node sweep, ${d.name}: draws the same nodes as an earlier diagram`); continue; }
      seen.add(key);
      await sweepOne(d, ok);
    }
    // a node without a name, or without exactly one click target, is refused at draw time and never drawn
    let refused = 0;
    for (const spec of [{}, { label: "x" }, { label: "x", key: "a", open: () => 0 }, { label: " ", key: "a" }]) { try { Nodes.wire(document.createElementNS(SVGNS, "g"), spec); } catch (e) { refused++; } }
    ok(refused === 4, "node sweep: the helper refuses a node with no name, no click target, or two", `node sweep: the helper let ${4 - refused} of 4 malformed nodes through`);
  }
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await checks(ok, lines); } catch (e) { lines.push("FAIL the node sweep threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the node sweep: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();

/* ------------------------------------------------------------ the key under every diagram (core.js, Legend)
   A block of its own, last, so it merges apart from the rest: it wraps SelfTest.run and adds its lines. It tours every
   diagram the page draws, in the states a reader reaches them in (picked, grouped, closed, a line chosen, a flow
   played, an app's levels), and in each: every look the drawing really has is in its key, every look the key lists is
   in the drawing, and every drawing has a key at all. A failure names the diagram and the meaning that is missing. */
(() => {
  const base = SelfTest.run;
  const found = new Map(), visited = new Set();
  /* Each drawing the page can show, how to find it, and the key it must have. */
  const EXPECT = [
    ["svg.cockpit.grouped", "map-grouped"], ["#main svg.cockpit.focus", "map-focus", "outside"], ["#inside-stage svg.cockpit.focus", "inside-context", "inside"],
    ["#main svg.cockpit:not(.grouped):not(.focus):not(.containers):not(.components)", "map-cockpit", "outside"], ["svg.transit", "map-lines"], ["table.dsm", "map-matrix"],
    ["svg.rl-map", "releases"], [".sl-table", "slices"], [".sl-path", "slices"], ["canvas.stage-canvas", "flow"], [".fp-pop:not([hidden])", "flows-list|lines-list"],
    ["svg.containers", "inside-containers"], ["svg.components", "inside-components"], [".in-er svg", "inside-data"], [".in-seq svg", "inside-sequence"],
    ["svg.plan-dag-svg", "plan-waits"], [".due-chart", "progress-due"], [".card table.t .ladder:not(.inline)", "progress-table"], [".card table.t .mix", "progress-table"],
  ];
  function look(where) {
    for (const p of Legend.audit()) if (!found.has(p)) found.set(p, where);
    const keys = Legend.keyed();
    for (const [sel, name, scope] of EXPECT) for (const el of $$(sel)) {
      if (scope === "outside" && el.closest("#inside-stage")) continue;
      const own = keys.find((lg) => name.split("|").includes(lg.name) && lg.def.root() && lg.def.root().contains(el));
      if (!own) found.set(`${name}: a drawing (${sel}) is on the page and has no key`, where);
      else visited.add(own.name);
    }
  }
  async function tour() {
    const apps = D.map.apps.map((a) => a.key);
    Nav.home(); go("lights", { reset: true });
    MapView.st.group = "none"; MapView.st.focus = null;
    for (const lens of ["cockpit", "transit", "matrix", "releases"]) {
      MapView.st.lens = lens; rerender(); look(`map, ${lens}`);
      if (lens === "cockpit" && apps.length) { go(apps[0], { reset: true }); look("map, cockpit, an app picked"); go("lights", { reset: true }); }
      if (lens === "transit" && D.flows.length) { MapView.st.line = D.flows[0].key; rerender(); look("map, line map, a line picked"); MapView.st.line = null; }
      if (lens === "matrix" && apps.length) { go(apps[0], { reset: true }); look("map, matrix, an app picked"); go("lights", { reset: true }); }
    }
    for (const g of ["domain", "capability"]) {
      if (!D.grouping[g]) continue;
      MapView.st.lens = "cockpit"; MapView.st.group = g;
      for (const open of [true, false]) { MapGroups.all(open); rerender(); look(`map, grouped by ${g}, ${open ? "open" : "closed"}`); }
      if (apps.length) { go(apps[0], { reset: true }); look(`map, grouped by ${g}, an app picked`); go("lights", { reset: true }); }
    }
    MapView.st.group = "none"; MapView.st.lens = "cockpit";
    for (const k of apps.slice(0, 3)) { MapView.st.focus = k; rerender(); look(`map, focus on ${titleOf(k)}`); }
    MapView.st.lens = null; MapView.st.group = null; MapView.st.focus = null; rerender();
    if (D.slicePlan.list.length) {
      for (const layout of ["table", "path"]) { Slices.st.layout = layout; Nav.open("slices"); look(`slices, ${layout}`); }
      Slices.st.layout = null;
    }
    Nav.open("releases"); look("releases section");
    for (let j = 0; j < Releases.STATES.length; j++) { const stop = $(`.rel-stop[data-state="${j}"]`); if (stop) { stop.click(); look(`releases, state ${j}`); } }
    Releases.st.compare = true; Releases.st.a = 0; Releases.st.b = Releases.STATES.length - 1; rerender(); look("releases, compared");
    Releases.st.compare = false; Releases.st.at = 0;
    if (D.flows.length) {
      showView("flows");
      for (const f of D.flows.slice(0, 6)) { Flows.select(f.key, -1); look(`flow ${f.key}`); }
      const picker = $(".flow-picker"); if (picker) { picker.open(); look("flows list"); }
      showView("map");
    }
    showView("progress"); look("progress");
    for (const k of apps) {
      for (const level of ["context", "containers", "components", "plan"]) {
        Inside.open(k, level); look(`${titleOf(k)}, inside ${level}`);
      }
      if (D.designs[k]) for (const tab of ["data", "flows"]) { Inside.open(k, "components", { tab }); look(`${titleOf(k)}, design tab ${tab}`); }
    }
    Nav.home(); go("lights", { reset: true });
  }
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    // The sensor must see what it is for: a look drawn but left out of its key, and a look in the key that is not drawn.
    const planted = h("div", {}, h("span", { class: "x-drawn" }));
    $("#main").append(planted);
    const fake = Legend.open("selftest-planted", { root: () => planted, probes: { "lamp.warning": ".x-drawn", "lamp.caution": ".x-absent" } });
    planted.append(fake.el()); fake.saw("lamp.caution"); fake.paint();
    const seen = Legend.audit().filter((p) => p.startsWith("selftest-planted"));
    planted.remove(); Legend.forget("selftest-planted");
    ok(seen.length === 2 && seen.some((p) => /drawing has/.test(p)) && seen.some((p) => /does not have it/.test(p)), "keys: the sensor flags a look drawn but missing from its key, and a look in the key that is not drawn", `keys: the sensor saw ${seen.length} of 2 planted faults: ${seen.join(" | ")}`);
    try {
      found.clear(); visited.clear();
      if (D.map.apps.length) await tour();
      const list = [...found].map(([problem, where]) => `${problem} (seen in ${where})`);
      const want = D.map.apps.length ? ["map-cockpit", "map-lines", "map-matrix", "releases", "progress-due"].concat(D.flows.length ? ["flow", "flows-list"] : []) : [];
      const missing = want.filter((n) => !visited.has(n));
      ok(!list.length, `keys: in ${visited.size} diagrams (${[...visited].sort().join(", ")}) every look drawn is in the key and every look in the key is drawn`,
        `keys: ${list.length} problems, ${list.slice(0, 12).join(" | ")}`);
      ok(!missing.length, "keys: the tour reached the cockpit, the line map, the matrix, releases and the progress charts, and each had a key", `keys: the tour found no key for ${missing.join(", ")}`);
    } catch (e) { lines.push("FAIL the key checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the key checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
