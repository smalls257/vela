/* The vault's own pages, readable here. build.py renders each page in vela's reading order (reading.arrange)
   and escapes all of its text, so the HTML holds only the renderer's own tags. Here a page is placed, its links
   open inside the explorer, and an ID the prose names in plain text (CST-3, UNK-006) becomes a link too when the
   vault holds it. Anchors are item IDs (CON-001) or heading slugs, so "Open the page" lands on the item. */
const Reader = (() => {
  const ID_TEXT = /(?<![\w-])((?:APP|RUN|CAP|FLO|EPC|ADR|CON|UNK|PTY|SV|CST|R)-[\w]*\d+(?:\.FR\d+)?|G\d+)(?![\w-])/g;
  const pageOf = (key) => { const e = E[key]; if (!e) return null; return e.path ? key : e.pageKey || null; };
  /* "read:<page>#<anchor>" for anything: a page reads from its top, an item from its own heading. */
  function keyFor(key) {
    const e = ent(key);
    if (!e) return null;
    if (e.kind === "reader") return key;
    const pk = pageOf(key);
    if (!pk || !D.reader[pk]) return null;
    const anchored = !e.path && D.reader[pk].html.includes(`id="${key}"`);
    return "read:" + pk + (anchored ? "#" + key : "");
  }
  function linkify(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: (n) => n.parentElement.closest("a,code,pre,summary,h1,h2,h3,h4") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const text = node.nodeValue;
      ID_TEXT.lastIndex = 0;
      if (!ID_TEXT.test(text)) continue;
      ID_TEXT.lastIndex = 0;
      const frag = document.createDocumentFragment();
      let last = 0, m, any = false;
      while ((m = ID_TEXT.exec(text))) {
        const key = keyForId(m[1]);
        if (!ent(key)) continue;
        frag.append(text.slice(last, m.index), h("a", { class: "ref ref-id", "data-ref": key, title: titleOf(key) }, m[1]));
        last = m.index + m[1].length; any = true;
      }
      if (!any) continue;
      frag.append(text.slice(last));
      node.replaceWith(frag);
    }
  }
  /* The page's body, ready to place: its HTML, every link live, and a contents list when it has sections. */
  function body(pk, opts = {}) {
    const r = D.reader[pk];
    const box = h("div", { class: "reader" + (opts.wide ? " wide" : "") });
    if (!r) { box.append(h("p", { class: "muted" }, "This page isn't available here.")); return box; }
    const text = h("article", { class: "r-text", html: r.html });
    linkify(text);
    $$("a.ref", text).forEach((a) => { if (!ent(a.dataset.ref)) a.classList.add("ref-dead"); });
    const toc = r.toc.filter((t) => t.level === 2);
    if (opts.toc !== false && toc.length > 2) box.append(h("nav", { class: "r-toc", "aria-label": "On this page" }, h("div", { class: "r-toc-h" }, "On this page"),
      toc.map((t) => h("button", { class: "r-toc-link", onclick: () => scrollTo(box, t.id) }, t.text))));
    box.append(text);
    return box;
  }
  function scrollTo(root, anchor) {
    if (!anchor) return false;
    const el = root.querySelector(`[id="${CSS.escape(anchor)}"]`);
    if (!el) return false;
    el.scrollIntoView({ block: "start", behavior: reducedMotion() ? "auto" : "smooth" });
    el.classList.add("r-here");
    setTimeout(() => el.classList.remove("r-here"), 1800);
    return true;
  }
  return { body, keyFor, scrollTo, linkify, pageOf };
})();
