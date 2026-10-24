/* ------------------------------------------------------------ The Flows view: pinned lane names, starts, fold and hide
   (flowview.js, flowkit.js, view-flows.js). A flow taller than its room keeps its row of lane names at the top while the
   host scrolls, with a shadow under it, and a click on a pinned name still lands. A flow with more than one start
   (starts_data.py) has "Starts from" in its header row, a Start tag on each entry lane, a heading and rail for each
   start, the band where they join, and dims the start not picked; a flow with one start has none of that. Lanes that
   talk to only one other lane fold into it (one step on the host, numbers kept, open questions kept), by the button,
   the F key, the badge on the name and the list; any lane hides to a narrow dashed column and comes back. All of it
   rides in the address per flow, and the saved clip never shows any of it. */
(() => {
  const base = SelfTest.run;
  /* Let the page settle, then draw one frame of the flow now. (The page's own frames come from requestAnimationFrame, which a
     headless run under a virtual-time budget stops giving once the checks before ours have used the canvas hard.) */
  const tick = async () => { await new Promise((r) => setTimeout(r, 0)); if (Flows.player() && Flows.player().canvas.isConnected) Flows.player().draw(performance.now()); };
  /* Every string the stage draws for a flow, after every step has played, on one scratch canvas kept for all the checks. */
  const SCRATCH = document.createElement("canvas"); SCRATCH.width = 1040; SCRATCH.height = 1600;
  function textOf(flow, w = 1040) {
    const drawn = [], ctx = SCRATCH.getContext("2d"), G = FlowKit.layout(flow, { x: 0, y: 6, w: w - 8, h: 600, s: clamp(w / 1040, 0.8, 1.2) });
    for (let cur = 0; cur <= flow.steps.length; cur++) FlowKit.drawScene(ctx, G, { cur, tau: 99, clock: 0, D: 0.8, images: false, drawn });
    return drawn;
  }
  const stageGeom = () => { const c = $(".stage-canvas"); return { canvas: c, rect: c.getBoundingClientRect() }; };
  const hitOf = (type, id) => Flows.player().hits.find((t) => t.type === type && (id === undefined || t.id === id));
  /* A click at the middle of a hit the player drew, the way a pointer lands on the canvas. */
  function clickHit(t) {
    const { canvas, rect } = stageGeom();
    canvas.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: rect.left + t.x + t.w / 2, clientY: rect.top + t.y + t.h / 2 }));
  }
  function moveTo(t) {
    const { canvas, rect } = stageGeom();
    canvas.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: rect.left + t.x + t.w / 2, clientY: rect.top + t.y + t.h / 2 }));
  }
  const press = (key, target) => (target || document).dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
  function clean(key) {  // every choice undone, so a check starts from the flow as it comes
    const v = FlowView.choices(key);
    for (const h of [...v.folded]) FlowView.toggleFold(key, h);
    for (const l of [...v.hidden]) FlowView.show(key, l);
    FlowView.setStart(key, "all");
  }
  const rowKinds = (flow) => FlowKit.layout(flow, { x: 0, y: 6, w: 1032, h: 694, s: 1 }).rows.map((r) => r.u.kind);

  async function pinned(ok) {
    const f = D.flows.slice().sort((a, b) => b.steps.length - a.steps.length)[0];
    Nav.open("flows", f.key); Flows.select(f.key, -1); await tick();
    const stage = $(".stage"), keep = [stage.style.flex, stage.style.height, stage.style.minHeight];
    stage.style.flex = "none"; stage.style.height = "200px"; stage.style.minHeight = "0"; await tick(); await tick();
    const scrollable = stage.scrollHeight > stage.clientHeight + 40;
    ok(scrollable, `pin: a short stage makes ${f.key} scroll`, `pin: the stage did not scroll (${stage.scrollHeight} in ${stage.clientHeight})`);
    const lane0 = hitOf("lane"), top0 = lane0 ? lane0.y : -1;
    stage.scrollTop = 180; await tick(); await tick();
    const lane1 = hitOf("lane"), under = Flows.player().hits.filter((t) => !["lane", "fold", "hide", "ghost", "starttag"].includes(t.type) && t.y + t.h <= stage.scrollTop + lane1.h);
    const offset = stage.getBoundingClientRect().top - stageGeom().rect.top;  // how far the canvas has scrolled past the top of the room
    ok(!!lane0 && !!lane1 && Math.abs(lane1.y - lane0.y - offset) < 3 && offset > 100, `pin: scrolled ${Math.round(offset)} px, the lane names stay at the top of the room (hit moved ${Math.round(lane1.y - lane0.y)} px)`,
      `pin: the names did not follow the scroll: ${lane0 && lane0.y} then ${lane1 && lane1.y}, scrolled ${offset}`);
    ok(under.length === 0, "pin: nothing under the pinned row can be hit there", `pin: ${under.length} hits lie under the pinned names`);
    clickHit(lane1); await tick();
    ok($("#panel-body") && !!$("#panel-body").textContent.trim() && App.trail.length > 0 && App.trail[App.trail.length - 1] === lane1.id, "pin: a click on a pinned name still opens that lane in the panel", `pin: the click on the pinned ${lane1.id} opened ${App.trail[App.trail.length - 1]}`);
    // pixels: the pinned row is drawn at the scroll offset, with a shadow under it once scrolled, and not drawn there at the top
    const flow = FlowKit.flowOf(f.key), ctx = SCRATCH.getContext("2d"), G = FlowKit.layout(flow, { x: 0, y: 6, w: 1032, h: 200, s: 1 });
    const hitsAt = (scroll) => FlowKit.drawScene(ctx, G, { cur: -1, tau: 99, clock: 0, D: 0.8, images: false, scroll });
    const pill = (scroll) => hitsAt(scroll).find((t) => t.type === "lane");
    ok(pill(0).y === 6 && Math.abs(pill(250).y - 256) < 1 && textOf(flow).length > 0, "pin: drawn with no scroll the names sit where they always did; with scroll 250 they sit 250 px lower", "pin: the pinned position is wrong on the scratch canvas");
    const sample = (scroll, y) => { hitsAt(scroll); return ctx.getImageData(40, y, 1, 1).data[3]; };
    ok(sample(250, 250 + G.headerH + 12) > 0, "pin: a shadow falls under the pinned row once scrolled", "pin: no shadow under the pinned names");
    // the clip is a flow whole, whatever the stage shows: no pinned row, no starts, no folds
    const plain = FlowKit.flowOf(f.key, { plain: true });
    ok(!plain.view && FlowKit.drawnClip(plain).every((t) => t !== "START" && !/hidden/.test(t)), "pin: the saved clip draws the flow whole, with none of the stage's choices", "pin: the clip drew a Start tag or a hidden lane");
    stage.scrollTop = 0;
    [stage.style.flex, stage.style.height, stage.style.minHeight] = keep;
  }

  async function starts(ok) {
    const withStarts = D.flows.filter((f) => f.starts), without = D.flows.filter((f) => !f.starts);
    for (const f of without.slice(0, 8)) {
      Nav.open("flows", f.key); Flows.select(f.key, -1); await tick();
      if ($("[data-starts]") || FlowKit.flowOf(f.key).steps.some((s) => s.start) || rowKinds(FlowKit.flowOf(f.key)).some((k) => k === "section" || k === "merge")) { ok(false, "", `starts: ${f.key} has one start and still shows starts`); return; }
    }
    ok(true, `starts: ${without.length} flows with one way in show no Starts from, no heading and no band`);
    for (const f of withStarts) {
      const key = f.key, s = f.starts;
      clean(key); Nav.open("flows", key); Flows.select(key, -1); await tick(); await tick();
      const box = $(`[data-starts="${CSS.escape(key)}"]`), radios = box ? $$("[role=radio]", box) : [];
      ok(!!box && box.closest(".flows-head") && radios.length === s.options.length + 1 && radios[0].textContent === "Either" && radios[0].getAttribute("aria-checked") === "true"
        && s.options.every((o, i) => radios[i + 1].textContent === o.label) && box.getAttribute("role") === "radiogroup" && /^Starts from/.test(box.textContent),
        `starts, ${key}: "Starts from" in the header row, Either chosen, then ${s.options.map((o) => `"${o.label}"`).join(" and ")}`, `starts, ${key}: the picker is ${box ? radios.map((r) => r.textContent).join(" | ") : "missing"}`);
      ok(!!box.querySelector(".starts-guess") === !!s.guessed, `starts, ${key}: ${s.guessed ? "a guess says it is one" : "stated, so no guess label"}`, `starts, ${key}: the guess label is ${s.guessed ? "missing" : "shown but the page states who sends"}`);
      ok(new RegExp(`This flow starts ${s.options.length === 2 ? "two ways" : s.options.length + " ways"}`).test($("#caption").textContent) && (!s.guessed || /A guess/.test($("#caption").textContent)),
        `starts, ${key}: the overview says how many ways in${s.guessed ? ", and that it is a guess" : ""}`, `starts, ${key}: the overview says "${$("#caption").textContent.slice(0, 160)}"`);
      const tags = Flows.player().hits.filter((t) => t.type === "starttag");
      ok(s.options.every((o) => tags.some((t) => t.ids.includes(o.id) && t.lane === o.lane)), `starts, ${key}: each entry lane carries a Start tag`, `starts, ${key}: ${tags.length} Start tags for ${s.options.length} starts`);
      const kinds = rowKinds(FlowKit.flowOf(key));
      ok(kinds.filter((k) => k === "section").length === s.options.length && kinds.filter((k) => k === "merge").length === (s.merge ? 1 : 0),
        `starts, ${key}: a heading for each start${s.merge ? " and one band where they join" : ""}`, `starts, ${key}: rows ${kinds.filter((k) => k === "section" || k === "merge").join(", ")}`);
      const words = textOf(FlowKit.flowOf(key)).join(" | ");
      ok(s.options.every((o) => words.includes(o.label)) && /STARTS HERE/.test(words) && (!s.merge || /starts reach|starts join/.test(words)), `starts, ${key}: the headings carry each start's own words${s.merge ? ", and the band says where they meet" : ""}`, `starts, ${key}: the drawing says "${words.slice(0, 200)}"`);
      // picking one
      const second = s.options[s.options.length - 1], other = s.options[0];
      radios[radios.length - 1].click(); await tick();
      const flow = FlowKit.flowOf(key), dim = flow.steps.filter((x) => FlowView.dimmedStep(key, x)).map((x) => x.n);
      ok(flow.view.start === second.id && FlowView.hashPart(key).includes(`start=${second.id}`) && JSON.stringify(dim) === JSON.stringify(s.options.filter((o) => o !== second).flatMap((o) => o.steps)) && $(`[data-starts] [aria-checked=true]`).textContent === second.label,
        `starts, ${key}: picking "${second.label}" dims exactly the steps of the other starts, and rides in the address`, `starts, ${key}: dimmed ${dim}, address "${FlowView.hashPart(key)}"`);
      Flows.player().go(-1); Flows.player().go(0);
      ok(flow.steps[Flows.player().cur].start !== other.id, `starts, ${key}: Next skips the steps of the start not picked`, `starts, ${key}: playing started on step ${flow.steps[Flows.player().cur].n}, in the other start`);
      ok(Legend.audit().filter((p) => p.startsWith("flow")).length === 0, `starts, ${key}: the key matches the drawing with a start picked`, `starts, ${key}: ${Legend.audit()[0]}`);
      press("ArrowLeft", $("[data-starts] [aria-checked=true]")); await tick();
      ok(FlowKit.flowOf(key).view.start === (s.options.length > 1 ? s.options[s.options.length - 2].id : "all") && document.activeElement.getAttribute("aria-checked") === "true", `starts, ${key}: the arrow keys move between the starts and keep focus`, `starts, ${key}: ArrowLeft left start ${FlowKit.flowOf(key).view.start}`);
      // a click on a Start tag picks that start, and a second click lets go
      const tag = Flows.player().hits.find((t) => t.type === "starttag" && t.ids[0] === other.id);
      FlowView.setStart(key, "all"); await tick(); clickHit(Flows.player().hits.find((t) => t.type === "starttag" && t.ids[0] === other.id)); await tick();
      const picked = FlowKit.flowOf(key).view.start; clickHit(Flows.player().hits.find((t) => t.type === "starttag" && t.ids[0] === other.id)); await tick();
      ok(!!tag && picked === other.id && FlowKit.flowOf(key).view.start === "all", `starts, ${key}: a click on a Start tag picks that start; a second click lets go`, `starts, ${key}: tag clicks gave ${picked} then ${FlowKit.flowOf(key).view.start}`);
      // the picked start, pressed again, goes back to Either
      FlowView.setStart(key, second.id); await tick(); $(`[data-starts] [data-start="${second.id}"]`).click(); await tick();
      ok(FlowKit.flowOf(key).view.start === "all" && $("[data-starts] [data-start=all]").getAttribute("aria-checked") === "true", `starts, ${key}: pressing the picked start again goes back to Either`, `starts, ${key}: a second press left start ${FlowKit.flowOf(key).view.start}`);
      // the address brings the pick back, and another flow does not carry it
      const had = [...HASH.entries()];
      HASH.set("open", key); HASH.set("start", second.id); Flows.select(key, -1); Nav.open("flows", key); await tick();
      const back = FlowKit.flowOf(key).view.start;
      for (const k of [...HASH.keys()]) HASH.delete(k);
      had.forEach(([k, v]) => HASH.append(k, v));
      const elsewhere = D.flows.find((g) => g.key !== key);
      if (elsewhere) Flows.select(elsewhere.key, -1);
      ok(back === second.id && (!elsewhere || (FlowView.hashPart(elsewhere.key) === "" && !/start=/.test(location.hash))), `starts, ${key}: a link naming the start opens with it picked; another flow starts clean`, `starts, ${key}: the link opened with ${back}; the other flow's address "${elsewhere && FlowView.hashPart(elsewhere.key)}" and "${location.hash}"`);
      clean(key);
    }
  }

  async function folding(ok) {
    const foldable = D.flows.filter((f) => Object.keys(FlowView.hostsOf(f.key)).length);
    if (!foldable.length) return;
    const bad = [], seenMerged = [];
    for (const f of foldable) {
      const key = f.key, hosts = FlowView.hostsOf(key), plain = FlowKit.flowOf(key, { plain: true });
      clean(key); Nav.open("flows", key); Flows.select(key, -1); await tick(); await tick();
      const btn = $("#simplify-btn");
      if (!btn || btn.getAttribute("aria-pressed") !== "false" || btn.textContent !== "Simplify") { bad.push(`${key}: no Simplify button`); continue; }
      const answering = new Set(plain.steps.flatMap((x) => x.messages.flatMap((m) => (m.kind === "request" ? [m.to] : m.kind === "answer" ? [m.from] : []))));
      for (const m of Object.values(hosts).flat()) if (!answering.has(m)) bad.push(`${key}: ${m} folds but never answers its partner`);
      const members = Object.values(hosts).flat(), before = FlowKit.touchedLanes(FlowKit.flowOf(key));
      if (!members.every((m) => before.has(m)) || !Object.keys(hosts).every((h) => hitOf("fold", h))) bad.push(`${key}: unfolded, a lane or its fold badge is missing`);
      btn.click(); await tick(); await tick();
      const flow = FlowKit.flowOf(key), after = FlowKit.touchedLanes(flow), merged = flow.steps.filter((x) => x.folded);
      if (members.some((m) => after.has(m))) bad.push(`${key}: a folded lane is still on the stage`);
      if (!merged.length || flow.steps.length > plain.steps.length) bad.push(`${key}: folding merged no steps (${plain.steps.length} to ${flow.steps.length})`);
      seenMerged.push(...merged);
      // numbers kept, in order, nothing lost
      const covered = flow.steps.flatMap((x) => (x.run || [x]).map((y) => y.n));
      if (JSON.stringify(covered) !== JSON.stringify(plain.steps.map((x) => x.n))) bad.push(`${key}: the folded steps lose or reorder a step: ${covered}`);
      for (const m of merged) if (m.run.length > 1 && m.nLabel !== `${m.run[0].n}–${m.run[m.run.length - 1].n}`) bad.push(`${key}: the merged step is called ${m.nLabel}`);
      // open questions stay on the folded step
      const wanted = new Set(plain.steps.flatMap((x) => x.unknowns.map((p) => p.id))), kept = new Set(flow.steps.flatMap((x) => x.unknowns.map((p) => p.id)));
      if ([...wanted].some((id) => !kept.has(id))) bad.push(`${key}: an open question fell off a folded step`);
      const drawnPins = new Set(Flows.player().hits.filter((t) => t.type === "unknown").map((t) => t.id));
      if ([...wanted].some((id) => ASK[id] && !drawnPins.has(id))) bad.push(`${key}: a question is not drawn on the folded stage`);
      if ($("#simplify-btn").getAttribute("aria-pressed") !== "true" || !/^Simplified · \d+ folded$/.test($("#simplify-btn").textContent)) bad.push(`${key}: the button says "${$("#simplify-btn").textContent}"`);
      if (!/fold=/.test(FlowView.hashPart(key)) || $$(".fn-act[aria-pressed=true]").length !== Object.keys(hosts).length) bad.push(`${key}: the address or the list does not show the folds`);
      if (Legend.audit().filter((p) => p.startsWith("flow")).length) bad.push(`${key}: ${Legend.audit()[0]}`);
      const text = textOf(flow);
      for (const m of merged) if (!text.join("").replace(/\s+/g, "").includes(m.say.replace(/\s+/g, ""))) bad.push(`${key}: the folded step's words are cut`);
      if (text.some((t) => /…/.test(t))) bad.push(`${key}: the folded drawing has an ellipsis`);
      // the player and the caption read the merged step
      const at = flow.steps.findIndex((x) => x.folded);
      Flows.player().go(at, { exact: true }); await tick();
      if (!new RegExp(`Step ${FlowKit.stepNo(flow.steps[at])} of ${flow.steps.length}`).test($("#caption").textContent) || !$("#caption").textContent.includes("folded into")) bad.push(`${key}: the caption of a folded step says "${$("#caption").textContent.slice(0, 120)}"`);
      // one click on the badge unfolds the one host
      const host = Object.keys(hosts)[0];
      clickHit(hitOf("fold", host)); await tick();
      if (FlowView.choices(key).folded.has(host) || (Object.keys(hosts).length === 1 && FlowKit.flowOf(key).steps.length !== plain.steps.length)) bad.push(`${key}: the badge did not unfold ${host}`);
      // F toggles them all again
      press("f"); await tick();
      const all = Object.keys(hosts).every((h) => FlowView.choices(key).folded.has(h));
      press("f"); await tick();
      if (all === Object.keys(hosts).every((h) => FlowView.choices(key).folded.has(h))) bad.push(`${key}: F did not toggle Simplify`);
      clean(key);
    }
    ok(!bad.length, `fold: on ${foldable.length} flows Simplify folds every lane that qualifies into one step on its host, keeps the numbers and the open questions, shows in the key and the address, and the badge and F undo it`, `fold: ${bad.slice(0, 6).join("; ")}`);
    ok(seenMerged.length > 0, `fold: ${seenMerged.length} steps were merged`, "fold: nothing merged");
  }

  async function hiding(ok) {
    const f = D.flows.find((x) => FlowKit.touchedLanes(FlowKit.flowOf(x.key)).size >= 3);
    if (!f) return;
    const key = f.key, bad = [];
    clean(key); Nav.open("flows", key); Flows.select(key, -1); await tick();
    const lane = [...FlowKit.touchedLanes(FlowKit.flowOf(key))].sort((a, b) => LANE_INDEX[b] - LANE_INDEX[a])[0];
    moveTo(hitOf("lane", lane)); await tick(); await tick();
    const x = hitOf("hide", lane);
    if (!x) bad.push("the pointer on a name shows no hide button");
    else { clickHit(x); await tick(); await tick(); }
    const flow = FlowKit.flowOf(key), ghost = hitOf("ghost", lane), colW = FlowKit.layout(flow, { x: 0, y: 6, w: 1032, h: 694, s: 1 });
    if (!FlowView.isHidden(key, lane) || !ghost || hitOf("lane", lane)) bad.push("hiding did not leave a ghost chip in place of the name");
    if (!/hide=/.test(FlowView.hashPart(key))) bad.push("the hidden lane is not in the address");
    const narrow = colW.weight.filter((w) => w > 0 && w < 1).length === 1;
    if (!narrow) bad.push("the hidden lane is not a narrow column");
    const text = textOf(flow);
    if (!text.includes("hidden · show")) bad.push("the ghost chip does not say how to show it");
    if (Legend.audit().filter((p) => p.startsWith("flow")).length) bad.push(Legend.audit()[0]);
    // nothing vanishes: every step that touches the hidden lane is still a row
    const touching = flow.steps.filter((s) => s.self === lane || s.messages.some((m) => m.from === lane || m.to === lane)).length;
    const rows = colW.rows.filter((r) => r.si >= 0 && (r.u.lane === lane || (r.u.from === lane || r.u.to === lane))).length;
    if (touching && rows < touching) bad.push(`steps in the hidden lane vanished (${rows} rows for ${touching} steps)`);
    clickHit(ghost); await tick();
    if (FlowView.isHidden(key, lane) || !hitOf("lane", lane)) bad.push("pressing the chip did not show the lane");
    // the list: a button for each, and Delete on a lane's name hides it
    $(".flow-nodes").open = true;
    const name = $$(".fn-lane .flow-node:not(.fn-act)", $(".flow-nodes")).find((b) => b.textContent === titleOf(lane));
    if (!name) bad.push("the list has no button for the lane");
    else { press("Delete", name); await tick(); if (!FlowView.isHidden(key, lane)) bad.push("Delete on the lane's name did not hide it"); }
    const show = $(`.fn-act[aria-label="Show ${titleOf(lane)}"]`);
    if (!show) bad.push("the list has no Show button for the hidden lane"); else { show.click(); await tick(); if (FlowView.isHidden(key, lane)) bad.push("the list's Show did not show it"); }
    clean(key);
    ok(!bad.length, `hide: on ${key}, a lane hides from its name, leaves a narrow dashed column with a chip, keeps every step, rides in the address, and comes back from the chip and from the list`, `hide: ${bad.slice(0, 6).join("; ")}`);
    // the address brings folds and hides back, and another flow does not carry them
    const had = [...HASH.entries()], other = D.flows.find((g) => g.key !== key);
    HASH.set("open", key); HASH.set("hide", lane); Flows.select(key, -1); Nav.open("flows", key); await tick();
    const back = FlowView.isHidden(key, lane);
    for (const k of [...HASH.keys()]) HASH.delete(k);
    had.forEach(([k, v]) => HASH.append(k, v));
    if (other) Flows.select(other.key, -1);
    ok(back && (!other || (!FlowView.isHidden(other.key, lane) && !/hide=/.test(location.hash))), "hide: a link naming a hidden lane opens with it hidden; another flow starts with nothing hidden", `hide: the link gave ${back}`);
    clean(key);
    // a link naming what the flow doesn't have says so, never silently
    const had2 = [...HASH.entries()];
    HASH.set("open", key); HASH.set("fold", "APP-nothing"); HASH.set("start", "S9"); Flows.select(key, -1); Nav.open("flows", key); await tick();
    const line = $("[data-ignored-link]");
    for (const k of [...HASH.keys()]) HASH.delete(k);
    had2.forEach(([k, v]) => HASH.append(k, v));
    ok(!!line && /folding/.test(line.textContent) && /doesn't have any more/.test(line.textContent), "address: a link that names a fold or a start the flow doesn't have says so on the page", `address: the link's ignored words say "${line && line.textContent}"`);
    clean(key);
  }

  async function fitting(ok) {
    const was = Theme.id, fx = FX.on, problems = [];
    const keys = D.flows.filter((f) => f.starts || Object.keys(FlowView.hostsOf(f.key)).length).slice(0, 4).map((f) => f.key);
    for (const [id, label, motion] of [...Theme.LIST.map((t) => [t.id, t.label, true]), [was, "Plain", false]]) {
      Theme.set(id); FX.set(motion);
      for (const key of keys) {
        Nav.open("flows", key); Flows.select(key, -1); await tick();
        if ($("#simplify-btn")) { $("#simplify-btn").click(); await tick(); }
        for (const b of [...TextFit.textFits($(".flows-head")), ...TextFit.clippedText($(".flows-head"))]) problems.push(`${label}, ${key}: "${b.text}" ${b.why}`);
        clean(key);
      }
    }
    Theme.set(was); FX.set(fx);
    ok(!problems.length, `flows: the Starts from picker and Simplify fit the header row in every theme and in Plain (${keys.length} flows)`, `flows: ${problems.slice(0, 6).join(" | ")}`);
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try {
      if (D.flows.length) {
        showView("flows");
        for (const part of [pinned, starts, folding, hiding, fitting]) await part(ok);
      }
    } catch (e) { lines.push("FAIL the flow view checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the flow view checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
