/* Who to ask: every open question as a paper strip in the rack of the person who holds the answer, like flight
   strips on a controller's board. The rack comes from the unknown's **Ask:** line, or, when it has none, a guess from
   its Owner line, marked with a pen question mark. A strip's edge is its light, by attention.hold: the same rule
   as every map. Drag a strip to another rack, flip it to read its blocking chain, declare it critical, meet a
   person. Nothing here writes to the vault: every change becomes a proposed line in the tray, to record by hand.
   This absorbs the old "What's holding things up" view; its chains are on each strip's flip side and in the panel. */
const Asks = (() => {
  /* "@product-owner (Product owner)" is how a page writes an owner; a reader hears the name in the brackets. */
  const ownerSaid = (raw) => { const m = String(raw || "").match(/^(@[\w/-]+)\s*\(([^)]+)\)\s*$/); return !raw ? "nobody yet" : peopleWords(m ? m[2] : raw); };
  const CRIT = "__critical";
  const store = `asks:${D.vaultId}`;
  const st = { days: null, widened: false, q: "", holdingOnly: false, meeting: "", expandedLater: new Set(), expandedDone: new Set(), flipped: new Set() };
  let marks = load();
  function load() { return Settings.readJson(store, fresh(), "the Who-to-ask board's marks"); }
  function fresh() { return { moved: {}, critical: {}, cocked: {}, asked: {} }; }
  function save() { try { localStorage.setItem(store, JSON.stringify(marks)); } catch (e) { console.warn("[asks] this browser would not keep the board marks:", e.message); } }
  const U = (id) => ASK[id];
  const rackOf = (u) => marks.moved[u.id] || u.ask.key;
  const holdsOf = (id) => (UNKNOWN[id] || { blocks: [] }).blocks;
  const shortId = (k) => (/^[A-Z]{2,}-/.test(idOf(k)) ? idOf(k) : "");
  function people() {
    const map = new Map();
    for (const u of D.asks) {
      const k = u.ask.key;
      if (!map.has(k)) map.set(k, { key: k, name: u.ask.name, handle: k.startsWith("@") ? k : "", inferred: 0, total: 0, unrecorded: 0 });
      const person = map.get(k);
      person.total++;
      if (u.ask.inferred) person.inferred++;
      if (!u.ask.recorded) person.unrecorded++;
    }
    return map;
  }
  const daysTo = (u) => isDate(u.askBy) ? dayNum(u.askBy) - TODAY : null;
  const inWindow = (u) => { const d = daysTo(u); return d === null ? st.days > 999 : d <= st.days; };
  function fill(u) {
    if (!isDate(u.opened) || !isDate(u.askBy)) return 0;
    const a = dayNum(u.opened), b = dayNum(u.askBy);
    return b <= a ? (TODAY >= b ? 1 : 0) : clamp((TODAY - a) / (b - a), 0, 1);
  }
  function matches(u) {
    if (st.holdingOnly && !holdsOf(u.id).length) return false;
    if (!st.q) return true;
    const hay = [u.id, E[u.id] ? E[u.id].title : "", u.question, u.ask.name, u.ask.key, u.ownerRaw, ...holdsOf(u.id).map((k) => k + " " + titleOf(k))].join(" ").toLowerCase();
    return st.q.toLowerCase().split(/\s+/).every((w) => hay.includes(w));
  }

  function holdsHtml(u) {
    const holds = holdsOf(u.id);
    if (!holds.length) return `<span class="label">blocks</span><span class="none">doesn't say</span>`;
    const first = holds[0], more = holds.length > 1 ? ` <span class="more">+${holds.length - 1}</span>` : "";
    return `<span class="label">blocks${more}</span><span class="tag-word hl" title="${esc(shortId(first) || titleOf(first))}">${esc(titleOf(first))}</span>`;
  }
  /* The flip side's blocking chain: what the Blocks line links, then what that is used by, from the typed record. */
  function chainHtml(u) {
    const holds = holdsOf(u.id);
    if (!holds.length) return `nothing: “${esc(u.holdsReason || (UNKNOWN[u.id] || {}).blocksText || "it doesn't say what it blocks")}”`;
    return holds.map((k) => {
      const parts = [`<a data-ref="${esc(k)}">${esc(titleOf(k))}${shortId(k) ? `<span class="id-tag">${esc(shortId(k))}</span>` : ""}</a>`];
      if (CONTRACT[k]) parts.push(`${esc(titleOf(CONTRACT[k].provider))} → ${esc(CONTRACT[k].consumers.map(titleOf).join(", "))}`);
      const fl = flowsFor(k);
      if (fl.length) parts.push(`used in ${fl.map((r) => `<a data-ref="${esc(r.flow)}" data-reveal>${esc(E[r.flow].title)}</a>`).join(", ")}`);
      return parts.join(", ");
    }).join("<br>") + ((UNKNOWN[u.id] || {}).holds.length > holds.length ? `<br><span class="muted">${UNKNOWN[u.id].holds.length} things held up in all, counting knock-on effects.</span>` : "");
  }
  function stripHtml(u) {
    const resolved = u.state !== "open", lvl = resolved ? "done" : u.light.level, crit = !!marks.critical[u.id], fails = crit && !holdsOf(u.id).length;
    const cls = ["strip", resolved ? "resolved" : "", marks.cocked[u.id] ? "cocked" : "", st.flipped.has(u.id) ? "flipped" : "", marks.asked[u.id] ? "asked" : "", fails ? "fails-check" : ""].filter(Boolean).join(" ");
    const title = E[u.id] ? E[u.id].title : u.id, q = u.question || title;
    const inferred = u.ask.inferred && !marks.moved[u.id] ? `<span class="mark inferred" title="${esc(u.ask.rule)}">?</span>` : "";
    const front = resolved
      ? `<div class="front"><div class="edge"></div><div class="cellbox idbox" title="${u.id}"><div class="rel">answered</div></div>
          <div class="cellbox qbox"><div class="q authored">${esc(q)}</div></div><div class="cellbox holdbox">${holdsHtml(u)}</div></div>`
      : `<div class="front"><div class="edge"></div>
          <div class="cellbox idbox" title="${u.id}"><div class="due">${esc(day(u.askBy))}</div><div class="rel">${relDueWords(u.askBy)}</div></div>
          <div class="cellbox qbox"><div class="q authored">${esc(q)}</div></div><div class="cellbox holdbox">${holdsHtml(u)}</div>
          <div class="timebar" title="Opened ${esc(day(u.opened))}, answer needed by ${esc(day(u.askBy))}"><i style="width:${(fill(u) * 100).toFixed(1)}%"></i></div>
          ${inferred}${fails ? `<span class="mark critical-note" title="Critical, but it doesn't say what it holds up. Add that in the next session, or unmark it.">Not blocking anything</span>` : ""}${marks.asked[u.id] ? `<span class="mark tick">✓</span>` : ""}</div>`;
    const who = marks.moved[u.id] ? `moved here by you; the plan ${u.ask.inferred ? "guessed" : "says"} <i>${esc(u.ask.name)}</i>` : u.ask.inferred ? `<span class="inferred-why">${esc(u.ask.rule)}</span>` : esc(u.ask.rule);
    const back = `<div class="face back"><h4>${esc(title)}<span class="id-tag">${u.id}</span></h4><dl>
        <dt>Holds up</dt><dd class="chain-cell">${chainHtml(u)}</dd>
        <dt>Who to ask</dt><dd>${who}</dd>
        ${resolved && u.outcome ? `<dt>Answer</dt><dd class="clamp authored">${esc(u.outcome)}</dd>` : `<dt>Question</dt><dd class="clamp authored">${esc(q)}</dd>`}
        <dt>Owner</dt><dd>${esc(ownerSaid(u.ownerRaw))}</dd>
        <dt>Dates</dt><dd>opened ${esc(day(u.opened))}${u.askBy ? `, answer needed by ${esc(day(u.askBy))}` : u.askByRaw ? `, answer needed by "${esc(u.askByRaw)}", which isn't a date` : ""}</dd></dl>
        ${resolved ? "" : `<div class="actions"><button data-act="open">Details</button><button data-act="crit">${crit ? "Not critical" : "Mark critical"}</button>
          <button data-act="cock">${marks.cocked[u.id] ? "Put back" : "Pull forward"}</button><button data-act="asked">${marks.asked[u.id] ? "Not asked yet" : "Mark asked"}</button>
          <button data-act="flip">Turn back over</button></div>`}</div>`;
    return `<div class="${cls}" data-id="${u.id}" data-level="${lvl}" style="--u:${resolved ? 0 : u.light.urgency}" tabindex="0" role="button" aria-label="${esc(q)}. ${resolved ? "Answered" : "Answer needed by " + esc(day(u.askBy))}.">
      <div class="card"><div class="face front-face">${front}</div>${back}</div></div>`;
  }
  function bays() {
    const ppl = people();
    for (const k of Object.values(marks.moved)) if (!ppl.has(k)) ppl.set(k, { key: k, name: k, handle: k.startsWith("@") ? k : "", inferred: 0, total: 0, unrecorded: 0 });
    const out = new Map(), mk = (key, person) => ({ key, person, open: [], shown: [], later: [], done: [], filteredOut: 0, failing: 0 });
    out.set(CRIT, mk(CRIT, null));
    for (const [k, p] of ppl) out.set(k, mk(k, p));
    const totals = { open: 0, shown: 0, later: 0, done: 0, filtered: 0 };
    const byDate = (a, b) => cmp(a.askBy || "9999", b.askBy || "9999") || cmp(a.id, b.id);
    for (const u of [...D.asks].sort(byDate)) {
      const resolved = u.state !== "open", bay = !resolved && marks.critical[u.id] ? out.get(CRIT) : out.get(rackOf(u));
      if (!matches(u)) { bay.filteredOut++; totals.filtered++; continue; }
      if (resolved) { bay.done.push(u); totals.done++; continue; }
      bay.open.push(u); totals.open++;
      if (bay.key === CRIT) { bay.shown.push(u); totals.shown++; if (!holdsOf(u.id).length) bay.failing++; continue; }
      if (inWindow(u) || marks.cocked[u.id] || (daysTo(u) !== null && daysTo(u) < 0)) { bay.shown.push(u); totals.shown++; } else { bay.later.push(u); totals.later++; }
    }
    const list = [...out.values()].filter((b) => b.key === CRIT || b.open.length || b.done.length || b.filteredOut);
    const first = (b) => (b.open[0] && b.open[0].askBy) || "9999";
    list.sort((a, b) => (a.key === CRIT ? -1 : b.key === CRIT ? 1 : cmp(first(a), first(b)) || b.open.length - a.open.length));
    const m = list.findIndex((b) => b.key === st.meeting);
    if (m > 0) list.unshift(...list.splice(m, 1));
    return { list, totals };
  }
  /* A rack whose questions carry no Ask line is where the owner sits, not a record that anyone was asked. */
  function notAsked(p) {
    if (!p.unrecorded) return "";
    const all = p.unrecorded === p.total;
    return `<div class="not-asked" title="Nobody is named to answer these, so they sit with the owner (or with our guess); it doesn't mean anyone was asked">${all ? "<b>Nobody's named to answer these</b>, so they sit with the owner" : `${p.unrecorded} of ${p.total} have nobody named to answer them, so they sit with the owner`}. Name someone in the next session.</div>`;
  }
  function bayHtml(b) {
    const isCrit = b.key === CRIT, first = b.open.find((u) => isDate(u.askBy));
    const worst = b.open.map((u) => u.light.level).sort((x, y) => rank(y) - rank(x))[0];
    const head = isCrit
      ? `<h2>Critical</h2><div class="who-meta">Drag a question here to put it first in the next session.</div>${b.open.length ? `<div class="counts"><b>${b.open.length}</b> marked${b.failing ? `, <b>${b.failing}</b> not blocking anything` : ""}</div>` : ""}`
      : `<h2>${worst && worst !== "dark" ? `<i class="lamp ${worst}"></i>` : ""}${esc(b.person.name)}</h2><div class="who-meta"${b.person.handle ? ` title="${esc(b.person.handle)}"` : ""}>${b.person.handle ? "" : "No contact recorded"}${b.person.inferred ? `${b.person.handle ? "" : ", "}${b.person.inferred} here by our guess` : ""}</div>${notAsked(b.person)}
         <div class="counts">${first ? `First due <b>${esc(day(first.askBy))}</b>` : b.open.length ? "No answer date set" : "Nothing open"}${b.done.length ? `, ${b.done.length} answered` : ""}</div>
         <button class="meet" data-meet="${esc(b.key)}" title="Go through this person's questions with them">${st.meeting === b.key ? "End meeting" : "Meet"}</button>`;
    let body = b.shown.map(stripHtml).join("");
    if (isCrit && !b.shown.length) body = `<div class="empty-hint">Nothing marked critical yet.</div>`;
    if (b.later.length) {
      const open = st.expandedLater.has(b.key);
      if (open) body += b.later.map(stripHtml).join("");
      body += `<button class="later" data-later="${esc(b.key)}"><span>${open ? `Tuck the <b>${b.later.length}</b> later ones away again` : `+ <b>${b.later.length}</b> later${b.later[0].askBy ? `, the earliest due ${esc(day(b.later[0].askBy))}` : ""}`}</span></button>`;
    }
    if (b.done.length) {
      const open = st.expandedDone.has(b.key);
      if (open) body += b.done.map(stripHtml).join("");
      body += `<button class="later" data-done="${esc(b.key)}"><span>${open ? "Tuck the answered ones away" : `<b>${b.done.length}</b> answered, tucked away`}</span></button>`;
    }
    return `<section class="bay${isCrit ? " critical" : ""}${st.meeting === b.key ? " front-bay" : ""}" data-bay="${esc(b.key)}" aria-label="${isCrit ? "Critical" : esc(b.person.name)}">
      <div class="bay-head">${head}</div><div class="rails">${body}</div>${b.filteredOut ? `<div class="who-meta filtered">${b.filteredOut} hidden by the filter</div>` : ""}</section>`;
  }

  function render(main) {
    // It opens on the next 14 days. When nothing open falls there, it opens on all of them and says so.
    if (st.days === null) {
      const open = D.asks.filter((u) => u.state === "open");
      st.days = open.length && !open.some((u) => daysTo(u) !== null && daysTo(u) <= 14) ? 9999 : 14;
      st.widened = st.days === 9999 && open.length > 0;
    }
    const { list, totals } = bays();
    main.append(h("div", { class: "view-head asks-head" },
      h("div", {}, h("h1", {}, "Who to ask"), h("p", {}, "Who you need answers from, and by when. Start with the person at the left: their questions fall due first. Click a question to see what it holds up.", Nav.ledeLink())),
      h("div", { class: "spacer" }),
      h("input", { type: "search", class: "board-find", placeholder: "Find a question or a person", value: st.q, oninput: (e) => { st.q = e.target.value.trim(); repaint(); } }),
      h("button", { class: "chip" + (st.holdingOnly ? " on" : ""), onclick: () => { st.holdingOnly = !st.holdingOnly; rerender(); }, title: "Only questions that say what they block" }, "Blocking something"),
      h("label", { class: "meet-pick" }, "Meeting with ", h("select", { onchange: (e) => meet(e.target.value) },
        h("option", { value: "" }, "pick a person"), list.filter((b) => b.key !== CRIT && b.open.length).map((b) => h("option", { value: b.key, selected: st.meeting === b.key ? "" : null }, `${b.person.name} (${b.open.length})`))))));
    const DUE = [[7, "In 7 days", "questions due this week, and any overdue"], [14, "In 14 days", "the next two weeks, and any overdue"], [30, "In 30 days", "the next month, and any overdue"], [9999, "Any time", "every open question, whenever it is due"]];
    const dueMenu = Menus.menu({ id: "due", label: "Due", current: DUE.find(([d]) => d === st.days)[1], title: "Show the questions due within this long",
      items: () => DUE.map(([d, label, say]) => ({ id: String(d), label, say, checked: st.days === d, attrs: { "data-days": String(d) }, run: () => { st.days = d; st.widened = false; rerender(); } })) });
    const diagram = [h("div", { class: "countline", id: "asks-tally" }, tally(list, totals)),
      h("nav", { class: "rack-index", id: "rack-index" }, list.filter((b) => b.key !== CRIT || b.open.length).map((b) => h("button", { "data-jump": b.key, class: (b.key === CRIT ? "crit " : "") + (b.open.some((u) => u.light.level === "warning") ? "late" : "") },
        b.key === CRIT ? "Critical" : b.person.name, h("b", {}, b.open.length))))];
    if (st.meeting) {
      const b = list.find((x) => x.key === st.meeting);
      if (b) diagram.push(h("div", { class: "meeting-banner" }, h("b", {}, `Meeting with ${b.person.name}`),
        h("span", {}, `${plural(b.open.length, "question")} to ask, ${b.open.filter((u) => marks.asked[u.id]).length} ticked as asked. Turn a question over to tick it; each tick becomes a line in the changes list.`),
        h("button", { class: "btn", onclick: () => meet("") }, "Done")));
    }
    const wrap = h("div", { class: "board-wrap", id: "asks-wrap" }, h("div", { class: "strip-board", id: "strip-board", html: list.map(bayHtml).join("") }));
    main.append(Menus.frame({ left: [dueMenu], right: [Nav.moreMenu()] }, ...diagram, wrap), tray());
    renderTray();
    if (!D.asks.length) wrap.append(emptyState("No open questions yet.", "Nobody is waiting on an answer. A grill session finds them.", "/vela:grill"));
    const tex = Assets.texture("strip-board");
    if (tex) wrap.style.setProperty("--texture", `url("${tex}")`);
  }
  /* The answer first: how many, with how many people, and when. The open count is D.counts.openQuestions, the number every
     view gives (E60); a search or the Blocking filter narrows it, and then it is this board's own and not tagged. */
  function tally(list, t) {
    const whole = !t.filtered, n = whole ? D.counts.openQuestions : t.open, people = list.filter((b) => b.key !== CRIT).length;
    const when = st.widened ? ", none due in the next two weeks" : st.days > 999 ? "" : `; ${t.shown} due within ${st.days} days, plus any overdue, pulled forward or critical, are shown`;
    const folded = [t.later ? `${plural(t.later, "later one")}` : "", t.done ? `${plural(t.done, "answered question")}` : ""].filter(Boolean).join(" and ");
    return [h("b", whole ? { "data-quantity": "openQuestions", "data-n": String(n) } : {}, plural(n, "open question")), ` with ${plural(people, "person", "people")}${when}. `,
      folded || t.filtered ? h("span", { class: "hidden-note" }, (folded ? `${upFirst(folded)} ${t.later + t.done === 1 ? "is" : "are"} folded under ${t.later + t.done === 1 ? "its person" : "their people"}` : "") + (t.filtered ? `${folded ? "; " : ""}${t.filtered} hidden by the filter` : "") + ". ") : null,
      D.risks.length ? "Risks are on the Unknowns and risks page." : ""];
  }
  function repaint() {
    const { list, totals } = bays();
    const board = $("#strip-board"); if (!board) return;
    board.innerHTML = list.map(bayHtml).join("");
    const t = $("#asks-tally"); if (t) { t.innerHTML = ""; t.append(...tally(list, totals)); }
    renderTray();
  }
  function tray() {
    const box = h("aside", { class: "changes-tray", id: "changes-tray" },
      h("header", { onclick: () => box.classList.toggle("open") }, h("span", {}, h("b", {}, "Changes to note"), " ", h("span", { id: "tray-count" })), h("span", { class: "muted" }, "copy them into the plan yourself")),
      h("div", { class: "lines", id: "tray-lines" }),
      h("div", { class: "tray-actions" }, h("button", { class: "btn", onclick: copy, title: "Copy the changes as lines to paste into the plan" }, "Copy the changes as text"), h("button", { class: "btn", onclick: () => { marks = fresh(); save(); repaint(); toast("Undid every change on the board."); } }, "Undo all")));
    return box;
  }
  /* The lines a change proposes. Who to ask is vela's own **Ask:** field; the rest are session notes, because
     vela has no field for "critical" or "asked in a meeting" (yet). */
  function trayLines() {
    const out = [], ppl = people();
    const named = (id) => esc(E[id] ? E[id].title : id), whoIs = (key) => esc((ppl.get(key) || {}).name || human(key));
    for (const [id, key] of Object.entries(marks.moved)) { const u = U(id); if (u) out.push({ text: `<b>${named(id)}</b>: ask ${whoIs(key)} <span class="muted">(${u.ask.inferred ? "was a guess" : "the plan said"}: ${esc(u.ask.name)})</span>`, raw: `${id}: - **Ask:** ${key}` }); }
    for (const id of Object.keys(marks.critical)) { const u = U(id); if (!u) continue;
      out.push({ text: `<b>${named(id)}</b>: marked critical on ${esc(day(D.today))} (a note for the next session)${holdsOf(id).length ? "" : ` <span class="warn">It doesn't say what it holds up, and a critical question should hold up a decision.</span>`}`, raw: `${id}: session note, declared critical on ${D.today}` }); }
    for (const id of Object.keys(marks.asked)) out.push({ text: `<b>${named(id)}</b>: asked ${esc(U(id) ? U(id).ask.name : "")} on ${esc(day(D.today))}, waiting for the answer (a note for the next session)`, raw: `${id}: session note, asked on ${D.today}, answer pending` });
    const cocked = Object.keys(marks.cocked).length;
    if (cocked) out.push({ text: `<span class="muted">${plural(cocked, "question")} pulled forward: a mark on this board only, not saved.</span>`, raw: "" });
    return out;
  }
  /* "@legal-counsel" said as a person reads it: "Legal counsel". */
  const human = (key) => { const w = String(key || "").replace(/^@/, "").replace(/-/g, " "); return w.charAt(0).toUpperCase() + w.slice(1); };
  function renderTray() {
    const lines = trayLines(), box = $("#tray-lines"); if (!box) return;
    $("#tray-count").textContent = lines.filter((l) => l.raw).length ? `(${lines.filter((l) => l.raw).length})` : "";
    box.innerHTML = lines.length ? lines.map((l) => `<div class="line">${l.text}</div>`).join("") : `<div class="empty">Nothing yet. Moving a question, marking it critical or ticking it adds a line here, so nothing changes in the plan without you seeing it.</div>`;
  }
  async function copy() {
    const t = trayLines().map((l) => l.raw).filter(Boolean).join("\n");
    if (!t) { toast("Nothing to copy yet."); return; }
    try { await navigator.clipboard.writeText(t); toast("Copied. Paste the lines into the plan yourself."); } catch (e) { toast("This page can't use the clipboard; copy the lines from the changes list by hand."); }
  }
  function moveTo(id, bayKey) {
    const u = U(id); if (!u) return;
    if (bayKey === CRIT) { marks.critical[id] = true; if (!holdsOf(id).length) toast(`${titleOf(id)} is marked critical, but it doesn't say what it blocks. The changes list flags it.`); }
    else { delete marks.critical[id]; if (bayKey === u.ask.key) delete marks.moved[id]; else marks.moved[id] = bayKey; }
    save();
  }
  function flip(id) {
    if (st.flipped.has(id)) st.flipped.delete(id); else st.flipped.add(id);
    const elx = $(`.strip[data-id="${CSS.escape(id)}"]`);
    if (elx) elx.classList.toggle("flipped", st.flipped.has(id));
  }
  function meet(key) { st.meeting = st.meeting === key ? "" : key; if (App.view !== "asks") showView("asks"); else rerender(); if (st.meeting) { const w = $("#asks-wrap"); if (w) w.scrollLeft = 0; } }

  /* ---------- dragging strips between racks ---------- */
  let drag = null, scrollRaf = 0;
  document.addEventListener("pointerdown", (e) => {
    const strip = App.view === "asks" && e.target.closest(".strip:not(.resolved)");
    if (!strip || e.button !== 0 || e.target.closest("button, a")) return;
    drag = { strip, id: strip.dataset.id, x0: e.clientX, y0: e.clientY, started: false };
  });
  document.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
    if (!drag.started) { if (Math.hypot(dx, dy) < 5) return; startDrag(); }
    const g = drag.ghost;
    g.style.left = drag.r.left + dx + "px"; g.style.top = drag.r.top + dy + "px";
    g.style.transform = `scale(1.035) rotate(${-1.2 + clamp((e.movementX || 0) * 0.4, -4, 4)}deg)`;
    placeSlot(e.clientX, e.clientY);
    autoScroll(e.clientX);
  });
  document.addEventListener("pointerup", (e) => {
    if (!drag) return;
    const d = drag; drag = null;
    if (!d.started) { flip(d.id); go(d.id, { quiet: true }); return; }
    finishDrag(d);
  });
  function startDrag() {
    drag.started = true; st.flipped.delete(drag.id); drag.strip.classList.remove("flipped");
    const r = drag.r = drag.strip.getBoundingClientRect(), g = drag.strip.cloneNode(true);
    g.classList.add("ghost"); g.classList.remove("cocked");
    Object.assign(g.style, { width: r.width + "px", height: r.height + "px", left: r.left + "px", top: r.top + "px" });
    document.body.appendChild(g); drag.ghost = g;
    drag.slot = h("div", { class: "slot" }); drag.strip.after(drag.slot);
    drag.strip.style.display = "none";
    drag.fromBay = drag.toBay = drag.strip.closest(".bay").dataset.bay;
  }
  function placeSlot(x, y) {
    const elx = document.elementFromPoint(x, y), bay = elx && elx.closest(".bay");
    $$(".bay.drop-target").forEach((b) => b.classList.remove("drop-target"));
    if (!bay) return;
    bay.classList.add("drop-target"); drag.toBay = bay.dataset.bay;
    const u = U(drag.id), rails = bay.querySelector(".rails");
    const after = [...rails.querySelectorAll(".strip:not(.resolved)")].filter((x) => x !== drag.strip).find((x) => { const o = U(x.dataset.id); return cmp(o.askBy || "9999", u.askBy || "9999") > 0 || (o.askBy === u.askBy && o.id > u.id); });
    const hint = rails.querySelector(".empty-hint"); if (hint) hint.style.display = "none";
    if (after) after.before(drag.slot); else { const fold = rails.querySelector(".later"); fold ? fold.before(drag.slot) : rails.appendChild(drag.slot); }
  }
  function autoScroll(x) {
    const w = $("#asks-wrap"), edge = 80;
    cancelAnimationFrame(scrollRaf);
    const v = x < edge ? -(edge - x) / 4 : x > innerWidth - edge - 400 ? (x - (innerWidth - edge - 400)) / 4 : 0;
    if (!v || !w) return;
    const step = () => { w.scrollLeft += v; if (drag) scrollRaf = requestAnimationFrame(step); };
    scrollRaf = requestAnimationFrame(step);
  }
  function finishDrag(d) {
    cancelAnimationFrame(scrollRaf);
    $$(".bay.drop-target").forEach((b) => b.classList.remove("drop-target"));
    const target = d.slot.getBoundingClientRect(), g = d.ghost;
    g.classList.add("settling"); g.style.left = target.left + "px"; g.style.top = target.top + "px"; g.style.transform = "scale(1) rotate(0deg)";
    setTimeout(() => {
      if (d.toBay !== d.fromBay) moveTo(d.id, d.toBay);
      g.remove(); repaint();
      const placed = $(`.strip[data-id="${CSS.escape(d.id)}"]`);
      if (placed) { placed.animate([{ transform: "translateY(-3px)" }, { transform: "translateY(1px)" }, { transform: "translateY(0)" }], { duration: 180 }); placed.focus({ preventScroll: true }); }
      if (d.toBay !== d.fromBay) toast(d.toBay === CRIT ? `${titleOf(d.id)} marked critical.` : `${titleOf(d.id)} now sits with ${$(`.bay[data-bay="${CSS.escape(d.toBay)}"] h2`)?.textContent || d.toBay}. The changes list has the line to record.`);
    }, 260);
  }
  document.addEventListener("click", (e) => {
    if (App.view !== "asks") return;
    const act = e.target.closest(".strip [data-act]");
    if (act) {
      const id = act.closest(".strip").dataset.id, a = act.dataset.act;
      if (a === "flip") { flip(id); return; }
      if (a === "open") { go(id, { quiet: true }); return; }
      if (a === "crit") { if (marks.critical[id]) delete marks.critical[id]; else moveTo(id, CRIT); }
      if (a === "cock") { if (marks.cocked[id]) delete marks.cocked[id]; else marks.cocked[id] = true; }
      if (a === "asked") { if (marks.asked[id]) delete marks.asked[id]; else marks.asked[id] = true; }
      save(); repaint(); return;
    }
    const done = e.target.closest(".strip.resolved");
    if (done) { flip(done.dataset.id); go(done.dataset.id, { quiet: true }); return; }
    const later = e.target.closest("[data-later]");
    if (later) { const k = later.dataset.later; st.expandedLater.has(k) ? st.expandedLater.delete(k) : st.expandedLater.add(k); repaint(); return; }
    const dn = e.target.closest("[data-done]");
    if (dn) { const k = dn.dataset.done; st.expandedDone.has(k) ? st.expandedDone.delete(k) : st.expandedDone.add(k); repaint(); return; }
    const jump = e.target.closest("[data-jump]");
    if (jump) { const b = $(`.bay[data-bay="${CSS.escape(jump.dataset.jump)}"]`); if (b) { $("#asks-wrap").scrollTo({ left: b.offsetLeft - 24, behavior: reducedMotion() ? "auto" : "smooth" }); b.animate([{ boxShadow: `0 0 0 3px ${LIGHT.caution.color}` }, { boxShadow: "0 0 0 0 transparent" }], { duration: 1200 }); } return; }
    const m = e.target.closest("[data-meet]");
    if (m) meet(m.dataset.meet);
  });
  document.addEventListener("keydown", (e) => {
    if (App.view !== "asks") return;
    const strip = document.activeElement && document.activeElement.closest && document.activeElement.closest(".strip");
    if (e.key === "Escape" && st.meeting) { meet(""); return; }
    if (!strip || e.target.tagName === "INPUT") return;
    const id = strip.dataset.id;
    if (e.key === "Enter") { e.preventDefault(); flip(id); return; }
    if (strip.classList.contains("resolved")) return;
    const racks = $$(".bay").map((b) => b.dataset.bay), here = strip.closest(".bay").dataset.bay;
    if (e.key === "[" || e.key === "]") { const i = racks.indexOf(here) + (e.key === "]" ? 1 : -1); if (i < 0 || i >= racks.length) return; moveTo(id, racks[i]); repaint(); $(`.strip[data-id="${CSS.escape(id)}"]`)?.focus(); }
    if (e.key === "!") { if (marks.critical[id]) delete marks.critical[id]; else moveTo(id, CRIT); save(); repaint(); $(`.strip[data-id="${CSS.escape(id)}"]`)?.focus(); }
    if (e.key.toLowerCase() === "k") { if (marks.cocked[id]) delete marks.cocked[id]; else marks.cocked[id] = true; save(); repaint(); $(`.strip[data-id="${CSS.escape(id)}"]`)?.focus(); }
  });
  /* Picked elsewhere: bring its strip into view, unfolded and flipped. */
  function highlight(key) {
    const u = U(key); if (!u) return;
    const rack = marks.critical[key] ? CRIT : rackOf(u);
    if (!$(`.strip[data-id="${CSS.escape(key)}"]`)) { st.expandedLater.add(rack); st.expandedDone.add(rack); if (st.q || st.holdingOnly) { st.q = ""; st.holdingOnly = false; } repaint(); }
    st.flipped.add(key);
    const elx = $(`.strip[data-id="${CSS.escape(key)}"]`);
    if (!elx) return;
    elx.classList.add("flipped");
    const bay = elx.closest(".bay"), w = $("#asks-wrap");
    if (bay && w) w.scrollLeft = Math.max(0, bay.offsetLeft - 24);
    elx.scrollIntoView({ block: "nearest" });
    elx.animate([{ boxShadow: `0 0 0 3px ${Theme.c("focus")}` }, { boxShadow: "0 0 0 0 transparent" }], { duration: 1400 });
  }
  function here() {
    if (App.view !== "asks" || !App.focus || !UNKNOWN[App.focus]) return null;
    return mapAnchors(App.focus);
  }
  return { render, highlight, here, meet, marks: () => marks, trayLines, st };
})();
View("asks", { label: "Who to ask", title: "Open questions, by who holds the answer", render: Asks.render, highlight: Asks.highlight, here: Asks.here,
  count: () => String(D.asks.filter((u) => u.state === "open").length),
  lamp: () => { const l = D.asks.filter((u) => u.state === "open").map((u) => u.light.level).sort((a, b) => rank(b) - rank(a))[0]; return l || null; } });
