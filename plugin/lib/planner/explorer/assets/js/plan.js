/* Build plan: the fourth level of Inside this app (DESIGN-INSIDE.md), the team's work breakdown drawn beside its design.

   - The build order, in one of three layouts the reader picks (List, Cards, Path; the choice is kept in this browser).
     Each story shows what it is, how many tasks it has and what it waits on, in words, never IDs or sizes. A story blocked
     by an open vault question is lit with that question's lamp (attention's, not the plan's); one blocked by an outside
     party says so. A story opens to what must be true when it is done, its flags, its trace chips (the same vault links the
     design's chips use) and its tasks, each with a component chip that jumps to that component in level 3. Stories the
     team marks as the tracer come first; stories with no tasks (merged, deferred) come last, under Not now.
   - The dependency view: stories left to right, an arrow for each Blocked by, the questions and outside parties that
     block them at the left edge. It uses the layout the components drawing uses, so no two boxes meet.
   - Coverage, computed from the stories' own Traces to lines and tasks (plan_data.py), with every empty cell lit;
     Not planned; the plan's status and gaps; the totals; the Jira CSV the tool writes, to copy, and the tickets file
     beside the plan when there is one.

   Nothing here fills a hole with a guess: a plan the reader could not fully read shows the list of what it could not.
   It also gives the rest of the page the plan's side of the trace ("Built by S-03") and each app's readiness for the
   doors. Loaded after inside.js, which hands it the drawing kit (Inside.kit) and calls render. */
