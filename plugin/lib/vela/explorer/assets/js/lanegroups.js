/* Lane groups on the Flows view: the Group button, the picker it opens, a group's panel, and the rows that name a group in the list under the diagram.
   What a group is, how it draws and what the address carries are flowview.js and flowkit.js; this file only asks the reader and says what a group is.

   The Violation this exists to prevent is a Leaky Narrative on the canvas: a way to group lanes that only a modifier-click on pixels could reach, which a
   reader on a call could not find and a keyboard could not use. Every way to make, rename, hide and undo a group is a real control: a button in the header
   (or the G key), a dialog of checkboxes, and buttons on the group's row in the list and in its panel. */
const LaneGroups = (() => {
  let pop = null, closing = null;  // the picker on the page; how to take its listeners off

  const nameFor = (ids) => { const n = ids.map(titleOf); return n.length === 0 ? "" : n.length === 1 ? n[0] : n.length === 2 ? `${n[0]} and ${n[1]}` : `${n[0]} and ${n.length - 1} more`; };
  const toGroup = (key) => FlowView.laneIds(key).length >= 3;  // two to group and one left out

  /* The header button: "Group", or "Grouped · 2" once there are groups. */
  function button(key, onOpen) {
    if (!toGroup(key)) return null;
    const n = FlowView.groupsFor(key).length;
    return h("button", { class: "dmenu-btn group-btn", id: "group-btn", type: "button", "aria-haspopup": "dialog", "aria-controls": "group-picker", "aria-expanded": String(!!pop), "aria-pressed": String(n > 0),
      "aria-label": n ? `Grouped, ${plural(n, "group")}` : "Group lanes", title: "Draw lanes as one lane (G)", onclick: onOpen },
    icon(), h("span", {}, n ? `Grouped · ${n}` : "Group"));
  }
  function icon() {
    const el = s("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 1.8 });
    el.innerHTML = '<rect x="3.5" y="5" width="17" height="14" rx="3"/><circle cx="8.5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="15.5" cy="12" r="1.6"/>';
    return el;
  }

  const isOpen = () => !!pop;
  function close(back = true) {
    if (!pop) return;
    pop.remove(); pop = null;
    if (closing) closing(); closing = null;
    const b = $("#group-btn");
    if (b) b.setAttribute("aria-expanded", "false");
    if (back && b) b.focus();
  }

  /* The picker: suggestions to take in one click, a checkbox for each lane of this flow, a name, and one way to finish. */
  function open(key) {
    close(false);
    const ids = FlowView.laneIds(key), stage = FlowView.groupsFor(key), inGroup = {};
    for (const g of stage) for (const m of g.members) inGroup[m] = g.name;
    const checked = new Set(), box = {}, dots = (members) => members.map((m) => h("i", { class: "gp-dot", style: `background:${FlowKit.laneColor(m)}` }));
    let typed = false;
    const name = h("input", { type: "text", id: "gp-name", value: "", "aria-label": "Call it", autocomplete: "off", spellcheck: "false", oninput: () => { typed = true; } });
    const go = h("button", { class: "btn primary", type: "button", id: "gp-go", disabled: true, onclick: () => finish() }, "Group these");
    const warn = h("div", { class: "gp-warn", role: "status", "aria-live": "polite" });
    function paint() {
      const n = checked.size, all = n >= ids.length;
      go.disabled = n < 2 || all;
      go.textContent = n >= 2 ? `Group these ${n}` : "Group these";
      warn.textContent = all ? "Leave at least one lane out" : "";
      if (!typed) name.value = nameFor(ids.filter((id) => checked.has(id)));
    }
    function pick(members) {
      checked.clear(); members.filter((m) => !inGroup[m]).forEach((m) => checked.add(m));
      ids.forEach((id) => { if (box[id]) box[id].checked = checked.has(id); });
      typed = false; paint();
    }
    function finish() {
      if (go.disabled) return;
      const members = ids.filter((id) => checked.has(id)), text = name.value;
      close(true);
      FlowView.makeGroup(key, text, members);
      const b = $("#group-btn"); if (b) b.focus();
    }
    const offered = FlowView.suggestions(key);
    const suggested = offered.length ? [h("div", { class: "gp-h" }, "Suggested"),
      offered.map((g) => h("button", { class: "gp-sugg", type: "button", "data-suggest": g.name, onclick: () => { pick(g.members); name.value = g.name; typed = true; $("#gp-go").focus(); } },
        h("span", { class: "gp-sname" }, ...dots(g.members.slice(0, 3)), h("b", {}, g.name), h("i", {}, g.why)), h("span", { class: "gp-smem" }, g.members.map(titleOf).join(", "))))] : [];
    const lanes = ids.map((id) => {
      const taken = inGroup[id];
      const cb = h("input", { type: "checkbox", disabled: !!taken, "data-lane": id, onchange: () => { if (cb.checked) checked.add(id); else checked.delete(id); paint(); } });
      box[id] = cb;
      return h("label", { class: "gp-lane" + (taken ? " taken" : "") }, cb, h("i", { class: "gp-dot", style: `background:${FlowKit.laneColor(id)}` }), h("span", {}, titleOf(id)), taken ? h("em", {}, `in ${taken}`) : null);
    });
    pop = h("div", { class: "gp", id: "group-picker", role: "dialog", "aria-label": "Group lanes", "data-group-picker": key },
      h("h3", {}, "Group lanes"), h("p", { class: "gp-help" }, "Pick two or more lanes to draw as one."),
      ...suggested, h("div", { class: "gp-h" }, "Or pick them"), h("div", { class: "gp-lanes" }, lanes),
      h("label", { class: "gp-name" }, h("span", {}, "Call it"), name), warn,
      h("div", { class: "gp-act" }, go, h("button", { class: "btn", type: "button", id: "gp-cancel", onclick: () => close(true) }, "Cancel"),
        h("span", { class: "gp-hint" }, h("kbd", {}, "G"), " opens this · ", h("kbd", {}, "Esc"), " closes")));
    document.body.append(pop);
    place(pop);
    const out = (e) => { if (pop && !pop.contains(e.target) && !(e.target.closest && e.target.closest("#group-btn"))) close(false); };
    const keys = (e) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(true); }
      else if (e.key === "Enter" && e.target === name) { e.preventDefault(); finish(); }
      else if (e.key === "Tab") trap(e);
    };
    document.addEventListener("pointerdown", out, true); pop.addEventListener("keydown", keys);
    closing = () => document.removeEventListener("pointerdown", out, true);
    const b = $("#group-btn"); if (b) b.setAttribute("aria-expanded", "true");
    paint();
    const first = pop.querySelector(".gp-sugg") || pop.querySelector("input[type=checkbox]:not(:disabled)");
    if (first) first.focus();
  }
  /* Under the button, kept on the page; a narrow window gets the room it has. */
  function place(el) {
    const b = $("#group-btn"), r = b ? b.getBoundingClientRect() : { left: 24, bottom: 60 };
    const width = Math.min(520, window.innerWidth - 24);
    el.style.width = width + "px";
    el.style.left = Math.max(12, Math.min(r.left, window.innerWidth - width - 12)) + "px";
    // under the button; a short window moves it up to keep the Group these button on the page, and scrolls what does not fit
    const top = Math.max(8, Math.min(r.bottom + 6, window.innerHeight - 300));
    el.style.top = top + "px";
    el.style.maxHeight = window.innerHeight - top - 8 + "px";
  }
  function trap(e) {
    const f = $$("button:not(:disabled),input:not(:disabled)", pop);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  /* G, like F for Simplify: not while typing, not with Ctrl, Cmd or Alt. */
  document.addEventListener("keydown", (e) => {
    if (e.key.toLowerCase() !== "g" || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.closest && e.target.closest("input,textarea,select,[contenteditable]")) return;
    if (App.view !== "flows" || !$("#overlay").hidden || !Flows.st.key || !toGroup(Flows.st.key)) return;
    e.preventDefault();
    if (pop) close(true); else open(Flows.st.key);
  });

  /* ------------------------------------------------------------ the panel */
  /* Who a group talks to outside itself, from the flow whole: "Booking (3 contracts) and Channels (1 step)". */
  function talksTo(key, g) {
    const plain = FlowKit.flowOf(key, { plain: true }), mine = new Set(g.members), stage = FlowView.groupsFor(key), memberOf = {};
    for (const x of stage) for (const m of x.members) memberOf[m] = x.name;
    const partners = new Map(), inner = [];
    for (const s of plain.steps) {
      if (s.messages.length && s.messages.every((m) => mine.has(m.from) && mine.has(m.to))) inner.push(s.n);
      for (const m of s.messages) {
        const other = mine.has(m.from) && !mine.has(m.to) ? m.to : mine.has(m.to) && !mine.has(m.from) ? m.from : null;
        if (!other) continue;
        const label = memberOf[other] || titleOf(other), p = partners.get(label) || { cons: new Set(), steps: new Set() };
        if (m.contract) p.cons.add(m.contract);
        p.steps.add(s.n); partners.set(label, p);
      }
    }
    const said = [...partners].map(([label, p]) => `${label} (${p.cons.size ? plural(p.cons.size, "contract") : plural(p.steps.size, "step")})`);
    const out = said.length ? `Talks to ${said.length > 1 ? said.slice(0, -1).join(", ") + " and " + said[said.length - 1] : said[0]}.` : "Talks to nothing outside itself in this flow.";
    return out + " " + (inner.length ? `${plural(inner.length, "step")} (${inner.join(", ")}) pass${inner.length === 1 ? "es" : ""} between its own lanes.` : "Nothing passes between its own lanes in this flow.");
  }
  /* A group's details, in the Details panel. */
  function panel(key, id) {
    const g = FlowView.groupsFor(key).find((x) => x.id === id);
    if (!g) return [h("div", { class: "p-empty" }, "That group isn't drawn on this flow any more. Pick it again.")];
    const n = g.members.length, hidden = FlowView.isHidden(key, id);
    const who = g.source === "page" ? "A group the flow page writes." : "A group you made on this flow.";
    const rename = h("span", { class: "gp-rename" });
    const startRename = () => {
      const input = h("input", { type: "text", value: g.name, "aria-label": "Group name", autocomplete: "off" });
      const save = () => { const t = input.value.trim(); if (t && t !== g.name) { if (FlowView.renameGroup(key, id, t)) return input.focus(); const next = FlowView.groupsFor(key).find((x) => x.name === t); DetailsPanel.show(next ? next.id : id, { reset: true }); } else paintBack(); };
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); save(); } else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); paintBack(); } });
      rename.replaceChildren(input, h("button", { class: "btn tiny", type: "button", onclick: save }, "Save"), h("button", { class: "btn tiny", type: "button", onclick: () => paintBack() }, "Cancel"));
      input.focus(); input.select();
    };
    const paintBack = () => rename.replaceChildren(h("button", { class: "btn tiny", type: "button", onclick: startRename }, "Rename"));
    paintBack();
    return [PlanDetails.head("Group", g.name, h("span", { class: "pill" }, `group of ${n}`)),
      h("div", { class: "p-body" },
        h("div", { class: "prose" }, h("div", { class: "prose-text" }, `${who} It draws ${n === 3 ? "three" : n} lanes as one: `, ...PlanDetails.joined(g.members.map((m) => PlanDetails.link(m))), ".")),
        h("div", { class: "p-note" }, talksTo(key, g)),
        h("div", { class: "p-actions gp-actions" }, rename,
          h("button", { class: "btn tiny", type: "button", "data-ungroup": id, onclick: () => FlowView.ungroup(key, id) }, "Ungroup"),
          h("button", { class: "btn tiny", type: "button", "aria-pressed": String(hidden), onclick: () => (hidden ? FlowView.show(key, id) : FlowView.hide(key, id)) }, hidden ? "Show" : "Hide")),
        h("div", { class: "p-note" }, g.source === "page" ? "Written on the flow page, so the flow opens this way. Ungroup is kept in this page's address, so a link you send opens it the way you left it."
          : "Kept in this page's address, so a link you send opens the flow grouped the same way."))];
  }

  return { button, open, close, isOpen, panel, nameFor, toGroup };
})();
