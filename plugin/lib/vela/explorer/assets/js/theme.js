/* Themes: the room's palette, picked in the top bar beside Effects, remembered in this browser like Effects, and
   starting from the build's --theme. A theme is a set of CSS custom properties (themes.css). The SVG drawings and
   the flow canvas read the same properties through Theme.c, so every view repaints from one palette, and LIGHT's
   colors are re-read from the theme's --warning, --caution, --unexamined, --override and --unlit, so a lamp keeps
   its meaning in every room. Plain works under every theme: it removes motion and glow, never a color. */
const Theme = (() => {
  const KEY = "explorer.theme", LIST = D.themes, ids = LIST.map((t) => t.id);
  const known = (v) => (ids.includes(v) ? v : null);
  const asked = HASH.get("theme");
  if (asked && !known(asked)) console.warn(`[theme] #theme=${asked} is not one of ${ids.join(", ")}; using the remembered or built theme`);
  let current = known(asked) || known(Settings.read(KEY)) || known(D.theme) || ids[0];
  let cache = {};
  function c(name) {
    if (!(name in cache)) cache[name] = getComputedStyle(document.documentElement).getPropertyValue("--" + name).trim();
    return cache[name];
  }
  const list = (name) => c(name).split(",").map((x) => x.trim()).filter(Boolean);
  function apply() {
    document.documentElement.dataset.theme = current;
    cache = {};
    for (const lv of Object.keys(LIGHT)) {
      const base = lv === "dark" ? "unlit" : lv;
      LIGHT[lv].color = c(base) || LIGHT[lv].color;
      LIGHT[lv].ink = c(base + "-ink") || LIGHT[lv].ink;
    }
    const sel = $("#theme");
    if (sel) { sel.value = current; sel.title = `Theme: ${LIST.find((t) => t.id === current).say}`; }
  }
  function set(id) {
    if (!known(id)) { console.warn(`[theme] ${id} is not a theme here`); return; }
    current = id;
    Settings.write(KEY, id);
    apply();
    if (typeof Motion !== "undefined") Motion.clear();
    if (typeof rerender === "function" && $("#main").childNodes.length) { rerender(); if (typeof Panel !== "undefined") Panel.render(); }
  }
  const sel = $("#theme");
  if (sel) {
    LIST.forEach((t) => sel.append(h("option", { value: t.id }, t.label)));
    sel.addEventListener("change", () => set(sel.value));
  }
  apply();
  return { get id() { return current; }, set, c, list, LIST };
})();
