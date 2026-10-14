/* ------------------------------------------------------------ Error cases: the branch picker (branches.js, D8)
   For every flow with branches: the picker lists "Happy path" first and every branch of the data under its call, each
   option with the flow check's word on it; picking one redraws exactly that branch's steps, its own steps marked as
   off the happy path, keeps it in the address, and every part drawn opens the panel by click and by Enter. Every
   branch is swept for text that does not fit, in every theme and in Plain. A flow with nothing to branch on shows one
   line and no picker. A flow whose check did not reach the end never has an option without "not fully checked". */
(() => {
  const base = SelfTest.run, frames = () => Promise.resolve();
  const pick = (box, id) => { const sel = $(".br-pick", box); sel.value = id; sel.dispatchEvent(new Event("change")); };
  const panelHead = () => { const b = $("#panel-body"), head = b && $(".p-head h2", b); return head ? head.textContent.trim() : ""; };
  async function checks(ok) {
    const keys = Object.keys(D.branches || {});
    if (!keys.length) { ok(true, "branches: no flows, nothing to pick"); return; }
    for (const key of keys) {
      const d = D.branches[key];
      Nav.open("flows", key); Flows.select(key, -1);
      const box = $(`[data-branches="${CSS.escape(key)}"]`);
      if (d.state !== "drawn") {
        ok(box && box.matches(".br-note") && !$(".br-pick") && box.textContent.includes("aren't drawn yet"), `branches, ${key}: one line says its error cases aren't drawn yet, and no picker`, `branches, ${key}: the not-drawn line is missing or a picker shows`);
        continue;
      }
      const sel = box && $(".br-pick", box), opts = sel ? [...sel.options] : [], all = [d.happy, ...d.groups.flatMap((g) => g.options)];
      const groups = sel ? [...sel.querySelectorAll("optgroup")].map((g) => g.label) : [];
      ok(!!sel && opts.length === all.length && opts[0].value === "happy" && opts[0].textContent.startsWith("Happy path") && sel.value === "happy" && sel.tabIndex >= 0
        && JSON.stringify(groups) === JSON.stringify(d.groups.map((g) => g.label)) && $("label", box) && $("label", box).textContent === "Show",
        `branches, ${key}: "Show" and one picker, Happy path first and chosen, ${plural(all.length - 1, "branch", "branches")} under ${plural(groups.length, "call")}`,
        `branches, ${key}: the picker has ${opts.length} options for ${all.length}, groups ${JSON.stringify(groups)}, chosen ${sel && sel.value}`);
      ok(!d.check.notChecked || opts.every((o) => o.textContent.includes("not fully checked")), `branches, ${key}: ${d.check.notChecked ? "every option says not fully checked" : "the check reached the end"}`,
        `branches, ${key}: the check did not reach the end, but an option does not say so`);
      ok(all.every((o) => o.marks.every((m) => opts.find((x) => x.value === o.id).textContent.includes(`${m}`))), `branches, ${key}: every option says its flow-check marks in words`, `branches, ${key}: an option drops its marks`);
      const bad = [];
      for (const o of all) {
        if (o.drawn === false) { if (!opts.find((x) => x.value === o.id).disabled) bad.push(`${o.id} is not drawn but can be picked`); continue; }
        pick(box, o.id);
        const now = $(`[data-branches="${CSS.escape(key)}"]`), steps = $$(".br-step", now), off = $$(".br-step.alt", now);
        if (steps.length !== o.steps.length) bad.push(`${o.id}: ${steps.length} steps drawn for ${o.steps.length}`);
        if (off.length !== o.steps.filter((x) => x.alt).length) bad.push(`${o.id}: ${off.length} off-path steps drawn for ${o.steps.filter((x) => x.alt).length}`);
        // what goes in the address (Chrome throttles history calls during a long self-test, so the bar itself is
        // checked by test_explorer_branches_browser.py on a fresh page)
        if (o.id !== "happy" && Branches.hashPart(key) !== `&branch=${encodeURIComponent(o.id)}`) bad.push(`${o.id}: the address part is "${Branches.hashPart(key)}"`);
        if (o.id === "happy" && Branches.hashPart(key)) bad.push("happy path still names a branch in the address");
        if (Branches.current(key).id !== o.id) bad.push(`${o.id}: the picker did not keep it`);
        for (const f of o.findings) if (!$$(".br-finding", now).some((b) => b.textContent.includes(d.findings[f].summary))) bad.push(`${o.id}: its finding is not shown under the drawing`);
        const nodes = $$("[data-node]", now), loose = $$(".br-step, .br-party", now).filter((el) => !el.hasAttribute("data-node"));
        if (loose.length) bad.push(`${o.id}: ${loose.length} parts drawn without Nodes.wire`);
        for (const n of nodes.slice(0, 40)) {
          for (const how of ["click", "Enter"]) {
            go("lights", { reset: true });
            const before = panelHead();
            n.dispatchEvent(how === "click" ? new MouseEvent("click", { bubbles: true }) : new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
            if (!panelHead() || panelHead() === before) bad.push(`${o.id}: ${how} on "${n.getAttribute("data-node").slice(0, 40)}" left the panel as it was`);
          }
        }
      }
      ok(!bad.length, `branches, ${key}: each of ${all.filter((o) => o.drawn !== false).length} branches redraws its own steps, marks the ones off the happy path, stays in the address, and every part opens the panel`,
        `branches, ${key}: ${bad.slice(0, 6).join("; ")}`);
      pick($(`[data-branches="${CSS.escape(key)}"]`), "happy");
    }
    // a link that names a branch opens it
    const first = keys.find((k) => D.branches[k].state === "drawn" && D.branches[k].groups.length);
    if (first) {
      const o = D.branches[first].groups[0].options.find((x) => x.drawn);
      if (o) {
        const had = [...HASH.entries()];
        HASH.set("open", first); HASH.set("branch", o.id);  // the address as a pasted link reads it
        Nav.open("flows", first); Flows.select(first, -1); await frames();
        const box = $(`[data-branches="${CSS.escape(first)}"]`);
        ok(Branches.current(first).id === o.id && box && $(".br-pick", box).value === o.id, `branches: a link naming ${o.id} opens that branch`, `branches: a link naming ${o.id} opened ${Branches.current(first).id}`);
        for (const k of [...HASH.keys()]) HASH.delete(k);
        had.forEach(([k, v]) => HASH.append(k, v));
        if (box) pick(box, "happy");
      }
    }
    // every branch, in every theme and in Plain: nothing runs past its box
    const was = Theme.id, fx = FX.on, themes = [...Theme.LIST.map((t) => [t.id, t.label, true]), [was, "Plain", false]];
    for (const [id, label, motion] of themes) {
      Theme.set(id); FX.set(motion);
      const problems = [];
      for (const key of keys.filter((k) => D.branches[k].state === "drawn")) {
        Nav.open("flows", key); Flows.select(key, -1);
        for (const o of [D.branches[key].happy, ...D.branches[key].groups.flatMap((g) => g.options)].filter((x) => x.drawn !== false)) {
          pick($(`[data-branches="${CSS.escape(key)}"]`), o.id);
          const box = $(`[data-branches="${CSS.escape(key)}"]`);
          for (const b of [...TextFit.textFits(box), ...TextFit.clippedText(box)]) problems.push(`${key} ${o.id}: "${b.text}" ${b.why}`);
        }
        pick($(`[data-branches="${CSS.escape(key)}"]`), "happy");
      }
      ok(!problems.length, `branches: in ${label}, every branch's words fit their boxes`, `branches in ${label}: ${problems.slice(0, 8).join(" | ")}`);
    }
    Theme.set(was); FX.set(fx);
  }
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await checks(ok); } catch (e) { lines.push("FAIL the branch checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the branch checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
