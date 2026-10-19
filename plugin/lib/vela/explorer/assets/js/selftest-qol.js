/* ------------------------------------------------------------ Quality-of-life checks (the dashboard audit, batch 2)
   Each group checks one change the way a reader meets it. A page opened narrow (under COMPACT_BELOW) runs the
   "compact" group; a wide one runs the rest. `#only=qol` skips every other check so the narrow run is quick, since
   the older checks were written for a wide window. */
(() => {
  const base = SelfTest.run, tick = () => Promise.resolve();
  const headText = () => ($("#panel .p-head h2") || { textContent: "" }).textContent;
  const wide = () => innerWidth >= COMPACT_BELOW;
  const rect = (sel) => { const el = typeof sel === "string" ? $(sel) : sel; return el ? el.getBoundingClientRect() : { left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0 }; };
  const shown = (sel) => { const el = $(sel); return !!el && el.offsetParent !== null || (!!el && getComputedStyle(el).position === "fixed" && getComputedStyle(el).display !== "none"); };

  /* A narrow window: the diagram has the whole width, the panel and the menu are slide-overs that open on a pick and
     close on Esc, and nothing scrolls sideways. */
  async function compact(ok) {
    PanelSize.hide(true); SideSize.hide(true);  // earlier checks leave them as they like
    const saved0 = Settings.read("explorer.panel.hidden"); Nav.home(); await tick();
    const side = rect("#side"), panel = rect("#panel"), main = rect("#main");
    ok(document.body.classList.contains("compact") && !shown("#side") && !shown("#panel") && main.width >= innerWidth - 30,
      `compact, ${innerWidth} px: the menu and the panel start closed and the diagram has ${Math.round(main.width)} of the ${innerWidth} px (the rest is a gutter for the Details tab)`, `compact: menu shown ${shown("#side")}, panel shown ${shown("#panel")}, main ${Math.round(main.width)} of ${innerWidth}`);
    ok(!$("#side-toggle").hidden && $("#side-toggle").getAttribute("aria-expanded") === "false" && !$("#panel-tab").hidden,
      "compact: the hamburger and the Details tab are the ways back to the menu and the panel", "compact: the hamburger or the Details tab is missing");
    $("#side-toggle").click(); await tick();
    ok(shown("#side") && rect("#side").right <= innerWidth && getComputedStyle($("#side")).position === "fixed" && $("#side-toggle").getAttribute("aria-expanded") === "true",
      "compact: the hamburger slides the menu over the diagram", `compact: menu shown ${shown("#side")} at ${Math.round(rect("#side").width)} px`);
    $("#side .side-link[data-section='apps']").click(); await tick();
    ok(!shown("#side") && App.section === "apps", "compact: choosing a section closes the menu and shows its diagram", `compact: menu still shown ${shown("#side")} after choosing Apps`);
    const key = D.nodes.find((n) => n.kind === "app");
    if (key) {
      go(key.key, { reset: true }); await tick();
      ok(shown("#panel") && getComputedStyle($("#panel")).position === "fixed" && rect("#panel").right <= innerWidth + 1 && headText().includes(titleOf(key.key)),
        `compact: picking ${titleOf(key.key)} slides the panel over the diagram`, `compact: panel shown ${shown("#panel")} after a pick`);
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      await tick();
      ok(!shown("#panel") && !$("#panel-tab").hidden, "compact: Esc closes the panel and leaves the Details tab", `compact: panel shown ${shown("#panel")} after Esc`);
    }
    ok(Settings.read("explorer.panel.hidden") === saved0, "compact: opening and closing a slide-over does not touch the width-window's saved choice", "compact: saved choice changed");
    ok(document.documentElement.scrollWidth <= innerWidth + 1, `compact: nothing scrolls sideways at ${innerWidth} px`, `compact: the page is ${document.documentElement.scrollWidth} px wide in ${innerWidth}`);
  }

  /* Finding 4: an app's panel opens on the flows it is in and what it talks to, each a button that goes there. */
  async function appPanel(ok) {
    const apps = D.map.apps.map((a) => a.key);
    if (!apps.length) { ok(true, "app panel: this vault has no apps, so nothing to click"); return; }
    const bad = [];
    for (const k of apps) {
      Nav.open("apps"); go(k, { reset: true }); await tick();
      const secs = $$("#panel .p-links .p-sec"), titles = secs.map((x) => $("h3", x).textContent.trim());
      const flowN = flowsFor(k).filter((r) => FLOW[r.flow]).length, a = D.apps[k], talkN = [...a.consumes, ...a.provides].filter((id) => CONTRACT[id]).length;
      if (titles.join("|") !== "In these flows|Talks to") bad.push(`${titleOf(k)}: rows ${titles.join("|")}`);
      if ($$("#panel [data-flow]").length !== flowN || $$("#panel [data-contract]").length !== talkN) bad.push(`${titleOf(k)}: ${$$("#panel [data-flow]").length} of ${flowN} flows, ${$$("#panel [data-contract]").length} of ${talkN} contracts`);
      const links = $("#panel .p-links"), why = $$("#panel .p-sec").find((x) => $("h3", x) && /Why it's waiting/.test($("h3", x).textContent));
      if (links && why && !(links.compareDocumentPosition(why) & Node.DOCUMENT_POSITION_FOLLOWING)) bad.push(`${titleOf(k)}: the questions come before the chips`);
      if ($$("#panel .p-sec h3").some((x) => /^(Flows that cross this|Provides|Consumes)/.test(x.textContent.trim()))) bad.push(`${titleOf(k)}: the panel still relists flows or contracts`);
      if ($$("#panel .p-chip").some((x) => x.tagName !== "BUTTON" || /\b(APP|FLO|CON)-\d/.test(x.textContent))) bad.push(`${titleOf(k)}: a chip is not a button or shows a code`);
    }
    ok(!bad.length, `app panel: clicking any of ${apps.length} apps opens In these flows and Talks to first, as buttons by name, with the questions below`, `app panel: ${bad.slice(0, 5).join(" | ")}`);
    const withFlow = apps.find((k) => $$("[data-flow]").length || flowsFor(k).length);
    if (withFlow) {
      Nav.open("apps"); go(withFlow, { reset: true }); await tick();
      const chip = $("#panel [data-flow]"), want = chip.dataset.flow;
      chip.click(); await tick();
      ok(App.view === "flows" && Flows.st.key === want && ($("#panel .p-head h2") || { textContent: "" }).textContent.includes(titleOf(want)), `app panel: the flow chip plays ${titleOf(want)} in one click`, `app panel: the flow chip left view ${App.view}, flow ${Flows.st.key}`);
    }
    const withContract = apps.find((k) => D.apps[k].provides.length || D.apps[k].consumes.length);
    if (withContract) {
      Nav.open("apps"); go(withContract, { reset: true }); await tick();
      const chip = $("#panel [data-contract]"), want = chip.dataset.contract;
      chip.click(); await tick();
      ok(headText().includes(titleOf(want)) && App.focus === want, `app panel: the contract chip opens ${titleOf(want)}`, `app panel: the contract chip opened ${headText()}`);
    }
  }

  /* Finding 5: search lists one row per thing, with the apps it touches as pills, no Claude row unless Claude is attached,
     and Enter on a flow plays it with its apps lit. */
  async function searchRows(ok) {
    const word = D.flows.length ? (E[D.flows[0].key].title.toLowerCase().match(/[a-z]{4,}/g) || ["flow"]).pop() : "app";
    for (const q of [word, "digest", "consent", "agent"]) {
      const keys = Search.type(q), dup = keys.filter((k, i) => keys.indexOf(k) !== i);
      const rows = $$("#results .result");
      const clutter = rows.filter((r) => $(".r-flows", r) || ($(".r-snip", r) && $(".r-apps", r)));
      ok(!dup.length && rows.length === keys.length && !clutter.length && !(location.protocol === "file:" && $("#results .r-ask")),
        `search "${q}": ${rows.length} rows, one per thing, no Claude row on a file`, `search "${q}": duplicates ${dup.join(",")}, rows ${rows.length} of ${keys.length}, clutter ${clutter.length}, ask row ${!!$("#results .r-ask")}`);
    }
    const flow = D.flows[0] && D.flows[0].key;
    if (flow) {
      const keys = Search.type(E[flow].title), at = keys.indexOf(flow), row = $$("#results .result")[at], pills = row ? $$(".r-app", row).filter((x) => !x.classList.contains("more")).map((x) => x.textContent) : [];
      const want = flowStations(FLOW[flow]).filter((k) => NODE[k] && NODE[k].kind === "app").map(titleOf);
      ok(pills.length > 0 && pills.every((x) => want.includes(x)), `search: the ${titleOf(flow)} row shows the apps it touches as pills (${pills.join(", ")})`, `search: pills ${pills.join(",")} of ${want.join(",")}`);
      Search.pick(at); await tick();
      const lit = $$("#panel-mini .mini-ring").length;
      ok(App.view === "flows" && Flows.st.key === flow && lit === mapAnchors(flow).filter((k) => NODE[k]).length && lit > 0 && !!$("#present-btn"),
        `search: Enter on ${titleOf(flow)} plays the flow with ${lit} of its apps lit on the overview`, `search: Enter left view ${App.view}, flow ${Flows.st.key}, ${lit} apps lit`);
    }
    Search.type(""); Nav.home(); await tick();
  }

  /* Finding 7: one number, "N waiting", wherever the count is said; the 18 + 3 split is on hover, and the side's count of
     all open questions says so. Finding 13: no banner or notes above the Home map; the notes are an "i" in its bar. */
  async function oneNumber(ok) {
    const n = Queue.needsYou().n, top = $("#masters .master.caution b");
    Nav.home(); await tick();
    const card = $(".q-card .q-count"), panelLede = $("#panel .p-lede");
    Nav.open("apps"); go("lights", { reset: true }); App.root = "lights"; Panel.render(); await tick();
    const lede = $("#panel .p-lede");
    const words = [$("#main"), $("#panel"), $("#masters")].map((e) => e.textContent).join(" ");
    if (!n) { ok(/Nothing/.test(card ? card.textContent : "Nothing") && +top.textContent === 0, "waiting: nothing waiting, and every place says so", `waiting: top ${top && top.textContent}, card "${card && card.textContent}"`); }
    else ok(+top.textContent === n && card && card.textContent.startsWith(`${n} waiting`) && lede && lede.textContent.startsWith(`${n} waiting`) && / (isn't|aren't|blocking)/.test(lede.title) && !/\d+ questions? (blocks?|(is|are) blocking) work|other things? (isn|aren)/.test(words),
      `waiting: one number, ${n}, on the top bar, the waiting card and the panel, with its parts on hover`, `waiting: top ${top && top.textContent}, card "${card && card.textContent}", panel "${lede && lede.textContent}", loose words ${(words.match(/\d+ questions? (block|are blocking)[^.]*/) || [""])[0]}`);
    const side = $("#side .side-link[data-section='unknowns'] .side-n");
    ok(!side || (/in all/.test(side.title) && side.title.includes(`${Queue.needsYou().n}`)), "waiting: the sidebar's count says it is all open questions, and how many of the things waiting", `waiting: sidebar title "${side && side.title}"`);
    Nav.home(); await tick();
    const note = $("#main [aria-controls^='dmenu-notes']");
    if (!note) { ok(!$("#main .q-kicker") && !$("#main .countline"), "Home: no banner or note line above the map, and no i when the diagram has no notes", "Home: a banner or note line is above the map"); return; }
    ok(!$("#main .q-kicker") && !$("#main .countline") && !!note && note.textContent === "i" && /\w/.test(note.title), "Home: no banner or note lines above the map; its notes are an i in the diagram bar, read on hover",
      `Home: kicker ${!!$("#main .q-kicker")}, countline ${!!$("#main .countline")}, note button ${!!note}`);
    note.click(); await tick();
    ok(!document.getElementById(note.getAttribute("aria-controls")).hidden && $$(".dia-notes p").length >= 1, "Home: the i opens the notes in place", "Home: the i opened nothing");
    Menus.close();
  }

  /* Finding 8: one "Read full page" on screen beside a section's page, and its file link only in the ... menu.
     Finding 9: the doors are the sidebar's buttons, not also a tab strip on every door page.
     Finding 14: no percent that says "done" under three names, and the release timeline only on Releases. */
  async function onceEach(ok) {
    const shownBtns = (root) => $$("a, button", root).filter((b) => b.offsetParent !== null && /^Read (the )?full page$/.test(b.textContent.trim()));
    const bad = [];
    let n = 0;
    for (const sec of D.sections) {
      Nav.open(sec.id); await tick();
      if (!Nav.sectionPage() || Nav.pageBeside() === "") continue;
      n++;
      const read = [...shownBtns($("#main")), ...shownBtns($("#panel"))], files = $$("#panel .p-actions a[href]").filter((a) => /Open the page/.test(a.textContent));
      if (read.length !== 1) bad.push(`${sec.label}: ${read.length} Read full page buttons`);
      if (files.length) bad.push(`${sec.label}: the panel repeats the file link`);
    }
    ok(n > 0 && !bad.length, `one Read full page: ${n} sections beside their pages show it once, and the file link is only in the ... menu`, `one Read full page: ${bad.join(" | ") || "no section had a page"}`);
    const doors = [];
    for (const [id] of Roles.ROLES.slice(1)) { Nav.role(id); await tick(); doors.push(`${id}:${$$("#main .door-switch").length}`); }
    ok(doors.every((x) => x.endsWith(":0")) && $$("#side .side-roles button").length === Roles.ROLES.length - 1, `role doors: the sidebar's ${Roles.ROLES.length - 1} buttons are the only doors; no tab strip on any door page`, `role doors: ${doors.join(" ")}`);
    const pct = [];
    for (const id of ["exec", "mgr"]) { Nav.role(id); await tick(); if (/\d+%/.test($("#main").textContent) || $(".mini-time", $("#main"))) pct.push(id); if (!$("#main [data-to='releases']")) pct.push(id + " has no link to the timeline"); }
    Nav.open("apps"); showView("progress"); await tick();
    if (/\d+%/.test($("#main").textContent)) pct.push("progress");
    Nav.open("releases"); await tick();
    ok(!pct.length && !!$("#main .rel-body, #main .releases, #main [data-view]"), "no percent that reads as done, and no timeline repeated on the doors; Releases has the timeline and the doors link to it", `percent or timeline left on: ${pct.join(", ")}`);
    Nav.home(); await tick();
  }

  /* Finding 10: the theme is one gear at the far right of the top bar, after the need-you button; no Theme select, no Animation. */
  async function gear(ok) {
    const btn = $("#settings .dmenu-btn"), top = $(".top"), need = $("#masters .master.caution");
    ok(!!btn && !$("#theme") && !$(".theme-pick") && !/Animation|Theme\b/.test(top.textContent.replace(/Theme\s*$/, "")) && need && need.compareDocumentPosition(btn) & Node.DOCUMENT_POSITION_FOLLOWING && btn.getBoundingClientRect().right > innerWidth - 60,
      "top bar: one gear at the far right replaces the Theme select and the Animation switch, after the need-you button", `top bar: gear ${!!btn}, theme select ${!!$("#theme")}, top text "${top.textContent.trim().slice(0, 80)}"`);
    const was = Theme.id, other = Theme.LIST.find((t) => t.id !== was);
    btn.click(); await tick();
    const pop = document.getElementById(btn.getAttribute("aria-controls")), items = $$("[role=menuitemradio]", pop), r = pop.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    ok(items.length === Theme.LIST.length && items.filter((x) => x.getAttribute("aria-checked") === "true").length === 1 && pop.contains(hit) && r.right <= innerWidth && btn.getAttribute("aria-expanded") === "true",
      `gear: opens ${items.length} themes, the current one checked, inside the window and on top`, `gear: ${items.length} radio items, ${items.filter((x) => x.getAttribute("aria-checked") === "true").length} checked`);
    items.find((x) => x.textContent.includes(other.label)).click(); await tick();
    ok(Theme.id === other.id && document.documentElement.dataset.theme === other.id, `gear: choosing ${other.label} changes the theme`, `gear: theme ${Theme.id}`);
    Theme.set(was);
  }

  /* Finding 11: flow names in the menu lose the words they share, and the text-first pages sit under one folded Read. */
  async function sideNames(ok) {
    Nav.st.expanded.add("flows"); Nav.st.expanded.delete("read"); Nav.home(); Nav.refresh(); await tick();
    const kids = $$("#side .side-kid[data-section=flows]"), full = kids.map((k) => k.title), shown = kids.map((k) => k.querySelector(".side-label").textContent);
    const lead = (t) => t.split(" ").slice(0, 2).join(" "), tally = {};
    for (const t of full) tally[lead(t)] = (tally[lead(t)] || 0) + 1;
    const [word, n] = Object.entries(tally).sort((x, y) => y[1] - x[1])[0] || ["", 0], shared = kids.length >= 3 && n >= 3 && n * 2 > kids.length;
    const right = shown.every((t, i) => full[i].endsWith(t)) && (shared ? shown.filter((t, i) => t.length < full[i].length).length === n && shown.every((t) => !t.startsWith(word)) : shown.every((t, i) => t === full[i]));
    ok(right, `menu: ${kids.length} flow names ${shared ? `lose the "${word}" most of them start with` : "start differently, so none is cut"} (${shown.slice(0, 2).join(" | ")}), and the hover keeps the whole name`, `menu: flow names ${shown.join(" | ")}`);
    const read = $("#side .side-link[data-group=read]"), box = $("#side-read"), members = $$("#side-read .side-link").map((b) => b.dataset.section);
    ok(!!read && box.hidden && read.parentElement.querySelector("[aria-expanded]").getAttribute("aria-expanded") === "false" && ["constraints", "strategy", "glossary"].every((id) => members.includes(id)) && !$$("#side > .side-group:last-of-type > .side-row .side-link").some((b) => ["constraints", "strategy", "glossary"].includes(b.dataset.section)),
      "menu: Constraints, Context, Strategy and Glossary sit under one Read heading, folded", `menu: read group ${!!read}, folded ${box && box.hidden}, members ${members}`);
    read.click(); await tick();
    ok(!$("#side-read").hidden, "menu: Read opens to its pages", "menu: Read did not open");
    $("#side .side-link[data-group=read]").click(); await tick();
    Nav.open("glossary"); await tick();
    ok(!$("#side-read").hidden && $("#side .side-link[data-section=glossary]").getAttribute("aria-current") === "page", "menu: Read stays open on one of its pages, with that page marked", "menu: Read closed on its own page");
    Nav.st.expanded.delete("read"); Nav.home(); await tick();
  }

  /* Finding 12: a few slices open without search and filter rows, the Key is a ? in the bar, and "Comes after" says
     "the first slice" with the name on hover. */
  async function slicesQuiet(ok) {
    const L = Slices.LIST;
    if (!L.length) { out_skip(ok, "slices quiet: this vault has no slices"); return; }
    Slices.st.filters = false; Slices.clear(); Nav.open("slices"); await tick();
    const few = L.length < Slices.FILTERS_FROM, after = $$("#main .sl-afterchip");
    const withAfter = L.filter((x) => x.after.length).length;
    ok((few ? !$(".sl-find") && !$(".sl-fgroup") : !!$(".sl-find")) && !$("#main .sl-results .legend") && !!$("#main [aria-controls^='dmenu-key']"),
      `slices: ${L.length} slices ${few ? "open with no search or filter rows" : "show their filters"}, and the key is a ? in the bar, not a block under the rows`, `slices: find ${!!$(".sl-find")}, filters ${!!$(".sl-fgroup")}, key block ${!!$("#main .sl-results .legend")}, ? button ${!!$("#main [aria-controls^='dmenu-key']")}`);
    const named = after.every((c) => /^(the \w+ slice|slice \d+)$/.test(c.textContent) && c.title.length > c.textContent.length);
    ok(after.length >= withAfter && named, `slices: Comes after says "${after[0] ? after[0].textContent : ""}", never a whole title, with the name on hover (${after.length} chips)`, `slices: chips ${after.map((c) => c.textContent).join(" | ")}`);
    const key = $("#main [aria-controls^='dmenu-key']"); key.click(); await tick();
    const pop = document.getElementById(key.getAttribute("aria-controls"));
    ok(!pop.hidden && $$(".lg-items li", pop).length > 0, "slices: the ? opens the key, one line for each look on the page", "slices: the ? opened an empty key");
    Menus.close(); Nav.home(); await tick();
  }
  const out_skip = (ok, text) => ok(true, text);

  /* Finding 15: the overview map is in the panel only where the map is the subject. Finding 16: names say what you will see. */
  async function overviewAndNames(ok) {
    const bad = [];
    for (const [name, show] of [["Home", () => Nav.home()], ...D.sections.map((x) => [x.label, () => Nav.open(x.id)])]) {
      show(); await tick();
      const id = App.section, want = ["home", "apps", "capabilities", "flows"].includes(id), mini = $("#panel-mini"), shown = !mini.hidden && mini.offsetParent !== null && (!D.nodes.length || !!$("svg", mini));
      if (shown !== want) bad.push(`${name}: overview ${shown ? "shown" : "missing"}`);
    }
    if (D.map.apps.length) { Inside.open(D.map.apps[0].key, "containers"); await tick(); if ($("#panel-mini").hidden) bad.push("Inside: overview missing"); }
    Nav.open("goals"); await tick();
    const body = $("#panel-body").getBoundingClientRect(), panel = $("#panel").getBoundingClientRect();
    ok(!bad.length && body.bottom >= panel.bottom - 2, "overview map: shown on Home, Apps, Capabilities, Flows and inside an app, and nowhere else, so the panel text gets the full height", `overview map: ${bad.join(" | ")}; body ends ${Math.round(body.bottom)} of ${Math.round(panel.bottom)}`);
    Nav.open("apps"); MapView.st.lens = null; rerender(); await tick();
    const view = $("#main [data-dmenu=view] .dmenu-btn"); view.click(); await tick();
    const labels = $$("#main [data-dmenu=view] [role^=menuitem]").map((x) => x.textContent).join(" | ");
    Menus.close();
    const old = ["Flow lines", "Who uses whom", "Animate flows", "Clipped corners", "Wide card", " 1 of 2", "tracer 1"];
    const text = [$("#main"), $("#panel"), $("#side")].map((e) => e.textContent).join(" ") + labels;
    ok(/Contracts only/.test(labels) && /Dependencies/.test(labels) && /Moving markers/.test(labels) && !old.some((w) => text.includes(w)), "labels: the View menu says Contracts only, Dependencies and Moving markers, and none of the old names is on the page", `labels: menu ${labels}; old names left: ${old.filter((w) => text.includes(w)).join(", ")}`);
    MapView.st.lens = null; Nav.home(); await tick();
    const tag = D.flows.map((f) => f.key).find((k) => typeof Releases !== "undefined" && Releases.tracerPlace(k));
    if (tag) {
      Nav.open("flows", tag); Flows.select(tag, -1); await tick();
      const place = $(".flows-head .tracer-place, .dia-bar .tracer-place");
      ok(!!place && /^first slice\s+flow \d+ of \d+$/.test(place.textContent.trim()), `labels: a flow in the first slice says so ("${place ? place.textContent.trim() : ""}"), not tracer and a bare 1 of 2`, `labels: flow tag "${place && place.textContent}"`);
    } else ok(true, "labels: this vault records no first slice, so no flow carries its tag");
    Nav.home(); await tick();
  }

  /* The wording: the page does not know who is reading, so it says "waiting", one number, and each item says who it is waiting
     on. "Waiting on you" is a filter that exists only when the build knew the reader's handle or the reader picked a role door. */
  async function waitingOnYou(ok) {
    const was = { me: D.me, chosen: Roles.st.chosen, role: Roles.st.role }, bare = !was.me.handle && !was.chosen;
    const rows = () => $$(".q-card .q-row");
    const open = () => { Nav.home(); return tick(); };
    D.me = { handle: "" }; Roles.st.chosen = false; await open();
    const none = !$(".q-mine") && !Queue.me();
    const text = [$("#main"), $("#panel"), $("#masters"), $("#side")].map((e) => e.textContent).join(" ");
    ok(none && !/\bneeds? you\b|waiting on you|\byou\b/i.test(text.replace(/Search by name[^/]*/, "")), "waiting: with no handle and no role door there is no Waiting on you filter, and nothing on Home says you", `waiting: filter ${!!$(".q-mine")}, text says ${(text.match(/.{20}\byou\b.{20}/i) || [""])[0]}`);
    const asked = Queue.items().map((x) => ASK[x.id].ask.key).find((k) => String(k).startsWith("@"));
    if (asked) {
      D.me = { handle: asked.slice(1) }; await open();
      const all = rows().length, chip = $(".q-mine");
      const want = Queue.items().filter((x) => [ASK[x.id].ask.key, ASK[x.id].ask.owner].some((k) => String(k).toLowerCase() === asked.toLowerCase())).length;
      chip.click(); await tick();
      const mineRows = rows().length;
      ok(!!chip && chip.dataset.me === "handle" && want > 0 && mineRows === Math.min(want, Queue.TOP) && mineRows <= all && $(".q-mine").getAttribute("aria-pressed") === "true",
        `waiting: with the handle ${asked}, Waiting on you shows the ${want} questions that name ${asked} as the owner or the one asked`, `waiting: handle ${asked}, rows ${mineRows} of ${all}, wanted ${want}`);
    }
    D.me = { handle: "" }; Roles.st.chosen = true; Roles.st.role = "product"; await open();
    ok(!!$(".q-mine") && $(".q-mine").dataset.me === "role", "waiting: a reader who picked the Product door gets Waiting on you for that role", "waiting: no filter after picking a role door");
    D.me = was.me; Roles.st.chosen = was.chosen; Roles.st.role = was.role; Queue.st.mine = false; await open();
  }

  /* A menu opened from a diagram bar or a page head is the topmost thing at its middle and its two ends, in every section
     and every map view, so no view's own layers (the matrix's frozen corner, a canvas) are ever drawn over it. */
  const GRID = [0.06, 0.3, 0.5, 0.7, 0.94].flatMap((x) => [0.06, 0.3, 0.5, 0.7, 0.94].map((y) => [x, y]));  // a corner of the frozen head sits over one part of a menu, not its middle
  async function menusOnTop(ok) {
    const trials = [["Home", () => Nav.home()], ...D.sections.map((x) => [x.label, () => Nav.open(x.id)]),
      ["Dependencies", () => { Nav.open("apps"); MapView.st.lens = "matrix"; rerender(); }], ["Contracts only", () => { Nav.open("apps"); MapView.st.lens = "transit"; rerender(); }],
      ["Before and after", () => { Nav.open("apps"); MapView.st.lens = "releases"; rerender(); }]];
    const was = { lens: MapView.st.lens, theme: Theme.id }, bad = [];
    for (const el of [document.scrollingElement, document.body, $("#main")]) if (el) { el.scrollTop = 0; el.scrollLeft = 0; }  // earlier checks scroll things into view
    let menus = 0;
    for (const theme of [was.theme, ...Theme.LIST.map((t) => t.id).filter((t) => t !== was.theme)]) {
      Theme.set(theme);
      for (const [name, show] of trials) {
        if (theme !== was.theme && name !== "Dependencies" && name !== "Epics") continue;  // the other themes are checked where the layers are heaviest
        show(); await tick();
        for (const btn of $$("#main [aria-haspopup]:not([disabled]):not([aria-disabled='true'])")) {
          if (btn.offsetParent === null) continue;  // a control a narrow bar folds away is not on the page
          btn.click(); await tick();
          const pop = document.getElementById(btn.getAttribute("aria-controls"));
          if (!pop || pop.hidden) continue;  // a button that is not a menu right now (a focus control with nothing picked)
          menus++;
          const r = pop.getBoundingClientRect();
          for (const [fx, fy] of GRID) {
            const x = r.left + r.width * fx, y = r.top + r.height * fy;
            if (y > innerHeight || x > innerWidth) continue;  // the part below the window is reported once, below
            const el = document.elementFromPoint(x, y);
            if (!el || !pop.contains(el)) bad.push(`${name}, ${theme}, "${btn.title}": covered by ${el ? el.tagName + "." + el.className : "nothing"} at ${fx},${fy} (menu ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}x${Math.round(r.height)})`);
          }
          if (r.right > innerWidth + 1 || r.left < -1 || r.bottom > innerHeight + 1) bad.push(`${name}, "${btn.title}": runs off the window (${Math.round(r.top)} to ${Math.round(r.bottom)} of ${innerHeight} high, page scrolled ${scrollY})`);
          Menus.close();
          if (btn.getAttribute("aria-expanded") === "true") btn.click();  // the flow picker keeps its own list open
        }
      }
    }
    Theme.set(was.theme); MapView.st.lens = was.lens; Nav.home(); await tick();
    ok(!bad.length && menus > 10, `menus on top: ${menus} open menus across every section, map view and theme are the topmost thing at 25 points across them`, `menus on top: ${bad.slice(0, 6).join(" | ")} (${menus} menus)`);
  }

  SelfTest.run = async () => {
    const only = HASH.get("only") === "qol";
    const report = only ? ["head"] : await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { if (!wide()) await compact(ok); else { await appPanel(ok); await searchRows(ok); await oneNumber(ok); await onceEach(ok); await gear(ok); await sideNames(ok); await slicesQuiet(ok); await overviewAndNames(ok); await waitingOnYou(ok); } await menusOnTop(ok); } catch (e) { lines.push("FAIL the quality-of-life checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the quality-of-life checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
