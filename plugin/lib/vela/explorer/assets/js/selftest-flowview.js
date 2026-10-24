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
    for (const g of FlowView.groupsFor(key)) FlowView.ungroup(key, g.id);  // a flow that opens grouped (its page's boxes) is drawn lane by lane for the checks that count lanes
  }
  const rowKinds = (flow) => FlowKit.layout(flow, { x: 0, y: 6, w: 1032, h: 694, s: 1 }).rows.map((r) => r.u.kind);

  async function pinned(ok) {
    const f = D.flows.slice().sort((a, b) => b.steps.length - a.steps.length)[0];
    Nav.open("flows", f.key); Flows.select(f.key, -1); await tick();
    const stage = $(".stage"), keep = [stage.style.flex, stage.style.height, stage.style.minHeight];
    stage.style.flex = "none"; stage.style.height = "120px"; stage.style.minHeight = "0"; await tick(); await tick();
    const scrollable = stage.scrollHeight > stage.clientHeight + 40;
    ok(scrollable, `pin: a short stage makes ${f.key} scroll`, `pin: the stage did not scroll (${stage.scrollHeight} in ${stage.clientHeight})`);
    const lane0 = hitOf("lane"), top0 = lane0 ? lane0.y : -1;
    stage.scrollTop = 180; await tick(); await tick();
    const lane1 = hitOf("lane"), under = Flows.player().hits.filter((t) => !["lane", "fold", "hide", "ghost", "starttag"].includes(t.type) && t.y + t.h <= stage.scrollTop + lane1.h);
    const offset = stage.getBoundingClientRect().top - stageGeom().rect.top;  // how far the canvas has scrolled past the top of the room
    ok(!!lane0 && !!lane1 && Math.abs(lane1.y - lane0.y - offset) < 3 && offset > 50, `pin: scrolled ${Math.round(offset)} px, the lane names stay at the top of the room (hit moved ${Math.round(lane1.y - lane0.y)} px)`,
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
      ok(back === second.id && (!elsewhere || (!/start=/.test(FlowView.hashPart(elsewhere.key)) && !/start=/.test(location.hash))), `starts, ${key}: a link naming the start opens with it picked; another flow starts clean`, `starts, ${key}: the link opened with ${back}; the other flow's address "${elsewhere && FlowView.hashPart(elsewhere.key)}" and "${location.hash}"`);
      clean(key);
    }
  }

  async function folding(ok) {
    const foldable = D.flows.filter((f) => Object.keys(FlowView.hostsOf(f.key)).length);
    if (!foldable.length) return;
    const bad = [], seenMerged = [];
    for (const f of foldable) {
      const key = f.key;
      Nav.open("flows", key); Flows.select(key, -1); await tick(); await tick();
      clean(key); await tick();  // a flow that opens grouped is checked lane by lane: what folds is worked out on the lanes as they are
      const hosts = FlowView.hostsOf(key), plain = FlowKit.flowOf(key, { plain: true });
      if (!Object.keys(hosts).length) continue;
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
    clean(key); await tick();  // opening the flow read its address again, which may bring back what its page groups
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
    if (!name) bad.push(`the list has no button for the lane ${lane}/${titleOf(lane)}: ${$$(".fn-lane .flow-node:not(.fn-act)", $(".flow-nodes")).map((b) => b.textContent).join("|")}`);
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


  /* ---------- lane groups: written on the flow page with `box`, made and taken apart by the reader, drawn as lanes of their own */
  const WEB = "APP-website", DESK = "APP-call-center", KIOSK = "APP-kiosks", BOOK = "APP-booking", PRICE = "APP-pricing", CUST = "APP-customer-identity", SCHED = "APP-vessel-schedule";
  const forgetGroups = () => { try { localStorage.removeItem(`explorer.lanegroups.${D.vaultId}`); } catch (e) { console.warn("[selftest] this browser keeps nothing, so no saved lane groups to clear:", e.message); } };
  async function reopen(key, extra = {}) {  // the way a pasted link or Back opens a flow: the address names what it names
    for (const step of [{ apart: "~" }, extra]) {
      for (const k of [...HASH.keys()]) HASH.delete(k);
      HASH.set("open", key); for (const [k, v] of Object.entries(step)) HASH.set(k, v);
      Flows.select(key, -1); Nav.open("flows", key); await tick();
    }
    FlowKit.flowOf(key);
  }
  /* A flow written for the check: three channels, Booking and Pricing, with the steps that make a group interesting. */
  function synthetic() {
    const msg = (from, to, contract = "CON-001", says = "hold a seat") => ({ from, to, contract, direction: "stated", kind: "send", says, answer: "" });
    const pin = D.asks.length ? [{ id: D.asks[0].id, why: "cited", textSaysOpen: false }] : [];
    const step = (n, messages, o = {}) => ({ n, html: `step ${n}`, text: `Step ${n} happens.`, short: `Step ${n} happens`, says: `step ${n} happens`, messages, self: null, recordsPair: true, lanesNamed: 0, unrecorded: false, ref: null, unknowns: [],
      contracts: [], linked: [], named: [], fromTable: false, start: "", ...o });
    FLOW["FLO-GROUPS"] = { key: "FLO-GROUPS", id: "FLO-GROUPS", steps: [
      step(1, [msg(WEB, BOOK)]), step(2, [msg(BOOK, PRICE, "CON-003", "price it")]),
      step(3, [msg(DESK, KIOSK, "", "hand the hold over")], { unknowns: pin }), step(4, [msg(KIOSK, DESK, "", "hand it back")], { unknowns: pin }),
      step(5, [msg(WEB, DESK, "", "pass a note")], { start: "S1" }), step(6, [msg(DESK, WEB, "", "pass it on")], { start: "S2" }),
      step(7, [msg(BOOK, WEB, "CON-001", "confirm"), msg(BOOK, DESK, "CON-001", "confirm"), msg(BOOK, KIOSK, "CON-001", "confirm"), msg(KIOSK, DESK, "", "tell the desk")]),
      step(8, [], { self: WEB })], unknowns: [], groups: [{ name: "Channels", lanes: [WEB, DESK, KIOSK] }] };
    E["FLO-GROUPS"] = { id: "FLO-GROUPS", title: "Groups flow", state: "", key: "FLO-GROUPS" };
    return "FLO-GROUPS";
  }

  async function grouping(ok) {
    const f1 = D.flows.find((f) => f.key === "FLO-001" && (f.groups || []).length === 2);
    if (!f1) { console.warn("[selftest] groups skipped: no FLO-001 with two page groups in this vault"); return; }
    const key = f1.key, bad = [];
    // opens grouped: the page's two boxes are two lanes, six lanes where there were ten, the step numbers unchanged
    await reopen(key);
    const plain = FlowKit.flowOf(key, { plain: true }), flow = FlowKit.flowOf(key), names = flow.view.laneGroups.map((g) => g.name);
    if (JSON.stringify(names) !== JSON.stringify(["Channels", "Lookups"])) bad.push(`opens with ${names}`);
    const drawn = flow.view.lanes.filter((l) => FlowKit.touchedLanes(flow).has(l.id)), was = FlowKit.touchedLanes(plain);
    if (drawn.length !== was.size - 4 || was.size < 8) bad.push(`${was.size} lanes became ${drawn.length}`);
    if (JSON.stringify(flow.steps.map((x) => x.n)) !== JSON.stringify(plain.steps.map((x) => x.n))) bad.push("a step number changed");
    if (!$("#group-btn") || $("#group-btn").textContent !== "Grouped · 2" || $("#group-btn").getAttribute("aria-label") !== "Grouped, 2 groups") bad.push(`the header button says "${$("#group-btn") && $("#group-btn").textContent}"`);
    // the same arrows become one that says who it stands for; different contracts stay separate
    const all3 = flow.steps.flatMap((x) => x.messages).filter((m) => (m.groupEnds || []).some((e) => e.all && e.members.length === 3));
    if (all3.length !== 1 || plain.steps.flatMap((x) => x.messages).filter((m) => [WEB, DESK, KIOSK].includes(m.from) && m.contract === "CON-001" && m.kind === "send").length !== 3) bad.push(`the three channels' arrows became ${all3.length}`);
    const lookups = flow.steps.find((x) => x.messages.filter((m) => m.to === "grp:lookups").length > 1);
    if (!lookups || new Set(lookups.messages.filter((m) => m.to === "grp:lookups").map((m) => m.contract)).size !== lookups.messages.filter((m) => m.to === "grp:lookups").length) bad.push("arrows with different contracts to Lookups were merged");
    const words = textOf(flow).join(" | ");
    if (!/from all 3 in Channels/.test(words) || !/to Vessel schedule/.test(words) || !/group of 3/.test(words)) bad.push(`the drawing says "${words.slice(0, 160)}"`);
    if (Legend.audit().filter((p) => p.startsWith("flow")).length) bad.push(Legend.audit()[0]);
    // the Start tag sits on the group; Starts from still names each start; picking one still dims the other's steps
    const tag = hitOf("starttag");
    if (!tag || tag.lane !== "grp:channels" || tag.ids.length !== 3 || !textOf(flow).includes("3 STARTS")) bad.push("the Start tag is not on the Channels group");
    if ($$("[data-starts] [role=radio]").length !== f1.starts.options.length + 1) bad.push("Starts from changed");
    FlowView.setStart(key, "S2"); await tick();
    if (FlowKit.flowOf(key).steps.filter((x) => FlowView.dimmedStep(key, x)).length !== f1.starts.options[0].steps.length + f1.starts.options[2].steps.length) bad.push("picking a start did not dim the others");
    FlowView.setStart(key, "all"); await tick();
    ok(!bad.length, `groups: ${key} opens with its page's Channels and Lookups, ${was.size} lanes drawn as ${drawn.length}, step numbers kept, the same arrows merged ("from all 3 in Channels"), starts working`, `groups: ${bad.slice(0, 6).join("; ")}`);

    // ungroup rides in the address (apart=), and a link with lanes= wins over the page's
    bad.length = 0;
    FlowView.ungroup(key, "grp:channels"); await tick();
    if (FlowView.hashPart(key) !== "&apart=Channels" || FlowView.groupsFor(key).length !== 1) bad.push(`ungroup wrote "${FlowView.hashPart(key)}"`);
    if ($("#group-btn").textContent !== "Grouped · 1") bad.push("the button did not follow");
    await reopen(key, { apart: "Channels" });
    if (FlowView.groupsFor(key).map((g) => g.name).join() !== "Lookups") bad.push("a link naming ungroup did not open ungrouped");
    await reopen(key, { lanes: `${encodeURIComponent("Ferry, lanes: two")}:${KIOSK},${WEB}`, apart: "Lookups" });
    const link = FlowView.groupsFor(key);
    if (link.length !== 1 || link[0].name !== "Ferry, lanes: two" || link[0].id !== "grp:ferry-lanes-two" || !/^&lanes=/.test(FlowView.hashPart(key)) || /apart/.test(FlowView.hashPart(key))) bad.push(`a link's group gave ${JSON.stringify(link)} and "${FlowView.hashPart(key)}"`);
    if (!FlowView.hashPart(key).startsWith("&lanes=Ferry%252C%2520lanes%253A%2520two%3AAPP-")) bad.push(`the name is not in the address: ${FlowView.hashPart(key)}`);
    // fold and hide name the group by its ID
    FlowView.hide(key, "grp:ferry-lanes-two"); await tick();
    if (!FlowKit.flowOf(key).view.hidden.has("grp:ferry-lanes-two") || !hitOf("ghost", "grp:ferry-lanes-two") || !textOf(FlowKit.flowOf(key)).includes("hidden · show")) bad.push("a hidden group is not a ghost chip");
    FlowView.show(key, "grp:ferry-lanes-two");
    // a link that cannot be honored is drawn as far as it can be, and says the rest
    await reopen(key, { lanes: `Channels:${WEB},${DESK},APP-nowhere;One:${PRICE};Both:${WEB},${CUST},${SCHED}` });
    const said = FlowKit.flowOf(key).view.said.join(" ");
    if (FlowView.groupsFor(key).map((g) => g.name).join() !== "Channels,Both" || !/APP-nowhere, which isn't in this flow/.test(said) || !/One has fewer than two lanes/.test(said)
      || !/puts Public website in two groups, so Both doesn't take it/.test(said)) bad.push(`an impossible link gave ${FlowView.groupsFor(key).map((g) => g.name)} and "${said}"`);
    if (!/which isn't in this flow/.test($("#caption").textContent)) bad.push("the page does not say what the link asked for");
    ok(!bad.length, "groups: ungroup rides in the address, a link's lanes= wins over the page's, names with commas and colons survive, a hidden group is a chip, an impossible link is drawn as far as it can be and says the rest", `groups: ${bad.slice(0, 6).join("; ")}`);

    // a name with , : ; and % survives the real address: written by hashPart, read back by URLSearchParams after a reload; a hand-typed % never throws
    bad.length = 0;
    for (const name of ["Ops: back, office", "50% off; today", "100%", "Plain"]) {
      await reopen(key, { apart: "Channels,Lookups" });
      FlowView.makeGroup(key, name, [KIOSK, WEB]); await tick();
      const wrote = FlowView.hashPart(key), addr = "#flows&open=" + encodeURIComponent(key) + wrote;  // the address Flows.select writes
      await reopen(key, { apart: "Channels,Lookups" });
      for (const k of [...HASH.keys()]) HASH.delete(k);
      new URLSearchParams(addr.slice(1)).forEach((v, k) => HASH.append(k, v)); FlowKit.flowOf(key);  // a reload: HASH is made from the address text, the one decode
      const back = FlowView.groupsFor(key).find((g) => g.members.includes(KIOSK));
      if (!back || back.name !== name || back.members.length !== 2) bad.push(`"${name}" came back as ${JSON.stringify(back && back.name)} from ${addr}`);
      if (FlowView.hashPart(key) !== wrote) bad.push(`"${name}" was written ${wrote} and again ${FlowView.hashPart(key)}`);
    }
    const errs = window.__errors.length;
    await reopen(key, { lanes: `50%off:${KIOSK},${WEB}` });
    if (window.__errors.length !== errs || FlowView.groupsFor(key).map((g) => g.name).join() !== "50%off") bad.push(`a hand-typed 50%off gave ${FlowView.groupsFor(key).map((g) => g.name)} and ${window.__errors.slice(errs)}`);
    // the map's own group= is not ours: a flows link carrying it neither makes groups here nor breaks the map
    await reopen(key, { group: "Channels:APP-website,APP-call-center" });
    if (FlowView.groupsFor(key).map((g) => g.name).join() !== "Channels,Lookups") bad.push("a map group= changed this flow's groups");
    ok(!bad.length, "groups: a name with , : ; and % round-trips through the real address, and a map group= is left alone", `groups: ${bad.slice(0, 6).join("; ")}`);

    // a group cannot be renamed to a name another group has (Ungroup would take both); the page's own unmakeable boxes are said
    bad.length = 0;
    await reopen(key);
    const before = FlowView.groupsFor(key).map((g) => g.name).join();
    const refused = FlowView.renameGroup(key, "grp:lookups", "Channels");
    if (!/already a group called Channels/.test(refused) || FlowView.groupsFor(key).map((g) => g.name).join() !== before) bad.push(`renaming to a taken name gave "${refused}" and ${FlowView.groupsFor(key).map((g) => g.name)}`);
    if (FlowView.renameGroup(key, "grp:lookups", "Lookups 2") !== "" || FlowView.groupsFor(key).map((g) => g.name).join() !== "Channels,Lookups 2") bad.push("a free name was refused");
    FlowView.ungroup(key, "grp:channels"); await tick();
    if (FlowView.groupsFor(key).map((g) => g.name).join() !== "Lookups 2") bad.push(`Ungroup took ${FlowView.groupsFor(key).map((g) => g.name)} with it`);
    FLOW[key].groupNotes = ["The box Odd has fewer than two lanes, so it is not drawn as a group."];
    await reopen(key);
    if (!FlowKit.flowOf(key).view.said.includes(FLOW[key].groupNotes[0]) || !$("#caption").textContent.includes("The box Odd has fewer than two lanes")) bad.push("a box the build could not draw is not said on the flow");
    delete FLOW[key].groupNotes; forgetGroups(); await reopen(key);
    ok(!bad.length, "groups: renaming to another group's name is refused in plain words, and a page box that cannot be drawn is said on the flow", `groups: ${bad.slice(0, 6).join("; ")}`);

    // fold works on the grouped flow; grouping a folded or hidden lane clears that choice and says so
    bad.length = 0;
    const f10 = D.flows.find((f) => f.key === "FLO-010");
    if (f10) {
      const fk = f10.key, NOTIFY = "APP-notifications";
      await reopen(fk);
      FlowView.simplify(fk); await tick();
      FlowView.hide(fk, NOTIFY); await tick();
      const was2 = [...FlowView.choices(fk).folded];
      FlowView.makeGroup(fk, "Back end", [PRICE, NOTIFY]); await tick();
      const told = $("#toast").textContent;
      if (!was2.length || FlowView.choices(fk).folded.size || FlowView.isHidden(fk, NOTIFY) || !/Unfolded Pricing to group it/.test(told) || !/Showed Notifications to group it/.test(told)) bad.push(`grouping left folded=${[...FlowView.choices(fk).folded]} hidden=${FlowView.isHidden(fk, NOTIFY)} and said "${told}"`);
      const hosts = FlowView.hostsOf(fk);
      if (JSON.stringify(hosts[BOOK]) !== JSON.stringify(["grp:back-end"])) bad.push(`the group is not offered to fold into Booking: ${JSON.stringify(hosts)}`);
      FlowView.simplify(fk); await tick();
      const folded = FlowKit.flowOf(fk);
      if (!folded.steps.some((x) => x.folded && (x.via || []).includes("Back end")) || FlowKit.touchedLanes(folded).has("grp:back-end") || !hitOf("lane", BOOK)) bad.push("Simplify did not fold the Back end group into Booking");
      FlowView.ungroup(fk, "grp:back-end"); await tick();
      if (FlowView.choices(fk).folded.size || !/Unfolded Back end to ungroup it/.test($("#toast").textContent)) bad.push(`ungrouping a folded group said "${$("#toast").textContent}"`);
      forgetGroups();
      await reopen(fk);
    }
    ok(!bad.length, "groups: a group can host a fold and Simplify folds what the grouped flow allows; grouping a folded or hidden lane clears that choice and says so", `groups: ${bad.slice(0, 6).join("; ")}`);

    // the picker: G opens it, Esc closes it and focus goes back, Group these needs two lanes and not every lane
    bad.length = 0;
    await reopen(key, { apart: "Channels,Lookups" });
    $("#group-btn").focus(); press("g"); await tick();
    const dlg = $("[data-group-picker]");
    if (!dlg || dlg.getAttribute("role") !== "dialog" || !dlg.contains(document.activeElement)) bad.push("G did not open the picker with focus inside it");
    const go = () => $("#gp-go"), boxes = () => $$("#group-picker input[type=checkbox]:not(:disabled)");
    const tick1 = (b) => { b.checked = !b.checked; b.dispatchEvent(new Event("change", { bubbles: true })); };
    if (!go().disabled) bad.push("Group these is enabled with nothing checked");
    tick1(boxes()[0]); if (!go().disabled) bad.push("Group these is enabled with one lane checked");
    tick1(boxes()[1]); if (go().disabled || go().textContent !== "Group these 2") bad.push(`Group these says "${go().textContent}" with two`);
    boxes().slice(2).forEach((b) => { if (!b.checked) tick1(b); });
    if (!go().disabled || !/Leave at least one lane out/.test($(".gp-warn").textContent)) bad.push("every lane checked still lets the group be made");
    press("Escape", dlg); await tick();
    if ($("[data-group-picker]") || document.activeElement !== $("#group-btn")) bad.push(`Esc left the picker or its focus: ${document.activeElement && document.activeElement.id}`);
    // the picker makes the group with the name typed, and takes a suggestion
    const domains = { ...D.domains };  // the plan's own business areas stay as they were; the check borrows two lanes for one of its own
    for (const id of Object.keys(D.domains)) D.domains[id] = "No domain";
    D.domains[PRICE] = "Quote desk"; D.domains[CUST] = "Quote desk";
    const offered = FlowView.suggestions(key).map((g) => g.name + ":" + g.why);
    D.domains[CUST] = "No domain";
    const one = FlowView.suggestions(key).some((g) => g.name === "Quote desk");
    D.domains[CUST] = "Quote desk";
    if (JSON.stringify(offered) !== JSON.stringify(["Quote desk:business area on the map"]) || one) bad.push(`suggestions from the map gave ${offered} and ${one} with one lane`);
    press("g"); await tick();
    const sugg = $("[data-suggest]"); if (!sugg) bad.push("no suggestion in the picker"); else { sugg.click(); await tick(); }
    if (!sugg || go().disabled || $("#gp-name").value !== "Quote desk" || go().textContent !== "Group these 2") bad.push("taking a suggestion did not fill the checkboxes and the name");
    go().click(); await tick();
    Object.assign(D.domains, domains);
    if (FlowView.groupsFor(key).map((g) => g.name).join() !== "Quote desk" || $("[data-group-picker]") || !/^&lanes=Quote%2520desk/.test(FlowView.hashPart(key)) || document.activeElement !== $("#group-btn")) bad.push(`the picker made ${FlowView.groupsFor(key).map((g) => g.name)}, address ${FlowView.hashPart(key)}`);
    // a group made here is offered on another flow, never applied
    const other = D.flows.find((g) => g.key !== key && FlowKit.touchedLanes(FlowKit.flowOf(g.key, { plain: true })).has(PRICE) && FlowKit.touchedLanes(FlowKit.flowOf(g.key, { plain: true })).has(CUST));
    if (other) {
      await reopen(other.key);
      const more = FlowView.suggestions(other.key).find((g) => g.name === "Quote desk");
      if (!more || !/^made on /.test(more.why) || FlowView.groupsFor(other.key).some((g) => g.name === "Quote desk")) bad.push(`another flow was not offered the group: ${JSON.stringify(more)}`);
    }
    forgetGroups();
    ok(!bad.length, "groups: G opens the picker and Esc closes it with focus back on the button, Group these needs two lanes and not every lane, a suggestion fills it in, the group rides in the address, and a group made on one flow is offered on another, never applied", `groups: ${bad.slice(0, 6).join("; ")}`);

    // the panel and the list: a click on the group's pill opens its panel and a second click puts it down; the list is the keyboard path
    bad.length = 0;
    await reopen(key);
    const pill = hitOf("lane", "grp:channels");
    if (!pill) bad.push("no group pill on the stage");
    else {
      clickHit(pill); await tick();
      if (App.trail[App.trail.length - 1] !== "grp:channels" || !/Group/.test($("#panel-body").textContent) || !/A group the flow page writes/.test($("#panel-body").textContent) || !/Rename/.test($("#panel-body").textContent)) bad.push(`the pill opened "${App.trail}" and "${$("#panel-body").textContent.slice(0, 80)}"`);
      clickHit(hitOf("lane", "grp:channels")); await tick();
      if (App.trail.length) bad.push(`a second click left ${App.trail}`);
    }
    $(".flow-nodes").open = true;
    const row = $(".fn-group-row"), name = row && $(".flow-node:not(.fn-act)", row);
    if (!row || !/^Channels, group of 3$/.test(name.textContent) || !$$(".fn-members .flow-node").some((b) => b.textContent === "Port kiosks")) bad.push("the list has no Channels row with its members");
    else {
      name.click(); await tick(); if (App.trail[App.trail.length - 1] !== "grp:channels") bad.push("the list row did not open the group's panel");
      name.click(); await tick(); if (App.trail.length) bad.push("a second press on the list row did not put the group down");
      press("Delete", name); await tick();
      if (!FlowView.isHidden(key, "grp:channels") || !$(`.fn-act[aria-label="Show Channels"]`)) bad.push("Delete on the row did not hide the group");
      $(`.fn-act[aria-label="Show Channels"]`).click(); await tick();
      $(`.fn-act[aria-label="Ungroup Channels"]`).click(); await tick();
      if (FlowView.groupsFor(key).some((g) => g.name === "Channels") || !$(`.fn-lane .flow-node[aria-label="Hide Public website"]`)) bad.push("Ungroup in the list did not take Channels apart and give its lanes their Hide buttons back");
    }
    // rename from the panel
    await reopen(key);
    DetailsPanel.show("grp:lookups", { reset: true }); await tick();
    const renamer = $$("#panel-body button").find((b) => b.textContent === "Rename"); if (renamer) renamer.click();
    const field = $("#panel-body .gp-rename input");
    if (!field) bad.push("Rename opened no field"); else { field.value = "Back end"; press("Enter", field); await tick(); }
    if (!FlowView.groupsFor(key).some((g) => g.name === "Back end" && g.id === "grp:back-end") || !textOf(FlowKit.flowOf(key)).includes("Back end")) bad.push("rename did not rename the lane");
    DetailsPanel.clear();
    ok(!bad.length, "groups: a click on a group's pill opens its panel and a second click puts it down; the list has a row for each group with Ungroup and Hide, Delete hides it, members stay buttons; Rename works from the panel", `groups: ${bad.slice(0, 6).join("; ")}`);

    // present mode draws the groups and carries what the reader did; the saved clip is the whole flow and says so
    bad.length = 0;
    await reopen(key);
    FlowView.ungroup(key, "grp:channels"); await tick();
    Flows.present(key, 0); await tick();
    const pf = FlowKit.flowOf(key);
    if (!$("#overlay").classList.contains("present") || !Flows.presenter() || FlowView.hashPart(key) !== "&apart=Channels" || pf.view.laneGroups.map((g) => g.name).join() !== "Lookups") bad.push(`present: ${FlowView.hashPart(key)}`);
    Flows.closePresent();
    const clip = FlowKit.flowOf(key, { plain: true });
    if (clip.view || clip.steps.length !== plain.steps.length || FlowKit.drawnClip(clip).some((t) => /group of|Lookups/.test(t)) || !/without your groups/.test(Flows.clipNote())) bad.push("the clip is not the whole flow without groups");
    ok(!bad.length, "groups: present mode draws the groups and its address carries what the reader did; Save as video records the whole flow and says it is without your groups", `groups: ${bad.slice(0, 6).join("; ")}`);

    // traffic inside a group: one beat with the numbers kept, the open questions kept, never across a start; a mixed step keeps its arrows and adds the beat
    bad.length = 0;
    const syn = synthetic();
    const sf = FlowKit.flowOf(syn), sp = FlowKit.flowOf(syn, { plain: true });
    const nos = sf.steps.map((x) => x.nLabel || String(x.n));
    const inner = sf.steps.find((x) => x.grouped && x.run.length === 2);
    if (JSON.stringify(nos) !== JSON.stringify(["1", "2", "3–4", "5", "6", "7", "8"])) bad.push(`steps read ${nos}`);
    if (!inner || !/^inside Channels: .* · 2 steps in one$/.test(inner.viaText) || inner.unknowns.length !== (sp.steps[2].unknowns.length ? 1 : 0)) bad.push(`the beat is ${inner && inner.viaText}`);
    if (sf.steps.filter((x) => x.grouped).map((x) => x.nLabel || x.n).join() !== "3–4,5,6,8") bad.push("a beat crossed a start, or a step that stays inside was left out");
    const mixed = sf.steps.find((x) => x.n === 7);
    if (!mixed || mixed.messages.length !== 1 || !mixed.inside || mixed.inside[0].via !== "inside Channels: Port kiosks to Call center desktop" || FlowKit.unitsOf(mixed).map((u) => u.kind).join() !== "msg,folded") bad.push("a step with arrows and inside traffic lost one of them");
    const lonely = sf.steps.find((x) => x.n === 8);
    if (!lonely || lonely.viaText !== "in Public website") bad.push(`a step on one member says "${lonely && lonely.viaText}"`);
    const said2 = textOf(sf).join(" | ");
    if (!/inside Channels: .* · 2 steps in one/.test(said2) || !/to all 3 in Channels/.test(said2)) bad.push(`the drawing says "${said2.slice(0, 200)}"`);
    delete FLOW[syn]; delete E[syn];
    ok(!bad.length, "groups: traffic inside a group is one card on its lane with the step numbers kept (3–4, 2 steps in one), its open questions kept, never merged across a start; a step with arrows and inside traffic keeps both; one member's step says which", `groups: ${bad.slice(0, 6).join("; ")}`);

    // no overlaps and nothing off the stage, grouped, at both widths
    bad.length = 0;
    await reopen(key);
    for (const w of [1040, 800]) {
      const g = FlowKit.flowOf(key), G = FlowKit.layout(g, { x: 0, y: 6, w: w - 8, h: 694, s: clamp(w / 1040, 0.8, 1.2) }), hits = FlowKit.drawScene(SCRATCH.getContext("2d"), G, { cur: -1, tau: 99, clock: 0, D: 0.8, images: false });
      const pills = hits.filter((t) => t.type === "lane").sort((a, b) => a.x - b.x);
      for (let i = 1; i < pills.length; i++) if (pills[i].x < pills[i - 1].x + pills[i - 1].w - 0.5) bad.push(`${w}: ${pills[i - 1].id} and ${pills[i].id} overlap`);
      for (const t of hits) if (t.x < -1 || t.x + t.w > w + 1) bad.push(`${w}: a ${t.type} runs off the stage`);
    }
    ok(!bad.length, "groups: with both groups on, the lane names do not overlap and nothing is off the stage at 1040 and at 800 wide", `groups: ${bad.slice(0, 4).join("; ")}`);
    await reopen(key);
  }


  /* What an arrow says once, and where lanes stand: the pill that names a contract is not said again under the arrow, a short pill is one line,
     and the first lane is the first actor (where the flow starts, then the order the steps reach each lane). */
  async function arrowsAndLanes(ok) {
    const bad = [];
    let chips = 0, said = 0;
    for (const f of D.flows) {
      const flow = FlowKit.flowOf(f.key, { plain: true }), norm = (t) => String(t).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
      for (const w of [1040, 800]) {
        const G = FlowKit.layout(flow, { x: 0, y: 6, w: w - 8, h: 694, s: clamp(w / 1040, 0.8, 1.2) });
        for (const r of G.rows) {
          if (!r.chip) continue;
          chips++;
          const title = r.chip.con.title;
          if (r.lines.length && norm(r.lines.join(" ")) === norm(title)) bad.push(`${f.key}: "${title}" is said on the pill and again under the arrow`);
          if (r.lines.length) said++;
          if (title.length <= 28 && r.chip.lines.length > 1) bad.push(`${f.key} at ${w}: the pill "${title}" wraps to ${r.chip.lines.length} lines`);
        }
      }
      const order = FlowKit.laneOrder(flow), first = f.starts ? f.starts.options[0].lane : flow.steps.map((x) => (x.messages[0] ? x.messages[0].from : x.self)).find(Boolean);
      if (order[0] !== first) bad.push(`${f.key}: the first lane is ${order[0]}, the first actor is ${first}`);
      if (f.starts && JSON.stringify(order.slice(0, f.starts.options.length)) !== JSON.stringify(f.starts.options.map((o) => o.lane))) bad.push(`${f.key}: the start lanes are not first, in start order`);
      const at = (id) => flow.steps.findIndex((x) => x.messages.some((m) => m.from === id || m.to === id) || x.self === id);
      const reached = order.filter((id) => !(f.starts && f.starts.options.some((o) => o.lane === id)));
      if (reached.some((id, i) => i && at(id) < at(reached[i - 1]))) bad.push(`${f.key}: a lane stands left of one the steps reach earlier`);
    }
    ok(!bad.length && chips > 0, `arrows: across ${D.flows.length} flows no pill's title is said again under its arrow, a short title is one line on a short arrow, and lanes stand in the order the flow reaches them (start lanes first)`, `arrows: ${bad.slice(0, 5).join("; ") || "no pills at all"}`);
  }

  /* The words that fit: "Grouped · 2" in the header row in every theme and in Plain. */
  async function groupFits(ok) {
    const f1 = D.flows.find((f) => f.key === "FLO-001" && (f.groups || []).length === 2);
    if (!f1) { console.warn("[selftest] groups skipped: no FLO-001 with two page groups in this vault"); return; }
    const was = Theme.id, fx = FX.on, problems = [];
    for (const [id, label, motion] of [...Theme.LIST.map((t) => [t.id, t.label, true]), [was, "Plain", false]]) {
      Theme.set(id); FX.set(motion);
      await reopen(f1.key);
      if ($("#simplify-btn")) { $("#simplify-btn").click(); await tick(); }
      if (!/Grouped/.test($("#group-btn").textContent)) problems.push(`${label}: ${$("#group-btn").textContent}`);
      for (const b of [...TextFit.textFits($(".flows-head")), ...TextFit.clippedText($(".flows-head"))]) problems.push(`${label}: "${b.text}" ${b.why}`);
    }
    Theme.set(was); FX.set(fx); await reopen(f1.key);
    ok(!problems.length, "groups: the Group button, Starts from and Simplify fit the header row in every theme and in Plain with the groups on", `groups: ${problems.slice(0, 6).join(" | ")}`);
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try {
      if (D.flows.length) {
        showView("flows");
        const hadHash = [...HASH.entries()];
        for (const part of [pinned, starts, folding, hiding, fitting, grouping, groupFits, arrowsAndLanes]) await part(ok);
        for (const k of [...HASH.keys()]) HASH.delete(k);
        hadHash.forEach(([k, v]) => HASH.append(k, v));
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
