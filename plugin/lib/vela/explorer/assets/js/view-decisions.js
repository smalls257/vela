/* The decision log: every recorded decision as a row a reader can sort and filter, and as a decision record
   (context, options, decision, consequences, history) when picked. It replaces a botanical drawing of the same data,
   which was memorable and unreadable on a call: a lead could not scan 12 plants for "which are still only proposed"
   or "what is each one waiting on". Here the answer to each of those is one column or one filter.
   Every part comes from a typed field (asks_data.decisions): an Options considered line, a decision record's
   Alternatives table and Assumptions section, and Blocks lines; a decision record's own sections are read from its
   page. Prose that merely mentions a decision is not listed. Routes: #decisions, #s=decisions, and the old #garden. */
const Decisions = (() => {
  const trees = [...D.garden.trees, ...D.garden.bare];
  const ISO = /\d{4}-\d{2}-\d{2}/;
  const STATES = [["decided", "Decided"], ["proposed", "Proposed"], ["pending", "Pending approval"], ["overridden", "Overridden"]];
  const STATE_ORDER = { pending: 0, proposed: 1, overridden: 2, decided: 3 };  // what a lead should look at first
  const STATE_SAY = { decided: "Decided, with the usual checks done", proposed: "Written down, not decided", pending: "Someone reading the plan decided this, and the owner hasn't reviewed it yet", overridden: "Decided before the usual checks were done, and nobody has confirmed it since" };
  const SORTS = [["state", "State"], ["name", "Name"], ["date", "Decided"], ["waits", "Open questions"]];
  const st = { sort: "state", flip: false, q: "", state: "", waiting: false, bare: false, mode: "log", open: "" };
  const sessionTitle = (id) => (D.sessions[id] && D.sessions[id].title) || id;
  const sessionDate = (id) => (D.sessions[id] && D.sessions[id].date) || (ISO.exec(id) || [""])[0];
  /* A handle as a person reads it: the name the vault gives the role, else the handle without its @ and team prefix. */
  const person = (text) => String(text || "").replace(/@[\w/-]+/g, (m) => {
    const said = D.owners[m] && D.owners[m].names[0], named = said && said.split(/\s+/).length <= 3 && !/^asking\b/i.test(said) ? said : "", w = named || m.replace(/^@/, "").replace(/^[^/]*\//, "").replace(/-/g, " ");
    return w.charAt(0).toUpperCase() + w.slice(1);
  });
  const longDate = (iso) => (isDate(iso) ? `${day(iso)} ${iso.slice(0, 4)}` : "");
  const sentence = (text) => { const t = String(text || "").trim(), m = t.match(/^.*?[.!?](?=\s|$)/); return m ? m[0] : t; };

  /* The page whose words say the decision: not an index page that only lists it. */
  const proseCarrier = (t) => t.carriedBy.find((w) => w.type !== "index" && w.text) || t.carriedBy[0];
  /* The pick, said plainly: the first sentence of the decision, with the option's own name stripped from its front. */
  function chosenOf(t) {
    const w = proseCarrier(t), prose = t.adr ? t.adr.decision : w.type === "concern" ? "" : w.text;
    const label = t.picked.label, rest = String(prose || "").replace(new RegExp("^" + label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "[,:.]?\\s*", "i"), "");
    const said = sentence(rest);
    return { label, said: said && said.toLowerCase() !== label.toLowerCase() ? said : "", condition: (t.picked.condition || "").replace(/^on condition that\s*/i, "") };
  }
  function deciders(t) {
    const by = new Set(), conf = new Set(), sessions = new Set(); let overrides = 0;
    for (const w of t.carriedBy) {
      w.decidedBy.forEach((x) => by.add(person(x))); w.confirmedBy.forEach((x) => conf.add(person(x)));
      w.decision.forEach((x) => { const m = x.match(/^\d{4}-\d{2}-\d{2}-[a-z0-9-]+/); if (m) sessions.add(m[0]); });
      overrides += w.overrides || 0;
    }
    return { by: [...by], conf: [...conf], sessions: [...sessions].sort(), overrides, owner: person(t.carriedBy.map((w) => w.owner).find(Boolean) || "") };
  }
  /* A reader's decision the owner has not reviewed: on the decision record, or on any page or item that carries it. */
  function pendingOf(t) {
    const keys = [t.adr && t.adr.key, ...t.carriedBy.flatMap((w) => [w.key, w.page])].filter(Boolean);
    const hit = keys.find((k) => E[k] && E[k].pending);
    return hit ? E[hit].pending : null;
  }
  function stateOf(t) {
    const d = deciders(t);
    if (pendingOf(t)) return "pending";
    if (d.overrides > 0 && !d.conf.length) return "overridden";
    return t.carriedBy.some((w) => w.state === "decided") ? "decided" : "proposed";
  }
  function dateOf(t) {
    const fromStatus = ISO.exec(t.carriedBy[0].status || "");  // a decision record: "Accepted, 2026-08-12, in a Grill session"
    if (fromStatus) return fromStatus[0];
    const dates = deciders(t).sessions.map(sessionDate).filter(Boolean).sort();
    return dates[dates.length - 1] || "";
  }
  function titleOfTree(t) { const w = t.carriedBy[0]; return w.type === "concern" && w.under ? `${w.pageTitle}, ${w.under}` : t.picked.label; }
  function recordedOn(t) {
    const seen = new Set(), out = [];
    for (const w of t.carriedBy) { const label = w.item ? titleOf(w.item) : w.under ? `${w.pageTitle}, ${w.under}` : w.pageTitle; if (!seen.has(label)) { seen.add(label); out.push({ label, key: w.key }); } }
    return out;
  }
  /* What a decision record changes: the pages and items that link to it, the ones that matter to a plan. */
  const AFFECTED = new Set(["epic", "capability", "requirement", "app", "flow", "contract", "concern", "runtime"]);
  function affects(t) {
    const own = recordedOn(t).filter((x) => !t.adr || x.key !== t.adr.key);
    const linked = t.adr ? (D.backlinks[t.adr.key] || []).filter((k) => ent(k) && AFFECTED.has(ent(k).kind)).map((k) => ({ label: titleOf(k), key: k })) : [];
    return [...own, ...linked].filter((x, i, all) => all.findIndex((y) => y.key === x.key) === i);
  }

  const entries = trees.map((t) => {
    const d = deciders(t), c = chosenOf(t), on = affects(t);
    return { t, id: t.adr ? t.adr.id : t.id, key: t.adr ? t.adr.key : t.carriedBy[0].key, name: titleOfTree(t), chosen: c, state: stateOf(t), pending: pendingOf(t),
      rejected: t.rejected, decider: d, by: d.by.join("; "), owner: d.owner, date: dateOf(t), affects: on, waits: t.buds, answered: t.leaves,
      bare: !!t.bare, recordedIn: recordedOn(t)[0] ? recordedOn(t)[0].label : "" };
  });
  /* Who decided, when the page says; when it does not, the owner, said as the owner and not as the decider. */
  const whoSaid = (e) => (e.by ? e.by : e.owner ? `Owner ${e.owner}` : "Nobody recorded");
  const withOptions = entries.filter((e) => !e.bare), bareOnes = entries.filter((e) => e.bare);
  const haystack = (e) => [e.name, e.chosen.label, e.chosen.said, e.by, e.recordedIn, ...e.rejected.flatMap((o) => [o.label, o.reason]), ...e.affects.map((a) => a.label), ...e.waits.map(titleOf)].join(" ").toLowerCase();
  const worstWait = (e) => e.waits.map(unknownLevel).sort((a, b) => rank(b) - rank(a))[0] || "dark";

  /* ------------------------------------------------------------ what is shown */
  const pool = () => (st.bare ? entries : withOptions);
  function matching(ignoreState) {
    const q = st.q.trim().toLowerCase();
    return pool().filter((e) => (!q || haystack(e).includes(q)) && (!st.waiting || e.waits.length) && (ignoreState || !st.state || e.state === st.state));
  }
  function sorted(list) {
    const dir = st.flip ? -1 : 1, by = {
      state: (a, b) => STATE_ORDER[a.state] - STATE_ORDER[b.state] || cmp(b.date, a.date) || cmp(a.name, b.name),
      name: (a, b) => cmp(a.name.toLowerCase(), b.name.toLowerCase()),
      date: (a, b) => (a.date ? 0 : 1) - (b.date ? 0 : 1) || cmp(b.date, a.date) || cmp(a.name, b.name),
      waits: (a, b) => b.waits.length - a.waits.length || cmp(a.name, b.name),
    }[st.sort];
    return list.slice().sort((a, b) => dir * by(a, b));
  }
  const visible = () => sorted(matching(false));
  const byId = (id) => entries.find((e) => e.id === id) || null;

  /* ------------------------------------------------------------ the log */
  const stateMark = (e) => (e.state === "pending" ? pendingPill(e.pending) : h("span", { class: "pill dl-" + e.state, title: STATE_SAY[e.state] }, STATES.find(([id]) => id === e.state)[1]));
  function waitsLine(e) {
    if (!e.waits.length) return h("span", { class: "muted" }, "No open question waits on it");
    return h("span", { class: "dl-waits" }, lampEl(worstWait(e)), `Waits on ${plural(e.waits.length, "open question")}`);
  }
  function rejectedList(e, max) {
    if (!e.rejected.length) return h("span", { class: "muted" }, e.bare ? "No options recorded" : "No alternatives recorded");
    const items = e.rejected.slice(0, max).map((o) => h("li", { title: `${o.label}: ${o.reason || "no reason recorded"}` }, h("span", { class: "dl-x", "aria-hidden": "true" }, o.forNow ? "◌" : "✕"),
      h("b", {}, o.label), h("span", { class: "dl-why" }, o.reason ? ` ${o.reason.replace(/^["“]|["”]$/g, "")}` : " no reason recorded")));
    if (e.rejected.length > max) items.push(h("li", { class: "dl-more" }, `and ${e.rejected.length - max} more`));
    return h("ul", { class: "dl-rej" }, items);
  }
  function row(e) {
    const open = () => select(e.id);
    return h("div", { class: "dl-row" + (st.open === e.id ? " on" : ""), role: "row", tabindex: 0, "data-decision": e.id, "aria-selected": String(st.open === e.id),
      onclick: open, onkeydown: (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } } },
      h("div", { class: "dl-c dl-state", role: "cell", "data-label": "State" }, stateMark(e)),
      h("div", { class: "dl-c dl-what", role: "cell", "data-label": "Decision" }, h("b", { class: "dl-name" }, e.name),
        e.chosen.said ? h("span", { class: "dl-chosen" }, e.chosen.said) : null, e.recordedIn && e.recordedIn !== e.name ? h("span", { class: "dl-in" }, `Written down in ${e.recordedIn}`) : null),
      h("div", { class: "dl-c dl-not", role: "cell", "data-label": "Turned down" }, rejectedList(e, 2)),
      h("div", { class: "dl-c dl-when", role: "cell", "data-label": "Decided" }, h("span", {}, e.date ? longDate(e.date) : "No date recorded"), h("span", { class: "muted" }, whoSaid(e))),
      h("div", { class: "dl-c dl-fx", role: "cell", "data-label": "What it affects and waits on" }, h("span", {}, e.affects.length ? `Affects ${e.affects.slice(0, 2).map((a) => a.label).join(", ")}${e.affects.length > 2 ? ` and ${e.affects.length - 2} more` : ""}` : "Affects nothing recorded"), waitsLine(e)));
  }
  function head() {
    const col = (id, label) => h("button", { class: "dl-th" + (st.sort === id ? " on" : ""), role: "columnheader", "aria-sort": st.sort === id ? (st.flip ? "descending" : "ascending") : "none", "data-sort": id,
      onclick: () => { if (st.sort === id) st.flip = !st.flip; else { st.sort = id; st.flip = false; } refresh(); } }, label, st.sort === id ? h("span", { "aria-hidden": "true" }, st.flip ? " ↑" : " ↓") : null);
    return h("div", { class: "dl-head", role: "row" }, col("state", "State"), col("name", "Decision"), h("span", { class: "dl-th plain", role: "columnheader" }, "Turned down, and why"), col("date", "Decided"), col("waits", "What it affects and waits on"));
  }
  function log(list) {
    const box = h("div", { class: "dl-log", role: "table", "aria-label": "Decisions" }, head());
    for (const e of list) box.append(row(e));
    return box;
  }

  /* ------------------------------------------------------------ the timeline: a compact dated list */
  function timeline(list) {
    const dated = list.filter((e) => e.date).sort((a, b) => cmp(a.date, b.date) || cmp(a.name, b.name)), undated = list.filter((e) => !e.date);
    const months = [...new Set(dated.map((e) => e.date.slice(0, 7)))];
    const month = (ym) => `${["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][+ym.slice(5) - 1]} ${ym.slice(0, 4)}`;
    const item = (e) => h("li", {}, h("button", { class: "dl-tl" + (st.open === e.id ? " on" : ""), "data-decision": e.id, onclick: () => select(e.id) },
      h("i", { class: "dl-dot dl-" + e.state, title: STATES.find(([id]) => id === e.state)[1] }), h("span", { class: "dl-tl-d" }, e.date ? day(e.date) : "no date"), h("b", {}, e.name),
      h("span", { class: "dl-tl-s" }, STATES.find(([id]) => id === e.state)[1])));
    const out = months.map((ym) => h("section", { class: "dl-month" }, h("h3", {}, month(ym)), h("ol", {}, dated.filter((e) => e.date.startsWith(ym)).map(item))));
    if (undated.length) out.push(h("section", { class: "dl-month" }, h("h3", {}, "No date recorded"), h("ol", {}, undated.map(item))));
    return h("div", { class: "dl-time", "aria-label": "Decisions by date" }, out);
  }

  /* ------------------------------------------------------------ one decision, as a decision record */
  function readerSection(key, name) {
    const page = D.reader[key];
    if (!page) return null;
    const box = h("div", { html: page.html }), start = $$("h2", box).find((x) => x.textContent.trim().toLowerCase() === name);
    if (!start) return null;
    const out = h("div", { class: "reader dl-prose" });
    for (let n = start.nextElementSibling; n && n.tagName !== "H2"; n = n.nextElementSibling) out.append(n.cloneNode(true));
    return out.childNodes.length ? out : null;
  }
  const sec = (title, ...kids) => { const body = kids.flat().filter(Boolean); return body.length ? h("section", { class: "dl-sec" }, h("h3", {}, title), ...body) : null; };
  function options(e) {
    const c = e.chosen, items = [h("li", { class: "chosen" }, h("span", { class: "dl-mark", "aria-hidden": "true" }, "✓"), h("div", {}, h("b", {}, c.label), h("span", { class: "dl-tag" }, "Chosen"),
      c.condition ? h("p", {}, `On condition that ${c.condition}`) : null))];
    for (const o of e.rejected) items.push(h("li", { class: "rejected" }, h("span", { class: "dl-mark", "aria-hidden": "true" }, o.forNow ? "◌" : "✕"),
      h("div", {}, h("b", {}, o.label), h("span", { class: "dl-tag" }, o.forNow ? "Set aside for now" : "Turned down"), h("p", {}, o.reason ? o.reason.replace(/^["“]|["”]$/g, "") : "No reason recorded."))));
    return h("ul", { class: "dl-options" }, items);
  }
  function chips(list) { return h("div", { class: "dl-chips" }, list.map((k) => refChip(k))); }
  function detail(e) {
    const t = e.t, w = proseCarrier(t), d = e.decider, adr = t.adr ? t.adr.key : "";
    const context = (adr && readerSection(adr, "context")) || (w.text && h("p", { class: "dl-p" }, shorten(w.text, 600)));
    const decision = (adr && readerSection(adr, "decision")) || (e.chosen.said || w.text ? h("p", { class: "dl-p" }, shorten(t.adr ? t.adr.decision : w.text, 600)) : h("p", { class: "muted" }, `The page records the pick as ${e.chosen.label}.`));
    const consequences = adr ? readerSection(adr, "consequences") : null;
    const status = adr ? readerSection(adr, "status") : null;
    const idx = visible().findIndex((x) => x.id === e.id), list = visible();
    const nav = h("div", { class: "dl-nav" }, h("button", { class: "linkish dl-back", onclick: () => select("") }, "← All decisions"), h("span", { class: "spacer" }),
      h("button", { class: "icon-btn", "aria-label": "The decision before", disabled: idx > 0 ? null : true, onclick: () => select(list[idx - 1].id) }, "‹"),
      h("button", { class: "icon-btn", "aria-label": "The decision after", disabled: idx >= 0 && idx < list.length - 1 ? null : true, onclick: () => select(list[idx + 1].id) }, "›"),
      h("button", { class: "icon-btn dl-close", "aria-label": "Close the record", onclick: () => select("") }, "✕"));
    const hist = [status, d.sessions.length ? h("ul", { class: "dl-hist" }, d.sessions.map((s) => h("li", {}, h("span", { class: "dl-tl-d" }, sessionDate(s) ? day(sessionDate(s)) : ""), ent(s) ? refChip(s) : sessionTitle(s)))) : null,
      e.pending ? h("p", { class: "dl-p" }, pendingPill(e.pending), ` ${person(e.pending.by)}, ${e.pending.date}: the owner has not reviewed it.`) : null,
      d.conf.length ? h("p", { class: "dl-p" }, `Confirmed by ${d.conf.join("; ")}.`) : h("p", { class: "dl-p" + (d.overrides ? " warn" : " muted") }, d.overrides ? `Not confirmed yet, and it stands on ${plural(d.overrides, "override")}.` : "No confirmation is recorded.")];
    const trace = [t.adr ? t.adr.id : null, t.adr ? null : w.key].filter(Boolean);
    return h("article", { class: "dl-detail", "aria-label": `Decision: ${e.name}` }, nav,
      h("p", { class: "dl-kicker" }, t.adr ? "Decision record" : e.bare ? "Decided, no options recorded" : `Decision recorded in ${e.recordedIn}`),
      h("h2", {}, e.name),
      h("div", { class: "dl-meta" }, stateMark(e), h("span", {}, e.date ? `Decided ${longDate(e.date)}` : "No decision date recorded"), h("span", {}, e.by ? `by ${e.by}` : e.owner ? `owned by ${e.owner}` : "")),
      sec("Context", context), sec("Options considered", e.bare ? null : options(e)), sec("Decision", decision),
      sec("Consequences", consequences, e.affects.length ? h("div", { class: "dl-fx-row" }, h("span", { class: "dl-l" }, "What it affects"), chips(e.affects.map((a) => a.key))) : null,
        e.waits.length ? h("div", { class: "dl-fx-row" }, h("span", { class: "dl-l" }, "Still waits on"), chips(e.waits)) : null,
        e.answered.length ? h("div", { class: "dl-fx-row" }, h("span", { class: "dl-l" }, "Answered"), chips(e.answered)) : null,
        !consequences && !e.affects.length && !e.waits.length && !e.answered.length ? h("p", { class: "muted" }, "The record doesn't name anything it changes, and no question waits on it.") : null),
      sec("History", hist),
      h("p", { class: "dl-trace", title: "How this decision is named in the plan, to find it again" }, "Plan reference: ", trace.map((x) => h("code", {}, x)), h("code", {}, e.t.id)));
  }

  /* ------------------------------------------------------------ the page */
  function bar() {
    const all = matching(true), seg = (id, label, n) => h("button", { "aria-pressed": String(st.state === id), "data-state": id, disabled: id && !n ? true : null,
      onclick: () => { st.state = st.state === id ? "" : id; refresh(); } }, label, h("span", { class: "dl-n" }, String(n)));
    const search = h("input", { type: "search", class: "dl-find", placeholder: "Find a decision, an option, a person", "aria-label": "Find a decision", value: st.q, autocomplete: "off", spellcheck: "false" });
    search.addEventListener("input", () => { st.q = search.value; refresh({ keepBar: true }); });
    return h("div", { class: "dl-bar" },
      search,
      h("div", { class: "seg small", role: "group", "aria-label": "State" }, seg("", "All", all.length), STATES.map(([id, label]) => seg(id, label, all.filter((e) => e.state === id).length))),
      h("button", { class: "chip" + (st.waiting ? " on" : ""), "aria-pressed": String(st.waiting), "data-filter": "waiting", title: "Only decisions an open question still waits on", onclick: () => { st.waiting = !st.waiting; refresh(); } }, "Waiting on a question"),
      bareOnes.length ? h("button", { class: "chip" + (st.bare ? " on" : ""), "aria-pressed": String(st.bare), "data-filter": "bare", title: "Decisions with no options written down", onclick: () => { st.bare = !st.bare; refresh(); } },
        `${st.bare ? "Hide" : "Include"} ${plural(bareOnes.length, "decision")} with no options written down`) : null,
      h("span", { class: "spacer" }),
      h("label", { class: "dl-sort" }, "Sort ", h("select", { "aria-label": "Sort the decisions", onchange: (ev) => { st.sort = ev.target.value; st.flip = false; refresh(); } },
        SORTS.map(([id, label]) => h("option", { value: id, selected: st.sort === id ? true : null }, label)))),
      h("div", { class: "seg small", role: "group", "aria-label": "Show as" }, [["log", "Log"], ["timeline", "Timeline"]].map(([id, label]) =>
        h("button", { "aria-pressed": String(st.mode === id), "data-mode": id, onclick: () => { st.mode = id; refresh(); } }, label))));
  }
  function summary(list) {
    const waiting = new Set(list.flatMap((e) => e.waits)).size, turned = list.reduce((n, e) => n + e.rejected.length, 0);
    return `${list.length === pool().length ? plural(list.length, "decision") : `${list.length} of ${plural(pool().length, "decision")}`}, ${plural(turned, "option")} turned down, ${waiting ? `${plural(waiting, "open question")} still to answer before they're final` : "no open question still to answer"}.`;
  }
  function render(main) {
    const stage = h("div", { class: "dl-stage" });
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, Nav.title("Decisions")),
      h("p", {}, "Every decision the plan records: what was chosen, what was turned down and why, who decided and when, and which open questions it still waits on. Pick one to read it as a decision record.")),
      h("div", { class: "spacer" }), Nav.pageActions()));
    if (!trees.length) { main.append(emptyState("No decision records its options yet.", "An Options considered line, or a decision record with an Alternatives considered table, is listed here.", "/vela:shape")); return; }
    main.append(h("div", { class: "dl-wrap" }, h("div", { class: "dl-barhost" }, bar()), h("p", { class: "dl-count", id: "dl-count", "aria-live": "polite" }), stage));
    paint();
  }
  /* The list and the record, redrawn in place; the bar is kept while its search box has the focus. */
  function paint() {
    const stage = $(".dl-stage"), list = visible();
    if (!stage) return;
    stage.className = "dl-stage" + (st.open ? " has-open" : "");
    stage.innerHTML = "";
    const left = h("div", { class: "dl-left" }, list.length ? (st.mode === "timeline" ? timeline(list) : log(list))
      : h("div", { class: "dl-none" }, h("b", {}, "No decision matches."), " Clear the search or the filters to see them all. ", h("button", { class: "linkish", onclick: () => { Object.assign(st, { q: "", state: "", waiting: false }); refresh(); } }, "Clear filters")));
    stage.append(h("div", { class: "dl-listwrap" }, left));
    const open = st.open && byId(st.open);
    if (open) stage.append(detail(open));
    $("#dl-count").textContent = summary(list);
  }
  /* While the search box has the focus the bar stays as it is, and only the state counts are brought up to date. */
  function refresh(opts = {}) {
    const host = $(".dl-barhost");
    if (host && !opts.keepBar) host.replaceChildren(bar());
    else if (host) {
      const all = matching(true);
      $$("button[data-state]", host).forEach((b) => { const n = b.dataset.state ? all.filter((e) => e.state === b.dataset.state).length : all.length; $(".dl-n", b).textContent = String(n); b.disabled = !!b.dataset.state && !n; });
    }
    paint();
  }
  /* Pick a decision; the panel follows it, as it follows a box on the map. */
  function select(id) {
    st.open = id;
    const e = id ? byId(id) : null;
    if (e) go(e.key, { reset: true, quiet: true });
    paint();
    if (e) { const on = $(".dl-row.on, .dl-tl.on"); if (on) on.scrollIntoView({ block: "nearest" }); }
  }
  document.addEventListener("keydown", (ev) => {
    if (App.view !== "decisions" || (ev.target.closest && ev.target.closest("input, select, textarea"))) return;
    if (ev.key === "Escape" && st.open) { select(""); return; }
    if ((ev.key === "ArrowDown" || ev.key === "ArrowUp") && ev.target.closest && ev.target.closest(".dl-row")) {
      const list = visible(), i = list.findIndex((x) => x.id === ev.target.dataset.decision), next = list[i + (ev.key === "ArrowDown" ? 1 : -1)];
      if (next) { ev.preventDefault(); const to = $(`.dl-row[data-decision="${next.id}"]`); if (to) to.focus(); }
    }
  });
  /* A deep link, a search result or a click on a decision anywhere opens its record here. */
  function showFor(key) {
    const e = entries.find((x) => (x.t.adr && x.t.adr.key === key) || x.t.carriedBy.some((w) => w.key === key || w.page === key) || x.waits.includes(key) || x.answered.includes(key));
    if (!e) return -1;
    if (e.bare) st.bare = true;
    st.open = e.id;
    if (App.view === "decisions") refresh();
    return entries.indexOf(e);
  }
  function here() {
    const e = st.open && byId(st.open);
    const keys = e ? e.t.carriedBy.map((w) => w.key).flatMap(mapAnchors) : [];
    return keys.length ? keys : null;
  }
  return { render, select, showFor, here, highlight: (k) => { if (App.view === "decisions") showFor(k); }, trees, entries, st, visible, STATES };
})();
View("decisions", { label: "Decisions", alias: "garden", title: "The decisions: what was chosen, what was turned down, and what each waits on", render: Decisions.render, here: Decisions.here, highlight: Decisions.highlight,
  count: () => String(Decisions.trees.length) });
