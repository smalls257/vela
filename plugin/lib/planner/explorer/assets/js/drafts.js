/* A reader's draft, and the decisions waiting for an owner. The top bar carries two quiet chips, "Draft: N pages
   changed" (readers only) and the pending-approval count; either opens this view (#drafts). The diff is computed at
   build time from the pristine baseline (planner's drafts.py), and every line of it is drawn with textContent,
   never as HTML: a page can hold any text. Additions and removals carry a symbol as well as a colour. */
const Drafts = (() => {
  const st = { from: null };
  const SYMBOL = { add: "+", del: "-", ctx: " ", hunk: "" };
  const reader = () => D.role === "reader";
  const count = () => (D.draft && D.draft.count) || 0;

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
  const STATUS = { changed: "changed", added: "new page", removed: "removed" };
  function pageCard(p, open) {
    const counts = p.binary ? "binary, not shown" : `+${p.added} -${p.removed}`;
    const head = h("summary", {}, h("span", { class: "dstate " + p.status }, STATUS[p.status] || p.status), h("b", {}, p.title || p.path), h("span", { class: "dpath" }, p.path), h("span", { class: "dn" }, counts),
      p.key && E[p.key] ? refChip(p.key) : null);
    const body = p.binary ? h("p", { class: "p-note" }, `${p.status === "removed" ? "A binary file was removed." : "A binary file changed."} A proposal lists it and does not include it.`)
      : h("div", {}, diffBlock(p.lines), p.truncated ? h("p", { class: "p-note" }, "Longer than this view shows; the rest of the change is in the file.") : null);
    const card = h("details", { class: "dpage", "data-path": p.path }, head, body);
    if (open) card.open = true;
    return card;
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
    if (!d.count) return h("section", { class: "d-sec" }, emptyState("No changes yet.", "You have not edited a page since you opened this copy."));
    return h("section", { class: "d-sec" }, h("h2", {}, "Changed pages", h("span", { class: "sub" }, String(d.count))),
      h("p", { class: "p-note" }, "Against the copy you opened. + is an added line, - a removed one; a generated table is collapsed to one line."),
      proposeHint(),
      d.pages.map((p, i) => pageCard(p, d.pages.length <= 3 || i === 0)));
  }
  function heading() {
    if (reader()) return D.draft && D.draft.problem ? "Draft: cannot compare" : `Draft: ${plural(count(), "page")} changed`;
    return `${D.pending.length} from readers awaiting your review`;
  }
  function render(main) {
    const crumbs = h("nav", { class: "ask-crumbs", "aria-label": "Where you came from" },
      h("button", { class: "ask-back", type: "button", title: "Back to where you were", onclick: back }, "‹ " + Nav.whereLabel(st.from)), h("span", { class: "sep" }, "›"), h("span", {}, reader() ? "Your draft" : "Awaiting review"));
    main.append(h("div", { class: "view-head" }, h("div", {}, crumbs, h("h1", {}, heading()))),
      h("div", { class: "scroll d-view" }, changes(), pendingList()));
  }
  function open() { if (App.view !== "drafts") st.from = Nav.where(); App.section = "drafts"; App.root = "lights"; showView("drafts"); Panel.render(); }
  function boot() { st.from = null; open(); return true; }
  function back() { const where = st.from; st.from = null; Nav.back(where); }

  /* The top bar: the draft chip (readers, once something changed) and the pending count (anyone, once something waits). */
  function badges() {
    const box = $("#flags");
    box.innerHTML = "";
    if (reader() && D.draft && (count() || D.draft.problem)) {
      box.append(h("button", { class: "chip draft-badge", id: "draft-badge", title: D.draft.problem || "Pages you changed since you opened this copy; click for the lines", onclick: open }, heading()));
    }
    if (D.pending.length) {
      const word = reader() ? `${D.pending.length} pending approval` : `${D.pending.length} from readers awaiting your review`;
      box.append(h("button", { class: "chip pending-chip", id: "pending-chip", title: LIGHT.pending.say, onclick: open }, lampEl("pending"), word));
    }
    box.hidden = !box.childNodes.length;
  }
  View("drafts", { label: "Drafts", title: "What you changed since you opened this copy", render });
  return { render, open, boot, badges, diffBlock, heading, st };
})();
