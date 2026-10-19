/* Menus on the diagram. A view's choices (which view, which grouping, what to do with the layout) sit in a bar on the
   top of the diagram they change, as real menus, so the diagram starts right under the section's title and lede and
   the page carries no rows of toggles above it.

   A menu is a button that opens a list: role "menu" with "menuitem", "menuitemradio" or "menuitemcheckbox" items,
   aria-expanded on the button, and the keys a menu button has everywhere: Enter, Space or Down opens it on the chosen
   item, Up and Down move, Home and End jump, Escape closes it and gives the focus back, Tab leaves it, and a click or
   focus outside closes it. Only one is open at a time. The list is solid, so it reads over any diagram, in every theme
   and in Plain. An item is {id, label, say, checked, checkbox, disabled, why, run} or {href, newTab} for a link, plus
   {heading} and {separator}. `items` may be a function, asked again each time the menu opens, so a menu never shows what
   was true when the page was drawn. Picking an item closes the menu, runs it, and puts the focus back on the menu's
   button, which the item's redraw may have replaced. */
const Menus = (() => {
  const ITEM = '[role="menuitem"]:not([aria-disabled="true"]), [role="menuitemradio"]:not([aria-disabled="true"]), [role="menuitemcheckbox"]:not([aria-disabled="true"])';
  let openNow = null, seq = 0;

  function closeNow(giveBackFocus) {
    if (!openNow) return;
    const { btn, pop } = openNow;
    openNow = null;
    pop.hidden = true; btn.setAttribute("aria-expanded", "false");
    if (giveBackFocus && btn.isConnected) btn.focus();
  }
  document.addEventListener("pointerdown", (e) => { if (openNow && !openNow.root.contains(e.target)) closeNow(false); }, true);
  document.addEventListener("focusin", (e) => { if (openNow && !openNow.root.contains(e.target)) closeNow(false); });
  addEventListener("resize", () => { if (openNow) openNow.place(); });  // the list stays open and finds its place again

  const itemsOf = (pop) => [...pop.querySelectorAll(ITEM)];
  function focusItem(pop, i) { const list = itemsOf(pop); if (list.length) list[(i + list.length) % list.length].focus(); }

  function icon(kind) {
    const paths = {
      more: '<circle cx="5" cy="12" r="1.7" fill="currentColor"/><circle cx="12" cy="12" r="1.7" fill="currentColor"/><circle cx="19" cy="12" r="1.7" fill="currentColor"/>',
      focus: '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="2.6" fill="currentColor"/>',
    };
    const el = s("svg", { viewBox: "0 0 24 24", class: "dbtn-ico", "aria-hidden": "true" });
    el.innerHTML = paths[kind];
    return el;
  }

  function fill(pop, id, items, finish) {
    pop.replaceChildren();
    for (const it of typeof items === "function" ? items() : items) {
      if (!it) continue;
      if (it.separator) { pop.append(h("div", { class: "dmenu-sep", role: "separator" })); continue; }
      if (it.node) { pop.append(h("div", { class: "dmenu-node", role: "presentation" }, it.node)); continue; }
      if (it.heading) { pop.append(h("div", { class: "dmenu-h", role: "presentation" }, it.heading)); continue; }
      const role = it.checkbox ? "menuitemcheckbox" : it.checked === undefined ? "menuitem" : "menuitemradio";
      const attrs = { class: "dmenu-item" + (it.disabled ? " off" : ""), role, tabindex: "-1", title: it.disabled && it.why ? it.why : it.say || null,
        "data-item": it.id || null, ...(it.attrs || {}) };
      if (role !== "menuitem") attrs["aria-checked"] = String(!!it.checked);
      if (it.disabled) attrs["aria-disabled"] = "true";
      const kids = [h("span", { class: "mi-l" }, it.label), it.say ? h("small", {}, it.say) : null].filter(Boolean);
      let el;
      if (it.href) el = h("a", { ...attrs, href: it.href, ...(it.newTab ? { target: "_blank", rel: "noopener" } : {}), onclick: () => finish(false) }, ...kids);
      else el = h("button", { ...attrs, type: "button", onclick: (e) => {
        if (it.disabled) { e.preventDefault(); return; }
        finish(true, it.run);
      } }, ...kids);
      pop.append(el);
    }
  }

  /* One menu. `kind: "choice"` shows what it sets ("View  System map"); `kind: "icon"` shows just its icon, named by `label`. */
  /* The right edge a menu keeps inside: in a narrow window the Details tab stands on the window's edge, and a menu does not run under it. */
  const edge = (lim) => lim.right - (document.body.classList.contains("compact") && $("#panel-tab") && !$("#panel-tab").hidden ? 30 : 0);
  function menu({ id, kind = "choice", label, current, glyph, items, align = "left", title, extraClass = "" }) {
    const uid = `dmenu-${id}-${++seq}`;
    const btn = h("button", { class: "dmenu-btn" + (kind === "icon" ? " icon" : "") + (extraClass ? " " + extraClass : ""), type: "button", id: uid + "-btn", "aria-haspopup": "menu", "aria-expanded": "false", "aria-controls": uid,
      title: title || (kind === "icon" ? label : `${label}: ${current}`), ...(kind === "icon" ? { "aria-label": label } : {}) },
      kind === "icon" ? icon(glyph) : [h("small", {}, label), h("b", {}, current), h("span", { class: "caret", "aria-hidden": "true" }, "▾")]);
    const pop = h("div", { class: "dmenu-pop " + align, id: uid, role: "menu", "aria-labelledby": btn.id, hidden: true });
    const root = h("div", { class: "dmenu", "data-dmenu": id }, btn, pop);
    const finish = (refocus, run) => {
      closeNow(false);
      if (run) run();
      requestAnimationFrame(() => { if (refocus) { const again = btn.isConnected ? btn : document.querySelector(`[data-dmenu="${CSS.escape(id)}"] .dmenu-btn`); if (again) again.focus(); } });
    };
    fill(pop, id, items, finish);  // built now as well as when it opens, so the page holds its items before anyone asks
    function place() {
      pop.style.left = ""; pop.style.right = ""; pop.style.maxHeight = "";
      const frame = root.closest(".dia") || root.closest("#main") || document.body, lim = frame.getBoundingClientRect(), r = pop.getBoundingClientRect();
      if (align === "right") { if (r.left < lim.left + 6) pop.style.right = `${r.left - lim.left - 6}px`; }
      else if (r.right > edge(lim) - 6) pop.style.left = `${Math.min(0, edge(lim) - 6 - r.right)}px`;
      const room = innerHeight - r.top - 10;  // a short window: the menu scrolls inside itself rather than run off the bottom
      if (r.height > room) pop.style.maxHeight = `${Math.max(120, room)}px`;
    }
    function open(which) {
      if (openNow && openNow.pop === pop) { closeNow(true); return; }
      closeNow(false);
      fill(pop, id, items, finish);
      pop.hidden = false; btn.setAttribute("aria-expanded", "true");
      openNow = { root, btn, pop, place };
      place();
      const list = itemsOf(pop), chosen = list.findIndex((x) => x.getAttribute("aria-checked") === "true");
      focusItem(pop, which === "last" ? -1 : chosen >= 0 && which !== "first" ? chosen : 0);
    }
    btn.addEventListener("click", () => open());
    btn.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); open("first"); }
      else if (e.key === "ArrowUp") { e.preventDefault(); open("last"); }
    });
    pop.addEventListener("keydown", (e) => {
      const list = itemsOf(pop), at = list.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); focusItem(pop, at + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); focusItem(pop, at < 0 ? -1 : at - 1); }
      else if (e.key === "Home") { e.preventDefault(); focusItem(pop, 0); }
      else if (e.key === "End") { e.preventDefault(); focusItem(pop, -1); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeNow(true); }
      else if (e.key === "Tab") closeNow(false);
      else if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {  // a letter jumps to the next item that starts with it
        const k = e.key.toLowerCase(), order = [...list.slice(at + 1), ...list.slice(0, at + 1)];
        const hit = order.find((x) => x.textContent.trim().toLowerCase().startsWith(k));
        if (hit) { e.preventDefault(); hit.focus(); }
      }
    });
    return root;
  }

  /* A button that opens a small panel of its own content (the Key). It is one of the bar's popups like a menu is: only one
     is open at a time, Escape and a click outside close it, and it stays inside the diagram's width. */
  function popover({ id, label, text, content, align = "right" }) {
    const uid = `dmenu-${id}-${++seq}`;
    const btn = h("button", { class: "dmenu-btn icon", type: "button", id: uid + "-btn", "aria-haspopup": "dialog", "aria-expanded": "false", "aria-controls": uid, "aria-label": label, title: label }, text);
    const pop = h("div", { class: "dmenu-pop wide " + align, id: uid, role: "dialog", "aria-label": label, hidden: true }, content);
    const root = h("div", { class: "dmenu", "data-dmenu": id }, btn, pop);
    function place() {
      pop.style.left = ""; pop.style.right = ""; pop.style.maxHeight = "";
      const frame = root.closest(".dia") || root.closest("#main") || document.body, lim = frame.getBoundingClientRect(), r = pop.getBoundingClientRect();
      if (align === "right") { if (r.left < lim.left + 6) pop.style.right = `${r.left - lim.left - 6}px`; }
      else if (r.right > edge(lim) - 6) pop.style.left = `${Math.min(0, edge(lim) - 6 - r.right)}px`;
      const room = innerHeight - r.top - 10;  // a short window: the menu scrolls inside itself rather than run off the bottom
      if (r.height > room) pop.style.maxHeight = `${Math.max(120, room)}px`;
    }
    btn.addEventListener("click", () => {
      if (openNow && openNow.pop === pop) { closeNow(true); return; }
      closeNow(false);
      pop.hidden = false; btn.setAttribute("aria-expanded", "true");
      openNow = { root, btn, pop, place };
      place();
    });
    pop.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeNow(true); } });
    return root;
  }
  /* The Key of a diagram, as a "?" in the bar: its legend, kept out of the way until asked for. */
  function keyButton(legend) {
    if (!legend) return null;
    const host = legend.el();
    host.classList.add("in-pop"); host.open = true;
    return popover({ id: "key", label: "Key: what the colors and shapes mean", text: "?", content: host });
  }

  /* The bar over a diagram: menus on its left, the diagram's own buttons on its right, and a line of what to do between. */
  function frame({ left = [], right = [], say = [], barClass = "" }, ...kids) {
    const clean = (x) => x.filter(Boolean);
    return h("div", { class: "dia" },
      h("div", { class: "dia-bar" + (barClass ? " " + barClass : "") }, h("div", { class: "dia-l" }, ...clean(left)), h("div", { class: "dia-mid" }, ...clean(say)), h("div", { class: "dia-r" }, ...clean(right))),
      ...clean(kids));
  }
  return { menu, popover, keyButton, frame, icon, close: () => closeNow(false), get isOpen() { return !!openNow; } };
})();
