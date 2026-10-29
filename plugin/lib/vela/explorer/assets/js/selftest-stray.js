/* ------------------------------------------------------------ Stray text (every view)
   A value turned into words by accident: native append prints a list as "[object HTMLDivElement],..." and a null as
   "null"; a template prints a missing field as "undefined" and a bad sum as "NaN". The checks before this one assert
   what each view should say; none can list everything it shouldn't. So this one watches every text and label the whole
   selftest puts on the page, in every view and panel it opens, and names each slip with the view it was in. Code blocks
   are left alone: a plan's own JSON can hold a null. */
(() => {
  const base = SelfTest.run;
  const SLIP = /\[object \w+\]|\bundefined\b|\bNaN\b|^\s*null\s*$|[\s:(,]null(?=[\s,.)]|$)|^null[\s,.)]/;
  const LABELS = ["title", "aria-label", "alt", "placeholder"];
  const inCode = (node) => !!(node.parentElement && node.parentElement.closest("pre, code, script, style, textarea"));
  // The element a slip landed in and its parent, by tag and class, so the line points at the code that drew it.
  const one = (el) => (el ? el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\s+/).join(".") : "") : "?");
  const placeOf = (node) => { const el = node && (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement); return `${one(el && el.parentElement)} > ${one(el)}`; };
  const where = () => `${App.view}${Nav.st && Nav.st.child ? " " + Nav.st.child : ""}`;

  function watch(seen) {
    const note = (text, how, at) => {
      if (!text || !SLIP.test(text)) return;
      seen.add(`${where()}: ${how} "${text.trim().slice(0, 70)}" in ${placeOf(at)}`);
    };
    const look = (node) => {
      if (node.nodeType === Node.TEXT_NODE) { if (!inCode(node)) note(node.nodeValue, "text", node); return; }
      if (node.nodeType !== Node.ELEMENT_NODE || node.closest("pre, code, script, style, textarea")) return;
      for (const a of LABELS) if (node.hasAttribute(a)) note(node.getAttribute(a), a, node);
      const walk = document.createTreeWalker(node, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
      for (let n = walk.nextNode(); n; n = walk.nextNode()) {
        if (n.nodeType === Node.TEXT_NODE) { if (!inCode(n)) note(n.nodeValue, "text", n); }
        else for (const a of LABELS) if (n.hasAttribute(a) && !n.closest("pre, code")) note(n.getAttribute(a), a, n);
      }
    };
    const observer = new MutationObserver((changes) => {
      for (const c of changes) {
        if (c.type === "childList") c.addedNodes.forEach(look);
        else if (c.type === "characterData") { if (!inCode(c.target)) note(c.target.nodeValue, "text", c.target); }
        else if (c.type === "attributes") note(c.target.getAttribute(c.attributeName), c.attributeName, c.target);
      }
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: LABELS });
    look(document.body);
    return observer;
  }

  SelfTest.run = async () => {
    const seen = new Set(), observer = watch(seen);
    let report;
    try { report = await base(); } finally { observer.disconnect(); }
    const slips = [...seen];
    const line = slips.length
      ? `FAIL stray text: ${slips.length} place${slips.length === 1 ? "" : "s"} printed a value by accident: ${slips.slice(0, 8).join(" | ")}`
      : "ok stray text: no view printed \"null\", \"undefined\", \"NaN\" or \"[object ...]\" in the whole selftest";
    const body = report.slice(1).concat([line]), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
