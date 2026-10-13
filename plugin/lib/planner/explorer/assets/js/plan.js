/* Build plan: the fourth level of Inside this app (DESIGN-INSIDE.md), the team's work breakdown drawn beside its design.

   - A lane of story cards in build order: what each is, its size, and what blocks it. A story blocked by an open vault
     question is lit with that question's lamp (attention's, not the plan's); one blocked by an outside party says so.
     A card opens to its acceptance criteria, its trace chips (the same vault links the design's chips use) and its
     tasks, each with a size chip and a component chip that jumps to that component in level 3.
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
  const SIZES = ["S", "M", "L"], POINTS = { S: 2, M: 5, L: 8 };  // the tool's mapping (tools/breakdown_to_tickets.py); sizes are for ordering
  const st = { open: new Set() };
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
      counts: `${plural(t.stories, "story", "stories")}, ${plural(t.tasks, "task")}, ${plural(t.points, "point")}` };
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
    st.open.add(id);
    if (!(App.view === "inside" && Inside.st.app === app && Inside.st.level === "plan")) Inside.open(app, "plan", { keepTrail: true, still: true });
    else $$(`.plan-card[data-story="${CSS.escape(id)}"]`).forEach((c) => { c.classList.add("open"); $(".plan-toggle", c).setAttribute("aria-expanded", "true"); });
    const card = $(`.plan-card[data-story="${CSS.escape(id)}"]`);
    if (card) card.scrollIntoView({ block: "nearest", inline: "center" });
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
    const p = plan(app), rows = p.stories.length + p.totals.tasks;
    try { await sink.write(p.csv); toast(`Copied the Jira CSV: ${plural(rows, "row")}, as tools/breakdown_to_tickets.py writes it.`); }
    catch (e) { console.warn("[plan] could not copy the CSV:", e); toast("This page could not reach the clipboard. Open the Tickets file instead, or run tools/breakdown_to_tickets.py."); }
  }

  /* ------------------------------------------------------------ small pieces */
  const sizeChip = (size) => h("span", { class: "plan-size s" + size, title: { S: "Small: up to about 2 days", M: "Medium: 3 to 5 days", L: "Large: 1 to 2 weeks" }[size] || "No valid size" }, size || "?");
  const sizeTotal = (text) => (text === "none" ? h("span", { class: "muted small" }, "no tasks")
    : h("span", { class: "plan-total", title: "The sizes of its tasks, largest first" }, text.split("+").map((x, i) => [i ? h("i", {}, "+") : null, sizeChip(x)])));
  const kv = (label, ...kids) => h("div", { class: "plan-kv" }, h("span", { class: "fl" }, label), ...kids);

  function statusPill(p) {
    const gaps = p.gaps.map((g) => g.id).filter(Boolean);
    return h("span", { class: "d-status " + (p.status || "unknown"), title: `The team's plan is ${p.status || "of no known status"}${gaps.length ? ", with " + gaps.join(", ") : ""}` },
      p.status === "complete-with-gaps" ? "complete with gaps" : p.status || "status not read", gaps.length ? h("b", {}, " " + gaps.join(" ")) : null);
  }

  /* What blocks a story, one chip each. A vault question is the vault's own chip with its own lamp. */
  function blocker(app, b) {
    if (b.kind === "story") return h("a", { class: "ref-chip plan-after", "data-after": b.ref, title: `Waits for ${b.ref}`, onclick: () => reveal(app, b.ref) }, "after ", h("span", { class: "rid" }, b.ref));
    if (b.kind === "question") {
      const open = isOpen(UNKNOWN[b.ref]);
      return h("span", { class: "plan-q", "data-question": b.ref }, refChip(keyForId(b.ref)), open ? null : h("span", { class: "muted small" }, " resolved"));
    }
    const label = { outside: "outside party", "plan-question": "open question, named only in the plan", gap: "gap or deferral", other: "not classified" }[b.kind];
    return h("span", { class: "plan-who " + b.kind, "data-blocker": b.kind, title: label }, h("b", {}, label + ": "), b.text);
  }
  function blockedLine(app, story) {
    if (!story.blockers.length) return h("div", { class: "plan-block ready" }, "Nothing blocks it: ready to start.");
    return h("div", { class: "plan-block" }, h("span", { class: "fl" }, "Blocked by"), story.blockers.map((b) => blocker(app, b)));
  }

  function taskRow(app, task) {
    const known = DES[app] && DES[app].components.some((c) => c.name.toLowerCase() === task.component.toLowerCase());
    const name = known ? DES[app].components.find((c) => c.name.toLowerCase() === task.component.toLowerCase()).name : task.component;
    return h("tr", {}, h("td", { class: "plan-task-size" }, sizeChip(task.size)), h("td", {}, task.name),
      h("td", {}, known ? h("a", { class: "ref-chip plan-comp", "data-component": name, title: `Show ${name} in the components`, onclick: () => toComponent(app, name) }, name)
        : h("span", { class: "ref-chip plan-comp dead", title: DES[app] ? "Not a component of the design" : "No design loaded to show it in" }, task.component || "no component")));
  }
  /* What the plan flags on a story, as small labelled badges: a question only the design can answer, and a clash with an
     epic criterion, named by the criterion's title and not just its ID. The full text is in the card's body. */
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
  function storyCard(app, p, story) {
    const lit = unclosedLevel(story), open = st.open.has(story.id), K = kit();
    const body = h("div", { class: "plan-card-body" },
      story.criteria.length ? h("div", {}, h("div", { class: "fl" }, "Acceptance criteria"), h("ul", { class: "plan-ac" }, story.criteria.map((c) => h("li", {}, K.prose(c))))) : h("div", { class: "gap" }, "No acceptance criteria in the plan."),
      flagNotes(story),
      h("div", { class: "fl" }, "Traces to"), h("div", { class: "plan-traces" }, story.traces.map((id) => K.idChip(id))),
      h("div", { class: "fl" }, "Tasks"),
      h("table", { class: "plan-tasks" }, story.tasks.map((t) => taskRow(app, t))));
    const toggle = h("button", { class: "btn tiny plan-toggle", "aria-expanded": String(open), onclick: () => {
      const now = card.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(now));
      if (now) st.open.add(story.id); else st.open.delete(story.id);
    } }, "Tasks and criteria");
    const card = h("article", { class: "plan-card" + (open ? " open" : "") + (lit ? " lit " + lit : ""), "data-story": story.id, "data-order": story.order || "", id: `plan-${app}-${story.id}` },
      h("header", {}, h("span", { class: "plan-n", title: story.order ? `Number ${story.order} in the build order` : "Not in the build order" }, story.order || "–"), h("b", { class: "plan-id" }, story.id),
        lit ? lampEl(lit, "Blocked by an open question: its lamp, from attention") : null, h("span", { class: "spacer" }), sizeTotal(story.size)),
      h("h4", {}, story.name),
      h("div", { class: "plan-meta muted small" }, `${plural(story.tasks.length, "task")} · ${plural(story.points, "point")} · ${plural(story.traces.length, "trace")}`),
      blockedLine(app, story),
      flagBadges(story),
      h("div", { class: "plan-glance" }, story.traces.slice(0, 3).map((id) => K.idChip(id)), story.traces.length > 3 ? h("span", { class: "muted small" }, ` +${story.traces.length - 3}`) : null),
      toggle, body);
    return card;
  }
  function lane(app, p) {
    const out = [];
    p.stories.forEach((story, i) => { if (i) out.push(h("span", { class: "plan-then", "aria-hidden": "true" }, "›")); out.push(storyCard(app, p, story)); });
    return h("div", { class: "plan-lane", role: "list", "aria-label": "Stories in build order" }, out);
  }

  /* ------------------------------------------------------------ the dependency view */
  function dependencyView(app, p) {
    const K = kit(), holder = h("div", { class: "plan-dag", id: "plan-dag" }), frame = h("div", { class: "inside-frame plan-dag-frame" }, holder);
    const nodes = p.stories.map((story) => ({ id: "s:" + story.id, kind: "story", w: 220, h: 66, story })), edges = [], stubs = {};
    const stubFor = (b) => {
      const id = `x:${b.kind}:${b.ref || b.text}`;
      if (!stubs[id]) { stubs[id] = true; nodes.push({ id, kind: "outer", side: "in", w: 184, h: 54, b }); }
      return id;
    };
    for (const story of p.stories) for (const b of story.blockers) {
      if (b.kind === "story") { if (p.stories.some((x) => x.id === b.ref)) edges.push({ from: "s:" + b.ref, to: "s:" + story.id, title: `${story.id} is blocked by ${b.ref}` }); continue; }
      edges.push({ from: stubFor(b), to: "s:" + story.id, soft: true, lit: b.kind === "question" && isOpen(UNKNOWN[b.ref]) ? levelForKey(keyForId(b.ref)) : "", title: `${story.id} is blocked by ${b.text}` });
    }
    const lay = K.layered(nodes, edges, { gapX: 96, gapY: 26, minColW: 184, dir: "LR" });
    const svg = s("svg", { class: "inside-svg cockpit plan-dag-svg", role: "img", "aria-label": `${titleOf(app)}'s stories, each after the stories that block it` }, holder);
    K.defsFor(svg);
    K.drawLayout(svg, lay, {
      story: (g, b) => {
        const story = b.node.story, lit = unclosedLevel(story), grp = s("g", { class: "in-node in-box plan-node", tabindex: 0, role: "button", "data-story": story.id, "aria-label": `${story.id} ${story.name}` }, g);
        s("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 10, class: "in-box-face" + (lit ? " lit " + lit : "") }, grp);
        s("text", { x: b.x + 14, y: b.y + 24, class: "in-box-name plan-id" }, grp).textContent = story.id;
        s("text", { x: b.x + b.w - 14, y: b.y + 24, "text-anchor": "end", class: "in-box-meta" }, grp).textContent = story.size;
        s("text", { x: b.x + 14, y: b.y + 46, class: "in-box-sub" }, grp).textContent = K.fit(story.name, b.w - 28, 11.5);
        s("title", {}, grp).textContent = `${story.id} ${story.name}\n${story.size}, ${plural(story.points, "point")}`;
        grp.addEventListener("click", () => reveal(app, story.id));
        grp.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); reveal(app, story.id); } });
      },
      outer: (g, b) => {
        const x = b.node.b, grp = s("g", { class: "in-node in-stub plan-outer " + x.kind, "data-blocker": x.kind, "aria-label": x.text }, g);
        s("path", { d: `M${b.x + 8},${b.y}H${b.x + b.w - 8}L${b.x + b.w},${b.y + 8}V${b.y + b.h - 8}L${b.x + b.w - 8},${b.y + b.h}H${b.x + 8}L${b.x},${b.y + b.h - 8}V${b.y + 8}Z`, class: "in-stub-face" }, grp);
        const level = x.kind === "question" && isOpen(UNKNOWN[x.ref]) ? levelForKey(keyForId(x.ref)) : "";
        if (level && level !== "dark") s("circle", { cx: b.x + 17, cy: b.y + 18, r: 5.5, class: "plan-dot " + level }, grp);
        s("text", { x: b.x + (level && level !== "dark" ? 30 : 14), y: b.y + 22, class: "in-box-name small" }, grp).textContent = K.fit(x.kind === "question" ? x.ref : { outside: "Outside party", "plan-question": "Plan's open question", gap: "Gap or deferral", other: "Not classified" }[x.kind], b.w - 44, 12.5, 600);
        s("text", { x: b.x + 14, y: b.y + 41, class: "in-box-sub" }, grp).textContent = K.fit(x.kind === "question" ? (E[keyForId(x.ref)] || {}).title || x.text : x.text, b.w - 24, 11);
        s("title", {}, grp).textContent = x.text;
      },
    });
    const b = K.boundsOf(Object.values(lay.box));
    holder.style.height = Math.round(clamp(b.y1 - b.y0 + 120, 220, 520)) + "px";
    const first = Object.values(lay.box).find((x) => x.node.kind === "story");
    K.sized(svg, holder, b, 24, { open: "read", key: "plan", focus: first });  // names stay readable; the drawing scrolls, with its minimap, when it is wider than the room
    return frame;
  }

  /* ------------------------------------------------------------ coverage, not planned, totals */
  function storyLinks(app, ids) {
    return ids.length ? ids.map((id) => h("a", { class: "ref-chip plan-after", onclick: () => reveal(app, id) }, h("span", { class: "rid" }, id))) : null;
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
      h("div", { class: "plan-kpis" }, ...[["stories", t.stories], ["tasks", t.tasks], ["points", t.points]].map(([w, n]) => h("div", { class: "plan-kpi", "data-kpi": w }, h("b", {}, n), h("span", {}, w))),
        h("div", { class: "plan-by-size", title: "Tasks by size; points are S=2, M=5, L=8, the tool's mapping, for ordering and not a commitment" }, SIZES.map((z) => h("span", { class: "plan-by", "data-size": z }, sizeChip(z), ` ${t.bySize[z].tasks} · ${t.bySize[z].points} pts`)))),
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
    page.append(section("Build order", plural(p.stories.length, "story", "stories"), h("p", { class: "plan-hint" }, "Left to right, in the order the plan says to build. A lit card is waiting on an open question in the vault, in that question's colour."), lane(app, p)));
    page.append(section("What waits on what", null, h("p", { class: "plan-hint" }, "An arrow runs from what blocks a story to the story. Questions and outside parties sit at the left edge."), dependencyView(app, p)));
    page.append(section("Coverage", null, coverageTable(app, p)));
    page.append(section("Not planned", p.notPlanned.length, p.notPlanned.length ? h("ul", { class: "plan-np" }, p.notPlanned.map((n) => h("li", {}, K.prose(n)))) : h("div", { class: "p-empty-line" }, "The plan lists nothing under Not planned.")));
    stage.append(page);
    K.placeDrawings();
  }

  return { render, st, readiness, readinessPill, built: (id) => BUILT[id] || [], planWord, reveal, copyCsv, sink, blockedOn, plan, statusPill, unclosedLevel };
})();
