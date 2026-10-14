/* ------------------------------------------------------------ Error cases: the Show picker on the played flow (D8)
   One diagram: for every flow with branches, the picker sits in the header row ("Show", Happy path first and
   chosen, every branch under its call, each option with the flow check's word on it), and picking one redraws the
   played flow with exactly that branch's steps, the ones off the happy path in amber and in the one key, the
   summary line under the header, the branch's findings in plain words under the diagram, its limits, and the
   address part. Every part opens the panel by click and by Enter, and the words fit in every theme and in Plain. A
   flow with nothing to branch on shows one line and no picker. The pills on the arrows never overlap one another,
   on any flow's happy path or branch: one pill per call and answer. */
(() => {
  const base = SelfTest.run, frames = () => Promise.resolve();
  const panelHead = () => { const b = $("#panel-body"), head = b && $(".p-head h2", b); return head ? head.textContent.trim() : ""; };
  const pick = (key, id) => { const sel = $(`[data-branches="${CSS.escape(key)}"] .br-pick`); if (!sel) return false; sel.value = id; sel.dispatchEvent(new Event("change")); return true; };
  /* Contract pills drawn for a flow, on a scratch canvas the stage's size, after every step has played. */
  /* What the stage draws for a flow, on a scratch canvas the stage's usual size, after every step has played. */
  function drawn(flow, w, ht) {
    const canvas = document.createElement("canvas"); canvas.width = w; canvas.height = ht;
    const G = FlowKit.layout(flow, { x: 0, y: 6, w: w - 8, h: ht - 6, s: clamp(w / 1040, 0.8, 1.2) });  // as the stage's player lays it out
    return FlowKit.drawScene(canvas.getContext("2d"), G, { cur: flow.steps.length, tau: 99, clock: 0, D: 0.8, images: false });
  }
  /* The stage at this window's size, and a short stage (a laptop with the key open), where rows sit closest. */
  const SIZES = () => { const r = $(".stage-canvas") ? $(".stage-canvas").getBoundingClientRect() : { width: 1040, height: 560 }; return [[Math.max(320, r.width), Math.max(240, r.height)], [1000, 300]]; };
  const meets = (a, b) => a.x < b.x + b.w - 1 && b.x < a.x + a.w - 1 && a.y < b.y + b.h - 1 && b.y < a.y + a.h - 1;
  /* A pill may not overlap another pill, nor sit across another step's arrow (a row's line runs through its middle). */
  function overlaps(flow) {
    const out = [];
    for (const [w, ht] of SIZES()) for (const o of overlapsAt(flow, w, ht)) out.push(`${o} (stage ${Math.round(w)}x${Math.round(ht)})`);
    return out;
  }
  function overlapsAt(flow, w, ht) {
    const hits = drawn(flow, w, ht), list = hits.filter((t) => t.type === "contract"), rows = hits.filter((t) => t.type === "row"), out = [];
    const at = (t) => `step ${flow.steps[t.si].n}`;
    list.forEach((a, i) => list.slice(i + 1).forEach((b) => { if (meets(a, b)) out.push(`the ${a.id} pill at ${at(a)} over the ${b.id} pill at ${at(b)}`); }));
    // one exchange, one pill: the answer to a call, on the next step over the same contract, is not labeled again
    list.forEach((a, i) => { const b = list[i + 1]; if (b && b.id === a.id && b.si === a.si + 1) out.push(`the ${a.id} pill drawn twice, at ${at(a)} and ${at(b)}`); });
    for (const a of list) for (const r of rows) {
      const line = r.y + r.h / 2;
      if (r.si !== a.si && line > a.y + 1 && line < a.y + a.h - 1 && a.x < r.x + r.w && r.x < a.x + a.w) out.push(`the ${a.id} pill at ${at(a)} across the arrow of ${at(r)}`);
    }
    return out;
  }
  /* A numbered item's number sits on its first line. An atomic inline box (an inline-block, or a button, which is one
     whatever its display) that wraps is one tall box whose baseline is its last line, and the list number follows the
     baseline: so any such child of an ol item, one box taller than a line and a half, puts the number out of line. */
  function markersOutOfLine(root) {
    const bad = [];
    for (const li of $$("ol > li", root)) {
      if (!li.getClientRects().length) continue;
      const lh = parseFloat(getComputedStyle(li).lineHeight) || parseFloat(getComputedStyle(li).fontSize) * 1.3;
      for (const el of li.children) {
        const rects = [...el.getClientRects()].filter((r) => r.width > 0), cs = getComputedStyle(el);
        const atomic = /^inline-(block|flex|grid|table)$/.test(cs.display) || (/^(BUTTON|SELECT|INPUT)$/.test(el.tagName) && cs.display === "inline");
        if (atomic && rects.length === 1 && rects[0].height > lh * 1.5) bad.push(shorten(li.textContent.trim(), 40));
      }
    }
    return bad;
  }
  async function checks(ok) {
    const off = [];
    for (const f of D.flows) { Nav.open("flows", f.key); Flows.select(f.key, -1); await frames(); for (const b of markersOutOfLine($("#main"))) off.push(`${f.key}: "${b}"`); }
    for (const s of D.sections) { Nav.open(s.id); await frames(); for (const b of markersOutOfLine($("#main"))) off.push(`${s.label}: "${b}"`); }
    ok(!off.length, "lists: every numbered item's number sits on its first line, on every flow and section page", `lists: numbers out of line with their text: ${off.slice(0, 6).join("; ")}`);
    const keys = Object.keys(D.branches || {});
    const crowded = [];
    for (const f of D.flows) for (const o of overlaps(FlowKit.flowOf(f.key))) crowded.push(`${f.key}: ${o}`);
    ok(!crowded.length, `flows: no two contract pills overlap on any flow (${D.flows.length} flows)`, `flows: pills overlap: ${crowded.slice(0, 6).join("; ")}`);
    if (!keys.length) return;
    for (const key of keys) {
      const d = D.branches[key];
      Nav.open("flows", key); Flows.select(key, -1); await frames();
      if (d.state !== "drawn") {
        ok($(`[data-branches-note="${CSS.escape(key)}"]`) && !$(".br-pick") && $(".br-note").textContent.includes("aren't drawn yet") && $$("canvas.stage-canvas").length === 1,
          `branches, ${key}: one line says its error cases aren't drawn yet, no picker, one diagram`, `branches, ${key}: the not-drawn line is missing, or a picker or a second diagram shows`);
        continue;
      }
      const head = $(".flows-head"), box = $(`[data-branches="${CSS.escape(key)}"]`, head || document), sel = box && $(".br-pick", box);
      const opts = sel ? [...sel.options] : [], all = [d.happy, ...d.groups.flatMap((g) => g.options)];
      const groups = sel ? [...sel.querySelectorAll("optgroup")].map((g) => g.label) : [];
      ok(!!sel && opts.length === all.length && opts[0].value === "happy" && opts[0].textContent.startsWith("Happy path") && sel.value === "happy" && sel.tabIndex >= 0
        && JSON.stringify(groups) === JSON.stringify(d.groups.map((g) => g.label)) && $("label", box).textContent === "Show" && $$("canvas.stage-canvas").length === 1 && !$("svg.br-svg"),
        `branches, ${key}: "Show" in the header row beside the flow picker, Happy path first and chosen, ${plural(all.length - 1, "branch", "branches")} under ${plural(groups.length, "call")}, one diagram`,
        `branches, ${key}: the picker has ${opts.length} options for ${all.length}, groups ${JSON.stringify(groups)}, chosen ${sel && sel.value}, ${$$("canvas.stage-canvas").length} canvases`);
      const sum = $(`[data-branches-summary="${CSS.escape(key)}"]`);
      ok(!!sum && sum.previousElementSibling === head && / ways this flow can go: the happy path and /.test(sum.textContent), `branches, ${key}: the summary line sits under the header row`, `branches, ${key}: the summary line is missing or out of place`);
      ok(!d.check.notChecked || opts.every((o) => o.textContent.includes("not fully checked")), `branches, ${key}: ${d.check.notChecked ? "every option says not fully checked" : "the check reached the end"}`,
        `branches, ${key}: the check did not reach the end, but an option does not say so`);
      ok(all.every((o) => o.marks.every((m) => opts.find((x) => x.value === o.id).textContent.includes(m))), `branches, ${key}: every option says its flow-check marks in words`, `branches, ${key}: an option drops its marks`);
      const bad = [];
      for (const o of all) {
        if (o.drawn === false) { if (!opts.find((x) => x.value === o.id).disabled) bad.push(`${o.id} is not drawn but can be picked`); continue; }
        if (!pick(key, o.id)) { bad.push(`${o.id}: no picker after a redraw`); continue; }
        await frames();
        const flow = FlowKit.flowOf(key), want = o.id === "happy" ? FLOW[key].steps.length : o.steps.length;
        if (flow.steps.length !== want || $$("#scrub .tick").length !== want) bad.push(`${o.id}: ${flow.steps.length} steps and ${$$("#scrub .tick").length} ticks for ${want}`);
        const last = flow.steps[flow.steps.length - 1];
        if (o.id !== "happy" && !(o.steps[o.steps.length - 1].kind === "end" && last && !last.messages.length && !last.self)) bad.push(`${o.id}: the branch does not end with its ending drawn as a band`);
        if (o.id !== "happy" && flow.steps.filter((x) => x.differs).length !== o.steps.filter((x) => x.differs).length) bad.push(`${o.id}: the amber steps do not match`);
        if (o.id !== "happy" && o.steps.some((x) => x.differs) && !$('.legend[data-legend="flow"] [data-lg="flow.differs"]')) bad.push(`${o.id}: the key does not say what amber means`);
        if ($$(".legend").filter((l) => !l.hidden && l.closest("#main")).length !== 1) bad.push(`${o.id}: ${$$(".legend").filter((l) => !l.hidden && l.closest("#main")).length} keys on the view`);
        const audit = Legend.audit().filter((p) => p.startsWith("flow:"));
        if (audit.length) bad.push(`${o.id}: ${audit[0]}`);
        if (o.id !== "happy" && Branches.hashPart(key) !== `&branch=${encodeURIComponent(o.id)}`) bad.push(`${o.id}: the address part is "${Branches.hashPart(key)}"`);
        if (o.id === "happy" && Branches.hashPart(key)) bad.push("happy path still names a branch in the address");
        const shown = $(`[data-branches-findings="${CSS.escape(key)}"]`);
        for (const i of [...o.findings, ...(o.id === "happy" ? d.flowWide : [])]) {
          if (!shown || !shown.textContent.includes(d.findings[i].summary)) bad.push(`${o.id}: its finding is not under the diagram`);
          if (shown && shown.compareDocumentPosition($(".stage")) & Node.DOCUMENT_POSITION_FOLLOWING) bad.push(`${o.id}: the finding sits above the diagram`);
        }
        const said = $$(".br-limits li").map((li) => li.textContent);
        if (JSON.stringify(said) !== JSON.stringify((o.limits || []).map((i) => d.limits[i]))) bad.push(`${o.id}: says ${said.length} of the check's limits for ${(o.limits || []).length}`);
        for (const c of overlaps(flow)) bad.push(`${o.id}: pills overlap, ${c}`);
        for (const n of $$("[data-node]", $("#main")).slice(0, 40)) {
          for (const how of ["click", "Enter"]) {
            if (!n.isConnected) continue;
            go("lights", { reset: true });
            const before = panelHead();
            n.dispatchEvent(how === "click" ? new MouseEvent("click", { bubbles: true }) : new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
            if (!panelHead() || panelHead() === before) bad.push(`${o.id}: ${how} on "${n.getAttribute("data-node").slice(0, 40)}" left the panel as it was`);
          }
        }
      }
      ok(!bad.length, `branches, ${key}: each of ${all.filter((o) => o.drawn !== false).length} redraws the one diagram with its own steps, amber where it leaves the happy path, its findings under it, and every part opens the panel`,
        `branches, ${key}: ${bad.slice(0, 6).join("; ")}`);
      pick(key, "happy");
    }
    // a link that names a branch opens it
    const first = keys.find((k) => D.branches[k].state === "drawn" && D.branches[k].groups.length);
    const o = first && D.branches[first].groups[0].options.find((x) => x.drawn);
    if (o) {
      const had = [...HASH.entries()];
      HASH.set("open", first); HASH.set("branch", o.id);  // the address as a pasted link reads it
      Nav.open("flows", first); Flows.select(first, -1); await frames();
      const sel = $(`[data-branches="${CSS.escape(first)}"] .br-pick`);
      ok(Branches.current(first).id === o.id && sel && sel.value === o.id && FlowKit.flowOf(first).branch === o.id, `branches: a link naming ${o.id} opens the flow drawn as that branch`,
        `branches: a link naming ${o.id} opened ${Branches.current(first).id}`);
      for (const k of [...HASH.keys()]) HASH.delete(k);
      had.forEach(([k, v]) => HASH.append(k, v));
      pick(first, "happy");
    }
    // every branch, in every theme and in Plain: the header, the summary and the findings fit
    const was = Theme.id, fx = FX.on, themes = [...Theme.LIST.map((t) => [t.id, t.label, true]), [was, "Plain", false]];
    for (const [id, label, motion] of themes) {
      Theme.set(id); FX.set(motion);
      const problems = [];
      for (const key of keys.filter((k) => D.branches[k].state === "drawn")) {
        Nav.open("flows", key); Flows.select(key, -1);
        for (const o of [D.branches[key].happy, ...D.branches[key].groups.flatMap((g) => g.options)].filter((x) => x.drawn !== false)) {
          pick(key, o.id);
          for (const root of [$(".flows-head"), $(".br-summary"), $(".br-findings")].filter(Boolean)) {
            for (const b of [...TextFit.textFits(root), ...TextFit.clippedText(root)]) problems.push(`${key} ${o.id}: "${b.text}" ${b.why}`);
          }
        }
        pick(key, "happy");
      }
      ok(!problems.length, `branches: in ${label}, every branch's header, summary and findings fit`, `branches in ${label}: ${problems.slice(0, 8).join(" | ")}`);
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
