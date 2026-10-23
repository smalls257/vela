/* What the reader has done to the Flows view, apart from the flow itself: which start they follow, which lanes they folded
   into another, which they hid. One flow at a time: every choice is kept per flow and rides in the address (#flows&open=FLO
   &start=S2&fold=APP-pricing,APP-ledger&hide=PTY-01), the way the Show picker's branch does, so it survives a reload and Back
   and never carries to another flow.

   FlowKit draws a flow as it is handed. flowOf hands it the played flow through apply() below, which returns the same flow
   with the folded lanes' steps merged into one step on their host and `view` saying what is hidden, what can fold, and which
   start is picked. Nothing here draws, and nothing here changes the record: the steps and starts come from the build
   (flows_data.py, starts_data.py).

   A lane can fold into another when it talks to exactly one other lane, which itself talks to at least two, and it is not
   where the flow starts (a start lane, or with one way in, the lane the first step is in): fold it and its steps read as one step on the other ("Booking prices the stay and takes the
   deposit, via Pricing, Ledger"), with the numbers it hid kept ("5–9"). "Simplify" folds every lane that can. Hiding is
   the reader's own: any lane can go to a narrow dashed column that says its name and how to show it. */
const FlowView = (() => {
  const picked = {}, seen = {}, cache = {}, listeners = [];  // flow key -> choices; the address last read; the last answer; who to tell
  let version = 0;
  const enc = encodeURIComponent;

  function choices(key) {
    if (!(key in picked)) picked[key] = { start: "all", folded: new Set(), hidden: new Set() };
    const sig = ["start", "fold", "hide"].map((n) => HASH.get(n) || "").join("|");
    // a pasted link or Back brings its own choices; the page's own changes write the address without reading it back
    if ((HASH.get("present") || HASH.get("open") || (typeof Flows !== "undefined" ? Flows.st.key : "")) === key && sig !== (seen[key] || "")) {
      seen[key] = sig;
      const list = (n) => (HASH.get(n) ? HASH.get(n).split(",").filter(Boolean) : []);
      picked[key] = { start: HASH.get("start") || "all", folded: new Set(list("fold")), hidden: new Set(list("hide")) };
      version++;
    }
    return picked[key];
  }
  /* What the address adds for this flow's choices. */
  function hashPart(key) {
    const v = choices(key), out = [];
    if (v.start !== "all") out.push("start=" + enc(v.start));
    if (v.folded.size) out.push("fold=" + enc([...v.folded].join(",")));
    if (v.hidden.size) out.push("hide=" + enc([...v.hidden].join(",")));
    return out.length ? "&" + out.join("&") : "";
  }

  /* Where the flow starts, for the flow as the page writes it; a branch picked in Show has its own steps and no starts. */
  const startsFor = (flow) => (flow.branch ? null : (FLOW[flow.key] && FLOW[flow.key].starts) || null);
  const actorsOf = (s) => (s.messages.length ? [...new Set(s.messages.flatMap((m) => [m.from, m.to]))] : s.self ? [s.self] : []);
  /* {host lane: [lanes that can fold into it]} for the steps shown. */
  function groupsOf(flow) {
    const partners = {};
    // where the flow starts stays on the stage: its start lanes, or with one way in, the lane of its first step
    const entry = startsFor(flow), first = flow.steps[0] ? actorsOf(flow.steps[0])[0] : null;
    const starts = new Set(entry ? entry.options.map((o) => o.lane) : first ? [flow.steps[0].messages[0] ? flow.steps[0].messages[0].from : first] : []);
    for (const s of flow.steps) for (const m of s.messages) { (partners[m.from] ||= new Set()).add(m.to); (partners[m.to] ||= new Set()).add(m.from); }
    const groups = {};
    for (const id of Object.keys(partners)) {
      if (starts.has(id) || partners[id].size !== 1) continue;
      const host = [...partners[id]][0];
      if (partners[host].size >= 2 && LANE_INDEX[id] !== undefined) (groups[host] ||= []).push(id);
    }
    for (const host of Object.keys(groups)) groups[host].sort((a, b) => LANE_INDEX[a] - LANE_INDEX[b]);
    return groups;
  }

  const lead = (step) => { const t = FlowKit.stepSays(step), m = t.match(/^.*?[.!?](?=\s|$)/); return (m ? m[0] : t).replace(/\.$/, "").trim(); };
  const uniq = (list, by) => { const seenIds = new Set(); return list.filter((x) => { const k = by ? by(x) : x; if (seenIds.has(k)) return false; seenIds.add(k); return true; }); };
  function merged(run, host, hostOf) {
    const first = run[0], last = run[run.length - 1];
    const via = uniq(run.flatMap(actorsOf).filter((a) => hostOf(a) === host)).map(FlowKit.laneName);
    const own = run.filter((x) => x.messages.some((m) => m.from === host));  // what the host asked for; the answers coming back add nothing to say
    const say = (own.length ? own : run).map((x) => upFirst(lead(x))).join("; ");
    return { n: first.n, nLabel: run.length > 1 ? `${first.n}–${last.n}` : String(first.n), folded: true, run, self: host, messages: [], via, say, says: say, short: say,
      text: run.map((x) => x.text).join(" "), html: run.map((x) => x.html).join(" "), unknowns: uniq(run.flatMap((x) => x.unknowns), (p) => p.id),
      contracts: uniq(run.flatMap((x) => x.contracts)), linked: uniq(run.flatMap((x) => x.linked || [])), named: uniq(run.flatMap((x) => x.named || [])),
      differs: run.some((x) => x.differs), ref: null, unrecorded: false, fromTable: false, recordsPair: false, lanesNamed: 0, start: first.start || "" };
  }
  /* Steps that run back to back inside a host and the lanes folded into it become one step; the run never crosses from one start's steps into another's. */
  function foldSteps(steps, hostOf) {
    const out = [];
    for (let i = 0; i < steps.length;) {
      const s = steps[i], host = actorsOf(s).map(hostOf).find(Boolean);
      if (!host) { out.push(s); i++; continue; }
      const inside = (x) => { const a = actorsOf(x); return a.length > 0 && a.every((id) => id === host || hostOf(id) === host) && (x.start || "") === (s.start || ""); };
      const touches = (x) => actorsOf(x).some((id) => hostOf(id) === host);
      let j = i;
      while (j + 1 < steps.length && inside(steps[j + 1])) j++;
      while (j > i && !touches(steps[j])) j--;
      out.push(merged(steps.slice(i, j + 1), host, hostOf));
      i = j + 1;
    }
    return out;
  }

  /* The flow FlowKit draws: `base` with the reader's folds applied and `view` for the rest. */
  function apply(base) {
    const key = base.key;
    if (!key || !FLOW[key]) return base;
    const v = choices(key), tag = `${base.branch || ""}|${version}|${v.start}`;
    if (cache[key] && cache[key].tag === tag) return cache[key].flow;
    const groups = groupsOf(base), touched = FlowKit.touchedLanes(base);
    const hostOf = (id) => Object.keys(groups).find((h) => v.folded.has(h) && groups[h].includes(id)) || null;
    const folding = Object.keys(groups).some((h) => v.folded.has(h));
    const hosts = {};
    for (const host of Object.keys(groups)) {
      const members = groups[host], foldedNow = v.folded.has(host);
      const pins = uniq(base.steps.filter((s) => actorsOf(s).some((a) => members.includes(a))).flatMap((s) => s.unknowns), (p) => p.id);
      hosts[host] = { members, folded: foldedNow, open: pins.filter((p) => ASK[p.id] && ASK[p.id].state === "open").length };
    }
    const entry = startsFor(base), start = entry && entry.options.some((o) => o.id === v.start) ? v.start : "all";
    const flow = { ...base, starts: entry, steps: folding ? foldSteps(base.steps, hostOf) : base.steps, view: { start, hidden: new Set([...v.hidden].filter((id) => touched.has(id))), hosts, groups } };
    cache[key] = { tag, flow };
    return flow;
  }

  function changed() { version++; listeners.forEach((fn) => fn()); }
  const watch = (fn) => { listeners.push(fn); };
  const keepInHash = (key) => {
    const kept = (location.hash || "#").slice(1).split("&").filter((p) => p && !/^(start|fold|hide)=/.test(p));
    history.replaceState(null, "", "#" + kept.join("&") + hashPart(key));
  };
  const change = (key, fn) => { choices(key); fn(picked[key]); keepInHash(key); changed(); };

  const setStart = (key, id) => change(key, (v) => { v.start = id || "all"; });
  const toggleFold = (key, host) => change(key, (v) => { v.folded.has(host) ? v.folded.delete(host) : v.folded.add(host); });
  const hide = (key, lane) => change(key, (v) => { v.hidden.add(lane); });
  const show = (key, lane) => change(key, (v) => { v.hidden.delete(lane); });
  /* Simplify: every lane that can fold, folded; pressed again, none. */
  function simplify(key) {
    const hosts = Object.keys(groupsOf(FlowKit.flowOf(key, { plain: true })));
    change(key, (v) => { const on = hosts.length > 0 && hosts.every((h) => v.folded.has(h)); hosts.forEach((h) => (on ? v.folded.delete(h) : v.folded.add(h))); });
  }

  /* What the header controls need to know. */
  const plain = (key) => FlowKit.flowOf(key, { plain: true });
  const hostsOf = (key) => groupsOf(plain(key));
  const simplified = (key) => { const hosts = Object.keys(hostsOf(key)); return hosts.length > 0 && hosts.every((h) => choices(key).folded.has(h)); };
  const foldedLanes = (key) => Object.entries(hostsOf(key)).filter(([h]) => choices(key).folded.has(h)).flatMap(([, members]) => members);
  const startsOf = (key) => startsFor(plain(key));
  const startPicked = (key) => { const f = FlowKit.flowOf(key); return f.view ? f.view.start : "all"; };
  /* A step of the start the reader did not pick (dimmed on the stage; Next and Previous go past it). */
  const dimmedStep = (key, step) => { const f = FlowKit.flowOf(key); return !!f.view && f.view.start !== "all" && !!step.start && step.start !== f.view.start; };
  const isHidden = (key, lane) => choices(key).hidden.has(lane);

  return { apply, hashPart, watch, setStart, toggleFold, hide, show, simplify, hostsOf, simplified, foldedLanes, startsOf, startPicked, dimmedStep, isHidden, choices, keepInHash };
})();
