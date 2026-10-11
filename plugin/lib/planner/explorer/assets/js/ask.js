/* Ask Claude. The search box answers instantly from the page's own index; when `planner explore --serve` is running
   it can also put the question to Claude, which reads the vault's pages and answers with citations.
   Opened as a file, the page makes no network request at all: it never fetches, and offers the question as a prompt
   to copy into Claude Code instead. Served, it asks /health on its own origin once to learn the helper is there.
   The answer arrives as Server-Sent Events from /ask: start, delta (text), tool (what Claude is reading), then done
   (cost, session) or error (the reason). Its text is rendered as text, never as HTML; a [[ID]] or [[path#heading]]
   in it becomes a chip when the vault holds it and a flagged plain mark when it does not. */
const Ask = (() => {
  const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);
  const CITE = /\[\[([^\[\]\n]{1,200})\]\]/g;
  const st = { draft: "", mode: "pending", health: null, fetches: 0, session: null, msgs: [], showing: false, harder: false, cleared: "", ctrl: null, busy: false };
  const note = (text) => h("div", { class: "r-more ask-note" }, text);
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
      $("#q").placeholder = "Search the vault, or press Enter to ask Claude";
    } catch (e) {
      st.mode = "static";
      console.warn("[ask] served from this machine, but the helper did not answer /health:", e.message);
    }
    flag();
    return st.mode;
  }
  const served = () => st.mode === "served";
  /* For #selftest, which plays a served page against a fake fetch and then puts the real state back. */
  const snapshot = () => ({ mode: st.mode, health: st.health, fetches: st.fetches });
  function restore(saved) {
    Object.assign(st, saved, { session: null, msgs: [], showing: false, busy: false, draft: "", harder: false, cleared: "" });
    fetchFn = (...a) => window.fetch(...a); syncButton(); flag();
  }
  const flag = () => { document.documentElement.dataset.ask = st.mode; };  // for checks that watch the page from outside

  /* ---------------------------------------------------------------- what the reader is looking at */
  function context() {
    const c = { view: (viewDef(App.view) || {}).label || App.view };
    const pres = typeof Flows !== "undefined" && Flows.presenter() ? Flows.presenter() : null;
    const flowKey = pres ? pres.key : App.view === "flows" && typeof Flows !== "undefined" ? Flows.st.key : null;
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
  /* The row above the search results: Ask when served, Copy as a prompt when not. Null for an empty box. */
  function row(q) {
    if (!q.trim() || st.mode === "pending") return null;
    if (served()) {
      return h("div", { class: "r-ask" }, h("button", { class: "ask-btn", type: "button", onmousedown: (ev) => { ev.preventDefault(); send(q); closeSearch(); } },
        h("b", {}, "Ask Claude"), h("span", { class: "ask-q" }, shorten(q, 70)), h("kbd", {}, "Enter"),
        h("span", { class: "ask-m" }, st.harder ? "Sonnet" : st.health.model === "sonnet" ? "Sonnet" : "Haiku")));
    }
    return h("div", { class: "r-ask" }, h("button", { class: "ask-btn", type: "button", onmousedown: (ev) => { ev.preventDefault(); copyPrompt(q); } },
      h("b", {}, "Copy as a Claude Code prompt"), h("span", { class: "ask-q" }, shorten(q, 60))),
    h("div", { class: "r-more" }, st.mode === "file" ? "Search only on a file. Run /planner:explore to ask Claude from this page." : "Search only: the helper did not answer. Run /planner:explore to ask Claude from this page."));
  }
  function closeSearch() { const q = $("#q"); q.value = ""; q.dispatchEvent(new Event("input")); q.blur(); }
  const enterAsks = (q) => served() && !!q.trim();

  /* ---------------------------------------------------------------- citations */
  /* [[FLO-002]] or [[releases/01.md#Scope]] to a chip that opens it here; anything the vault does not hold stays plain and flagged. */
  function cite(ref) {
    const [target, heading] = ref.split("#").map((x) => x.trim());
    let key = keyForId(target);
    if (!ent(key)) { const p = target.replace(/^\.\//, ""); key = (Object.values(E).find((x) => x.path === p) || {}).key; }
    if (!key || !ent(key)) {
      return h("span", { class: "ref-chip ask-unknown", title: "Claude cited this, but the vault holds no such ID or page" }, ref, h("span", { class: "ask-flag" }, "not in this vault"));
    }
    const chip = refChip(key, heading ? h("span", { class: "rid" }, "#" + heading) : null);
    chip.setAttribute("data-reveal", ""); chip.setAttribute("tabindex", "0"); chip.setAttribute("role", "link");
    return chip;
  }
  function cited(text) {
    const frag = document.createDocumentFragment();
    let last = 0;
    for (const m of text.matchAll(CITE)) { frag.append(text.slice(last, m.index), cite(m[1])); last = m.index + m[0].length; }
    frag.append(text.slice(last));
    return frag;
  }

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
    const msg = { q: question, about: ctx ? aboutLabel(ctx) : "", a: "", state: "running", tool: "", cost: null, model: model || st.health.model, modelId: "", error: "", ask: model };
    if (opts.fresh) st.session = null;
    st.msgs.push(msg); st.busy = true; st.ctrl = new AbortController();
    show();
    if (question.length > max) { fail(msg, `The question is ${question.length} characters; the limit is ${max}.`); return; }
    try {
      st.fetches++;
      const res = await fetchFn("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, signal: st.ctrl.signal,
        body: JSON.stringify({ question, context: ctx || {}, conversation_id: st.session || undefined, model: model || undefined }) });
      if (!res.ok) { const body = await res.json().catch(() => ({})); fail(msg, `The helper refused the question (${res.status}): ${body.error || res.statusText}`); return; }
      await readEvents(res, msg);
      if (msg.state === "running") fail(msg, "The answer stream ended without a result. The helper may have stopped; check the terminal running planner explore.");
    } catch (e) {
      if (e.name === "AbortError") { msg.state = "stopped"; done(msg); }
      else fail(msg, `The question did not complete: ${e.message}`);
    }
  }
  async function readEvents(res, msg) {
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done: end } = await reader.read();
      buf += dec.decode(value || new Uint8Array(), { stream: !end });
      let at;
      while ((at = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, at); buf = buf.slice(at + 2);
        if (chunk.startsWith("data: ")) apply(msg, JSON.parse(chunk.slice(6)));
      }
      if (end) return;
    }
  }
  function apply(msg, ev) {
    if (ev.type === "start") msg.modelId = ev.model;
    else if (ev.type === "delta") { msg.a += ev.text; msg.tool = ""; }
    else if (ev.type === "tool") msg.tool = `${ev.name} ${ev.target}`.trim();
    else if (ev.type === "error") { fail(msg, ev.message); return; }
    else if (ev.type === "done") {
      msg.cost = ev.cost; msg.modelId = ev.model || msg.modelId; msg.state = "done"; msg.tool = "";
      if (ev.session_id) st.session = ev.session_id;
      done(msg); return;
    }
    paint(msg);
  }
  function fail(msg, reason) { msg.state = "error"; msg.error = reason; msg.tool = ""; done(msg); }
  function done(msg) { st.busy = false; st.ctrl = null; paint(msg); syncButton(); }
  function stop() { if (st.ctrl) st.ctrl.abort(); }
  function newConversation() { stop(); st.msgs = []; st.session = null; st.busy = false; syncButton(); Panel.render(); }

  /* ---------------------------------------------------------------- the conversation in the panel */
  const modelWord = (msg) => (/sonnet/.test(msg.modelId || msg.model) ? "Sonnet" : "Haiku");
  function answerEl(msg) {
    const live = msg.state === "running";
    const box = h("div", { class: "ask-a" + (msg.state === "error" ? " bad" : ""), "aria-live": "polite", "aria-busy": String(live) });
    if (msg.a) box.append(cited(msg.a));
    else if (live) box.append(h("span", { class: "ask-wait" }, "Reading the vault"));
    if (live && msg.tool) box.append(h("div", { class: "ask-tool" }, shorten(msg.tool, 80)));
    if (msg.state === "error") box.append(h("div", { class: "ask-error", role: "alert" }, h("b", {}, "No answer. "), msg.error));
    if (msg.state === "stopped") box.append(h("div", { class: "ask-tool" }, "Stopped."));
    return box;
  }
  function metaEl(msg) {
    if (msg.state === "running") return h("div", { class: "ask-meta" }, h("button", { class: "btn tiny", type: "button", onclick: stop }, "Stop"));
    const bits = [modelWord(msg)];
    if (typeof msg.cost === "number") bits.push(`$${msg.cost.toFixed(4)}`);
    const harder = msg.state !== "error" && modelWord(msg) !== "Sonnet" && served()
      ? h("button", { class: "btn tiny", type: "button", title: "Ask this question again on Sonnet, in a fresh session", onclick: () => send(msg.q, { model: "sonnet", fresh: true }) }, "Think harder") : null;
    const again = msg.state === "error" ? h("button", { class: "btn tiny", type: "button", onclick: () => send(msg.q, { fresh: !st.session }) }, "Try again") : null;
    return h("div", { class: "ask-meta" }, h("span", {}, bits.join(" · ")), harder, again);
  }
  function paint(msg) {
    if (!msg.el) return;
    msg.el.replaceChildren(...entry(msg).children);
    const log = $(".ask-log");
    if (log) log.scrollTop = log.scrollHeight;
  }
  function entry(msg) {
    return h("div", {}, h("div", { class: "ask-you" }, msg.q, msg.about ? h("span", { class: "ask-about-tag" }, msg.about) : null), answerEl(msg), metaEl(msg));
  }
  function aboutLine() {
    const c = liveContext();
    if (!c) return h("div", { class: "ask-about off" }, "No context is sent with the next question.");
    return h("div", { class: "ask-about" }, "Asking about: ", h("b", {}, aboutLabel(c)),
      h("button", { class: "ask-clear", type: "button", "aria-label": "Do not send what I am looking at", title: "Do not send what I am looking at", onclick: () => { st.cleared = signature(c); Panel.render(); } }, "×"));
  }
  function composer() {
    const box = h("textarea", { class: "ask-input", rows: "2", "aria-label": "Follow-up question", placeholder: st.msgs.length ? "Ask a follow-up. Enter sends, Shift+Enter adds a line." : "Ask the vault. Enter sends, Shift+Enter adds a line." });
    box.value = st.draft;
    box.addEventListener("input", () => { st.draft = box.value; });
    const submit = () => { const q = box.value; box.value = st.draft = ""; send(q); };
    box.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); submit(); }
    });
    const harder = h("button", { class: "btn tiny think", type: "button", "aria-pressed": String(st.harder), title: "Send the next questions to Sonnet: slower, dearer, more careful",
      onclick: (ev) => { st.harder = !st.harder; ev.currentTarget.setAttribute("aria-pressed", String(st.harder)); } }, "Think harder");
    const go_ = h("button", { class: "btn tiny primary", type: "button", onclick: submit }, "Ask");
    return h("div", { class: "ask-compose" }, aboutLine(), box, h("div", { class: "ask-actions" }, harder, h("span", { class: "spacer" }), go_));
  }
  /* The panel's content while the conversation is showing. */
  function panel() {
    const log = h("div", { class: "ask-log", tabindex: "-1" });
    for (const msg of st.msgs) { msg.el = h("div", { class: "ask-turn" }); msg.el.append(...entry(msg).children); log.append(msg.el); }
    const head = h("div", { class: "p-head" }, h("div", { class: "kind" }, "Ask Claude"), h("h2", {}, "Conversation"),
      h("div", { class: "p-actions" }, h("button", { class: "btn tiny", type: "button", onclick: close }, "Back to details"),
        h("button", { class: "btn tiny quiet", type: "button", onclick: newConversation }, "New conversation")));
    const body = h("div", { class: "ask-panel" }, head, st.msgs.length ? log : note("Type a question in the search box and press Enter, or ask here."), composer());
    body.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); close(); }
      else if (ev.key === "Enter" && ev.target.closest("[data-ref]")) ev.target.closest("[data-ref]").click();
    });
    // a citation opens in the explorer, and the panel then shows that item; the conversation waits behind the panel's button
    body.addEventListener("click", (ev) => { if (ev.target.closest("[data-ref]")) leave(); });
    queueMicrotask(() => { const l = $(".ask-log"); if (l) l.scrollTop = l.scrollHeight; });
    return body;
  }
  function show() { st.showing = true; PanelSize.reveal(); syncButton(); Panel.render(); const i = $(".ask-input"); if (i) i.focus(); }
  function leave() { st.showing = false; syncButton(); }
  function close() { leave(); Panel.render(); }
  function syncButton() {
    const b = $("#panel-ask");
    b.hidden = !st.msgs.length;
    b.setAttribute("aria-pressed", String(st.showing));
    b.querySelector("span").textContent = st.busy ? "Answering…" : "Conversation";
  }
  $("#panel-ask").addEventListener("click", () => (st.showing ? close() : show()));

  return { detect, snapshot, restore, served, row, enterAsks, ask: send, copyPrompt, promptFor, panel, showing: () => st.showing, close, leave, cited, cite, context, aboutLabel, st };
})();
