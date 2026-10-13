/* The flow picker: one button that names the flow you are on and opens a searchable list of every flow. It replaces
   the strip of flow tabs, which ran off the page at about eight flows. The Flows view and the line map's Lines key
   both use it, so a flow is chosen the same way everywhere.

   Up to TEN_FLOWS flows the list is flat, in the vault's own order (the flow numbers, which is the order the story is
   told in and the order the sidebar lists them). Past that it is grouped, so a reader scans a handful of headings
   before a long run of names:
     1. the capability the flow serves, as its `capabilities:` frontmatter records it (first is primary);
     2. else the capability its steps' "Uses [[CAP-...]]" lines suggest, under a heading that says it is a guess;
     3. else the domain most of the apps it crosses carry;
     4. else "Other".
   A flow serving several capabilities sits under its first and names the others on its muted line. The grouping is
   decided by how many flows the vault holds, never by how many match what was typed, so the list does not change
   shape under the reader's fingers while they filter.

   Inside a group the flows run most-urgent lamp first, then by name. A reader opening the list mid-conversation is
   looking for what needs them; the name is the tie-break, so the order is the same every time the lamps agree.
   The groups themselves run alphabetically (recorded capabilities, guessed ones, domains, then Other) so a heading is found where it
   was left and does not jump when a lamp changes.

   The grouping and filtering are plain functions over the record (arrange); the widget only draws what they return. */
