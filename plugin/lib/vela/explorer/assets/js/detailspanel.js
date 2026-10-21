/* The Details panel: one scope at a time, with a trail back, for any page that has a diagram and a summary behind it.

   The Violation this exists to prevent is a Distributed Monolith of panel behavior: if each page grows its own copy of
   "pick a thing, show only that thing, keep a way back, clear on Escape", the copies drift and every page behaves a
   little differently. The panel owns the behavior; a page owns only what it says.

   What the panel owns
   - The two tabs, Details and What's waiting.
   - The trail. The page's summary is the root; every thing shown is a key in App.trail (the same trail go() keeps), so
     a link, a chip with data-ref, a node wired with Nodes.wire and the browser's own history all land in one place.
     The trail reads "Design › NoteClient › Note request", each earlier name returns there, and "← back" pops one.
   - Open. A thing with a view of its own (another app, a flow) shows an Open button in its Details header. The first
     click on the thing only shows its details; Open is the second click and is the one that jumps.
   - Escape, and the page calling clear() on empty space, return to the summary. Hovering never changes the panel.
   - Falling back: a key the page does not own (a vault page, a contract) is drawn by Panel.keyNodes, so the panel
     is never empty and a page need not know how every vault thing looks.

   What a page supplies (DetailsPanel.register(name, spec)); every function may be asked many times and must be cheap
     view      the App.view this page lives on                                    (required)
     live()    true while the page wants this panel (e.g. it has a design loaded) (required)
     root      the summary's key, which is App.root while live                    (the page sets App.root itself)
     rootLabel the summary's name in the trail, e.g. "Design"                     (required)
     summary() nodes for nothing picked: the page at a glance                     (required)
     owns(key) true for a key the page draws itself                               (required)
     detail(key)  nodes for an owned key; its first .p-head may take the Open button
     label(key)   the key's short name in the trail (owned keys; others use titleOf)
     open(key)    null, or {label, run} when the key has a view of its own
     waiting(key) nodes for the What's waiting tab, given what is picked (or null)  (required)
     waitingCount() the number on the tab                                        (required)
     focus(key)   paint the diagram for what is picked, or clear it when null     (required)
     rendered()   called after Details is drawn, for a drawing that must be placed once it is on the page
   and it calls DetailsPanel.show(key) to pick (reset: true starts a new trail), .clear() for empty space, and
   .link(key, text) for an inline link that pushes onto the trail.

   Used by: Inside this app (inside.js), Flows, the Apps map, Who to ask and Decisions (their view-*.js files). The
   things those four pages share (a contract, a question, a person, an outside service, an app, the What's waiting
   tab, what a pick holds up, and which thing has an Open) are in PlanDetails below, so they are written once. */
