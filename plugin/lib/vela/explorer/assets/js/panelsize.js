/* The room each side column takes: the right-hand panel and the left-hand sections bar. Each can be hidden, and each
   has a handle on its inner edge to drag wider or narrower; both choices are remembered in this browser like Effects
   and Theme (global, not per vault). One factory serves both edges, so the two cannot drift apart in how they clamp,
   remember or refit: a Shield against two copies of the same drag code each growing its own bugs.

   A remembered width is only a wish: it is clamped to the window as it is now, on load and on every window resize,
   and the wish itself is kept so a larger window gets it back. The views that size themselves to the main area refit
   on the window's resize event, so a change here sends one, held back while a drag is going.

   The panel: hidden, the main area takes the width and a slim tab on the right edge brings it back; picking anything
   that opens in the panel brings it back too (go() calls reveal). "]" toggles it.
   The sections bar: the top bar's menu button hides and shows it (that button is always on screen, so it needs no
   tab). "[" toggles it. Its hidden state keeps the key and the true/false the sidebar always stored, so a reader's
   choice from before survives. */
function EdgeSize(spec) {
  const { el, grip, hideBtn, tab, hiddenKey, widthKey, cssVar, hiddenClass, dragClass, min, maxShare, edge, key, on = "1", off = "0" } = spec;
  const STEP = 24, SETTLE_MS = 90;
  const root = document.documentElement;
  const max = () => Math.max(min, Math.floor(innerWidth * maxShare));
  const clamp = (w) => Math.min(max(), Math.max(min, Math.round(w)));
  const saved = Number(Settings.read(widthKey));
  const st = { hidden: Settings.read(hiddenKey) === on, want: Number.isFinite(saved) && saved > 0 ? saved : null, drag: null };
  let settleTimer = 0;
  /* Which way a pointer or an arrow key grows the column: the panel's handle is on its left, the bar's on its right. */
  const grows = edge === "left" ? "ArrowLeft" : "ArrowRight", shrinks = edge === "left" ? "ArrowRight" : "ArrowLeft";
  const widthAt = (x) => (edge === "left" ? innerWidth - x : x - el.getBoundingClientRect().left);

  /* The refit every size-aware view already listens for; the Inside drawings send the same event. */
  function refit() { clearTimeout(settleTimer); settleTimer = 0; dispatchEvent(new Event("resize")); }
  function refitSoon() { clearTimeout(settleTimer); settleTimer = setTimeout(refit, SETTLE_MS); }

  function width() { return st.hidden ? 0 : Math.round(el.getBoundingClientRect().width); }
  function paint() {
    document.body.classList.toggle(hiddenClass, st.hidden);
    // no inline width means the stylesheet's own default for this window, so a reset is just removing the property
    if (st.want === null) root.style.removeProperty(cssVar); else root.style.setProperty(cssVar, clamp(st.want) + "px");
    hideBtn.setAttribute("aria-expanded", String(!st.hidden));
    if (tab) tab.hidden = !st.hidden;
    grip.hidden = st.hidden;
    if (st.hidden) return;
    const now = width();
    grip.setAttribute("aria-valuemin", String(min)); grip.setAttribute("aria-valuemax", String(max())); grip.setAttribute("aria-valuenow", String(now));
    grip.setAttribute("aria-valuetext", `${now} pixels wide`);
  }

  function hide(hidden, opts = {}) {
    if (st.hidden === hidden) return;
    const hadFocus = el.contains(document.activeElement) || grip === document.activeElement;
    st.hidden = hidden; Settings.write(hiddenKey, hidden ? on : off);
    paint();
    if (hidden && hadFocus) (tab || hideBtn).focus();
    else if (!hidden && opts.focus) hideBtn.focus();
    refit();
  }
  function setWidth(w, opts = {}) {
    st.want = w === null ? null : clamp(w);
    if (opts.keep !== false) Settings.write(widthKey, st.want === null ? "" : String(st.want));
    paint();
    opts.now ? refit() : refitSoon();
  }

  grip.addEventListener("pointerdown", (ev) => {
    if (ev.button !== undefined && ev.button > 0) return;
    ev.preventDefault();
    grip.setPointerCapture(ev.pointerId);
    st.drag = { id: ev.pointerId, moved: false };
    document.body.classList.add(dragClass);
  });
  grip.addEventListener("pointermove", (ev) => {
    if (!st.drag) return;
    st.drag.moved = true;
    setWidth(widthAt(ev.clientX), { keep: false });
  });
  const endDrag = (ev) => {
    if (!st.drag) return;
    const moved = st.drag.moved;
    st.drag = null;
    document.body.classList.remove(dragClass);
    if (grip.hasPointerCapture && grip.hasPointerCapture(ev.pointerId)) grip.releasePointerCapture(ev.pointerId);
    if (moved) setWidth(st.want, { now: true });  // remember where the drag ended; a bare click changes nothing
  };
  grip.addEventListener("pointerup", endDrag);
  grip.addEventListener("pointercancel", endDrag);
  grip.addEventListener("dblclick", () => setWidth(null, { now: true }));
  grip.addEventListener("keydown", (ev) => {
    if (ev.key !== grows && ev.key !== shrinks) return;
    ev.preventDefault();
    setWidth(width() + (ev.key === grows ? STEP : -STEP), { now: true });
  });
  /* The toggle key. Who to ask already uses [ and ] to move a focused strip between racks, so it keeps them there. */
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== key || ev.metaKey || ev.ctrlKey || ev.altKey || ev.defaultPrevented) return;
    if (ev.target.closest && ev.target.closest("input,textarea,select,.strip")) return;
    if (!$("#overlay").hidden) return;
    ev.preventDefault(); hide(!st.hidden);
  });
  addEventListener("resize", paint);
  paint();
  return { get hidden() { return st.hidden; }, get wanted() { return st.want; }, width, hide, setWidth, refit, MIN: min, max, STEP, paint };
}

const PanelSize = (() => {
  const tab = $("#panel-tab"), hideBtn = $("#panel-hide");
  const edge = EdgeSize({ el: $("#panel"), grip: $("#panel-grip"), hideBtn, tab, hiddenKey: "explorer.panel.hidden", widthKey: "explorer.panel.width",
    cssVar: "--panel-w", hiddenClass: "panel-hidden", dragClass: "panel-dragging", min: 280, maxShare: 0.6, edge: "left", key: "]" });
  hideBtn.addEventListener("click", () => edge.hide(true));
  tab.addEventListener("click", () => edge.hide(false, { focus: true }));
  /* Something was picked that shows in the panel: a hidden panel opens for it, and stays as the reader chose it. */
  edge.reveal = () => edge.hide(false);
  return edge;
})();

const SideSize = (() => {
  const hideBtn = $("#side-toggle");
  const edge = EdgeSize({ el: $("#side"), grip: $("#side-grip"), hideBtn, hiddenKey: "explorer.side", widthKey: "explorer.side.width",
    cssVar: "--side-w", hiddenClass: "side-hidden", dragClass: "side-dragging", min: 150, maxShare: 0.34, edge: "right", key: "[", on: "true", off: "false" });
  hideBtn.addEventListener("click", () => edge.hide(!edge.hidden));
  return edge;
})();
