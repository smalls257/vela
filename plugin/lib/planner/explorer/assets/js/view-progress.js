/* Progress: where each app stands on the stage ladder, how complete the design is by the planner's five measures,
   what is due when, and what still waits on someone. These are the numbers planner status and planner next compute
   (progress.grid, progress.best, completeness.measure, override, handoff); the page only draws them. */
const ProgressView = (() => {
  const MIX = ["inkling", "assumption", "fact", "decided"].map((s) => [s, `var(--mix-${s})`]);
  const { bx } = Legend;
  const step = (o) => bx({ y: 5, height: 6, rx: 2, width: 8, ...o });
  Legend.define("pg.done", [step({ x: 3, fill: "ink-3" }), step({ x: 13, fill: "ink-3" })], "Grey step: a stage the app has already passed");
  Legend.define("pg.cur", [step({ x: 12, fill: "ink" })], "Bright step: the stage the app is at");
  Legend.define("pg.reach", [step({ x: 12, fill: "deck-3", stroke: "ink-2", w: 1.4 })], "Ringed step: how far its pages already reach, ahead of the recorded stage");
  Legend.define("pg.empty", [step({ x: 12, fill: "deck-3" })], "Empty step: a stage still to come");
  Legend.define("pg.off", [step({ x: 12, fill: "deck" })], "Dim steps: outside the ladder, so no stage applies");
  const MIX_SAY = { inkling: "a hunch", assumption: "believed but not checked", fact: "has a source", decided: "came out of a Grill session" };
  for (const [state, colour] of MIX) Legend.define("pg.mix." + state, [{ k: "box", y: 5, height: 6, rx: 2, fill: `mix-${state}` }], `${state[0].toUpperCase() + state.slice(1)}: ${MIX_SAY[state]}`);
  Legend.define("pg.fade", [bx({ fill: "caution", opacity: 0.4, x: 11, y: 2, width: 12, height: 12, rx: 3 })], "Paler bar: the most urgent question is some way off; bars strengthen as they fall due");
  function render(main) {
    const P = D.progress, sc = h("div", { class: "scroll pages" });
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Progress"),
      h("p", {}, "Where each app stands on the stage ladder, how complete the design is by the planner's five measures, and what still waits on someone. The numbers are planner status's and planner next's."))), sc);
    const totals = [0, 0, 0, 0];
    P.rows.forEach((r) => r.mix.forEach((n, i) => { totals[i] += n; }));
    const ring = (pct) => {
      const C = 2 * Math.PI * 52, svg = s("svg", { viewBox: "0 0 128 128", class: "kpi-ring" });
      s("circle", { cx: 64, cy: 64, r: 52, fill: "none", stroke: Theme.c("rule"), "stroke-width": 12 }, svg);
      const arc = s("circle", { cx: 64, cy: 64, r: 52, fill: "none", stroke: Theme.c("ink"), "stroke-width": 12, "stroke-linecap": "round", transform: "rotate(-90 64 64)", "stroke-dasharray": C, "stroke-dashoffset": reducedMotion() ? C * (1 - pct / 100) : C }, svg);
      if (!reducedMotion()) requestAnimationFrame(() => requestAnimationFrame(() => { arc.style.transition = "stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1)"; arc.setAttribute("stroke-dashoffset", C * (1 - pct / 100)); }));
      s("text", { x: 64, y: 72, "text-anchor": "middle", class: "kpi-num" }, svg).textContent = pct + "%";
      return svg;
    };
    sc.append(h("section", { class: "card kpis" },
      h("div", { class: "kpi-big" }, ring(P.percent), h("div", { class: "lab" }, h("b", {}, "Completeness"), "The mean of the five shares. It never means done; it counts only what is written down.")),
      h("div", { class: "shares" }, P.shares.map((x) => h("div", { class: "share" }, h("span", {}, x.name), h("div", { class: "bar" }, h("span", { style: `width:${x.total ? ((100 * x.done) / x.total).toFixed(1) : 100}%` })), h("span", { class: "v" }, `${x.done} of ${x.total}`)))),
      h("div", { class: "tiles" }, [3, 2, 1, 0].map((i) => h("div", { class: "tile" }, h("div", { class: "num" }, totals[i]), h("div", { class: "lab" }, h("i", { class: "sw", style: `background:${MIX[i][1]}` }), MIX[i][0])))),
      P.next ? h("div", { class: "note next" }, h("b", {}, "Planner's next step: "), `${P.next.mode} `, P.next.subject ? refChip(keyForId(P.next.subject)) : null, " ", P.next.reason) : null));
    const tableKey = Legend.open("progress-table", { root: () => tableCard, probes: { "pg.done": ".ladder .done", "pg.cur": ".ladder .cur", "pg.reach": ".ladder .reach", "pg.empty": ".ladder:not(.off) span:not(.done):not(.cur):not(.reach)",
      "pg.off": ".ladder.off", ...Object.fromEntries(MIX.map(([state]) => ["pg.mix." + state, `.mix span[style*="--mix-${state}"]`])) } });
    const table = h("table", { class: "t" }, h("tr", {}, h("th", {}, "App"), h("th", {}, "Light"), h("th", {}, "Stage"), h("th", {}, "States"), h("th", {}, "Next, by planner's rule"), h("th", {}, "Handoff"), h("th", {}, "Team design")));
    for (const r of P.rows) {
      const a = E[r.app], ad = D.apps[r.app], idx = P.stages.indexOf(r.stage), reach = P.stages.indexOf(ad.reached), lv = levelOf(r.app);
      if (r.stage) {
        if (idx > 0) tableKey.saw("pg.done");
        tableKey.saw("pg.cur");
        if (reach > idx) tableKey.saw("pg.reach");
        if (P.stages.some((x, i) => i > idx && !(i === reach && reach > idx))) tableKey.saw("pg.empty");
      } else tableKey.saw("pg.off");
      r.mix.forEach((n, i) => { if (n) tableKey.saw("pg.mix." + MIX[i][0]); });
      const caption = r.stage ? `at ${r.stage}` + (reach > idx ? `; its pages already reach ${ad.reached}` : "") : `${a.change || "no change"}: outside the ladder`;
      table.append(h("tr", { class: "click", onclick: () => go(r.app, { reset: true }) },
        h("td", {}, h("b", {}, a.title), h("div", { class: "muted" }, a.change || "")),
        h("td", {}, lampEl(lv), " ", h("span", { class: "muted" }, LIGHT[lv].word)),
        h("td", {}, h("div", { class: "ladder" + (r.stage ? "" : " off") }, P.stages.map((x, i) => h("span", { class: r.stage ? (i < idx ? "done" : i === idx ? "cur" : "") + (i === reach && reach > idx ? " reach" : "") : "", title: x }))), h("div", { class: "muted small" }, caption)),
        h("td", {}, h("div", { class: "mix", title: r.mix.map((n, i) => `${n} ${MIX[i][0]}`).join(", ") }, r.mix.map((n, i) => (n ? h("span", { style: `flex:${n};background:${MIX[i][1]}` }) : null))),
          h("div", { class: "muted small" }, [3, 2, 1, 0].filter((i) => r.mix[i]).map((i) => `${r.mix[i]} ${MIX[i][0]}`).join(", ") || "nothing yet", r.byOverride ? ` (${r.byOverride} decided by override)` : "")),
        h("td", { class: "wide" }, h("b", {}, r.mode === "none" ? "nothing to run" : r.mode), h("div", { class: "muted small" }, r.reason), r.oldest ? h("div", { class: "small" }, h("span", { class: "muted" }, "oldest blocker: "), refChip(r.oldest)) : null),
        h("td", { class: "small" }, handoff(r.handoff)), h("td", { class: "small" }, Inside.statusCell(r.app))));
    }
    const tableCard = h("section", { class: "card" }, h("h2", {}, "Each app on the ladder", h("span", { class: "sub" }, `${P.stages.join(" → ")}; filled to the recorded stage, a ringed step is where the pages already reach`)), table, tableKey.el());
    sc.append(tableCard);
    tableKey.paint();
    sc.append(dueChart());
    const ov = h("section", { class: "card" }, h("h2", {}, "Overrides awaiting confirmation"));
    if (P.awaiting.length) ov.append(h("table", { class: "t" }, h("tr", {}, h("th", {}, "On"), h("th", {}, "Decided by"), h("th", {}, "On behalf of, not yet confirmed")),
      P.awaiting.map((a) => h("tr", { class: "click", onclick: () => go(a.key, { reset: true }) }, h("td", {}, refChip(a.key)), h("td", {}, a.by), h("td", {}, a.owners.join(", "))))));
    else ov.append(h("div", { class: "note" }, "None. No decision made on someone's behalf is waiting for their confirmation."));
    if (P.overrides.length) ov.append(h("h2", { style: "margin-top:16px" }, "Overrides recorded", h("span", { class: "sub" }, String(P.overrides.length))),
      h("table", { class: "t" }, h("tr", {}, h("th", {}, "On"), h("th", {}, "Rules"), h("th", {}, "By"), h("th", {}, "Reason")),
        P.overrides.map((o) => h("tr", { class: "click", onclick: () => go(o.key, { reset: true }) }, h("td", {}, refChip(o.key)), h("td", {}, o.rules.join(", ")), h("td", {}, `${o.by}, ${o.date}`), h("td", {}, o.reason)))));
    sc.append(ov);
  }
  function handoff(x) {
    if (!x.manifest && !x.handedOff) return h("span", { class: "muted" }, "not handed off");
    const out = h("div", {});
    if (x.handedOff) out.append(h("div", {}, x.handedOff));
    if (!x.manifest) out.append(h("div", { class: "muted" }, "no manifest in handoffs/"));
    else if (x.problem) out.append(h("div", { class: "gap" }, "manifest unreadable: " + x.problem));
    else {
      const drift = x.changed + x.removed;
      out.append(h("div", { class: drift ? "gap" : "muted" }, drift ? `${x.changed} changed, ${x.removed} removed since the senior accepted it` : "nothing the senior accepted has changed", x.added ? `; ${x.added} added` : ""));
      if (x.changes && x.changes.length) out.title = x.changes.join("\n");
    }
    return out;
  }
  /* Open questions by the week they fall due. A bar takes the lamp colour of its most urgent question, by attention.hold. */
  function dueChart() {
    const open = D.asks.filter((u) => u.state === "open");
    const sec = h("section", { class: "card" }, h("h2", {}, "Open questions by the week they are due", h("span", { class: "sub" }, `${open.length} open; weeks start on Monday; click a bar for its list`)));
    if (!open.length) { sec.append(h("div", { class: "note" }, "No question is open.")); return sec; }
    const monday = TODAY - ((new Date(D.today + "T00:00:00Z").getUTCDay() + 6) % 7);
    const buckets = [{ label: "Overdue", ids: [] }];
    for (let w = 0; w < 10; w++) buckets.push({ label: new Date((monday + 7 * w) * DAY).toISOString().slice(5, 10).replace(/^(\d\d)-(\d\d)$/, (m, mo, d) => `${+d} ${MONTHS[+mo - 1]}`), sub: w === 0 ? "this week" : "", ids: [] });
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
        const colour = LIGHT[lit.level].colour, op = lit.level === "warning" ? 1 : 0.35 + 0.65 * lit.urgency;
        const r = s("rect", { x, y: H - bh, width: bw - 8, height: bh, rx: 4, fill: colour, opacity: op.toFixed(2), class: "bar-r " + lit.level }, svg);
        key.saw("lamp." + lit.level); if (op < 1) key.saw("pg.fade");
        r.addEventListener("mousemove", (ev) => showTip(ev, `<b>${esc(b.label)}${b.sub ? " (" + b.sub + ")" : ""}: ${b.ids.length}</b>${esc(b.ids.join(", "))}`));
        r.addEventListener("mouseleave", hideTip);
        const week = `${b.label}${b.sub ? " (" + b.sub + ")" : ""}`;
        const note = Nodes.note({ diagram: "Open questions by week", name: week, kind: "Questions due in this bucket", text: `${plural(b.ids.length, "open question")} fall${b.ids.length === 1 ? "s" : ""} due in ${week.toLowerCase().startsWith("overdue") || week === "Later" || week === "No date" ? week.toLowerCase() : "the week starting " + week}. The bar takes the colour of the most urgent.`, stands: b.ids });
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
View("progress", { label: "Progress", title: "The stage ladder, completeness and what is due", render: ProgressView.render, count: () => D.progress.percent + "%" });