const DetailsPanel = (() => {
  const pages = {};
  const st = { tab: "details", seen: "" };
  const current = () => Object.values(pages).find((p) => p.view === App.view && p.live()) || null;
  const active = () => !!current();
  const topKey = () => App.trail[App.trail.length - 1] || "";

  function register(name, spec) {
    for (const need of ["view", "live", "rootLabel", "summary", "owns", "waiting", "waitingCount", "focus"]) {
      if (spec[need] === undefined) throw new Error(`[details panel] ${name} must supply ${need}`);
    }
    pages[name] = spec;
  }

  const labelOf = (spec, key) => (spec.owns(key) && spec.label ? spec.label(key) : titleOf(key));
  const refresh = () => { Panel.render(); const p = current(); if (p) p.focus(topKey() || null); };

  /* Pick a thing: its details show, the trail keeps the thread, and the diagram lights what it touches. */
  function show(key, opts = {}) {
    st.tab = "details";
    go(key, opts);  // go() reveals a hidden panel, keeps the trail and renders; the page's highlight follows from it
    const p = current();
    if (p) p.focus(topKey() || null);
  }
  function back() {
    if (!App.trail.length) return;
    App.trail = App.trail.slice(0, -1);
    st.tab = "details"; refresh();
  }
  function trailTo(i) { App.trail = App.trail.slice(0, i + 1); st.tab = "details"; refresh(); }
  /* Back to the page's summary: empty space, Escape, the crumb that names the page. */
  function clear() {
    if (!App.trail.length && st.tab === "details") return false;
    App.trail = []; st.tab = "details"; refresh();
    return true;
  }
  /* A page was entered fresh: nothing is picked and Details shows. */
  function reset() { st.tab = "details"; st.seen = ""; }
  function setTab(tab) { st.tab = tab; Panel.render(); const p = current(); if (p) p.focus(topKey() || null); }
  /* An inline link inside Details that pushes the thing onto the trail. A button, so the keyboard has it. */
  function link(key, text, title) {
    return h("button", { class: "linkish dp-link", type: "button", "data-dp": key, title: title || null, onclick: (ev) => { ev.stopPropagation(); show(key); } }, text);
  }

  function tabs(spec) {
    const n = spec.waitingCount();
    const tab = (id, text) => h("button", { role: "tab", "aria-selected": String(st.tab === id), "aria-pressed": String(st.tab === id), "data-dp-tab": id, onclick: () => setTab(id) }, text);
    return h("div", { class: "p-homes dp-tabs", role: "tablist", "aria-label": "Details" }, tab("details", "Details"), tab("waiting", n ? `What's waiting ${n}` : "What's waiting"));
  }
  function trail(spec) {
    const keys = App.trail, last = keys.length - 1;
    const first = h("button", { class: "linkish", type: "button", onclick: () => clear() }, typeof spec.rootLabel === "function" ? spec.rootLabel() : spec.rootLabel);
    const crumbs = keys.map((k, i) => [h("span", { class: "sep" }, "›"),
      i === last ? h("span", { class: "cur" }, shorten(labelOf(spec, k), 28)) : h("button", { class: "linkish", type: "button", onclick: () => trailTo(i) }, shorten(labelOf(spec, k), 22))]);
    const prev = keys.length > 1 ? labelOf(spec, keys[last - 1]) : null;
    return [h("nav", { class: "crumbs dp-trail", "aria-label": "Trail" }, first, ...crumbs),
      h("button", { class: "btn dp-back", type: "button", onclick: () => back() }, prev ? `← back to ${shorten(prev, 26)}` : "← back to the summary")];
  }
  /* The Open button goes in the thing's header, as the page described it; without a header it leads the body. */
  function withOpen(spec, key, nodes) {
    const o = spec.open ? spec.open(key) : null;
    if (!o) return nodes;
    const btn = h("button", { class: "btn dp-open", type: "button", title: o.title || null, onclick: () => o.run() }, o.label || "Open");
    const header = nodes.find((n) => n && n.classList && n.classList.contains("p-head"));
    const actions = header && header.querySelector(".p-actions");  // a header that has buttons already keeps them, Open first
    if (actions) actions.prepend(btn); else if (header) header.append(h("div", { class: "p-actions" }, btn)); else nodes.unshift(btn);
    return nodes;
  }

  function render(root) {
    const spec = current();
    const key = topKey();
    if (key !== st.seen) { st.seen = key; st.tab = "details"; }  // a new thing is picked: show it
    root.append(tabs(spec));
    if (st.tab === "waiting") { root.append(...[].concat(spec.waiting(key || null)).filter(Boolean)); return; }
    if (key) root.append(...trail(spec));
    const nodes = key ? (spec.owns(key) ? spec.detail(key) : Panel.keyNodes(key)) : spec.summary();
    root.append(...(key ? withOpen(spec, key, nodes.filter(Boolean)) : nodes.filter(Boolean)));
    if (spec.rendered) spec.rendered();
  }

  /* Escape goes back to the summary, unless something nearer wants it: a menu, a field, the full-screen view. */
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape" || ev.defaultPrevented || !active() || Menus.isOpen) return;
    if (ev.target.closest && ev.target.closest("input,textarea,select")) return;
    if (document.querySelector("#main.inside-full")) return;  // the page leaves full screen first
    if ($("#overlay") && !$("#overlay").hidden) return;
    if (clear()) { ev.preventDefault(); }
  });

  return { register, active, current, render, show, back, clear, trailTo, setTab, link, refresh, reset, get tab() { return st.tab; } };
})();

