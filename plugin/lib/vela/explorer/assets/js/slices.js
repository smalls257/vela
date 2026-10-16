/* Slices: the unit of done, from vela.slices (slices_data.py), in one of two layouts the reader picks (Table, Path;
   the choice is kept in this browser, like the build plan's List / Cards / Path).

   Table is for finding one slice fast in a live call: a row each with its name, where it stands, what it comes after
   and whether it needs you; a row is a button that folds open to its flows, its joins with both sides, its journey or
   the date it is due, what is left out of it, and its flow check with any overrides. Path is for the planning talk:
   what comes after what, drawn as boxes whose edge is the status color, an arrow for "comes after", and slices side by
   side when they can be built at the same time.

   Why the search and filters live here and in the address bar: under pressure a lead says "show me what's building for
   Kiosks", and the answer has to be two clicks and a link that opens the same view for someone else. Both layouts read
   one filter state, so a filter can never show one set of slices in the table and another on the path. The hash carries
   the filters (sl-find, sl-status, sl-app, sl-milestone, sl-needs, sl-layout); a value the vault no longer has is kept and
   shown as a pressed chip with a count of 0, never dropped, so a stale link says why it is empty instead of quietly
   showing everything. Every name goes through Nodes.wire, so it opens the panel by click and by Enter. */
