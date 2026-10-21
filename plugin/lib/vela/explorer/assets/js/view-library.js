/* The Library: everything outside the plan (provider API specs, designs, documents, wiki and tracker links), grouped by
   what it is, not by the app it serves. A row says what the item is, who kept it and when, what it relates to, and whether
   the file itself is in the vault or only a link. Picking a row opens it in the right-hand panel: where it is kept, its
   version, the original, what it relates to, and what cites it (counted from the pages, never typed).

   The Violation this exists to prevent is a Leaky Narrative on the page: every rule about the register (a Figma address
   is a design, `v1.0 (latest v1.1)` is a newer version, "cited" means a page names the ID) is decided in
   library_data.py and arrives as fields; this file only draws them. The other direction is the Library section in an
   app's, contract's or party's own panel (`backlinks`): an item that names a thing is listed on that thing.
   Routes: #s=library, #s=library&open=SRC-05. */
const Library = (() => {
  const rows = (D.library && D.library.rows) || [];
  const BY = Object.fromEntries(rows.map((r) => [r.key, r]));
  const BY_ID = Object.fromEntries(rows.map((r) => [r.id, r]));
  const GROUPS = [["API specs", ["spec"]], ["Designs", ["design"]], ["Documents", ["document"]], ["Wiki and tracker", ["wiki", "tracker"]], ["Other links", ["link"]]];
  const TYPE_WORD = { spec: "API spec", design: "Design", document: "Document", wiki: "Wiki page", tracker: "Tracker", link: "Link" };
  const GLYPH = { spec: "api", design: "design", document: "docs", wiki: "wiki", tracker: "tracker", link: "link" };
  const FILTERS = [["all", "All"], ["vault", "In the vault"], ["links", "Links"], ["cited", "Cited by the plan"]];
  const FILTER_SAY = { all: "Everything in the library", vault: "Items whose file is kept in the vault", links: "Items kept only as a link to a web address", cited: "Items a page of the plan cites" };
  const st = { filter: "all", q: "", open: "" };
  const CITER_WORD = { contract: "contract", unknown: "question", app: "app", capability: "capability", requirement: "requirement", epic: "epic", flow: "flow", decision: "decision",
    concern: "concern", party: "outside service", slice: "slice", risk: "risk" };

  const entry = (key) => (BY[key] ? { key, kind: "library", title: BY[key].title, id: BY[key].id } : null);  // core.js ent() asks for these
  const byId = (id) => BY_ID[id] || null;
  const inVault = (r) => !!r.stored;
  const cited = (r) => r.citedBy.length > 0;
  const FILTER_TEST = { all: () => true, vault: inVault, links: (r) => !inVault(r) && r.web, cited };
  const count = (filter) => rows.filter(FILTER_TEST[filter]).length;
  const person = (text) => peopleWords(text);
  const dateWords = (iso) => (isDate(iso) ? dayYear(iso) : "");
  const TAGS = { newer: ["stale", "newer version out"], vault: ["in", "in the vault"], link: ["out", "link"], listed: ["out", "listed only"] };
  const tagOf = (r) => (r.where === "both" ? ["in", `link + ${r.ext}`] : TAGS[r.where]);
  const haystack = (r) => [r.title, r.format, TYPE_WORD[r.type], r.version, person(r.owner), ...r.relates.map((k) => titleOf(k))].join(" ").toLowerCase();

  /* ------------------------------------------------------------ what is shown */
  function matching(ignoreFilter) {
    const q = st.q.trim().toLowerCase(), words = q.split(/\s+/).filter(Boolean);
    return rows.filter((r) => (ignoreFilter || FILTER_TEST[st.filter](r)) && words.every((w) => haystack(r).includes(w)));
  }
  const visible = () => matching(false);
  const groups = (list) => GROUPS.map(([label, types]) => [label, list.filter((r) => types.includes(r.type))]).filter(([, items]) => items.length);

  function metaLine(r) {
    const saved = r.date ? `${inVault(r) ? "saved " : ""}${dateWords(r.date)}` : "";
    return [r.format, r.version, r.owner ? person(r.owner) : "", saved].filter(Boolean).join(" · ");
  }
  function row(r) {
    const [tone, word] = tagOf(r), open = () => select(r.key);
    const related = r.relates.map((k) => (ent(k) ? h("span", {}, titleOf(k)) : null)).filter(Boolean);
    return h("button", { class: "lb-row" + (st.open === r.key ? " on" : ""), type: "button", "data-library": r.id, "data-type": r.type, "aria-pressed": String(st.open === r.key), onclick: open },
      h("span", { class: `lb-ic lb-${r.type}`, "aria-hidden": "true" }, Icons.el(GLYPH[r.type])),
      h("span", { class: "lb-main" }, h("span", { class: "lb-t" }, r.title), h("span", { class: "lb-m" }, metaLine(r)),
        related.length ? h("span", { class: "lb-rel" }, related) : null),
      h("span", { class: `lb-where lb-${tone}` }, word));
  }

  function bar() {
    const search = h("input", { type: "search", class: "lb-find", placeholder: "Search the library", "aria-label": "Search the library", value: st.q, autocomplete: "off", spellcheck: "false" });
    search.addEventListener("input", () => { st.q = search.value; refresh({ keepBar: true }); });
    const chips = FILTERS.map(([id, label]) => h("button", { class: "chip" + (st.filter === id ? " on" : ""), type: "button", "aria-pressed": String(st.filter === id), "data-filter": id, title: FILTER_SAY[id],
      onclick: () => { st.filter = id; refresh(); } }, label, id === "all" ? null : h("span", { class: "lb-n" }, String(count(id)))));
    return h("div", { class: "lb-bar" }, search, h("div", { class: "lb-filters", role: "group", "aria-label": "Show" }, chips));
  }
  function summaryLine(list) {
    const vault = count("vault"), links = count("links"), listed = rows.length - vault - links;
    const whole = `${plural(rows.length, "item")} · ${vault} in the vault, ${plural(links, "link")}${listed ? `, ${listed} listed only` : ""}`;
    return list.length === rows.length ? whole : `Showing ${list.length} of ${plural(rows.length, "item")}`;
  }
  function list(items) {
    if (!items.length) {
      return h("div", { class: "lb-none" }, h("b", {}, "Nothing matches."), " Clear the search or the filter to see everything. ",
        h("button", { class: "linkish", type: "button", onclick: () => { st.q = ""; st.filter = "all"; refresh(); } }, "Clear filters"));
    }
    return h("div", { class: "lb-groups" }, groups(items).map(([label, group]) => h("section", { class: "lb-group", "data-group": label },
      h("h3", {}, label, h("span", { class: "lb-gn" }, ` · ${group.length}`)), h("div", { class: "lb-list" }, group.map(row)))));
  }
  function render(main) {
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, Nav.title("Library")),
      h("p", {}, "Everything outside the plan, grouped by what it is. Pick one to see where it is kept, what it relates to and what cites it.", Nav.ledeLink())),
      h("div", { class: "spacer" }), Nav.pageActions()));
    if (!rows.length) { main.append(emptyState("Nothing is in the library yet.", "When the plan's lead adds a link or a file, it shows up here.")); return; }
    main.append(h("div", { class: "lb-wrap" }, h("div", { class: "lb-barhost" }, bar()), h("p", { class: "lb-count", id: "lb-count", "aria-live": "polite" }), h("div", { class: "lb-stage" })));
    paint();
  }
  function paint() {
    const stage = $(".lb-stage"), items = visible();
    if (!stage) return;
    stage.innerHTML = "";
    stage.append(list(items));
    $("#lb-count").textContent = summaryLine(items);
  }
  /* While the search box has the focus the bar stays as it is, and only the counts are brought up to date. */
  function refresh(opts = {}) {
    const host = $(".lb-barhost");
    if (host && !opts.keepBar) host.replaceChildren(bar());
    paint();
  }
  function select(key) {
    st.open = key;
    if (key) DetailsPanel.show(key, { reset: true, quiet: true }); else DetailsPanel.clear();
    paint();
    const on = $(".lb-row.on");
    if (on) on.scrollIntoView({ block: "nearest" });
  }
  document.addEventListener("keydown", (ev) => {
    if (App.view !== "library" || (ev.target.closest && ev.target.closest("input, select, textarea"))) return;
    const at = ev.target.closest && ev.target.closest(".lb-row");
    if (!at || (ev.key !== "ArrowDown" && ev.key !== "ArrowUp")) return;
    const all = $$(".lb-row"), next = all[all.indexOf(at) + (ev.key === "ArrowDown" ? 1 : -1)];
    if (next) { ev.preventDefault(); next.focus(); }
  });
  /* A deep link, a search result or a click on a library chip anywhere opens its row here. */
  function showFor(key) {
    const r = BY[key] || BY_ID[key];
    if (!r) return -1;
    st.open = r.key; App.trail = [r.key]; App.focus = r.key;  // the panel follows the trail
    if (App.view === "library") refresh();
    return rows.indexOf(r);
  }

  /* ------------------------------------------------------------ one item, in the right-hand panel */
  /* A chip that names a thing: a link a person can also reach with the keyboard (the shared chip is a bare anchor). */
  function chip(key) {
    const a = refChip(key);
    a.tabIndex = 0; a.setAttribute("role", "link");
    a.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); a.click(); } });
    return a;
  }
  const kv = (pairs) => h("dl", { class: "lb-kv" }, pairs.filter(([, v]) => v).flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)]));
  const href = (url) => (/^https?:\/\//i.test(url) ? url : null);
  function citedSummary(r) {
    const tally = {};
    for (const k of r.citedBy) { const word = CITER_WORD[(ent(k) || {}).kind] || "page"; tally[word] = (tally[word] || 0) + 1; }
    return Object.entries(tally).map(([w, n]) => plural(n, w)).join(", ");
  }
  function actions(r) {
    const out = [], file = r.stored ? openLink(["Open the file"], D.vault ? D.vault + "/" + r.stored : "", r.stored, `${r.stored}, in a new tab`, "btn") : null;
    if (file) out.push(file);
    const original = href(r.location);
    if (original) out.push(h("a", { class: "btn", href: original, target: "_blank", rel: "noopener noreferrer", title: "The original, in a new tab" }, "Open the original"));
    out.push(h("button", { class: "btn", type: "button", "data-act": "cites", disabled: cited(r) ? null : true, title: cited(r) ? "Jump to the pages and items that cite it" : "Nothing in the plan cites it yet",
      onclick: () => showCiting() }, "Show what cites it"));
    return h("div", { class: "p-actions lb-actions" }, out);
  }
  function showCiting() {
    const box = $("#panel-body .lb-cites");
    if (!box) return;
    box.scrollIntoView({ block: "nearest" });
    box.classList.add("flash");
    const first = $("a, button", box);
    if (first) first.focus();
    setTimeout(() => box.classList.remove("flash"), 1600);
  }
  function nodes(key) {
    const r = BY[key], [tone, word] = tagOf(r);
    const related = r.relates.filter((k) => ent(k)).map(chip);
    const newer = r.newer ? h("div", { class: "lb-warn", role: "note" }, `A newer version is out: ${r.newer}. The plan was written against ${r.version || "an earlier one"}.`) : null;
    const when = [r.version, r.date ? `${inVault(r) ? "saved " : ""}${dateWords(r.date)}` : ""].filter(Boolean).join(", ");
    return [PlanDetails.head(`${TYPE_WORD[r.type]} · ${r.format}`, r.title, h("span", { class: `lb-where lb-${tone}` }, word)),
      h("div", { class: "p-body" }, newer,
        kv([["Stored", r.stored ? h("code", {}, r.stored) : "Not kept in the vault: a link only"],
          ["Version", r.type === "spec" ? when || "Not recorded" : ""],
          ["Saved", r.type !== "spec" && r.date ? dateWords(r.date) : ""],
          ["From", r.location || "Not recorded"],
          ["Added by", r.owner ? person(r.owner) : "Not recorded"],
          ["Relates to", related.length ? h("span", { class: "lb-chips" }, related) : "Nothing in particular"],
          ["Cited by", cited(r) ? citedSummary(r) : "Nothing in the plan cites it yet"]]),
        actions(r),
        cited(r) ? h("section", { class: "p-sec lb-cites" }, h("h3", {}, "What cites it", h("span", { class: "ct" }, ` ${r.citedBy.length}`)),
          h("div", { class: "lb-chips" }, r.citedBy.filter((k) => ent(k)).map(chip))) : null,
        App.view === "library" ? null : h("div", { class: "p-actions" }, h("button", { class: "btn", type: "button", onclick: () => go(key, { reset: true, reveal: true }) }, "Show in the Library")))];
  }

  /* The Library section in the panel of anything an item relates to: an app, a contract, a party, a capability. */
  function backlinks(key) {
    const named = rows.filter((r) => r.relates.includes(key));
    if (!named.length) return null;
    return Panel.section("Library", named.length, h("ul", { class: "mini-list lb-back" }, named.map((r) => h("li", {}, chip(r.key), " ", h("span", { class: "muted" }, r.format)))));
  }

  /* ------------------------------------------------------------ the Details panel (detailspanel.js) */
  const closeItem = () => { if (st.open) { st.open = ""; if (App.view === "library") paint(); } };
  function summaryNodes() {
    const newer = rows.filter((r) => r.newer);
    return [PlanDetails.head("Library", plural(rows.length, "item")),
      h("div", { class: "p-body" },
        Panel.section("Newer version out", newer.length || null, newer.length ? PlanDetails.bullets(newer.map((r) => [PlanDetails.link(r.key, r.title), h("span", { class: "muted" }, ` ${r.version} in the plan, ${r.newer} out`)]))
          : PlanDetails.quiet("No item has a newer version recorded.")),
        Panel.section("Cited by the plan", count("cited") || null, count("cited") ? PlanDetails.bullets(rows.filter(cited).slice(0, 6).map((r) => PlanDetails.link(r.key, r.title))) : PlanDetails.quiet("No page of the plan cites an item yet.")),
        h("div", { class: "p-note" }, "Pick an item to see where it is kept, what it relates to and what cites it."))];
  }
  DetailsPanel.register("library", {
    view: "library", live: () => rows.length > 0, rootLabel: "Library", summary: summaryNodes,
    owns: (k) => !!BY[k] || PlanDetails.owns(k), detail: (k) => (BY[k] ? nodes(k) : PlanDetails.detail(k, "library")),
    label: (k) => (BY[k] ? BY[k].title : PlanDetails.label(k)), open: (k) => (BY[k] ? null : PlanDetails.openFor(k, "library")),
    waiting: (k) => PlanDetails.waitingTab(k, "queue"), waitingCount: () => PlanDetails.waitingCount("queue"),
    focus: (k) => { if (!k) closeItem(); else if (BY[k] && st.open !== k) { st.open = k; if (App.view === "library") paint(); } },
  });
  /* The search box's own: items whose title, format or related names hold every word typed. */
  function find(q) {
    const words = String(q || "").toLowerCase().match(/[a-z0-9]+/g) || [];
    return words.length ? rows.filter((r) => words.every((w) => haystack(r).includes(w))) : [];
  }
  return { rows, entry, render, byId, nodes, backlinks, find, showFor, select, st, visible, groups, matching, count, tagOf, metaLine, citedSummary,
    highlight: (k) => { if (App.view === "library" && BY[k]) { st.open = k; paint(); } } };
})();
View("library", { label: "Library", title: "The library: every spec, design, document and link the plan rests on, grouped by what it is", render: Library.render,
  highlight: (k) => Library.highlight(k), count: () => String(Library.rows.length) });
