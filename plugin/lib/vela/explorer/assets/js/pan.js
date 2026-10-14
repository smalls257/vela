/* Drag to pan: press on the empty background of a drawing and drag, and the view moves with the pointer.

   One helper for every drawing that can be panned (the cockpit, grouped and focus maps, the line map, the releases
   map, the drawings inside an app, the build plan's path), so the gesture means the same everywhere. Each view calls
   Pan.attach(holder, { key, svg }) after it draws.
   - A press on anything a reader can point at (a box, a lamp, a line, a button, anything focusable or movable) is
     left alone: a box still moves by its own drag (layout.js), and a click still selects.
   - A press on the background pans only once the pointer has moved a few pixels, so a click there stays a click.
     After a pan the click the browser sends on release is swallowed, so letting go never opens anything.
   - Where the drawing's holder scrolls (or, for a scrollOnly drawing, a box around it), the pan scrolls it; a drawing fitted to its board has
     nothing to scroll, so the pan shifts its viewBox instead, and keeps that shift (by `key`) when the view is
     drawn again. A double click on the background puts a shifted drawing back.
   - Mouse and pen only: touch keeps the browser's own scrolling, and the wheel, the touchpad and the keyboard
     scroll as they always did. */
const Pan = (() => {
  const MOVE = 5;  // pixels the pointer travels before a press on the background becomes a pan
  const POINTABLE = 'a, button, input, select, textarea, label, summary, [tabindex], [data-movable], [role="button"], [role="link"], .in-zoom, .in-mini, .legend';
  const shifts = {};  // key -> [dx, dy], in drawing units: how far a fitted drawing's viewBox is panned
  let pans = 0;       // how many pans have happened, for #selftest
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
  /* The drawing's own viewBox, before any pan, kept on the element so a shift is never added twice. */
  function baseBox(svg) {
    if (!svg.dataset.panBase) svg.dataset.panBase = svg.getAttribute("viewBox") || "";
    return svg.dataset.panBase.split(/[\s,]+/).map(Number);
  }
  function shiftTo(svg, key, d) {
    const b = baseBox(svg);
    if (b.length !== 4 || b.some((v) => !isFinite(v))) return false;
    shifts[key] = d;
    svg.setAttribute("viewBox", `${b[0] + d[0]} ${b[1] + d[1]} ${b[2]} ${b[3]}`);
    return true;
  }
  function attach(holder, opts = {}) {
    const key = opts.key || holder.id || holder.className;
    holder.__pan = { key, svg: opts.svg || (() => holder.querySelector("svg")), scrollOnly: !!opts.scrollOnly };
    holder.classList.add("pannable");
    holder.dataset.pan = key;
    const svg = holder.__pan.svg();
    if (svg && shifts[key] && !holder.__pan.scrollOnly) { delete svg.dataset.panBase; shiftTo(svg, key, shifts[key]); }
    if (holder.__panWired) return;
    holder.__panWired = true;
    holder.addEventListener("pointerdown", (e) => start(e, holder));
    holder.addEventListener("dblclick", (e) => {
      const p = holder.__pan, svg = p.svg();
      if (pointable(e.target, holder) || !svg || !shifts[p.key]) return;
      shiftTo(svg, p.key, [0, 0]);
      delete shifts[p.key];
    });
  }
  function start(e, holder) {
    if (e.button !== 0 || e.pointerType === "touch" || e.isPrimary === false || pointable(e.target, holder)) return;
    const p = holder.__pan, from = { x: e.clientX, y: e.clientY };
    let mode = null, scroll = null, at0 = null, svg = null, k = 1;
    const begin = () => {
      scroll = scroller(holder, p.scrollOnly);
      svg = p.svg();
      if (scroll) { mode = "scroll"; at0 = [scroll.scrollLeft, scroll.scrollTop]; }
      else if (svg && !p.scrollOnly && baseBox(svg).length === 4) {
        mode = "view"; at0 = (shifts[p.key] || [0, 0]).slice();
        const r = svg.getBoundingClientRect();
        k = r.width ? baseBox(svg)[2] / r.width : 1;  // drawing units per screen pixel
      } else mode = "none";
      holder.classList.add("panning"); document.documentElement.classList.add("pan-now");
      if (typeof hideTip === "function") hideTip();
    };
    const onMove = (ev) => {
      const dx = ev.clientX - from.x, dy = ev.clientY - from.y;
      if (!mode) { if (Math.hypot(dx, dy) < MOVE) return; begin(); }
      ev.preventDefault();
      if (mode === "scroll") { scroll.scrollLeft = at0[0] - dx; scroll.scrollTop = at0[1] - dy; }
      if (mode === "view") shiftTo(p.svg() || svg, p.key, [at0[0] - dx * k, at0[1] - dy * k]);
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
  /* For #selftest: forget every shift, and put the drawings on screen back. */
  function reset() {
    for (const holder of document.querySelectorAll(".pannable")) { const svg = holder.__pan && holder.__pan.svg(); if (svg && svg.dataset.panBase) shiftTo(svg, holder.__pan.key, [0, 0]); }
    for (const k of Object.keys(shifts)) delete shifts[k];
  }
  return { attach, reset, shift: (key) => (shifts[key] || [0, 0]).slice(), get pans() { return pans; }, MOVE };
})();