const Slices = (() => {
  const P = D.slicePlan, LIST = P.list, BY = Object.fromEntries(LIST.map((x) => [x.slice, x]));
  const LAYOUT_KEY = "explorer.slices.layout", LAYOUTS = [["table", "Table"], ["path", "Path"]];
  const NOT_PLANNED = "not planned yet", NO_MILESTONE = "no milestone";
  const STATUS_SAY = { [NOT_PLANNED]: "nobody has planned it yet", planned: "the lead planned it in a working session", building: "the teams accepted their parts",
    "journey passes": "the journey was tried end to end and worked", "live but off": "released with its switch off", on: "someone switched it on for users" };
  /* The words a reader sees for each status; the values stay the plan's own, so links and filters keep working. */
  const STATUS_WORD = { [NOT_PLANNED]: "not planned yet", planned: "planned", building: "building", "journey passes": "tested end to end", "live but off": "released, switched off", on: "switched on" };
  const statusWord = (s) => STATUS_WORD[s] || s;
  const STATUS_CLASS = { [NOT_PLANNED]: "none", planned: "planned", building: "building", "journey passes": "passes", "live but off": "off", on: "on" };
  const ORDER = [NOT_PLANNED, ...P.statuses];
  const GROUPS = [["status", "Status", "sl-status"], ["app", "Team", "sl-app"], ["milestone", "Milestone", "sl-milestone"]];
  const st = { pick: "", open: new Set(), find: "", status: new Set(), app: new Set(), milestone: new Set(), needs: false, layout: null };
  const statusOf = (x) => x.status || NOT_PLANNED;
  const layoutNow = () => { const v = st.layout || Settings.read(LAYOUT_KEY); return LAYOUTS.some(([id]) => id === v) ? v : "table"; };

  /* ------------------------------------------------------------ the key */
  const { bx, ln } = Legend;
  const EDGE = { none: "ink-4", planned: "ink-3", building: "mix-assumption", passes: "mix-fact", off: "heuristic-ink", on: "ink" };
  for (const s of ORDER) {
    const c = STATUS_CLASS[s], o = { stroke: EDGE[c], w: c === "on" ? 2.6 : 2, rx: 4, ...(c === "none" ? { dash: "3 2" } : {}) };
    Legend.define("sl.st." + c, [bx(o)], `${statusWord(s)[0].toUpperCase()}${statusWord(s).slice(1)}: ${STATUS_SAY[s]}`);
  }
  Legend.define("sl.after", [ln({ stroke: "ink-3", w: 1.6, head: "fill" })], "Arrow: the slice it points at comes after the one it starts from");
  Legend.define("sl.parallel", [bx({ x: 2, width: 13, stroke: "ink-3", w: 1.2, rx: 3 }), bx({ x: 19, width: 13, stroke: "ink-3", w: 1.2, rx: 3 })],
    "Side by side: slices that can be built at the same time");
  Legend.define("sl.tracer", [bx({ fill: "caution", opacity: 0.35, stroke: "caution", w: 1, rx: 7 })], termTip("tracer"));
  Legend.define("sl.circle", [bx({ stroke: "warning", w: 2, rx: 3 })], "Red edge: slices that come after each other in a circle, so none can start");
  Legend.define("sl.due", [bx({ fill: "warning", opacity: 0.3, rx: 7 })], "Journey due: the date has passed and nobody has recorded trying it, so it needs you");
  const PROBES = Object.fromEntries([
    ...ORDER.map((s) => { const c = STATUS_CLASS[s]; return ["sl.st." + c, `.sl-st.st-${c}, .sl-node.st-${c}`]; }),
    ["sl.after", ".sl-path-arrows path.sl-after"], ["sl.parallel", ".sl-level.parallel"], ["sl.tracer", ".tracer-tag"],
    ["sl.circle", ".sl-tr.circled, .sl-node.circled"], ["sl.due", ".sl-due"]]);
  let KEY = null;
  function sawRow(x) {
    KEY.saw("sl.st." + STATUS_CLASS[statusOf(x)]);
    if (x.tracer) KEY.saw("sl.tracer");
    if (x.circled) KEY.saw("sl.circle");
    if (x.overdue) KEY.saw("sl.due");
  }

  /* ------------------------------------------------------------ names that open the panel */
  /* The panel key for a slice: its page, or a note when it is read from the releases page and has no page of its own. */
  function keyOf(x) {
    if (x.key && E[x.key]) return { key: x.key };
    return { note: Nodes.note({ diagram: "Slices", name: x.name, kind: "Slice, named on the releases page",
      text: "Each slice gets its own page once the releases session runs again.",
      facts: [["Flows", x.flows.map((f) => f.id).join(", ") || "none"], ...(x.after.length ? [["After", x.after.join(", ")]] : [])],
      relates: [x.page, ...x.flows.map((f) => f.key)].filter(Boolean) }) };
  }
  const nameOf = (k) => (BY[k] ? BY[k].name : k);
  const APP_BY_NAME = Object.fromEntries(D.map.apps.map((a) => [titleOf(a.key).toLowerCase(), a.key]));
  function chip(label, id, spec, cls) {
    const el = h("span", { class: "chip sl-chip " + cls }, label, id && id !== label ? idTag(id) : null);
    return Nodes.wire(el, { label: id && id !== label ? `${label} (${id})` : label, stop: true, ...spec });
  }
  const missing = (name, kind, text) => ({ note: Nodes.note({ diagram: "Slices", name, kind, text }) });
  function flowChip(f) {
    if (f.key && E[f.key]) return chip(E[f.key].title, f.id, { key: f.key }, "sl-flow");
    return chip(f.id, "", missing(f.id, "Flow with no page", `The slice names ${f.id}, and the plan has no flow page for it.`), "sl-flow gap");
  }
  function sideChip(side) {
    if (!side) return h("span", { class: "muted" }, "no one named");
    const app = APP_BY_NAME[side.toLowerCase()];
    if (app) return chip(side, "", { key: app }, "sl-side");
    return chip(side, "", missing(side, "Outside company", `A step of this slice's flows names ${side} on one side of a contract. It has no app page in the plan.`), "sl-side");
  }
  function joinItem(j) {
    const head = j.key && E[j.key] ? chip(E[j.key].title, j.id, { key: j.key }, "sl-join")
      : chip(j.id, "", missing(j.id, "Contract not in the plan", `A flow step names ${j.id}, and the plan has no contract by that ID.`), "sl-join gap");
    return h("span", { class: "sl-joinitem" }, head, j.from || j.to ? h("span", { class: "sl-sides", title: "Who sends and who receives, as the flow step names them" }, sideChip(j.from), "→", sideChip(j.to)) : null);
  }
  function afterChip(k) {
    const x = BY[k];
    if (!x) return chip(k, "", missing(k, "Slice with no page", `The slice comes after ${k}, and the plan has no slice by that name.`), "sl-afterchip gap");
    return Nodes.wire(h("span", { class: "chip sl-chip sl-afterchip", title: x.id || null }, x.name), { label: x.label, stop: true, ...keyOf(x) });  // the ID in the tooltip: a narrow cell has no room for it
  }
  /* A person by the name the vault gives the role, else the handle in words; the handle itself rides in the tooltip. */
  const personWords = (handle) => (D.owners[handle] && D.owners[handle].names[0]) || String(handle).replace(/^@/, "").replace(/^[^/]*\//, "").replace(/-/g, " ");
  function ownerChip(handle) {
    const el = D.owners[handle] ? chip(personWords(handle), "", { key: "owner:" + handle }, "sl-owner")
      : chip(personWords(handle), "", missing(handle, "Person", `${personWords(handle)} is named on this slice and has no page in the plan.`), "sl-owner");
    el.title = handle;
    return el;
  }
  function statusPill(x) {
    const s = statusOf(x), raw = !x.status && x.statusRaw;
    return h("span", { class: `pill sl-st st-${STATUS_CLASS[s]}`, title: raw ? `The status says "${x.statusRaw}", which isn't one the plan knows. Fix it on the slice page.` : `${statusWord(s)}: ${STATUS_SAY[s]}` }, raw ? `"${x.statusRaw}"?` : statusWord(s));
  }
  const duePill = (x) => (x.overdue ? h("span", { class: "pill sl-due", title: x.overdue }, `journey due ${isDate(x.journeyDue) ? day(x.journeyDue) : x.journeyDue}`) : null);

  /* ------------------------------------------------------------ search and filters: one state for both layouts */
  const appsOf = (x) => x.apps;
  const milestonesOf = (x) => (x.milestones.length ? x.milestones : [NO_MILESTONE]);
  const valuesOf = { status: (x) => [statusOf(x)], app: appsOf, milestone: milestonesOf };
  const words = (x) => [x.name, x.id, ...x.flows.flatMap((f) => [f.id, f.key && E[f.key] ? E[f.key].title : ""]),
    ...x.joins.flatMap((j) => [j.id, j.key && E[j.key] ? E[j.key].title : "", j.from, j.to]), ...x.apps.map(titleOf), ...x.after.map(nameOf)].join(" ").toLowerCase();
  const WORDS = Object.fromEntries(LIST.map((x) => [x.slice, words(x)]));
  const terms = () => st.find.toLowerCase().split(/\s+/).filter(Boolean);
  function matches(x, except) {
    if (terms().some((t) => !WORDS[x.slice].includes(t))) return false;
    for (const [g] of GROUPS) if (g !== except && st[g].size && !valuesOf[g](x).some((v) => st[g].has(v))) return false;
    return except === "needs" || !st.needs || !!x.overdue;
  }
  const shown = () => LIST.filter((x) => matches(x));
  const filtered = () => !!(st.find || st.needs || GROUPS.some(([g]) => st[g].size));
  function options(g) {
    const seen = new Set(LIST.flatMap(valuesOf[g]));
    const order = g === "status" ? ORDER.filter((s) => seen.has(s)) : g === "app" ? D.map.apps.map((a) => a.key).filter((k) => seen.has(k))
      : [...seen].filter((v) => v !== NO_MILESTONE).sort().concat(seen.has(NO_MILESTONE) ? [NO_MILESTONE] : []);
    return order.concat([...st[g]].filter((v) => !order.includes(v)));  // a value from a link the vault no longer has stays pressable
  }
  const labelOf = (g, v) => (g === "app" ? (ent(v) ? titleOf(v) : v) : g === "status" ? statusWord(v) : v);
  function says() {
    const parts = [];
    for (const [g, , ] of GROUPS) {
      if (!st[g].size) continue;
      const list = [...st[g]].map((v) => labelOf(g, v)), or = list.length > 1 ? `${list.slice(0, -1).join(", ")} or ${list[list.length - 1]}` : list[0];
      parts.push(g === "status" ? `status ${or}` : g === "app" ? `${or} taking part` : `milestone ${or}`);
    }
    if (st.needs) parts.push("needing you");
    if (st.find) parts.push(`the words "${st.find}"`);
    return parts.length > 1 ? `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}` : parts[0] || "";
  }
  let refresh = () => {};
  function changed() { refresh(); if (typeof Nav !== "undefined") Nav.syncHash({ replace: true }); }
  function clear() { st.find = ""; st.needs = false; for (const [g] of GROUPS) st[g].clear(); const f = $(".sl-find"); if (f) f.value = ""; changed(); }
  function filterBar() {
    const bar = h("div", { class: "sl-filters", role: "group", "aria-label": "Filter the slices" });
    for (const [g, label] of GROUPS) {
      const opts = options(g);
      if (!st[g].size && (!opts.length || (g === "app" && !LIST.some((x) => x.apps.length)) || (g === "milestone" && opts.length === 1 && opts[0] === NO_MILESTONE))) continue;
      bar.append(h("div", { class: "sl-fgroup", "data-group": g }, h("span", { class: "sl-flabel" }, label),
        opts.map((v) => {
          const n = LIST.filter((x) => matches(x, g) && valuesOf[g](x).includes(v)).length, on = st[g].has(v);
          return h("button", { class: "chip sl-fchip" + (on ? " on" : "") + (n || on ? "" : " zero"), "aria-pressed": String(on), "data-value": v,
            title: g === "app" ? `${labelOf(g, v)} takes part: a step of the slice's flows is on it, or the slice uses a contract it provides` : g === "status" ? STATUS_SAY[v] || null : null,
            onclick: () => { if (st[g].has(v)) st[g].delete(v); else st[g].add(v); changed(); } }, labelOf(g, v), h("span", { class: "ct" }, String(n)));
        })));
    }
    const late = LIST.filter((x) => matches(x, "needs") && x.overdue).length;
    bar.append(h("div", { class: "sl-fgroup", "data-group": "needs" }, h("button", { class: "chip sl-fchip" + (st.needs ? " on" : ""), "aria-pressed": String(st.needs),
      disabled: late || st.needs ? null : true, title: late ? null : "Nothing needs you here", onclick: () => { st.needs = !st.needs; changed(); } }, "Needs you only", h("span", { class: "ct" }, String(late)))));
    return bar;
  }

  /* ------------------------------------------------------------ Table */
  const line = (label, kids) => (kids && [].concat(kids).filter(Boolean).length ? h("div", { class: "sl-line" }, h("span", { class: "sl-l" }, label), h("span", { class: "sl-v" }, kids)) : null);
  function journeySays(x) {
    if (x.journey && !x.journey.problem) return [`tried end to end on ${day(x.journey.date)} by `, ownerChip(x.journey.by), x.journey.html ? h("span", { html: ", " + x.journey.html }) : null];
    if (x.journey) return [`the journey note can't be read: it ${x.journey.problem}`];
    if (x.overdue) return [h("span", { class: "sl-late" }, `was due ${(isDate(x.journeyDue) ? day(x.journeyDue) : x.journeyDue)} and nobody has tried it yet. Try it end to end, or move the date.`)];
    if (x.journeyDue) return [`due ${(isDate(x.journeyDue) ? day(x.journeyDue) : x.journeyDue)}`];
    return [h("span", { class: "muted" }, "no date to try it yet; it gets one when the slice starts building")];
  }
  function checkSays(c) {
    if (!c) return [h("span", { class: "muted" }, "not read")];
    const covered = c.covered ? `, ${plural(c.covered, "problem")} accepted for now` : "";
    if (c.status === "not run") return [h("span", { class: "muted" }, "not run yet; it runs once the slice is building")];
    if (c.status === "passes") return [`passes${covered}`];
    return [`${c.status}: ${c.open.join("; ")}${covered}`];  // each problem by its name (flowcheck.TITLES); no codes
  }
  /* The last full flow check, as recorded (flowcheck/standing.py reads the record; the page never does). A slice with
     no record, or one that changed since, says so in amber: never shown as passed. */
  function recordedSays(r) {
    if (!r) return [h("span", { class: "gap small" }, "not checked")];
    const day_ = (d) => (isDate(d) ? day(d) : d);
    const said = r.state === "stale" ? `not checked since ${day_(r.checked)}. ${r.why}` : r.state === "not checked" ? `not checked. ${r.why}`
      : `${r.words}${r.open.length ? ` (${r.open.join(", ")})` : ""}, recorded ${day_(r.checked)}`;
    return [h("span", { class: r.passed ? "" : "gap small", "data-recorded": r.state }, said)];
  }
  function overrideItem(o) {
    const item = E[o.item] ? chip(E[o.item].title, o.item, { key: o.item }, "sl-join") : h("span", {}, o.item);
    const until = isDate(o.until) ? day(o.until) : o.until;
    return h("li", { class: o.ended ? "sl-ended" : "", title: o.code }, item, `: accepted until ${until} (${o.case})`, o.ended ? h("b", {}, ". That date has passed, so it doesn't cover anything now") : null);
  }
  function detail(x) {
    return [
      line("Flows", x.flows.length ? x.flows.map(flowChip) : h("span", { class: "gap small" }, x.flowsNone ? `none: ${x.flowsNone}` : "names no flows")),
      line("Contracts it uses", x.joins.length ? x.joins.map(joinItem) : h("span", { class: "muted" }, "none: no step of its flows crosses a contract")),
      line("Teams", x.apps.map((k) => chip(titleOf(k), "", { key: k }, "sl-app"))),
      line("Journey", journeySays(x)),
      x.doneWhen ? line("Done when", x.doneWhen) : null,
      x.shipsOff ? line("Ships off", x.shipsOff) : null,
      x.owner ? line("Owner", ownerChip(x.owner)) : null,
      x.milestones.length ? line("Milestone", x.milestones.join("; ")) : null,
      x.notIn.length ? line("Not in it", h("ul", { class: "sl-notin" }, x.notIn.map((l) => h("li", {}, l.text)))) : null,
      line("Quick flow check", checkSays(x.check)),
      line("Last full check", recordedSays(x.recorded)),
      x.check && x.check.overrides.length ? line("Overrides", h("ul", { class: "sl-overrides" }, x.check.overrides.map(overrideItem))) : null,
    ].filter(Boolean);
  }
  function toggle(tr, more) {
    const open = more.hidden;
    more.hidden = !open;
    tr.setAttribute("aria-expanded", String(open));
    $(".sl-caret", tr).textContent = open ? "▾" : "▸";
    if (open) st.open.add(tr.dataset.slice); else st.open.delete(tr.dataset.slice);
  }
  function tableRow(x, i) {
    const open = st.open.has(x.slice), id = "sl-more-" + i;
    const name = Nodes.wire(h("span", { class: "sl-name" }, x.name), { label: x.label, stop: true, ...keyOf(x) });
    const tr = h("div", { class: "sl-tr" + (x.circled ? " circled" : "") + (st.pick === x.slice ? " picked" : ""), role: "button", tabindex: "0",
      "aria-expanded": String(open), "aria-controls": id, "data-slice": x.slice, title: open ? "Fold it" : "Show its flows, contracts, journey and flow check" },
      h("span", { class: "sl-caret", "aria-hidden": "true" }, open ? "▾" : "▸"),
      h("span", { class: "sl-c sl-c-name" }, name, idTag(x.id), x.tracer ? h("span", { class: "tracer-tag", title: termTip("tracer") }, "tracer") : null),
      h("span", { class: "sl-c sl-c-status" }, statusPill(x)),
      h("span", { class: "sl-c sl-c-after" }, x.after.length ? x.after.map(afterChip) : h("span", { class: "muted" }, "can start first")),
      h("span", { class: "sl-c sl-c-need" }, duePill(x)));
    const more = h("div", { class: "sl-more", id, hidden: !open, role: "region", "aria-label": `${x.name}, in full` }, detail(x));
    tr.addEventListener("click", (ev) => { if (!(ev.target.closest && ev.target.closest("[data-node]"))) toggle(tr, more); });
    tr.addEventListener("keydown", (ev) => { if (ev.target === tr && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); toggle(tr, more); } });
    return [tr, more];
  }
  function tableLayout(list) {
    const head = h("div", { class: "sl-th", "aria-hidden": "true" }, h("span", {}), h("span", {}, "Slice"), h("span", {}, "Status"), h("span", {}, "Comes after"), h("span", {}, "Needs you"));
    list.forEach(sawRow);
    return h("div", { class: "sl-table" }, head, ...list.flatMap(tableRow));
  }

  /* ------------------------------------------------------------ Path */
  /* Depth: the longest run of slices before it, so a slice sits one level below everything it comes after. */
  const DEPTH = {};
  function depthOf(x, seen = new Set()) {
    if (x.slice in DEPTH) return DEPTH[x.slice];
    if (seen.has(x.slice)) return 0;  // a circle (E394): it is drawn, with its red edge, instead of looping
    seen.add(x.slice);
    const d = x.after.reduce((m, k) => (BY[k] ? Math.max(m, 1 + depthOf(BY[k], seen)) : m), 0);
    seen.delete(x.slice);
    return (DEPTH[x.slice] = d);
  }
  function pathNode(x) {
    const s = statusOf(x), raw = !x.status && x.statusRaw, overrides = x.check ? x.check.overrides.length : 0;
    const facts = [plural(x.flows.length, "flow"), plural(x.joins.length, "contract"), overrides ? `${overrides} accepted for now` : null].filter(Boolean);
    const el = h("div", { class: `sl-node st-${STATUS_CLASS[s]}` + (x.circled ? " circled" : "") + (st.pick === x.slice ? " picked" : ""), "data-slice": x.slice, title: `${x.name}: ${facts.join(", ")}` },
      h("span", { class: "sl-node-name" }, x.name), x.tracer ? h("span", { class: "tracer-tag", title: termTip("tracer") }, "tracer") : null,
      h("span", { class: "sl-node-sub" }, raw ? `status "${x.statusRaw}"?` : statusWord(s)),
      x.overdue ? h("span", { class: "sl-due sl-node-due" }, `journey due ${day(x.journeyDue)}, not tried yet`)
        : x.journeyDue && !x.journey ? h("span", { class: "sl-node-sub" }, `journey due ${isDate(x.journeyDue) ? day(x.journeyDue) : x.journeyDue}`) : null);
    return Nodes.wire(el, { label: x.label, aria: `${x.label}: ${statusWord(s)}`, ...keyOf(x) });
  }
  function pathLayout(list) {
    const levels = new Map();
    for (const x of list) { const d = depthOf(x); if (!levels.has(d)) levels.set(d, []); levels.get(d).push(x); }
    const wrap = h("div", { class: "sl-path" }), svg = s("svg", { class: "sl-path-arrows", "aria-hidden": "true" });
    wrap.append(svg, ...[...levels.keys()].sort((a, b) => a - b).map((d) => {
      const xs = levels.get(d);
      return h("div", { class: "sl-level" + (xs.length > 1 ? " parallel" : ""), "data-depth": d }, xs.map(pathNode));
    }));
    list.forEach(sawRow);
    if ([...levels.values()].some((xs) => xs.length > 1)) KEY.saw("sl.parallel");
    if (list.some((x) => x.after.some((k) => list.includes(BY[k])))) KEY.saw("sl.after");
    return wrap;
  }
  function arrows(wrap) {
    const svg = $(".sl-path-arrows", wrap);
    if (!svg) return;
    svg.replaceChildren();
    const marker = s("marker", { id: "sl-head", viewBox: "0 0 8 8", refX: 7, refY: 4, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, s("defs", {}, svg));
    s("path", { d: "M0 0L8 4L0 8Z", class: "sl-head" }, marker);
    const box = wrap.getBoundingClientRect(), nodes = Object.fromEntries($$(".sl-node", wrap).map((n) => [n.dataset.slice, n.getBoundingClientRect()]));
    svg.setAttribute("width", Math.round(box.width)); svg.setAttribute("height", Math.round(wrap.scrollHeight));
    for (const [k, to] of Object.entries(nodes)) for (const a of BY[k].after) {
      const from = nodes[a];
      if (!from) continue;
      const x1 = from.left + from.width / 2 - box.left, y1 = from.bottom - box.top, x2 = to.left + to.width / 2 - box.left, y2 = to.top - box.top - 2, mid = (y1 + y2) / 2;
      s("path", { class: "sl-after", d: `M${x1} ${y1}C${x1} ${mid} ${x2} ${mid} ${x2} ${y2}`, "marker-end": "url(#sl-head)" }, svg);
    }
  }

  /* ------------------------------------------------------------ the view */
  function results(host) {
    const list = shown(), layout = layoutNow();
    KEY = Legend.open("slices", { root: () => host, probes: PROBES });
    host.replaceChildren();
    host.dataset.layout = layout;
    if (!list.length) {
      host.append(h("div", { class: "sl-empty" }, h("p", {}, `No slice matches ${says()}. `, `${plural(LIST.length, "slice")} in all.`),
        h("button", { class: "btn", onclick: clear }, "Clear filters")));
      return;
    }
    if (filtered()) host.append(h("p", { class: "sl-count" }, `${list.length} of ${plural(LIST.length, "slice")}: ${says()}. `, h("button", { class: "linkish", onclick: clear }, "Clear filters")));
    const drawn = layout === "path" ? pathLayout(list) : tableLayout(list);
    host.append(drawn, KEY.el());
    const draw = () => { if (drawn.isConnected) { if (layout === "path") arrows(drawn); KEY.paint(); } };
    draw();
    requestAnimationFrame(draw);
    if (typeof ResizeObserver !== "undefined" && layout === "path") new ResizeObserver(draw).observe(drawn);
  }
  function body(box) {
    box.replaceChildren();
    if (!LIST.length) {
      box.append(emptyState("No slices yet.", `${termTip("slice")} The releases session plans them, the tracer first.`, "/vela:releases"));
      return;
    }
    if (!P.onPages) box.append(h("p", { class: "note sl-old" }, "Each slice gets its own page once the releases session runs again."));
    const find = h("input", { type: "search", class: "sl-find", placeholder: "Search slices, flows, apps, contracts", "aria-label": "Search the slices", value: st.find });
    find.addEventListener("input", () => { st.find = find.value.trim(); changed(); });
    const seg = h("div", { class: "plan-seg sl-seg", role: "group", "aria-label": "How to lay out the slices" }, LAYOUTS.map(([id, label]) =>
      h("button", { class: "btn tiny", "data-layout": id, "aria-pressed": String(id === layoutNow()), onclick: () => {
        Settings.write(LAYOUT_KEY, id); st.layout = id;
        $$("button", seg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.layout === id)));
        changed();
      } }, label)));
    const bar = h("div", { class: "sl-filterhost" }), host = h("div", { class: "sl-results" });
    box.append(h("div", { class: "sl-tools" }, find, seg), bar, host);
    refresh = () => { if (!host.isConnected) return; bar.replaceChildren(filterBar()); results(host); };
    bar.append(filterBar());
    results(host);
  }
  function render(main) {
    const n = LIST.length, moving = LIST.filter((x) => P.statuses.indexOf(x.status) >= 1).length, late = LIST.filter((x) => x.overdue).length;
    const title = typeof Nav !== "undefined" ? Nav.title("Slices") : "Slices";
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, title),
      h("p", {}, termEl("slice", n ? plural(n, "slice") : "Slices"), n ? `, ${moving ? `${moving} building or further along` : "none building yet"}${late ? `, ${late} with a journey past its due date` : ""}${LIST.some((x) => x.tracer) && !moving ? ". The first to plan is the tracer" : ""}; pick a row to see what's in it.` : " are the pieces the product is built and shipped in.")),
      h("div", { class: "spacer" }), typeof Nav !== "undefined" ? Nav.pageActions() : null));
    const box = h("div", { class: "sl-body scroll", id: "board" });
    main.append(box);
    body(box);
  }
  function highlight(key) {
    const x = LIST.find((y) => y.key === key);
    st.pick = x ? x.slice : "";
    $$(".sl-tr, .sl-node").forEach((r) => r.classList.toggle("picked", r.dataset.slice === st.pick));
    const el = st.pick && $(`.sl-tr[data-slice="${CSS.escape(st.pick)}"], .sl-node[data-slice="${CSS.escape(st.pick)}"]`);
    if (el) el.scrollIntoView({ block: "nearest" });
  }

  /* ------------------------------------------------------------ the address bar */
  function hashParts() {
    const p = [];
    if (st.find) p.push("sl-find=" + encodeURIComponent(st.find));
    for (const [g, , key] of GROUPS) for (const v of st[g]) p.push(key + "=" + encodeURIComponent(v));
    if (st.needs) p.push("sl-needs");
    if (layoutNow() !== "table") p.push("sl-layout=" + layoutNow());
    return p;
  }
  /* The filters from the hash a link or Back brought; a hash with none of them clears them. */
  function readHash() {
    st.find = (HASH.get("sl-find") || "").trim();
    for (const [g, , key] of GROUPS) st[g] = new Set(HASH.getAll(key).filter(Boolean));
    st.needs = HASH.has("sl-needs");
    const l = HASH.get("sl-layout");
    st.layout = LAYOUTS.some(([id]) => id === l) ? l : null;
  }

  /* ------------------------------------------------------------ the panel's part for a slice page */
  function panelPart(key) {
    const x = LIST.find((y) => y.key === key);
    if (!x) return [];
    const chips = (list, fn) => h("div", {}, list.map(fn));
    return [Panel.section("Where it stands", null, h("div", {}, h("span", { class: "pill" }, statusWord(statusOf(x))),
        x.journey && !x.journey.problem ? h("span", { class: "muted small" }, ` tried end to end on ${day(x.journey.date)} by ${x.journey.by}`) : null,
        x.overdue ? h("p", { class: "sl-late" }, x.overdue[0].toUpperCase() + x.overdue.slice(1) + ".") : x.journeyDue && !x.journey ? h("span", { class: "muted small" }, ` journey due ${isDate(x.journeyDue) ? day(x.journeyDue) : x.journeyDue}`) : null,
        h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => { Nav.open("slices", key); } }, "Show it among the slices")))),
      x.flows.length ? Panel.section("Flows it proves", x.flows.length, chips(x.flows, (f) => (f.key ? refChip(f.key) : h("span", { class: "ref-chip ref-dead" }, f.id)))) : null,
      x.joins.length ? Panel.section("Contracts its flows use", x.joins.length, h("ul", { class: "mini-list" }, x.joins.map((j) =>
        h("li", {}, j.key ? refChip(j.key) : h("span", { class: "ref-chip ref-dead" }, j.id), j.from || j.to ? ` ${j.from || "?"} → ${j.to || "?"}` : null)))) : null,
      x.after.length ? Panel.section("Comes after", x.after.length, chips(x.after, (k) => (BY[k] && BY[k].key ? refChip(BY[k].key) : h("span", { class: "ref-chip ref-dead" }, nameOf(k))))) : null,
      x.notIn.length ? Panel.section("Not in this slice", x.notIn.length, h("ul", { class: "mini-list" }, x.notIn.map((l) => h("li", {}, l.text)))) : null].filter(Boolean);
  }
  return { render, highlight, panelPart, hashParts, readHash, clear, LIST, st, LAYOUT_KEY, matches, shown };
})();
View("slices", { label: "Slices", title: "Each slice: one journey proven end to end, and where it stands", render: Slices.render, highlight: Slices.highlight, count: () => String(D.slicePlan.list.length) });
