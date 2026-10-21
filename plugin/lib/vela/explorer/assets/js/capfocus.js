/* Capability focus: pick one capability and the map and the sidebar keep only what it touches. The rest is removed, not dimmed.

   What a capability touches comes from how the plan links it (read here, never guessed):
   - the apps whose Requirements allocated tables carry one of its requirements, and the contracts those rows go through;
   - the apps the epics that deliver it list, and the contracts those epics consume;
   - the flows that name it in `capabilities:`, the flows those epics list, and every app, outside service and contract their steps cross;
   - every contract above brings its provider and its consumers, so no line is left hanging.
   The focus is the capabilities section's open item (#s=capabilities&open=CAP-...), so a link reopens it and Nav's own
   hash is the only place it lives. Nav sets and clears it; the map and the sidebar read it. */
const CapFocus = (() => {
  const st = { key: "" };
  const cache = {};
  const set = (key) => { st.key = key && ent(key) && ent(key).kind === "capability" ? key : ""; };
  const key = () => st.key;
  const isIt = (k) => !!st.key && st.key === k;
  function compute(capKey) {
    const id = ent(capKey).id, nodes = new Set(), apps = new Set(), contracts = new Set(), flows = new Set(), epics = new Set();
    const reqs = new Set(D.trace.requirements.filter((r) => r.capability === id).map((r) => r.id));
    for (const row of D.trace.allocation) if (reqs.has(row.requirement)) { apps.add(row.app); row.through.forEach((c) => contracts.add(c)); }
    for (const [app, v] of Object.entries(D.appCaps)) if (v.caps.includes(id)) apps.add(app);
    for (const ep of D.trace.epics) {
      if (!ep.delivers.includes(id)) continue;
      epics.add(ep.key);
      ep.apps.forEach((a) => { const k = keyForId(a); if (NODE[k]) apps.add(k); });
      ep.consumes.forEach((c) => { if (CONTRACT[c]) contracts.add(c); });
      ep.flows.forEach((f) => { const k = keyForId(f); if (FLOW[k]) flows.add(k); });
    }
    for (const f of D.flows) if ((f.capabilities || []).includes(capKey)) flows.add(f.key);
    for (const f of D.flows) {
      if (!flows.has(f.key)) continue;
      for (const s of f.steps) for (const m of s.messages) { contracts.add(m.contract); nodes.add(m.from); nodes.add(m.to); }
    }
    for (const c of D.map.contracts) {
      if (!contracts.has(c.id)) continue;
      nodes.add(c.provider); c.consumers.forEach((k) => nodes.add(k));
    }
    apps.forEach((a) => nodes.add(a));
    for (const n of [...nodes]) if (!NODE[n]) nodes.delete(n);
    for (const c of [...contracts]) if (!CONTRACT[c]) contracts.delete(c);
    return { nodes, apps: new Set([...nodes].filter((k) => NODE[k].kind === "app")), contracts, flows, epics,
      empty: !nodes.size };
  }
  /* What the focused capability touches, or null when nothing is focused. */
  const scope = () => (st.key ? (cache[st.key] = cache[st.key] || compute(st.key)) : null);
  const showsNode = (k) => { const s = scope(); return !s || s.nodes.has(k); };
  const flows = () => { const s = scope(); return s ? D.flows.filter((f) => s.flows.has(f.key)) : D.flows; };
  const contracts = () => { const s = scope(); return s ? D.map.contracts.filter((c) => s.contracts.has(c.id)) : D.map.contracts; };
  /* The sidebar's lists: apps, flows and epics keep only what is touched. Other lists are not about a capability. */
  function kids(section) {
    const s = scope();
    if (!s) return section.children;
    const keep = section.id === "apps" ? s.apps : section.id === "flows" ? s.flows : section.id === "epics" ? s.epics : null;
    return keep ? section.children.filter((k) => keep.has(k)) : section.children;
  }
  const narrowed = (section) => !!scope() && ["apps", "flows", "epics"].includes(section.id);
  function summary() {
    const s = scope();
    return s ? `${plural(s.apps.size, "app")}, ${plural(s.contracts.size, "contract")}, ${plural(s.flows.size, "flow")}` : "";
  }
  /* "Showing <capability> only · Show everything", the same bar over the map and at the top of the sidebar. */
  function bar(where) {
    if (!st.key) return null;
    return h("div", { class: "capfocus-bar", "data-where": where, role: "status" },
      h("span", { class: "capfocus-say" }, "Showing ", h("b", {}, ent(st.key).title), " only", where === "map" ? h("span", { class: "capfocus-n" }, " · " + summary()) : null),
      h("button", { type: "button", class: "capfocus-clear", onclick: () => Nav.open("capabilities") }, "Show everything"));
  }
  const reset = () => { for (const k of Object.keys(cache)) delete cache[k]; };
  return { st, set, key, isIt, scope, showsNode, flows, contracts, kids, narrowed, summary, bar, reset };
})();
