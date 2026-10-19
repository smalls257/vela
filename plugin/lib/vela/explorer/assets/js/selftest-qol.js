/* ------------------------------------------------------------ Quality-of-life checks (the dashboard audit, batch 2)
   Each group checks one change the way a reader meets it. A page opened narrow (under COMPACT_BELOW) runs the
   "compact" group; a wide one runs the rest. `#only=qol` skips every other check so the narrow run is quick, since
   the older checks were written for a wide window. */
(() => {
  const base = SelfTest.run, tick = () => Promise.resolve();
  const wide = () => innerWidth >= COMPACT_BELOW;
  const rect = (sel) => { const el = typeof sel === "string" ? $(sel) : sel; return el ? el.getBoundingClientRect() : { left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0 }; };
  const shown = (sel) => { const el = $(sel); return !!el && el.offsetParent !== null || (!!el && getComputedStyle(el).position === "fixed" && getComputedStyle(el).display !== "none"); };

  /* A narrow window: the diagram has the whole width, the panel and the menu are slide-overs that open on a pick and
     close on Esc, and nothing scrolls sideways. */
  async function compact(ok) {
    const saved0 = Settings.read("explorer.panel.hidden"); Nav.home(); await tick();
    const side = rect("#side"), panel = rect("#panel"), main = rect("#main");
    ok(document.body.classList.contains("compact") && !shown("#side") && !shown("#panel") && main.width >= innerWidth - 1,
      `compact, ${innerWidth} px: the menu and the panel start closed and the diagram has the whole ${Math.round(main.width)} px`, `compact: menu shown ${shown("#side")}, panel shown ${shown("#panel")}, main ${Math.round(main.width)} of ${innerWidth}`);
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
      ok(shown("#panel") && getComputedStyle($("#panel")).position === "fixed" && rect("#panel").right <= innerWidth + 1 && $("#panel .p-head h2").textContent.includes(titleOf(key.key)),
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
      const links = $("#panel .p-links"), why = $$("#panel .p-sec").find((x) => /Why it needs you/.test($("h3", x).textContent));
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
      ok(App.view === "flows" && Flows.st.key === want && $("#panel .p-head h2").textContent.includes(titleOf(want)), `app panel: the flow chip plays ${titleOf(want)} in one click`, `app panel: the flow chip left view ${App.view}, flow ${Flows.st.key}`);
    }
    const withContract = apps.find((k) => D.apps[k].provides.length || D.apps[k].consumes.length);
    if (withContract) {
      Nav.open("apps"); go(withContract, { reset: true }); await tick();
      const chip = $("#panel [data-contract]"), want = chip.dataset.contract;
      chip.click(); await tick();
      ok($("#panel .p-head h2").textContent.includes(titleOf(want)) && App.focus === want, `app panel: the contract chip opens ${titleOf(want)}`, `app panel: the contract chip opened ${$("#panel .p-head h2").textContent}`);
    }
  }

  SelfTest.run = async () => {
    const only = HASH.get("only") === "qol";
    const report = only ? ["head"] : await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { if (!wide()) await compact(ok); else await appPanel(ok); } catch (e) { lines.push("FAIL the quality-of-life checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the quality-of-life checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