const FlowPicker = (() => {
  Legend.define("list.swatch", [Legend.ln({ stroke: "line-grey", w: 4 })], "Coloured bar: the colour this flow has on the line map");
  const TEN_FLOWS = 10;
  let uid = 0, pendingFocus = null;  // choosing redraws the whole view; the new button takes the focus the old one held

  function entry(f) {
    const open = FlowKit.flowQuestions(f).filter((id) => ASK[id].state === "open").length;
    const caps = (f.capabilities || []).filter((k) => E[k]).map((k) => E[k].title);
    return { key: f.key, id: E[f.key].id, title: E[f.key].title, level: levelOf(f.key), steps: f.steps.length, open, caps, guessed: f.capabilitiesFrom === "steps", domain: f.domain || "" };
  }
  const entries = () => D.flows.map(entry);

  function groupOf(e) {
    if (e.caps.length) return { kind: e.guessed ? "guessed" : "capability", name: e.caps[0] };
    if (e.domain) return { kind: "domain", name: e.domain };
    return { kind: "other", name: "Other" };
  }
  const GROUP_ORDER = { capability: 0, guessed: 1, domain: 2, other: 3 };
  const urgent = (a, b) => rank(b.level) - rank(a.level) || a.title.localeCompare(b.title);
  const matches = (e, q) => !q || [e.title, e.id, ...e.caps, e.domain].some((t) => t.toLowerCase().includes(q));

  /* The list as drawn: [{ heading: null | { kind, name }, items: [entry], total }] for the query, and whether it is
     grouped. `total` is the group's size before filtering, so a heading can say "2 of 5" while a query narrows it. */
  function arrange(all, query) {
    const q = String(query || "").trim().toLowerCase();
    const shown = all.filter((e) => matches(e, q));
    if (all.length <= TEN_FLOWS) return { grouped: false, groups: [{ heading: null, items: shown, total: all.length }], count: shown.length };
    const sizes = {};
    for (const e of all) { const g = groupOf(e); sizes[g.kind + ":" + g.name] = (sizes[g.kind + ":" + g.name] || 0) + 1; }
    const byGroup = new Map();
    for (const e of shown) {
      const g = groupOf(e), id = g.kind + ":" + g.name;
      if (!byGroup.has(id)) byGroup.set(id, { heading: g, items: [], total: sizes[id] });
      byGroup.get(id).items.push(e);
    }
    const groups = [...byGroup.values()].sort((a, b) => GROUP_ORDER[a.heading.kind] - GROUP_ORDER[b.heading.kind] || a.heading.name.localeCompare(b.heading.name));
    groups.forEach((g) => g.items.sort(urgent));
    return { grouped: true, groups, count: shown.length };
  }

  const mutedLine = (e, grouped) => {
    const bits = [plural(e.steps, "step")];
    if (e.open) bits.push(plural(e.open, "open question"));
    const pl = Releases.tracerPlace(e.key);
    if (pl) bits.push(`${Releases.tracerPlaceWords(pl)} in the tracer`);
    if (grouped && e.caps.length > 1) bits.push(`also serves ${e.caps.slice(1).join(", ")}`);
    return bits.join(" · ");
  };
  const headingText = (g) => (g.kind === "domain" ? `${g.name} (domain)` : g.kind === "guessed" ? `${g.name} (guessed from the flow's steps)` : g.name);

  /* make({ current, onPick, none, swatch })
       current  () => the chosen flow key, or null
       onPick   (key | null) => void; null only when `none` is given
       none     the words for "no flow chosen" ("Every line"), or null when a flow must be chosen
       swatch   (key) => colour, to draw the line's colour beside the name, or null
     Returns the element; el.refresh() redraws the button after the choice changed somewhere else. */
  function make({ current, onPick, none = null, swatch = null, label = "Flow" }) {
    const id = ++uid, listId = `fp-list-${id}`;
    let open = false, query = "", active = -1, options = [];
    const wrap = h("div", { class: "flow-picker" });
    const trigger = h("button", { class: "fp-trigger", type: "button", "aria-haspopup": "listbox", "aria-expanded": "false", "aria-controls": listId });
    const input = h("input", { class: "fp-input", type: "text", role: "combobox", autocomplete: "off", spellcheck: "false", "aria-expanded": "false",
      "aria-controls": listId, "aria-autocomplete": "list", "aria-label": `Find a ${label.toLowerCase()}`, placeholder: `Find a ${label.toLowerCase()}, ${D.flows.length} in all` });
    const list = h("div", { class: "fp-list", id: listId, role: "listbox", "aria-label": `${label}s` });
    const status = h("div", { class: "fp-status", role: "status", "aria-live": "polite" });
    const pop = h("div", { class: "fp-pop", hidden: "" }, input, list, status);
    // what the little marks in front of each flow mean; the key is folded until a reader opens it
    const key = Legend.open(label === "Flow" ? "flows-list" : "lines-list", { root: () => pop, open: false,
      probes: { "list.swatch": ".fp-opt .swatch", ...Legend.lampProbes((lv) => `.fp-opt .lamp.${lv}`) } });
    pop.append(key.el());
    key.el().classList.add("tight");
    wrap.append(trigger, pop);

    const swatchEl = (key) => (swatch && key ? h("span", { class: "swatch", style: `--c:${swatch(key)}` }) : null);
    function caret() {
      const el = s("svg", { class: "fp-caret", viewBox: "0 0 12 12", "aria-hidden": "true" });
      el.innerHTML = '<path d="M2 4.5l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6"/>';
      return el;
    }
    function paintTrigger() {
      const key = current(), e = key && FLOW[key] ? entry(FLOW[key]) : null;
      trigger.innerHTML = "";
      const parts = e ? [swatchEl(e.key), lampEl(e.level), h("span", { class: "fp-name" }, e.title)] : [h("span", { class: "fp-name" }, none || "Choose")];
      trigger.append(h("span", { class: "fp-kind" }, label), ...parts.filter(Boolean), caret());  // native append prints a null as "null"
      trigger.setAttribute("aria-label", `${label}: ${e ? e.title : none || "none chosen"}. Choose another`);
    }

    function option(e, grouped) {
      const on = e.key === current();
      key.saw("lamp." + e.level); if (swatch) key.saw("list.swatch");
      return h("div", { class: "fp-opt" + (on ? " on" : ""), role: "option", id: `fp-${id}-${options.length}`, "aria-selected": String(on), "data-flow": e.key,
        onmousedown: (ev) => ev.preventDefault(), onclick: () => choose(e.key), onmousemove: () => { const at = options.findIndex((o) => o.key === e.key); if (at !== active) setActive(at, false); } },
        swatchEl(e.key), lampEl(e.level),
        h("span", { class: "fp-text" }, h("span", { class: "fp-title" }, e.title, Releases.tracerTag(e.key)), h("small", {}, mutedLine(e, grouped))));
    }
    function noneOption() {
      const on = current() === null;
      return h("div", { class: "fp-opt fp-none" + (on ? " on" : ""), role: "option", id: `fp-${id}-${options.length}`, "aria-selected": String(on), "data-flow": "",
        onmousedown: (ev) => ev.preventDefault(), onclick: () => choose(null), onmousemove: () => { const at = options.findIndex((o) => o.key === null); if (at !== active) setActive(at, false); } },
        h("span", { class: "fp-text" }, h("span", { class: "fp-title" }, none)));
    }
    function paintList() {
      const plan = arrange(entries(), query);
      list.innerHTML = ""; options = []; key.seen.clear();
      if (none && !query.trim()) { list.append(noneOption()); options.push({ key: null }); }
      for (const g of plan.groups) {
        if (!g.items.length) continue;
        const items = g.items.map((e) => { const el = option(e, plan.grouped); options.push({ key: e.key }); return el; });
        if (!g.heading) { list.append(...items); continue; }
        const hid = `fp-${id}-h${options.length}`, n = g.items.length === g.total ? String(g.total) : `${g.items.length} of ${g.total}`;
        list.append(h("div", { class: "fp-group", role: "group", "aria-labelledby": hid },
          h("div", { class: "fp-head", id: hid }, h("span", {}, headingText(g.heading)), h("span", { class: "fp-count" }, n)), ...items));
      }
      key.paint();
      status.textContent = plan.count ? (query.trim() ? `${plural(plan.count, "flow")} match` : "") : "No flow matches";
      if (!plan.count) list.append(h("div", { class: "fp-empty" }, `No flow matches "${query.trim()}".`));
      const at = options.findIndex((o) => o.key === current());
      setActive(query.trim() ? 0 : Math.max(0, at), true);
    }
    function setActive(at, scroll) {
      active = options.length ? (at + options.length) % options.length : -1;
      $$(".fp-opt", list).forEach((el, i) => el.classList.toggle("active", i === active));
      const el = active >= 0 ? $$(".fp-opt", list)[active] : null;
      if (el) { input.setAttribute("aria-activedescendant", el.id); if (scroll) el.scrollIntoView({ block: "nearest" }); }
      else input.removeAttribute("aria-activedescendant");
    }
    function show() {
      if (open) return;
      open = true; query = ""; input.value = "";
      pop.hidden = false; trigger.setAttribute("aria-expanded", "true"); input.setAttribute("aria-expanded", "true");
      paintList(); input.focus();
      document.addEventListener("pointerdown", outside, true);
    }
    function hide(refocus) {
      if (!open) return;
      open = false; pop.hidden = true; trigger.setAttribute("aria-expanded", "false"); input.setAttribute("aria-expanded", "false");
      document.removeEventListener("pointerdown", outside, true);
      if (refocus) trigger.focus();
    }
    const outside = (ev) => { if (!wrap.contains(ev.target)) hide(false); };
    function choose(key) { hide(true); pendingFocus = label; onPick(key); pendingFocus = null; paintTrigger(); }

    trigger.addEventListener("click", () => (open ? hide(true) : show()));
    // The Flows view plays on Space and steps on the arrows; a key meant for the picker must not reach it.
    trigger.addEventListener("keydown", (ev) => {
      if (["ArrowDown", "ArrowUp", " ", "Enter"].includes(ev.key)) { ev.stopPropagation(); if (ev.key.startsWith("Arrow")) { ev.preventDefault(); show(); } }
    });
    input.addEventListener("input", () => { query = input.value; paintList(); });
    input.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "ArrowDown") { ev.preventDefault(); setActive(active + 1, true); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); setActive(active - 1, true); }
      else if (ev.key === "Home") { ev.preventDefault(); setActive(0, true); }
      else if (ev.key === "End") { ev.preventDefault(); setActive(options.length - 1, true); }
      else if (ev.key === "Enter") { ev.preventDefault(); if (active >= 0) choose(options[active].key); }
      else if (ev.key === "Escape") { ev.preventDefault(); hide(true); }
      else if (ev.key === "Tab") hide(false);
    });
    wrap.open = show;
    wrap.refresh = () => { paintTrigger(); if (open) paintList(); };
    paintTrigger();
    if (pendingFocus === label) { pendingFocus = null; queueMicrotask(() => { if (trigger.isConnected) trigger.focus(); }); }
    return wrap;
  }

  return { make, arrange, entries, TEN_FLOWS };
})();
