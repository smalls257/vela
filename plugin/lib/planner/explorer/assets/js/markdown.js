/* Markdown for Claude's answers. The answer is model output: it is read as untrusted, however polite it looks.
   marked (inlined once by build.py, vendored in plugin/lib/planner/assets) parses it, with raw HTML switched off and
   images turned into text; then everything it produced is rebuilt node by node from a short allowlist, so a tag, an
   attribute or a link scheme marked did not think of still cannot reach the page. Links keep only http, https and
   mailto, or an in-page `#ID` that the vault holds. The result is a DocumentFragment: no string of HTML is ever
   handed to innerHTML, and citation linking (ask.js) works on its text nodes. */
const Markdown = (() => {
  const TAGS = new Set(["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "strong", "em", "del", "code", "pre", "blockquote",
    "hr", "br", "table", "thead", "tbody", "tr", "th", "td", "sup", "sub"]);
  const ALIGN = new Set(["left", "center", "right"]);
  const SCHEME = /^([a-z][a-z0-9+.-]*):/i;
  let engine = null, warned = false;

  /* The href a link may keep: http(s), mailto, or an in-page #target. Entities and control characters are removed
     first, because a browser reads "java&#x73;cript:" and "java\tscript:" as javascript:. */
  function safeHref(raw) {
    const t = (raw || "").replace(/&#x([0-9a-f]+);?/gi, (_, n) => String.fromCodePoint(parseInt(n, 16))).replace(/&#(\d+);?/g, (_, n) => String.fromCodePoint(+n))
      .replace(/[\u0000- \u007f-\u009f]/g, "");
    if (t.startsWith("#") && t.length > 1) return t;
    const m = SCHEME.exec(t);
    return m && /^(https?|mailto)$/i.test(m[1]) ? t : null;
  }

  function parser() {
    if (engine) return engine;
    if (typeof marked === "undefined" || !marked.Marked) return null;
    engine = new marked.Marked({ gfm: true, breaks: false, async: false });
    engine.use({ renderer: {
      html: (html) => esc(html),  // raw HTML in an answer is shown as the text it is
      image: (href, title, text) => esc(text || "image"),  // an image would be a request to the network
      link: (href, title, text) => (safeHref(href) ? false : text),
    } });
    return engine;
  }

  /* Rebuild `from`'s children under `into`, keeping only what the allowlist names. */
  function rebuild(from, into) {
    for (const node of [...from.childNodes]) {
      if (node.nodeType === Node.TEXT_NODE) { into.append(node.nodeValue); continue; }
      if (node.nodeType !== Node.ELEMENT_NODE) continue;
      const tag = node.localName;
      if (tag === "input") { into.append(node.hasAttribute("checked") ? "☑ " : "☐ "); continue; }  // a task list's box
      if (!TAGS.has(tag)) { into.append(node.textContent); continue; }
      const keep = document.createElement(tag);
      if (tag === "a" && !decorate(node, keep)) { rebuild(node, into); continue; }
      if (tag === "ol" && /^\d{1,6}$/.test(node.getAttribute("start") || "")) keep.setAttribute("start", node.getAttribute("start"));
      if ((tag === "td" || tag === "th") && ALIGN.has(node.getAttribute("align"))) keep.className = "al-" + node.getAttribute("align");
      if (tag === "code" && /^language-[a-z0-9_+-]{1,30}$/i.test(node.className)) keep.setAttribute("data-lang", node.className.slice(9));
      rebuild(node, keep);
      into.append(tag === "table" ? h("div", { class: "md-table" }, keep) : keep);
    }
  }
  /* Set a link's attributes; false when it may not be a link at all (its text is kept). */
  function decorate(from, a) {
    const href = safeHref(from.getAttribute("href"));
    if (!href) return false;
    if (href.startsWith("#")) {
      const key = keyForId(decodeURIComponent(href.slice(1)).trim());
      if (!ent(key)) return false;
      a.setAttribute("data-ref", key);
      return true;
    }
    a.setAttribute("href", href);
    a.setAttribute("target", "_blank");
    a.setAttribute("rel", "noopener noreferrer");
    return true;
  }

  /* A growing answer is cut back to what is certain: a line that is only the start of a marker ("-", "1.", "|", "```")
     and a table's header row whose rule has not arrived would flash as text and then jump into their real shape.
     Prose is never held back, so the answer still reads as it arrives. */
  const MARKER_FRAGMENT = /^\s*(?:[-*+>|#:]+|\d+[.)]?|`{1,2}|~{1,2})?\s*$/;
  function stable(md) {
    const lines = md.split("\n");
    if (MARKER_FRAGMENT.test(lines[lines.length - 1])) lines.pop();
    const last = (lines[lines.length - 1] || "").trim(), before = (lines[lines.length - 2] || "").trim();
    if (last.startsWith("|") && !before.startsWith("|")) lines.pop();
    return lines.join("\n");
  }

  /* The answer as a fragment. `growing` is an answer still arriving. */
  function render(md, growing) {
    const frag = document.createDocumentFragment();
    const p = parser();
    if (!p) {
      if (!warned) { console.error("[markdown] marked is not on the page, so answers are shown as plain text"); warned = true; }
      frag.append(h("div", { class: "md-plain" }, md));
      return frag;
    }
    const holder = document.createElement("template");
    holder.innerHTML = p.parse(growing ? stable(md) : md);
    rebuild(holder.content, frag);
    return frag;
  }
  return { render, safeHref };
})();
