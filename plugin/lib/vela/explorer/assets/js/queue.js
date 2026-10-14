/* The work queue: the open questions that hold something up, as a short ranked list a person can keep in mind.
   Why it is this way: the strip it replaces drew one yellow chip per (question, thing held) pair, ID first, so 17
   questions read as 34 chips and none said what it held up. That is a Leaky Narrative (the pairing is the data's
   shape, not the lead's) and, past about seven, a wall nobody can scan. A row here is one question in plain words:
   what is waiting, what it holds up, who to ask and by when. The lamp is the question's own light and the order is
   attention.ranked's rule (level, then urgency, then ID); nothing here ranks or colors on its own. The top five show;
   "Show all" groups the rest by the thing each holds, so the reader can find "what holds the strategy" in one look.
   The ID rides in the tooltip, and the question's own words, with who and when, open in the panel. */
const Queue = (() => {
  const TOP = 5;
  const st = { all: false };
  const GROUPS = [["strategy", "Strategy"], ["scope", "Scope"], ["epics", "Epics"], ["parts", "Apps and contracts"], ["concerns", "Concerns"], ["releases", "Releases"], ["questions", "Other questions"]];
  const PARTS = new Set(["app", "contract", "flow", "runtime", "external", "party", "page"]);
  const NUMBER = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
  const said = (n) => NUMBER[n] || String(n);
  const epicTotal = Object.values(E).filter((e) => e.kind === "epic").length;

  /* What a held thing is, for grouping: the question's most important hold names its group. */
  function groupOf(key) {
    const e = ent(key);
    if (!e) return "scope";  // a goal (G1) has no page of its own
    if (e.kind === "epic") return "epics";
    if (e.kind === "concern") return "concerns";
    if (e.kind === "unknown") return "questions";
    if (PARTS.has(e.kind)) return "parts";
    const section = D.sections.find((x) => x.page === key);
    if (section && section.id === "strategy") return "strategy";
    if (section && section.id === "releases") return "releases";
    return "scope";
  }
  const kindOfKey = (key) => (ent(key) || { kind: "goal" }).kind;

  /* "the strategy, all four epics and the release plan": plain words, at most three, then how many more. */
  function say(keys) {
    const by = Object.fromEntries(GROUPS.map(([id]) => [id, keys.filter((k) => groupOf(k) === id)]));
    const named = (list, one, many) => (list.length === 1 ? `the ${titleOf(list[0])} ${one}` : list.length ? `${said(list.length)} ${many}` : null);
    const caps = by.scope.filter((k) => kindOfKey(k) === "capability");
    const reqs = by.scope.filter((k) => kindOfKey(k) === "requirement" && !caps.includes((D.trace.requirements.find((r) => r.id === (E[k] || {}).id) || {}).capability));
    const pages = by.scope.filter((k) => kindOfKey(k) === "section" || kindOfKey(k) === "page");
    const goals = by.scope.filter((k) => kindOfKey(k) === "goal");
    const apps = by.parts.filter((k) => kindOfKey(k) === "app"), contracts = by.parts.filter((k) => kindOfKey(k) === "contract");
    const otherParts = by.parts.filter((k) => !["app", "contract"].includes(kindOfKey(k)));
    const parts = [apps.length === 1 ? `the ${titleOf(apps[0])} app` : apps.length ? `${said(apps.length)} apps` : null,
      contracts.length === 1 ? `the ${titleOf(contracts[0])} contract` : contracts.length ? `${said(contracts.length)} contracts` : null,
      otherParts.length ? `${said(otherParts.length)} other ${otherParts.length === 1 ? "part" : "parts"} of the system` : null];
    const phrases = [
      by.strategy.length ? "the strategy" : null,
      ...pages.map((k) => `the ${titleOf(k).toLowerCase()}`),
      named(caps, "capability", "capabilities"),
      named(reqs, "requirement", "requirements"),
      goals.length ? `${said(goals.length)} ${goals.length === 1 ? "goal" : "goals"}` : null,
      by.epics.length === 1 ? `the ${titleOf(by.epics[0])} epic` : by.epics.length && by.epics.length === epicTotal ? `all ${said(epicTotal)} epics` : by.epics.length ? `${said(by.epics.length)} epics` : null,
      ...parts,
      by.concerns.length === 1 ? `the ${titleOf(by.concerns[0])} concern` : by.concerns.length ? `${said(by.concerns.length)} concerns` : null,
      by.questions.length === 1 ? `the question ${titleOf(by.questions[0])}` : by.questions.length ? `${said(by.questions.length)} other questions` : null,
      by.releases.length ? "the release plan" : null,
    ].filter(Boolean);
    if (phrases.length <= 3) return phrases.length > 1 ? `${phrases.slice(0, -1).join(", ")} and ${phrases[phrases.length - 1]}` : phrases[0] || "nothing yet";
    return `${phrases.slice(0, 3).join(", ")} and ${phrases.length - 3} more`;
  }

  /* One item per open question that holds something, in attention.ranked's order. Questions that hold nothing yet
     are not a queue: they wait on Who to ask, and the card says how many. */
  let cache = null;
  function build() {
    const holds = new Map();
    const add = (u, key) => { if (!isOpen(ASK[u]) || !key) return; if (!holds.has(u)) holds.set(u, new Set()); holds.get(u).add(key); };
    for (const [key, unknowns] of Object.entries(D.blockedBy)) unknowns.forEach((u) => add(u, key));
    for (const a of D.above) add(a.unknown, a.key);
    const items = [...holds.entries()].map(([id, keys]) => {
      const u = ASK[id], list = [...keys], top = GROUPS.map(([g]) => g).find((g) => list.some((k) => groupOf(k) === g));
      return { id, title: (E[id] || { title: id }).title, question: u.question, level: u.light.level, urgency: u.light.urgency, askBy: u.askBy,
        who: u.ask.name, guess: !!u.ask.inferred, holds: list, group: top, says: say(list) };
    });
    items.sort((a, b) => rank(b.level) - rank(a.level) || b.urgency - a.urgency || cmp(a.id, b.id));
    return items;
  }
  const items = () => (cache = cache || build());
  const holdless = () => D.asks.filter((u) => u.state === "open" && !items().some((x) => x.id === u.id)).length;

  /* The numbers for the top bar and the sidebar: a question counts once, however many things it holds, and a lit
     thing counts only when no question explains it. */
  function counts() {
    const out = {};
    for (const lv of LEVELS) out[lv] = items().filter((x) => x.level === lv).length + otherLit().filter((x) => x.light.level === lv).length;
    return out;
  }
  const otherLit = () => litSubjects().filter((x) => !x.light.reasons.some((r) => r.kind === "held"));
  /* "Needs you" is one count everywhere it is shown: the top bar, the side door, the waiting card and the panel all read it.
     It is the questions that hold something up plus the other things lit overdue or needs-you, each counted once. Pending
     approval and never-examined are lit too, but they are not waiting on the lead, so they are not in it. */
  const NEEDS = ["warning", "caution"];
  function needsYou() {
    const q = items().filter((x) => NEEDS.includes(x.level)), other = otherLit().filter((x) => NEEDS.includes(x.light.level));
    return { n: q.length + other.length, questions: q.length, other: other.length, late: q.filter((x) => x.level === "warning").length + other.filter((x) => x.light.level === "warning").length };
  }
  /* What the number is made of, in words: "20 need you: 16 questions holding things up and 4 other things lit". */
  function needsYouSays() {
    const c = needsYou();
    if (!c.n) return "Nothing needs you";
    const parts = [c.questions ? `${plural(c.questions, "open question")} blocking work` : null, c.other ? `${plural(c.other, "other item")} not decided yet` : null].filter(Boolean);
    return `${c.n} need you: ${parts.join(", and ")}${c.late ? ` (${c.late} overdue)` : ""}`;
  }
  const total = () => needsYou().n;

  function row(it) {
    const late = it.level === "warning", when = isDate(it.askBy) ? relDueWords(it.askBy) : "no date";
    return h("li", {}, h("button", { class: "q-row" + (App.focus === it.id ? " on" : ""), "data-ref": it.id, title: `${it.id}: ${it.question}` },
      lampEl(it.level),
      h("span", { class: "q-main" }, h("span", { class: "q-title" }, it.title),
        h("span", { class: "q-sub" }, `Blocks ${it.says}`),
        h("span", { class: "q-ask" }, `Ask: ${it.who}${it.guess ? " (a guess)" : ""}`)),
      h("span", { class: "q-when" + (late ? " late" : "") }, h("b", {}, day(it.askBy)), h("i", {}, when))));
  }
  function grouped(list) {
    const out = [];
    for (const [id, label] of GROUPS) {
      const here = list.filter((x) => x.group === id);
      if (!here.length) continue;
      out.push(h("section", { class: "q-group", "data-group": id }, h("h4", {}, label, h("span", { class: "ct" }, String(here.length))), h("ul", { class: "q-list" }, here.map(row))));
    }
    return out;
  }
  /* The list, its toggle and the count of questions that hold nothing: the part both homes share. */
  function block() {
    const list = items(), box = h("div", { class: "q-block" });
    if (!list.length) {
      box.append(h("p", { class: "q-none" }, "No open question is blocking anything."));
    } else {
      box.append(...(st.all ? grouped(list) : [h("ul", { class: "q-list" }, list.slice(0, TOP).map(row))]));
      if (list.length > TOP) {
        box.append(h("button", { class: "q-more", "aria-expanded": String(st.all), onclick: () => {
          st.all = !st.all;
          const fresh = block(); box.replaceWith(fresh); $(".q-more", fresh).focus({ preventScroll: true });
        } }, st.all ? `Show the top ${TOP}` : `Show all ${list.length}`));
      }
    }
    const quiet = holdless();
    if (quiet) box.append(h("p", { class: "q-quiet" }, `${plural(quiet, "more open question")} ${quiet === 1 ? "isn't" : "aren't"} blocking anything yet. `, h("button", { class: "linkish", onclick: () => Nav.open("unknowns") }, "See them all")));
    return box;
  }
  /* The card beside the map. In a narrow window it folds to its heading, so the map keeps the screen. */
  /* Beside the map the card takes a third of the width; the reader can fold it to its heading to give the map the
     whole width back, and a window too narrow for both opens it folded. The reader's choice is kept in this browser. */
  const NARROW = 880, FOLD_KEY = "explorer.queue.folded";
  const folded = (width) => width < NARROW || Settings.read(FOLD_KEY) === "1";
  function card(width) {
    const list = items(), fold = folded(width);
    const say1 = needsYou().n ? needsYouSays() : "Nothing is waiting on an answer";
    const el = h("section", { class: "q-card" + (fold ? "" : " open"), "aria-label": "What is waiting on an answer" },
      h("div", { class: "q-head" }, h("span", { class: "q-kicker" }, "Waiting on an answer"), h("span", { class: "q-count" }, say1),
        h("button", { class: "q-fold", "aria-expanded": String(!fold), title: "Hide the list so the map gets the full width", onclick: (ev) => {
          const open = !el.classList.contains("open");
          if (width >= NARROW) { Settings.write(FOLD_KEY, open ? "0" : "1"); rerender(); return; }  // the map refits to the room the fold gave or took
          el.classList.toggle("open", open);  // a narrow window only shows or hides the list; the map keeps its place
          ev.currentTarget.setAttribute("aria-expanded", String(open)); ev.currentTarget.textContent = open ? "Hide" : "Show";
        } }, fold ? "Show" : "Hide")),
      h("div", { class: "q-body" }, list.length ? h("p", { class: "q-hint" }, "Most urgent first. Pick one to read it, with who to ask, in the panel.") : null, block()));
    return el;
  }
  /* The row picked anywhere stays marked here. */
  function sync() { $$(".q-row").forEach((b) => b.classList.toggle("on", b.dataset.ref === App.focus)); }
  return { items, card, folded, block, counts, needsYou, needsYouSays, total, sync, holdless, say, TOP, GROUPS, st, otherLit };
})();
