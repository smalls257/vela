/* ------------------------------------------------------------ Capability focus (capfocus.js)
   Pick a capability: the focus view opens and the sidebar keeps only the apps, flows and epics it touches. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const same = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

  async function focusing(ok, out) {
    const caps = D.trace.capabilities.map((c) => c.key);
    if (!caps.length) { out.push("skip capability focus: this vault has no capabilities"); return; }
    let narrower = 0;
    for (const cap of caps) {
      const title = ent(cap).title;
      Nav.open("capabilities", cap); await tick();
      const s = CapFocus.scope(), side = $('#side .capfocus-bar'), shown = !!$("#cv-board svg.cv-svg") || !!$("#main .cv-lone");
      ok(!!s && CapFocus.key() === cap && App.view === "capmap" && shown && !!side && side.textContent.includes(`Showing ${title} only`) && side.textContent.includes("Show everything") && !$("#main .cv-grid"),
        `capability focus, ${title}: the focus view is up, not the cards, and the sidebar says it is the only one showing, with a way back`, `capability focus, ${title}: view ${App.view}, drawn ${shown}, side ${!!side}, key ${CapFocus.key()}`);
      // the panel's "Flows that cross this" and the sidebar's Flows list are one list
      const sec = $$("#panel .p-sec").find((x) => $("h3", x) && /^Flows that cross this/.test($("h3", x).textContent.trim())), listed = sec ? $$(".flow-chip [data-ref]", sec).map((a) => a.dataset.ref) : [];
      const counted = sec && /(\d+)\s*$/.exec($("h3", sec).textContent.trim());
      ok(!!sec && same(listed, [...s.flows]) && (!counted || +counted[1] === s.flows.size),
        `capability focus, ${title}: the panel's "Flows that cross this" lists the ${s.flows.size} flows the focus counts`,
        `capability focus, ${title}: panel lists ${listed.join(",") || "none"}${counted ? " (heading " + counted[1] + ")" : ""}, focus uses ${[...s.flows].join(",") || "none"}`);
      const apps = $$('#side .side-kid[data-section="apps"]');
      const row = $('#side .side-link[data-section="apps"] .capfocus-count');
      ok(!!row && row.textContent === `${s.apps.size} of ${D.sections.find((x) => x.id === "apps").children.length}` && (!apps.length || apps.length === s.apps.size),
        `capability focus, ${title}: the sidebar's Apps list narrows to the ${s.apps.size} it touches, with a count`, `capability focus, ${title}: apps row ${row ? row.textContent : "none"}, ${apps.length} listed, wanted ${s.apps.size}`);
      if (s.apps.size < D.map.apps.length) narrower++;
    }
    if (narrower) ok(true, `capability focus: ${narrower} of ${caps.length} capabilities leave apps out of the sidebar's list (removed, not dimmed)`);
    else out.push("skip capability focus: every capability touches every app, so nothing could be removed");
    const cap = caps[0];
    Nav.open("capabilities", cap); await tick();
    $('#side .capfocus-bar .capfocus-clear').click(); await tick();
    ok(!CapFocus.key() && !$(".capfocus-bar") && !$('#side .capfocus-count') && App.view === "capmap" && !!$("#main .cv-grid"), "capability focus: Show everything brings back the cards and the whole sidebar", `capability focus: after Show everything key ${CapFocus.key()}, bar ${!!$(".capfocus-bar")}, cards ${!!$("#main .cv-grid")}`);
    Nav.home(); await tick();
    go(cap, { reveal: true }); await tick();
    ok(CapFocus.key() === cap && App.section === "capabilities" && !!($("#cv-board svg.cv-svg") || $("#main .cv-lone")), "capability focus: a capability chip picked from another page lands on its focus view", `capability focus: chip left key ${CapFocus.key()} in ${App.section}, view ${App.view}`);
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
