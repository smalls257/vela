/* Zoom and pan for every drawing: one shared piece, so the buttons, the gestures and the keys mean the same everywhere.

   Each view calls Pan.attach(holder, { key, svg, ... }) after it draws. That gives the drawing:
   - a zoom bar (-, Fit, +) at its bottom right, the same bar on every drawing (a drawing may add "Reading size");
   - drag to pan, wheel or pinch to zoom, and the keys + - 0 and the arrows when the drawing itself has focus.
   Gestures:
   - A press on anything a reader can point at (a box, a lamp, a line, a button, anything focusable or movable) is
     left alone: a box still moves by its own drag (layout.js), and a click still selects.
   - A press on the background pans only once the pointer has moved a few pixels, so a click there stays a click.
     After a pan the click the browser sends on release is swallowed, so letting go never opens anything.
   - A drawing fitted to its board has nothing to scroll, so zoom and pan change its viewBox, and keep that view (by
     `key`) when the view is drawn again. A double click on the background, or Fit, or 0, puts it back. The wheel
     zooms it; on a drawing that scrolls (a scrollOnly one, or one with its own engine) Ctrl or Cmd with the wheel
     zooms, so the plain wheel still scrolls the page. A pinch of two fingers zooms a fitted drawing on a touch screen.
   - Where the holder scrolls (or, for a scrollOnly drawing, a box around it), a pan scrolls it, until the drawing is
     zoomed in the viewBox, when the pan moves what the viewBox shows.
   - A drawing that sizes itself (inside.js) passes `engine` ({ zoomBy, fit, reading?, panBy }) and keeps its own
     zoom; the bar, wheel and keys are still these.
   - Mouse and pen drag; touch keeps the browser's own scrolling, and the plain wheel and touchpad scroll as they always did. */
