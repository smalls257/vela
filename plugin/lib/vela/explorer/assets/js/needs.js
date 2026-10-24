/* Needs you: what the person viewing has to act on, at the top of every role overview, most urgent first.

   The Violation this prevents is a Leaky Narrative: what is late, what counts as just handed over and which grills are
   ready are decided in vela/needsyou.py and arrive as D.needs.lines, already in order and each with the handles it is
   for. This file asks Viewer who is looking, keeps the lines that are for them (never re-sorting) and draws them. The
   same count feeds the "N for you" badge, so the block and the badge cannot disagree.

   Four kinds of line, each opening its item in the right-hand panel: a question they were asked (with the ask-by date),
   a grill they own that is ready, a proposal waiting on their yes, an app just handed to them. At most five show; the rest
   sit behind "N more". With nothing, one line says so and names the next date on their side; the badge goes away.
   With nobody viewing, the block says how to pick, and never says "you". */
const Needs = (() => {
  const SHOWN = 5;
  const st = { all: false };
  const lines = () => D.needs.lines.filter(Viewer.isFor);
  const count = () => lines().length;
  const nextDate = () => D.needs.dates.filter(Viewer.isFor)[0] || null;
  const you = () => Viewer.hasPerson();
  const grillOf = (id) => Grills.rows.find((r) => r.id === id);
  const roleWord = (id) => ((Roles.ROLES.find(([r]) => r === id) || [id, id])[1]).toLowerCase();
  const titleFor = (key) => (ent(key) ? ent(key).title : key);

  /* One line's words, by kind: [mark, title, sub, when text, when tone]. */
  const SAY = {
    question(l) {
      const q = ASK[l.key], held = Queue.items().find((x) => x.id === l.key);
      const due = l.standing === "none" ? "no date" : `due ${day(l.date)}`;
      return ["?", q ? q.question : titleFor(l.key), `${you() ? "You were asked" : `Asked of ${l.words || "your role"}`}${held ? ` · it holds up ${held.says}` : ""}`, due,
        l.standing === "late" ? "late" : l.standing === "soon" ? "soon" : "ok"];
    },
    grill(l) {
      const g = grillOf(l.grill);
      return ["✓", `Grill: ${g ? g.name : titleFor(l.key)}`, `${you() ? "Yours to run" : "Waiting to be run"} · ${l.standing === "said-yes" ? "the lead already said yes, settle it or grill it" : "ready, nothing in the way"}`, "ready", "ok"];
    },
    proposal(l) {
      const by = l.by ? personName(l.by) : "A reader";
      return ["↗", `Review a proposal: "${titleFor(l.key)}"`, `From ${by} · waiting on ${you() ? "your" : "the owner's"} yes or no`, l.date ? `sent ${day(l.date)}` : "waiting", l.date ? "soon" : "ok"];
    },
    handed(l) {
      return ["+", `${titleFor(l.key)} was handed to ${you() ? "you" : "this role"}`, "Open it to see what the app team was given", `handed ${day(l.date)}`, "ok"];
    },
  };
  const KIND_CLASS = { question: "q", grill: "g", proposal: "r", handed: "n" };

  function lineEl(l) {
    const [mark, title, sub, when, tone] = SAY[l.kind](l);
    return h("button", { class: "ny-line", type: "button", "data-ref": l.key, "data-kind": l.kind, "data-for-you": "" },
      h("span", { class: `ny-ico ${KIND_CLASS[l.kind]}`, "aria-hidden": "true" }, mark),
      h("span", { class: "ny-main" }, h("span", { class: "ny-t" }, title), h("span", { class: "ny-m" }, sub)),
      h("span", { class: `ny-when ${tone}` }, when));
  }
  function joinLink() {
    const n = typeof Grills !== "undefined" && Grills.exists() && Grills.hasViewer() ? Grills.countOf("join") : 0;
    if (!n) return null;
    return h("button", { class: "linkish ny-join", type: "button", onclick: () => { Grills.st.scope = "join"; Grills.open(); } }, `${plural(n, "more grill")} where you're asked to join → Waiting for a decision`);
  }
  function body(list) {
    const shown = st.all ? list : list.slice(0, SHOWN), rest = list.length - SHOWN;
    const out = shown.map(lineEl);
    if (rest > 0) {
      out.push(h("button", { class: "linkish ny-more", type: "button", "aria-expanded": String(st.all), onclick: () => { st.all = !st.all; const fresh = block(); box().replaceWith(fresh); $(".ny-more", fresh).focus({ preventScroll: true }); } },
        st.all ? `Show the first ${SHOWN}` : `${rest} more`));
    }
    return out;
  }
  const box = () => $("#needs-you");

  /* The block itself. It always renders, so the reader finds the place the badge jumps to: lines, or one line saying why not. */
  function block() {
    const list = lines(), el = h("section", { class: "needs-you" + (list.length ? "" : " empty"), id: "needs-you", tabindex: "-1", "aria-label": "Needs you", "data-n": String(list.length) });
    if (!Viewer.known()) {  // a list it cannot tell is theirs would read "Nothing needs you" for someone it simply doesn't know
      el.append(h("div", { class: "ny-quiet" }, Viewer.viewer().role
        ? `Nothing in the plan says who the ${roleWord(Viewer.viewer().role)} is, so there is no list to show here.`
        : "Pick who is viewing, under Viewing as in the sidebar, and this lists what needs them."));
      return el;
    }
    if (!list.length) {
      const next = nextDate();
      el.append(h("div", { class: "ny-quiet" }, next ? `Nothing needs you right now. The next date on your side is ${next.askedName ? `${next.askedName}'s` : "an"} answer, due ${day(next.date)}.` : "Nothing needs you right now.",
        joinLink()));
      return el;
    }
    el.append(h("div", { class: "ny-hd" }, h("b", {}, "Needs you"), h("span", {}, `${plural(list.length, "thing")}, most urgent first`)), ...body(list), ...[joinLink()].filter(Boolean));
    return el;
  }
  /* The right-hand panel's default summary where no section page is beside the visual: the same lines, in the panel's width, with
     no id (the overview's block owns it). On a role overview the block is already the main page, so the panel says nothing twice. */
  function lede(opts = {}) {
    const n = count(), hint = opts.queue === false ? " Pick a box on the map to read it here." : "";
    if (App.view === "role") return "Pick something on the page to read it here.";
    if (!Viewer.known()) return "Pick who is viewing, under Viewing as in the sidebar, and this lists what needs them." + hint;
    return (n ? `${plural(n, "thing")}, most urgent first.` : "Nothing needs you right now.") + hint;
  }
  function panel() {
    const list = lines();
    if (App.view === "role" || !Viewer.known() || !list.length) return null;
    const el = h("section", { class: "needs-you needs-panel", "data-n": String(list.length) }, ...list.slice(0, SHOWN).map(lineEl));
    if (list.length > SHOWN) el.append(h("button", { class: "linkish ny-more", type: "button", onclick: () => Nav.overview() }, `${list.length - SHOWN} more on the overview`));
    return el;
  }
  /* The badge's jump: to the viewer's role overview if they are not on one, then to the block. */
  function jump() {
    if (App.view !== "role") Nav.overview();
    const el = box();
    if (el) { el.scrollIntoView({ block: "start" }); el.focus({ preventScroll: true }); }
  }
  return { block, lede, panel, count, lines, nextDate, jump, SHOWN, st };
})();
