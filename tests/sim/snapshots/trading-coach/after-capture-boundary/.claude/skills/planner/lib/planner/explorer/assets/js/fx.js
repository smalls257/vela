/* Effects: On or Plain, in the top bar, remembered in this browser, On by default.
   Plain removes every motion, glow and pulse on the page and keeps every colour's meaning: a lamp is still the
   colour attention.lights gives it; it only stops breathing and glowing. The map's motion option (trace on demand,
   ripple of impact, or trains on the line map) is remembered the same way. */
const FX = (() => {
  const KEY = "explorer.effects", MOTION_KEY = "explorer.motion";
  const MOTIONS = [["trace", "Trace", "Pick a flow or contract: its path lights hop by hop"],
    ["ripple", "Ripple", "Pick an app or decision: a ripple spreads, ring by ring, to what depends on it"],
    ["trains", "Trains", "The line map, with a train running each flow's journey"]];
  const read = Settings.read, write = Settings.write;
  const fromHash = HASH.get("fx");
  let on = fromHash ? fromHash !== "plain" : read(KEY) !== "plain";
  let motion = HASH.get("motion") || read(MOTION_KEY) || "trace";
  if (!MOTIONS.some(([m]) => m === motion)) motion = "trace";
  function apply() {
    document.documentElement.classList.toggle("plain", !on);
    const b = $("#fx");
    if (b) {
      b.setAttribute("aria-pressed", String(on));
      b.title = on ? "Effects on: motion and glow that carry meaning. Switch to Plain for a still page with the same colours."
        : "Plain: no motion, glow or pulsing; every colour keeps its meaning. Switch effects back on.";
      $$("button", b).forEach((x) => x.setAttribute("aria-current", String((x.dataset.fx === "on") === on)));
    }
  }
  function set(value) {
    on = !!value;
    write(KEY, on ? "on" : "plain");
    apply();
    if (typeof Motion !== "undefined") Motion.clear();
    if (typeof rerender === "function" && $("#main").childNodes.length) rerender();
  }
  function setMotion(m) { motion = m; write(MOTION_KEY, m); }
  const box = $("#fx");
  if (box) box.addEventListener("click", (ev) => { const b = ev.target.closest("button[data-fx]"); if (b) set(b.dataset.fx === "on"); });
  apply();
  return { get on() { return on; }, set, get motion() { return motion; }, setMotion, MOTIONS };
})();
