/* ------------------------------------------------------------ Zoom and pan on every drawing (pan.js)
   One list of the drawings the dashboard draws, each opened the way a reader opens it. Every one must carry the same
   zoom bar (-, Fit, +) and answer the same gestures: the buttons, the wheel, a pinch (fitted drawings), the keys
   + - 0 and the arrows, and a drag that pans without picking anything. The flow canvas keeps its own controls and is not here. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const mouse = (type, x, y) => new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, buttons: 1, isPrimary: true, pointerId: 31, pointerType: "mouse" });
  const touch = (type, id, x, y) => new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, isPrimary: id === 41, pointerId: id, pointerType: "touch" });
  const press = (el, k) => el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  const wheel = (el, dy, mods = {}) => { const e = new WheelEvent("wheel", { bubbles: true, cancelable: true, clientX: 0, clientY: 0, deltaY: dy, ...mods }); el.dispatchEvent(e); return e.defaultPrevented; };
  const vbox = (svg) => svg.getAttribute("viewBox").split(/\s+/).map(Number);
  /* how much bigger than fitted the drawing is: the viewBox's zoom, or for a drawing that sizes itself its own scale */
  const magnification = (holder) => (holder.__pan.own ? +holder.dataset.scale : Pan.view(holder.__pan.key).z);
  const barOf = (holder) => $$(".zoom-bar").find((b) => b.dataset.for === holder.__pan.key && b.closest(".zoom-frame").contains(holder.__pan.svg()));
  const button = (bar, title) => [...$$("button", bar)].find((b) => b.getAttribute("aria-label").startsWith(title));
  /* a point on the drawing's empty background, where a press means pan */
  function backdrop(svg, holder) {
    holder.scrollIntoView({ block: "nearest" });
    const a = svg.getBoundingClientRect(), b = holder.getBoundingClientRect();
    // inset on the left and top: the drag below ends 40 and 30 pixels up and left of where it starts, and must end inside the drawing
    const left = Math.max(a.left, b.left + 50, 0), right = Math.min(a.right, b.right, innerWidth), top = Math.max(a.top, b.top + 40, 0), bottom = Math.min(a.bottom, b.bottom, innerHeight);
    for (let fy = 0.02; fy < 1; fy += 0.04) for (let fx = 0.02; fx < 1; fx += 0.04) {
      const x = left + (right - left) * fx, y = top + (bottom - top) * fy, el = document.elementFromPoint(x, y);
      if (el && svg.contains(el) && !el.closest("g[tabindex], g.hit, g[role], a, button, [data-movable]")) return { x, y };
    }
    return null;
  }

  /* The words a <text> draws itself (its tspans, not the <title> hover text inside it). */
  const drawnWords = (el) => [...el.childNodes].filter((n) => n.nodeType === 3 || n.localName === "tspan").map((n) => n.textContent).join("");
  /* No label on a drawing is cut short with an ellipsis: a long name wraps, shrinks to a floor, or grows its box. */
  function noCutLabels(ok, name, svg) {
    const cut = $$("text", svg).map(drawnWords).filter((w) => /…\s*$/.test(w));
    ok(!cut.length, `zoom, ${name}: no drawn label ends in an ellipsis`, `zoom, ${name}: cut labels: ${cut.slice(0, 4).join(" | ")}`);
  }
  const NODES = ".hit, g.station, .rl-node, .plan-node, .in-node";
  const centerOf = (r) => ({ x: r.left + r.width / 2, y: r.top + r.height / 2 });
  /* The drawing's viewport is its whole container, and zoom and pan move the content inside it: zoomed in and panned to each edge, the
     node that stood nearest that edge is drawn inside the container and is what a pointer finds there (nothing is cut at the
     drawing's original bounds). */
  async function reachesEveryEdge(ok, name, holder, frame) {
    const p = holder.__pan, svg = p.svg();
    if (p.own || !(p.fitted || holder.id === "plan-dag") || !svg) return;
    frame.scrollIntoView({ block: "center" });
    const inner = () => { const r = frame.getBoundingClientRect(), cs = getComputedStyle(frame), px = (v) => parseFloat(v) || 0;
      return { left: r.left + px(cs.borderLeftWidth) + px(cs.paddingLeft), right: r.right - px(cs.borderRightWidth) - px(cs.paddingRight), top: r.top + px(cs.borderTopWidth) + px(cs.paddingTop), bottom: r.bottom - px(cs.borderBottomWidth) - px(cs.paddingBottom) }; };
    const c = inner(), sv = svg.getBoundingClientRect();
    ok(sv.left <= c.left + 3 && sv.right >= c.right - 3 && (holder.id === "plan-dag" || (sv.top <= c.top + 3 && sv.bottom >= c.bottom - 3)),
      `zoom, ${name}: the drawing is as big as its container, so nothing is cut at the drawing's own bounds`,
      `zoom, ${name}: drawing ${Math.round(sv.left)},${Math.round(sv.top)} to ${Math.round(sv.right)},${Math.round(sv.bottom)} inside a container ${Math.round(c.left)},${Math.round(c.top)} to ${Math.round(c.right)},${Math.round(c.bottom)}`);
    const face = (g) => g.querySelector("rect, path, circle") || g;  // a station's group also holds its name, which stands to one side
    const nodes = $$(NODES, svg).filter((g) => g.getBoundingClientRect().width > 0);
    if (nodes.length < 2) return;
    const pick = { left: (r) => r.left, right: (r) => -r.right, top: (r) => r.top, bottom: (r) => -r.bottom };
    for (const edge of Object.keys(pick)) {
      p.engine.fit(); await tick();
      const node = nodes.slice().sort((a, b) => pick[edge](face(a).getBoundingClientRect()) - pick[edge](face(b).getBoundingClientRect()))[0];
      p.engine.zoomBy(2, null);
      const box = inner(), at = centerOf(face(node).getBoundingClientRect());
      const seen = { left: Math.max(box.left, 0), right: Math.min(box.right, innerWidth), top: Math.max(box.top, 0), bottom: Math.min(box.bottom, innerHeight) };  // the part of the container the window shows
      const want = { x: edge === "left" ? seen.left + 70 : edge === "right" ? seen.right - 70 : clamp(at.x, seen.left + 70, seen.right - 70),
        y: edge === "top" ? seen.top + 50 : edge === "bottom" ? seen.bottom - 90 : clamp(at.y, seen.top + 50, seen.bottom - 90) };
      p.engine.panBy(at.x - want.x, at.y - want.y);
      const now = centerOf(face(node).getBoundingClientRect()), found = document.elementFromPoint(now.x, now.y);
      // something laid over the drawing (the top bar, the details panel in a narrow window) can cover the spot; that says nothing about the drawing
      const covered = !!found && !frame.contains(found);
      ok(now.x >= box.left && now.x <= box.right && now.y >= box.top && now.y <= box.bottom + 1 && (covered || (!!found && svg.contains(found))),  // a moving train or a lamp may stand over the node; the drawing is what must be there, not the board behind it
        `zoom, ${name}: zoomed in and panned to the ${edge} edge, the node nearest it is drawn there, inside the container`,
        `zoom, ${name}: ${edge}: the node's middle is at ${Math.round(now.x)},${Math.round(now.y)} in a container ${Math.round(box.left)},${Math.round(box.top)} to ${Math.round(box.right)},${Math.round(box.bottom)}; the drawing is not there: a pointer finds ${found ? found.tagName + "." + (found.getAttribute("class") || "") : "nothing"}`);
    }
    p.engine.fit(); await tick();
  }

  /* One drawing: the bar is there, in view and not over the page; each way of zooming changes the view; each way of getting back works. */
  async function oneDrawing(ok, name, holder) {
    if (!holder || !holder.__pan) { ok(false, `zoom, ${name}: the drawing has no zoom and pan (pan.js was never attached); the board holds "${($("#board") ? $("#board").className + ": " + $("#board").textContent : "nothing, the view is " + App.view + " in " + App.section + ": " + $("#main").textContent).slice(0, 160)}"`); return; }
    const p = holder.__pan, svg = p.svg(), bar = barOf(holder);
    ok(!!bar && bar.querySelectorAll("button").length >= 3 && !!button(bar, "Zoom out") && !!button(bar, "Fit") && !!button(bar, "Zoom in"),
      `zoom, ${name}: the drawing has the zoom bar (-, Fit, +)`, `zoom, ${name}: no zoom bar, or it lacks a button (${bar ? [...$$("button", bar)].map((b) => b.textContent).join(" ") : "none"})`);
    if (!bar) return;
    const frame = bar.closest(".zoom-frame").getBoundingClientRect(), at = bar.getBoundingClientRect();
    ok(at.width > 0 && at.right <= frame.right + 1 && at.bottom <= frame.bottom + 1 && at.left >= frame.left - 1 && at.top >= frame.top - 1, `zoom, ${name}: the bar sits inside the drawing's frame`,
      `zoom, ${name}: the bar is at ${Math.round(at.left)},${Math.round(at.top)} ${Math.round(at.width)}x${Math.round(at.height)}, outside its frame ${Math.round(frame.left)},${Math.round(frame.top)} ${Math.round(frame.width)}x${Math.round(frame.height)}`);
    noCutLabels(ok, name, svg);
    await reachesEveryEdge(ok, name, holder, bar.closest(".zoom-frame"));
    const m0 = magnification(holder);
    button(bar, "Zoom in").click(); const afterIn = magnification(holder);
    button(bar, "Zoom out").click(); button(bar, "Zoom out").click(); const afterOut = magnification(holder);
    button(bar, "Fit").click(); await tick(); const fitted = magnification(holder);
    ok(afterIn > m0 && afterOut < afterIn && (p.own ? fitted > 0 : fitted === 1), `zoom, ${name}: + zooms in, - zooms out, Fit puts it back (${m0.toFixed(2)}, ${afterIn.toFixed(2)}, ${afterOut.toFixed(2)}, ${fitted.toFixed(2)})`,
      `zoom, ${name}: buttons: start ${m0.toFixed(2)}, after + ${afterIn.toFixed(2)}, after - - ${afterOut.toFixed(2)}, after Fit ${fitted.toFixed(2)}`);
    const w0 = magnification(holder), seen = wheel(svg, -200, { ctrlKey: true }), w1 = magnification(holder);
    ok(seen && w1 > w0, `zoom, ${name}: Ctrl and the wheel (a touchpad pinch) zooms in without scrolling the page`, `zoom, ${name}: Ctrl+wheel prevented ${seen}, zoom ${w0.toFixed(2)} to ${w1.toFixed(2)}`);
    button(bar, "Fit").click();
    const plain = wheel(svg, -200), plainMoved = magnification(holder) > 1;
    ok(p.fitted ? plain && plainMoved : !plain, `zoom, ${name}: the plain wheel ${p.fitted ? "zooms a fitted drawing" : "still scrolls the page"}`, `zoom, ${name}: plain wheel prevented ${plain}, zoomed ${plainMoved}, fitted ${p.fitted}`);
    button(bar, "Fit").click();
    holder.focus(); const k0 = magnification(holder);
    press(holder, "+"); const k1 = magnification(holder); press(holder, "-"); press(holder, "-"); const k2 = magnification(holder); press(holder, "0"); const k3 = magnification(holder);
    ok(k1 > k0 && k2 < k1 && Math.abs(k3 - k0) < 0.01, `zoom, ${name}: the keys + - 0 zoom and fit the focused drawing`, `zoom, ${name}: keys: + ${k1.toFixed(2)}, - - ${k2.toFixed(2)}, 0 ${k3.toFixed(2)} from ${k0.toFixed(2)}`);
    if (p.own) {
      const can = holder.scrollWidth > holder.clientWidth + 1, was = holder.scrollLeft;
      press(holder, "ArrowRight"); press(holder, "ArrowLeft");
      press(holder, "ArrowRight");
      ok(!can || holder.scrollLeft !== was || holder.scrollLeft + holder.clientWidth >= holder.scrollWidth - 1, `zoom, ${name}: the arrow keys scroll the drawing`, `zoom, ${name}: ArrowRight left it at ${holder.scrollLeft}, was ${was}`);
      holder.scrollLeft = was; button(bar, "Fit").click();
      return;
    }
    press(holder, "+"); press(holder, "+");
    const v0 = vbox(svg); press(holder, "ArrowRight"); press(holder, "ArrowDown"); const v1 = vbox(svg);
    ok(v1[0] > v0[0] && v1[1] > v0[1] && v1[2] === v0[2], `zoom, ${name}: the arrow keys move the zoomed drawing`, `zoom, ${name}: arrows moved the view from ${v0.slice(0, 2).map((v) => v.toFixed(1))} to ${v1.slice(0, 2).map((v) => v.toFixed(1))}`);
    // a drag that pans moves the view, and its release picks nothing
    const spot = backdrop(svg, holder);
    if (!spot) { ok(false, `zoom, ${name}: no empty background to press on`); button(bar, "Fit").click(); return; }
    const before = vbox(svg), pans = Pan.pans;
    let picked = 0; const spy = () => { picked++; }; holder.addEventListener("click", spy);
    svg.dispatchEvent(mouse("pointerdown", spot.x, spot.y)); window.dispatchEvent(mouse("pointermove", spot.x + 3, spot.y + 2)); window.dispatchEvent(mouse("pointermove", spot.x - 40, spot.y - 30)); window.dispatchEvent(mouse("pointerup", spot.x - 40, spot.y - 30));
    const el = document.elementFromPoint(spot.x - 40, spot.y - 30) || svg;
    el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, clientX: spot.x - 40, clientY: spot.y - 30 }));
    holder.removeEventListener("click", spy); await tick();  // the release's click is swallowed only until the next turn
    const after = vbox(svg);
    ok(Pan.pans === pans + 1 && after[0] > before[0] && after[1] > before[1] && after[2] === before[2] && !picked, `zoom, ${name}: dragging the zoomed drawing pans it, and the release picks nothing`,
      `zoom, ${name}: drag: pans ${Pan.pans - pans}, view from ${before.slice(0, 2).map((v) => v.toFixed(1))} to ${after.slice(0, 2).map((v) => v.toFixed(1))}, release clicks ${picked}`);
    svg.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, clientX: spot.x, clientY: spot.y }));
    ok(Pan.view(p.key).z === 1 && Pan.view(p.key).dx === 0, `zoom, ${name}: a double click on the background puts it back`, `zoom, ${name}: after a double click the view is ${JSON.stringify(Pan.view(p.key))}`);
    if (p.fitted) {  // two fingers
      const r = svg.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, z0 = magnification(holder);
      svg.dispatchEvent(touch("pointerdown", 41, cx - 40, cy)); svg.dispatchEvent(touch("pointerdown", 42, cx + 40, cy));
      svg.dispatchEvent(touch("pointermove", 41, cx - 90, cy)); svg.dispatchEvent(touch("pointermove", 42, cx + 90, cy));
      svg.dispatchEvent(touch("pointerup", 41, cx - 90, cy)); svg.dispatchEvent(touch("pointerup", 42, cx + 90, cy));
      ok(magnification(holder) > z0 * 1.5, `zoom, ${name}: spreading two fingers zooms in`, `zoom, ${name}: a pinch took the zoom from ${z0.toFixed(2)} to ${magnification(holder).toFixed(2)}`);
    }
    button(bar, "Fit").click();
  }

  async function everyDrawing(ok, out) {
    const apps = D.map.apps.map((a) => a.key), loaded = apps.filter((k) => D.designs[k]);
    if (!apps.length) { out.push("skip zoom, every drawing: this vault has no apps"); return; }
    Pan.reset(); Nav.home();
    const map = async (lens, group, focus) => { MapView.st.lens = lens; MapView.st.group = group; MapView.st.focus = focus; rerender(); await tick(); };
    const holderOf = (sel) => { const el = $(sel); return el && el.closest(".pannable"); };
    await map("cockpit", "none", null);
    await oneDrawing(ok, "the system map", holderOf("#board svg.cockpit"));
    // the view is kept when the map is drawn again
    $("#board").__pan.engine.zoomBy(2, null); const z = Pan.view("cockpit").z; rerender(); await tick();
    ok(Pan.view("cockpit").z === z && z > 1 && Math.abs(vbox($("#board svg.cockpit"))[2] - JSON.parse("[" + $("#board svg.cockpit").dataset.panBase.split(/\s+/).join(",") + "]")[2] / z) < 0.5, "zoom, the system map: the zoom holds when the map is drawn again",
      `zoom, the system map: zoom ${z}, then ${Pan.view("cockpit").z} after a redraw`);
    Pan.reset(); rerender(); await tick();
    for (const mode of ["domain", "capability"]) {
      if (mode === "domain" ? D.map.apps.some((a) => a.domain) : Object.keys(D.appCaps || {}).length) { await map("cockpit", mode, null); await oneDrawing(ok, `the map grouped by ${mode === "domain" ? "business area" : "capability"}`, holderOf("#board svg.cockpit.grouped")); }
      else out.push(`skip zoom, the map grouped by ${mode}: this vault has nothing to group by`);
    }
    await map("cockpit", "none", apps[0]); await oneDrawing(ok, "one app and its neighbors (focus)", holderOf("#board svg.cockpit.focus"));
    await map("transit", "none", null); await oneDrawing(ok, "contracts only", holderOf("#board svg.transit"));
    await map("releases", "none", null);
    if ($("#board svg.rl-map")) await oneDrawing(ok, "before and after (releases)", holderOf("#board svg.rl-map")); else out.push("skip zoom, before and after: this vault has no releases drawing");
    await map(null, null, null);
    const app = loaded[0] || apps[0];
    Inside.open(app, "context"); await tick();
    await oneDrawing(ok, "an app in context", holderOf("#inside-stage svg.cockpit.focus"));
    Inside.open(app, "containers"); await tick();
    if ($("#inside-stage svg.containers")) { await oneDrawing(ok, "an app's containers", holderOf("#inside-stage svg.containers")); delete Inside.st.zoom.containers; } else out.push("skip zoom, containers: this app draws none");
    if (loaded.length) {
      Inside.open(app, "components"); await tick();
      await oneDrawing(ok, "an app's components", holderOf("#inside-stage svg.inside-svg")); delete Inside.st.zoom.components;
      go(`inside:${app}|sec|data`, { reset: true }); await tick();
      if ($("#panel .in-er svg")) { await oneDrawing(ok, "an app's data model", holderOf("#panel .in-er svg")); delete Inside.st.zoom.er; } else out.push("skip zoom, data model: this design has no erDiagram");
      go(`inside:${app}|sec|flows`, { reset: true }); await tick();
      if ($("#panel svg.seq")) await oneDrawing(ok, "a key flow's sequence diagram", holderOf("#panel svg.seq")); else out.push("skip zoom, sequence diagram: this design has no sequence diagram");
      Inside.open(app, "plan"); await tick();
      if ($("#plan-dag svg")) await oneDrawing(ok, "the build plan's path", $("#plan-dag")); else out.push("skip zoom, build plan: this app has no build plan");
    } else out.push("skip zoom, components, data model, sequence and build plan: no --design was given to this build");
    Pan.reset(); Nav.home(); await tick();
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await everyDrawing(ok, lines); } catch (e) { lines.push(`FAIL the zoom check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the zoom checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
