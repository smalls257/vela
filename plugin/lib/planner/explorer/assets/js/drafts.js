/* A reader's draft, and the decisions waiting for an owner. The top bar carries two quiet chips, "Draft: N pages
   changed" (readers only) and the pending-approval count; either opens this view (#drafts). The diff is computed at
   build time from the pristine baseline (planner's drafts.py), and every line of it is drawn with textContent,
   never as HTML: a page can hold any text. Additions and removals carry a symbol as well as a colour. */
const Drafts = (() => {
  const st = { from: null };
  const SYMBOL = { add: "+", del: "-", ctx: " ", hunk: "" };
  const reader = () => D.role === "reader";
  const count = () => (D.draft && D.draft.count) || 0;
  const conflicts = () => (D.draft && D.draft.conflicts) || [];

  /* One page's diff as rows. Text goes in with textContent, so markup in a vault page stays visible text. */
  function diffBlock(rows) {
    const box = h("div", { class: "diff", role: "table", "aria-label": "Changed lines" });
    for (const [kind, text] of rows) {
      const row = h("div", { class: "dl " + kind, role: "row" });
      const sym = h("span", { class: "sym", "aria-hidden": "true" }); sym.textContent = SYMBOL[kind] || "";
      const tx = h("span", { class: "tx" }); tx.textContent = text;
      row.append(sym, tx);
      box.append(row);
    }
    return box;
  }
  const STATUS = { changed: "changed", added: "new page", removed: "removed", conflict: "Conflict" };
  function pageCard(p, open) {
    const counts = p.binary ? "binary, not shown" : `+${p.added} -${p.removed}`;
    const head = h("summary", {}, h("span", { class: "dstate " + p.status }, STATUS[p.status] || p.status), p.merged ? h("span", { class: "dstate merged", title: "Your lines and the owner's were joined when you re-opened; read it once" }, "merged") : null,
      h("b", {}, p.title || p.path), h("span", { class: "dpath" }, p.path), h("span", { class: "dn" }, counts),
      p.key && E[p.key] ? refChip(p.key) : null);
    const body = p.binary ? h("p", { class: "p-note" }, `${p.status === "removed" ? "A binary file was removed." : "A binary file changed."} A proposal lists it and does not include it.`)
      : h("div", {}, diffBlock(p.lines), p.truncated ? h("p", { class: "p-note" }, "Longer than this view shows; the rest of the change is in the file.") : null);
    const card = h("details", { class: "dpage", "data-path": p.path }, head, body);
    if (open) card.open = true;
    return card;
  }
  /* A page the replay could not settle: it holds the owner's version and the reader's sits beside it. Shown before every other draft. */
  function conflictCard(c) {
    const where = (c.ranges || []).map(([a, b]) => (a === b ? "line " + a : b > a ? `lines ${a}-${b}` : "near line " + Math.max(a - 1, 0))).join(", ");
    const head = h("summary", {}, h("span", { class: "dstate conflict" }, STATUS.conflict), h("b", {}, c.title || c.path), h("span", { class: "dpath" }, c.path),
      c.binary || !c.lines.length ? null : h("span", { class: "dn" }, `+${c.added} -${c.removed}`), c.key && E[c.key] ? refChip(c.key) : null);
    const note = h("p", { class: "p-note" }, c.why + (where ? ` (${where} of the copy you opened).` : ""), " The page now holds the owner's version. Yours is saved as ", h("code", {}, c.mine),
      ". Copy over what you want to keep, then delete that file to close the conflict.", c.lines.length ? " Below, + is in your version and - is on the owner's page." : "");
    const card = h("details", { class: "dpage conflict", "data-path": c.path }, head, note, c.lines.length ? h("div", {}, diffBlock(c.lines)) : null);
    card.open = true;
    return card;
  }
  function conflictList() {
    if (!conflicts().length) return null;
    return h("section", { class: "d-sec", id: "conflicts" }, h("h2", {}, "Conflicts", h("span", { class: "sub" }, String(conflicts().length))),
      h("p", { class: "p-note" }, "These pages changed on both sides since you opened the earlier copy. Nothing of yours was overwritten, and you cannot propose until each is settled."),
      conflicts().map(conflictCard));
  }
  function pendingList() {
    if (!D.pending.length) return null;
    return h("section", { class: "d-sec" }, h("h2", {}, "Pending approval", h("span", { class: "sub" }, String(D.pending.length))),
      h("p", { class: "p-note" }, reader() ? "Decisions you recorded. They look settled and are not until the owner reviews them." : "Decisions a reader recorded. Each stays marked until you accept, reject or edit it."),
      h("ul", { class: "mini-list d-pending" }, D.pending.map((p) => h("li", {}, E[p.key] ? refChip(p.key) : p.subject, " ", h("span", { class: "muted" }, `${p.by}, ${p.date}`)))));
  }
  /* How a draft reaches the owner. The page only names the command: it has no network and sends nothing. */
  function proposeHint() {
    if (!reader()) return null;
    return h("p", { class: "p-note propose-hint", id: "propose-hint" }, "To send these to the owner, run ", h("code", {}, "/planner:propose"),
      " in Claude Code from this folder. It asks you why for each change and writes a proposal folder you send yourself. Nothing is sent from this page.");
  }
  function changes() {
    const d = D.draft;
    if (!d) return null;
    if (d.problem) return h("section", { class: "d-sec" }, emptyState("I could not compare your pages with the copy you opened.", d.problem));
    if (!d.count) return conflicts().length ? null : h("section", { class: "d-sec" }, emptyState("No changes yet.", "You have not edited a page since you opened this copy."));
    return h("section", { class: "d-sec" }, h("h2", {}, "Changed pages", h("span", { class: "sub" }, String(d.count))),
      h("p", { class: "p-note" }, "Against the copy you opened. + is an added line, - a removed one; a generated table is collapsed to one line."),
      proposeHint(),
      d.pages.map((p, i) => pageCard(p, d.pages.length <= 3 || i === 0)));
  }
  function heading() {
    if (reader()) {
      if (D.draft && D.draft.problem) return "Draft: cannot compare";
      const open = conflicts().length, pages = count() ? `${plural(count(), "page")} changed` : "";
      return "Draft: " + [pages, open ? plural(open, "conflict") : ""].filter(Boolean).join(", ");
    }
    return `${D.pending.length} from readers awaiting your review`;
  }
  function render(main) {
    const crumbs = h("nav", { class: "ask-crumbs", "aria-label": "Where you came from" },
      h("button", { class: "ask-back", type: "button", title: "Back to where you were", onclick: back }, "‹ " + Nav.whereLabel(st.from)), h("span", { class: "sep" }, "›"), h("span", {}, reader() ? "Your draft" : "Awaiting review"));
    main.append(h("div", { class: "view-head" }, h("div", {}, crumbs, h("h1", {}, heading()))),
      h("div", { class: "scroll d-view" }, conflictList(), changes(), pendingList()));
  }
  function open() { if (App.view !== "drafts") st.from = Nav.where(); App.section = "drafts"; App.root = "lights"; showView("drafts"); Panel.render(); }
  function boot() { st.from = null; open(); return true; }
  function back() { const where = st.from; st.from = null; Nav.back(where); }

  /* The top bar: the draft chip (readers, once something changed) and the pending count (anyone, once something waits). */
  function badges() {
    const box = $("#flags");
    box.innerHTML = "";
    if (reader() && D.draft && (count() || conflicts().length || D.draft.problem)) {
      box.append(h("button", { class: "chip draft-badge" + (conflicts().length ? " has-conflict" : ""), id: "draft-badge", title: D.draft.problem || "Pages you changed since you opened this copy; click for the lines", onclick: open }, heading()));
    }
    if (D.pending.length) {
      const word = reader() ? `${D.pending.length} pending approval` : `${D.pending.length} from readers awaiting your review`;
      box.append(h("button", { class: "chip pending-chip", id: "pending-chip", title: LIGHT.pending.say, onclick: open }, lampEl("pending"), word));
    }
    box.hidden = !box.childNodes.length;
  }
  View("drafts", { label: "Drafts", title: "What you changed since you opened this copy", render });
  return { render, open, boot, badges, diffBlock, conflictCard, heading, st };
})();
