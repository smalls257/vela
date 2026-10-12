/* The right-hand panel's room: hide it, drag its left edge to widen or narrow it, and both choices are remembered in
   this browser like the sidebar's, Effects and Theme (global, not per vault). Hidden, the main area takes the width
   and a slim tab on the right edge brings the panel back; picking anything that opens in the panel brings it back too
   (go() calls reveal). A remembered width is only a wish: it is clamped to the window as it is now, on load and on
   every window resize, and the wish itself is kept so a larger window gets it back. The views that size themselves
   to the main area refit on the window's resize event, so a change here sends one, held back while a drag is going. */
const PanelSize = (() => {
  const HIDDEN_KEY = "explorer.panel.hidden", WIDTH_KEY = "explorer.panel.width";
  const MIN = 280, MAX_SHARE = 0.6, STEP = 24, SETTLE_MS = 90;
  const panel = $("#panel"), grip = $("#panel-grip"), hideBtn = $("#panel-hide"), tab = $("#panel-tab");
  const root = document.documentElement;
  const max = () => Math.max(MIN, Math.floor(innerWidth * MAX_SHARE));
  const clamp = (w) => Math.min(max(), Math.max(MIN, Math.round(w)));
  const saved = Number(Settings.read(WIDTH_KEY));
  const st = { hidden: Settings.read(HIDDEN_KEY) === "1", want: Number.isFinite(saved) && saved > 0 ? saved : null, drag: null };
  let settleTimer = 0;

  /* The refit every size-aware view already listens for; the Inside drawings send the same event. */
  function refit() { clearTimeout(settleTimer); settleTimer = 0; dispatchEvent(new Event("resize")); }
  function refitSoon() { clearTimeout(settleTimer); settleTimer = setTimeout(refit, SETTLE_MS); }

  function width() { return st.hidden ? 0 : Math.round(panel.getBoundingClientRect().width); }
  function paint() {
    document.body.classList.toggle("panel-hidden", st.hidden);
    // no inline width means the stylesheet's own default for this window, so a reset is just removing the property
    if (st.want === null) root.style.removeProperty("--panel-w"); else root.style.setProperty("--panel-w", clamp(st.want) + "px");
    hideBtn.setAttribute("aria-expanded", String(!st.hidden));
    tab.hidden = !st.hidden;
    grip.hidden = st.hidden;
    if (st.hidden) return;
    const now = width();
    grip.setAttribute("aria-valuemin", String(MIN)); grip.setAttribute("aria-valuemax", String(max())); grip.setAttribute("aria-valuenow", String(now));
    grip.setAttribute("aria-valuetext", `${now} pixels wide`);
  }

  function hide(on, opts = {}) {
    if (st.hidden === on) return;
    const hadFocus = panel.contains(document.activeElement);
    st.hidden = on; Settings.write(HIDDEN_KEY, on ? "1" : "0");
    paint();
    if (on && hadFocus) tab.focus();
    else if (!on && opts.focus) hideBtn.focus();
    refit();
  }
  /* Something was picked that shows in the panel: a hidden panel opens for it, and stays as the reader chose it. */
  function reveal() { hide(false); }
  function setWidth(w, opts = {}) {
    st.want = w === null ? null : clamp(w);
    if (opts.keep !== false) { if (st.want === null) Settings.write(WIDTH_KEY, ""); else Settings.write(WIDTH_KEY, String(st.want)); }
    paint();
    opts.now ? refit() : refitSoon();
  }

  grip.addEventListener("pointerdown", (ev) => {
    if (ev.button !== undefined && ev.button > 0) return;
    ev.preventDefault();
    grip.setPointerCapture(ev.pointerId);
    st.drag = { id: ev.pointerId, moved: false };
    document.body.classList.add("panel-dragging");
  });
  grip.addEventListener("pointermove", (ev) => {
    if (!st.drag) return;
    st.drag.moved = true;
    setWidth(innerWidth - ev.clientX, { keep: false });  // the panel's right edge is the window's
  });
  const endDrag = (ev) => {
    if (!st.drag) return;
    const moved = st.drag.moved;
    st.drag = null;
    document.body.classList.remove("panel-dragging");
    if (grip.hasPointerCapture && grip.hasPointerCapture(ev.pointerId)) grip.releasePointerCapture(ev.pointerId);
    if (moved) setWidth(st.want, { now: true });  // remember where the drag ended; a bare click changes nothing
  };
  grip.addEventListener("pointerup", endDrag);
  grip.addEventListener("pointercancel", endDrag);
  grip.addEventListener("dblclick", () => setWidth(null, { now: true }));
  grip.addEventListener("keydown", (ev) => {
    if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
    ev.preventDefault();
    setWidth(width() + (ev.key === "ArrowLeft" ? STEP : -STEP), { now: true });  // the edge moves left: the panel grows
  });

  hideBtn.addEventListener("click", () => hide(true));
  tab.addEventListener("click", () => hide(false, { focus: true }));
  /* "]" toggles it. Who to ask already uses [ and ] to move a focused strip between racks, so it keeps them there. */
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "]" || ev.metaKey || ev.ctrlKey || ev.altKey || ev.defaultPrevented) return;
    if (ev.target.closest && ev.target.closest("input,textarea,select,.strip")) return;
    if (!$("#overlay").hidden) return;
    ev.preventDefault(); hide(!st.hidden);
  });
  addEventListener("resize", paint);
  paint();
  return { get hidden() { return st.hidden; }, get wanted() { return st.want; }, width, hide, reveal, setWidth, refit, MIN, max, STEP };
})();