const Plan = (() => {
  const PLANS = D.plans || {}, DES = D.designs || {};
  const LAYOUT_KEY = "explorer.plan.layout", LAYOUTS = [["list", "List"], ["cards", "Cards"], ["path", "Path"]];
  const st = { open: new Set(), pick: "" };
  const layoutNow = () => { const v = Settings.read(LAYOUT_KEY); return LAYOUTS.some(([id]) => id === v) ? v : "list"; };
  const plan = (app) => PLANS[app] || null;
  const kit = () => Inside.kit;
  const planWord = (app) => `${titleOf(app)} plan`;
  const base = (id) => id.split("@")[0];

  /* ------------------------------------------------------------ the plan, from the rest of the page */
  /* The stories that build a vault ID, keyed as the design's owners are (the ID and the ID without its @APP). */
  const BUILT = {};
  for (const [app, p] of Object.entries(PLANS)) {
    for (const story of p.stories) for (const id of story.traces) for (const k of new Set([id, base(id)])) {
      const list = (BUILT[k] = BUILT[k] || []);
      if (!list.some((x) => x.app === app && x.story === story.id)) list.push({ app, story: story.id, name: story.name });
    }
  }
  const unclosedLevel = (story) => {  // the lamp of the worst open vault question that blocks the story
    const levels = story.blockers.filter((b) => b.kind === "question" && isOpen(UNKNOWN[b.ref])).map((b) => levelForKey(keyForId(b.ref))).filter((l) => l && l !== "dark");
    return levels.sort((p, q) => rank(q) - rank(p))[0] || "";
  };
  /* Where an app stands, for the doors: no design, design only, plan complete, plan with gaps (plan in progress when
     the plan's own status is neither). */
  function readiness(app) {
    const p = plan(app);
    if (!p) return DES[app] ? { id: "design", word: "design only", counts: "" } : { id: "none", word: "no design", counts: "" };
    const t = p.totals, id = p.status === "complete" ? "complete" : p.status === "complete-with-gaps" ? "gaps" : "progress";
    return { id, word: { complete: "plan complete", gaps: "plan with gaps", progress: "plan in progress" }[id],
      counts: `${plural(t.stories, "story", "stories")}, ${plural(t.tasks, "task")}` };
  }
  const readinessPill = (app) => { const r = readiness(app); return h("span", { class: "d-status plan-ready " + r.id, "data-ready": r.id, title: r.counts || r.word }, r.word); };
  /* Everything outside the plan that holds stories, grouped by what holds them: for the managers' door. */
  function blockedOn() {
    const by = {};
    for (const [app, p] of Object.entries(PLANS)) for (const story of p.stories) for (const b of story.blockers) {
      if (b.kind === "story" || (b.kind === "question" && !isOpen(UNKNOWN[b.ref]))) continue;
      const k = `${b.kind}:${b.ref || b.text}`;
      (by[k] = by[k] || { kind: b.kind, ref: b.ref, text: b.text, stories: [] }).stories.push({ app, id: story.id });
    }
    return Object.values(by).sort((a, b) => b.stories.length - a.stories.length || cmp(a.text, b.text));
  }

  /* ------------------------------------------------------------ going to a story, a component, the CSV */
  function reveal(app, id) {
    st.open.add(id); st.pick = id;
    if (!(App.view === "inside" && Inside.st.app === app && Inside.st.level === "plan")) Inside.open(app, "plan", { keepTrail: true, still: true });
    else {
      $$(`.plan-card[data-story="${CSS.escape(id)}"]`).forEach((c) => { c.classList.add("open"); const t = $(".plan-toggle", c); if (t) t.setAttribute("aria-expanded", "true"); });
      pickInPath(id);
    }
    const card = $(`.plan-card[data-story="${CSS.escape(id)}"]`);
    if (card) card.scrollIntoView({ block: "nearest" });
  }
  function toComponent(app, name) {
    Inside.open(app, "components", { keepTrail: true, still: true });
    go(Inside.kit.key(app, "c", name), {});
  }
  const sink = {  // where "Copy as Jira CSV" writes; the self-test swaps it to read what would have been copied
    async write(text) {
      if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); return; }
      const box = h("textarea", { style: { position: "fixed", opacity: "0" } });
      box.value = text; document.body.append(box); box.select();
      const done = document.execCommand("copy");
      box.remove();
      if (!done) throw new Error("this browser would not copy");
    },
  };
  async function copyCsv(app) {
    const p = plan(app), rows = (p.totals.built ?? p.stories.length) + p.totals.tasks;  // merged and deferred stories get no ticket
    try { await sink.write(p.csv); toast(`Copied the Jira CSV: ${plural(rows, "row")}, as tools/breakdown_to_tickets.py writes it.`); }
    catch (e) { console.warn("[plan] could not copy the CSV:", e); toast("This page could not reach the clipboard. Open the Tickets file instead, or run tools/breakdown_to_tickets.py."); }
  }

  /* ------------------------------------------------------------ small pieces */
  function statusPill(p) {
    const gaps = p.gaps.map((g) => g.id).filter(Boolean);
    return h("span", { class: "d-status " + (p.status || "unknown"), title: `The team's plan is ${p.status || "of no known status"}${gaps.length ? ", with " + gaps.join(", ") : ""}` },
      p.status === "complete-with-gaps" ? "complete with gaps" : p.status || "status not read", gapsTag(gaps));
  }

  /* ------------------------------------------------------------ the stories, as the three layouts draw them */
  /* The groups, from the plan alone: the tracer stories first (only when the team marked some), then the rest in build order,
     then the stories with no tasks, which are merged into another or deferred. */
  function arrange(p) {
    const tasked = p.stories.filter((x) => x.tasks.length), tracer = tasked.filter((x) => x.tracer), rest = tasked.filter((x) => !x.tracer);
    const groups = tracer.length
      ? [{ id: "tracer", title: "Build first: the tracer", note: "one thin path a person can use", stories: tracer }, { id: "then", title: "Then", note: "", stories: rest }]
      : [{ id: "order", title: "In build order", note: "", stories: rest }];
    const idle = p.stories.filter((x) => !x.tasks.length);
    return groups.filter((g) => g.stories.length).concat(idle.length ? [{ id: "notnow", title: "Not now", note: "", stories: idle }] : []);
  }
  const numberOf = (groups) => { const n = {}; let i = 0; for (const g of groups) if (g.id !== "notnow") for (const x of g.stories) n[x.id] = ++i; return n; };
  const plainText = (t) => String(t || "").replace(/`/g, "").replace(/\s+/g, " ").trim();
  const trimmed = (t, max) => { const x = plainText(t); if (x.length <= max) return x; return x.slice(0, max).replace(/\s+\S*$/, "") + "…"; };
  const storyById = (p, id) => p.stories.find((x) => x.id === id);
  const cleanName = (name) => plainText(name).replace(/\s*\(deferred\)\s*$/i, "");

  /* What a story waits on, in words: a story by its name, a vault question by its title. */
  function waitsText(p, story) {
    const words = story.blockers.map((b) => {
      if (b.kind === "story") { const w = storyById(p, b.ref); return w ? cleanName(w.name) : b.ref; }
      if (b.kind === "question") { const title = (E[keyForId(b.ref)] || {}).title; return (title || b.text || b.ref) + (isOpen(UNKNOWN[b.ref]) ? "" : " (resolved)"); }
      return plainText(b.text);
    }).filter(Boolean);
    return words.length ? words.join("; ") : "Nothing";
  }
  const waitsEl = (p, story) => h("span", { class: "plan-waits" }, "Waits on: " + waitsText(p, story));

  /* Why a story with no tasks is parked, in the plan's own words where it has them. */
  function parkedReason(p, story) {
    const merged = /^\(merged into (S-[\w-]+)\)/i.exec(story.name);
    if (merged) { const into = storyById(p, merged[1]); return "Merged into " + (into ? cleanName(into.name) : merged[1]); }
    const line = p.notPlanned.find((t) => t.slice(0, Math.max(t.indexOf(":"), 0)).includes(story.id));
    const after = line ? line.slice(line.indexOf(":") + 1).trim().split(/\.\s/)[0].replace(/\.$/, "") : "";
    if (after) return after[0].toUpperCase() + after.slice(1);
    return /deferred/i.test(story.name) ? "Deferred" : "No tasks planned";
  }
  const parkedName = (story) => (/^\(merged into/i.test(story.name) ? `${story.id}, merged` : cleanName(story.name));
  const seeText = (story) => (story.criteria.length ? trimmed(story.criteria[0], 150) : "");

  function taskRow(app, task) {
    const known = DES[app] && DES[app].components.some((c) => c.name.toLowerCase() === task.component.toLowerCase());
    const name = known ? DES[app].components.find((c) => c.name.toLowerCase() === task.component.toLowerCase()).name : task.component;
    return h("li", { class: "plan-task" }, h("span", { class: "plan-task-name" }, plainText(task.name)),
      known ? h("a", { class: "ref-chip plan-comp", "data-component": name, title: `Show ${name} in the components`, onclick: () => toComponent(app, name) }, name)
        : h("span", { class: "ref-chip plan-comp dead", title: DES[app] ? "Not a component of the design" : "No design loaded to show it in" }, task.component || "no component"));
  }
  /* What the plan flags on a story, as small labelled badges: a question only the design can answer, and a clash with an
     epic criterion, named by the criterion's title and not just its ID. The full text is in the story's detail. */
  function flagBadges(story) {
    const open = story.openNotes.length ? [h("span", { class: "plan-badge open", "data-flag": "open", title: story.openNotes.join("\n\n") },
      story.openNotes.length > 1 ? `Open for design · ${story.openNotes.length}` : "Open for design")] : [];
    const clash = story.conflicts.map((c) => h("span", { class: "plan-badge conflict", "data-flag": "conflict", title: c.text },
      c.ref ? ["Conflicts with ", refChip(keyForId(c.ref))] : "Conflicts with an epic criterion"));
    return open.length || clash.length ? h("div", { class: "plan-flags" }, open, clash) : null;
  }
  function flagNotes(story) {
    const K = kit(), note = (title, items) => (items.length ? h("div", { class: "plan-notes" }, h("div", { class: "fl" }, title), h("ul", { class: "plan-ac" }, items.map((t) => h("li", {}, K.prose(t))))) : null);
    return [note("Open for the design", story.openNotes), note("Conflicts with an epic criterion", story.conflicts.map((c) => c.text))];
  }
  /* The detail, the same in all three layouts: done when, flags, traces, tasks. */
  function storyDetail(app, story) {
    const K = kit();
    return h("div", { class: "plan-card-body" },
      h("div", { class: "fl" }, "Done when"),
      story.criteria.length ? h("ul", { class: "plan-ac" }, story.criteria.map((c) => h("li", {}, K.prose(c)))) : h("div", { class: "gap" }, "No acceptance criteria in the plan."),
      flagNotes(story),
      h("div", { class: "fl" }, "Traces to"), h("div", { class: "plan-traces" }, story.traces.length ? story.traces.map((id) => K.idChip(id)) : h("span", { class: "muted small" }, "Nothing named.")),
      h("div", { class: "fl" }, `Tasks (${story.tasks.length})`),
      story.tasks.length ? h("ol", { class: "plan-tasks" }, story.tasks.map((t) => taskRow(app, t))) : h("div", { class: "muted small" }, "No tasks."));
  }
  const litOf = (story) => { const lit = unclosedLevel(story); return { cls: lit ? " lit " + lit : "", lamp: lit ? lampEl(lit, "Waiting on an open question: its lamp, from attention") : null }; };

  /* A folding story (List and Cards): a button that is the story's headline, flags beside it, the detail under it. */
  function foldingStory(app, story, kind, head, extra) {
    const { cls, lamp } = litOf(story), open = st.open.has(story.id);
    const toggle = h("button", { class: "plan-toggle", "aria-expanded": String(open), onclick: () => {
      const now = card.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(now));
      if (now) st.open.add(story.id); else st.open.delete(story.id);
    } }, head(lamp));
    const card = h("article", { class: `plan-card plan-${kind}` + (open ? " open" : "") + cls + (extra || ""), "data-story": story.id, id: `plan-${app}-${story.id}` },
      toggle, flagBadges(story), storyDetail(app, story));
    return card;
  }
  function listRow(app, p, story, n, tracer) {
    const parked = !story.tasks.length;
    return foldingStory(app, story, "row", (lamp) => [
      h("span", { class: "plan-n", title: n ? `Number ${n} in the build order` : "Not in the build order" }, n || "–"),
      h("span", { class: "plan-name" }, lamp, parked ? parkedName(story) : cleanName(story.name)),
      parked ? null : h("span", { class: "plan-count" }, plural(story.tasks.length, "task")),
      parked ? h("span", { class: "plan-waits" }, parkedReason(p, story)) : waitsEl(p, story)], (tracer ? " tracer" : "") + (parked ? " off" : ""));
  }
  function cardTile(app, p, story, tracer) {
    const parked = !story.tasks.length, see = seeText(story);
    return foldingStory(app, story, "tile", (lamp) => [
      h("span", { class: "plan-name" }, lamp, parked ? parkedName(story) : cleanName(story.name)),
      !parked && see ? h("span", { class: "plan-see", title: "What a person can see when it is done" }, see) : null,
      parked ? h("span", { class: "plan-waits" }, parkedReason(p, story))
        : h("span", { class: "plan-foot" }, h("span", { class: "plan-count" }, plural(story.tasks.length, "task")), waitsEl(p, story))], (tracer ? " tracer" : "") + (parked ? " off" : ""));
  }
  const groupHead = (g) => h("h4", { class: "plan-group-head" }, g.title, g.note ? h("span", {}, g.note) : null);

  function listLayout(app, p, groups) {
    const num = numberOf(groups);
    return groups.map((g) => h("div", { class: "plan-group", "data-group": g.id }, groupHead(g),
      h("div", { class: "plan-rows" }, g.stories.map((x) => listRow(app, p, x, num[x.id], g.id === "tracer")))));
  }
  function cardsLayout(app, p, groups) {
    return groups.map((g) => h("div", { class: "plan-group", "data-group": g.id }, groupHead(g),
      h("div", { class: "plan-grid" }, g.stories.map((x) => cardTile(app, p, x, g.id === "tracer")))));
  }

  /* Path: a vertical line of stories, the picked one's detail beside it (under it on a narrow window). Every story's
     detail is in the page, the others hidden, so what the page holds does not depend on which is picked. */
  function pickInPath(id) {
    const path = $(".plan-path");
    if (!path) return;
    $$(".plan-card", path).forEach((li) => { const on = li.dataset.story === id; li.classList.toggle("on", on); $(".plan-toggle", li).setAttribute("aria-current", String(on)); });
    $$(".plan-pane", path.parentNode).forEach((pane) => { pane.hidden = pane.dataset.pane !== id; });
  }
  function pathLayout(app, p, groups) {
    const num = numberOf(groups), all = groups.flatMap((g) => g.stories.map((x) => ({ x, g })));
    const total = Object.keys(num).length;
    if (!all.some(({ x }) => x.id === st.pick)) st.pick = all.length ? all[0].x.id : "";
    const items = [], panes = [];
    for (const g of groups) {
      items.push(h("li", { class: "plan-path-group plan-group", "data-group": g.id }, g.title));
      for (const story of g.stories) {
        const parked = !story.tasks.length, { cls, lamp } = litOf(story);
        const li = h("li", { class: "plan-card plan-step" + cls + (g.id === "tracer" ? " tracer" : "") + (parked ? " off" : "") + (story.id === st.pick ? " on" : ""), "data-story": story.id, id: `plan-${app}-${story.id}` },
          h("button", { class: "plan-toggle", "aria-current": String(story.id === st.pick), onclick: () => { st.pick = story.id; pickInPath(story.id); } },
            h("span", { class: "plan-name" }, lamp, parked ? `${parkedName(story)} · ${parkedReason(p, story)}` : cleanName(story.name))),
          flagBadges(story));
        items.push(li);
        const kick = parked ? "Not now" : `Story ${num[story.id]} of ${total}` + (g.id === "tracer" ? ", part of the tracer" : "");
        panes.push(h("section", { class: "plan-pane", "data-pane": story.id, hidden: story.id !== st.pick },
          h("p", { class: "plan-kick" }, kick), h("h4", {}, parked ? parkedName(story) : cleanName(story.name)),
          parked ? h("p", { class: "plan-waits" }, parkedReason(p, story)) : h("p", {}, waitsEl(p, story)), storyDetail(app, story)));
      }
    }
    return h("div", { class: "plan-split" }, h("ol", { class: "plan-path" }, items), h("div", { class: "plan-panes" }, panes));
  }

  const BUILDERS = { list: listLayout, cards: cardsLayout, path: pathLayout };
  function buildOrder(app, p) {
    const host = h("div", { class: "plan-layout" }), groups = arrange(p), draw = (now) => { host.dataset.layout = now; host.replaceChildren(...[].concat(BUILDERS[now](app, p, groups))); };
    const seg = h("div", { class: "plan-seg", role: "group", "aria-label": "How to lay out the build order" }, LAYOUTS.map(([id, label]) =>
      h("button", { class: "btn tiny", "data-layout": id, "aria-pressed": String(id === layoutNow()), onclick: () => {
        Settings.write(LAYOUT_KEY, id); draw(id);
        $$("button", seg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.layout === id)));
      } }, label)));
    draw(layoutNow());
    return h("div", { class: "plan-order" }, seg, host);
  }

  /* ------------------------------------------------------------ the dependency view */
  const { ln, bx } = Legend;
  Legend.define("pw.story", [bx({ fill: "deck-2", stroke: "rule-3", w: 1.4, rx: 4 })], "Flat box with an ID: a story, with its task count");
  Legend.define("pw.arrow", [ln({ stroke: "ink-3", w: 1.6, head: "fill" })], "Solid arrow: a story that blocks another, pointing at it");
  Legend.define("pw.soft", [ln({ stroke: "ink-4", w: 1.6, head: "fill", dash: "4 3" })], "Dashed arrow: something other than a story blocks a story");
  Legend.define("pw.stub", [{ k: "clip", fill: "room-2", stroke: "ink-4", w: 1.4, dash: "4 3" }], "Clipped dashed box: an open question, a gap or a deferral blocking a story");
  Legend.define("pw.outside", [{ k: "clip", fill: "room-2", stroke: "ink-2", w: 1.6 }], "Clipped solid box: an outside party a story waits on");
  const WAITS_LOOKS = () => ({
    "pw.story": "g.plan-node", "pw.arrow": "path.in-edge:not(.soft)", "pw.soft": "path.in-edge.soft", "pw.stub": ".plan-outer:not(.outside) .in-stub-face", "pw.outside": ".plan-outer.outside .in-stub-face",
    ...Legend.lampProbes((lv) => (lv === "dark" ? "g.hit.dark" : `.plan-node .in-box-face.lit.${lv}, .plan-dot.${lv}, .in-edge.lit.${lv}`)),
  });
  const BLOCKER_WORD = { question: "Open question", outside: "Outside party", "plan-question": "Plan's open question", gap: "Gap or deferral", other: "Outside the plan" };
  /* Every node the view draws goes through here, and so through Nodes.wire (core.js): none can be drawn that a reader
     cannot click or a screen reader cannot name (the Sensor rule: a node that does nothing when clicked is a Black Box). */
  function planNode(g, b, spec) {
    const grp = s("g", { class: "in-node plan-hit " + spec.cls, ...spec.attrs }, g);
    spec.draw(grp);
    s("title", {}, grp).textContent = spec.title || spec.label;
    return Nodes.wire(grp, { label: spec.label, open: spec.open });
  }
  /* Lays the dependency view out in rows that fit a fixed width (DAG_W). The blockers outside the plan take the first rows;
     each story sits on the row after the deepest story that blocks it, and a row that holds more than fit wraps onto the
     next. An arrow leaves the bottom of what blocks, runs along the gap under its row, and enters the top of the story it
     blocks (the bottom, when both sit on one row). Arrows are drawn beneath the boxes, so one that crosses a row passes behind. */
  const DAG_W = 880, DAG_GAP = 16, DAG_ROW_GAP = 46;
  function wrapped(nodes, edges) {
    const stories = nodes.filter((n) => n.kind === "story"), stubs = nodes.filter((n) => n.kind === "outer");
    const after = {};  // story node id -> the story nodes that block it
    for (const e of edges) if (e.from.startsWith("s:")) (after[e.to] = after[e.to] || []).push(e.from);
    const depth = {}, visiting = new Set();
    const deepest = (id) => {
      if (depth[id] !== undefined) return depth[id];
      if (visiting.has(id)) return 0;  // a cycle in the plan: break it here, the plan's own check reports it
      visiting.add(id);
      depth[id] = 1 + Math.max(-1, ...(after[id] || []).map(deepest));
      visiting.delete(id);
      return depth[id];
    };
    stories.forEach((n) => deepest(n.id));
    const rows = [];
    const addRow = (list) => { const per = Math.max(1, Math.floor((DAG_W + DAG_GAP) / (list[0].w + DAG_GAP))); for (let i = 0; i < list.length; i += per) rows.push(list.slice(i, i + per)); };
    if (stubs.length) addRow(stubs);
    for (let d = 0; d <= Math.max(0, ...Object.values(depth)); d++) { const layer = stories.filter((n) => depth[n.id] === d); if (layer.length) addRow(layer); }
    const box = {}, rowOf = {}, rowTop = [];
    let y = 0;
    rows.forEach((row, r) => {
      const w = row.reduce((n, x) => n + x.w, 0) + DAG_GAP * (row.length - 1), h0 = Math.max(...row.map((x) => x.h));
      let x = (DAG_W - w) / 2;
      rowTop[r] = { y, h: h0 };
      for (const n of row) { box[n.id] = { x, y: y + (h0 - n.h) / 2, w: n.w, h: n.h, node: n }; rowOf[n.id] = r; x += n.w + DAG_GAP; }
      y += h0 + DAG_ROW_GAP;
    });
    const paths = [];
    edges.forEach((e, i) => {
      const a = box[e.from], b = box[e.to];
      if (!a || !b) return;
      const ra = rowOf[e.from], rb = rowOf[e.to], jitter = ((i % 5) - 2) * 3;
      const sx = a.x + a.w / 2, sy = a.y + a.h, below = rowTop[ra].y + rowTop[ra].h + DAG_ROW_GAP / 2 + jitter;
      const tx = b.x + b.w / 2 + ((i % 3) - 1) * 10;
      let pts;
      if (ra === rb) pts = [{ x: sx, y: sy }, { x: sx, y: below }, { x: tx, y: below }, { x: tx, y: b.y + b.h }];
      else {
        // down the gutter beside the target (clear of its row's boxes), then along the gap over it and into its top
        const above = rowTop[rb].y - DAG_ROW_GAP / 2 + jitter, gx = b.x - DAG_GAP / 2 + ((i % 3) - 1) * 3;
        pts = ra + 1 === rb ? [{ x: sx, y: sy }, { x: sx, y: below }, { x: tx, y: below }, { x: tx, y: b.y }]
          : [{ x: sx, y: sy }, { x: sx, y: below }, { x: gx, y: below }, { x: gx, y: above }, { x: tx, y: above }, { x: tx, y: b.y }];
      }
      paths.push({ e, pts });
    });
    return { box, paths, gaps: [], dir: "TB" };
  }
  function dependencyView(app, p) {
    const K = kit(), holder = h("div", { class: "plan-dag", id: "plan-dag" }), frame = h("div", { class: "inside-frame plan-dag-frame" }, holder);
    const wrap = h("div", { class: "plan-dag-wrap" }, frame), lg = Legend.open("plan-waits", { root: () => wrap, probes: WAITS_LOOKS() });
    wrap.append(lg.el());  // under the frame, not in it: the drawing's minimap sits over the frame's corner
    const nodes = p.stories.map((story) => ({ id: "s:" + story.id, kind: "story", w: 204, h: 66, story })), edges = [], stubs = {};
    const stubFor = (b) => {
      const id = `x:${b.kind}:${b.ref || b.text}`;
      if (!stubs[id]) { stubs[id] = true; nodes.push({ id, kind: "outer", side: "in", w: 204, h: 54, b }); }
      return id;
    };
    for (const story of p.stories) for (const b of story.blockers) {
      if (b.kind === "story") { if (p.stories.some((x) => x.id === b.ref)) edges.push({ from: "s:" + b.ref, to: "s:" + story.id, title: `${story.id} is blocked by ${b.ref}` }); continue; }
      edges.push({ from: stubFor(b), to: "s:" + story.id, soft: true, lit: b.kind === "question" && isOpen(UNKNOWN[b.ref]) ? levelForKey(keyForId(b.ref)) : "", title: `${story.id} is blocked by ${b.text}` });
    }
    // top to bottom, wrapped to the room's width: the page never scrolls sideways, the drawing grows taller instead
    const lay = wrapped(nodes, edges);
    lay.looks = { solid: "pw.arrow", soft: "pw.soft" };
    const svg = s("svg", { class: "inside-svg cockpit plan-dag-svg", role: "img", "aria-label": `${titleOf(app)}'s stories, each after the stories that block it` }, holder);
    K.defsFor(svg);
    lg.within(() => K.drawLayout(svg, lay, {
      story: (g, b) => {
        const story = b.node.story, lit = unclosedLevel(story);
        Legend.saw("pw.story"); if (lit) Legend.saw("lamp." + lit);
        planNode(g, b, { cls: "plan-node in-box", attrs: { "data-story": story.id }, label: `${story.id} ${cleanName(story.name)}`, title: `${story.id} ${cleanName(story.name)}\n${plural(story.tasks.length, "task")}`,
          open: () => openStory(app, story.id),
          draw: (grp) => {
            s("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 10, class: "in-box-face" + (lit ? " lit " + lit : "") }, grp);
            s("text", { x: b.x + 14, y: b.y + 24, class: "in-box-name plan-id" }, grp).textContent = story.id;
            s("text", { x: b.x + b.w - 14, y: b.y + 24, "text-anchor": "end", class: "in-box-meta" }, grp).textContent = story.tasks.length ? plural(story.tasks.length, "task") : "no tasks";
            s("text", { x: b.x + 14, y: b.y + 46, class: "in-box-sub" }, grp).textContent = K.fit(cleanName(story.name), b.w - 28, 11.5);
          } });
      },
      outer: (g, b) => {
        const x = b.node.b, level = x.kind === "question" && isOpen(UNKNOWN[x.ref]) ? levelForKey(keyForId(x.ref)) : "", vault = x.kind === "question" && ent(keyForId(x.ref)) ? keyForId(x.ref) : "";
        const word = x.kind === "question" ? (vault ? titleOf(vault) : x.ref) : BLOCKER_WORD[x.kind];
        Legend.saw(x.kind === "outside" ? "pw.outside" : "pw.stub"); if (level && level !== "dark") Legend.saw("lamp." + level);
        planNode(g, b, { cls: "in-stub plan-outer " + x.kind, attrs: { "data-blocker": x.kind }, label: `${BLOCKER_WORD[x.kind]}: ${plainText(x.text)}`, title: x.text,
          open: () => (vault ? go(vault, {}) : go(Inside.kit.key(app, "blocker", `${x.kind}:${x.ref || x.text}`), {})),
          draw: (grp) => {
            s("path", { d: `M${b.x + 8},${b.y}H${b.x + b.w - 8}L${b.x + b.w},${b.y + 8}V${b.y + b.h - 8}L${b.x + b.w - 8},${b.y + b.h}H${b.x + 8}L${b.x},${b.y + b.h - 8}V${b.y + 8}Z`, class: "in-stub-face" }, grp);
            if (level && level !== "dark") s("circle", { cx: b.x + 17, cy: b.y + 18, r: 5.5, class: "plan-dot " + level }, grp);
            s("text", { x: b.x + (level && level !== "dark" ? 30 : 14), y: b.y + 22, class: "in-box-name small" }, grp).textContent = K.fit(x.kind === "question" ? x.ref : word, b.w - 44, 12.5, 600);
            s("text", { x: b.x + 14, y: b.y + 41, class: "in-box-sub" }, grp).textContent = K.fit(x.kind === "question" ? (E[keyForId(x.ref)] || {}).title || plainText(x.text) : plainText(x.text), b.w - 24, 11);
          } });
      },
    }));
    lg.paint();
    const b = K.boundsOf(Object.values(lay.box));
    const pad = 24, w = b.x1 - b.x0 + pad * 2, ht = b.y1 - b.y0 + pad * 2;
    svg.setAttribute("viewBox", `${(b.x0 - pad).toFixed(1)} ${(b.y0 - pad).toFixed(1)} ${w.toFixed(1)} ${ht.toFixed(1)}`);
    svg.style.width = "100%"; svg.style.maxWidth = Math.round(w * 1.15) + "px"; svg.style.height = "auto";  // the width the room gives sets the height
    return wrap;
  }

  /* ------------------------------------------------------------ the right-hand panel: a story, or a blocker with no page of its own */
  const storyKey = (app, id) => Inside.kit.key(app, "story", id);
  function openStory(app, id) { reveal(app, id); go(storyKey(app, id), {}); }
  const blockerId = (b) => `${b.kind}:${b.ref || b.text}`;
  const stubHolds = (p, name) => p.stories.filter((x) => x.blockers.some((b) => blockerId(b) === name));
  function panelTitle(app, kind, name) {
    const p = plan(app);
    if (!p) return name;
    if (kind === "story") { const x = storyById(p, name); return x ? `${x.id} ${x.tasks.length ? cleanName(x.name) : parkedName(x)}` : name; }
    const hit = p.stories.flatMap((x) => x.blockers).find((b) => blockerId(b) === name);
    return hit ? `${BLOCKER_WORD[hit.kind]}: ${trimmed(hit.text, 60)}` : name;
  }
  function panelFor(app, kind, name) {
    const p = plan(app), K = kit();
    const head = (what, title, ...more) => h("div", { class: "p-head" }, h("div", { class: "kind" }, what), h("h2", {}, title), ...more.filter(Boolean));
    if (!p) return [h("div", { class: "p-empty" }, `${titleOf(app)} has no build plan loaded.`)];
    if (kind === "story") {
      const story = storyById(p, name);
      if (!story) return [h("div", { class: "p-empty" }, `The ${planWord(app)} has no story ${name}.`)];
      const parked = !story.tasks.length, into = /^\(merged into (S-[\w-]+)\)/i.exec(story.name), line = p.notPlanned.find((t) => t.slice(0, Math.max(t.indexOf(":"), 0)).includes(story.id));
      return [head(`Story · ${planWord(app)}`, panelTitle(app, "story", name), h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => reveal(app, story.id) }, "Show it in the build order"))),
        h("div", { class: "p-body" },
          parked ? Panel.section("What happened to it", null,
            into ? h("div", {}, "Merged into ", storyLinks(app, [into[1]]), storyById(p, into[1]) ? " " + cleanName(storyById(p, into[1]).name) : "")
              : h("div", {}, line ? K.prose(line) : "The plan gives it no tasks and says nothing more about it."))
            : Panel.section("Waits on", story.blockers.length, story.blockers.length ? h("ul", { class: "mini-list" }, story.blockers.map((b) => h("li", {},
              b.kind === "story" ? storyLinks(app, [b.ref]) : b.kind === "question" && ent(keyForId(b.ref)) ? refChip(keyForId(b.ref)) : h("span", {}, h("b", {}, BLOCKER_WORD[b.kind] + ": "), plainText(b.text))))) : h("div", { class: "p-empty-line" }, "Nothing: it can start now.")),
          storyDetail(app, story))];
    }
    const holds = stubHolds(p, name), first = holds.length ? holds[0].blockers.find((b) => blockerId(b) === name) : null;
    if (!first) return [h("div", { class: "p-empty" }, `No story in the ${planWord(app)} waits on that.`)];
    return [head(`${BLOCKER_WORD[first.kind]} · ${planWord(app)}`, trimmed(first.text, 80)),
      h("div", { class: "p-body" },
        Panel.section("What the plan says", null, h("div", { class: "prose-text" }, first.kind === "question" ? `${first.ref}: ${plainText(first.text)}. The vault holds no page for it.` : plainText(first.text))),
        Panel.section("Holds up", holds.length, h("ul", { class: "mini-list" }, holds.map((x) => h("li", {}, storyLinks(app, [x.id]), " " + cleanName(x.name))))))];
  }

  /* ------------------------------------------------------------ coverage, not planned, totals */
  function storyLinks(app, ids) {
    return ids.length ? ids.map((id) => h("a", { class: "ref-chip plan-after", onclick: () => openStory(app, id) }, h("span", { class: "rid" }, id))) : null;
  }
  function coverageTable(app, p) {
    const K = kit(), c = p.coverage;
    const empty = (rows) => rows.filter((r) => !r.stories.length);
    const noStory = h("td", { class: "plan-empty" }, lampEl("caution"), " No story covers it");
    const targets = h("table", { class: "t plan-cov", "data-cov": "targets" }, h("tr", {}, h("th", {}, "Trace target"), h("th", {}, "Stories")),
      c.targets.map((r) => h("tr", { class: r.stories.length ? "" : "empty", "data-target": r.target },
        h("td", {}, K.idChip(r.target)), r.stories.length ? h("td", {}, storyLinks(app, r.stories)) : noStory.cloneNode(true))));
    const comps = h("table", { class: "t plan-cov", "data-cov": "components" }, h("tr", {}, h("th", {}, "Component"), h("th", {}, "Stories")),
      c.components.map((r) => h("tr", { class: r.stories.length ? "" : "empty", "data-component": r.name },
        h("td", {}, DES[app] && DES[app].components.some((x) => x.name === r.name) ? h("a", { class: "ref-chip plan-comp", onclick: () => toComponent(app, r.name) }, r.name) : h("span", { class: "ref-chip plan-comp" }, r.name)),
        r.stories.length ? h("td", {}, storyLinks(app, r.stories)) : noStory.cloneNode(true))));
    const a = empty(c.targets).length, b = empty(c.components).length;
    return [h("p", { class: "plan-sum" + (a + b ? " bad" : "") }, a + b ? lampEl("caution") : null,
      ` ${c.targets.length - a} of ${plural(c.targets.length, "trace target")} covered by a story`, a ? `, ${a} with no story` : "",
      c.components.length ? `; ${c.components.length - b} of ${plural(c.components.length, "component")} have a task` : "", b ? `, ${b} with none` : "", ". ",
      h("span", { class: "heuristic" }, "Computed from each story's own Traces to line and its tasks' components, then held against the plan's Coverage table.")),
    h("div", { class: "plan-cov-grid" }, h("div", { class: "plan-cov-box" }, targets), h("div", { class: "plan-cov-box" }, comps))];
  }
  /* The count of what the reader could not make of the plan, always shown. The list it opens is collapsed until asked for,
     so a long list never fills the page before the plan does. */
  function problemsChip(p, list) {
    const n = p.problems.length, un = p.unresolved.length, some = n || un;
    const say = (shown) => (n ? `${plural(n, "line")} this page could not read — ${shown ? "hide" : "show"}` : "read with no problems");
    const label = h("span", {}, say(false));
    return h("button", { class: "chip d-problems" + (some ? " some" : ""), "data-problems": n, "aria-expanded": "false", title: "What this page could not read in the plan, or found that disagrees with itself",
      onclick: (ev) => {
        list.hidden = !list.hidden;
        label.textContent = say(!list.hidden);
        ev.currentTarget.setAttribute("aria-expanded", String(!list.hidden));
      } }, Icons.el(some ? "audit" : "consent"), label,
    un ? h("span", { class: "ct" }, ` · ${un} not in the vault`) : null);
  }
  function problemsList(p) {
    const n = p.problems.length + p.unresolved.length;
    return h("div", { class: "plan-problems", id: "plan-problems", hidden: true, "data-count": n },
      h("ol", { class: "in-problems" }, p.problems.map((t) => h("li", {}, h("span", { class: "in-line" }, "the plan"), t)),
        p.unresolved.map((u) => h("li", {}, h("span", { class: "in-line" }, u.story), h("b", {}, u.id), " is traced, but the vault holds no such thing"))));
  }
  const section = (title, count, ...kids) => h("section", { class: "plan-sec" }, h("h3", {}, title, count !== null && count !== undefined ? h("span", { class: "ct" }, " " + count) : null), ...kids.flat().filter(Boolean));

  function barOf(app, p, list) {
    const t = p.totals;
    const tickets = p.hasTickets ? openLink([Icons.el("docs"), "Tickets"], p.ticketsHref, p.ticketsVaultPath, "The tickets file tools/breakdown_to_tickets.py wrote beside the plan", "btn quiet plan-tickets") : null;
    const file = openLink([Icons.el("docs"), "Open the plan"], p.href, p.vaultPath, p.file);
    return h("div", { class: "plan-bar" },
      h("div", { class: "plan-kpis" }, ...[["stories", t.stories], ["tasks", t.tasks]].map(([w, n]) => h("div", { class: "plan-kpi", "data-kpi": w }, h("b", {}, n), h("span", {}, w)))),
      h("div", { class: "plan-acts" }, statusPill(p), problemsChip(p, list), file, tickets,
        h("button", { class: "btn plan-copy", title: "The same CSV tools/breakdown_to_tickets.py writes to tickets.csv, ready to paste into Jira's CSV import", onclick: () => copyCsv(app) }, "Copy as Jira CSV")));
  }

  /* ------------------------------------------------------------ the level */
  function render(stage, app) {
    const p = plan(app), K = kit();
    if (!p) {
      stage.dataset.plan = "none";
      stage.append(K.chipCard("docs", "No build plan yet.", h("span", {}, "The team's work-breakdown skill writes ", h("code", {}, "docs/plan/<slug>-breakdown.md"), " after the tech design. Build with ",
        h("code", {}, `--breakdown ${D.map.apps.find((a) => a.key === app).id}=<team repo>/docs/plan/<slug>-breakdown.md`), ", or set ", h("code", {}, "breakdown:"), " on the app's page (or ", h("code", {}, "breakdowns:"),
        " in .planner.yaml); with the design loaded the build also looks beside it. Context, Containers and Components still draw."),
        h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => K.open(app, "components") }, "Components, from the team's design"))));
      return;
    }
    stage.dataset.plan = p.status || "unknown";
    const list = problemsList(p), page = h("div", { class: "plan-page", id: "plan-page" }, barOf(app, p, list), list);
    if (p.gaps.length) page.append(h("div", { class: "plan-gaps" }, p.gaps.map((g) => h("div", { class: "in-gap" }, h("b", {}, g.id || "a gap"), " ", K.prose(g.note)))));
    page.append(section("Build order", plural(p.stories.length, "story", "stories"), h("p", { class: "plan-hint" }, "In the order the plan says to build. A story with a lamp is waiting on an open question in the vault, in that question's colour."), buildOrder(app, p)));
    page.append(section("What waits on what", null, h("p", { class: "plan-hint" }, "An arrow runs from what blocks a story to the story. Questions and outside parties sit at the top; the drawing fits the width and grows taller."), dependencyView(app, p)));
    page.append(section("Coverage", null, coverageTable(app, p)));
    page.append(section("Not planned", p.notPlanned.length, p.notPlanned.length ? h("ul", { class: "plan-np" }, p.notPlanned.map((n) => h("li", {}, K.prose(n)))) : h("div", { class: "p-empty-line" }, "The plan lists nothing under Not planned.")));
    stage.append(page);
    K.placeDrawings();
  }

  return { render, st, readiness, readinessPill, built: (id) => BUILT[id] || [], planWord, reveal, copyCsv, sink, blockedOn, plan, statusPill, unclosedLevel, panel: panelFor, panelTitle };
})();
