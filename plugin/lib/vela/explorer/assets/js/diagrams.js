/* Drawing a diagram the page has no drawing of its own for: a flowchart, a state diagram, an ER diagram, or a sequence the
   step-through reader (inside.js) can't read to the end. The bundled Mermaid renderer draws it, under the rules the
   offline viewer uses (mermaid-safe.js: strict mode, no diagram-borne configuration, the SVG cleaned before it is shown),
   and the drawing gets the same zoom and pan as every other drawing (pan.js). If Mermaid rejects the source, the reader
   gets its reason in plain words and the source, never an empty box. The renderer is inlined only when a design needs it
   (build.py), so a page built without it says so instead of failing. */
const Diagrams = (() => {
  let count = 0, turn = Promise.resolve(), stage = null;
  /* Mermaid measures a diagram in a box it adds to the page, and leaves it behind when it rejects one. It gets a box of its own, off
     screen, so nothing it adds or leaves can move the page; one diagram at a time, so one's cleanup never takes another's box. */
  const offscreen = () => stage || (stage = document.body.appendChild(h("div", { class: "mm-stage", "aria-hidden": "true" })));
  const inTurn = (work) => { const next = turn.then(work, work); turn = next.catch(() => {}); return next; };
  const isDark = () => {
    const hex = (Theme.c("room") || "").trim(), m = /^#([0-9a-f]{6})$/i.exec(hex);
    if (!m) return false;
    const n = parseInt(m[1], 16);
    return 0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255) < 128;
  };
  const firstLine = (e) => String((e && e.message) || e || "").split("\n").map((x) => x.trim()).find(Boolean) || "it isn't valid Mermaid";
  function failed(holder, why, source) {
    holder.dataset.drawn = "error";
    holder.className = "mm-error";
    holder.replaceChildren(h("div", { class: "muted small" }, `This diagram can't be drawn: ${why}. Here is its source.`), h("pre", { class: "in-src" }, source));
  }
  /* The element comes back at once; the drawing fills it when Mermaid is done. data-drawn is "yes" or "error" by then. */
  function draw(source, opts = {}) {
    const holder = h("div", { class: "mm-frame", "data-drawn": "pending", "data-mermaid": "1" }, h("span", { class: "muted small" }, "Drawing the diagram…"));
    const key = opts.key || "mermaid-" + (++count);
    (async () => {
      if (!window.mermaid) return failed(holder, "this page was built without the drawing library", source);
      if (hasDiagramConfig(source)) return failed(holder, "diagram directives aren't allowed in an offline page", source);
      const id = "mm-" + (++count);
      try {
        const { svg } = await inTurn(async () => {
          try { mermaid.initialize(mermaidSettings(isDark())); return await mermaid.render(id, source, offscreen()); } finally { offscreen().replaceChildren(); }
        });
        const frag = sanitizeSvg(svg), el = frag.querySelector("svg");
        if (!el) return failed(holder, "Mermaid drew nothing", source);
        el.removeAttribute("style"); el.removeAttribute("width"); el.removeAttribute("height");
        el.classList.add("mm-svg");
        el.setAttribute("role", "img"); el.setAttribute("aria-label", opts.label || "Diagram");
        holder.replaceChildren(el);
        holder.dataset.drawn = "yes";
        Pan.attach(holder, { key, svg: () => holder.querySelector("svg.mm-svg"), frame: holder });
      } catch (e) {
        failed(holder, firstLine(e), source);
      }
    })();
    return holder;
  }
  return { draw };
})();
