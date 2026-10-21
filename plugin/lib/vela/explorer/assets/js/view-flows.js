/* Flows, played. Each step's messages travel as pulses between the apps' lanes, in the map's left-to-right order;
   open questions from the record sit at the step they hold, breathing in their lamp color. One player drives the
   view and one drives present mode, both on FlowKit's renderer. Save clip records the same frames as MP4 or WebM in
   the browser. Heuristics are labeled where they show: an inferred direction says so under its arrow. */
const Flows = (() => {
  /* A contract's state and light in one sentence: "Not decided yet, and it is waiting". */
  const LIGHT_SAYS = { warning: "it's overdue", caution: "it's waiting", pending: "it's waiting on the owner's approval", unexamined: "nobody has reviewed it yet",
    override: "a check was skipped on it", dark: "nothing is blocking it" };
  const contractSays = (id) => `${CONTRACT[id].state ? stateWord(CONTRACT[id].state) : "Nobody has given it a state yet"}, and ${LIGHT_SAYS[levelOf(id)] || LIGHT[levelOf(id)].word.toLowerCase()}`;
  const TRAVEL = 0.8;
  const st = { key: D.flows.length ? D.flows[0].key : null, cur: -1, speed: 1 };
  let player = null, presenter = null, recording = false;

  function makePlayer(canvas, opts) {
    const ctx = canvas.getContext("2d");
    const p = { canvas, ctx, cur: opts.cur ?? -1, entered: performance.now(), playing: false, hits: [], w: 0, h: 0, present: !!opts.present, key: opts.key };
    const flow = () => FlowKit.flowOf(p.key);
    const size = () => {
      const r = canvas.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
      canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); p.w = r.width; p.h = r.height;
    };
    new ResizeObserver(size).observe(canvas);
    size();
    p.frame = (now) => {
      if (!canvas.isConnected) return;
      if (p.w && p.h) {
        const f = flow(), k = clamp(p.w / (p.present ? 960 : 1040), 0.8, p.present ? 1.6 : 1.2);
        // The host (the stage, or present mode's scroller) is the room the diagram has; a flow whose words need more makes the canvas taller and the host scrolls.
        const room = opts.host ? opts.host.clientHeight : p.h, G = FlowKit.layout(f, { x: 0, y: 6, w: p.w - 8, h: room - 6, s: k, fit: p.present });
        const want = Math.ceil(G.h + 6) > room ? Math.ceil(G.h + 6) + "px" : "";
        if (canvas.dataset.grown !== want) { canvas.dataset.grown = want; canvas.style.height = want; }
        ctx.clearRect(0, 0, p.w, p.h);
        const tau = ((now - p.entered) / 1000) * st.speed, cur = p.cur === -1 ? f.steps.length : p.cur;
        const pick = App.trail[App.trail.length - 1] || null;  // what the panel shows: back and Escape move it, so the glow follows it
        const hl = p.present || !pick ? null : litBy(pick);
        // Plain: every message is drawn where it lands, nothing travels; the step timing still drives Play.
        p.hits = FlowKit.drawScene(ctx, G, { cur, tau: FX.on ? tau : 99, clock: now / 1000, D: TRAVEL, highlight: hl });
        if (p.playing && p.cur >= 0) {
          const step = f.steps[p.cur];
          if (tau > FlowKit.travelTime(step, TRAVEL) + (p.present ? 3.0 : 3.4)) {
            if (p.cur < f.steps.length - 1) p.go(p.cur + 1); else p.pause();
          }
        }
      }
      requestAnimationFrame(p.frame);
    };
    p.go = (i) => {
      const n = flow().steps.length;
      p.cur = clamp(i, -1, n - 1);
      p.entered = performance.now();
      opts.onStep && opts.onStep(p);
    };
    p.play = () => { p.playing = true; if (p.cur === -1 || p.cur === flow().steps.length - 1) p.go(0); else p.go(p.cur); opts.onPlay && opts.onPlay(p); };
    p.pause = () => { p.playing = false; opts.onPlay && opts.onPlay(p); };
    p.toggle = () => (p.playing ? p.pause() : p.play());
    const hitAt = (e) => {
      const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      const order = { unknown: 0, ref: 1, contract: 2, step: 3, row: 4, lane: 5 };
      return p.hits.filter((t) => x >= t.x && x <= t.x + t.w && y >= t.y && y <= t.y + t.h).sort((a, b) => order[a.type] - order[b.type])[0];
    };
    canvas.addEventListener("mousemove", (e) => {
      const t = hitAt(e);
      canvas.style.cursor = t ? "pointer" : "default";
      if (t && t.type === "unknown") { const q = ASK[t.id]; showTip(e, `<b>${esc(E[t.id] ? E[t.id].title : t.id)}</b>${esc(q.state === "open" ? q.question : "Answered: " + (q.outcome || q.question))}`); }
      else if (t && t.type === "lane") showTip(e, `<b>${esc(FlowKit.laneName(t.id))}</b>${FlowKit.touchedLanes(FlowKit.flowOf(p.key)).has(t.id) ? "in this flow" : "not in this flow"}`);
      else if (t && t.type === "contract") showTip(e, `<b>${esc(CONTRACT[t.id].title)}</b>${esc(contractSays(t.id))}`);
      else hideTip();
    });
    canvas.addEventListener("mouseleave", hideTip);
    canvas.addEventListener("click", (e) => {
      const t = hitAt(e);
      if (!t) { if (!p.present) DetailsPanel.clear(); return; }  // empty space goes back to the flow's summary
      if (t.type === "unknown" || t.type === "contract") { if (!p.present) DetailsPanel.show(t.id, { reset: true }); else opts.onPick && opts.onPick(t); }
      else if (t.type === "ref") { p.key = t.id; p.go(-1); opts.onFlow && opts.onFlow(p); }
      else if (t.type === "lane") { if (!p.present) DetailsPanel.show(t.id, { reset: true }); }
      else if (t.si !== undefined) { p.pause(); p.go(t.si); if (!p.present) DetailsPanel.show(PlanDetails.stepKey(p.key, t.si), { reset: true }); }
    });
    requestAnimationFrame(p.frame);
    return p;
  }

  /* ------------------------------------------------------------ the view */
  function render(main) {
    if (!D.flows.length) { main.append(emptyState("No flows yet.", "Once the plan writes a flow with its steps, it plays here, step by step across the apps.", "/vela:boundary")); return; }
    const f = FlowKit.flowOf(st.key);
    const picker = FlowPicker.make({ current: () => st.key, onPick: (key) => select(key, -1) });
    const present_ = h("button", { class: "dmenu-btn primary", id: "present-btn", type: "button", onclick: () => present(st.key, Math.max(0, st.cur)), title: "Present full screen (P)" }, svgIcon("present"), "Present");
    const tag = Releases.tracerTag(st.key), pl = Releases.tracerPlace(st.key);
    // the Show picker swaps a branch's steps into this same diagram (branches.js); the step numbers change, so the play head starts over
    const branch = Branches.picker(st.key, () => { st.cur = -1; rerender(); });
    const stage = h("div", { class: "stage" });
    const canvas = h("canvas", { class: "stage-canvas", role: "img", "aria-label": `Sequence of ${f.title}` });
    stage.append(canvas);
    const key = Legend.open("flow", { root: () => $(".stage"), probes: FlowKit.flowProbes(() => st.key) });
    FlowKit.census(f).forEach((id) => key.saw(id));
    // Present is the diagram's one button; Rehearse, Save as video and the sentence about the flow's error cases are in its menu
    const sum = Branches.summary(st.key);
    const moreFlow = () => [
      { id: "rehearse", label: "Rehearse this flow", say: "Quiz yourself: rebuild the flow from memory, then reveal it", run: () => Rehearse.open(st.key) },
      { id: "clip", label: "Save as video", say: clipNote(), attrs: { id: "clip-btn" }, run: saveClip },
      sum ? { separator: true } : null, sum ? { node: sum } : null];
    const diagram = Menus.frame({ barClass: "flows-head", left: [picker, branch], right: [Menus.keyButton(key), present_, Nav.moreMenu(moreFlow)],
      say: [tag ? h("span", { class: "tracer-place" }, tag, ` ${Releases.tracerPlaceWords(pl)}`) : null, h("span", { class: "dia-hint", id: "clip-status", role: "status", "aria-live": "polite" })] }, stage);
    main.append(diagram);
    if (HASH.has("picker")) picker.open();  // #flows&picker opens the list on arrival, for screenshots
    const nodeList = flowNodes(st.key, () => player);
    const caption = h("section", { class: "caption", id: "caption", "aria-live": "polite" });
    const transport = h("footer", { class: "transport", id: "transport" });
    main.append(...[Branches.findings(st.key)].filter(Boolean), nodeList, caption, transport);
    key.paint();
    player = makePlayer(canvas, { host: stage, key: st.key, cur: st.cur, onStep: (p) => { st.cur = p.cur; paintCaption(); paintTransport(); followStep(p); Minimap.refresh(); }, onPlay: paintTransport,
      onFlow: (p) => select(p.key, -1) });
    paintCaption(); buildTransport(); paintTransport();
  }
  /* The canvas is pixels, so a keyboard cannot reach what is drawn on it. This list is the same nodes as buttons: every
     lane, step, contract and open question the canvas draws, each opening the panel as a click on the canvas does. */
  function flowNodes(flowKey, playerOf) {
    const f = FlowKit.flowOf(flowKey);
    const lanes = [...FlowKit.touchedLanes(f)].sort((a, b) => LANE_INDEX[a] - LANE_INDEX[b]);
    const contracts = [...new Set(f.steps.flatMap((x) => x.contracts))].filter((c) => CONTRACT[c]);
    const pins = [...new Set(f.steps.flatMap((x) => x.unknowns.map((u) => u.id)))].filter((u) => ent(u));
    const btn = (spec) => Nodes.wire(h("button", { class: "flow-node", type: "button" }, spec.text), spec);
    const group = (title, kids) => (kids.length ? h("div", { class: "fn-group" }, h("b", {}, title), kids) : null);
    return h("details", { class: "flow-nodes", "data-flow-nodes": flowKey },
      h("summary", {}, "The flow as a list"),
      group("Apps and outside services", lanes.filter((k) => ent(k)).map((k) => btn({ text: titleOf(k), label: titleOf(k), key: k }))),
      group("Contracts", contracts.map((c) => btn({ text: CONTRACT[c].title, label: `${CONTRACT[c].title} (${c})`, key: c }))),
      group("Open questions", pins.map((u) => btn({ text: titleOf(u), label: `${titleOf(u)} (${u})`, key: u }))));
  }
  function svgIcon(kind) {
    const paths = { present: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>', download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
      rehearse: '<path d="M4 7h6M14 7h6M4 17h10M18 17h2"/><circle cx="12" cy="7" r="2"/><circle cx="16" cy="17" r="2"/>' };
    const el = s("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 1.8 });
    el.innerHTML = paths[kind];
    return el;
  }
  function inferredLine() { const t = FlowKit.inferredNote(st.key); return t ? h("div", { class: "cap-inferred heuristic", "data-inferred-flow": st.key }, t) : null; }
  function paintCaption() {
    const box = $("#caption"); if (!box) return;
    const f = FlowKit.flowOf(st.key);
    box.innerHTML = "";
    if (st.cur === -1) {
      const e = E[st.key];
      box.append(h("div", { class: "cap-where" }, h("span", {}, `${e.state ? stateWord(e.state) : "Nobody has given this flow a state yet"} \u00b7 ${plural(f.steps.length, "step")}`), h("span", { class: "muted" }, "Press space to play, or pick a step")),
        h("div", { class: "cap-title" }, e.title), ...[inferredLine()].filter(Boolean));  // native append prints a null as "null"
      return;
    }
    const stp = f.steps[st.cur];
    const facts = h("ul", { class: "cap-facts" });
    // One line per contract and sender: a contract sent to three consumers is one fact, not three.
    const groups = [];
    for (const m of stp.messages) {
      const g = groups.find((x) => x.contract === m.contract && x.from === m.from && x.direction === m.direction && x.kind === m.kind);
      if (g) g.to.push(m.to); else groups.push({ ...m, to: [m.to] });
    }
    for (const m of groups) {
      const c = CONTRACT[m.contract];
      if (!c) { facts.append(h("li", { "data-no-contract": "" }, h("i", { class: "lane-dot", style: `background:${FlowKit.laneColor(m.from)}` }), h("span", {}, h("b", {}, `${titleOf(m.from)} to ${m.to.map(titleOf).join(", ")}`), ", no contract named."))); continue; }
      facts.append(h("li", {}, h("i", { class: "lane-dot", style: `background:${FlowKit.laneColor(m.from)}` }),
        h("span", {}, h("b", {}, `${titleOf(m.from)} to ${m.to.map(titleOf).join(", ")}`), " over ", refChip(m.contract), m.kind === "request" ? ", and the answer comes back." : ".",
          m.direction === "inferred" ? h("span", { class: "heuristic", title: `The arrow is drawn from ${titleOf(c.provider)}, the contract's provider${m.to.length > 1 ? `, to all ${m.to.length} of its users` : ""}` }, " (The page doesn't say who sends this; fix the step text to say.)") : null,
          c.crosses ? h("div", { class: "muted crosses-line", html: "Carries: " + c.crosses }) : null)));
    }
    if (!stp.messages.length && stp.self) facts.append(h("li", {}, h("i", { class: "lane-dot", style: `background:${FlowKit.laneColor(stp.self)}` }),
      h("span", {}, "Inside ", h("b", {}, titleOf(stp.self)), "; no other app is involved.")));
    if (stp.unrecorded) facts.append(h("li", { "data-unrecorded": "" }, h("i", { class: "lane-dot named" }), h("span", { class: "heuristic" }, "The step names more than one app or party, and the page doesn't say who sends to whom. Start the step with \"Sender -> Receiver:\".")));
    for (const pin of stp.unknowns) {
      const q = ASK[pin.id]; if (!q) continue;
      const lv = unknownLevel(pin.id);
      // the chip names the question once; what it holds up is said by name, never by the contract's code
      const holds = pin.why.startsWith("holds") ? pin.why.replace(/^holds\s*/, "").replace(/[A-Z][A-Z0-9]*-[\w.-]+/g, (id) => titleOf(keyForId(id) || id)) : "";
      facts.append(h("li", {}, lampEl(lv === "resolved" ? "resolved" : lv), h("span", {}, refChip(pin.id), " ",
        q.state === "open" ? h("span", { class: "pill " + lv }, `Open, ask ${q.ask.name} by ${day(q.askBy)}`) : h("span", { class: "pill" }, "Answered"),
        holds ? h("span", { class: "muted" }, ` Holds up ${holds}.`) : null,
        q.state !== "open" && pin.textSaysOpen ? h("div", { class: "heuristic" }, "Answered, but the flow page still calls it open; update the page.") : null)));
    }
    const ends = stepEnds(stp), named = stp.named.filter((k) => !ends.has(k));
    if (named.length) facts.append(h("li", {}, h("i", { class: "lane-dot named" }), h("span", { class: "heuristic" }, "Also mentioned in the step: ", named.map((k) => refChip(k)))));
    box.append(h("div", { class: "cap-where" }, h("span", {}, h("b", {}, `Step ${stp.n}`), ` of ${f.steps.length}`, " ",
      h("button", { class: "linkish", type: "button", "data-step-details": "", onclick: () => DetailsPanel.show(PlanDetails.stepKey(st.key, st.cur), { reset: true }) }, "Details for this step")), h("span", { class: "muted" }, E[st.key].title)),
      h("div", { class: "cap-text", html: stp.html }), facts, ...[inferredLine()].filter(Boolean));  // native append prints a null as "null"
  }
  function buildTransport() {
    const tr = $("#transport"); if (!tr) return;
    const f = FlowKit.flowOf(st.key), n = f.steps.length;
    tr.innerHTML = "";
    const keys = h("div", { class: "keys" },
      h("button", { class: "key", "aria-label": "Previous step", onclick: () => { player.pause(); player.go(player.cur <= 0 ? 0 : player.cur - 1); }, html: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>' }),
      h("button", { class: "key big", id: "play-btn", "aria-label": "Play", onclick: () => player.toggle() }),
      h("button", { class: "key", "aria-label": "Next step", onclick: () => { player.pause(); player.go(player.cur + 1); }, html: '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>' }));
    const scrub = h("div", { class: "scrub", id: "scrub", role: "slider", tabindex: 0, "aria-label": "Step", "aria-valuemin": 1, "aria-valuemax": n }, h("div", { class: "rail" }), h("div", { class: "fill", id: "scrub-fill" }));
    f.steps.forEach((stp, i) => {
      const first = stp.messages[0];
      const t = h("div", { class: "tick", style: `left:${pct(i, n)};color:${first ? FlowKit.laneColor(first.from) : stp.self ? FlowKit.laneColor(stp.self) : Theme.c("ink-3")}`, title: `Step ${stp.n}: ${stp.short}` });
      stp.unknowns.forEach((p) => { if (ASK[p.id]) t.append(h("i", { class: "q " + unknownLevel(p.id) })); });
      scrub.append(t);
    });
    scrub.append(h("div", { class: "lbl", style: "left:0;transform:none" }, "Step 1"), h("div", { class: "lbl", style: "right:0;left:auto;transform:none" }, `Step ${n}`));
    let down = false;
    const at = (e) => { const r = scrub.getBoundingClientRect(); return clamp(Math.round(((e.clientX - r.left) / r.width) * (n - 1)), 0, n - 1); };
    scrub.addEventListener("pointerdown", (e) => { down = true; scrub.setPointerCapture(e.pointerId); player.pause(); player.go(at(e)); });
    scrub.addEventListener("pointermove", (e) => { if (down && at(e) !== player.cur) player.go(at(e)); });
    scrub.addEventListener("pointerup", () => { down = false; });
    const speed = h("div", { class: "seg", "aria-label": "Speed" }, [["0.6", "Slow"], ["1", "Normal"], ["1.6", "Fast"]].map(([v, label]) =>
      h("button", { "aria-pressed": String(+v === st.speed), onclick: (ev) => { st.speed = +v; $$("button", ev.currentTarget.parentNode).forEach((b) => b.setAttribute("aria-pressed", String(b === ev.currentTarget))); } }, label)));
    tr.append(keys, scrub, h("div", { class: "meta" }, speed, h("span", { class: "hints" }, h("kbd", {}, "←"), " ", h("kbd", {}, "→"), ": step · ", h("kbd", {}, "Space"), ": play · ", h("kbd", {}, "P"), ": present")));
  }
  const pct = (i, n) => (n === 1 ? "50%" : `${(i / (n - 1)) * 100}%`);
  function paintTransport() {
    const n = FlowKit.flowOf(st.key).steps.length, cur = player ? player.cur : -1;
    $$("#scrub .tick").forEach((t, i) => { t.classList.toggle("done", cur === -1 || i <= cur); t.classList.toggle("now", i === cur); });
    const fill = $("#scrub-fill"); if (fill) fill.style.width = cur === -1 ? "100%" : n === 1 ? "50%" : `${(cur / (n - 1)) * 100}%`;
    const sc = $("#scrub"); if (sc) { sc.setAttribute("aria-valuenow", Math.max(1, cur + 1)); sc.setAttribute("aria-valuetext", cur === -1 ? "Overview" : `Step ${cur + 1} of ${n}`); }
    const btn = $("#play-btn"); if (btn) { btn.innerHTML = player && player.playing ? '<svg viewBox="0 0 24 24"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>'; btn.setAttribute("aria-label", player && player.playing ? "Pause" : "Play"); }
  }
  function select(key, step) {
    if (!FLOW[key]) return;
    const changed = key !== st.key;
    st.key = key; st.cur = step ?? -1;
    if (App.trail.length === 1 && App.trail[0] === key) { App.trail = []; }  // arriving at a flow is its summary, not a pick
    if (App.view !== "flows") { showView("flows"); }
    else if (changed || !player || !player.canvas.isConnected) rerender();
    else { player.pause(); player.go(st.cur); }
    history.replaceState(null, "", `#flows&open=${encodeURIComponent(key)}${st.cur >= 0 ? `&step=${st.cur + 1}` : ""}${Branches.hashPart(key)}`);
  }
  function clipNote() { const fmt = FlowKit.clipFormat(); return fmt ? "Saves this flow as a video you can drop into slides" : "Recording a video doesn't work in this browser; try Chrome"; }
  async function saveClip() {
    await (document.fonts ? document.fonts.ready : Promise.resolve());
    if (recording) return;
    const f = FlowKit.flowOf(st.key), status = () => $("#clip-status");
    if (!FlowKit.clipFormat()) { toast("This browser can't record video. Try Chrome."); return; }
    recording = true;
    try {
      const total = Math.round(FlowKit.clipPlan(f).total);
      const out = await FlowKit.recordClip(f, { onProgress: (p, T) => { const b = status(); if (b) b.textContent = `Recording ${Math.ceil(T)} of ${total} s`; } });
      window.__clipResult = { ok: true, mime: out.mime, size: out.blob.size, name: out.name };
      if (window.__selftestClip) window.__clipBlob = out.blob;
      if (!window.__selftestClip) FlowKit.download(out.blob, out.name);
      toast(`Saved ${out.name}, ${(out.blob.size / 1024 / 1024).toFixed(1)} MB`);
    } catch (err) {
      console.error("[flows] the clip was not saved", err);
      window.__clipResult = { ok: false, error: String(err.message || err) };
      toast(`The video didn't save: ${err.message}`);
    } finally {
      recording = false;
      const b = status(); if (b) b.textContent = "";
    }
  }

  /* ------------------------------------------------------------ present mode */
  function present(key, step) {
    if (!FLOW[key]) return;
    const root = $("#overlay");
    root.hidden = false; root.className = "present"; root.innerHTML = "";
    const e = E[key];
    const canvas = h("canvas", { class: "present-canvas", role: "img", "aria-label": `Sequence of ${e.title}` });
    const cap = h("div", { class: "present-caption", "aria-live": "polite" }, h("div", { class: "pc-n", id: "pc-n" }), h("p", { class: "pc-c", id: "pc-c" }), FlowKit.inferredNote(key) ? h("div", { class: "pc-inferred heuristic", "data-inferred-flow": key }, FlowKit.inferredNote(key)) : null);
    const bar = h("div", { class: "present-bar" },
      h("button", { class: "key", "aria-label": "Previous step", onclick: () => { presenter.pause(); presenter.go(Math.max(0, presenter.cur - 1)); }, html: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>' }),
      h("button", { class: "key big", id: "pr-play", "aria-label": "Play", onclick: () => presenter.toggle() }),
      h("button", { class: "key", "aria-label": "Next step", onclick: () => { presenter.pause(); presenter.go(presenter.cur + 1); }, html: '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>' }),
      h("div", { class: "pr-dots", id: "pr-dots" }),
      h("span", { class: "hints" }, h("kbd", {}, "←"), " ", h("kbd", {}, "→"), " or ", h("kbd", {}, "Space"), " · ", h("kbd", {}, "Esc"), " to leave"),
      h("button", { class: "btn", onclick: closePresent }, "Exit (Esc)"));
    const scroller = h("div", { class: "present-scroll" }, canvas);
    root.append(h("div", { class: "present-top" }, h("div", {}, h("div", { class: "pt-kicker" }, `${e.id} · ${D.title}`), h("h1", {}, e.title))), scroller, cap, bar);
    const paint = (p) => {
      const f = FlowKit.flowOf(p.key), stp = f.steps[p.cur];
      $("#pc-n").textContent = stp ? `Step ${stp.n} of ${f.steps.length}` : `${plural(f.steps.length, "step")}. Press space to play.`;
      $("#pc-c").textContent = stp ? FlowKit.captionOf(stp) : f.title;
      $("#pr-dots").innerHTML = "";
      f.steps.forEach((x, i) => $("#pr-dots").append(h("button", { class: i === p.cur ? "on" : i < p.cur ? "done" : "", title: `Step ${x.n}`, onclick: () => { p.pause(); p.go(i); } })));
      const btn = $("#pr-play");
      btn.innerHTML = p.playing ? '<svg viewBox="0 0 24 24"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>';
      root.dataset.step = stp ? stp.n : "";
    };
    presenter = makePlayer(canvas, { host: scroller, key, cur: -1, present: true, onStep: paint, onPlay: paint, onFlow: paint, onPick: (t) => toast(`Press Esc to leave, then open ${titleOf(keyForId(t.id) || t.id)}`) });
    presenter.go(step ?? 0);
    paint(presenter);
    let idle = 0;
    root.onmousemove = () => { root.classList.remove("idle"); clearTimeout(idle); idle = setTimeout(() => root.classList.add("idle"), 2400); };
    history.replaceState(null, "", `#present=${encodeURIComponent(key)}&step=${(step ?? 0) + 1}`);
  }
  function closePresent() {
    const root = $("#overlay");
    if (!root.classList.contains("present")) return;
    root.hidden = true; root.className = ""; root.innerHTML = ""; presenter = null;
    history.replaceState(null, "", "#" + App.view);
  }
  document.addEventListener("keydown", (e) => {
    if (e.target.closest && e.target.closest("input,textarea,select,[contenteditable]")) return;
    // on a focused button, link, tab or option the key belongs to that control: Space presses it, arrows move among tabs
    if (e.target.closest && e.target.closest("button,a[href],[role=tab],[role=option],[role=combobox],[role=button]") && !(e.key === "Escape")) return;
    const pr = presenter && $("#overlay").classList.contains("present") ? presenter : null;
    const p = pr || (App.view === "flows" && $("#overlay").hidden ? player : null);
    if (!p) return;
    if (e.key === "ArrowRight" || (pr && e.key === "PageDown")) { e.preventDefault(); p.pause(); p.go(p.cur + 1); }
    else if (e.key === "ArrowLeft" || (pr && e.key === "PageUp")) { e.preventDefault(); p.pause(); p.go(Math.max(0, p.cur - 1)); }
    else if (e.key === " ") { e.preventDefault(); p.toggle(); }
    else if (e.key === "Home") p.go(0);
    else if (e.key === "End") p.go(FlowKit.flowOf(p.key).steps.length - 1);
    else if (e.key === "Escape" && pr) closePresent();
    else if (e.key.toLowerCase() === "p" && !pr) present(st.key, Math.max(0, st.cur));
  });
  function here() {
    if (!st.key || App.view !== "flows") return null;
    const f = FlowKit.flowOf(st.key);  // the branch shown, when one is picked
    return st.cur >= 0 ? [...laneEnds(f.steps[st.cur])] : flowStations(f);
  }
  function highlight(key) { if (FLOW[key] && key !== st.key) select(key, -1); paintFocus(key); }
  /* ------------------------------------------------------------ the Details panel (detailspanel.js) */
  const flowOf = () => FlowKit.flowOf(st.key);
  /* The lanes a pick lights on the canvas: a step's ends, a contract's two sides, what a question holds up. */
  function litBy(key) {
    if (PlanDetails.isStep(key)) { const s = flowOf().steps[PlanDetails.parseStep(key).i]; return s ? [...stepEnds(s)] : []; }
    return [...new Set([...mapAnchors(key), ...PlanDetails.held(key).apps])];
  }
  /* The play head follows a picked step, and the scrub ticks of the steps a picked question or contract touches are marked. */
  function paintFocus(key) {
    if (App.view !== "flows") return;
    if (key && PlanDetails.isStep(key)) { const i = PlanDetails.parseStep(key).i; if (player && player.cur !== i && flowOf().steps[i]) { player.pause(); player.go(i); } }
    const contracts = key && UNKNOWN[key] ? PlanDetails.held(key).contracts : new Set(key && CONTRACT[key] ? [key] : []);
    $$("#scrub .tick").forEach((t, i) => {
      const s = flowOf().steps[i];
      t.classList.toggle("held", !!key && !!s && !PlanDetails.isStep(key) && (s.unknowns.some((x) => x.id === key) || s.contracts.some((c) => contracts.has(c))));
    });
  }
  /* A step picked in the panel, then the play head moved (arrow keys, scrub, Play): the panel follows to the new step. */
  function followStep(p) {
    const top = App.trail[App.trail.length - 1] || "";
    if (!PlanDetails.isStep(top) || p.key !== st.key) return;
    if (p.cur < 0) { DetailsPanel.clear(); return; }
    const next = PlanDetails.stepKey(st.key, p.cur);
    if (next !== top) DetailsPanel.show(next, { reset: true });
  }
  function flowSummary() {
    const f = flowOf(), e = E[st.key];
    const lanes = [...FlowKit.touchedLanes(f)].sort((a, b) => LANE_INDEX[a] - LANE_INDEX[b]).filter((k) => ent(k));
    const contracts = [...new Set(f.steps.flatMap((x) => x.contracts))].filter((c) => CONTRACT[c]);
    const ids = PlanDetails.relatedQuestions(st.key), way = Branches.say(st.key);
    return [PlanDetails.head("Flow", e.title, statePill(e.state), h("span", { class: "pill" }, plural(f.steps.length, "step"))),
      h("div", { class: "p-body" },
        e.text ? PlanDetails.prose(shorten(e.text, 360)) : PlanDetails.quiet("Not recorded: the flow's page says nothing about what it is for."),
        PlanDetails.sec("Who is in it", lanes.length || null, lanes.length ? PlanDetails.bullets(lanes.map((k) => PlanDetails.link(k))) : PlanDetails.quiet("Not recorded")),
        PlanDetails.sec("The contracts it uses", contracts.length || null, contracts.length ? PlanDetails.bullets(contracts.map((c) => PlanDetails.link(c))) : PlanDetails.quiet("No step names a contract.")),
        PlanDetails.sec("How it can go wrong", null, h("div", { class: "p-note" }, way || "Not recorded: the flow's page doesn't draw its error cases yet.")),
        PlanDetails.sec("What's waiting on it", ids.length || null, ids.length ? ids.map(PlanDetails.questionRow) : PlanDetails.quiet("Nothing is waiting on it.")),
        h("div", { class: "p-note" }, "Pick a step or a contract on the diagram to see just that one."), PlanDetails.aboutSection())];
  }
  /* One step: who sends, the contract and every way it can answer, the error branches, and what waits on it. */
  function stepNodes(key) {
    const p = PlanDetails.parseStep(key), f = FlowKit.flowOf(p.flow), s = f.steps[p.i];
    if (!s) return [h("div", { class: "p-empty" }, "That step isn't in the flow shown any more. Pick it again.")];
    const groups = [];
    for (const m of s.messages) {
      const g = groups.find((x) => x.contract === m.contract && x.from === m.from && x.kind === m.kind);
      if (g) g.to.push(m.to); else groups.push({ ...m, to: [m.to] });
    }
    const senders = groups.map((m) => h("li", {}, h("i", { class: "lane-dot", style: `background:${FlowKit.laneColor(m.from)}` }), " ", PlanDetails.link(m.from), " to ", ...PlanDetails.joined(m.to.map((k) => PlanDetails.link(k))),
      ...(m.contract ? [" over ", PlanDetails.link(m.contract)] : [", no contract named"]), m.kind === "request" ? ", and the answer comes back." : ".", m.direction === "inferred" ? h("div", { class: "heuristic" }, "The page doesn't say who sends this; the contract's provider is shown.") : null));
    if (!groups.length && s.unrecorded) senders.push(h("li", {}, "More than one app or party is named, and the page doesn't say who sends to whom."));
    if (!groups.length && s.self) senders.push(h("li", {}, "Inside ", PlanDetails.link(s.self), "; no other app is involved."));
    const contracts = [...new Set(s.contracts)].filter((c) => CONTRACT[c]), branches = (D.branches || {})[p.flow];
    const ways = (c) => {
      const w = (D.contractAnswers || {})[c] || [];
      return w.length ? h("ul", { class: "dp-ways" }, w.map((x) => h("li", { class: x.error ? "err" : "" }, h("b", {}, x.case), x.error ? h("span", { class: "pill" }, "error") : null, h("div", { class: "ml-sub" }, x.says || ""))))
        : PlanDetails.quiet("Not recorded: no table of how it can answer.");
    };
    const wrong = contracts.flatMap((c) => (branches && branches.state === "drawn" ? branches.groups.filter((g) => g.item === c).flatMap((g) => g.options) : []));
    const ids = PlanDetails.relatedQuestions(key);
    return [PlanDetails.head(`Step ${s.n} of ${f.steps.length}`, s.short, h("span", { class: "pill" }, E[p.flow].title)),
      h("div", { class: "p-body" },
        PlanDetails.sec("Who sends", null, senders.length ? h("ul", { class: "mini-list" }, senders) : PlanDetails.quiet("Not recorded: the step names no sender.")),
        PlanDetails.sec(contracts.length > 1 ? "The contracts it uses" : "The contract it uses", null, contracts.length
          ? contracts.map((c) => h("div", { class: "dp-contract" }, h("div", {}, PlanDetails.link(c), CONTRACT[c].crosses ? h("div", { class: "muted crosses-line", html: "Carries: " + CONTRACT[c].crosses }) : null), h("div", { class: "gl" }, "Every way it can answer"), ways(c)))
          : PlanDetails.quiet("This step uses no contract.")),
        PlanDetails.sec("If it goes wrong", wrong.length || null, wrong.length ? h("ul", { class: "mini-list" }, wrong.map((o) => h("li", {}, h("b", {}, o.label), o.marks.length ? h("span", { class: "muted" }, ` (${o.marks.join(", ")})`) : null,
          o.drawn ? [" ", h("button", { class: "btn tiny", type: "button", onclick: () => showBranch(p.flow, o.id) }, "Show it in the diagram")] : h("div", { class: "ml-sub" }, "Not drawn yet"))))
          : PlanDetails.quiet("Not recorded: no error branch is drawn at this step.")),
        PlanDetails.sec("What's waiting on it", ids.length || null, ids.length ? ids.map(PlanDetails.questionRow) : PlanDetails.quiet("Nothing is waiting on it.")))];
  }
  function showBranch(flow, id) { Branches.choose(flow, id); st.cur = -1; DetailsPanel.clear(); rerender(); }
  DetailsPanel.register("flows", {
    view: "flows", live: () => D.flows.length > 0 && !!st.key && !!FLOW[st.key],
    rootLabel: () => (E[st.key] ? shorten(E[st.key].title, 26) : "The flow"), summary: flowSummary,
    owns: (k) => PlanDetails.owns(k) || (k === st.key && !!FLOW[k]),
    detail: (k) => (PlanDetails.isStep(k) ? stepNodes(k) : k === st.key && FLOW[k] ? flowSummary() : PlanDetails.detail(k, "flows")),
    label: PlanDetails.label, open: (k) => PlanDetails.openFor(k, "flows"),
    waiting: (k) => PlanDetails.waitingTab(k, "queue"), waitingCount: () => PlanDetails.waitingCount("queue"), focus: (k) => paintFocus(k),
  });
  return { render, select, present, closePresent, here, highlight, st, player: () => player, presenter: () => presenter, saveClip };
})();
View("flows", { label: "Flows", title: "Each flow, played step by step across the apps", render: Flows.render, here: Flows.here, highlight: Flows.highlight,
  count: () => String(D.flows.length), lamp: () => { const l = D.flows.map((f) => levelOf(f.key)).filter((x) => x !== "dark").sort((a, b) => rank(b) - rank(a))[0]; return l || null; } });
