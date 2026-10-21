/* ------------------------------------------------------------ Capability focus (capfocus.js)
   Pick a capability and the map and the sidebar keep only what it touches; the rest is removed, not dimmed. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const drawnNodes = () => $$("#board svg.cockpit g.hit[data-key]").map((g) => g.dataset.key).filter((k) => NODE[k]);
  const drawnFlows = () => $$("#board svg.cockpit g.hit[data-key]").map((g) => g.dataset.key).filter((k) => FLOW[k]);
  const same = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

  async function focusing(ok, out) {
    const caps = D.trace.capabilities.map((c) => c.key);
    if (!caps.length || !D.nodes.length) { out.push("skip capability focus: this vault has no capabilities or no apps"); return; }
    let narrower = 0, empties = 0;
    for (const cap of caps) {
      const title = ent(cap).title;
      Nav.open("capabilities", cap); await tick();
      const s = CapFocus.scope(), bar = $('#main .capfocus-bar[data-where="map"]'), side = $('#side .capfocus-bar');
      ok(!!s && CapFocus.key() === cap && !!bar && bar.textContent.includes(`Showing ${title} only`) && bar.textContent.includes("Show everything") && !!side,
        `capability focus, ${title}: the map and the sidebar both say it is the only one showing, with a way back`, `capability focus, ${title}: bar ${!!bar}, side ${!!side}, key ${CapFocus.key()}`);
      if (s.empty) {
        empties++;
        ok(!!$("#board .empty-state") && !$("#board svg.cockpit"), `capability focus, ${title}: it touches nothing yet, and the view says so instead of drawing an empty map`, `capability focus, ${title}: empty scope, board shows ${$("#board").textContent.slice(0, 80)}`);
      } else {
        const nodes = drawnNodes(), flows = drawnFlows();
        ok(same(nodes, [...s.nodes]) && same(flows, [...s.flows]), `capability focus, ${title}: the map draws only its ${s.nodes.size} boxes and ${s.flows.size} flows`, `capability focus, ${title}: drawn ${nodes.join(",")} / ${flows.join(",")}, wanted ${[...s.nodes].join(",")} / ${[...s.flows].join(",")}`);
        const lamps = $$("#board svg.cockpit [data-contract]").map((e) => e.dataset.contract).filter((c, i, a) => a.indexOf(c) === i);
        ok(lamps.every((c) => s.contracts.has(c)), `capability focus, ${title}: no contract it doesn't touch is on the map`, `capability focus, ${title}: stray contracts ${lamps.filter((c) => !s.contracts.has(c)).join(",")}`);
        if (s.nodes.size < D.nodes.length) narrower++;
        const vb = $("#board svg.cockpit").getAttribute("viewBox");
        ok(Pan.view("cockpit").z === 1 && !!vb, `capability focus, ${title}: the drawing is fitted to what is left (zoom back at 1)`, `capability focus, ${title}: zoom ${Pan.view("cockpit").z}`);
      }
      const apps = $$('#side .side-kid[data-section="apps"]');
      const row = $('#side .side-link[data-section="apps"] .capfocus-count');
      ok(!!row && row.textContent === `${s.apps.size} of ${D.sections.find((x) => x.id === "apps").children.length}` && (!apps.length || apps.length === s.apps.size),
        `capability focus, ${title}: the sidebar's Apps list narrows to the ${s.apps.size} it touches, with a count`, `capability focus, ${title}: apps row ${row ? row.textContent : "none"}, ${apps.length} listed, wanted ${s.apps.size}`);
    }
    if (narrower) ok(true, `capability focus: ${narrower} of ${caps.length} capabilities leave boxes off the map (removed, not dimmed)`);
    else out.push("skip capability focus: every capability here touches every box, so nothing could be removed");
    const cap = caps[0];
    Nav.open("capabilities", cap); await tick();
    $('#main .capfocus-bar .capfocus-clear').click(); await tick();
    ok(!CapFocus.key() && !$(".capfocus-bar") && (!!$("#board svg.cockpit.grouped") || drawnNodes().length === D.nodes.length) && !$('#side .capfocus-count'), "capability focus: Show everything brings back the whole map and the whole sidebar", `capability focus: after Show everything ${drawnNodes().length} of ${D.nodes.length} boxes, grouped ${!!$("#board svg.cockpit.grouped")}, bar ${!!$(".capfocus-bar")}`);
    Nav.home(); await tick();
    MapView.st.lens = "cockpit"; rerender(); await tick();
    go(cap, { reveal: true }); await tick();
    ok(CapFocus.key() === cap && App.section === "capabilities", "capability focus: a capability chip picked from the map focuses it", `capability focus: chip left key ${CapFocus.key()} in ${App.section}`);
    Nav.home(); await tick();
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await focusing(ok, lines); } catch (e) { lines.push(`FAIL the capability focus check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the capability focus checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
