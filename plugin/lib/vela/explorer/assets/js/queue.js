/* The queue: the open questions that hold something up, ranked as attention.ranked ranks them (level, then urgency, then
   ID), each with what it holds up said in plain words. It is data, not a page: Needs you reads a question's "holds up" words
   from it, the overview cards say what a question holds with `say`, and the counts below are what the details and the
   sidebar quote. The What's waiting page, the panel list and the "Waiting on you" filter that drew it are gone; Needs you
   lists what is for the person viewing. */
const Queue = (() => {
  const TOP = 5;  // the overview's "top" cut, kept for the selftest
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
     are not a queue: they wait on Who to ask, and the panel's list says how many. */
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

  /* The numbers for the top bar and the sidebar: a question counts once, however many things it holds, and a lit
     thing counts only when no question explains it. */
  function counts() {
    const out = {};
    for (const lv of LEVELS) out[lv] = items().filter((x) => x.level === lv).length + otherLit().filter((x) => x.light.level === lv).length;
    return out;
  }
  const otherLit = () => litSubjects().filter((x) => !x.light.reasons.some((r) => r.kind === "held"));
  /* One count of what the plan is waiting on: the questions that hold something up plus the other things lit overdue or needs-you, each counted once. Pending
     approval and never-examined are lit too, but they are not waiting on the lead, so they are not in it. */
  const NEEDS = ["warning", "caution"];
  function needsYou() {
    const q = items().filter((x) => NEEDS.includes(x.level)), other = otherLit().filter((x) => NEEDS.includes(x.light.level));
    return { n: q.length + other.length, questions: q.length, other: other.length, late: q.filter((x) => x.level === "warning").length + other.filter((x) => x.light.level === "warning").length };
  }
  return { items, counts, needsYou, say, TOP, GROUPS, otherLit };
})();