/* What Flows, the Apps map, Who to ask and Decisions say about the same few things, written once.

   The Violation this exists to prevent is a Distributed Monolith of wording: four pages each describing "a contract"
   or "a question" in their own copy, so a fix to one (say, listing every way a contract can answer) misses three.
   A Leaky Narrative is the other risk: a contract shown as CON-004 sends the reader to the vault. Every name here is
   a title or a person's name; an ID only travels as a key, never as text.

   Each builder answers one key and says "Not recorded" where the plan is silent; nothing is made up to fill a section. */
const PlanDetails = (() => {
  const NEEDS = ["warning", "caution"];
  const sec = (title, n, ...kids) => Panel.section(title, n, ...kids);
  const quiet = (text) => Panel.empty(text);
  const link = (key, text) => DetailsPanel.link(key, text || titleOf(key));
  const joined = (nodes) => nodes.flatMap((n, i) => (i ? [", ", n] : [n]));
  const head = (kind, title, ...meta) => { const m = meta.filter(Boolean); return h("div", { class: "p-head" }, h("div", { class: "kind" }, kind), h("h2", {}, title), m.length ? h("div", { class: "p-meta" }, ...m) : null); };
  const bullets = (rows) => h("ul", { class: "mini-list" }, rows.map((r) => h("li", {}, ...[].concat(r))));
  /* A prose block that may be taller than its room folds with Show more, so no sentence just stops. */
  const prose = (content, isHtml) => { const t = h("div", { class: "prose-text", ...(isHtml ? { html: content } : {}) }, isHtml ? null : content); return foldProse(h("div", { class: "prose" }, t), t); };
  /* The section's own page, beside the page's visual, under the page's summary; its header carries the one Read full page. */
  function aboutSection() {
    const pk = typeof Nav !== "undefined" ? Nav.pageBeside() : "";
    if (!pk || !D.reader[pk]) return null;
    return h("section", { class: "p-sec dp-about" }, h("h3", {}, "About this section"), ...Panel.keyNodes("read:" + pk));
  }
  /* A flow in a list: its name (details), its Open, and Present from the first step that touches `key`. */
  function flowRow(flow, key, view) {
    const at = firstStepTouching(FLOW[flow], key);
    return h("div", { class: "flow-chip" }, ...openRow(flow, view), " ",
      h("button", { class: "btn primary present-btn tiny", type: "button", title: "Present this flow full screen", onclick: () => Flows.present(flow, at) }, at > 0 ? `▶ Present from step ${FLOW[flow].steps[at].n}` : "▶ Present"));
  }
  const readLink = (key) => { const pk = typeof Reader !== "undefined" ? Reader.keyFor(key) : ""; return pk ? h("div", { class: "p-note" }, link("read:" + pk, `Read ${titleOf(key)}'s page`)) : null; };

  /* ---- keys the shared builders own */
  const stepKey = (flow, i) => `flowstep:${encodeURIComponent(flow)}|${i}`;
  const isStep = (k) => k.startsWith("flowstep:");
  const parseStep = (k) => { const [f, i] = k.slice(9).split("|"); return { flow: decodeURIComponent(f), i: +i }; };
  const personKey = (who) => "person:" + who;
  const whoOf = (k) => (k.startsWith("person:") ? k.slice(7) : k.startsWith("owner:") ? k.slice(6) : "");
  const askedOf = (who) => D.asks.filter((u) => u.ask.key === who || (u.ask.owner || "") === who);
  const personLabel = (who) => { const u = askedOf(who)[0]; return u ? u.ask.name : personName(who); };
  const isQuestion = (k) => !!(UNKNOWN[k] && ASK[k]);
  const kindOf = (k) => (ent(k) || {}).kind;
  const isOutside = (k) => ["party", "external"].includes(kindOf(k));
  const isRelease = (k) => k.startsWith("release:") && !!ent(k);
  const owns = (k) => isStep(k) || !!whoOf(k) || !!CONTRACT[k] || isQuestion(k) || isOutside(k) || !!APPS[k] || isRelease(k);
  const label = (k) => {
    if (whoOf(k)) return personLabel(whoOf(k));
    if (isStep(k)) { const p = parseStep(k), s = FlowKit.flowOf(p.flow).steps[p.i]; return s ? `Step ${s.n}: ${s.short}` : "A step"; }
    return titleOf(k);
  };

  /* ---- what a pick holds up, for the page to light: the apps, contracts and flows on its drawing */
  function held(key) {
    const out = { apps: new Set(), contracts: new Set(), flows: new Set() };
    const add = (k) => {
      if (CONTRACT[k]) { out.contracts.add(k); [CONTRACT[k].provider, ...CONTRACT[k].consumers].forEach((x) => out.apps.add(x)); }
      else if (NODE[k]) out.apps.add(k);
      else if (FLOW[k]) { out.flows.add(k); flowStations(FLOW[k]).forEach((x) => out.apps.add(x)); }
    };
    if (!key) return out;
    if (isQuestion(key)) {
      const u = UNKNOWN[key];
      [...u.blocks, ...u.holds].forEach(add);
      for (const [app, a] of Object.entries(D.apps)) if (a.questions.some((q) => q.id === key)) out.apps.add(app);
    } else if (whoOf(key)) askedOf(whoOf(key)).forEach((u) => held(u.id).apps.forEach((x) => out.apps.add(x)));
    else add(key);
    return out;
  }

  /* ---- which thing has a view of its own, and where the Open button goes. Null means this page is that view. */
  function openFor(key, view) {
    if (APPS[key] && typeof Inside !== "undefined") return { label: "Open", title: `Go inside ${titleOf(key)}`, run: () => Inside.open(key, "context", {}) };
    const jump = (title, to) => ({ label: "Open", title, run: () => go(to || key, { reset: true, reveal: true }) });
    if (FLOW[key]) return view === "flows" ? null : jump("Play it on the Flows view");
    if (CONTRACT[key]) {
      if (view !== "map") return jump("Show it on the map");
      const flow = flowsFor(key).find((r) => FLOW[r.flow]);
      return flow ? jump(`Play ${titleOf(flow.flow)}, a flow that uses it`, flow.flow) : null;
    }
    if (isQuestion(key)) return view === "asks" ? null : jump("See it in Who to ask");
    if (whoOf(key)) return view === "asks" || typeof Asks === "undefined" ? null : { label: "Open", title: "Go to their place on Who to ask", run: () => Asks.meet(whoOf(key)) };
    if (kindOf(key) === "decision") return view === "decisions" ? null : jump("See it in the decision log");
    if (isRelease(key)) return view === "releases" ? null : { label: "Open", title: "See it on the Releases view", run: () => Nav.openRelease(+key.slice(8)) };
    return null;
  }
  /* A link that shows details, and beside it the Open that jumps, for a list of things each with a view of its own. */
  function openRow(key, view, text) {
    const o = openFor(key, view);
    return [link(key, text), o ? h("button", { class: "btn tiny dp-open-row", type: "button", title: o.title || null, "aria-label": `${o.label} ${text || titleOf(key)}`, onclick: () => o.run() }, o.label) : null];
  }

  /* ---- an app: the panel's own account of it (In these flows and Talks to lead), with the Open in its header */
  function appNodes(key) {
    const nodes = Panel.keyNodes(key);
    for (const n of nodes) if (n.classList && n.classList.contains("p-head")) {
      const actions = n.querySelector(".p-actions");
      if (actions) { actions.querySelectorAll(".inside-btn").forEach((b) => b.remove()); if (!actions.children.length) actions.remove(); }
    }
    return nodes;
  }

  /* ---- a contract: who provides it and calls it, every way it can answer, what it carries, what waits on it */
  function contractNodes(key, view) {
    const c = CONTRACT[key], ways = (D.contractAnswers || {})[key] || [], blocked = D.blockedBy[key] || [];
    const flows = flowsFor(key).filter((r) => FLOW[r.flow]);
    const level = levelOf(key);
    const answers = ways.length ? h("ul", { class: "dp-ways" }, ways.map((w) => h("li", { class: w.error ? "err" : "" },
      h("b", {}, w.case), w.error ? h("span", { class: "pill" }, "error") : null, h("div", { class: "ml-sub" }, [w.when ? `When ${w.when}. ` : "", w.says || ""].join("")))))
      : quiet("Not recorded: the contract has no table of how it can answer yet.");
    return [head("Contract", c.title, h("span", { class: "pill" }, `${titleOf(c.provider)} → ${c.consumers.map(titleOf).join(", ") || "no one recorded"}`),
      level !== "dark" ? levelPill(level) : null, statePill(c.state)),
    h("div", { class: "p-body" },
      sec("Who provides it, who calls it", null, bullets([[h("b", {}, "Provided by: "), link(c.provider)],
        [h("b", {}, "Called by: "), ...(c.consumers.length ? joined(c.consumers.map((k) => link(k))) : ["Not recorded"])]])),
      sec("Ways it can answer", ways.length || null, answers),
      sec("What it carries", null, c.crosses ? h("div", { class: "crosses", html: c.crosses }) : quiet("Not recorded: nothing says yet what data this contract carries.")),
      sec("What's waiting on it", blocked.length || null, blocked.length ? bullets(blocked.map((id) => [lampEl(unknownLevel(id)), " ", link(id)])) : quiet("Nothing is waiting on it.")),
      sec("Flows that use it", flows.length || null, flows.length ? flows.map((r) => flowRow(r.flow, key, view)) : quiet("No flow uses it yet.")),
      Library.backlinks(key),
      readLink(key))];
  }

  /* ---- an outside service: no status of its own, so what it provides and where it appears */
  function outsideNodes(key, view) {
    const provided = D.map.contracts.filter((c) => c.provider === key), flows = flowsFor(key).filter((r) => FLOW[r.flow]);
    const said = EXTERNAL[key] && EXTERNAL[key].said !== EXTERNAL[key].title ? EXTERNAL[key].said : "";
    return [head("Outside service", titleOf(key)),
      h("div", { class: "p-body" },
        said ? sec("As the contract words it", null, prose(said)) : null,
        sec("Contracts it provides", provided.length || null, provided.length ? bullets(provided.map((c) => openRow(c.id, view, c.title))) : quiet("It doesn't provide any contract.")),
        sec("Flows it appears in", flows.length || null, flows.length ? flows.map((r) => flowRow(r.flow, key, view)) : quiet("No flow names it yet.")),
        Library.backlinks(key),
        h("div", { class: "p-note" }, "An outside service has no status of its own. Check the contracts that connect to it."),
        readLink(key))];
  }

  /* ---- a question: what is asked, who answers and by when, and what it holds up */
  function questionNodes(key, view) {
    const u = UNKNOWN[key], a = ASK[key], open = isOpen(u), title = titleOf(key), flows = flowsFor(key).filter((r) => FLOW[r.flow]);
    const knock = u.holds.length - u.blocks.length;
    return [head(open ? "Open question" : "Answered question", title, open ? levelPill(a.light.level, dueText(u.askBy)) : h("span", { class: "pill" }, "Answered")),
      h("div", { class: "p-body" },
        a.question && a.question !== title ? h("div", { class: "big-q" }, a.question) : null,
        sec("Who to ask", null, h("div", {}, link(personKey(a.ask.key), a.ask.name), " ", h("span", { class: a.ask.inferred ? "heuristic" : "muted" }, a.ask.rule.startsWith(a.ask.name) ? a.ask.rule.slice(a.ask.name.length).replace(/^[,:\s]+/, "") : a.ask.rule)),
          h("div", { class: "ml-sub" }, "Owner: " + (u.owner ? peopleWords(u.owner) : "Not recorded"))),
        open ? sec("Answer needed by", null, h("div", {}, isDate(u.askBy) ? `${day(u.askBy)}, ${dueText(u.askBy)}` : dueText(u.askByText), u.opened ? h("span", { class: "muted" }, ` · opened ${day(u.opened)}`) : null)) : null,
        sec("It holds up", u.blocks.length || null, u.blocks.length ? [bullets(u.blocks.map((k) => openRow(k, view))), knock > 0 ? h("div", { class: "ml-sub" }, `Through these it holds up ${plural(knock, "more thing")}.`) : null]
          : quiet(`Not recorded: it doesn't say what it holds up${u.blocksText ? `; the question itself says it blocks "${u.blocksText}"` : ""}.`)),
        flows.length ? sec("Flows it touches", flows.length, flows.map((r) => flowRow(r.flow, key, view))) : null,
        Library.backlinks(key),
        a.outcome ? sec("Answer", null, prose(a.outcome)) : null,
        readLink(key))];
  }

  /* ---- a person: the questions waiting on them, each opening its own details */
  function questionRow(id) {
    const holds = (UNKNOWN[id] || { blocks: [] }).blocks;
    return h("button", { class: "wq", type: "button", "data-oq": id, onclick: () => DetailsPanel.show(id, { reset: true }) },
      h("b", {}, lampEl(unknownLevel(id)), " ", titleOf(id)), h("small", {}, holds.length ? "Holds up " + holds.map(titleOf).join(", ") : "Doesn't say what it holds up"));
  }
  const byDue = (a, b) => cmp(a.askBy || "9999", b.askBy || "9999") || cmp(a.id, b.id);
  function personNodes(key, view) {
    const who = whoOf(key), all = askedOf(who), open = all.filter(isOpen).sort(byDue), done = all.filter((u) => !isOpen(u));
    const first = open.find((u) => isDate(u.askBy));
    return [head("Who to ask", personLabel(who), h("span", { class: "pill" }, plural(open.length, "open question")), first ? h("span", { class: "pill" }, `First due ${day(first.askBy)}`) : null),
      h("div", { class: "p-body" },
        sec("Their open questions", open.length || null, open.length ? open.map((u) => questionRow(u.id)) : quiet("Nothing is waiting on them.")),
        done.length ? sec("Answered", done.length, bullets(done.map((u) => link(u.id)))) : null,
        ownedBy(who))];
  }
  /* What a person owns besides the questions: the pages and items the plan gives them, each a link to its details. */
  function ownedBy(who) {
    const o = D.owners[who], rest = o ? o.owns.filter((k) => ent(k) && !["unknown", "session"].includes(kindOf(k))) : [];
    return rest.length ? sec("What they own", rest.length, bullets(rest.map((k) => link(k)))) : null;
  }

  /* ---- a release: what it ships, which apps and contracts it brings or changes, and what holds it up */
  function releaseNodes(key, view) {
    const j = +key.slice(8), S = D.releases.states[j], c = Releases.changes(j), title = titleOf(key);
    const shipped = (S.rows || []).filter((r) => r.requirement && ent(r.requirement));
    const criteria = (r) => (!r.criteria.length ? "all criteria" : `${r.criteria.length === 1 ? "criterion" : "criteria"} ${r.criteria.join(", ")} of ${r.of}`);
    const touched = [...c.arrive, ...c.change, ...(S.through || [])], held = [...new Set(touched.flatMap((k) => [...(D.blockedBy[k] || []), ...(D.apps[k] ? D.apps[k].questions.map((q) => q.id) : [])]))].filter((id) => UNKNOWN[id] && isOpen(UNKNOWN[id]));
    const group = (heading, keys) => (keys.length ? sec(heading, keys.length, bullets(keys.map((k) => openRow(k, view)))) : null);
    return [head("Release", title, S.target ? h("span", { class: "pill" }, dayYear(S.target)) : h("span", { class: "pill" }, "No date yet"), S.state ? statePill(S.state) : null),
      h("div", { class: "p-body" },
        sec("What it ships", shipped.length || null, shipped.length ? bullets(shipped.map((r) => [link(r.requirement), h("span", { class: "muted" }, " " + criteria(r) + (r.note ? `: ${r.note}` : ""))])) : quiet("Not recorded: no requirement is written against this release yet.")),
        group("New apps", c.arrive), group("Changed apps", c.change), group("Retired apps", c.gone), group("New contracts", c.appear),
        sec("What holds it up", held.length || null, held.length ? held.map(questionRow) : quiet("No open question holds up an app or contract it touches.")),
        readLink("releases"))];
  }

  /* ---- the What's waiting tab: what holds up the pick first, then the rest. "queue" is the one count every page gives
     (Queue.needsYou, E60); "asks" is Who to ask's own board, which lists every open question. */
  function relatedQuestions(key) {
    if (!key) return [];
    if (isStep(key)) {
      const p = parseStep(key), s = FlowKit.flowOf(p.flow).steps[p.i];
      return s ? [...new Set([...s.unknowns.map((x) => x.id), ...s.contracts.flatMap((c) => D.blockedBy[c] || [])])] : [];
    }
    if (isQuestion(key)) return [key];
    if (whoOf(key)) return askedOf(whoOf(key)).filter(isOpen).map((u) => u.id);
    const ids = [...(D.blockedBy[key] || [])];
    if (D.apps[key]) ids.push(...D.apps[key].questions.map((q) => q.id));
    if (FLOW[key]) ids.push(...FLOW[key].unknowns, ...FLOW[key].steps.flatMap((s) => s.unknowns.map((x) => x.id)));
    return [...new Set(ids)];
  }
  const queueIds = () => Queue.items().filter((x) => NEEDS.includes(x.level)).map((x) => x.id);
  const openIds = () => D.asks.filter(isOpen).sort((a, b) => rank(b.light.level) - rank(a.light.level) || b.light.urgency - a.light.urgency || cmp(a.id, b.id)).map((u) => u.id);
  const lit = () => Queue.otherLit().filter((x) => NEEDS.includes(x.light.level));
  const waitingCount = (scope) => (scope === "asks" ? D.counts.openQuestions : Queue.needsYou().n);
  function waitingTab(key, scope) {
    const ids = scope === "asks" ? openIds() : queueIds(), things = scope === "asks" ? [] : lit();
    if (!ids.length && !things.length) return [quiet(scope === "asks" ? "No open question is waiting on an answer." : "Nothing is waiting.")];
    const mine = relatedQuestions(key).filter((id) => ids.includes(id)), rest = ids.filter((id) => !mine.includes(id));
    const thingRow = (x) => h("button", { class: "wq", type: "button", "data-thing": x.key, onclick: () => DetailsPanel.show(x.key, { reset: true }) },
      h("b", {}, lampEl(x.light.level), " ", titleOf(x.key)), h("small", {}, (x.light.reasons.find((r) => r.text) || {}).text || LIGHT[x.light.level].say));
    return [mine.length ? h("div", { class: "gl" }, `Holding up ${label(key)}`) : null, ...mine.map(questionRow),
      (mine.length && rest.length) ? h("div", { class: "gl" }, "Others") : (rest.length ? h("div", { class: "gl" }, "Open questions") : null), ...rest.map(questionRow),
      things.length ? h("div", { class: "gl" }, "Not decided yet") : null, ...things.map(thingRow)].filter(Boolean);
  }

  /* Detail for any key this file owns; a page calls it from its own detail(). */
  function detail(key, view) {
    if (whoOf(key)) return personNodes(key, view);
    if (CONTRACT[key]) return contractNodes(key, view);
    if (isQuestion(key)) return questionNodes(key, view);
    if (isOutside(key)) return outsideNodes(key, view);
    if (isRelease(key)) return releaseNodes(key, view);
    return appNodes(key);
  }

  return { prose, aboutSection, owns, detail, label, held, openFor, openRow, waitingTab, waitingCount, relatedQuestions, questionRow, stepKey, parseStep, isStep, personKey, whoOf, askedOf, head, sec, bullets, quiet, link, joined, readLink, isQuestion, NEEDS, byDue };
})();
