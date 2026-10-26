/* ------------------------------------------------------------ The Details panel on Flows, the Apps map, Who to ask and Decisions
   (detailspanel.js, PlanDetails). The same behavior as inside an app, driven as a person would: pick a thing and only that
   shows; follow a link and the trail reads back; Escape or empty space returns to the page's summary; the first click shows,
   Open jumps; a waiting question lights what it holds up. And one check that is about the panel's scroll: a jump inside the
   side panel moves the panel and nothing else. A block of its own after SelfTest, so it merges apart from the checks above. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const click = (el) => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  const esc = () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  const head = () => { const h2 = $("#panel-body .p-head h2"); return h2 ? h2.textContent.trim() : ""; };
  const kind = () => { const k = $("#panel-body .p-head .kind"); return k ? k.textContent.trim() : ""; };
  const trail = () => { const t = $("#panel-body .dp-trail"); return t ? t.textContent.replace(/\s+/g, " ").trim() : ""; };
  const sections = () => $$("#panel-body .p-sec h3").map((x) => x.textContent.replace(/\s+\d+$/, "").trim());
  const link = (name) => $$("#panel-body .dp-link").find((b) => b.textContent.trim() === name);
  const CODE = /\b(?:CON|CAP|EPC|UNK|CST|PTY|FLO|SV)-\d{2,3}\b|\bOQ-\d{3}\b|\bADR-\d{4}\b/;
  const tabs = () => $$("#panel-body .dp-tabs [role=tab]").map((b) => b.textContent.replace(/\s+/g, " ").trim());  // none: the Details panel is one list now

  async function flows(ok) {
    const flow = D.flows.find((f) => f.steps.length > 1 && f.steps.some((s) => s.contracts.length)) || D.flows[0];
    if (!flow) return;
    const title = E[flow.key].title;
    Flows.select(flow.key, -1); await tick();
    ok(App.view === "flows" && head() === title && !tabs().length && !$("#panel-body ol") && !$("#panel-body .steps-list"),
      `details panel (flows): nothing picked shows the flow's own summary, not its step list, with no tabs`, `details panel (flows): summary shows "${head()}", tabs ${tabs().join(" | ")}`);
    const si = flow.steps.findIndex((s) => s.contracts.length), stp = flow.steps[si];
    Flows.player().go(si); await tick();
    click($("[data-step-details]")); await tick();
    ok(kind() === `Step ${stp.n} of ${flow.steps.length}` && head() === stp.short && sections().includes("Who sends") && sections().some((s) => /^The contracts? it uses$/.test(s)) && sections().includes("If it goes wrong") && sections().includes("What's waiting on it"),
      `details panel (flows): picking step ${stp.n} shows who sends, the contract and every way it answers, the error branch and what waits on it`, `details panel (flows): step shows "${kind()}" / "${head()}" with ${sections().join(", ")}`);
    const con = stp.contracts[0], conTitle = CONTRACT[con].title;
    click(link(conTitle)); await tick();
    ok(head() === conTitle && kind() === "Contract" && sections().includes("Ways it can answer") && /›.*›/.test(trail()) && !!$("#panel-body .dp-open"),
      `details panel (flows): the contract link opens ${conTitle} with ways it can answer, the trail "${trail()}" and an Open button`, `details panel (flows): contract link gave "${head()}", trail "${trail()}"`);
    const ways = (D.contractAnswers || {})[con] || [];
    ok(ways.length ? $$("#panel-body .dp-ways li").length === ways.length && $$("#panel-body .dp-ways li.err").length === ways.filter((w) => w.error).length : /Not recorded/.test($("#panel-body").textContent),
      ways.length ? `details panel (flows): all ${ways.length} ways ${conTitle} can answer are listed, the errors marked` : `details panel (flows): a contract with no case table says Not recorded`, "details panel (flows): the ways a contract answers are wrong");
    click($("#panel-body .dp-back")); await tick();
    ok(head() === stp.short, "details panel (flows): ← back returns to the step", `details panel (flows): back left "${head()}"`);
    click($("#panel-body .dp-trail .linkish")); await tick();
    ok(head() === title, "details panel (flows): the crumb that names the flow returns to its summary", `details panel (flows): crumb left "${head()}"`);
    const node = $(`.flow-nodes [data-opens="${con}"]`);
    click(node); await tick();
    ok(head() === conTitle, "details panel (flows): a contract in the list under the diagram shows its details first", `details panel (flows): list gave "${head()}"`);
    const open = $("#panel-body .dp-open"), was = App.view;
    ok(App.view === was && !!open, "details panel (flows): the first click only shows; Open is the second click", "details panel (flows): no Open button on the contract");
    esc(); await tick();
    ok(head() === title && !$("#panel-body .dp-trail"), "details panel (flows): Escape returns to the flow's summary", `details panel (flows): Escape left "${head()}"`);
    // a second click on what is picked puts it down: a contract in the list, a step and a lane on the stage
    click(node); await tick(); const once = head(); click(node); await tick();
    const hitClick = (t) => { const c = $(".stage-canvas"), r = c.getBoundingClientRect(); c.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: r.left + t.x + t.w / 2, clientY: r.top + t.y + t.h / 2 })); };
    const stepHit = () => Flows.player().hits.find((t) => t.si === si), laneHit = () => Flows.player().hits.find((t) => t.type === "lane");
    const drawn = () => { const p = Flows.player(); if (p && p.canvas.isConnected) p.draw(performance.now()); };  // requestAnimationFrame does not run in a headless page
    const twice = async (find) => { drawn(); const t = find(); if (!t) return ["", ""]; hitClick(t); await tick(); const a = head(); drawn(); hitClick(find()); await tick(); return [a, head()]; };
    const [stepOnce, stepTwice] = await twice(stepHit), [laneOnce, laneTwice] = await twice(laneHit);
    ok(once === conTitle && head() === title && stepOnce && stepOnce !== title && stepTwice === title && laneOnce && laneOnce !== title && laneTwice === title,
      "details panel (flows): a second click on the picked contract, step or lane returns to the flow's summary", `details panel (flows): second clicks left contract "${once}", step "${stepOnce}" then "${stepTwice}", lane "${laneOnce}" then "${laneTwice}"`);
    // an open question lights the steps and lanes it holds up
    const held = D.flows.flatMap((f) => f.steps.flatMap((s) => s.unknowns.filter((u) => ASK[u.id] && isOpen(ASK[u.id])).map((u) => ({ flow: f.key, id: u.id }))))[0];
    if (held) {
      Flows.select(held.flow, -1); await tick();
      DetailsPanel.show(held.id, { reset: true }); await tick();
      const lit = $$("#scrub .tick.held").length;
      ok(head() === titleOf(held.id) && lit >= 1, `details panel (flows): the open question "${shorten(titleOf(held.id), 40)}" shows its question and marks ${lit} step${lit === 1 ? "" : "s"} it holds up`, `details panel (flows): question opened "${head()}", ${lit} marked`);
    }
    esc(); await tick();
    const said = () => { const c = $("#panel-body").cloneNode(true); c.querySelectorAll(".dp-about").forEach((x) => x.remove()); return c.textContent; };  // the section's page is read as written
    ok(!CODE.test(said()), "details panel (flows): say names, never codes", `details panel (flows): a code shows: ${((said().match(/.{0,50}(?:CON|CAP|EPC|UNK|CST|PTY|FLO|SV)-\d{2,3}.{0,30}/) || [])[0])}`);
  }

  async function map(ok) {
    if (!D.map.apps.length || !Object.keys(CONTRACT).length) return;  // an empty plan has no map to pick from
    Nav.open("apps"); MapView.st.lens = "cockpit"; MapView.st.group = "none"; MapView.st.focus = null; showView("map"); await tick();
    go("lights", { reset: true }); await tick();
    ok(head() === "Needs you" && !tabs().length, `details panel (map): nothing picked shows the page summary (Needs you), with no tabs`, `details panel (map): summary shows "${head()}"`);
    const byName = (name) => $$("#board [data-node]").find((el) => el.dataset.node === name);
    const con = Object.values(CONTRACT).find((c) => byName(c.title)) || Object.values(CONTRACT)[0], conTitle = con.title;
    const pickCon = async () => { if (byName(conTitle)) click(byName(conTitle)); else go(con.id, { reset: true }); await tick(); };  // a line's label, or its key when the map draws it inside a bundle
    await pickCon();
    ok(kind() === "Contract" && sections().includes("Who provides it, who calls it") && sections().includes("Ways it can answer") && sections().includes("What's waiting on it"),
      `details panel (map): a contract label opens its own details: ${sections().join(", ")}`, `details panel (map): contract label gave "${kind()}" / "${head()}" with ${sections().join(", ")}`);
    const ext = D.map.externals[0];
    if (ext) {
      if (byName(ext.title)) click(byName(ext.title)); else go(ext.key, { reset: true });
      await tick();
      ok(kind() === "Outside service" && head() === ext.title && sections().includes("Contracts it provides"), `details panel (map): the outside service ${ext.title} has full details`, `details panel (map): outside service gave "${kind()}" / "${head()}"`);
    }
    const app = D.map.apps[0].key;
    click(byName(titleOf(app))); await tick();
    const where = $$("#panel-body .p-sec h3").map((x) => x.textContent.trim());
    ok(App.view === "map" && where[0].startsWith("In these flows") && where[1].startsWith("Talks to") && !!$("#panel-body .dp-open"),
      "details panel (map): an app keeps In these flows and Talks to at the top, with an Open button, and the first click stays on the map", `details panel (map): app sections ${where.slice(0, 3).join(" | ")}, view ${App.view}`);
    click($("#panel-body .dp-open")); await tick();
    ok(App.view === "inside", "details panel (map): Open goes inside the app", `details panel (map): Open went to ${App.view}`);
    Nav.open("apps"); showView("map"); await tick(); go("lights", { reset: true }); await tick();
    await pickCon(); esc(); await tick();
    ok(head() === "Needs you" && !$("#panel-body .dp-trail"), "details panel (map): Escape returns to the summary", `details panel (map): Escape left "${head()}"`);
    await pickCon(); click($("#board")); await tick();
    ok(head() === "Needs you", "details panel (map): a click on empty space returns to the summary", `details panel (map): empty space left "${head()}"`);
    const box = () => byName(titleOf(app));
    click(box()); await tick(); const appOnce = head(); click(box()); await tick();
    const conBox = () => $$("#board [data-opens]").find((el) => CONTRACT[el.dataset.opens]), conKey = conBox() ? conBox().dataset.opens : "";
    let traced = false, wasTraced = false, conOnce = "";
    if (conKey) { click(conBox()); await tick(); conOnce = head(); wasTraced = !!Motion.active; click(conBox()); await tick(); traced = !!Motion.active || !!$("#motion-legend"); }
    const fl = D.flows[0] ? D.flows[0].key : "";  // a flow picked on the map is traced; picked again, the trace goes with it
    let flowTraced = false, flowAfter = false;
    if (fl) { DetailsPanel.toggle(fl, { reset: true }); await tick(); flowTraced = !!Motion.active && !!$("#motion-legend"); DetailsPanel.toggle(fl, { reset: true }); await tick(); flowAfter = !!Motion.active || !!$("#motion-legend"); }
    ok(appOnce.endsWith(titleOf(app)) && head() === "Needs you" && (!conKey || (conOnce === CONTRACT[conKey].title && wasTraced && !traced)) && (!fl || (flowTraced && !flowAfter && head() === "Needs you")),
      `details panel (map): a second click on the picked box returns to the summary${conKey ? ` and takes the trace of ${CONTRACT[conKey].title} away` : ""}${fl ? `; a flow picked again takes its trace away` : ""}`, `details panel (map): second clicks left app "${appOnce}", contract "${conOnce}", "${head()}", traced ${wasTraced} then ${traced}, flow traced ${flowTraced} then ${flowAfter}`);
    const q = Object.keys(UNKNOWN).find((id) => isOpen(UNKNOWN[id]) && PlanDetails.held(id).apps.size && Queue.items().some((x) => x.id === id && PlanDetails.NEEDS.includes(x.level)));
    if (q) {
      DetailsPanel.show(q, { reset: true }); await tick();
      const lit = $$("#board g.picked, #board g.hit.picked, #board g.station.picked").length;
      ok(head() === titleOf(q) && kind() === "Open question" && lit >= 1 && sections().includes("It holds up"), `details panel (map): the open question "${shorten(titleOf(q), 40)}" shows its question and lights ${lit} boxes it holds up`, `details panel (map): question gave "${head()}", ${lit} lit`);
      esc(); await tick();
    }
  }

  async function asks(ok) {
    if (!D.asks.some((u) => isOpen(u))) return;
    showView("asks"); go("lights", { reset: true }); DetailsPanel.clear(); await tick();
    const open = D.asks.filter((u) => isOpen(u)).length;
    ok(/open question/.test(head()) && !$("#panel-body ol") && !tabs().length, `details panel (asks): nothing picked says "${head()}", with the people to ask`, `details panel (asks): summary shows "${head()}"`);
    const bay = $(".bay-name");
    click(bay); await tick();
    const rows = $$("#panel-body .wq").length;
    ok(kind() === "Who to ask" && head() === bay.textContent.trim() && rows >= 1, `details panel (asks): a person shows their ${rows} open question${rows === 1 ? "" : "s"}, each opening its details`, `details panel (asks): person gave "${kind()}" / "${head()}", ${rows} rows`);
    const first = $("#panel-body .wq");
    click(first); await tick();
    ok(kind() === "Open question" && sections().includes("It holds up") && /›.*›/.test(trail()) === false && !$("#panel-body .dp-open"), "details panel (asks): picking a question shows it, with no Open since this is Who to ask", `details panel (asks): question gave "${kind()}", trail "${trail()}"`);
    click($("#panel-body .dp-trail .dp-trail ~ *") || $("#panel-body .dp-back")); await tick();
    ok(DetailsPanel.tab === "details" && head() === bay.textContent.trim() || head() !== "", "details panel (asks): ← back returns toward the person", `details panel (asks): back left "${head()}"`);
    esc(); await tick();
    ok(/open question/.test(head()), "details panel (asks): Escape returns to the summary", `details panel (asks): Escape left "${head()}"`);
    const strip = $(".strip:not(.resolved)");
    if (strip) { click($(".bay .rails")); await tick(); ok(/open question/.test(head()), "details panel (asks): empty space returns to the summary", `details panel (asks): empty space left "${head()}"`); }
  }

  async function decisions(ok) {
    const e = Decisions.entries.find((x) => x.affects.some((a) => ent(a.key) && a.key !== x.key && PlanDetails.openFor(a.key, "decisions"))) || Decisions.entries[0];
    if (!e) return;
    showView("decisions"); DetailsPanel.clear(); await tick();
    ok(head() === `${Decisions.visible().length ? D.garden.trees.length + D.garden.bare.length : 0} decisions`.replace(/^1 decisions/, "1 decision") || /decision/.test(head()), `details panel (decisions): nothing picked shows "${head()}"`, `details panel (decisions): summary shows "${head()}"`);
    Decisions.st.bare = true; Decisions.select(e.id); await tick();
    ok(kind() === "Decision" && head() === e.name && sections().includes("What it affects") && sections().includes("What it still waits on"), `details panel (decisions): picking ${shorten(e.name, 40)} shows what it affects and waits on`, `details panel (decisions): "${kind()}" / "${head()}" with ${sections().join(", ")}`);
    const affected = e.affects.filter((a) => ent(a.key) && a.key !== e.key), withOpen = $$("#panel-body .dp-open-row").length;
    ok(!affected.length || $$("#panel-body .dp-link").length >= affected.length, `details panel (decisions): the ${affected.length} thing${affected.length === 1 ? "" : "s"} it affects each link, ${withOpen} with an Open`, `details panel (decisions): ${$$("#panel-body .dp-link").length} links for ${affected.length} affected`);
    const target = affected[0];
    if (target) {
      click(link(target.label) || $$("#panel-body .dp-link")[0]); await tick();
      ok(/›.*›/.test(trail()) || trail().split("›").length >= 3, `details panel (decisions): following a link stacks the trail "${trail()}"`, `details panel (decisions): trail "${trail()}"`);
      click($("#panel-body .dp-back")); await tick();
      ok(head() === e.name, "details panel (decisions): ← back returns to the decision", `details panel (decisions): back left "${head()}"`);
      const row = $$("#panel-body .dp-open-row")[0];
      if (row) { const view = App.view; click(row); await tick(); ok(App.view !== view, `details panel (decisions): Open jumps to ${App.view}`, "details panel (decisions): Open stayed on the log"); showView("decisions"); Decisions.select(e.id); await tick(); }
    }
    esc(); await tick();
    ok(!$("#panel-body .dp-trail") && !$(".dl-stage.has-open"), "details panel (decisions): Escape returns to the summary and closes the record", `details panel (decisions): Escape left "${head()}", record open ${!!$(".dl-stage.has-open")}`);
  }

  /* A jump inside the side panel moves the panel and nothing else (a scrollIntoView moved the whole page up). */
  async function panelJump(ok) {
    const bad = [];
    let tried = 0;
    for (const sec of D.sections) {
      Nav.open(sec.id); await tick();
      const toc = $$("#panel .r-toc-link");
      if (toc.length < 3) continue;
      const main = $("#main"), before = { y: window.scrollY, doc: document.scrollingElement.scrollTop, main: main.scrollTop };
      click(toc[toc.length - 1]); await new Promise((r) => setTimeout(r, 700));
      tried++;
      if (window.scrollY !== before.y || document.scrollingElement.scrollTop !== before.doc || main.scrollTop !== before.main) bad.push(`${sec.label}: window ${before.y}→${window.scrollY}, main ${before.main}→${main.scrollTop}`);
    }
    ok(tried > 0 ? !bad.length : true, `panel jump: ${tried} contents jumps inside the side panel left the window and the main column where they were`, `panel jump: ${bad.join("; ")}`);
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    for (const check of [flows, map, asks, decisions, panelJump]) {
      try { await check(ok); } catch (e) { lines.push(`FAIL the details panel check ${check.name} threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the details panel checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };

  /* #scene=<name> in a build made with --selftest: the page set up as a person's clicks would, for a screenshot.
     flow-step, flow-contract, map-contract, map-waiting, asks-person, asks-question, decision. */
  addEventListener("load", () => {
    const scene = HASH.get("scene");
    if (!scene || !/^(flow|map|asks|decision)/.test(scene)) return;
    setTimeout(() => {
      if (scene.startsWith("flow")) {
        const flow = D.flows.find((f) => f.steps.some((s) => s.contracts.length)) || D.flows[0], si = flow.steps.findIndex((s) => s.contracts.length);
        Flows.select(flow.key, -1);
        DetailsPanel.show(PlanDetails.stepKey(flow.key, si), { reset: true });
        if (scene === "flow-contract") DetailsPanel.show(flow.steps[si].contracts[0]);
      } else if (scene.startsWith("map")) {
        Nav.open("apps"); MapView.st.lens = "cockpit"; MapView.st.group = "none"; showView("map");
        if (scene === "map-contract") DetailsPanel.show(Object.values(CONTRACT)[0].id, { reset: true });
        else {
          const q = Object.keys(UNKNOWN).find((id) => isOpen(UNKNOWN[id]) && PlanDetails.held(id).apps.size && Queue.items().some((x) => x.id === id));
          if (q) DetailsPanel.show(q, { reset: true });
        }
      } else if (scene.startsWith("asks")) {
        showView("asks");
        const bay = $(".bay-name");
        if (scene === "asks-person" && bay) click(bay);
        else { const u = D.asks.find((x) => isOpen(x)); if (u) DetailsPanel.show(u.id, { reset: true }); }
      } else {
        const e = Decisions.entries.find((x) => x.affects.length) || Decisions.entries[0];
        Decisions.st.bare = true; showView("decisions"); Decisions.select(e.id);
      }
      if (isCompact()) PanelSize.hide(false);
      document.body.setAttribute("data-scene", scene);
    }, 400);
  });
})();
