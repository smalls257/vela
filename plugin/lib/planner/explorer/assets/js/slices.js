/* Slices: the unit of done, one row each, from planner.slices (slices_data.py). A row shows where the slice stands as
   pills across the five statuses, the flows it proves and the joins it crosses as chips, and an arrow from each slice
   it comes after. Every part a reader can point at goes through Nodes.wire, so it opens the panel by click and by
   Enter: the slice to its page, a flow to the flow, a join to its contract, a slice it comes after to that slice. A
   vault that still names its slices on the releases page shows them too, and says so. */
const Slices = (() => {
  const P = D.slicePlan, LIST = P.list, BY = Object.fromEntries(LIST.map((x) => [x.slice, x]));
  const STATUS_SAY = { planned: "the lead planned it in a Grill", building: "the teams accepted their parts", "journey passes": "the journey ran green",
    "live but off": "deployed with its switch off", on: "someone switched it on" };
  const { bx, ln } = Legend;
  Legend.define("sl.on", [bx({ fill: "ink", rx: 7 })], "Filled pill: where the slice stands now");
  Legend.define("sl.past", [bx({ fill: "deck-3", stroke: "ink-3", w: 1.4, rx: 7 })], "Outlined pill: a status it has passed");
  Legend.define("sl.ahead", [bx({ stroke: "rule-3", w: 1.2, rx: 7, dash: "2 2" })], "Dashed pill: a status still ahead");
  Legend.define("sl.none", [bx({ stroke: "ink-4", w: 1.2, rx: 7 })], "Not planned yet: no Grill has planned the slice");
  Legend.define("sl.after", [ln({ stroke: "ink-3", w: 1.6, head: "fill" })], "Arrow: the slice it points at comes after the one it starts from");
  Legend.define("sl.tracer", [bx({ fill: "caution", opacity: 0.35, stroke: "caution", w: 1, rx: 7 })], "Tracer: the first slice, built first and kept");
  Legend.define("sl.circle", [bx({ stroke: "warning", w: 2, rx: 3 })], "Red edge: slices that come after each other in a circle, so none can start");
  const PROBES = { "sl.on": ".sl-pill.on", "sl.past": ".sl-pill.past", "sl.ahead": ".sl-pill.ahead", "sl.none": ".sl-pill.none",
    "sl.after": ".sl-arrows path.sl-after", "sl.tracer": ".sl-row .tracer-tag", "sl.circle": ".sl-row.circled" };
  const st = { pick: "" };
  let KEY = null;

  const rank = (status) => P.statuses.indexOf(status);
  /* The panel key for a slice: its page, or a note when it is read from the releases page and has no page of its own. */
  function keyOf(x) {
    if (x.key && E[x.key]) return { key: x.key };
    return { note: Nodes.note({ diagram: "Slices", name: x.name, kind: "Slice, named on the releases page",
      text: "This vault still names its slices on the releases page. Each gets a page of its own in slices/, with a status, what it comes after and the joins it crosses.",
      facts: [["Flows", x.flows.map((f) => f.id).join(", ") || "none"], ...(x.after.length ? [["After", x.after.join(", ")]] : [])],
      relates: [x.page, ...x.flows.map((f) => f.key)].filter(Boolean) }) };
  }
  const nameOf = (k) => (BY[k] ? BY[k].name : k);
  function chip(label, id, spec, cls) {
    const el = h("span", { class: "chip sl-chip " + cls }, label, id && id !== label ? idTag(id) : null);
    return Nodes.wire(el, { label: id && id !== label ? `${label} (${id})` : label, ...spec });
  }
  function flowChip(f) {
    if (f.key && E[f.key]) return chip(E[f.key].title, f.id, { key: f.key }, "sl-flow");
    return chip(f.id, "", { note: Nodes.note({ diagram: "Slices", name: f.id, kind: "Flow with no page", text: `The slice names ${f.id}, and this vault has no flow page for it.` }) }, "sl-flow gap");
  }
  function joinChip(j) {
    if (j.key && E[j.key]) return chip(E[j.key].title, j.id, { key: j.key }, "sl-join");
    return chip(j.id, "", { note: Nodes.note({ diagram: "Slices", name: j.id, kind: "Join with no contract", text: `The slice names ${j.id}, and this vault has no contract by that ID.` }) }, "sl-join gap");
  }
  function afterChip(k) {
    const x = BY[k];
    if (!x) return chip(k, "", { note: Nodes.note({ diagram: "Slices", name: k, kind: "Slice with no page", text: `The slice comes after ${k}, and this vault has no slice by that name.` }) }, "sl-afterchip gap");
    return chip(x.name, x.id, keyOf(x), "sl-afterchip");
  }
  function pills(x) {
    const at = rank(x.status), out = [];
    if (at < 0) out.push(h("span", { class: "sl-pill none", title: x.statusRaw ? `Status says "${x.statusRaw}", which is not one of the five` : "No Grill has planned it yet" }, x.statusRaw ? `"${x.statusRaw}"?` : "not planned yet"));
    P.statuses.forEach((s, i) => out.push(h("span", { class: "sl-pill " + (i === at ? "on" : i < at ? "past" : "ahead"), title: `${s}: ${STATUS_SAY[s]}` }, s)));
    return h("div", { class: "sl-pills", role: "list", "aria-label": `Status: ${x.status || "not planned yet"}` }, out);
  }
  const line = (label, kids) => (kids && kids.length ? h("div", { class: "sl-line" }, h("span", { class: "sl-l" }, label), h("span", { class: "sl-v" }, kids)) : null);
  function row(x) {
    const headSpec = keyOf(x);
    const head = h("div", { class: "sl-head" }, h("span", { class: "sl-name" }, x.name), idTag(x.id),
      x.tracer ? h("span", { class: "tracer-tag", title: "The first slice: one thin path through every app, built first and kept" }, "tracer") : null);
    Nodes.wire(head, { label: x.label, ...headSpec });
    const facts = [x.doneWhen ? h("div", { class: "sl-fact" }, h("b", {}, "Done when: "), x.doneWhen) : null,
      x.shipsOff ? h("div", { class: "sl-fact" }, h("b", {}, "Ships switched off: "), x.shipsOff) : null,
      x.journey && !x.journey.problem ? h("div", { class: "sl-fact" }, h("b", {}, "Journey: "), `passed ${day(x.journey.date)} by ${x.journey.by}`) : null,
      x.milestones.length ? h("div", { class: "sl-fact" }, h("b", {}, "Milestone: "), x.milestones.join("; ")) : null].filter(Boolean);
    return h("section", { class: "sl-row" + (x.circled ? " circled" : "") + (st.pick === x.slice || (x.key && App.focus === x.key) ? " on" : ""), "data-slice": x.slice },
      head, pills(x),
      line("Flows", x.flows.length ? x.flows.map(flowChip) : [h("span", { class: "gap small" }, x.flowsNone ? `none: ${x.flowsNone}` : "names no flows")]),
      line("Joins", x.joins.map(joinChip)),
      line("After", x.after.map(afterChip)),
      facts.length ? h("div", { class: "sl-facts" }, facts) : null);
  }
  /* Depth: how many slices stand before it, so the arrows fan out in the gutter instead of lying on top of each other. */
  function depthOf(x, seen = new Set()) {
    if (seen.has(x.slice)) return 0;
    seen.add(x.slice);
    return x.after.reduce((d, k) => (BY[k] ? Math.max(d, 1 + depthOf(BY[k], seen)) : d), 0);
  }
  function arrows(list, svg) {
    svg.replaceChildren();
    const marker = s("marker", { id: "sl-head", viewBox: "0 0 8 8", refX: 7, refY: 4, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, s("defs", {}, svg));
    s("path", { d: "M0 0L8 4L0 8Z", class: "sl-head" }, marker);
    const top = list.getBoundingClientRect().top, rows = Object.fromEntries($$(".sl-row", list).map((r) => [r.dataset.slice, r]));
    const mid = (el) => { const r = $(".sl-head", el).getBoundingClientRect(); return r.top - top + r.height / 2; };
    let lane = 0;
    for (const x of LIST) for (const k of x.after) {
      if (!rows[k] || !rows[x.slice]) continue;
      const y1 = mid(rows[k]), y2 = mid(rows[x.slice]), gx = 46, bend = 10 + 9 * (lane++ % 3);
      s("path", { class: "sl-after", d: `M${gx} ${y1}C${gx - bend - 14} ${y1} ${gx - bend - 14} ${y2} ${gx - 2} ${y2}`, "marker-end": "url(#sl-head)" }, svg);
      KEY.saw("sl.after");
    }
    svg.setAttribute("height", list.scrollHeight);
  }
  function body(box) {
    box.innerHTML = "";
    KEY = Legend.open("slices", { root: () => box, probes: PROBES });
    if (!LIST.length) {
      box.append(emptyState("No slices yet.", "A slice is one journey proven end to end; each gets a page in slices/, the tracer first as SLC-001.", "/planner:releases"));
      return;
    }
    if (!P.onPages) box.append(h("p", { class: "note sl-old" }, "These slices are still named on the releases page. Each gets a page of its own in slices/, with a status, what it comes after and the joins it crosses."));
    const list = h("div", { class: "sl-list" }), svg = s("svg", { class: "sl-arrows", width: 48, "aria-hidden": "true" });
    list.append(svg, ...LIST.map(row));
    box.append(list, KEY.el());
    for (const x of LIST) {
      const at = rank(x.status);
      KEY.saw(at < 0 ? "sl.none" : "sl.on");
      if (at > 0) KEY.saw("sl.past");
      if (at < P.statuses.length - 1) KEY.saw("sl.ahead");
      if (x.tracer) KEY.saw("sl.tracer");
      if (x.circled) KEY.saw("sl.circle");
    }
    const draw = () => { if (list.isConnected) { arrows(list, svg); KEY.paint(); } };
    requestAnimationFrame(draw);
    draw();
    if (typeof ResizeObserver !== "undefined") new ResizeObserver(draw).observe(list);
  }
  function render(main) {
    const n = LIST.length, moving = LIST.filter((x) => rank(x.status) >= 1).length;
    const title = typeof Nav !== "undefined" ? Nav.title("Slices") : "Slices";
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, title),
      h("p", {}, n ? `${plural(n, "slice")}, ${moving ? `${moving} building or further along` : "none building yet"}. Each is one journey, done when it passes and switched on when someone decides. An arrow points from a slice to the one that comes after it.` : "Slices are the unit of done.")),
      h("div", { class: "spacer" }), typeof Nav !== "undefined" ? Nav.pageActions() : null));
    const box = h("div", { class: "sl-body scroll", id: "board" });
    main.append(box);
    body(box);
  }
  function highlight(key) {
    const x = LIST.find((y) => y.key === key);
    st.pick = x ? x.slice : "";
    $$(".sl-row").forEach((r) => r.classList.toggle("on", r.dataset.slice === st.pick));
    const el = st.pick && $(`.sl-row[data-slice="${CSS.escape(st.pick)}"]`);
    if (el) el.scrollIntoView({ block: "nearest" });
  }
  /* The panel's part for a slice page: where it stands, and the parts of it, each a chip to its own page. */
  function panelPart(key) {
    const x = LIST.find((y) => y.key === key);
    if (!x) return [];
    const chips = (list, fn) => h("div", {}, list.map(fn));
    return [Panel.section("Where it stands", null, h("div", {}, h("span", { class: "pill" }, x.status || "not planned yet"),
        x.journey && !x.journey.problem ? h("span", { class: "muted small" }, ` journey passed ${day(x.journey.date)} by ${x.journey.by}`) : null,
        h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => { Nav.open("slices", key); } }, "Show it among the slices")))),
      x.flows.length ? Panel.section("Flows it proves", x.flows.length, chips(x.flows, (f) => (f.key ? refChip(f.key) : h("span", { class: "ref-chip ref-dead" }, f.id)))) : null,
      x.joins.length ? Panel.section("Joins it crosses", x.joins.length, chips(x.joins, (j) => (j.key ? refChip(j.key) : h("span", { class: "ref-chip ref-dead" }, j.id)))) : null,
      x.after.length ? Panel.section("Comes after", x.after.length, chips(x.after, (k) => (BY[k] && BY[k].key ? refChip(BY[k].key) : h("span", { class: "ref-chip ref-dead" }, nameOf(k))))) : null,
      x.notIn.length ? Panel.section("Not in this slice", x.notIn.length, h("ul", { class: "mini-list" }, x.notIn.map((l) => h("li", {}, l.text)))) : null].filter(Boolean);
  }
  return { render, highlight, panelPart, LIST, st };
})();
View("slices", { label: "Slices", title: "Each slice: one journey proven end to end, and where it stands", render: Slices.render, highlight: Slices.highlight, count: () => String(D.slicePlan.list.length) });
