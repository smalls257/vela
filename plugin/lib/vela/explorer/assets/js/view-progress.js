/* Progress: where each app stands on the stage ladder, how complete the design is by vela's five measures,
   what is due when, and what still waits on someone. These are the numbers vela status and vela next compute
   (progress.grid, progress.best, completeness.measure, override, handoff); the page only draws them. */
const ProgressView = (() => {
  const MIX = ["inkling", "assumption", "fact", "decided"].map((s) => [s, `var(--mix-${s})`]);
  const { bx } = Legend;
  const step = (o) => bx({ y: 5, height: 6, rx: 2, width: 8, ...o });
  Legend.define("pg.done", [step({ x: 3, fill: "ink-3" }), step({ x: 13, fill: "ink-3" })], "Gray step: a stage the app has already passed");
  Legend.define("pg.cur", [step({ x: 12, fill: "ink" })], "Bright step: the stage the app is at");
  Legend.define("pg.empty", [step({ x: 12, fill: "deck-3" })], "Empty step: a stage still to come");
  Legend.define("pg.off", [step({ x: 12, fill: "deck" })], "Dim steps: no planning stages apply to this app");
  const MIX_SAY = { inkling: "a hunch", assumption: "believed but not checked", fact: "has a source", decided: "settled in a working session" };
  for (const [state, color] of MIX) Legend.define("pg.mix." + state, [{ k: "box", y: 5, height: 6, rx: 2, fill: `mix-${state}` }], `${stateWord(state)}: ${MIX_SAY[state]}`);
  /* The next step Vela suggests, in words; the command it would run rides in the tooltip. */
  const MODE_SAY = { probe: "chase an answer on", boundary: "read back the boundary of", discover: "gather sources for", shape: "lay out the options for", epics: "write epics for", none: "nothing to run" };
  const modeEl = (mode) => (mode === "grill" ? h("span", {}, "hold a ", termEl("grill"), " on") : h("span", { title: mode === "none" ? null : `/vela:${mode}` }, MODE_SAY[mode] || mode));
  Legend.define("pg.fade", [bx({ fill: "caution", opacity: 0.4, x: 11, y: 2, width: 12, height: 12, rx: 3 })], "Paler bar: the most urgent question is some way off; bars strengthen as they fall due");
  /* A handle as a person reads it (the vault's name for the role, else the handle in words), and a reason without its
     capture marks: the reader text rule, no @handles or ^c codes. Same rule as the decision log's person(). */
  const personOf = (t) => peopleWords(t);
  const unmarked = (t) => String(t || "").replace(/\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\\?\|([^\]]+))?\]\]/g, (m, target, label) => label || titleOf(target))
    .replace(/\s*\^c\d+\b/g, "");
  function render(main) {
    const P = D.progress, sc = h("div", { class: "scroll pages" });
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Progress"),
      h("p", {}, "Each app's planning stage and what's still waiting on someone. The suggested next step is at the top.", Nav.ledeLink())),
      h("div", { class: "spacer" }), Nav.pageActions()), sc);
    const totals = [0, 0, 0, 0];
    P.rows.forEach((r) => r.mix.forEach((n, i) => { totals[i] += n; }));
    sc.append(h("section", { class: "card kpis" },
      h("div", { class: "shares" }, P.shares.map((x) => h("div", { class: "share" }, h("span", {}, x.name), h("div", { class: "bar" }, h("span", { style: `width:${x.total ? ((100 * x.done) / x.total).toFixed(1) : 100}%` })), h("span", { class: "v" }, `${x.done} of ${x.total}`)))),
      h("div", { class: "tiles" }, [3, 2, 1, 0].map((i) => h("div", { class: "tile" }, h("div", { class: "num" }, totals[i]), h("div", { class: "lab" }, h("i", { class: "sw", style: `background:${MIX[i][1]}` }), stateWord(MIX[i][0]))))),
      P.next ? h("div", { class: "note next" }, h("b", {}, "Suggested next step: "), modeEl(P.next.mode), " ", P.next.subject ? refChip(keyForId(P.next.subject)) : null, " ", P.next.reason) : null));
    const tableKey = Legend.open("progress-table", { root: () => tableCard, probes: { "pg.done": ".ladder .done", "pg.cur": ".ladder .cur", "pg.empty": ".ladder:not(.off) span:not(.done):not(.cur):not(.reach)",
      "pg.off": ".ladder.off", ...Object.fromEntries(MIX.map(([state]) => ["pg.mix." + state, `.mix span[style*="--mix-${state}"]`])) } });
    const table = h("table", { class: "t" }, h("tr", {}, h("th", {}, "App"), h("th", {}, "Waiting"), h("th", {}, "Stage"), h("th", {}, "Next step"), h("th", {}, "Handoff")));
    for (const r of P.rows) {
      const a = E[r.app], idx = P.stages.indexOf(r.stage), lv = levelOf(r.app);
      if (r.stage) {
        if (idx > 0) tableKey.saw("pg.done");
        tableKey.saw("pg.cur");
        if (P.stages.some((x, i) => i > idx)) tableKey.saw("pg.empty");
      } else tableKey.saw("pg.off");
      r.mix.forEach((n, i) => { if (n) tableKey.saw("pg.mix." + MIX[i][0]); });
      const caption = r.stage ? stageWord(r.stage) : `${a.change ? stateWord(a.change) : "No change"}: no planning stages apply`;
      // 89: "3 not decided yet", the state's own words, not "3 assumption"
      const settled = [3, 2, 1, 0].filter((i) => r.mix[i]).map((i) => `${r.mix[i]} ${stateWord(MIX[i][0]).toLowerCase()}`).join(", ") || "nothing yet";
      const howSettled = `How settled: ${settled}${r.byOverride ? ` (${r.byOverride} decided by skipping a check)` : ""}`;
      table.append(h("tr", { class: "click", onclick: () => go(r.app, { reset: true }) },
        h("td", {}, h("b", {}, a.title), h("div", { class: "muted" }, a.change ? stateWord(a.change) : "")),
        h("td", {}, lampEl(lv), " ", h("span", { class: "muted" }, LIGHT[lv].word)),
        h("td", { title: howSettled }, h("div", { class: "ladder" + (r.stage ? "" : " off") }, P.stages.map((x, i) => h("span", { class: r.stage ? (i < idx ? "done" : i === idx ? "cur" : "") : "", title: stageWord(x) }))), h("div", { class: "muted small" }, caption),
          h("div", { class: "mix" }, r.mix.map((n, i) => (n ? h("span", { style: `flex:${n};background:${MIX[i][1]}` }) : null)))),
        h("td", { class: "wide" }, h("b", {}, modeEl(r.mode)), h("div", { class: "muted small" }, r.reason), r.oldest ? h("div", { class: "small" }, h("span", { class: "muted" }, "oldest blocker: "), refChip(r.oldest)) : null),
        h("td", { class: "small" }, handoff(r.handoff), Inside.statusCell(r.app))));
    }
    const tableCard = h("section", { class: "card" }, h("h2", {}, "Planning stage for each app"), table, tableKey.el());
    sc.append(tableCard);
    tableKey.paint();
    sc.append(dueChart());
    const ov = h("section", { class: "card" }, h("h2", {}, "Decisions made on someone's behalf, not yet confirmed"));
    if (P.awaiting.length) ov.append(h("table", { class: "t" }, h("tr", {}, h("th", {}, "On"), h("th", {}, "Decided by"), h("th", {}, "On behalf of")),
      P.awaiting.map((a) => h("tr", { class: "click", onclick: () => go(a.key, { reset: true }) }, h("td", {}, refChip(a.key)), h("td", {}, personOf(a.by)), h("td", {}, a.owners.map(personOf).join(", "))))));
    else ov.append(h("div", { class: "note" }, "Nobody is waiting to confirm a decision made for them."));
    if (P.overrides.length) ov.append(h("h2", { style: "margin-top:16px" }, "Rules skipped on purpose", h("span", { class: "sub" }, String(P.overrides.length))),
      h("table", { class: "t" }, h("tr", {}, h("th", {}, "On"), h("th", {}, "Rule skipped"), h("th", {}, "By"), h("th", {}, "Reason")),
        P.overrides.map((o) => h("tr", { class: "click", onclick: () => go(o.key, { reset: true }) }, h("td", {}, refChip(o.key)), h("td", { title: o.rules.join(", ") }, (o.skipped || o.rules).join(", ")),
          h("td", {}, `${personOf(o.by)}, ${isDate(o.date) ? day(o.date) : o.date}`), h("td", { class: "authored" }, unmarked(o.reason))))));
    sc.append(ov);
  }
  function handoff(x) {
    if (!x.manifest && !x.handedOff) return h("span", { class: "muted" }, "not handed to a team yet");
    const out = h("div", {});
    if (x.handedOff) out.append(h("div", {}, personOf(x.handedOff).replace(/\b\d{4}-\d{2}-\d{2}\b/g, (iso) => day(iso))));  // dates in words, as everywhere else
    if (!x.manifest) out.append(h("div", { class: "muted" }, "no handoff record written yet"));
    else if (x.problem) out.append(h("div", { class: "gap" }, "the handoff record can't be read: " + x.problem));
    else {
      const drift = x.changed + x.removed;
      out.append(h("div", { class: drift ? "gap" : "muted" }, drift ? `${x.changed} changed, ${x.removed} removed since the team's lead accepted it` : "nothing the team's lead accepted has changed", x.added ? `; ${x.added} added` : ""));
      if (x.changes && x.changes.length) out.title = x.changes.join("\n");
    }
    return out;
  }
  /* Open questions by the week they fall due. A bar takes the lamp color of its most urgent question, by attention.hold. */
  function dueChart() {
    const open = D.asks.filter((u) => u.state === "open");
    const sec = h("section", { class: "card" }, h("h2", {}, "Open questions by the week they're due", h("span", { class: "sub" }, "click a bar for the list")));
    if (!open.length) { sec.append(h("div", { class: "note" }, "No question is open.")); return sec; }
    const monday = TODAY - ((new Date(D.today + "T00:00:00Z").getUTCDay() + 6) % 7);
    const buckets = [{ label: "Overdue", ids: [] }];
    for (let w = 0; w < 10; w++) buckets.push({ label: new Date((monday + 7 * w) * DAY).toISOString().slice(5, 10).replace(/^(\d\d)-(\d\d)$/, (m, mo, d) => `${MONTHS[+mo - 1]} ${+d}`), sub: w === 0 ? "this week" : "", ids: [] });
    buckets.push({ label: "Later", ids: [] }, { label: "No date", ids: [] });
    for (const u of open) {
      if (!isDate(u.askBy)) { buckets[buckets.length - 1].ids.push(u.id); continue; }
      const d = dayNum(u.askBy);
      if (d < TODAY) { buckets[0].ids.push(u.id); continue; }
      const w = Math.floor((d - monday) / 7);
      (w < 10 ? buckets[1 + w] : buckets[buckets.length - 2]).ids.push(u.id);
    }
    const W = 900, H = 190, pad = 30, bw = (W - pad) / buckets.length, max = Math.max(...buckets.map((b) => b.ids.length), 1);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H + 36}`, class: "due-chart" });
    const key = Legend.open("progress-due", { root: () => sec, probes: { ...Legend.lampProbes((lv) => `rect.bar-r.${lv}`), "pg.fade": 'rect.bar-r:not([opacity="1.00"])' } });
    for (let g = 0; g <= max; g += Math.max(1, Math.ceil(max / 4))) {
      const y = H - ((H - 20) * g) / max;
      s("line", { x1: pad, x2: W, y1: y, y2: y, stroke: Theme.c("rule") }, svg);
      s("text", { x: pad - 6, y: y + 4, "text-anchor": "end", class: "axis" }, svg).textContent = g;
    }
    const listBox = h("div", {});
    buckets.forEach((b, i) => {
      const x = pad + i * bw + 4, bh = ((H - 20) * b.ids.length) / max;
      if (b.ids.length) {
        const lit = b.ids.map((id) => ASK[id].light).sort((p, q) => rank(q.level) - rank(p.level) || q.urgency - p.urgency)[0];
        const color = LIGHT[lit.level].color, op = lit.level === "warning" ? 1 : 0.35 + 0.65 * lit.urgency;
        const r = s("rect", { x, y: H - bh, width: bw - 8, height: bh, rx: 4, fill: color, opacity: op.toFixed(2), class: "bar-r " + lit.level }, svg);
        key.saw("lamp." + lit.level); if (op < 1) key.saw("pg.fade");
        r.addEventListener("mousemove", (ev) => showTip(ev, `<b>${esc(b.label)}${b.sub ? " (" + b.sub + ")" : ""}: ${b.ids.length}</b>${esc(b.ids.join(", "))}`));
        r.addEventListener("mouseleave", hideTip);
        const week = `${b.label}${b.sub ? " (" + b.sub + ")" : ""}`;
        const note = Nodes.note({ diagram: "Open questions by week", name: week, kind: "Questions due in this bucket", text: `${plural(b.ids.length, "open question")} fall${b.ids.length === 1 ? "s" : ""} due in ${week.toLowerCase().startsWith("overdue") || week === "Later" || week === "No date" ? week.toLowerCase() : "the week starting " + week}. The bar takes the color of the most urgent.`, stands: b.ids });
        Nodes.wire(r, { label: `${week}: ${plural(b.ids.length, "open question")}`, open: () => { hideTip(); listBox.innerHTML = ""; listBox.append(h("div", { class: "note" }, h("b", {}, `${b.label}: `), b.ids.map((id) => refChip(id)))); go(note, { reset: true }); } });
        s("text", { x: x + (bw - 8) / 2, y: H - bh - 6, "text-anchor": "middle", class: "bar-n" }, svg).textContent = b.ids.length;
      }
      s("text", { x: x + (bw - 8) / 2, y: H + 16, "text-anchor": "middle", class: "axis" + (i === 0 ? " warn" : "") }, svg).textContent = b.label;
      if (b.sub) s("text", { x: x + (bw - 8) / 2, y: H + 30, "text-anchor": "middle", class: "axis faint" }, svg).textContent = b.sub;
    });
    s("line", { x1: pad, x2: W, y1: H, y2: H, stroke: Theme.c("rule-3") }, svg);
    sec.append(h("div", { class: "chart" }, svg), key.el(), listBox);
    key.paint();
    return sec;
  }
  return { render };
})();
View("progress", { label: "Progress", title: "The stage ladder, how much is written down and what is due", render: ProgressView.render });
