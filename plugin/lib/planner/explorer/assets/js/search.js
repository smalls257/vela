/* Search, in plain words. The ranking is planner.search's, ported: the same sections, stems, weights and order.
   build.py embeds the CLI's own answers to a few queries and #selftest compares the two, so drift shows up. */
const Search = (() => {
  const S = D.search, STOP = new Set(S.stop);
  /* planner.search.stem: drop one suffix, then a final "e", so place, places and placed all come to "plac". */
  function stem(w) {
    for (const suf of ["ing", "ies", "es", "ed", "s"]) {
      if (w.endsWith(suf) && w.length - suf.length >= 3) { w = w.slice(0, -suf.length) + (suf === "ies" ? "y" : ""); break; }
    }
    return w.endsWith("e") && w.length >= 4 ? w.slice(0, -1) : w;
  }
  function terms(q) {
    const seen = [];
    for (const w of (q.toLowerCase().match(/[a-z0-9]+/g) || [])) { const st = stem(w); if (!STOP.has(w) && !seen.includes(st)) seen.push(st); }
    return seen;
  }
  const ROWS = S.rows.map((r) => ({ ...r, sets: [["title", new Set(r.t)], ["heading", new Set(r.h)], ["opening", new Set(r.o)], ["text", new Set(r.x)]] }));
  for (const r of ROWS) { const e = E[r.key]; r.isFlow = !!(e && (e.kind === "flow" || (E[e.pageKey] || {}).kind === "flow")); }
  function rank(q) {
    const wanted = terms(q);
    if (!wanted.length) return { wanted, hits: [] };
    const need = Math.max(1, Math.ceil(wanted.length / 2)), how = /\bhow\b/.test(q.toLowerCase()), hits = [];
    for (const r of ROWS) {
      let score = 0; const matched = [];
      for (const t of wanted) {
        let best = 0;
        for (const [place, set] of r.sets) if (set.has(t)) best = Math.max(best, S.weight[place]);
        if (best) { score += best; matched.push(t); }
      }
      if (matched.length < need) continue;
      if (how && r.isFlow) score += 4;  // "how does X" is a flow's question
      hits.push({ r, score, matched });
    }
    hits.sort((a, b) => b.score - a.score || b.matched.length - a.matched.length || cmp(a.r.page, b.r.page) || cmp(a.r.heading, b.r.heading));
    const perPage = {}, kept = [];
    for (const x of hits) if ((perPage[x.r.page] || 0) < 2) { kept.push(x); perPage[x.r.page] = (perPage[x.r.page] || 0) + 1; }
    return { wanted, hits: kept };
  }
  function parity() {
    return S.check.map((c) => {
      const mine = rank(c.q).hits.slice(0, 8).map((x) => `${x.r.page}::${x.r.heading}`);
      return { q: c.q, same: JSON.stringify(mine) === JSON.stringify(c.hits), cli: c.hits, page: mine };
    });
  }

  // Results come in groups, flows first: on a call, the flow and the contract are what the lead wants.
  const GROUPS = [["exact", "Exact match"], ["link", "How they connect"], ["flow", "Flows"], ["node", "Apps and outside services"], ["contract", "Contracts"],
    ["need", "Capabilities and requirements"], ["flow-part", "Flows that match some of the words"], ["epic", "Epics"], ["question", "Open questions"],
    ["decision", "Decisions"], ["other", "Other pages and items"], ["closed", "Resolved questions"]];
  function groupOf(key) {
    const e = ent(key), k = e ? e.kind : "";
    if (k === "flow") return "flow";
    if (k === "app" || k === "party" || k === "external") return "node";
    if (k === "contract") return "contract";
    if (k === "capability" || k === "requirement") return "need";
    if (k === "epic") return "epic";
    if (k === "decision") return "decision";
    if (k === "unknown") return isOpen(UNKNOWN[key]) ? "question" : "closed";
    return "other";
  }
  /* Two apps or parties named in the query: the contracts between them, straight from the map's typed edges. */
  function connections(q) {
    const low = " " + q.toLowerCase().replace(/[^a-z0-9]+/g, " ") + " ";
    const named = [...D.map.apps.map((a) => [a.key, a.title]), ...D.map.parties.map((p) => [p.key, p.title]), ...D.map.externals.map((x) => [x.key, x.title])]
      .filter(([, t]) => low.includes(" " + t.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim() + " ")).map(([k]) => k);
    if (named.length < 2) return [];
    return D.map.contracts.filter((c) => named.includes(c.provider) && c.consumers.some((k) => named.includes(k) && k !== c.provider));
  }
  function exactMatches(q) {
    const t = q.trim(), up = t.toUpperCase(), out = [];
    if (!t) return out;
    if (E[up]) out.push(up); else if (E[t]) out.push(t);
    const page = Object.values(E).find((e) => e.path && e.id && e.id.toUpperCase() === up && !out.includes(e.key));
    if (page) out.push(page.key);
    if (t.startsWith("@") && D.owners[t]) out.push("owner:" + t);
    return out;
  }
  function marked(text, wanted) {
    const frag = document.createDocumentFragment();
    if (!text) return frag;
    if (!wanted.length) { frag.append(text); return frag; }
    const re = new RegExp("\\b(" + wanted.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")[a-z]*", "ig");
    let last = 0;
    text.replace(re, (m, _g, i) => { frag.append(text.slice(last, i), h("mark", {}, m)); last = i + m.length; return m; });
    frag.append(text.slice(last));
    return frag;
  }
  function goesTo(key) {
    const e = ent(key);
    if (!e) return "";
    if (e.kind === "flow") return "Enter plays it, ready to present";
    if (e.kind === "contract") { const f = flowsFor(key); return f.length ? `Enter shows it on the map, with ${plural(f.length, "flow")} to present from` : "Enter shows it on the map"; }
    if (e.kind === "unknown") return "Enter opens it in Who to ask";
    if (e.kind === "decision") return "Enter opens it in the decision log";
    return "";
  }

  let at = 0, results = [], moved = false;  // moved: the reader arrowed into the results, so Enter opens one rather than asks
  const input = $("#q"), box = $("#results");
  /* The results, with the Ask Claude row (or, on a file, the Copy as a prompt row) above them. */
  function show() {
    renderResults();
    const row = Ask.row(input.value);
    if (row) { box.prepend(row); box.hidden = false; }
    sync();
  }
  /* What a screen reader hears (E22): the box is a combobox whose popup is a listbox; the highlighted result is the
     active descendant, and the count or the "nothing" message goes to a polite status line. */
  function sync() {
    const open = !box.hidden;
    input.setAttribute("aria-expanded", String(open));
    for (const el of box.children) if (el.getAttribute("role") !== "option") el.setAttribute("role", "presentation");
    const active = open && results.length ? $("#res-" + clamp(at, 0, results.length - 1), box) : null;
    if (active) input.setAttribute("aria-activedescendant", active.id); else input.removeAttribute("aria-activedescendant");
    const note = $(".r-more", box);
    $("#results-status").textContent = !open ? "" : note ? note.textContent : results.length ? plural(results.length, "result") + ", use the arrow keys" : "";
  }
  function renderResults() {
    const q = input.value;
    box.innerHTML = ""; results = [];
    if (!q.trim()) { box.hidden = true; return; }
    const { wanted, hits } = rank(q), byGroup = {};
    const exact = exactMatches(q);
    if (exact.length) byGroup.exact = exact.map((key) => ({ key, snip: (E[key] && E[key].text) || "", flows: [] }));
    const links = connections(q);
    if (links.length) byGroup.link = links.map((c) => ({ key: c.id, link: true, flows: flowsFor(c.id).map((f) => f.flow) }));
    for (const x of hits) {
      if (!ent(x.r.key)) continue;
      let g = groupOf(x.r.key);
      // A flow leads when it holds every word or is planner's own top hit; a flow matching only some words waits lower.
      if (g === "flow" && x.matched.length < wanted.length && x.score < hits[0].score) g = "flow-part";
      (byGroup[g] = byGroup[g] || []).push({ key: x.r.key, snip: x.r.snip, heading: x.r.heading, flows: x.r.flows });
    }
    const noFlows = /\bhow\b/.test(q.toLowerCase()) && !D.flows.length;  // "how does X" is a flow's question; say so rather than return nothing
    if (noFlows) box.append(emptyState("No flows yet.", "A \"how does ...\" question is answered by a flow, and the plan has none yet.", "/planner:boundary", "small"));
    if (!hits.length && !links.length && !exact.length) {
      if (noFlows) { box.hidden = false; return; }
      box.append(h("div", { class: "r-more" }, wanted.length ? `No matches for ${wanted.join(", ")}. Search looks in titles, headings and page text; try a more specific word.`
        : "Type a word that carries meaning; words such as how, the and does are skipped."));
      box.hidden = false; return;
    }
    for (const [g, label] of GROUPS) {
      const list = byGroup[g];
      if (!list || !list.length) continue;
      const cap = g === "closed" || g === "other" ? 2 : g === "question" ? 3 : 4;
      box.append(h("div", { class: "r-group" }, label, h("span", { class: "ct" }, list.length > cap ? ` · ${cap} of ${list.length}` : ` · ${list.length}`)));
      for (const r of list.slice(0, cap)) {
        const i = results.length; results.push(r);
        const e = ent(r.key), id = idOf(r.key), c = r.link ? CONTRACT[r.key] : null, lvl = levelForKey(r.key);
        const crossing = [...new Set((r.flows || []).filter((f) => f !== r.key && E[f]))];
        box.append(h("div", { class: "result" + (i === at ? " on" : ""), role: "option", id: "res-" + i, "aria-selected": String(i === at), "data-key": r.key, onmousedown: (ev) => { ev.preventDefault(); pick(i); } },
          h("span", { class: "r-lamp lamp " + (lvl || "dark") }),
          h("div", {},
            h("div", { class: "r-head" }, h("span", { class: "kind" }, KIND_WORD[e.kind] || e.kind), h("span", { class: "r-title" }, e.title), id ? h("span", { class: "r-id" }, id) : null,
              FLOW[r.key] ? h("span", { class: "r-id" }, plural(FLOW[r.key].steps.length, "step")) : null),
            h("div", { class: "r-snip" }, c ? `${titleOf(c.provider)} → ${c.consumers.map(titleOf).join(", ")} · ${c.state || "no state"}` : marked(r.snip, wanted)),
            crossing.length ? h("div", { class: "r-flows" }, "▶ crossed by ", crossing.map((f) => E[f].title).join(", ")) : null,
            linkChips(r.key, { small: true }),
            i === at ? h("div", { class: "r-go" }, goesTo(r.key)) : null)));
      }
    }
    at = clamp(at, 0, results.length - 1);
    box.hidden = false;
  }
  function pick(i) {
    const r = results[i];
    if (!r) return;
    box.hidden = true; sync(); input.blur();
    go(r.key, { reset: true, reveal: true });
  }
  input.addEventListener("input", () => { at = 0; moved = false; show(); });
  input.addEventListener("focus", show);
  input.addEventListener("blur", () => setTimeout(() => { box.hidden = true; sync(); }, 140));
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") { at = Math.min(at + 1, results.length - 1); moved = true; show(); ev.preventDefault(); }
    else if (ev.key === "ArrowUp") { at = Math.max(at - 1, 0); moved = true; show(); ev.preventDefault(); }
    else if (ev.key === "Enter") {
      ev.preventDefault();
      // an exact ID or "@owner" is a jump, not a question
      if (!moved && Ask.enterAsks(input.value) && !exactMatches(input.value).length) { Ask.ask(input.value); input.value = ""; show(); input.blur(); }
      else pick(at);
    }
    else if (ev.key === "Escape") { input.value = ""; show(); input.blur(); }
  });
  document.addEventListener("keydown", (ev) => {
    // '/' is a character in the Ask composer, the board filter and every other field: only outside them is it the search key
    if (ev.key === "/" && !ev.ctrlKey && !ev.metaKey && !ev.altKey && !(ev.target.closest && ev.target.closest("input,textarea,select,[contenteditable]")) && $("#overlay").hidden) { ev.preventDefault(); input.focus(); input.select(); }
  });
  /* For the self-test: type, as a person would, and return the keys of the results in order. */
  function type(q) { input.value = q; at = 0; show(); return results.map((r) => r.key); }
  return { rank, parity, type, pick, terms, stem };
})();
