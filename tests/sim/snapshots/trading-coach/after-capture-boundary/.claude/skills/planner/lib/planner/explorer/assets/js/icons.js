/* The page's own icons: hand-drawn line glyphs on a 24 grid, one stroke weight, in currentColor, so they take the
   theme's ink and the lamp's ink and never carry a colour of their own (the lamps keep colour to themselves).

   Every app and outside party has one: build.py picks it (icons_data.py: the page's icon:, else a keyword, else a
   shape kept by the name) and says why. A generated emblem, when its slot resolves, still wins (Assets.emblem).
   Each glyph is path data only, so the same drawing serves SVG, HTML and the flow canvas (Path2D). The link chips
   wear the last six. */
const Icons = (() => {
  const G = {
    payments: "M3 6h18v12H3z M3 10h18 M7 15h4",
    booking: "M4 6h16v14H4z M4 10h16 M8 3v5 M16 3v5 M8 14h3",
    identity: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21c0-4 4-6 8-6s8 2 8 6",
    lock: "M6 11h12v10H6z M8 11V8a4 4 0 0 1 8 0v3 M12 15v2",
    consent: "M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z M9 12l2 2 4-4",
    fraud: "M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z M12 8v5 M12 16v.5",
    notifications: "M6 17h12l-1.5-2v-4a4.5 4.5 0 0 0-9 0v4z M10 20a2 2 0 0 0 4 0",
    messaging: "M4 5h16v11H9l-5 4z M8 9h8 M8 12h5",
    search: "M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z M15.5 15.5L20 20",
    catalogue: "M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z",
    analytics: "M4 20h16 M7 20v-6 M12 20V8 M17 20V10",
    gateway: "M12 3v18 M3 12h6 M15 12h6 M6 9l-3 3 3 3 M18 9l3 3-3 3",
    database: "M5 6c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3z M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6 M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3",
    mobile: "M8 3h8v18H8z M11 18h2",
    web: "M3 5h18v14H3z M3 9h18 M6 7h1 M9 7h1",
    kiosk: "M7 3h10v12H7z M10 7h4 M10 15v4 M14 15v4 M6 21h12",
    callcentre: "M5 14v-2a7 7 0 0 1 14 0v2 M5 14h3v5H5z M16 14h3v5h-3z M19 19c0 1.5-2 2-5 2",
    ship: "M3 16h18l-2.5 4h-13z M6 16v-5h12v5 M10 11V7h4v4",
    schedule: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3 2",
    pricing: "M3 12V4h8l10 10-8 8z M7 8a1 1 0 1 0 2 0 1 1 0 0 0-2 0",
    ledger: "M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z M5 17a3 3 0 0 1 3-3h11 M9 8h6",
    inventory: "M3 8l9-5 9 5v8l-9 5-9-5z M3 8l9 5 9-5 M12 13v8",
    audit: "M8 3h8v3H8z M6 5H5v16h14V5h-1 M9 13l2 2 4-4",
    loyalty: "M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6l-5.4 2.9 1.2-6-4.5-4.2 6.1-.7z",
    voucher: "M3 7h18v3a2 2 0 0 0 0 4v3H3v-3a2 2 0 0 0 0-4z M14 7v2 M14 11v2 M14 15v2",
    refund: "M4 12a8 8 0 1 0 2.3-5.7 M4 4v4h4",
    legacy: "M4 4h16v6H4z M4 14h16v6H4z M7 7h3 M7 17h3 M15 7h2 M15 17h2",
    legal: "M12 4v16 M7 20h10 M5 7h14 M5 7l-3 6h6z M19 7l-3 6h6z",
    location: "M12 21s-7-6.5-7-11a7 7 0 0 1 14 0c0 4.5-7 11-7 11z M12 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
    news: "M4 5h13v14H6a2 2 0 0 1-2-2z M17 9h3v8a2 2 0 0 1-2 2 M7 9h7 M7 13h7 M7 16h4",
    learning: "M2 9l10-5 10 5-10 5z M6 11v5c3 2 9 2 12 0v-5 M22 9v5",
    trading: "M3 17l6-6 4 4 8-8 M15 7h6v6",
    partner: "M9 15a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M15 19a5 5 0 1 0 0-10 5 5 0 0 0 0 10z",
    cube: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M4 7.5l8 4.5 8-4.5 M12 12v9",
    hexagon: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M12 8l4 2.2v4.6L12 17l-4-2.2v-4.6z",
    layers: "M12 4l9 5-9 5-9-5z M3 14l9 5 9-5",
    nodes: "M6 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M18 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M12 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M8 6h8 M7 7.8l4 8.4 M17 7.8l-4 8.4",
    diamond: "M12 3l9 9-9 9-9-9z M12 8l4 4-4 4-4-4z",
    // link chips: a tracker issue, a wiki page, a repo branch, an API spec, docs, a plain link
    tracker: "M4 4h16v16H4z M8 12l3 3 5-6",
    wiki: "M6 3h12v18H6z M9 8c1.5-1 3 1 4.5 0 M9 12h6 M9 16h4",
    repo: "M6 3v12 M6 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M18 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M18 9c0 5-12 3-12 8",
    api: "M9 4c-2 0-3 1-3 3v2l-2 3 2 3v2c0 2 1 3 3 3 M15 4c2 0 3 1 3 3v2l2 3-2 3v2c0 2-1 3-3 3",
    docs: "M6 3h9l4 4v14H6z M15 3v4h4 M9 12h7 M9 16h7",
    link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  };
  const FALLBACK = "cube";
  const name = (key) => { const x = (D.icons || {})[key]; return x && G[x.icon] ? x.icon : FALLBACK; };
  const why = (key) => { const x = (D.icons || {})[key]; return x ? x.why : ""; };
  /* HTML: an inline <svg> that sizes with the text. */
  function el(glyph, cls) {
    const svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("aria-hidden", "true"); svg.setAttribute("class", "ico" + (cls ? " " + cls : ""));
    s("path", { d: G[glyph] || G[FALLBACK] }, svg);
    return svg;
  }
  const forKey = (key, cls) => { const node = el(name(key), cls); const t = why(key); if (t) node.appendChild(document.createElementNS(SVGNS, "title")).textContent = `Icon: ${t}`; return node; };
  /* SVG: a glyph of `size` centred on (cx, cy), in the current text colour of its parent. */
  function put(parent, glyph, cx, cy, size, cls) {
    const k = size / 24;
    const g = s("g", { class: "glyph" + (cls ? " " + cls : ""), transform: `translate(${(cx - size / 2).toFixed(1)},${(cy - size / 2).toFixed(1)}) scale(${k.toFixed(3)})` }, parent);
    s("path", { d: G[glyph] || G[FALLBACK], "stroke-width": size < 16 ? 2.3 : 1.8 }, g);
    return g;
  }
  /* Canvas: the glyph as a Path2D on the 24 grid; the caller scales and strokes it. */
  const paths = {};
  const path = (glyph) => paths[glyph] || (paths[glyph] = new Path2D(G[glyph] || G[FALLBACK]));
  function stroke(ctx, glyph, cx, cy, size, colour) {
    const k = size / 24;
    ctx.save(); ctx.translate(cx - size / 2, cy - size / 2); ctx.scale(k, k);
    ctx.strokeStyle = colour; ctx.lineWidth = 1.8; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(path(glyph));
    ctx.restore();
  }
  return { G, name, why, el, forKey, put, stroke, has: (g) => !!G[g] };
})();
