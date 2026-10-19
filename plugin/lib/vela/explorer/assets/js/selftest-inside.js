/* ------------------------------------------------------------ The Details panel inside an app (detailspanel.js, inside.js)
   One right panel, one scope at a time. These checks drive it as a person would: pick a component and only that shows;
   pick a contract label, follow a link, and the trail reads back; a waiting question lights what it holds up; Escape
   and empty space return to the summary; the first click on another app only shows it and Open jumps; names stand
   where the codes were; and the page keeps its shape at the narrow width. A block of its own after SelfTest, so it
   merges apart from the checks above.

   It also answers `#scene=<name>` in a build made with --selftest, so a screenshot can be taken of a state the clicks
   reach (a, b, c, d, e: nothing picked, a component, a contract, a waiting question, the waiting tab). */
(() => {
  const base = SelfTest.run, frames = () => Promise.resolve();
  const CODE = /\b(?:CON|CAP|EPC|UNK|CST|PTY|FLO|SV)-\d{2,3}\b|\bOQ-\d{3}\b|\bADR-\d{4}\b/;
  const click = (el) => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  const head = () => { const h2 = $("#panel-body .p-head h2"); return h2 ? h2.textContent.trim() : ""; };
  const trailText = () => { const t = $("#panel-body .dp-trail"); return t ? t.textContent.replace(/\s+/g, " ").trim() : ""; };
  const esc = () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  const box = (app, name) => $(`#inside-draw g.in-box[data-key="${CSS.escape(`inside:${app}|c|${encodeURIComponent(name)}`)}"]`);
  const dimmed = () => $$("#inside-draw g.in-node.dim").length;
  const key = (app, kind, name) => `inside:${app}|${kind}|${encodeURIComponent(name)}`;

  /* The component with the most neighbors that also has a contract on a line and an open question, else any. */
  function chosen(app) {
    const P = D.insidePanel[app];
    const names = Object.keys(P.components);
    return names.find((n) => P.components[n].contracts.length && P.components[n].waiting.length) || names.find((n) => P.components[n].contracts.length) || names[0];
  }

  async function checks(ok, out) {
    const apps = D.map.apps.map((a) => a.key), app = apps.find((k) => D.designs[k] && D.insidePanel && D.insidePanel[k]);
    if (!app) { out.push("skip details panel: no --design was given to this build"); return; }
    const d = D.designs[app], P = D.insidePanel[app], name = chosen(app), comp = P.components[name], title = titleOf(app);
    Inside.open(app, "components"); await frames();

    // the header says the design's state and what was not read, once
    const chips = $$("#main .page-actions .d-state");
    ok(chips.length === 1 && !$("#main .page-actions .d-status:not(.d-state)") && /^Design.* · (\d+ parts? not read|read in full)/.test(chips[0].textContent.trim()),
      `details panel: the header says "${chips[0] ? chips[0].textContent.trim() : ""}" once`, `details panel: the header has ${chips.length} state chips: ${chips.map((c) => c.textContent.trim()).join(" | ")}`);

    // nothing picked: the design at a glance, one right panel, two tabs, no separate design-tabs column
    const tabs = $$("#panel-body .dp-tabs [role=tab]").map((b) => b.textContent.replace(/\s+/g, " ").trim());
    const cards = $$("#panel-body .glance .in-card h3").map((x) => x.textContent.replace(/\s+/g, " ").trim());
    ok(head() === "The design at a glance" && tabs.length === 2 && tabs[0] === "Details" && /^What's waiting/.test(tabs[1]) && !$(".inside-side, .inside-tabs") && !$("#panel-body .comp-sec"),
      `details panel: nothing picked shows the design at a glance, with the tabs ${tabs.join(" and ")}, and no column of design tabs`, `details panel: nothing picked shows "${head()}", tabs ${tabs.join(" | ")}`);
    const want = ["About this section", "What it is", "The stack in one line", "Top risks", "Quality targets", "Coverage gaps"];
    ok(want.every((w) => cards.some((c) => c.startsWith(w))) && $$("#panel-body .glance [data-open-section]").length >= want.length - 1,
      `details panel: the summary cards are ${cards.join(", ")}, each with a way into its full section`, `details panel: the summary cards are ${cards.join(", ")}`);
    click($("#panel-body .glance .more[data-open-section=risks]"));
    const back = $("#panel-body .dp-back");
    ok(head() === "Risks" && !!back && /back to the summary/.test(back.textContent), "details panel: a card opens its whole section, with ← back to the summary", `details panel: the risks card opened "${head()}", back is ${back ? back.textContent : "missing"}`);
    click(back);
    ok(head() === "The design at a glance", "details panel: ← back returns to the summary", `details panel: back left "${head()}"`);

    // one scope at a time: a component shows only itself, and lights it and its neighbors
    const el = box(app, name);
    click(el); await frames();
    const sections = $$("#panel-body .comp-sec h4").map((x) => x.textContent.trim());
    ok(head() === `${name} · part of ${title}` && !$("#panel-body .glance") && ["What it delivers", "Its contracts", "Its flows", "What's waiting"].every((s) => sections.includes(s)),
      `details panel: picking ${name} shows only ${name}: ${sections.join(", ")}`, `details panel: picking ${name} shows "${head()}" with sections ${sections.join(", ")}`);
    const nodes = $$("#inside-draw g.in-node[data-nid]").length, lit = nodes - dimmed();
    ok(dimmed() > 0 && lit >= 1 && !el.classList.contains("dim") && el.classList.contains("picked"), `details panel: ${name} and its neighbors are lit (${lit} of ${nodes}), the rest dimmed`, `details panel: ${lit} of ${nodes} lit, picked ${el.classList.contains("picked")}`);
    const noFlow = !comp.flows.length ? /No key flow names it/.test($("#panel-body").textContent) : comp.flows.every((f) => $$(`#panel-body [data-dp="${CSS.escape(key(app, "flow", String(f.index)))}"]`).length === 1);
    const noWait = !comp.waiting.length ? /No open question names it/.test($("#panel-body").textContent) : comp.waiting.every((q) => $$(`#panel-body [data-dp="${CSS.escape(key(app, "oq", q.id))}"]`).length === 1);
    ok(noFlow && noWait && !/Risks|Decision/.test(sections.join()), `details panel: ${name}'s flows (${comp.flows.length}) and waiting questions (${comp.waiting.length}) are only the ones the design ties to it, and it shows no decision or risk`,
      `details panel: flows ${noFlow}, waiting ${noWait}, sections ${sections.join()}`);

    // a link inside Details pushes onto the trail; the trail and ← back return
    const contractLink = $(`#panel-body .comp-sec [data-dp*="|con|"]`);
    if (contractLink) {
      click(contractLink); await frames();
      const cn = P.contracts[decodeURIComponent(contractLink.dataset.dp.split("|").pop())].name;
      ok(head() === cn && trailText().replace(/\s/g, "").startsWith(`Design›${name}›`.replace(/\s/g, "")) && trailText().includes(cn.slice(0, 20)) && /back to /.test($("#panel-body .dp-back").textContent),
        `details panel: following ${cn} reads "${trailText()}" with ← back to ${name}`, `details panel: after the link the heading is "${head()}", the trail "${trailText()}"`);
      click($("#panel-body .dp-back"));
      ok(head().startsWith(name), `details panel: ← back returns to ${name}`, `details panel: back left "${head()}"`);
    } else out.push(`skip details panel: ${name} has no contract link`);

    // a contract label on a line: Details for the contract, ways it answers, the connection, who provides and calls it
    esc(); await frames();
    ok(head() === "The design at a glance" && !App.trail.length && dimmed() === 0, "details panel: Escape returns to the summary and clears the lighting", `details panel: Escape left "${head()}", trail ${App.trail.length}, dimmed ${dimmed()}`);
    const label = $$("#inside-draw g.in-label.pick").find((g) => g.dataset.cons && !g.dataset.cons.includes(","));
    if (label) {
      const id = label.dataset.cons, k = P.contracts[id];
      click(label); await frames();
      const h4s = $$("#panel-body .comp-sec h4").map((x) => x.textContent.trim());
      ok(head() === k.name && App.trail.length === 1 && ["Who provides it, who calls it", "Ways it answers", "The connection", "What's waiting"].every((s) => h4s.includes(s)) && !$("#panel-body .glance"),
        `details panel: the label ${k.name} opens that contract: ${h4s.join(", ")}`, `details panel: the label opened "${head()}" with ${h4s.join(", ")}`);
      const body = $("#panel-body").textContent;
      ok(k.provider.name && body.includes(k.provider.name) && k.callers.every((c) => body.includes(c)) && (!k.answers.length || k.answers.every((a) => body.includes(a.when))) && (!k.connection.protocol || body.includes(k.connection.protocol.slice(0, 20))),
        `details panel: ${k.name} says who provides it (${k.provider.name}), who calls it (${k.callers.join(", ")}), how it answers and the connection`, `details panel: ${k.name} is missing its provider, callers, answers or connection`);
      ok($$("#inside-draw path.in-edge.near").length >= 1 && dimmed() > 0, `details panel: the contract's line and both ends are lit`, "details panel: the contract's line is not lit");
    } else out.push("skip details panel: no single-contract label is drawn");

    // a waiting item shows its question and lights the parts it holds up
    const q = P.waiting.find((x) => x.holds.length);
    if (q) {
      esc(); await frames();
      DetailsPanel.setTab("waiting"); await frames();
      const rows = $$("#panel-body .wq");
      click(rows.find((r) => r.dataset.oq === q.id)); await frames();
      const held = $$("#inside-draw g.in-node.held").map((g) => g.dataset.nid);
      ok(rows.length === P.waiting.length && $("#panel-body .kind").textContent === "Open question" && head() === q.question && DetailsPanel.tab === "details" && held.length === q.holds.length && q.holds.every((n) => held.includes("c:" + n)),
        `details panel: the waiting item "${shorten(q.question, 40)}" shows its question and lights the ${q.holds.length} parts it holds up`, `details panel: the waiting item opened "${head()}", ${held.length} lit of ${q.holds.length}, tab ${DetailsPanel.tab}`);
      esc(); await frames();
      DetailsPanel.setTab("waiting");
      click($(`#panel-body [data-dp-tab=details]`)); await frames();
    }

    // empty space goes back to the summary, as Escape does; hovering lights neighbors and leaves the panel alone
    click(box(app, name)); await frames();
    const holderSvg = $("#inside-draw svg");
    click(holderSvg);
    ok(head() === "The design at a glance" && !App.trail.length, "details panel: a click on empty space in the drawing returns to the summary", `details panel: empty space left "${head()}"`);
    click(box(app, name));
    const other = Object.keys(P.components).find((n) => n !== name), h0 = head();
    box(app, other).dispatchEvent(new PointerEvent("pointerover", { bubbles: true }));
    const hoverDim = dimmed(), h1 = head();
    $("#inside-draw").dispatchEvent(new PointerEvent("pointerleave"));
    ok(h0 === h1 && hoverDim > 0 && App.trail.length === 1, `details panel: hovering ${other} lights its neighbors and the panel stays on ${name}`, `details panel: hover changed "${h0}" to "${h1}" or lit nothing (${hoverDim})`);

    // keyboard: a box is reached by Tab, Enter picks it, Escape clears
    esc();
    const kb = box(app, other);
    kb.focus();
    kb.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true })); await frames();
    const picked = head();
    esc();
    ok(kb.getAttribute("tabindex") === "0" && picked.startsWith(other) && head() === "The design at a glance", `details panel: ${other} takes Tab, Enter picks it and Escape clears it`, `details panel: Enter showed "${picked}", Escape "${head()}"`);

    // another app: the first click only shows it, Open jumps
    const stub = $$("#inside-draw g.in-stub").find((g) => g.dataset.key.includes("|app|"));
    if (stub) {
      const nk = parse2(stub.dataset.key), view0 = App.view, was = Inside.st.level;
      click(stub); await frames();
      const open = $("#panel-body .p-head .dp-open");
      ok(!!open && head() === titleOf(nk) && Inside.st.app === app && Inside.st.level === was && App.view === view0, `details panel: ${titleOf(nk)} shows its details first, with an Open button, and the page has not moved`, `details panel: the first click on ${titleOf(nk)} showed "${head()}", app ${Inside.st.app}, Open ${!!open}`);
      click(open); await frames();
      ok(Inside.st.app === nk && Inside.st.level === "context", `details panel: Open goes inside ${titleOf(nk)}`, `details panel: Open left us in ${Inside.st.app} at ${Inside.st.level}`);
      Inside.open(app, "components"); await frames();
    } else out.push("skip details panel: no other app is drawn beside the components");

    // names, never codes, in the panel and on the diagram
    const leaks = [];
    const see = (where) => { const t = ($("#panel-body") ? $("#panel-body").textContent : "") + " " + $$("#inside-draw svg text, #inside-draw svg title").map((x) => x.textContent).join(" "); const m = t.match(CODE); if (m) leaks.push(`${where}: ${m[0]}`); };
    esc(); see("the summary");
    for (const n of Object.keys(P.components)) { go(key(app, "c", n), { reset: true }); see(n); }
    for (const id of Object.keys(P.contracts)) { go(key(app, "con", id), { reset: true }); see(P.contracts[id].name); }
    for (const x of P.waiting) { go(key(app, "oq", x.id), { reset: true }); see(shorten(x.question, 20)); }
    for (const [t] of Inside.TABS) { go(key(app, "sec", t), { reset: true }); see(t); }
    esc();
    ok(!leaks.length, "details panel: the summary, every component, contract, question and section, and the diagram say names, never codes", `details panel: codes shown: ${leaks.slice(0, 6).join("; ")}`);

    // the diagram's bar: Show, Highlight, the Key, full screen, more
    const bar = $$("#main .dia-bar .dmenu-btn").map((b) => b.getAttribute("aria-label") || b.textContent.replace(/\s+/g, " ").trim());
    ok(["Show", "Highlight"].every((w) => bar.some((b) => b.startsWith(w))) && !!$("#main .dia-bar [data-dmenu=key]") && !!$("#inside-full") && !!$("#main .dia-bar [data-dmenu=more]"),
      `details panel: the diagram bar carries Show, Highlight, the Key, full screen and more (${bar.join(" | ")})`, `details panel: the diagram bar has ${bar.join(" | ")}`);
    const stubs0 = $$("#inside-draw g.in-stub").length;
    Inside.st.show = "components"; rerender(); await frames();
    const stubs1 = $$("#inside-draw g.in-stub").length;
    Inside.st.show = "all"; rerender(); await frames();
    ok(stubs0 > 0 ? stubs1 === 0 : true, `details panel: Show "Components only" takes the ${stubs0} outside services off the drawing`, `details panel: ${stubs1} outside services stayed`);
    Inside.st.hl = "waiting"; rerender(); await frames();
    const heldNow = $$("#inside-draw g.in-node.held").length, wantHeld = Object.values(P.components).filter((c) => c.waiting.length).length;
    Inside.st.hl = "near"; rerender(); await frames();
    ok(heldNow === wantHeld, `details panel: Highlight "What's waiting" lights the ${wantHeld} components with an open question`, `details panel: ${heldNow} lit, wanted ${wantHeld}`);
    click($("#inside-full")); await frames();
    const full = $("#main").classList.contains("inside-full") && getComputedStyle($("#panel")).display === "none";
    esc(); await frames();
    ok(full && !$("#main").classList.contains("inside-full"), "details panel: full screen hides the panel and Escape leaves it", `details panel: full screen ${full}, after Escape ${$("#main").classList.contains("inside-full")}`);

    // Not recorded: a section the design lacks says so, and no field is invented
    const was = P.summary.stack; P.summary.stack = null; go(key(app, "c", name), { reset: true }); esc();
    ok(/Not recorded/.test($("#panel-body .glance").textContent), "details panel: a summary card with nothing behind it says Not recorded", "details panel: an empty card does not say Not recorded");
    P.summary.stack = was;

    // Widen is remembered; the panel keeps its shape at this width
    const w0 = $("#panel").getBoundingClientRect().width, widen = $("#panel-widen");
    if (!isCompact()) {
      click(widen); await frames();
      const w1 = $("#panel").getBoundingClientRect().width, kept = Settings.read("explorer.panel.width");
      click(widen); await frames();
      ok(w1 > w0 + 40 && widen.textContent === "Widen" && kept === "640", `details panel: Widen takes the panel from ${Math.round(w0)} to ${Math.round(w1)} px, remembers it, and Narrow puts it back`, `details panel: Widen ${Math.round(w0)} to ${Math.round(w1)}, remembered ${kept}`);
    }
    go(key(app, "c", name), { reset: true }); await frames();
    const over = document.documentElement.scrollWidth - innerWidth;
    ok(over <= 1 && (!isCompact() || (document.body.classList.contains("compact") && $("#panel-body").textContent.includes(name))),
      `details panel: at ${innerWidth} px the page does not scroll sideways${isCompact() ? ", and the panel is the slide-over holding the pick" : ", and the panel is the third column"}`, `details panel: at ${innerWidth} px the page is ${over} px too wide, compact ${document.body.classList.contains("compact")}`);
    esc();

    // Context and Containers use the same panel
    for (const level of ["context", "containers"]) {
      Inside.open(app, level); await frames();
      ok(head() === "The app at a glance" && $$("#panel-body .dp-tabs [role=tab]").length === 2 && !!$("#main .dia-bar [data-dmenu=key]"), `details panel: ${level} uses the same panel, tabs and diagram bar`, `details panel: ${level} shows "${head()}"`);
    }
    Inside.open(app, "components"); await frames();
  }
  const parse2 = (k) => decodeURIComponent(k.split("|").pop());

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await checks(ok, lines); } catch (e) { lines.push("FAIL the details panel checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the details panel checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };

  /* #scene=a|b|c|d|e: set the page up as a person's clicks would, for a screenshot. */
  addEventListener("load", () => {
    const scene = HASH.get("scene");
    if (!scene) return;
    setTimeout(() => {
      const app = D.map.apps.map((a) => a.key).find((k) => D.designs[k] && D.insidePanel[k]);
      if (!app) return;
      const P = D.insidePanel[app], name = HASH.get("component") || chosen(app), oq = P.waiting.find((x) => x.holds.length);
      Inside.open(app, "components", { still: true });
      const con = (P.components[name].contracts[0] || {}).id;
      if (scene === "b") go(key(app, "c", name), { reset: true });
      if (scene === "c") { go(key(app, "c", name), { reset: true }); if (con) go(key(app, "con", con)); }
      if (scene === "d" && oq) go(key(app, "oq", oq.id), { reset: true });
      if (scene === "e") { go(key(app, "c", name), { reset: true }); DetailsPanel.setTab("waiting"); }
      if (isCompact()) PanelSize.hide(false);  // the slide-over is closed until asked for; a screenshot of the panel needs it open
      document.body.setAttribute("data-scene", scene);
    }, 300);
  });
})();
