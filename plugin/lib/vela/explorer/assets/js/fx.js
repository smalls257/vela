/* Effects follow the browser's own "reduce motion" setting and nothing else; the page has no switch of its own.
   With it set, the page is Plain: it removes every motion, glow and pulse and keeps every color's meaning (a lamp is
   still the color attention.lights gives it; it only stops breathing and glowing). `#fx=plain` forces Plain for a
   still screenshot, and FX.set is the selftest's way to compare the two. Nothing is remembered between visits. */
const FX = (() => {
  const fromHash = HASH.get("fx");
  let on = fromHash ? fromHash !== "plain" : !matchMedia("(prefers-reduced-motion: reduce)").matches;
  function apply() { document.documentElement.classList.toggle("plain", !on); }
  function set(value) {
    on = !!value;
    apply();
    if (typeof Motion !== "undefined") Motion.clear();
    if (typeof rerender === "function" && $("#main").childNodes.length) rerender();
  }
  apply();
  return { get on() { return on; }, set };
})();
