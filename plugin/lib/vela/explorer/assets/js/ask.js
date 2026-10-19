/* Ask Claude. The search box answers instantly from the page's own index; when `vela explore --serve` is running
   it can also put the question to Claude, which reads the vault's pages and answers with citations.
   Opened as a file, the page makes no network request at all: it never fetches, and offers the question as a prompt
   to copy into Claude Code instead. Served, it asks /health on its own origin once to learn the helper is there.
   The answer arrives as Server-Sent Events from /ask: start, delta (text), tool (what Claude is reading), then done
   (cost, session) or error (the reason).
   The conversation is a view of its own (#ask, #ask&c=<conversation>) in the main area, where there is room to read;
   a citation opens its item in the right panel, so the sources are read beside the chat. The answer is Markdown,
   rendered by markdown.js with raw HTML shown as text; a [[ID]] or [[path#heading]] in it, or an ID the vault holds
   written bare, becomes a chip on the rendered text, and a [[...]] the vault does not hold is flagged. Conversations
   are kept for the page session and, per vault, in this browser. */
const Ask = (() => {
  const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);
  const STORE = `explorer.ask.${D.vaultId}`, KEEP_CONVERSATIONS = 12, THROTTLE_MS = 90, NEAR_BOTTOM = 48;
  const CITE = /\[\[([^\[\]\n]{1,600})\]\]/g;  // room for a sentence-long |label: a shorter cap left such a link as raw text
  // a vault ID written bare: APP-booking, CAP-001.FR1. Whether the vault holds it is decided by lookup, never by shape;
  // the shape only says where to look. IDs of another shape (a session's 2026-10-06-kickoff) are found by name.
  const ID_SHAPE = /^[A-Z][A-Z0-9]{1,6}-[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*$/;
  const BARE_ID = /(?<![\w./-])([A-Z][A-Z0-9]{1,6}-[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)(?![\w-])/g;
  const NOTHING = /(?!)/g;
  const literal = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const st = { draft: "", mode: "pending", health: null, fetches: 0, convs: [], cur: null, from: null, harder: false, cleared: "", ctrl: null, busy: false, last: null };
  let fetchFn = (...a) => window.fetch(...a);

  /* ---------------------------------------------------------------- is the helper here? */
  /* The page asks only when it was served from this machine; a file or any other address never gets a request.
     `net` and `where` are injectable so #selftest can play the served page without a server. */
  async function detect(net, where) {
    const loc = where || window.location;
    if (loc.protocol === "file:") { st.mode = "file"; flag(); return st.mode; }
    if (!/^https?:$/.test(loc.protocol) || !LOOPBACK.has(loc.hostname)) { st.mode = "static"; flag(); return st.mode; }
    fetchFn = net || fetchFn;
    try {
      st.fetches++;
      const res = await fetchFn("/health");
      const body = res.ok ? await res.json() : null;
      if (!body || body.ok !== true) throw new Error(`/health answered ${res.status}`);
      st.health = body; st.mode = "served";
      $("#q").placeholder = "Search the plan, or press Enter to ask Claude";
    } catch (e) {
      st.mode = "static";
      console.warn("[ask] served from this machine, but the helper did not answer /health:", e.message);
    }
    flag();
    return st.mode;
  }
  const served = () => st.mode === "served";
  /* For #selftest, which plays a served page against a fake fetch and then puts the real state back. */
  const snapshot = () => ({ mode: st.mode, health: st.health, fetches: st.fetches, convs: st.convs.slice(), cur: st.cur, from: st.from });
  function restore(saved) {
    Object.assign(st, saved, { busy: false, draft: "", harder: false, cleared: "", ctrl: null });
    fetchFn = (...a) => window.fetch(...a); flag(); persist();
  }
  /* The sidebar's door and an open Ask view follow what detection found (it finishes after the first draw). */
  function flag() {
    document.documentElement.dataset.ask = st.mode;  // for checks that watch the page from outside
    if (typeof Nav !== "undefined") Nav.refresh();
    if (App.view === "ask" && $("#main")) rerender();
  }

  /* ---------------------------------------------------------------- conversations, kept in this browser per vault */
  const turnOf = (m) => ({ q: m.q, about: m.about, a: m.a, state: m.state, cost: m.cost, model: m.model, modelId: m.modelId, error: m.error, ask: m.ask });
  function persist() {
    const kept = st.convs.filter((c) => c.msgs.length).slice(-KEEP_CONVERSATIONS);
    Settings.write(STORE, JSON.stringify({ cur: st.cur ? st.cur.id : "", convs: kept.map((c) => ({ id: c.id, title: c.title, session: c.session, at: c.at, msgs: c.msgs.map(turnOf) })) }));
  }
  /* What an earlier visit kept. A turn that was still arriving when the page closed says so; it never looks answered. */
  function load() {
    const raw = Settings.read(STORE);
    if (!raw) return;
    try {
      const saved = JSON.parse(raw);
      st.convs = saved.convs.map((c) => ({ id: String(c.id), title: String(c.title || ""), session: c.session || null, at: c.at || 0,
        msgs: c.msgs.map((m) => (m.state === "running" ? { ...m, state: "error", error: "The page was closed before this answer finished." } : m)) }));
      st.cur = st.convs.find((c) => c.id === saved.cur) || null;
    } catch (e) {
      console.warn("[ask] the kept conversations could not be read and are left out:", e.message);
      st.convs = []; st.cur = null;
    }
  }
  const newId = () => "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  function startConversation() { const c = { id: newId(), title: "", session: null, at: Date.now(), msgs: [] }; st.convs.push(c); return c; }
  const conversation = () => st.cur || (st.cur = startConversation());
  const titleOfConversation = (c) => c.title || "New conversation";

  /* ---------------------------------------------------------------- what the reader is looking at */
  /* The view the question is about: while the Ask view is up, the one the reader came from. */
  const aboutView = () => (App.view === "ask" ? (st.from && st.from.view) || "map" : App.view);
  function context() {
    const view = aboutView();
    const c = { view: (viewDef(view) || {}).label || view };
    const pres = typeof Flows !== "undefined" && Flows.presenter() ? Flows.presenter() : null;
    const flowKey = pres ? pres.key : view === "flows" && typeof Flows !== "undefined" ? Flows.st.key : null;
    const cur = pres ? pres.cur : flowKey ? Flows.st.cur : -1;
    const key = App.focus && ent(App.focus) ? App.focus : null;
    if (key) { const e = ent(key); c.item = idOf(key) || e.title; c.item_title = e.title; c.kind = KIND_WORD[e.kind] || e.kind; }
    if (flowKey && FLOW[flowKey]) { c.flow = idOf(flowKey) || titleOf(flowKey); if (cur >= 0) c.step = cur + 1; }
    return c;
  }
  /* "FLO-002 step 2": the most specific thing first. A view alone is not worth a line unless nothing else is picked. */
  function aboutLabel(c) {
    if (c.flow) return c.flow + (c.step ? ` step ${c.step}` : "") + (c.item && c.item !== c.flow ? `, ${c.item}` : "");
    return c.item ? c.item : `the ${c.view} view`;
  }
  const signature = (c) => JSON.stringify(c);
  /* The context to send: what is on screen, unless the reader cleared this exact context. */
  function liveContext() { const c = context(); return st.cleared === signature(c) ? null : c; }

  /* ---------------------------------------------------------------- the question, as a prompt to copy */
  function promptFor(question) {
    const c = liveContext();
    return [question.trim(), c ? `I am looking at ${aboutLabel(c)} in the vault explorer.` : "", D.ask.rules.join(" ")].filter(Boolean).join("\n\n");
  }
  async function copyPrompt(question) {
    const text = promptFor(question);
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(text);
      else {
        const box = h("textarea", { style: { position: "fixed", opacity: "0" } }); box.value = text; document.body.append(box); box.select();
        const done = document.execCommand("copy"); box.remove();
        if (!done) throw new Error("the browser refused the copy command");
      }
      toast("Copied. Paste it into Claude Code in this vault.");
    } catch (e) {
      console.warn("[ask] copy failed:", e.message);
      toast(`Could not copy: ${e.message}`);
    }
  }

  /* ---------------------------------------------------------------- the box's own row in the results */
  /* The row above the search results: Ask Claude, when Claude is attached. A page opened as a file has no Claude to ask, so
     it has no row at all: a row that only copies a prompt put a dead end first in every result list. Null otherwise. */
  function row(q) {
    if (!q.trim() || st.mode === "pending" || !served()) return null;
    return h("div", { class: "r-ask" }, h("button", { class: "ask-btn", type: "button", onmousedown: (ev) => { ev.preventDefault(); send(q); closeSearch(); } },
      h("b", {}, "Ask Claude"), h("span", { class: "ask-q" }, shorten(q, 70)), h("kbd", {}, "Enter"),
      h("span", { class: "ask-m" }, nextModel())));
  }
  function closeSearch() { const q = $("#q"); q.value = ""; q.dispatchEvent(new Event("input")); q.blur(); }
  const enterAsks = (q) => served() && !!q.trim();
  const nextModel = () => (st.harder || (st.health && st.health.model === "sonnet") ? "Sonnet" : "Haiku");

  /* ---------------------------------------------------------------- citations */
  /* What the vault holds, by ID and by path, built once. Lookups are by own key: a name like "constructor" in an
     answer must not find something on Object.prototype. */
  let index = null;
  function held() {
    if (index) return index;
    index = { keys: new Set(Object.keys(E)), ids: new Map(), paths: new Map() };
    for (const e of Object.values(E)) {
      if (!e.path) continue;
      // Claude writes links the way the vault does (Obsidian): "13-epics/EPC-001-x.md", "13-epics/EPC-001-x" or just
      // "EPC-001-x". Each spelling finds the page; a page's own key wins over a file name that two folders share.
      const stem = e.path.replace(/\.md$/, ""), base = stem.split("/").pop();
      for (const name of [e.path, stem, base]) if (!index.paths.has(name)) index.paths.set(name, e.key);
      if (e.id) index.ids.set(e.id, e.key);
    }
    const odd = [...new Set(Object.values(E).map((e) => e.id).filter((id) => id && id.length >= 5 && /-\d/.test(id) && !ID_SHAPE.test(id) && (index.keys.has(id) || index.ids.has(id))))].sort((a, b) => b.length - a.length);
    index.odd = odd.length ? new RegExp(`(?<![\\w./-])(${odd.map(literal).join("|")})(?![\\w-])`, "g") : NOTHING;
    return index;
  }
  function keyFor(target) {
    const ix = held();
    if (ix.keys.has(target)) return target;
    return ix.ids.get(target) || ix.paths.get(target.replace(/^\.\//, "")) || null;
  }
  /* "Scope" or "scope" or a heading slug, to the id the reader scrolls to on that page. */
  function anchorFor(pageKey, heading) {
    const r = D.reader[pageKey];
    if (!r || !heading) return "";
    const want = heading.toLowerCase();
    const t = r.toc.find((x) => x.id === heading || x.text.toLowerCase() === want || x.id === want);
    return t ? t.id : r.html.includes(`id="${heading}"`) ? heading : "";
  }
  /* [[FLO-002]] or [[releases/01.md#Scope]] to a chip that opens it in the panel; null when the vault holds nothing by that name. */
  function chipFor(target, heading, label) {
    const key = keyFor(target);
    if (!key || !ent(key)) return null;
    const chip = refChip(key, label ? h("span", { class: "rid" }, label) : heading ? h("span", { class: "rid" }, "#" + heading) : null);
    if (heading && D.reader[key]) chip.setAttribute("data-ref", "read:" + key + (anchorFor(key, heading) ? "#" + anchorFor(key, heading) : ""));
    chip.setAttribute("tabindex", "0"); chip.setAttribute("role", "link");
    return chip;
  }
  /* [[target#heading|label]], every part but the target optional, as Obsidian and the vault's own pages write it. */
  function cite(ref) {
    const [link, ...rest] = ref.split("|");
    const label = rest.join("|").trim();
    const [target, heading] = link.split("#").map((x) => x.trim());
    // A label longer than a name ("It stays the news app, and gains…") reads as prose, so it is a link in the sentence
    // that opens like a chip; a short one stays a chip.
    if (label.length > 40) {
      const chip = chipFor(target, heading);
      if (chip) return h("a", { class: "ask-prose-link", "data-ref": chip.getAttribute("data-ref"), tabindex: "0", role: "link", title: chip.textContent }, label);
    }
    return chipFor(target, heading, label) || h("span", { class: "ref-chip ask-unknown", title: "Claude cited this, but the vault holds no such ID or page" }, ref, h("span", { class: "ask-flag" }, "not in this vault"));
  }
  /* A bare ID: the longest leading part the vault holds ("CAP-001.FR1.Note" finds CAP-001.FR1). Unknown ones stay text:
     a bare "UTF-8" is not a broken citation. */
  function bare(id) {
    for (let at = id; at; at = at.includes(".") ? at.slice(0, at.lastIndexOf(".")) : "") {
      const chip = chipFor(at);
      if (chip) return { chip, length: at.length };
    }
    return null;
  }
  /* Split a text node into text and chips. Only text is read: nothing in an answer is ever parsed as markup here. */
  function chipsIn(text) {
    const pieces = [];
    const found = [...text.matchAll(CITE)].map((m) => ({ at: m.index, length: m[0].length, chip: cite(m[1]) }));
    for (const m of [...text.matchAll(BARE_ID), ...text.matchAll(held().odd)]) {
      if (found.some((f) => m.index < f.at + f.length && m.index + m[1].length > f.at)) continue;  // inside a [[...]] already
      const hit = bare(m[1]);
      if (hit) found.push({ at: m.index, length: hit.length, chip: hit.chip });
    }
    found.sort((x, y) => x.at - y.at);
    let last = 0;
    for (const f of found) { pieces.push(text.slice(last, f.at), f.chip); last = f.at + f.length; }
    pieces.push(text.slice(last));
    return found.length ? pieces : null;
  }
  /* Citation linking on the rendered answer: its text nodes, outside links and code blocks. An inline `code` that is
     only a reference (`CAP-001.FR1`, `[[FLO-002]]`) becomes the chip, since models quote IDs that way. */
  function linkCitations(root) {
    for (const code of [...root.querySelectorAll("code")]) {
      if (code.closest("pre")) continue;
      const pieces = chipsIn(code.textContent.trim());
      if (pieces && pieces.every((p, i) => (i % 2 ? true : p === ""))) code.replaceWith(pieces[1]);
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.parentElement && n.parentElement.closest("a,pre,code,.ref-chip") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const pieces = chipsIn(node.nodeValue);
      if (pieces) node.replaceWith(...pieces.filter((p) => p !== ""));
    }
    return root;
  }
  const rendered = (md, growing) => linkCitations(Markdown.render(md, growing));

  /* ---------------------------------------------------------------- asking */
  function modelKey() { return st.harder ? "sonnet" : null; }
  /* st.last is the question in flight, so a check can wait for it. */
  function send(question, opts) { st.last = ask(question, opts || {}); return st.last; }
  async function ask(question, opts) {
    question = (question || "").trim();
    if (!served() || !question) return;
    if (st.busy) { toast("Claude is still answering. Stop it first, or wait."); return; }
    const max = st.health.maxQuestion || 2000;
    const model = opts.model !== undefined ? opts.model : modelKey();
    const ctx = opts.noContext ? null : liveContext();
    const conv = conversation();
    const msg = { q: question, about: ctx ? aboutLabel(ctx) : "", a: "", state: "running", tool: "", cost: null, model: model || st.health.model, modelId: "", error: "", ask: model };
    if (opts.fresh) conv.session = null;
    if (!conv.title) conv.title = shorten(question, 60);
    conv.msgs.push(msg); st.busy = true; st.ctrl = new AbortController();
    show(msg);
    if (question.length > max) { fail(msg, `The question is ${question.length} characters; the limit is ${max}.`); return; }
    try {
      st.fetches++;
      const res = await fetchFn("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, signal: st.ctrl.signal,
        body: JSON.stringify({ question, context: ctx || {}, conversation_id: conv.session || undefined, model: model || undefined }) });
      if (!res.ok) { const body = await res.json().catch(() => ({})); fail(msg, `The local Claude connection turned the question down (${res.status}): ${body.error || res.statusText}`); return; }
      await readEvents(res, msg, conv);
      if (msg.state === "running") fail(msg, "The answer stopped before it finished. The local Claude connection may have stopped; check the terminal where you started it.");
    } catch (e) {
      if (e.name === "AbortError") { msg.state = "stopped"; done(msg); }
      else fail(msg, `The question did not complete: ${e.message}`);
    }
  }
  async function readEvents(res, msg, conv) {
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done: end } = await reader.read();
      buf += dec.decode(value || new Uint8Array(), { stream: !end });
      let at;
      while ((at = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, at); buf = buf.slice(at + 2);
        if (chunk.startsWith("data: ")) apply(msg, conv, JSON.parse(chunk.slice(6)));
      }
      if (end) return;
    }
  }
  function apply(msg, conv, ev) {
    if (ev.type === "start") msg.modelId = ev.model;
    else if (ev.type === "delta") { msg.a += ev.text; msg.tool = ""; }
    else if (ev.type === "tool") msg.tool = `${ev.name} ${ev.target}`.trim();
    else if (ev.type === "error") { fail(msg, ev.message); return; }
    else if (ev.type === "done") {
      msg.cost = ev.cost; msg.modelId = ev.model || msg.modelId; msg.state = "done"; msg.tool = "";
      if (ev.session_id) conv.session = ev.session_id;
      done(msg); return;
    }
    paint(msg);
  }
  function fail(msg, reason) { msg.state = "error"; msg.error = reason; msg.tool = ""; done(msg); }
  function done(msg) { st.busy = false; st.ctrl = null; paint(msg, true); persist(); }
  function stop() { if (st.ctrl) st.ctrl.abort(); }

  /* ---------------------------------------------------------------- the conversation, in the main area */
  const modelWord = (msg) => (/sonnet/.test(msg.modelId || msg.model) ? "Sonnet" : "Haiku");
  function fillAnswer(msg) {
    const live = msg.state === "running", box = msg.answerEl;
    box.className = "ask-a md" + (msg.state === "error" ? " bad" : "");
    box.setAttribute("aria-busy", String(live));
    const kids = [];
    if (msg.a) kids.push(rendered(msg.a, live));
    else if (live) kids.push(h("span", { class: "ask-wait" }, "Reading the plan"));
    if (live && msg.tool) kids.push(h("div", { class: "ask-tool" }, shorten(msg.tool, 80)));
    if (msg.state === "error") kids.push(h("div", { class: "ask-error", role: "alert" }, h("b", {}, "No answer. "), msg.error));
    if (msg.state === "stopped") kids.push(h("div", { class: "ask-tool" }, "Stopped."));
    box.replaceChildren(...kids);
  }
  function fillMeta(msg) {
    msg.metaState = msg.state;
    if (msg.state === "running") { msg.metaEl.replaceChildren(h("button", { class: "btn tiny", type: "button", onclick: stop }, "Stop")); return; }
    const bits = [modelWord(msg)];
    if (typeof msg.cost === "number") bits.push(`$${msg.cost.toFixed(4)}`);
    const harder = msg.state !== "error" && modelWord(msg) !== "Sonnet" && served()
      ? h("button", { class: "btn tiny", type: "button", title: "Ask this question again on Sonnet, in a fresh session", onclick: () => send(msg.q, { model: "sonnet", fresh: true }) }, "Think harder") : null;
    const again = msg.state === "error" ? h("button", { class: "btn tiny", type: "button", onclick: () => send(msg.q, { fresh: !conversation().session }) }, "Try again") : null;
    msg.metaEl.replaceChildren(...[h("span", {}, bits.join(" · ")), harder, again].filter(Boolean));  // replaceChildren would write a null as the word "null"
  }
  /* The turn's three parts are made once and then filled, so the Stop button under a streaming answer is the same
     element from the first word to the last and a click on it lands. */
  function turn(msg) {
    msg.answerEl = h("div", { "aria-live": "polite" }); msg.metaEl = h("div", { class: "ask-meta" });
    msg.el = h("div", { class: "ask-turn" }, h("div", { class: "ask-you" }, msg.q, msg.about ? h("span", { class: "ask-about-tag" }, msg.about) : null), msg.answerEl, msg.metaEl);
    fillAnswer(msg); fillMeta(msg);
    return msg.el;
  }
  /* Update a turn. While it streams the redraw is throttled: the whole Markdown is parsed again each time, so a table or
     list that is half there settles into shape instead of flickering on every token. */
  function paint(msg, now) {
    if (!msg.el || !msg.el.isConnected) return;  // the reader is elsewhere; the turn is drawn afresh when they return
    if (!now && msg.state === "running") { if (!msg.timer) msg.timer = setTimeout(() => { msg.timer = 0; paint(msg, true); }, THROTTLE_MS); return; }
    clearTimeout(msg.timer); msg.timer = 0;
    const log = msg.el.closest(".ask-log");
    const follow = !log || log.scrollHeight - log.scrollTop - log.clientHeight < NEAR_BOTTOM;
    fillAnswer(msg);
    if (msg.metaState !== msg.state) fillMeta(msg);
    if (log && follow) log.scrollTop = log.scrollHeight;
  }

  const crumbLabel = () => Nav.whereLabel(st.from);
  function aboutLine() {
    const c = liveContext();
    if (!c) return h("div", { class: "ask-about off" }, "No context is sent with the next question.");
    return h("div", { class: "ask-about" }, "Asking about: ", h("b", {}, aboutLabel(c)),
      h("button", { class: "ask-clear", type: "button", "aria-label": "Do not send what I am looking at", title: "Do not send what I am looking at", onclick: () => { st.cleared = signature(c); refreshAbout(); } }, "×"));
  }
  function refreshAbout() { const old = $(".ask-about"); if (old) old.replaceWith(aboutLine()); }
  function composer() {
    const conv = st.cur;
    const live = served();
    const box = h("textarea", { class: "ask-input", rows: "1", "aria-label": live ? "Question" : "Question, to copy as a prompt",
      placeholder: live ? (conv && conv.msgs.length ? "Ask a follow-up" : "Ask about the plan in plain words") : "Write the question, then Enter copies it as a prompt" });
    box.value = st.draft;
    const grow = () => { box.style.height = "auto"; box.style.height = Math.min(box.scrollHeight + 2, Math.round(innerHeight * 0.24)) + "px"; };  // the box follows what is typed, up to a quarter of the window
    box.addEventListener("input", () => { st.draft = box.value; grow(); });
    const submit = () => { const q = box.value; if (!q.trim()) return; box.value = st.draft = ""; grow(); if (live) send(q); else copyPrompt(q); };
    box.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); submit(); }
    });
    const harder = live ? h("button", { class: "btn tiny think", type: "button", "aria-pressed": String(st.harder), title: "Use the stronger model (Sonnet) for the next questions: slower and costs more, but more careful",
      onclick: (ev) => { st.harder = !st.harder; ev.currentTarget.setAttribute("aria-pressed", String(st.harder)); $(".ask-next").textContent = nextModel(); } }, "Think harder") : null;
    const go_ = h("button", { class: "btn tiny primary", type: "button", onclick: submit }, live ? "Ask" : "Copy as a prompt");
    return h("div", { class: "ask-compose" }, h("div", { class: "ask-col" }, aboutLine(), box,
      h("div", { class: "ask-actions" }, harder, live ? h("span", { class: "ask-next muted", title: "The model for the next question" }, nextModel()) : null,
      h("span", { class: "spacer" }), h("span", { class: "ask-keys" }, live ? "Enter sends \u00b7 Shift+Enter adds a line \u00b7 Esc leaves" : "Enter copies \u00b7 Shift+Enter adds a line \u00b7 Esc leaves"), go_)));
  }
  function picker() {
    const kept = st.convs.filter((c) => c.msgs.length);
    if (kept.length < 2) return null;
    const sel = h("select", { class: "ask-pick", "aria-label": "Switch conversation" }, kept.map((c) => h("option", { value: c.id }, shorten(titleOfConversation(c), 48))));
    sel.value = st.cur ? st.cur.id : "";
    sel.addEventListener("change", () => select(sel.value));
    return sel;
  }
  function emptyLog() {
    if (served()) return h("div", { class: "ask-empty" }, h("b", {}, "Ask about the plan in plain words."), " Claude reads its pages and answers with citations. Click a citation to read the source in the panel beside this conversation.");
    return emptyState("Claude isn't connected to this page.", st.mode === "file" ? "Open it with /vela:explore to ask questions." : st.mode === "pending" ? "Looking for Claude on this computer." : "Claude on this computer didn't answer. Open the page again with /vela:explore.",
      "/vela:explore", "ask-empty");
  }
  function renderView(main) {
    const conv = st.cur;
    const crumbs = h("nav", { class: "ask-crumbs", "aria-label": "Where you came from" },
      h("button", { class: "ask-back", type: "button", title: "Back to where you were (Esc)", onclick: back }, "‹ " + crumbLabel()), h("span", { class: "sep" }, "›"), h("span", {}, "Ask Claude"));
    main.append(h("div", { class: "view-head ask-head" }, h("div", {}, crumbs, h("h1", {}, conv ? titleOfConversation(conv) : "New conversation")), h("div", { class: "spacer" }),
      h("div", { class: "page-actions" }, picker(),
        h("button", { class: "btn", type: "button", disabled: conv && conv.msgs.length ? null : true, onclick: newConversation, title: "New conversation" }, h("span", {}, "New", h("span", { class: "ask-more" }, " conversation"))))));
    const log = h("div", { class: "ask-log", tabindex: "-1" });
    const col = h("div", { class: "ask-col" });
    if (conv && conv.msgs.length) for (const msg of conv.msgs) col.append(turn(msg));
    else col.append(emptyLog());
    log.append(col);
    const view = h("div", { class: "ask-view" }, log, composer());
    view.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !ev.defaultPrevented) { ev.preventDefault(); back(); }
      else if (ev.key === "Enter" && ev.target.closest("[data-ref]")) ev.target.closest("[data-ref]").click();
    });
    // a citation opens in the panel (the page's own handler); what the reader is now looking at is what the next question is about
    log.addEventListener("click", (ev) => { if (ev.target.closest("[data-ref]")) setTimeout(refreshAbout, 0); });
    main.append(view);
    queueMicrotask(() => { log.scrollTop = log.scrollHeight; });
  }

  /* ---------------------------------------------------------------- going in and out */
  function enter(focusBox) {
    App.section = "ask"; App.root = "lights";
    showView("ask");
    Panel.render();
    if (focusBox !== false) { const box = $(".ask-input"); if (box) box.focus(); }
  }
  /* Show the conversation, from the search box, the sidebar or a button. Where the reader was is kept for the way back. */
  function open() { if (App.view !== "ask") st.from = Nav.where(); enter(); }
  /* A deep link: #ask opens the last conversation, #ask&c=<id> that one. */
  function boot(id) {
    if (id && !st.convs.some((c) => c.id === id)) console.warn(`[ask] #ask&c=${id}: this browser keeps no such conversation; showing a new one`);
    if (id) st.cur = st.convs.find((c) => c.id === id) || null;
    st.from = null;
    enter();
  }
  function show(msg) {
    if (App.view !== "ask") { open(); return; }
    const col = $(".ask-col"), log = $(".ask-log");
    Nav.syncHash();
    if (!col || !log || st.cur.msgs.length === 1) { rerender(); const box = $(".ask-input"); if (box) box.focus(); return; }  // a first question names the conversation and may add the switcher
    col.append(turn(msg));
    log.scrollTop = log.scrollHeight;
  }
  function back() { const where = st.from; st.from = null; Nav.back(where); }
  function select(id) { st.cur = st.convs.find((c) => c.id === id) || null; Nav.syncHash(); rerender(); persist(); }
  function newConversation() {
    if (st.busy) { stop(); toast("Stopped the answer in progress."); }
    st.cur = null; Nav.syncHash(); rerender(); persist();
    const box = $(".ask-input"); if (box) box.focus();
  }
  const hash = () => "ask" + (st.cur && st.cur.msgs.length ? "&c=" + encodeURIComponent(st.cur.id) : "");

  View("ask", { label: "Ask Claude", render: renderView });
  load();

  return { detect, snapshot, restore, served, row, enterAsks, ask: send, copyPrompt, promptFor, open, boot, back, hash, count: () => st.convs.filter((c) => c.msgs.length).length,
    linkCitations, rendered, cite, context, aboutLabel, st };
})();
