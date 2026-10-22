/* ------------------------------------------------------------ Capability views (capview.js)
   Cards, focus and matrix all draw D.capDeps and nothing else; the selection is carried from one to the next. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 40));
  const EDGES = D.capDeps.edges, NO_CAPS = D.capDeps.noCapabilities;
  const caps = () => D.trace.capabilities.map((c) => c.key);
  const press = (el, k) => el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  const said = (card) => (($(".cv-said", card) || $(".pill", card) || {}).textContent || "");  // state is said by the pill, the others by the line beside it
  const drawnWords = (el) => [...el.childNodes].filter((n) => n.nodeType === 3 || n.localName === "tspan").map((n) => n.textContent).join("");
  const inside = (inner, outer) => inner.x >= outer.x - 0.5 && inner.y >= outer.y - 0.5 && inner.x + inner.width <= outer.x + outer.width + 0.5 && inner.y + inner.height <= outer.y + outer.height + 0.5;

  /* The data: every edge has a reason in a flow whose capabilities were recorded, and nothing else. */
  function reasons(ok) {
    const bad = [];
    for (const e of EDGES) {
      if (!caps().includes(e.from) || !caps().includes(e.to) || e.from === e.to) bad.push(`${e.from} > ${e.to}: not two different capabilities`);
      if (!e.flows.length || e.nFlows !== e.flows.length) bad.push(`${e.from} > ${e.to}: flows ${e.flows.length}, said ${e.nFlows}`);
      if (e.nContracts !== e.contracts.length || e.contracts.some((c) => !CONTRACT[c])) bad.push(`${e.from} > ${e.to}: contracts ${e.contracts.join(",")}`);
      for (const f of e.flows) {
        const fl = FLOW[f.flow];
        if (!fl || fl.capabilitiesFrom !== "frontmatter") { bad.push(`${e.from} > ${e.to}: ${f.flow} has no recorded capabilities`); continue; }
        const lists = f.lists && fl.capabilities[0] === e.from && fl.capabilities.includes(e.to);
        const repeats = f.repeats.some((r) => fl.capabilities[0] === e.from && FLOW[r] && FLOW[r].capabilities[0] === e.to);
        if (!lists && !repeats) bad.push(`${e.from} > ${e.to}: ${f.flow} neither lists ${e.to} with ${e.from} first nor repeats a flow that does`);
      }
      if (e.both !== EDGES.some((x) => x.from === e.to && x.to === e.from)) bad.push(`${e.from} > ${e.to}: both-ways flag is wrong`);
    }
    const bare = D.flows.filter((f) => f.capabilitiesFrom !== "frontmatter").map((f) => f.key).sort();
    if (bare.join() !== [...NO_CAPS].sort().join()) bad.push(`flows without recorded capabilities: page says ${NO_CAPS.join(",")}, flows say ${bare.join(",")}`);
    ok(!bad.length, `capability dependencies: ${EDGES.length} edges, each from a flow that records its capabilities, and ${NO_CAPS.length} flows left out`, `capability dependencies: ${bad.slice(0, 4).join(" | ")}`);
  }

  async function cardsView(ok) {
    Nav.open("capabilities"); await tick();
    const cards = $$("#main .cv-card");
    ok(App.view === "capmap" && cards.length === caps().length && cards.every((c) => c.tagName === "BUTTON" && c.tabIndex >= 0), `capability cards: one keyboard-reachable button for each of the ${caps().length} capabilities`, `capability cards: ${cards.length} cards for ${caps().length} capabilities in ${App.view}`);
    const wrong = caps().filter((k) => {
      const card = $(`#main .cv-card[data-cap="${k}"]`), row = card && $(".cv-deps", card), n = EDGES.filter((e) => e.from === k).length, by = EDGES.filter((e) => e.to === k).length;
      return !row || row.textContent.replace(/\s+/g, "") !== `Needs${n}Neededby${by}`;
    });
    ok(!wrong.length, "capability cards: each card's Needs and Needed by counts are the edges the flows make", `capability cards: wrong counts on ${wrong.join(", ")}`);
    const groups = $$("#main .cv-group");
    ok(groups.length >= 1 && groups.reduce((n, g) => n + $$(".cv-card", g).length, 0) === caps().length, `capability cards: ${groups.length} release groups hold every card once`, "capability cards: groups do not hold each card once");
    const seen = new Set();
    for (const mode of ["state", "open", "ready"]) {
      $(`#main [data-color="${mode}"]`).click(); await tick();
      const ink = $$("#main .cv-card").map((c) => getComputedStyle(c).borderLeftColor + "|" + said(c));
      seen.add(ink.join(";"));
      ok($(`#main [data-color="${mode}"]`).getAttribute("aria-pressed") === "true" && $$("#main .cv-card").every((c) => said(c).length > 0), `capability cards: colored by ${mode}, every card says in words what its color means`, `capability cards: ${mode} left a card without words`);
    }
    ok(seen.size > 1, "capability cards: the three colorings are different", "capability cards: the three colorings look the same");
    $('#main [data-color="state"]').click(); await tick();
    const first = $("#main .cv-card");
    first.click(); await tick();
    const k = first.dataset.cap;
    ok(CapFocus.key() === k && !!($("#cv-board svg.cv-svg") || $("#main .cv-lone")) && /./.test($("#panel-body h2") ? $("#panel-body h2").textContent : ""), "capability cards: picking a card opens its focus view and its details in the panel", `capability cards: key ${CapFocus.key()}, view ${App.view}`);
    Nav.open("capabilities"); await tick();
    if (caps().length > 12) ok(!!$("#main [data-cv-matrix]"), `capability cards: ${caps().length} capabilities, so the matrix is offered`, "capability cards: no matrix offer past twelve");
    else ok(!$("#main [data-cv-matrix]") && !!$('#main [data-cv="matrix"]'), `capability cards: ${caps().length} capabilities, the matrix is one click away in the toggle and not pushed`, "capability cards: matrix offer wrong");
    if (!EDGES.length) ok(!!$('#main .empty-state[data-empty*="no capability depends"]'), "capability cards: no flow records capabilities, and the page says so and points at /vela:shape", "capability cards: no empty state for a vault without recorded flows");
    else if (NO_CAPS.length) { const note = $("#main [data-no-caps]"); ok(!!note && +note.dataset.noCaps === NO_CAPS.length && $$("[data-ref]", note).length === Math.min(6, NO_CAPS.length), `capability cards: ${NO_CAPS.length} flows left out are named and linked`, "capability cards: the left-out flows are not named"); }
  }

  async function focusView(ok) {
    const linked = caps().filter((k) => EDGES.some((e) => e.from === k || e.to === k));
    if (!linked.length) { ok(true, "skip capability focus view: no capability has a dependency in the flows here"); return; }
    const k = linked.sort((a, b) => EDGES.filter((e) => e.to === b || e.from === b).length - EDGES.filter((e) => e.to === a || e.from === a).length)[0];
    Nav.open("capabilities", k); await tick();
    const left = EDGES.filter((e) => e.to === k), right = EDGES.filter((e) => e.from === k), svg = $("#cv-board svg.cv-svg");
    const nodes = (side) => $$(`#cv-board .cv-node:not(.sel)`).filter((n) => (side === "l") === (+n.querySelector("rect").getAttribute("x") < 100));
    ok(!!svg && $("#cv-board .cv-node.sel").dataset.cap === k, `capability focus view: ${titleOf(k)} stands in the middle`, "capability focus view: the picked capability is not in the middle");
    ok(nodes("l").length === Math.min(7, left.length) && nodes("r").length === Math.min(7, right.length), `capability focus view: ${left.length} that need it on the left and ${right.length} it needs on the right, at most seven a side`, `capability focus view: drawn ${nodes("l").length} / ${nodes("r").length} for ${left.length} / ${right.length}`);
    const folded = Math.max(0, left.length - 7) + Math.max(0, right.length - 7);
    ok($$("#cv-board .cv-more").length === (left.length > 7) + (right.length > 7), `capability focus view: ${folded ? "the rest fold into +N more" : "nothing folds, since no side passes seven"}`, "capability focus view: +N more is wrong");
    const chips = $$("#cv-board .cv-edge");
    ok(chips.length === nodes("l").length + nodes("r").length && chips.every((c) => /^\d+ contracts?$/.test(drawnWords($(".cv-chip-n", c)).trim()) && drawnWords($(".cv-chip-t", c)).trim().length > 0 && c.tabIndex >= 0), "capability focus view: every arrow has a chip naming its flow and its contract count, reachable by keyboard", `capability focus view: chips ${chips.map((c) => c.textContent).join(" | ")}`);
    const cut = $$("#cv-board text").map(drawnWords).filter((w) => /…\s*$/.test(w));
    const spill = $$("#cv-board .cv-node, #cv-board .cv-edge").filter((g) => $$("text", g).some((x) => !inside(x.getBBox(), g.querySelector("rect").getBBox())));
    ok(!cut.length && !spill.length, "capability focus view: no label is cut, and each one sits inside its box", `capability focus view: cut ${cut.join("|")}, spilling ${spill.map((g) => g.textContent).join("|")}`);
    const board = $("#cv-board");
    ok(!!board.querySelector(".zoom-bar") || !!board.closest(".zoom-frame") && !!board.closest(".zoom-frame").querySelector(".zoom-bar"), "capability focus view: it has the shared zoom bar", "capability focus view: no zoom bar");
    board.focus(); const z0 = Pan.view("capfocus").z; press(board, "+"); await tick();
    ok(Pan.view("capfocus").z > z0, "capability focus view: the + key zooms the drawing", "capability focus view: + did nothing");
    press(board, "0"); await tick();
    // a chip lists its flows and contracts in the panel
    const e = (left[0] || right[0]), chip = $(`#cv-board .cv-edge[data-dep="${e.from}>${e.to}"]`);
    chip.dispatchEvent(new MouseEvent("click", { bubbles: true })); await tick();
    const items = $$("#panel-body .mini-list li").length, heading = $("#panel-body h2") && $("#panel-body h2").textContent;
    ok(heading === `${titleOf(e.from)} needs ${titleOf(e.to)}` && items >= e.nFlows && e.contracts.every((c) => $(`#panel-body [data-ref="${c}"]`)) && e.flows.every((f) => $(`#panel-body [data-ref="${f.flow}"]`)),
      "capability focus view: a chip lists the flows that make the dependency and the contracts they cross, in the panel", `capability focus view: panel says "${heading}" with ${items} rows`);
    chip.classList.contains("picked") || ok(false, "capability focus view: the picked chip is marked in the drawing");
    // picking another capability refocuses, by mouse and by keyboard
    const other = nodes("l")[0] || nodes("r")[0];
    press(other, "Enter"); await tick();
    ok(CapFocus.key() === other.dataset.cap && $("#cv-board .cv-node.sel").dataset.cap === other.dataset.cap && $("#side .capfocus-bar"), "capability focus view: Enter on another box refocuses on it, and the sidebar follows", `capability focus view: key ${CapFocus.key()}`);
    // both ways are marked
    const pair = EDGES.find((x) => x.both);
    if (pair) { Nav.open("capabilities", pair.from); await tick(); ok(!!$(`#cv-board .cv-node.both[data-cap="${pair.to}"]`) && !!$("#main .cv-both"), "capability focus view: a pair that needs each other is marked on the box and said under the drawing", "capability focus view: both ways not marked"); }
    else ok(true, "skip capability focus view: no pair here needs each other");
    const wide = caps().find((c) => EDGES.filter((x) => x.to === c).length > 7 || EDGES.filter((x) => x.from === c).length > 7);
    if (wide) { Nav.open("capabilities", wide); await tick(); const before = $$("#cv-board .cv-node:not(.sel)").length; $("#cv-board .cv-more").dispatchEvent(new MouseEvent("click", { bubbles: true })); await tick();
      ok($$("#cv-board .cv-node:not(.sel)").length > before, "capability focus view: +N more shows the rest", "capability focus view: +N more did nothing"); }
    else ok(true, "skip capability focus view: no capability has more than seven on a side here");
    const lone = caps().find((c) => !EDGES.some((x) => x.from === c || x.to === c));
    if (lone) { Nav.open("capabilities", lone); await tick(); ok(!!$("#main .cv-lone") && /no dependencies/.test($("#main .cv-lone").textContent), "capability focus view: a capability no flow ties to another says so", "capability focus view: lone capability not explained"); }
  }

  async function matrixView(ok) {
    const sel = caps()[0];
    Nav.open("capabilities", sel); await tick();
    $('#main [data-cv="matrix"]').click(); await tick();
    const cells = $$("#main .cv-cell.d"), rows = $$("#main .cv-mx tbody tr");
    ok(App.view === "capmatrix" && rows.length === caps().length && cells.length === EDGES.length, `capability matrix: ${rows.length} rows, ${cells.length} filled cells, one for each edge`, `capability matrix: ${rows.length} rows, ${cells.length} cells for ${EDGES.length} edges in ${App.view}`);
    const wrong = EDGES.filter((e) => { const c = $(`#main .cv-cell.d[data-dep="${e.from}>${e.to}"]`); return !c || c.firstChild.textContent !== String(e.nFlows) || c.tagName !== "BUTTON" || !!c.querySelector(".cv-both-mark") !== e.both || !c.classList.contains("both") === e.both; });
    ok(!wrong.length, "capability matrix: each cell is a button with the number of flows, and a both-ways cell carries the mark", `capability matrix: wrong cells ${wrong.map((e) => e.from + ">" + e.to).join(", ")}`);
    ok(CapFocus.key() === sel && !!$("#main .cv-mx th.row.on") && $("#main .cv-mx th.row.on button").dataset.cap === sel, "capability matrix: the capability picked before is still the picked one, marked in its row", "capability matrix: selection lost");
    if (EDGES.length) {
      const e = EDGES[0], cell = $(`#main .cv-cell.d[data-dep="${e.from}>${e.to}"]`);
      cell.click(); await tick();
      ok(App.view === "capmatrix" && $("#panel-body h2").textContent === `${titleOf(e.from)} needs ${titleOf(e.to)}` && e.flows.every((f) => $(`#panel-body [data-ref="${f.flow}"]`)) && CapFocus.key() === e.from,
        "capability matrix: a cell lists its flows and contracts in the panel, and stays in the matrix with its row picked", `capability matrix: panel "${$("#panel-body h2").textContent}", view ${App.view}`);
    }
    const head = $("#main .cv-mx th.col button"); head.click(); await tick();
    ok(App.view === "capmatrix" && CapFocus.key() === head.dataset.cap, "capability matrix: a column name picks that capability and stays in the matrix", `capability matrix: header left ${App.view}`);
    $('#main [data-cv="cards"]').click(); await tick();
    const on = $("#main .cv-card.on");
    ok(App.view === "capmap" && !!on && on.dataset.cap === CapFocus.key(), "capability views: back on the cards, the capability picked in the matrix is still marked", `capability views: cards kept ${on ? on.dataset.cap : "nothing"}`);
    $('#main [data-cv="focus"]').click(); await tick();
    ok($("#cv-board .cv-node.sel, #main .cv-lone") && App.view === "capmap" && CapFocus.key() === (on && on.dataset.cap), "capability views: Focus opens the same capability", "capability views: Focus lost the selection");
    Nav.open("capabilities"); await tick();
    const menu = Nav.viewItems().map((x) => x.label).join("|");
    ok(/Capabilities/.test(menu) && /Dependency matrix/.test(menu), "capability views: the View menu offers the cards and the matrix", `capability views: menu ${menu}`);
    location.hash = "#s=capabilities&v=capmatrix"; await tick(); await tick();
    ok(App.view === "capmatrix", "capability views: a link with v=capmatrix opens the matrix", `capability views: hash left ${App.view}`);
    Nav.home(); await tick();
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try {
      reasons(ok);
      if (caps().length) { await cardsView(ok); await focusView(ok); await matrixView(ok); } else ok(true, "skip capability views: no capabilities in this vault");
    } catch (e) { lines.push(`FAIL the capability views check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the capability views checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
