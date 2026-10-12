/* The one right-hand panel, on every view. Its home is the lights, most urgent first: what needs the lead, from
   attention.lights. Anything picked anywhere opens here with a trail of breadcrumbs back, and every app, contract,
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

  /* The panel's two homes: the lights, and on a section, that section's own page beside its visual. */
  function homes() {
    const page = typeof Nav !== "undefined" ? Nav.pageBeside() : "";
    // inside an app with its team's design loaded, the design is a third home
    const design = App.view === "inside" && typeof Inside !== "undefined" ? Inside.designKey() : "";
    if (!page && !design) return null;
    const pick = (root) => { App.root = root; App.trail = []; render(); };
    return h("div", { class: "p-homes", role: "tablist" },
      design ? h("button", { role: "tab", "aria-selected": String(App.root === design), onclick: () => pick(design) }, "The design") : null,
      page ? h("button", { role: "tab", "aria-selected": String(App.root.startsWith("read:")), onclick: () => pick("read:" + page) }, "The page") : null,
      h("button", { role: "tab", "aria-selected": String(App.root === "lights"), onclick: () => pick("lights") }, "What needs you"));
  }
  function crumbs() {
    const box = h("nav", { class: "crumbs", "aria-label": "Trail" });
    const rootIsPage = App.root.startsWith("read:") || App.root.startsWith("inside:");
    box.append(h("a", { onclick: () => { App.trail = []; render(); }, class: App.trail.length ? "" : "cur", title: rootIsPage ? "Back to the page" : "What needs you, most urgent first" },
      rootIsPage ? "◧ " + shorten(titleOf(App.root), 22) : "◉ Lights"));
    App.trail.forEach((k, i) => {
      box.append(h("span", { class: "sep" }, "›"));
      box.append(i === App.trail.length - 1 ? h("span", { class: "cur" }, idOf(k) || shorten(titleOf(k), 26)) : h("a", { "data-ref": k, title: titleOf(k) }, idOf(k) || shorten(titleOf(k), 20)));
    });
    return box;
  }

  function render() {
    const root = body();
    root.innerHTML = "";
    const key = App.trail[App.trail.length - 1] || (App.root !== "lights" ? App.root : null);
    const tabs = homes();
    if (tabs) root.append(tabs);
    root.append(crumbs());
    if (App.view === "ask" && !key) root.append(h("p", { class: "p-note ask-hint" }, "A citation in the conversation opens here, so you can read the source beside it."));
    if (!key) { root.append(...home()); root.scrollTop = 0; return; }
    if (key.startsWith("read:")) { root.append(...reading(key)); return; }
    if (key.startsWith("bundle:")) { root.append(...bundle(key)); return; }
    if (key.startsWith("inside:") && typeof Inside !== "undefined") { root.append(...Inside.panel(key)); root.scrollTop = 0; return; }
    const e = ent(key);
    if (!e) { root.append(h("div", { class: "p-empty" }, `Nothing in the vault is called ${key}.`)); return; }
    root.append(head(e), h("div", { class: "p-body" }, ...detail(e)));
    root.scrollTop = 0;
  }

  /* ------------------------------------------------------------ home: the lights */
  function home() {
    const lit = litSubjects(), dark = darkSubjects();
    const out = [h("div", { class: "p-head" }, h("div", { class: "kind" }, `Lit from the record as of ${day(D.today)}`), h("h2", {}, "What needs you"),
      h("p", { class: "p-lede" }, lit.length ? `${plural(lit.length, "thing")} lit, most urgent first${D.above.length ? `, and ${plural(D.above.length, "question")} held above the map` : ""}. Everything else is dark: settled, with nothing holding it.`
        : "Nothing is lit. Every app, contract and flow has a recorded state, is settled, and no open question holds it."))];
    out.push(section("Lights, most urgent first", lit.length, lit.length ? h("ul", { class: "lights" }, lit.map(({ key, light }) => h("li", {},
      h("button", { class: "light-row" + (key === App.focus ? " on" : ""), "data-ref": key },
        lampEl(light.level), h("span", {}, h("span", { class: "what", style: `color:${LIGHT[light.level].colour}` }, `${idOf(key) ? idOf(key) + " " : ""}${titleOf(key)}`),
          h("span", { class: "why" }, `${LIGHT[light.level].word}: ${reasonSummary(light, 1)}`))))))
      : empty("Nothing is lit.")));
    if (D.above.length) out.push(section("Held above the map", D.above.length, h("p", { class: "p-note" }, "Open questions that hold something no map draws: the strategy, a goal, another question."),
      h("ul", { class: "lights" }, D.above.map((a) => {
        const u = ASK[a.unknown], lvl = u ? u.light.level : "caution";
        return h("li", {}, h("button", { class: "light-row", "data-ref": a.unknown },
          lampEl(lvl), h("span", {}, h("span", { class: "what" }, `${a.unknown} holds ${a.title}`), h("span", { class: "why" }, u ? `${u.question ? shorten(u.question, 110) + " " : ""}Ask ${u.ask.name}${u.ask.inferred ? " (a guess)" : ""} by ${day(a.ask_by)}` : ""))));
      }))));
    const challenged = typeof Inside !== "undefined" ? Inside.homeSection() : null;
    if (challenged) out.push(challenged);  // Element.append writes a null as the text "null"
    out.push(section("Dark, settled", dark.length, h("p", { class: "p-note" }, dark.map((k) => idOf(k) || titleOf(k)).join(", ") || "None.")));
    out.push(h("div", { class: "p-key" }, LEVELS.map((l) => h("span", {}, lampEl(l), LIGHT[l].word))));
    return out;
  }

  /* ------------------------------------------------------------ a page, to read */
  function reading(key) {
    const [pk, anchor] = key.slice(5).split("#"), e = E[pk];
    const out = [h("div", { class: "p-head" }, h("div", { class: "kind" }, ["page", "section"].includes(e.kind) ? "Page" : (KIND_WORD[e.kind] || "Page") + " page", h("span", { class: "p-id" }, e.path)),
      h("h2", {}, e.title), linkChips(pk),
      h("div", { class: "p-actions" }, typeof Nav !== "undefined" ? h("button", { class: "btn", onclick: () => Nav.readWide(pk, anchor) }, "Read full width") : null,
        ent(pk) && e.kind !== "section" && e.kind !== "page" ? h("button", { class: "btn", onclick: () => go(pk, {}) }, "What it is and what holds it") : null,
        D.vault ? h("a", { class: "btn quiet", href: encodeURI(D.vault + "/" + e.path), target: "_blank", title: "Open the Markdown file itself" }, "Open the file") : null))];
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
        h("button", { class: "btn", onclick: () => { showView("flows"); Flows.select(e.key, -1); } }, "Play it"),
        h("button", { class: "btn", onclick: () => Rehearse.open(e.key) }, "Rehearse this flow"));
    }
    if (onMap(e.key) && App.view !== "map") actions.append(h("button", { class: "btn", onclick: () => { showView("map"); viewDef("map").highlight(e.key); } }, "Show on the map"));
    if (e.kind === "unknown" && App.view !== "asks") actions.append(h("button", { class: "btn", onclick: () => { showView("asks"); viewDef("asks").highlight(e.key); } }, "Show its strip"));
    const readKey = Reader.keyFor(e.key);
    if (readKey) actions.append(h("button", { class: "btn open-page", title: "Read it here, in the vault's own words", onclick: () => go(readKey, {}) }, "Open the page"));
    if (e.kind === "app" && typeof MapView !== "undefined") actions.append(h("button", { class: "btn", onclick: () => Nav.focusApp(e.key) }, "Focus on the map"));
    if (e.kind === "app" && typeof Inside !== "undefined") actions.append(h("button", { class: "btn inside-btn", title: "Its context, its main containers and the team's components", onclick: () => Inside.open(e.key, "containers") }, "Inside this app"));
    if ((e.kind === "app" || e.kind === "decision") && typeof Motion !== "undefined") actions.append(h("button", { class: "btn", title: "What depends on it, ring by ring", onclick: () => Nav.ripple(e.key) }, "Ripple: what depends on it"));
    if ((e.kind === "flow" || e.kind === "contract") && typeof Motion !== "undefined") actions.append(h("button", { class: "btn", title: "Light its path on the map, hop by hop", onclick: () => Nav.trace(e.key) }, "Trace on the map"));
    const light = lightOf(e.key), u = UNKNOWN[e.key];
    return h("div", { class: "p-head" },
      h("div", { class: "kind" }, KIND_WORD[e.kind] || e.kind, e.id && e.id !== e.title ? h("span", { class: "p-id" }, e.id) : null),
      h("h2", {}, NODE[e.key] ? Icons.forKey(e.key, "p-glyph") : null, e.title),
      h("div", { class: "p-meta" }, light && light.level !== "pending" ? levelPill(light.level) : null, e.pending ? pendingPill(e.pending) : null,
        u && isOpen(u) ? levelPill(ASK[e.key].light.level, dueText(u.askBy)) : null,
        e.kind === "app" && e.change ? h("span", { class: "pill" }, e.change) : null, e.stage ? h("span", { class: "pill" }, "stage " + e.stage) : null,
        e.state && e.kind !== "unknown" ? statePill(e.state) : u ? statePill(u.state) : null),
      linkChips(e.key),
      actions.childNodes.length ? actions : null);
  }
  function prose(e) {
    if (!e.prose) return null;
    const text = h("div", { class: "prose-text", html: e.prose });
    const box = h("div", { class: "prose" }, text);
    const more = h("button", { class: "linkish", onclick: () => { box.classList.toggle("open"); more.textContent = box.classList.contains("open") ? "Show less" : "Show more"; } }, "Show more");
    box.append(more);
    requestAnimationFrame(() => { if (text.scrollHeight <= text.clientHeight + 4) { more.remove(); box.classList.add("open"); } });
    if (e.cut) box.append(h("div", { class: "cut" }, "The page goes on. Open it for the rest."));
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
    return section("Why it is lit", null, h("ul", { class: "reasons" }, light.reasons.map((r) => h("li", { class: "r-" + r.kind },
      lampEl(r.kind === "held" && r.unknown ? unknownLevel(r.unknown) : r.kind === "override" ? "override" : r.kind === "unexamined" ? "unexamined" : r.kind === "pending" ? "pending" : "caution"),
      h("span", {}, r.unknown ? h("a", { "data-ref": r.unknown }, r.unknown) : null, " ", r.unknown ? reasonText(r).replace(r.unknown, "").trim() : r.text)))),
      h("div", { class: "p-note" }, `${LIGHT[light.level].word}: ${LIGHT[light.level].say}. The rule is attention.py's, the same on every view.`));
  }
  function flowsSection(key) {
    const rows = flowsFor(key);
    return section("Flows that cross this", rows.length, rows.length ? rows.map((r) => {
      const f = ent(r.flow), fl = FLOW[r.flow], at = firstStepTouching(fl, key);
      return h("div", { class: "flow-chip" },
        h("div", { class: "fc-main" }, h("a", { class: "fc-t", "data-ref": r.flow, "data-reveal": "" }, f.title),
          h("div", { class: "fc-s" }, `${f.id} · ${plural(fl.steps.length, "step")}`), h("div", { class: "fc-why" }, [...r.why].slice(0, 3).join("; "))),
        h("button", { class: "btn primary present-btn", title: "Present this flow full screen", onclick: () => Flows.present(r.flow, at) }, at > 0 ? `▶ Present from step ${fl.steps[at].n}` : "▶ Present"));
    }) : empty("No flow page links this, and no flow step uses or names it."));
  }
  function unknownLine(id, via) {
    const u = UNKNOWN[id], e = E[id], q = e && fact(e, "Question");
    return h("li", {}, refChip(id), " ", u && isOpen(u) ? levelPill(ASK[id].light.level, dueText(u.askBy)) : statePill(u && u.state),
      q ? h("div", { class: "ml-sub" }, shorten(q.text, 160)) : null,
      via && via.length ? h("div", { class: "ml-sub" }, "holds ", via.map((v) => idOf(v) || titleOf(v)).join(", ")) : null);
  }
  function heldBy(key) {
    const ids = D.blockedBy[key] || [];
    return ids.length ? section("Held up by", ids.length, h("ul", { class: "mini-list" }, ids.map((id) => unknownLine(id)))) : null;
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
    if (!u || !u.blocks.length) return empty(`Its Blocks line links nothing${u && u.blocksText ? `: "${u.blocksText}"` : "."}`);
    return h("ul", { class: "chain" }, u.blocks.map((k) => {
      const below = [];
      if (CONTRACT[k]) below.push(`${titleOf(CONTRACT[k].provider)} → ${CONTRACT[k].consumers.map(titleOf).join(", ")}`);
      const fl = flowsFor(k).map((r) => E[r.flow].title);
      if (fl.length) below.push(`used in ${fl.join(", ")}`);
      const further = u.holds.filter((x) => x !== k && !u.blocks.includes(x));
      return h("li", {}, refChip(k), below.length ? h("div", { class: "ml-sub" }, below.join("; ")) : null,
        further.length && k === u.blocks[u.blocks.length - 1] ? h("div", { class: "ml-sub" }, `Through these the planner counts it holding ${plural(u.holds.length, "unit")}: ${u.holds.map((x) => idOf(x) || titleOf(x)).join(", ")}.`) : null);
    }));
  }

  function detail(e) {
    const out = [], k = e.key;
    if (typeof Inside !== "undefined") out.push(Inside.challengeSection(k));
    if (e.kind === "app") {
      const a = D.apps[k];
      out.push(whyLit(k), prose(e), flowsSection(k));
      out.push(section("Provides", a.provides.length, a.provides.length ? h("ul", { class: "mini-list" }, a.provides.map((id) => contractRow(id, "out"))) : empty("No contract lives on this app's page.")));
      out.push(section("Consumes", a.consumes.length, a.consumes.length ? h("ul", { class: "mini-list" }, a.consumes.map((id) => contractRow(id, "in"))) : empty("No contract lists this app as a consumer.")));
      out.push(section("Open questions holding it up", a.questions.length, a.questions.length ? h("ul", { class: "mini-list" }, a.questions.map((q) => unknownLine(q.id, q.via))) : empty("No open unknown's Blocks line points at this app or its items.")));
      out.push(section("Epics", a.epics.length, a.epics.length ? h("div", {}, a.epics.map((x) => refChip(x))) : empty("No epic lists this app.")));
      const caps = D.appCaps[k];
      out.push(section("Domain and capabilities", null, h("div", { class: "p-note" }, `Domain: ${D.domains[k]}${D.domains[k] === "No domain" ? " (its page has no domain: line)" : ""}.`),
        caps && caps.caps.length ? h("div", { style: "margin-top:6px" }, caps.caps.map((c) => refChip(keyForId(c))), h("div", { class: "ml-sub heuristic" }, caps.via === "allocation" ? "From the requirements its allocation rows carry." : "From the epics that list it; it has no allocation rows.")) : empty("No allocation row or epic ties it to a capability.")));
      const fail = D.failure[k];
      if (fail) out.push(section("When something fails", fail.sections.length || null, fail.sections.length ? fail.sections.map((x) => h("div", { class: "fail" }, h("b", {}, x.heading), h("div", { class: "prose-text fail-text", html: x.html })))
        : h("div", { class: "gap" }, fail.runtime ? "Its runtime page has no section on failure (ladder.FAILURE finds none)." : "It has no runtime page, so nothing says how it behaves on failure.")));
      if (a.reached || a.needs.length) out.push(section("Stage ladder", null, h("div", { class: "p-note" }, `The pages reach ${a.reached || "no stage"}.`, a.needs.length ? h("ul", {}, a.needs.map((n) => h("li", {}, n))) : " Nothing more is needed for the next stage.")));
      if (a.runtime) out.push(section("Runtime", null, refChip(a.runtime)));
    } else if (e.kind === "contract") {
      const c = CONTRACT[k];
      out.push(section("Who talks to whom", null, h("div", { class: "ends" },
        h("div", { class: "end" }, h("div", { class: "kind" }, "Provider"), refChip(c.provider)),
        h("div", { class: "arrow" }, "provides it to →"),
        h("div", { class: "end" }, h("div", { class: "kind" }, c.consumers.length > 1 ? "Consumers" : "Consumer"), c.consumers.length ? c.consumers.map((x) => refChip(x)) : empty("none recorded")))));
      if (typeof Inside !== "undefined") out.push(Inside.ownedBy(k));
      out.push(flowsSection(k));
      out.push(section("What crosses", null, c.crosses ? h("div", { class: "crosses", html: c.crosses }) : empty("The contract has no Crosses the boundary line yet.")));
      out.push(whyLit(k), prose(e), heldBy(k));
      const epics = D.trace.epics.filter((x) => x.delivers.includes(k) || x.consumes.includes(k));
      out.push(section("Epics", epics.length, epics.length ? epics.map((x) => refChip(x.key, h("span", { class: "rid" }, x.delivers.includes(k) ? "delivers" : "consumes"))) : empty("No epic delivers or consumes it.")));
      out.push(section("The rest of the contract", null, factsGrid(e.facts, ["Crosses the boundary", "Consumers", "Provider", "State", "Change"])));
      if (c.providerKind !== "app") out.push(h("div", { class: "note" }, "The provider is outside the vault, so the contract is kept on ", refChip(c.keptOn), "'s page."));
    } else if (e.kind === "party" || e.kind === "external") {
      const provided = D.map.contracts.filter((c) => c.provider === k);
      out.push(prose(e), flowsSection(k));
      out.push(section("Contracts it provides", provided.length, provided.length ? h("ul", { class: "mini-list" }, provided.map((c) => contractRow(c.id, "out"))) : empty("No contract names it as provider.")));
      out.push(section("Facts", null, factsGrid(e.facts, [])));
      out.push(h("div", { class: "p-note" }, "Outside parties carry no light of their own: attention.py lights apps, contracts and flows. Their contracts are lit."));
    } else if (e.kind === "unknown") {
      const u = UNKNOWN[k], a = ASK[k], q = fact(e, "Question");
      if (q) out.push(h("div", { class: "big-q", html: q.html }));
      out.push(section("Who holds the answer", null, h("div", {}, a.ask.key.startsWith("@") ? refChip("owner:" + a.ask.key) : h("b", {}, a.ask.name), " ",
        h("span", { class: a.ask.inferred ? "heuristic" : "muted" }, a.ask.rule)), h("div", { class: "ml-sub" }, "Owner line: " + (u.owner || "none"))));
      out.push(section("Ask by", null, h("div", {}, isDate(u.askBy) ? `${day(u.askBy)}, ${dueText(u.askBy)}` : dueText(u.askByText), u.opened ? h("span", { class: "muted" }, ` · opened ${day(u.opened)}`) : null)));
      out.push(section("What it holds up", u.blocks.length, chain(k)));
      out.push(flowsSection(k));
      if (a.outcome) out.push(section("Answer", null, h("div", { class: "prose-text" }, a.outcome)));
      out.push(prose(e));
      const notes = (e.facts || []).filter((f) => f.label === "Notes");
      out.push(section("Notes", notes.length, notes.map((n) => h("div", { class: "prose-text", html: "<p>" + n.html + "</p>" }))));
      out.push(section("Other facts", null, factsGrid(e.facts, ["Question", "Owner", "Ask by", "Opened", "Blocks", "Notes", "State", "Outcome", "Ask"])));
    } else if (e.kind === "epic") {
      const x = EPIC[k];
      out.push(prose(e), section("Apps", x.apps.length, x.apps.map((id) => APP_BY_ID[id] ? refChip(APP_BY_ID[id].key) : h("span", { class: "ref-chip" }, id))));
      out.push(section("Delivers", x.delivers.length, x.delivers.map((id) => refChip(keyForId(id)))));
      out.push(section("Consumes", x.consumes.length, x.consumes.map((id) => refChip(keyForId(id)))));
      out.push(section("Depends on", x.dependsOn.length, x.dependsOn.map((id) => refChip(keyForId(id)))));
      const ac = D.epicCriteria[k] || [];
      out.push(section("Acceptance criteria", ac.length, ac.length ? h("ol", { class: "ac-list" }, ac.map((c) => h("li", { class: c.struck ? "struck" : "", value: c.n }, h("span", { html: c.html }), c.markers.map((m) => h("span", { class: "marker" }, m)),
        typeof Inside !== "undefined" ? Inside.ownedBy(`${e.id}.AC${c.n}`, { inline: true }) : null))) : h("div", { class: "gap" }, "No numbered acceptance criteria under an \"acceptance criteria\" heading.")));
      out.push(flowsSection(k), heldBy(k));
    } else if (e.kind === "capability") {
      const epics = D.trace.epics.filter((x) => x.delivers.includes(e.id));
      out.push(prose(e), flowsSection(k));
      out.push(section("Delivered by", epics.length, epics.length ? epics.map((x) => refChip(x.key)) : h("div", { class: "gap" }, "No epic delivers it.")));
      const reqs = D.trace.requirements.filter((r) => r.capability === e.id);
      out.push(section("Functional requirements", reqs.length, reqs.length ? reqs.map((r) => refChip(r.id)) : empty("None written yet.")));
    } else if (e.kind === "requirement") {
      const rows = D.trace.allocation.filter((r) => r.requirement === k);
      if (typeof Inside !== "undefined") out.push(Inside.ownedBy(k));
      out.push(prose(e), section("Allocated to", rows.length, rows.length ? h("ul", { class: "mini-list" }, rows.map((r) => h("li", {}, refChip(r.app), " ", statePill(r.state), h("div", { class: "ml-sub" }, r.share), r.through.length ? h("div", {}, r.through.map((c) => refChip(c))) : null))) : h("div", { class: "gap" }, "No app's Requirements allocated table carries it.")));
      const ac = D.reqCriteria[k] || [];
      out.push(section("Acceptance criteria", ac.length, ac.length ? h("ol", { class: "ac-list" }, ac.map((c) => h("li", { html: c }))) : empty("No criteria listed under it.")));
      const rel = typeof Releases !== "undefined" ? Releases.deliveringRequirement(k) : [];
      out.push(section("Releases that deliver it", rel.length, rel.length ? h("ul", { class: "mini-list" }, rel.map((r) => h("li", {}, h("a", { onclick: () => Nav.openRelease(r.index) }, r.name), " ", h("span", { class: "pill" }, r.criteria)))) : empty(D.releases.count ? "No release lists it yet." : "This vault plans no releases.")));
      out.push(flowsSection(k), heldBy(k), section("Facts", null, factsGrid(e.facts.filter((f) => f.label), [])));
    } else if (e.kind === "flow") {
      const f = FLOW[k];
      out.push(whyLit(k), prose(e));
      out.push(section("Steps", f.steps.length, f.steps.length ? h("ol", { class: "steps-list" }, f.steps.map((st, i) => h("li", {},
        h("button", { class: "step-link", onclick: () => { if (App.view !== "flows") showView("flows"); Flows.select(k, i); } }, h("span", { html: st.html }))))) : empty("This flow page has no numbered Steps section.")));
      const qs = [...new Set([...f.unknowns, ...f.steps.flatMap((st) => st.unknowns.map((p) => p.id))])];
      out.push(section("Questions on this flow", qs.length, qs.length ? h("ul", { class: "mini-list" }, qs.map((id) => unknownLine(id))) : null));
      out.push(section("Apps and parties in it", flowStations(f).length, flowStations(f).map((x) => refChip(x))));
    } else if (e.kind === "owner") {
      const o = D.owners[e.title], owned = o.owns.map(ent).filter(Boolean);
      const openQ = owned.filter((x) => x.kind === "unknown" && isOpen(UNKNOWN[x.key])).sort((a, b) => cmp(UNKNOWN[a.key].askBy || "9999", UNKNOWN[b.key].askBy || "9999"));
      if (o.names.length) out.push(h("div", { class: "note" }, "Described in the vault as: " + o.names.slice(0, 4).join("; ")));
      out.push(h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => { showView("asks"); Asks.meet(e.title); } }, "Meet with them")));
      out.push(section("Open questions they own", openQ.length, openQ.length ? h("ul", { class: "mini-list" }, openQ.map((x) => unknownLine(x.key))) : empty("None open.")));
      const rest = owned.filter((x) => !(x.kind === "unknown" && isOpen(UNKNOWN[x.key])) && x.kind !== "session");
      out.push(section("Everything else they own", rest.length, rest.map((x) => refChip(x.key))));
    } else {
      if (e.kind === "runtime" && RUNTIME_TO_APP[k]) out.push(section("Runtime of", null, refChip(RUNTIME_TO_APP[k])));
      if (e.kind === "decision") out.push(h("div", { class: "p-actions" }, h("button", { class: "btn", onclick: () => { showView("garden"); Garden.showFor(k); } }, "See it grow in the garden")));
      out.push(prose(e), heldBy(k));
      if (["concern", "decision", "section", "risk", "stored-value"].includes(e.kind)) out.push(flowsSection(k));
      out.push(section("Facts", null, factsGrid(e.facts, [])));
    }
    out.push(backlinks(k));
    return out.filter(Boolean);
  }
  function bundle(key) {
    const parts = key.slice(7).split("|"), ids = parts[0].split(","), c0 = CONTRACT[ids[0]];
    // two parts: provider's contracts to one consumer; three: everything between two boxes on a grouped map
    const title = parts.length === 3 ? `Between ${parts[1]} and ${parts[2]}` : `${titleOf(c0.provider)} → ${titleOf(parts[1] || "")}`;
    return [h("div", { class: "p-head" }, h("div", { class: "kind" }, "Contracts"), h("h2", {}, title),
      h("p", { class: "p-lede" }, `${ids.length} contracts share this pair of ends, so the map draws them as one duct.`)),
    h("div", { class: "p-body" }, h("ul", { class: "mini-list" }, ids.map((id) => contractRow(id, "out"))))];
  }
  return { render, section };
})();