const Pan = (() => {
  const MOVE = 5;  // pixels the pointer travels before a press on the background becomes a pan
  const STEP = 1.25, MIN_Z = 0.5, MAX_Z = 8, KEY_PX = 60;  // one button press or key; how far a drawing zooms out and in; one arrow key
  const POINTABLE = 'a, button, input, select, textarea, label, summary, [tabindex], [data-movable], [role="button"], [role="link"], .zoom-bar, .in-mini, .legend';
  const ARROWS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  const views = {};   // key -> { dx, dy, z }: how far a fitted drawing's viewBox is moved (drawing units) and zoomed (1 = as fitted)
  let pans = 0, zooms = 0;  // how many pans and zooms have happened, for #selftest
  const pointable = (el, holder) => {
    for (let x = el; x && x !== holder; x = x.parentElement) if (x.matches && x.matches(POINTABLE)) return true;
    return false;
  };
  /* The element that scrolls and has more to show: the holder itself, or with `outward` the nearest one around it
     (the build plan's path grows the page, not its own box). A fitted map does not look outward: dragging it must
     not scroll the page it sits on. */
  function scroller(el, outward) {
    for (let x = el; x && x !== document.body && x !== document.documentElement; x = outward ? x.parentElement : null) {
      const cs = getComputedStyle(x), can = (o) => o === "auto" || o === "scroll";
      if ((can(cs.overflowX) && x.scrollWidth > x.clientWidth + 1) || (can(cs.overflowY) && x.scrollHeight > x.clientHeight + 1)) return x;
    }
    return null;
  }
  /* ------------------------------------------------------------ the view: a viewBox moved and zoomed */
  /* The drawing's own viewBox, before any pan or zoom, kept on the element so a shift is never added twice. */
  function baseBox(svg) {
    if (!svg.dataset.panBase) svg.dataset.panBase = svg.getAttribute("viewBox") || "";
    return svg.dataset.panBase.split(/[\s,]+/).map(Number);
  }
  const still = (v) => !v || (v.dx === 0 && v.dy === 0 && v.z === 1);
  function showView(svg, key, v) {
    const b = baseBox(svg);
    if (b.length !== 4 || b.some((n) => !isFinite(n))) return false;
    if (still(v)) { delete views[key]; v = { dx: 0, dy: 0, z: 1 }; } else views[key] = v;
    svg.setAttribute("viewBox", `${b[0] + v.dx} ${b[1] + v.dy} ${b[2] / v.z} ${b[3] / v.z}`);
    svg.classList.toggle("pan-zoomed", v.z !== 1);  // zoomed in, a drawing must not paint outside its own box
    return true;
  }
  const viewOf = (key) => Object.assign({ dx: 0, dy: 0, z: 1 }, views[key]);
  /* The point of the drawing under a screen point, or the middle of what is in view. */
  function drawingPoint(svg, key, client) {
    const b = baseBox(svg), v = viewOf(key);
    const ctm = client && svg.getScreenCTM && svg.getScreenCTM();
    if (ctm) { const p = svg.createSVGPoint(); p.x = client.x; p.y = client.y; const q = p.matrixTransform(ctm.inverse()); return { x: q.x, y: q.y }; }
    return { x: b[0] + v.dx + b[2] / v.z / 2, y: b[1] + v.dy + b[3] / v.z / 2 };
  }
  /* The default engine: a fitted drawing zooms and pans by its viewBox. Zooming keeps the point under the pointer
     (or the middle) where it is. */
  function viewEngine(p) {
    return {
      zoomBy(f, client) {
        const svg = p.svg(); if (!svg) return;
        const b = baseBox(svg), v = viewOf(p.key); if (b.length !== 4) return;
        let z = Math.min(MAX_Z, Math.max(MIN_Z, v.z * f)); if (Math.abs(z - 1) < 0.02) z = 1;
        if (z === v.z) return;
        const a = drawingPoint(svg, p.key, client), vx = b[0] + v.dx, vy = b[1] + v.dy, r = v.z / z;
        showView(svg, p.key, { dx: a.x - (a.x - vx) * r - b[0], dy: a.y - (a.y - vy) * r - b[1], z });
        zooms++;
      },
      panBy(px, py) {
        const svg = p.svg(); if (!svg) return;
        const b = baseBox(svg), v = viewOf(p.key), rect = svg.getBoundingClientRect(); if (b.length !== 4 || !rect.width) return;
        const k = b[2] / v.z / rect.width;
        showView(svg, p.key, { dx: v.dx + px * k, dy: v.dy + py * k, z: v.z });
      },
      fit() { const svg = p.svg(); if (svg) { showView(svg, p.key, null); zooms++; } },
    };
  }
  /* ------------------------------------------------------------ the bar, the wheel, the keys */
  function bar(holder, p, opts) {
    const frame = opts.frame || (p.scrollOnly ? holder.parentElement : holder);
    if (!frame || frame === document.body) throw new Error(`[pan] the zoom bar for ${p.key} has no frame of its own to sit in; pass opts.frame`);
    for (const old of [...frame.children]) if (old.classList.contains("zoom-bar") && old.dataset.for === p.key) old.remove();
    frame.classList.add("zoom-frame");
    const go = (f) => () => p.engine.zoomBy(f, null);
    const btn = (title, text, run) => h("button", { type: "button", title, "aria-label": title, onclick: run }, text);
    frame.append(h("div", { class: "zoom-bar", role: "group", "aria-label": "Zoom", "data-for": p.key },
      btn("Zoom out (-)", "−", go(1 / STEP)),
      btn(opts.fitTitle || "Fit the whole drawing in view (0)", "Fit", () => p.engine.fit()),
      p.engine.reading ? btn(opts.readingTitle || "Back to a size you can read", "Reading size", () => p.engine.reading()) : null,
      btn("Zoom in (+)", "+", go(STEP))));
  }
  function wireGestures(holder) {
    const P = () => holder.__pan;
    holder.addEventListener("pointerdown", (e) => start(e, holder));
    holder.addEventListener("dblclick", (e) => {
      const p = P(), svg = p.svg();
      if (pointable(e.target, holder) || !svg || !views[p.key]) return;
      showView(svg, p.key, null);
    });
    holder.addEventListener("wheel", (e) => {
      const p = P();
      if (pointable(e.target, holder) || !p.svg()) return;
      // a fitted drawing has nothing to scroll, so the plain wheel zooms it; elsewhere Ctrl or Cmd does (a touchpad pinch arrives as Ctrl)
      if (!(p.fitted || e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      p.engine.zoomBy(Math.exp(-Math.max(-60, Math.min(60, e.deltaY)) * (e.deltaMode ? 0.05 : 0.004)), { x: e.clientX, y: e.clientY });
    }, { passive: false });
    holder.addEventListener("keydown", (e) => {
      const p = P();
      if (e.target !== holder || e.altKey || e.ctrlKey || e.metaKey) return;  // a focused box keeps its own keys; Ctrl and Cmd are the browser's zoom
      const arrow = ARROWS[e.key];
      if (e.key === "+" || e.key === "=") p.engine.zoomBy(STEP, null);
      else if (e.key === "-" || e.key === "_") p.engine.zoomBy(1 / STEP, null);
      else if (e.key === "0") p.engine.fit();
      else if (arrow) p.engine.panBy(arrow[0] * KEY_PX * (e.shiftKey ? 3 : 1), arrow[1] * KEY_PX * (e.shiftKey ? 3 : 1));
      else return;
      e.preventDefault();
    });
    pinch(holder, P);
  }
  /* Two fingers on a fitted drawing: the distance between them zooms, the middle between them pans. */
  function pinch(holder, P) {
    const down = new Map();
    let last = null;
    const read = () => { const [a, b] = [...down.values()]; return { d: Math.hypot(a.x - b.x, a.y - b.y), x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; };
    holder.addEventListener("pointerdown", (e) => { if (e.pointerType !== "touch") return; down.set(e.pointerId, { x: e.clientX, y: e.clientY }); last = down.size === 2 ? read() : null; });
    holder.addEventListener("pointermove", (e) => {
      if (!down.has(e.pointerId)) return;
      down.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const p = P();
      if (down.size !== 2 || !last || !p.fitted) return;
      const now = read();
      if (last.d > 0) p.engine.zoomBy(now.d / last.d, { x: now.x, y: now.y });
      p.engine.panBy(last.x - now.x, last.y - now.y);
      last = now;
    });
    const lift = (e) => { down.delete(e.pointerId); last = null; };
    holder.addEventListener("pointerup", lift); holder.addEventListener("pointercancel", lift);
  }
  /* opts: key (where the view is remembered), svg (a function that finds the drawing), scrollOnly (a pan scrolls the
     box around it), frame (what carries the zoom bar: the holder, or for a scrollOnly drawing its parent), engine and
     readingTitle (for a drawing that sizes itself). */
  function attach(holder, opts = {}) {
    const key = opts.key || holder.id || holder.className;
    const p = { key, svg: opts.svg || (() => holder.querySelector("svg")), scrollOnly: !!opts.scrollOnly, own: !!opts.engine, fitted: !opts.scrollOnly && !opts.engine };
    p.engine = opts.engine || viewEngine(p);
    holder.__pan = p;
    holder.classList.add("pannable");
    holder.dataset.pan = key;
    if (p.fitted) holder.dataset.fitted = "1"; else delete holder.dataset.fitted;
    if (!holder.hasAttribute("tabindex")) holder.setAttribute("tabindex", "0");
    holder.setAttribute("aria-keyshortcuts", "+ - 0 ArrowLeft ArrowRight ArrowUp ArrowDown");
    if (!holder.hasAttribute("aria-label")) holder.setAttribute("aria-label", "Drawing: + and - zoom, 0 fits, the arrow keys move");
    const svg = p.svg();
    if (svg && views[key] && !p.own) { delete svg.dataset.panBase; showView(svg, key, views[key]); }
    bar(holder, p, opts);
    if (holder.__panWired) return;
    holder.__panWired = true;
    wireGestures(holder);
  }
  function start(e, holder) {
    if (e.button !== 0 || e.pointerType === "touch" || e.isPrimary === false || pointable(e.target, holder)) return;
    const p = holder.__pan, from = { x: e.clientX, y: e.clientY };
    let mode = null, scroll = null, at0 = null, svg = null, k = 1;
    const begin = () => {
      scroll = scroller(holder, p.scrollOnly);
      svg = p.svg();
      const zoomedIn = !p.own && views[p.key] && views[p.key].z > 1;  // zoomed in, a pan moves the view, not the page
      if (scroll && !zoomedIn) { mode = "scroll"; at0 = [scroll.scrollLeft, scroll.scrollTop]; }
      else if (svg && !p.own && (zoomedIn || !p.scrollOnly) && baseBox(svg).length === 4) {
        mode = "view"; at0 = viewOf(p.key);
        const r = svg.getBoundingClientRect();
        k = r.width ? baseBox(svg)[2] / at0.z / r.width : 1;  // drawing units per screen pixel
      } else mode = "none";
      holder.classList.add("panning"); document.documentElement.classList.add("pan-now");
      if (typeof hideTip === "function") hideTip();
    };
    const onMove = (ev) => {
      const dx = ev.clientX - from.x, dy = ev.clientY - from.y;
      if (!mode) { if (Math.hypot(dx, dy) < MOVE) return; begin(); }
      ev.preventDefault();
      if (mode === "scroll") { scroll.scrollLeft = at0[0] - dx; scroll.scrollTop = at0[1] - dy; }
      if (mode === "view") showView(p.svg() || svg, p.key, { dx: at0.dx - dx * k, dy: at0.dy - dy * k, z: at0.z });
    };
    const onUp = () => {
      removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); removeEventListener("pointercancel", onUp);
      if (!mode) return;
      holder.classList.remove("panning"); document.documentElement.classList.remove("pan-now");
      if (mode === "none") return;
      pans++;
      // the click that follows the release, on the drawing, is the end of the pan, not a pick; a click anywhere else is left alone
      const swallow = (ev) => { if (!holder.contains(ev.target)) return; ev.stopPropagation(); ev.preventDefault(); removeEventListener("click", swallow, true); };
      addEventListener("click", swallow, true);
      setTimeout(() => removeEventListener("click", swallow, true), 0);
    };
    addEventListener("pointermove", onMove); addEventListener("pointerup", onUp); addEventListener("pointercancel", onUp);
  }
  /* For #selftest: forget every view, and put the drawings on screen back. */
  function reset() {
    for (const holder of document.querySelectorAll(".pannable")) { const svg = holder.__pan && !holder.__pan.own && holder.__pan.svg(); if (svg && svg.dataset.panBase) showView(svg, holder.__pan.key, null); }
    for (const k of Object.keys(views)) delete views[k];
  }
  /* Forget the saved view of drawings whose content has just changed, so they open fitted to what they now show. */
  const forget = (...keys) => { for (const k of keys) delete views[k]; };
  return { attach, reset, forget, view: (key) => viewOf(key), engineOf: (holder) => holder.__pan && holder.__pan.engine,
    get pans() { return pans; }, get zooms() { return zooms; }, MOVE, STEP };
})();
