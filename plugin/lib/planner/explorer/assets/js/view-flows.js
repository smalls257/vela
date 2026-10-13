/* Flows, played. Each step's messages travel as pulses between the apps' lanes, in the map's left-to-right order;
   open questions from the record sit at the step they hold, breathing in their lamp colour. One player drives the
   view and one drives present mode, both on FlowKit's renderer. Save clip records the same frames as MP4 or WebM in
   the browser. Heuristics are labelled where they show: an inferred direction says so under its arrow. */
const Flows = (() => {
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
        const G = FlowKit.layout(f, { x: 0, y: 6, w: p.w - 8, h: p.h - 6, s: k });
        ctx.clearRect(0, 0, p.w, p.h);
        const tau = ((now - p.entered) / 1000) * st.speed, cur = p.cur === -1 ? f.steps.length : p.cur;
        const hl = p.present ? null : App.focus ? [...new Set([...mapAnchors(App.focus), ...(CONTRACT[App.focus] ? [CONTRACT[App.focus].provider, ...CONTRACT[App.focus].consumers] : [])])] : null;
        // Plain: every message is drawn where it lands, nothing travels; the step timing still drives Play.
        p.hits = FlowKit.drawScene(ctx, G, { cur, tau: FX.on ? tau : 99, clock: now / 1000, D: TRAVEL, highlight: hl });
        if (p.playing && p.cur >= 0) {
          const step = f.steps[p.cur];
          if (tau > FlowKit.travelTime(step, TRAVEL) + (p.present ? 3.0 : 3.4)) {
            if (p.cur < f.steps.length - 1) p.go(p.cur + 1); else { p.pause(); Sound.chime(); }
          }
        }
      }
      requestAnimationFrame(p.frame);
    };
    p.go = (i, sound = true) => {
      const n = flow().steps.length;
      p.cur = clamp(i, -1, n - 1);
      p.entered = performance.now();
      if (p.cur >= 0 && sound) Sound.playStep(flow().steps[p.cur], TRAVEL / st.speed);
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
      if (t && t.type === "unknown") { const q = ASK[t.id]; showTip(e, `<b>${esc(t.id)} ${esc(E[t.id] ? E[t.id].title : "")}</b>${esc(q.state === "open" ? q.question : "Settled: " + (q.outcome || q.question))}`); }
      else if (t && t.type === "lane") showTip(e, `<b>${esc(FlowKit.laneName(t.id))}</b>${FlowKit.touchedLanes(FlowKit.flowOf(p.key)).has(t.id) ? "in this flow" : "not in this flow; its lane keeps its place"}`);
      else if (t && t.type === "contract") showTip(e, `<b>${esc(t.id)} ${esc(CONTRACT[t.id].title)}</b>${esc(CONTRACT[t.id].state || "no state")}; ${esc(LIGHT[levelOf(t.id)].word.toLowerCase())}`);
      else hideTip();
    });
    canvas.addEventListener("mouseleave", hideTip);
    canvas.addEventListener("click", (e) => {
      const t = hitAt(e);
      if (!t) return;
      if (t.type === "unknown" || t.type === "contract") { if (!p.present) go(t.id, {}); else opts.onPick && opts.onPick(t); }
      else if (t.type === "ref") { p.key = t.id; p.go(-1, false); opts.onFlow && opts.onFlow(p); }
      else if (t.type === "lane") { if (!p.present) go(t.id, {}); if (!Assets.theme(FlowKit.laneName(t.id))) Sound.lane(t.id, undefined, { gain: 0.45, dur: 1.2 }); }
      else if (t.si !== undefined) { p.pause(); p.go(t.si); }
    });
    requestAnimationFrame(p.frame);
    return p;
  }

  /* ------------------------------------------------------------ the view */
  function render(main) {
    if (!D.flows.length) { main.append(emptyState("No flows yet.", "A flow page (FLO-nnn) with numbered Steps plays here, step by step across the apps.", "/planner:boundary")); return; }
    const f = FlowKit.flowOf(st.key);
    const picker = FlowPicker.make({ current: () => st.key, onPick: (key) => select(key, -1) });
    const actions = h("div", { class: "flow-actions" },
      h("button", { class: "btn", onclick: () => Rehearse.open(st.key), title: "Rebuild the flow from memory, then reveal it" }, svgIcon("rehearse"), "Rehearse this flow"),
      h("button", { class: "btn", id: "clip-btn", onclick: saveClip, title: clipNote() }, svgIcon("download"), "Save clip"),
      h("button", { class: "btn primary", id: "present-btn", onclick: () => present(st.key, Math.max(0, st.cur)), title: "Present full screen (P)" }, svgIcon("present"), "Present"));
    main.append(h("div", { class: "flows-head" }, picker, actions));
    if (HASH.has("picker")) picker.open();  // #flows&picker opens the list on arrival, for screenshots
    const stage = h("div", { class: "stage" });
    const canvas = h("canvas", { class: "stage-canvas", role: "img", "aria-label": `Sequence of ${f.title}` });
    stage.append(canvas, legendRow());
    const caption = h("section", { class: "caption", id: "caption", "aria-live": "polite" });
    const transport = h("footer", { class: "transport", id: "transport" });
    main.append(stage, caption, transport);
    player = makePlayer(canvas, { key: st.key, cur: st.cur, onStep: (p) => { st.cur = p.cur; paintCaption(); paintTransport(); Minimap.refresh(); }, onPlay: paintTransport,
      onFlow: (p) => select(p.key, -1) });
    paintCaption(); buildTransport(); paintTransport();
  }
  function svgIcon(kind) {
    const paths = { present: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>', download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
      rehearse: '<path d="M4 7h6M14 7h6M4 17h10M18 17h2"/><circle cx="12" cy="7" r="2"/><circle cx="16" cy="17" r="2"/>' };
    const el = s("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 1.8 });
    el.innerHTML = paths[kind];
    return el;
  }
  function legendRow() {
    return h("div", { class: "stage-legend", "aria-hidden": "true", html:
      `<span><svg viewBox="0 0 22 10"><path d="M1 5h15" stroke="currentColor" stroke-width="1.6"/><path d="M14 1l7 4-7 4z" fill="currentColor"/></svg>The step says who sends</span>
       <span><svg viewBox="0 0 22 10"><path d="M1 5h18" stroke="currentColor" stroke-width="1.6"/><path d="M14 1l6 4-6 4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg><i class="heuristic">Direction inferred from the contract</i></span>
       <span><i class="lamp warning"></i>Open, overdue</span><span><i class="lamp caution"></i>Open question</span><span><i class="lamp resolved"></i>Settled, still cited</span>` });
  }
  function inferredLine() { const t = FlowKit.inferredNote(st.key); return t ? h("div", { class: "cap-inferred heuristic", "data-inferred-flow": st.key }, t) : null; }
  function paintCaption() {
    const box = $("#caption"); if (!box) return;
    const f = FlowKit.flowOf(st.key);
    box.innerHTML = "";
    if (st.cur === -1) {
      const e = E[st.key];
      box.append(h("div", { class: "cap-where" }, h("span", {}, `${e.id}, ${e.state || "no state"} · ${plural(f.steps.length, "step")}`), h("span", { class: "muted" }, "Press space to play, or pick a step")),
        h("div", { class: "cap-title" }, e.title), e.text ? h("p", { class: "cap-intro" }, shorten(e.text, 360)) : "",
        h("ol", { class: "cap-steps" }, f.steps.map((stp, i) => h("li", {}, h("button", { onclick: () => { player.pause(); player.go(i); } }, stp.short)))), ...[inferredLine()].filter(Boolean));  // native append prints a null as "null"
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
      facts.append(h("li", {}, h("i", { class: "lane-dot", style: `background:${FlowKit.laneColor(m.from)}` }),
        h("span", {}, h("b", {}, `${titleOf(m.from)} to ${m.to.map(titleOf).join(", ")}`), " over ", refChip(m.contract), m.kind === "request" ? ", and the answer comes back." : ".",
          m.direction === "inferred" ? h("span", { class: "heuristic" }, ` Direction inferred: ${titleOf(c.provider)} provides it${m.to.length > 1 ? `; the step names no consumer, so all ${m.to.length} are drawn` : ""}${stp.fromTable ? "; the contract comes from the Contracts used table" : ""}.`) : null,
          c.crosses ? h("div", { class: "muted crosses-line", html: "Crosses: " + c.crosses }) : null)));
    }
    if (!stp.messages.length && stp.self) facts.append(h("li", {}, h("i", { class: "lane-dot", style: `background:${FlowKit.laneColor(stp.self)}` }),
      h("span", {}, "Inside ", h("b", {}, titleOf(stp.self)), "; nothing crosses a contract. ", h("span", { class: "heuristic" }, "The lane is the first app the text names."))));
    for (const pin of stp.unknowns) {
      const q = ASK[pin.id]; if (!q) continue;
      const lv = unknownLevel(pin.id);
      facts.append(h("li", {}, lampEl(lv === "resolved" ? "resolved" : lv), h("span", {}, refChip(pin.id), " ", E[pin.id] ? E[pin.id].title + ". " : "",
        q.state === "open" ? h("span", { class: "pill " + lv }, `Open, ask ${q.ask.name} by ${day(q.askBy)}`) : h("span", { class: "pill" }, "Settled"),
        pin.why.startsWith("holds") ? h("span", { class: "muted" }, ` Pinned here because it ${pin.why}.`) : null,
        q.state !== "open" && pin.textSaysOpen ? h("div", { class: "heuristic" }, "The flow text still calls this open; the question itself records it settled, so the marker shows it settled.") : null)));
    }
    const ends = stepEnds(stp), named = stp.named.filter((k) => !ends.has(k));
    if (named.length) facts.append(h("li", {}, h("i", { class: "lane-dot named" }), h("span", { class: "heuristic" }, "Also named in the text, not linked: ", named.map((k) => refChip(k)))));
    box.append(h("div", { class: "cap-where" }, h("span", {}, h("b", {}, `Step ${stp.n}`), ` of ${f.steps.length}`), h("span", { class: "muted" }, `${E[st.key].id} ${E[st.key].title}`)),
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
    tr.append(keys, scrub, h("div", { class: "meta" }, speed, h("span", { class: "hints" }, h("kbd", {}, "←"), " ", h("kbd", {}, "→"), " step ", h("kbd", {}, "Space"), " play ", h("kbd", {}, "P"), " present")));
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
    if (App.view !== "flows") { showView("flows"); }
    else if (changed || !player || !player.canvas.isConnected) rerender();
    else { player.pause(); player.go(st.cur, step >= 0); }
    history.replaceState(null, "", `#flows&open=${encodeURIComponent(key)}${st.cur >= 0 ? `&step=${st.cur + 1}` : ""}`);
  }
  function clipNote() { const fmt = FlowKit.clipFormat(); return fmt ? `Records a ${fmt.ext.toUpperCase()} clip, 1280 by 720${Sound.enabled ? ", with sound" : ""}, in the browser` : "Recording is not available in this browser"; }
  async function saveClip() {
    await (document.fonts ? document.fonts.ready : Promise.resolve());
    if (recording) return;
    const f = FlowKit.flowOf(st.key), btn = $("#clip-btn");
    if (!FlowKit.clipFormat()) { toast("This browser cannot record video, so no clip was saved."); return; }
    recording = true; if (btn) btn.disabled = true;
    try {
      const total = Math.round(FlowKit.clipPlan(f).total);
      const out = await FlowKit.recordClip(f, { onProgress: (p, T) => { const b = $("#clip-btn"); if (b) b.lastChild.textContent = `Recording ${Math.ceil(T)} of ${total} s`; } });
      window.__clipResult = { ok: true, mime: out.mime, size: out.blob.size, name: out.name };
      if (window.__selftestClip) window.__clipBlob = out.blob;
      if (!window.__selftestClip) FlowKit.download(out.blob, out.name);
      toast(`Saved ${out.name}, ${(out.blob.size / 1024 / 1024).toFixed(1)} MB`);
    } catch (err) {
      console.error("[flows] the clip was not saved", err);
      window.__clipResult = { ok: false, error: String(err.message || err) };
      toast(`The clip was not saved: ${err.message}`);
    } finally {
      recording = false;
      const b = $("#clip-btn"); if (b) { b.disabled = false; b.lastChild.textContent = "Save clip"; }
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
      h("button", { class: "btn", onclick: closePresent }, "Leave present"));
    root.append(h("div", { class: "present-top" }, h("div", {}, h("div", { class: "pt-kicker" }, `${e.id} · ${D.title}`), h("h1", {}, e.title))), canvas, cap, bar);
    const paint = (p) => {
      const f = FlowKit.flowOf(p.key), stp = f.steps[p.cur];
      $("#pc-n").textContent = stp ? `Step ${stp.n} of ${f.steps.length}` : `${plural(f.steps.length, "step")}. Press space to play.`;
      $("#pc-c").textContent = stp ? stp.short : f.title;
      $("#pr-dots").innerHTML = "";
      f.steps.forEach((x, i) => $("#pr-dots").append(h("button", { class: i === p.cur ? "on" : i < p.cur ? "done" : "", title: `Step ${x.n}`, onclick: () => { p.pause(); p.go(i); } })));
      const btn = $("#pr-play");
      btn.innerHTML = p.playing ? '<svg viewBox="0 0 24 24"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>';
      root.dataset.step = stp ? stp.n : "";
    };
    presenter = makePlayer(canvas, { key, cur: -1, present: true, onStep: paint, onPlay: paint, onFlow: paint, onPick: (t) => toast(`${t.id}: leave present mode to open it`) });
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
    if (e.key.toLowerCase() === "s" && !e.metaKey && !e.ctrlKey && !e.altKey) { Sound.set(!Sound.enabled); return; }
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
    const f = FLOW[st.key];
    return st.cur >= 0 ? [...stepEnds(f.steps[st.cur])] : flowStations(f);
  }
  function highlight(key) { if (FLOW[key] && key !== st.key) select(key, -1); }
  return { render, select, present, closePresent, here, highlight, st, player: () => player, presenter: () => presenter, saveClip };
})();
View("flows", { label: "Flows", title: "Each flow, played step by step across the apps", render: Flows.render, here: Flows.here, highlight: Flows.highlight,
  count: () => String(D.flows.length), lamp: () => { const l = D.flows.map((f) => levelOf(f.key)).filter((x) => x !== "dark").sort((a, b) => rank(b) - rank(a))[0]; return l || null; } });
