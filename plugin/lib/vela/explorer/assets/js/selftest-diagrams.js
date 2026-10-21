/* ------------------------------------------------------------ Every diagram in a design's Key flows and Supporting diagrams is drawn
   A plain sequence is stepped through; any other diagram, and a sequence the stepper can't read to the end, is drawn
   by Mermaid with the shared zoom bar. Only a diagram Mermaid itself rejects shows source, with the reason in plain words. */
(() => {
  const base = SelfTest.run, wait = (ms) => new Promise((r) => setTimeout(r, ms));
  async function settled() { for (let i = 0; i < 100 && $$('#panel [data-drawn="pending"], #main [data-drawn="pending"]').length; i++) await wait(50); }

  async function drawn(ok, out) {
    const apps = D.map.apps.map((a) => a.key).filter((k) => D.designs[k]);
    if (!apps.length) { out.push("skip diagrams: no --design was given to this build"); return; }
    for (const app of apps) {
      const d = D.designs[app], all = [...d.flows, ...d.diagrams], name = titleOf(app);
      if (!all.length) continue;
      go(`inside:${app}|sec|flows`, { reset: true }); await wait(30); await settled();
      const cards = $$("#panel .inside-tab-body > .in-card");
      ok(cards.length === all.length, `diagrams, ${name}: its ${all.length} diagrams each have a card`, `diagrams, ${name}: ${cards.length} cards for ${all.length} diagrams`);
      all.forEach((f, i) => {
        const card = cards[i], what = `${name}, ${f.title || f.kind}`;
        if (!card) return;
        if (f.stepper) { ok(!!$(".in-seq svg.seq", card) && !$(".mm-frame", card), `diagrams, ${what}: a sequence read to the end is stepped through`, `diagrams, ${what}: no stepper drawn`); return; }
        const frame = $(".mm-frame, .mm-error", card);
        if (!frame) { ok(false, `diagrams, ${what}: nothing drew it (${card.textContent.slice(0, 80)})`); return; }
        if (frame.classList.contains("mm-error")) {
          ok(/can't be drawn: \S/.test(frame.textContent) && !!$("pre", frame), `diagrams, ${what}: Mermaid rejected it, so the reader gets the reason in words and the source`, `diagrams, ${what}: rejected without a reason or source`);
          return;
        }
        const svg = $("svg.mm-svg", frame), bar = $(".zoom-bar", frame);
        ok(frame.dataset.drawn === "yes" && !!svg && svg.querySelectorAll("*").length > 3 && !$("script, foreignObject", svg), `diagrams, ${what}: ${f.kind} is drawn by Mermaid (${svg ? svg.querySelectorAll("*").length : 0} parts)`, `diagrams, ${what}: not drawn (state ${frame.dataset.drawn}, ${card.textContent.slice(0, 80)})`);
        if (!svg || !bar) { ok(false, `diagrams, ${what}: a drawn diagram has the zoom bar`); return; }
        const before = svg.getAttribute("viewBox"), plus = [...$$("button", bar)].find((b) => b.getAttribute("aria-label").startsWith("Zoom in"));
        plus.click();
        ok(svg.getAttribute("viewBox") !== before && Pan.view(frame.__pan.key).z > 1, `diagrams, ${what}: it has the zoom bar, and + zooms it`, `diagrams, ${what}: + left the view at ${svg.getAttribute("viewBox")}`);
        [...$$("button", bar)].find((b) => b.getAttribute("aria-label").startsWith("Fit")).click();
      });
      ok(!/can't draw/.test($("#panel .inside-tab-body").textContent), `diagrams, ${name}: no card says the page can't draw a diagram`, `diagrams, ${name}: a card still says the page can't draw one`);
    }
    Nav.home(); await wait(30);
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await drawn(ok, lines); } catch (e) { lines.push(`FAIL the diagram check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the diagram checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
