/* The one right-hand panel, on every view. Its default is the section's own page beside its visual, or, where there is none,
   what needs the person viewing (Needs you). Anything picked anywhere opens here with a trail of breadcrumbs back, and every app, contract,
   capability and question lists the flows that cross it, each with a Present button. */
const Panel = (() => {
  const body = () => $("#panel-body");
  function section(title, count, ...kids) {
    const content = kids.flat().filter(Boolean);
    if (!content.length) return null;
    return h("section", { class: "p-sec" }, h("h3", {}, title, count !== null && count !== undefined ? h("span", { class: "ct" }, ` ${count}`) : null), ...content);
  }
  const empty = (text) => h("div", { class: "p-empty-line" }, text);
  const fact = (e, label) => (e.facts || []).find((f) => f.label === label);

  /* A design loaded for the app: its design and the section's page are two homes, picked by tab. */
  function homes() {
    const page = typeof Nav !== "undefined" ? Nav.pageBeside() : "";
    // inside an app with its team's design loaded, the design is a third home
    const design = App.view === "inside" && typeof Inside !== "undefined" ? Inside.designKey() : "";
    if (!design) return null;  // two homes only when a design is loaded; otherwise the section's page is the default, with no tab to pick
    const pick = (root) => { App.root = root; App.trail = []; render(); };
    return h("div", { class: "p-homes", role: "tablist" },
      design ? h("button", { role: "tab", "aria-selected": String(App.root === design), onclick: () => pick(design) }, "The design") : null,
      page ? h("button", { role: "tab", "aria-selected": String(App.root.startsWith("read:")), onclick: () => pick("read:" + page) }, "About this section") : null,
      null);
  }
  /* Where the panel returns to: a picked root, else the section's page beside the visual, else nothing (Needs you). */
  function rootKey() {
    if (App.root !== "lights") return App.root;
    const page = typeof Nav !== "undefined" ? Nav.pageBeside() : "";
    return page ? "read:" + page : "";
  }
  function crumbs() {
    const box = h("nav", { class: "crumbs", "aria-label": "Trail" });
    const root = rootKey(), rootIsPage = root.startsWith("read:") || root.startsWith("inside:");
    box.append(h("a", { onclick: () => { App.trail = []; render(); }, class: App.trail.length ? "" : "cur", title: rootIsPage ? "Back to the page" : "What needs you" },
      rootIsPage ? "◧ " + shorten(titleOf(root), 22) : "◉ Needs you"));
    App.trail.forEach((k, i) => {
      box.append(h("span", { class: "sep" }, "›"));
      box.append(i === App.trail.length - 1 ? h("span", { class: "cur", title: idOf(k) || null }, shorten(titleOf(k), 26)) : h("a", { "data-ref": k, title: idOf(k) ? `${titleOf(k)} (${idOf(k)})` : titleOf(k) }, shorten(titleOf(k), 20)));
    });
    return box;
  }

  /* What a key shows in the panel, as nodes: the one place that knows how each kind of key is drawn, so the home panel
     and a page's own Details panel (detailspanel.js) draw a vault page, a note, a bundle or an inside key alike. */
  function keyNodes(key) {
    if (key.startsWith("read:")) return reading(key);
    if (key.startsWith("node:")) return Nodes.panel(key);
    if (key.startsWith("bundle:")) return bundle(key);
    if (key.startsWith("lib:") && typeof Library !== "undefined") return Library.nodes(key);
    if (key.startsWith("grill:") && typeof Grills !== "undefined") return Grills.nodes(key);
    if (key.startsWith("inside:") && typeof Inside !== "undefined") return Inside.panel(key);
    const e = ent(key);
    if (!e) return [h("div", { class: "p-empty" }, `Nothing in the plan is called ${key}. Try the search box.`)];
    return [head(e), h("div", { class: "p-body" }, ...detail(e))];
  }
  function render() {
    const root = body();
    root.innerHTML = "";
    if (typeof DetailsPanel !== "undefined" && DetailsPanel.active()) { DetailsPanel.render(root); root.scrollTop = 0; return; }  // a page that brings its own Details
    const key = App.trail[App.trail.length - 1] || rootKey() || null;
    const tabs = homes();
    if (tabs) root.append(tabs);
    root.append(crumbs());
    if (App.view === "ask" && !key) root.append(h("p", { class: "p-note ask-hint" }, "A citation in the conversation opens here, so you can read the source beside it."));
    if (!key) { root.append(...home()); root.scrollTop = 0; return; }
    root.append(...keyNodes(key));
    if (!key.startsWith("read:") && !key.startsWith("bundle:")) root.scrollTop = 0;
  }

  /* ------------------------------------------------------------ home: the default summary */
  /* The panel's default summary where no section page sits beside the visual: what needs the person viewing, as the same
     lines the overview opens with. Where a page does sit beside the visual, that page is the default (see render). */
  function home(opts = {}) {
    const out = [h("div", { class: "p-head" }, h("h2", {}, "Needs you"), h("p", { class: "p-lede" }, Needs.lede(opts)))];
    const lines = Needs.panel();
    if (lines) out.push(lines);
    const challenged = typeof Inside !== "undefined" ? Inside.homeSection() : null;
    if (challenged) out.push(challenged);  // Element.append writes a null as the text "null"
    return out;
  }

  /* ------------------------------------------------------------ a page, to read */
  function reading(key) {
    const [pk, anchor] = key.slice(5).split("#"), e = E[pk];
    // No file path in reader text (the wording rule: no file paths or commit hashes): the page is named by its title
    const out = [h("div", { class: "p-head" }, h("div", { class: "kind" }, ["page", "section"].includes(e.kind) ? "Page" : (KIND_WORD[e.kind] || "Page") + " page"),
      h("h2", {}, e.title), linkChips(pk),
      h("div", { class: "p-actions" }, typeof Nav !== "undefined" ? h("button", { class: "btn", onclick: () => Nav.readWide(pk, anchor) }, "Read full page") : null,
        ent(pk) && e.kind !== "section" && e.kind !== "page" ? h("button", { class: "btn", onclick: () => go(pk, {}) }, "About it and what is blocking it") : null,
        // the section's own page opens as a file from the ... menu; a page read here from somewhere else keeps its file link
        typeof Nav !== "undefined" && pk === Nav.sectionPage() ? null : openLink(["Open the page"], D.vault ? D.vault + "/" + e.path : "", e.path, "The page as it is written, in a new tab")))];
    const body = Reader.body(pk, { toc: true });
    out.push(body);
    requestAnimationFrame(() => { if (!Reader.scrollTo(body, anchor)) $("#panel-body").scrollTop = 0; });
    return out;
  }

  /* ------------------------------------------------------------ one thing */
  function head(e) {
    const actions = h("div", { class: "p-actions" });
    if (e.kind === "flow") {
      actions.append(h("button", { class: "btn primary", onclick: () => Flows.present(e.key, 0) }, "▶ Present"),
        h("button", { class: "btn", onclick: () => { showView("flows"); Flows.select(e.key, -1); } }, "Step through"),
        h("button", { class: "btn", title: "Quiz yourself on this flow, step by step", onclick: () => Rehearse.open(e.key) }, "Rehearse this flow"));
    }
    if (onMap(e.key) && App.view !== "map") actions.append(h("button", { class: "btn", onclick: () => { showView("map"); viewDef("map").highlight(e.key); } }, "Show on the map"));
    if (e.kind === "unknown" && App.view !== "asks") actions.append(h("button", { class: "btn", onclick: () => { showView("asks"); viewDef("asks").highlight(e.key); } }, "Show in Who to ask"));
    const readKey = Reader.keyFor(e.key);
    if (readKey) actions.append(h("button", { class: "btn open-page", title: "Read it here, in the plan's own words", onclick: () => go(readKey, {}) }, "Read the page"));
    if (e.kind === "app" && typeof MapView !== "undefined") actions.append(h("button", { class: "btn", onclick: () => Nav.focusApp(e.key) }, "Focus on the map"));
    if (e.kind === "app" && typeof Inside !== "undefined") actions.append(h("button", { class: "btn inside-btn", title: "How this app is built, and the team's plan for building it", onclick: () => Inside.open(e.key, "containers") }, "Inside this app"));
    if ((e.kind === "flow" || e.kind === "contract") && typeof Motion !== "undefined") actions.append(h("button", { class: "btn", title: "Show the route it takes on the map, step by step", onclick: () => Nav.trace(e.key) }, "Show its path on the map"));
    const light = lightOf(e.key), u = UNKNOWN[e.key];
    return h("div", { class: "p-head" },
      h("div", { class: "kind" }, KIND_WORD[e.kind] || e.kind, e.id && e.id !== e.title ? h("span", { class: "p-id" }, e.id) : null),
      h("h2", {}, NODE[e.key] ? Icons.forKey(e.key, "p-glyph") : null, e.title),
      h("div", { class: "p-meta" }, light && light.level !== "pending" ? levelPill(light.level) : null, e.pending ? pendingPill(e.pending) : null,
        u && isOpen(u) ? levelPill(ASK[e.key].light.level, dueText(u.askBy)) : null,
        e.kind === "app" && e.change ? h("span", { class: "pill" }, stateWord(e.change)) : null, e.stage ? h("span", { class: "pill", title: "How far planning has got for it" }, "Planned so far: " + stageWord(e.stage)) : null,
        e.state && e.kind !== "unknown" ? statePill(e.state) : u ? statePill(u.state) : null),
      linkChips(e.key),
      actions.childNodes.length ? actions : null);
  }
  /* A block of the panel's own prose: cut to a few lines, with Show more, so no sentence just stops. */
  const foldedText = (text) => foldProse(h("div", { class: "prose" }, text), text);
  function prose(e) {
    if (!e.prose) return null;
    const text = h("div", { class: "prose-text", html: e.prose });
    const box = foldProse(h("div", { class: "prose" }, text), text);
    if (e.cut) box.append(h("div", { class: "cut" }, "There is more on the page. Open it for the rest."));
    return box;
  }
  function factsGrid(facts, skip) {
    const rows = (facts || []).filter((f) => !skip.includes(f.label));
    if (!rows.length) return null;
    const grid = h("div", { class: "facts" });
    for (const f of rows) grid.append(h("div", { class: "fl" }, f.label), h("div", { html: f.html }));
    return grid;
  }
  function whyLit(key) {
    const light = lightOf(key);
    if (!light || light.level === "dark") return null;
    // a question reads by its name, with its ID as a small tag; the rest of the reason follows the name
    const named = (r) => { const t = titleOf(r.unknown), text = reasonText(r); return [h("a", { "data-ref": r.unknown }, t), idTag(idOf(r.unknown)), text.startsWith(t) ? text.slice(t.length) : " " + text]; };
    // Five "X: not reviewed yet" lines say one thing; they read as one line naming the five.
    const unseen = light.reasons.filter((r) => r.kind === "unexamined" && / not reviewed yet$/.test(r.text || "")), merged = unseen.length > 1;
    const rows = light.reasons.filter((r) => !(merged && unseen.includes(r)));
    const lamp = (r) => lampEl(r.kind === "held" && r.unknown ? unknownLevel(r.unknown) : r.kind === "override" ? "override" : r.kind === "unexamined" ? "unexamined" : r.kind === "pending" ? "pending" : "caution");
    return section("Why it's waiting", null, h("ul", { class: "reasons" }, rows.map((r) => h("li", { class: "r-" + r.kind }, lamp(r), h("span", {}, r.unknown ? named(r) : r.text))),
      merged ? h("li", { class: "r-unexamined" }, lampEl("unexamined"), h("span", {}, "Not reviewed yet: " + unseen.map((r) => r.text.replace(/:? ?not reviewed yet$/, "")).join(", "))) : null),
      h("div", { class: "p-note" }, light.level === "caution" || light.level === "warning" ? "Answer the questions above, or decide it in a grill session, and it turns gray." : `${LIGHT[light.level].word}: ${LIGHT[light.level].say}.`));
  }
  /* What an app is for on a call, before anything else: the flows it takes part in (a click plays the flow at the step
     that uses it) and the apps and outside services it talks to (a click opens the contract). Each chip is a button, so
     the keyboard has them too. */
  function appLinks(k) {
    const a = D.apps[k], flows = flowsFor(k).filter((r) => FLOW[r.flow]);
    const flowChips = flows.map((r) => {
      const at = firstStepTouching(FLOW[r.flow], k);
      return h("button", { class: "chip p-chip", "data-flow": r.flow, title: `Play it from step ${FLOW[r.flow].steps[at] ? FLOW[r.flow].steps[at].n : 1}, where ${titleOf(k)} first comes in`,
        onclick: () => { go(r.flow, { reset: true, reveal: true }); if (at > 0) Flows.select(r.flow, at); } }, titleOf(r.flow));
    });
    const contracts = [...a.consumes, ...a.provides].filter((id) => CONTRACT[id]);
    const talks = contracts.map((id) => {
      const c = CONTRACT[id], others = c.provider === k ? c.consumers : [c.provider];
      return h("button", { class: "chip p-chip", "data-contract": id, title: `${titleOf(id)}: ${c.provider === k ? "it provides this to" : "it uses this from"} ${others.map(titleOf).join(", ")}`,
        onclick: () => go(id, { reset: true, reveal: true }) }, others.map(titleOf).join(", "), h("span", { class: "ct" }, titleOf(id)));
    });
    const row = (title, chips, none) => section(title, null, chips.length ? h("div", { class: "p-chips" }, chips) : empty(none));
    return h("div", { class: "p-links" }, row("In these flows", flowChips, "No flow uses this app yet."), row("Talks to", talks, "This app doesn't talk to any other app or service yet."));
  }
  function flowsSection(key, tied) {
    const rows = tied || flowsFor(key);
    return section("Flows that cross this", rows.length, rows.length ? rows.map((r) => {
      const f = ent(r.flow), fl = FLOW[r.flow], at = firstStepTouching(fl, key);
      return h("div", { class: "flow-chip" },
        h("div", { class: "fc-main" }, h("a", { class: "fc-t", "data-ref": r.flow, "data-reveal": "" }, f.title),
          h("div", { class: "fc-s" }, `${f.id} · ${plural(fl.steps.length, "step")}`), h("div", { class: "fc-why" }, [...r.why].slice(0, 3).join("; "))),
        h("button", { class: "btn primary present-btn", title: "Present this flow full screen", onclick: () => Flows.present(r.flow, at) }, at > 0 ? `▶ Present from step ${fl.steps[at].n}` : "▶ Present"));
    }) : empty("No flow uses or mentions this."));
  }
  function unknownLine(id, via) {
    const u = UNKNOWN[id], e = E[id], q = e && fact(e, "Question");
    return h("li", {}, refChip(id), " ", u && isOpen(u) ? levelPill(ASK[id].light.level, dueText(u.askBy)) : statePill(u && u.state),
      q ? h("div", { class: "ml-sub" }, shorten(q.text, 160)) : null,
      via && via.length ? h("div", { class: "ml-sub" }, "blocks ", via.map((v) => titleOf(v)).join(", ")) : null);
  }
  function heldBy(key) {
    const ids = D.blockedBy[key] || [];
    return ids.length ? section("Blocked by", ids.length, h("ul", { class: "mini-list" }, ids.map((id) => unknownLine(id)))) : null;
  }
  function backlinks(key) {
    const keys = (D.backlinks[key] || []).filter((k) => ent(k));
    if (!keys.length) return null;
    return h("section", { class: "p-sec" }, h("details", {}, h("summary", {}, `Linked from ${plural(keys.length, "page")}`), h("div", { style: "margin-top:8px" }, keys.map((k) => refChip(k)))));
  }
  function contractRow(id, dir) {
    const c = CONTRACT[id];
    if (!c) return h("li", {}, refChip(id));
    const other = dir === "out" ? c.consumers.map(titleOf).join(", ") || "no consumer recorded" : titleOf(c.provider);
    return h("li", {}, refChip(id), " ", statePill(c.state), h("div", { class: "ml-sub" }, (dir === "out" ? "to " : "from ") + other));
  }
  /* What an open question holds, and what that holds in turn: the blocking chain, from Blocks and the model. */
  function chain(id) {
    const u = UNKNOWN[id];
    if (!u || !u.blocks.length) return empty(`No page says it's blocked by this yet${u && u.blocksText ? `; the question itself says it blocks "${u.blocksText}".` : "."}`);
    return h("ul", { class: "chain" }, u.blocks.map((k) => {
      const below = [];
      if (CONTRACT[k]) below.push(`${titleOf(CONTRACT[k].provider)} → ${CONTRACT[k].consumers.map(titleOf).join(", ")}`);
      const fl = flowsFor(k).map((r) => E[r.flow].title);
      if (fl.length) below.push(`used in ${fl.join(", ")}`);
      const further = u.holds.filter((x) => x !== k && !u.blocks.includes(x));
      return h("li", {}, refChip(k), below.length ? h("div", { class: "ml-sub" }, below.join("; ")) : null,
        further.length && k === u.blocks[u.blocks.length - 1] ? h("div", { class: "ml-sub" }, `Through these, it is blocking ${plural(u.holds.length, "thing")}: ${u.holds.map((x) => titleOf(x)).join(", ")}.`) : null);
    }));
  }

  function detail(e) {
    const out = [], k = e.key;
    if (typeof Inside !== "undefined") out.push(Inside.challengeSection(k));
    if (e.kind === "app") {
      const a = D.apps[k];
      // "Why it's waiting" already names the questions that light the app; this list only adds the ones it does not
      const lit = lightOf(k) && lightOf(k).level !== "dark", named = new Set(((lightOf(k) || {}).reasons || []).map((r) => r.unknown).filter(Boolean));
      const rest = a.questions.filter((q) => !named.has(q.id));
      out.push(appLinks(k), whyLit(k), prose(e));
      if (rest.length || !lit) out.push(section("Open questions blocking it", rest.length, rest.length ? h("ul", { class: "mini-list" }, rest.map((q) => unknownLine(q.id, q.via))) : empty("No open question is blocking this app.")));
      out.push(section("Epics", a.epics.length, a.epics.length ? h("div", {}, a.epics.map((x) => refChip(x))) : empty("No epic lists this app.")));
      const caps = D.appCaps[k];
      out.push(section("Business area and capabilities", null, h("div", { class: "p-note" }, D.domains[k] === "No domain" ? "Business area: not recorded yet." : `Business area: ${D.domains[k]}.`),
        caps && caps.caps.length ? h("div", { style: "margin-top:6px" }, caps.caps.map((c) => refChip(keyForId(c))), h("div", { class: "ml-sub heuristic" }, caps.via === "allocation" ? "From the requirements assigned to it." : "From the epics that list it; no requirements are assigned to it yet.")) : empty("No requirement or epic ties it to a capability yet.")));
      const fail = D.failure[k];
      if (fail) out.push(section("When something fails", fail.sections.length || null, fail.sections.length ? fail.sections.map((x) => h("div", { class: "fail" }, h("b", {}, x.heading), h("div", { class: "prose-text fail-text", html: x.html })))
        : h("div", { class: "gap" }, fail.runtime ? "No page says what this app does when something fails." : "Nothing says yet how this app runs, so nothing says what it does when something fails.")));
      if (a.reached || a.needs.length) out.push(section("Planning stage", null, h("div", { class: "p-note" }, a.reached ? `Planned so far: ${stageWord(a.reached)}.` : "Not past the first planning stage yet.", a.needs.length ? [" Still to settle:", h("ul", {}, a.needs.map((n) => h("li", {}, upFirst(n) + ".")))] : " Ready for the next planning session.")));
      if (a.runtime) out.push(section("How it runs", null, refChip(a.runtime)));
      if (typeof Plan !== "undefined") out.push(section("Build plan", null, h("div", { class: "plan-ready-row", "data-ready": Plan.readiness(k).id }, Plan.readinessPill(k), h("span", { class: "muted small" }, " " + Plan.readiness(k).counts),
        h("button", { class: "btn tiny", onclick: () => Inside.open(k, "plan") }, "Build plan"))));
    } else if (e.kind === "contract") {
      const c = CONTRACT[k];
      out.push(section("Who talks to whom", null, h("div", { class: "ends" },
        h("div", { class: "end" }, h("div", { class: "kind" }, "Provider"), refChip(c.provider)),
        h("div", { class: "arrow" }, "provides it to →"),
        h("div", { class: "end" }, h("div", { class: "kind" }, c.consumers.length > 1 ? "Consumers" : "Consumer"), c.consumers.length ? c.consumers.map((x) => refChip(x)) : empty("none recorded")))));
      if (typeof Inside !== "undefined") out.push(Inside.ownedBy(k));
      out.push(flowsSection(k));
      out.push(section("What it carries", null, c.crosses ? h("div", { class: "crosses", html: c.crosses }) : empty("Nothing says yet what data this contract carries.")));
      out.push(whyLit(k), prose(e), heldBy(k));
      const epics = D.trace.epics.filter((x) => x.delivers.includes(k) || x.consumes.includes(k));
      out.push(section("Epics", epics.length, epics.length ? epics.map((x) => refChip(x.key, h("span", { class: "rid" }, x.delivers.includes(k) ? "delivers" : "consumes"))) : empty("No epic delivers or consumes it.")));
      out.push(section("The rest of the contract", null, factsGrid(e.facts, ["Crosses the boundary", "Consumers", "Provider", "State", "Change"])));
      if (c.providerKind !== "app") out.push(h("div", { class: "note" }, "The provider is an outside service, so the contract is written up on ", refChip(c.keptOn), "'s page."));
    } else if (e.kind === "party" || e.kind === "external") {
      const provided = D.map.contracts.filter((c) => c.provider === k);
      const said = EXTERNAL[k] && EXTERNAL[k].said !== EXTERNAL[k].title ? EXTERNAL[k].said : "";
      if (said) out.push(section("As the contract words it", null, foldedText(h("div", { class: "prose-text" }, said)),
        h("div", { class: "p-note" }, "This service isn't on the outside-services list yet, so its name comes from the contract. Add it to Context and scope to give it its own box.")));
      out.push(prose(e), flowsSection(k));
      out.push(section("Contracts it provides", provided.length, provided.length ? h("ul", { class: "mini-list" }, provided.map((c) => contractRow(c.id, "out"))) : empty("It doesn't provide any contract.")));
      out.push(section("Facts", null, factsGrid(e.facts, [])));
      out.push(h("div", { class: "p-note" }, "Outside services have no status of their own. Check the contracts that connect to them."));
    } else if (e.kind === "unknown") {
      const u = UNKNOWN[k], a = ASK[k], q = fact(e, "Question");
      if (q) out.push(h("div", { class: "big-q", html: q.html }));
      out.push(section("Who to ask", null, h("div", {}, a.ask.key.startsWith("@") ? refChip("owner:" + a.ask.key) : h("b", {}, a.ask.name), " ",
        h("span", { class: a.ask.inferred ? "heuristic" : "muted" }, a.ask.rule)), h("div", { class: "ml-sub" }, "Owner: " + (u.owner ? u.owner.replace(/@[\w/-]+/g, personName) : "not recorded"))));
      out.push(section("Answer needed by", null, h("div", {}, isDate(u.askBy) ? `${day(u.askBy)}, ${dueText(u.askBy)}` : dueText(u.askByText), u.opened ? h("span", { class: "muted" }, ` · opened ${day(u.opened)}`) : null)));
      out.push(section("What it blocks", u.blocks.length, chain(k)));
      out.push(flowsSection(k));
      if (a.outcome) out.push(section("Answer", null, foldedText(h("div", { class: "prose-text" }, a.outcome))));
      out.push(prose(e));
      const notes = (e.facts || []).filter((f) => f.label === "Notes");
      out.push(section("Notes", notes.length, notes.map((n) => foldedText(h("div", { class: "prose-text", html: "<p>" + n.html + "</p>" })))));
      out.push(section("More about it", null, factsGrid(e.facts, ["Question", "Owner", "Ask by", "Opened", "Blocks", "Notes", "State", "Outcome", "Ask"])));
    } else if (e.kind === "epic") {
      const x = EPIC[k];
      out.push(prose(e), section("Apps", x.apps.length, x.apps.map((id) => APP_BY_ID[id] ? refChip(APP_BY_ID[id].key) : h("span", { class: "ref-chip" }, id))));
      out.push(section("Delivers", x.delivers.length, x.delivers.map((id) => refChip(keyForId(id)))));
      out.push(section("Consumes", x.consumes.length, x.consumes.map((id) => refChip(keyForId(id)))));
      out.push(section("Depends on", x.dependsOn.length, x.dependsOn.map((id) => refChip(keyForId(id)))));
      const ac = D.epicCriteria[k] || [];
      out.push(section("Acceptance criteria", ac.length, ac.length ? h("ol", { class: "ac-list" }, ac.map((c) => h("li", { class: c.struck ? "struck" : "", value: c.n }, c.heading ? h("b", { class: "ac-head" }, c.heading) : null, h("span", { html: c.html }), c.markers.map((m) => h("span", { class: "marker" }, m)), c.trace ? h("div", { class: "ac-trace", html: c.trace }) : null,
        typeof Inside !== "undefined" ? Inside.ownedBy(`${e.id}.AC${c.n}`, { inline: true }) : null))) : h("div", { class: "gap" }, "No acceptance criteria written yet.")));
      out.push(flowsSection(k), heldBy(k));
    } else if (e.kind === "capability") {
      const epics = D.trace.epics.filter((x) => x.delivers.includes(e.id));
      out.push(prose(e), flowsSection(k, CapFocus.flowRows(k)));  // the same flows the sidebar's capability focus counts, not a second list
      out.push(section("Delivered by", epics.length, epics.length ? epics.map((x) => refChip(x.key)) : h("div", { class: "gap" }, "No epic delivers it.")));
      const reqs = D.trace.requirements.filter((r) => r.capability === e.id);
      out.push(section("Functional requirements", reqs.length, reqs.length ? reqs.map((r) => refChip(r.id)) : empty("None written yet.")));
    } else if (e.kind === "requirement") {
      const rows = D.trace.allocation.filter((r) => r.requirement === k);
      if (typeof Inside !== "undefined") out.push(Inside.ownedBy(k));
      out.push(prose(e), section("Assigned to", rows.length, rows.length ? h("ul", { class: "mini-list" }, rows.map((r) => h("li", {}, refChip(r.app), " ", statePill(r.state), h("div", { class: "ml-sub" }, r.share), r.through.length ? h("div", {}, r.through.map((c) => refChip(c))) : null))) : h("div", { class: "gap" }, "No app has this requirement assigned to it yet.")));
      const ac = D.reqCriteria[k] || [];
      out.push(section("Acceptance criteria", ac.length, ac.length ? h("ol", { class: "ac-list" }, ac.map((c) => h("li", { html: c }))) : empty("No criteria listed under it.")));
      const rel = typeof Releases !== "undefined" ? Releases.deliveringRequirement(k) : [];
      out.push(section("Releases that deliver it", rel.length, rel.length ? h("ul", { class: "mini-list" }, rel.map((r) => h("li", {}, h("a", { onclick: () => Nav.openRelease(r.index) }, r.name), " ", h("span", { class: "pill" }, r.criteria)))) : empty(D.releases.count ? "No release lists it yet." : "The plan has no releases yet.")));
      out.push(flowsSection(k), heldBy(k), section("Facts", null, factsGrid(e.facts.filter((f) => f.label), [])));
    } else if (e.kind === "flow") {
      const f = FLOW[k];
      out.push(whyLit(k), prose(e));
      out.push(section("Steps", f.steps.length, f.steps.length ? h("ol", { class: "steps-list" }, f.steps.map((st, i) => h("li", {},
        h("button", { class: "step-link", onclick: () => { if (App.view !== "flows") showView("flows"); Flows.select(k, i); } }, h("span", { html: st.html }))))) : empty("No steps written for this flow yet.")));
      const qs = [...new Set([...f.unknowns, ...f.steps.flatMap((st) => st.unknowns.map((p) => p.id))])];
      out.push(section("Questions on this flow", qs.length, qs.length ? h("ul", { class: "mini-list" }, qs.map((id) => unknownLine(id))) : null));
      out.push(section("Apps and outside services in it", flowStations(f).length, flowStations(f).map((x) => refChip(x))));
    } else if (e.kind === "owner") {
      const o = D.owners[e.title], owned = o.owns.map(ent).filter(Boolean);
      const openQ = owned.filter((x) => x.kind === "unknown" && isOpen(UNKNOWN[x.key])).sort((a, b) => cmp(UNKNOWN[a.key].askBy || "9999", UNKNOWN[b.key].askBy || "9999"));
      if (o.names.length) out.push(h("div", { class: "note" }, "Also called: " + o.names.slice(0, 4).join("; ")));
      out.push(h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => { showView("asks"); Asks.meet(e.title); } }, "Meet with them")));
      out.push(section("Open questions they own", openQ.length, openQ.length ? h("ul", { class: "mini-list" }, openQ.map((x) => unknownLine(x.key))) : empty("None open.")));
      const rest = owned.filter((x) => !(x.kind === "unknown" && isOpen(UNKNOWN[x.key])) && x.kind !== "session");
      out.push(section("Everything else they own", rest.length, rest.map((x) => refChip(x.key))));
    } else {
      if (e.kind === "runtime" && RUNTIME_TO_APP[k]) out.push(section("How this app runs", null, refChip(RUNTIME_TO_APP[k])));
      if (e.kind === "slice" && typeof Slices !== "undefined") out.push(...Slices.panelPart(k));
      if (e.kind === "decision") out.push(h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => { showView("decisions"); Decisions.showFor(k); } }, "Open it in the decision log")));
      out.push(prose(e), heldBy(k));
      if (["concern", "decision", "section", "risk", "stored-value"].includes(e.kind)) out.push(flowsSection(k));
      out.push(section("Facts", null, factsGrid(e.facts, [])));
    }
    if (typeof Library !== "undefined") out.push(Library.backlinks(k));  // the Library items that name this thing
    if (typeof Grills !== "undefined") out.push(Grills.readyLine(k));  // a small line when a grill could decide it now
    out.push(backlinks(k));
    return out.filter(Boolean);
  }
  function bundle(key) {
    const parts = key.slice(7).split("|"), ids = parts[0].split(","), c0 = CONTRACT[ids[0]];
    // two parts: provider's contracts to one consumer; three: everything between two boxes on a grouped map
    const title = parts.length === 3 ? `Between ${parts[1]} and ${parts[2]}` : `${titleOf(c0.provider)} → ${titleOf(parts[1] || "")}`;
    return [h("div", { class: "p-head" }, h("div", { class: "kind" }, "Contracts"), h("h2", {}, title),
      h("p", { class: "p-lede" }, `${ids.length} contracts connect these apps, so the map draws them as one line.`)),
    h("div", { class: "p-body" }, h("ul", { class: "mini-list" }, ids.map((id) => contractRow(id, "out"))))];
  }
  /* What holds a page or app up, for a page's "What's waiting" tab: why it is lit, then the questions that block it. */
  const waitingFor = (key) => [whyLit(key), heldBy(key)].filter(Boolean);
  return { render, section, keyNodes, waitingFor, empty, homeNodes: home };
})();
