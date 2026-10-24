/* What the reader has done to the Flows view, apart from the flow itself: which start they follow, which lanes they grouped,
   folded into another, or hid. One flow at a time: every choice is kept per flow and rides in the address (#flows&open=FLO
   &start=S2&group=Channels:APP-a,APP-b&fold=APP-pricing,APP-ledger&hide=PTY-01), the way the Show picker's branch does, so it
   survives a reload and Back and never carries to another flow.

   FlowKit draws a flow as it is handed. flowOf hands it the played flow through apply() below, which returns the same flow
   with the groups drawn as lanes of their own, the folded lanes' steps merged into one step on their host and `view` saying
   which lanes are drawn, what is hidden, what can fold, and which start is picked. Nothing here draws, and nothing here changes
   the record: the steps and starts come from the build (flows_data.py, starts_data.py).

   A group draws several lanes as one (a lane id "grp:channels", neutral in color, not any one app). It is applied first, then
   what can fold is worked out again on the grouped flow, so a group is a lane like any other. Arrows to and from its members
   move onto it, and those that end up the same become one arrow that says who it stands for ("to all 3 in Channels"); what
   passes between its own members becomes a card on its lane with the step numbers kept ("6–7, 2 steps in one"), so no step
   goes missing. The flow page can write groups with mermaid's `box` (the build reads them as flow.groups); they apply when the
   flow opens, `ungroup=Channels` in the address takes one away, and a `group=` in the address wins over the page's. The saved
   clip, the list and the panel keep every app.

   A lane can fold into another when it talks to exactly one other lane, answers it at least once, that lane itself talks to at least two, and it is not
   where the flow starts (a start lane, or with one way in, the lane the first step is in): fold it and its steps read as one step on the other ("Booking prices the stay and takes the
   deposit, via Pricing, Ledger"), with the numbers it hid kept ("5–9"). "Simplify" folds every lane that can. Hiding is
   the reader's own: any lane can go to a narrow dashed column that says its name and how to show it. */
const FlowView = (() => {
  const picked = {}, seen = {}, cache = {}, listeners = [], GROUPS = {};  // flow key -> choices; the address last read; the last answer; who to tell; group lane id -> {name, members}
  let version = 0;
  const enc = encodeURIComponent;
  const SAVED = () => `explorer.lanegroups.${D.vaultId}`, SAVED_MAX = 12;  // groups made on other flows, offered here (newest first)

  const blank = () => ({ start: "all", folded: new Set(), hidden: new Set(), groups: null, ungroup: new Set() });
  /* The groups the address names: "Channels:APP-a,APP-b;Lookups:APP-c,APP-d", each name and ID encoded. */
  function readGroups(text) {
    return text.split(";").filter(Boolean).map((part) => {
      const at = part.indexOf(":");
      return at < 0 ? null : { name: decodeURIComponent(part.slice(0, at)), members: part.slice(at + 1).split(",").filter(Boolean).map(decodeURIComponent) };
    }).filter((g) => g && g.name);
  }
  const writeGroups = (groups) => groups.map((g) => `${enc(g.name)}:${g.members.map(enc).join(",")}`).join(";");
  const names = (text) => (text ? text.split(",").filter(Boolean).map(decodeURIComponent) : []);

  function choices(key) {
    if (!(key in picked)) picked[key] = blank();
    const sig = ["start", "fold", "hide", "group", "ungroup"].map((n) => HASH.get(n) || "").join("|");
    // a pasted link or Back brings its own choices; the page's own changes write the address without reading it back
    if ((HASH.get("present") || HASH.get("open") || (typeof Flows !== "undefined" ? Flows.st.key : "")) === key && sig !== (seen[key] || "")) {
      seen[key] = sig;
      const list = (n) => (HASH.get(n) ? HASH.get(n).split(",").filter(Boolean) : []);
      // the map's own address also has a group= (how it groups apps): only what reads as groups here is one
      const made = HASH.get("group") ? readGroups(HASH.get("group")) : [];
      picked[key] = { start: HASH.get("start") || "all", folded: new Set(list("fold")), hidden: new Set(list("hide")),
        groups: made.length ? made : null, ungroup: new Set(names(HASH.get("ungroup"))) };
      version++;
    }
    return picked[key];
  }
  /* What the address adds for this flow's choices. */
  function hashPart(key) {
    const v = choices(key), out = [];
    if (v.start !== "all") out.push("start=" + enc(v.start));
    if (v.groups) out.push("group=" + writeGroups(v.groups));  // names and IDs are encoded one by one; the : , ; between them read as they are
    else if (v.ungroup.size) out.push("ungroup=" + enc([...v.ungroup].map(enc).join(",")));
    if (v.folded.size) out.push("fold=" + enc([...v.folded].join(",")));
    if (v.hidden.size) out.push("hide=" + enc([...v.hidden].join(",")));
    return out.length ? "&" + out.join("&") : "";
  }

  /* Where the flow starts, for the flow as the page writes it; a branch picked in Show has its own steps and no starts. */
  const startsFor = (flow) => (flow.branch ? null : (FLOW[flow.key] && FLOW[flow.key].starts) || null);
  const actorsOf = (s) => (s.messages.length ? [...new Set(s.messages.flatMap((m) => [m.from, m.to]))] : s.self ? [s.self] : []);
  /* {host lane: [lanes that can fold into it]} for the steps shown. `order` lists the lanes as drawn; `laneOf` says which lane a start's app is drawn in (its group, or itself). */
  function groupsOf(flow, order, laneOf = (id) => id) {
    const partners = {};
    // where the flow starts stays on the stage: its start lanes, or with one way in, the lane of its first step
    const entry = startsFor(flow), first = flow.steps[0] ? actorsOf(flow.steps[0])[0] : null;
    const starts = new Set(entry ? entry.options.map((o) => laneOf(o.lane)) : first ? [flow.steps[0].messages[0] ? flow.steps[0].messages[0].from : first] : []);
    for (const s of flow.steps) for (const m of s.messages) { (partners[m.from] ||= new Set()).add(m.to); (partners[m.to] ||= new Set()).add(m.from); }
    // a lane answers when a request was made of it (its answer comes back) or one of its messages is an answer
    const answers = new Set();
    for (const s of flow.steps) for (const m of s.messages) { if (m.kind === "request") answers.add(m.to); if (m.kind === "answer") answers.add(m.from); }
    const at = (id) => { const i = order.indexOf(id); return i < 0 ? 1e6 : i; };
    const groups = {};
    for (const id of Object.keys(partners)) {
      if (starts.has(id) || partners[id].size !== 1 || !answers.has(id)) continue;
      const host = [...partners[id]][0];
      if (partners[host].size >= 2 && FlowKit.isLane(id)) (groups[host] ||= []).push(id);
    }
    for (const host of Object.keys(groups)) groups[host].sort((a, b) => at(a) - at(b));
    return groups;
  }

  const lead = (step) => { const t = FlowKit.stepSays(step), m = t.match(/^.*?[.!?](?=\s|$)/); return (m ? m[0] : t).replace(/\.$/, "").trim(); };
  const uniq = (list, by) => { const seenIds = new Set(); return list.filter((x) => { const k = by ? by(x) : x; if (seenIds.has(k)) return false; seenIds.add(k); return true; }); };
  const lastNo = (x) => (x.run ? x.run[x.run.length - 1].n : x.n);
  /* The step several steps become: numbered by the first ("5–9" for a run), carrying everything the steps in it carried. A fold and a group's inside card both make it. */
  function joined(run) {
    const first = run[0], last = run[run.length - 1];
    return { n: first.n, nLabel: run.length > 1 ? `${first.n}–${lastNo(last)}` : String(first.n), folded: true, run, messages: [],
      text: run.map((x) => x.text).join(" "), html: run.map((x) => x.html).join(" "), unknowns: uniq(run.flatMap((x) => x.unknowns), (p) => p.id),
      contracts: uniq(run.flatMap((x) => x.contracts)), linked: uniq(run.flatMap((x) => x.linked || [])), named: uniq(run.flatMap((x) => x.named || [])),
      differs: run.some((x) => x.differs), ref: null, unrecorded: false, fromTable: false, recordsPair: false, lanesNamed: 0, start: first.start || "" };
  }
  function merged(run, host, hostOf) {
    const via = uniq(run.flatMap(actorsOf).filter((a) => hostOf(a) === host)).map(FlowKit.laneName);
    const own = run.filter((x) => x.messages.some((m) => m.from === host));  // what the host asked for; the answers coming back add nothing to say
    const say = (own.length ? own : run).map((x) => upFirst(lead(x))).join("; ");
    return { ...joined(run), self: host, via, say, says: say, short: say };
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

  /* ---------- groups */
  const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "group";
  /* "grp:channels"; a second group of the same name gets a 2 on its ID. */
  function idFor(name, taken) { let id = "grp:" + slug(name), n = 2; while (taken.has(id)) id = `grp:${slug(name)}${n++}`; return id; }
  const pageGroups = (key) => ((FLOW[key] && FLOW[key].groups) || []).map((g) => ({ name: g.name, members: g.lanes.slice() }));
  /* The groups this flow is asked to draw: the address's (made by the reader, or sent in a link), else the ones its page writes except those the reader took apart. */
  const wanted = (key, v) => (v.groups ? v.groups.map((g) => ({ ...g, members: g.members.slice() })) : pageGroups(key).filter((g) => !v.ungroup.has(g.name)));
  const sameGroup = (a, b) => a.name === b.name && a.members.length === b.members.length && a.members.every((m) => b.members.includes(m));
  const placesOf = (m) => `${FlowKit.laneName(m.from)} to ${FlowKit.laneName(m.to)}`;

  /* One step as the groups see it: the arrows to and from members move onto the group (those that end up the same become one, saying who they stand for),
     what passes between members of one group is kept as an inside card on it, and a step that is only that becomes a beat to merge with its neighbors. */
  function remapStep(s, by, memberOf, order) {
    const out = [], inside = new Map(), at = new Map(), ends = new Map();
    const note = (msg, lane, member) => { const e = (ends.get(msg) || ends.set(msg, new Map()).get(msg)); (e.get(lane) || e.set(lane, new Set()).get(lane)).add(member); };
    let changed = false;
    for (const m of s.messages) {
      const gf = memberOf[m.from], gt = memberOf[m.to];
      if (gf && gf === gt) { (inside.get(gf) || inside.set(gf, []).get(gf)).push(m); continue; }
      if (!gf && !gt) { out.push(m); continue; }
      changed = true;
      const from = gf || m.from, to = gt || m.to, sig = [from, to, m.contract, m.kind, m.direction].join("|");
      let one = at.get(sig);
      if (!one) { one = { ...m, from, to }; at.set(sig, one); out.push(one); }
      if (gf) note(one, from, m.from);
      if (gt) note(one, to, m.to);
    }
    for (const [msg, lanes] of ends) {
      msg.groupEnds = [...lanes].map(([lane, set]) => { const members = [...set].sort((a, b) => order.indexOf(a) - order.indexOf(b)); return { lane, members, all: members.length === by[lane].members.length }; });
    }
    const selfIn = !s.messages.length && s.self && memberOf[s.self] ? memberOf[s.self] : null;
    if (selfIn) return { step: s, beatOf: selfIn, places: [FlowKit.laneName(s.self)], lone: true };
    if (!changed && !inside.size) return { step: s };
    if (!out.length && inside.size === 1) { const [gid, msgs] = [...inside][0]; return { step: s, beatOf: gid, places: uniq(msgs.map(placesOf)) }; }
    const cards = [...inside].map(([gid, msgs]) => ({ lane: gid, say: upFirst(lead(s)), via: `inside ${by[gid].name}: ${uniq(msgs.map(placesOf)).join("; ")}`, stacked: false }));
    return { step: { ...s, messages: out, inside: cards.length ? cards : undefined, plain: s } };
  }
  /* Back-to-back steps that happen entirely inside one group: one beat on its lane, numbered by the first and the last ("6–7, 2 steps in one"). */
  function beat(items, group) {
    const run = items.map((x) => x.step), say = run.map((x) => upFirst(lead(x))).join("; ");
    const places = uniq(items.flatMap((x) => x.places)), lone = items.length === 1 && items[0].lone;
    const viaText = lone ? `in ${places[0]}` : `inside ${group.name}: ${places.join("; ")}${run.length > 1 ? ` · ${run.length} steps in one` : ""}`;
    return { ...joined(run), grouped: true, self: group.id, via: [], viaText, say, says: say, short: say };
  }
  function groupSteps(steps, live, memberOf, order) {
    const by = Object.fromEntries(live.map((g) => [g.id, g])), one = steps.map((s) => remapStep(s, by, memberOf, order)), out = [];
    for (let i = 0; i < one.length;) {
      const x = one[i];
      if (!x.beatOf) { out.push(x.step); i++; continue; }
      let j = i;  // a merge never crosses from one start's steps into another's
      while (j + 1 < one.length && one[j + 1].beatOf === x.beatOf && (one[j + 1].step.start || "") === (x.step.start || "")) j++;
      out.push(beat(one.slice(i, j + 1), by[x.beatOf]));
      i = j + 1;
    }
    return out;
  }
  /* The stage the groups make of a flow: the groups that can be drawn (and what could not be, said), the lanes in the order drawn, and the steps with the groups applied. */
  function groupStage(base, v, key) {
    const touched = FlowKit.touchedLanes(base), order = FlowKit.laneOrder(base), said = [], taken = new Set(), live = [], ids = new Set();
    const asked = wanted(key, v), link = !!v.groups, page = pageGroups(key);
    for (const g of asked) {
      const present = g.members.filter((m) => touched.has(m)), free = present.filter((m) => !taken.has(m));
      if (link) {
        for (const m of g.members) if (!touched.has(m)) said.push(`This link groups ${titleOf(m)}, which isn't in this flow.`);
        for (const m of present) if (taken.has(m)) said.push(`This link puts ${titleOf(m)} in two groups, so ${g.name} doesn't take it.`);
      }
      if (free.length < 2) { if (link) said.push(`${g.name} has fewer than two lanes in this flow, so it isn't drawn.`); continue; }
      if (free.length >= touched.size) { said.push(`${g.name} would be every lane in this flow, so it isn't drawn.`); continue; }
      const id = idFor(g.name, ids), members = free.sort((a, b) => order.indexOf(a) - order.indexOf(b));
      ids.add(id); free.forEach((m) => taken.add(m));
      const source = page.some((p) => sameGroup(p, { name: g.name, members })) ? "page" : "you";
      live.push({ id, name: g.name, members, source });
      GROUPS[id] = { name: g.name, members };
    }
    const memberOf = {};
    for (const g of live) for (const m of g.members) memberOf[m] = g.id;
    const laneObj = (id) => { const g = live.find((x) => x.id === id); return g ? { id, name: g.name, group: { members: g.members, source: g.source } } : D.lanes[LANE_INDEX[id]]; };
    const drawn = [];
    for (const id of order) { const lane = memberOf[id] || id; if (!drawn.includes(lane)) drawn.push(lane); }
    return { live, said, memberOf, order, drawn, lanes: drawn.map(laneObj), steps: live.length ? groupSteps(base.steps, live, memberOf, order) : base.steps };
  }
  /* The same, for the flow whole (what the controls and the list ask about), kept until a choice changes. */
  function stageOf(key) {
    const base = FlowKit.flowOf(key, { plain: true }), tag = `${base.branch || ""}|${version}`;
    const hit = cache["stage:" + key];
    if (hit && hit.tag === tag) return hit.stage;
    const stage = groupStage(base, choices(key), key);
    cache["stage:" + key] = { tag, stage };
    return stage;
  }
  const groupedFlow = (key) => { const base = FlowKit.flowOf(key, { plain: true }), st = stageOf(key); return { ...base, steps: st.steps }; };
  const foldHosts = (key) => { const st = stageOf(key); return groupsOf(groupedFlow(key), st.drawn, (id) => st.memberOf[id] || id); };

  /* The flow FlowKit draws: `base` with the reader's groups and folds applied and `view` for the rest. */
  function apply(base) {
    const key = base.key;
    if (!key || !FLOW[key]) return base;
    const v = choices(key), tag = `${base.branch || ""}|${version}|${v.start}`;
    if (cache[key] && cache[key].tag === tag) return cache[key].flow;
    const stage = groupStage(base, v, key), grouped = { ...base, steps: stage.steps };
    const groups = groupsOf(grouped, stage.drawn, (id) => stage.memberOf[id] || id), touched = FlowKit.touchedLanes(grouped);
    const hostOf = (id) => Object.keys(groups).find((h) => v.folded.has(h) && groups[h].includes(id)) || null;
    const folding = Object.keys(groups).some((h) => v.folded.has(h));
    const hosts = {};
    for (const host of Object.keys(groups)) {
      const members = groups[host], foldedNow = v.folded.has(host);
      const pins = uniq(stage.steps.filter((s) => actorsOf(s).some((a) => members.includes(a))).flatMap((s) => s.unknowns), (p) => p.id);
      hosts[host] = { members, folded: foldedNow, open: pins.filter((p) => ASK[p.id] && ASK[p.id].state === "open").length };
    }
    const entry = startsFor(base), start = entry && entry.options.some((o) => o.id === v.start) ? v.start : "all";
    // what a pasted link asked for that this flow no longer has, said on the page rather than dropped
    const ignored = [];
    if (!base.branch && v.start !== "all" && start === "all") ignored.push(`a start (${v.start})`);
    for (const h of v.folded) if (!groups[h]) ignored.push(`folding ${titleOf(h)}`);
    for (const l of v.hidden) if (!touched.has(l)) ignored.push(`hiding ${titleOf(l)}`);
    const flow = { ...base, starts: entry, steps: folding ? foldSteps(stage.steps, hostOf) : stage.steps,
      view: { start, hidden: new Set([...v.hidden].filter((id) => touched.has(id))), hosts, groups, ignored, said: stage.said, lanes: stage.lanes, laneGroups: stage.live, memberOf: stage.memberOf } };
    cache[key] = { tag, flow };
    return flow;
  }

  function changed() { version++; listeners.forEach((fn) => fn()); }
  const watch = (fn) => { listeners.push(fn); };
  const keepInHash = (key) => {
    const kept = (location.hash || "#").slice(1).split("&").filter((p) => p && !/^(start|fold|hide|group|ungroup)=/.test(p));
    history.replaceState(null, "", "#" + kept.join("&") + hashPart(key));
  };
  const change = (key, fn) => { choices(key); fn(picked[key]); keepInHash(key); changed(); };

  const setStart = (key, id) => change(key, (v) => { v.start = id || "all"; });
  const toggleFold = (key, host) => change(key, (v) => { v.folded.has(host) ? v.folded.delete(host) : v.folded.add(host); });
  const hide = (key, lane) => change(key, (v) => { v.hidden.add(lane); });
  const show = (key, lane) => change(key, (v) => { v.hidden.delete(lane); });
  /* Simplify: every lane that can fold, folded; pressed again, none. */
  function simplify(key) {
    const hosts = Object.keys(foldHosts(key));
    change(key, (v) => { const on = hosts.length > 0 && hosts.every((h) => v.folded.has(h)); hosts.forEach((h) => (on ? v.folded.delete(h) : v.folded.add(h))); });
  }

  /* ---------- making and taking apart groups */
  function remember(key, group) {
    const saved = Settings.readJson(SAVED(), [], "your lane groups").filter((g) => !(g.name === group.name && g.flow === key));
    saved.unshift({ name: group.name, members: group.members, flow: key });
    Settings.write(SAVED(), JSON.stringify(saved.slice(0, SAVED_MAX)));
  }
  /* A choice a change to the groups makes impossible is cleared, never dropped quietly: a fold that has one of these lanes in it (as the lane that folds or the lane folded in), a lane hidden that is now a member. */
  function clearBroken(key, v, why, ids, hostsBefore) {
    const out = [];
    for (const h of [...v.folded]) {
      const hit = ids.includes(h) ? [h] : (hostsBefore[h] || []).filter((m) => ids.includes(m));
      if (hit.length) { v.folded.delete(h); out.push(["Unfolded", hit.map(titleOf).join(" and ")]); }
    }
    for (const l of [...v.hidden]) if (ids.includes(l)) { v.hidden.delete(l); out.push(["Showed", titleOf(l)]); }
    return out.map(([verb, what]) => `${verb} ${what} ${why}`).join(". ");
  }
  /* Draw these lanes as one. Returns what had to be cleared, in words, or "". */
  function makeGroup(key, name, members) {
    let said = "";
    const hostsBefore = foldHosts(key);
    change(key, (v) => {
      const now = wanted(key, v);
      const clean = name.trim() || "Group", unique = now.some((g) => g.name === clean) ? `${clean} 2` : clean;
      v.groups = [...now.map((g) => ({ ...g, members: g.members.filter((m) => !members.includes(m)) })).filter((g) => g.members.length >= 2), { name: unique, members: members.slice() }];
      v.ungroup = new Set();
      said = clearBroken(key, v, "to group it", members, hostsBefore);
      remember(key, { name: unique, members });
    });
    if (said) toast(said);
    return said;
  }
  /* Draw a group's lanes apart again. A group the page writes goes into `ungroup`; one the reader made is taken out of the list. */
  function ungroup(key, id) {
    const g = stageOf(key).live.find((x) => x.id === id);
    if (!g) return;
    let said = "";
    const hostsBefore = foldHosts(key);
    change(key, (v) => {
      if (!v.groups) v.ungroup.add(g.name);
      else {
        v.groups = v.groups.filter((x) => x.name !== g.name);
        if (!v.groups.length) { v.groups = null; v.ungroup = new Set(pageGroups(key).map((p) => p.name)); }
      }
      said = clearBroken(key, v, "to ungroup it", [id], hostsBefore);
    });
    if (said) toast(said);
  }
  function renameGroup(key, id, name) {
    const g = stageOf(key).live.find((x) => x.id === id), clean = (name || "").trim();
    if (!g || !clean || clean === g.name) return;
    change(key, (v) => {
      const now = wanted(key, v).map((x) => (x.name === g.name ? { ...x, name: clean } : x));
      v.groups = now; v.ungroup = new Set();
      const next = idFor(clean, new Set(now.filter((x) => x.name !== clean).map((x) => "grp:" + slug(x.name))));
      for (const set of [v.folded, v.hidden]) if (set.delete(id)) set.add(next);
      remember(key, { name: clean, members: g.members });
    });
  }
  /* Groups offered, never applied: the business areas the map names (two or more of this flow's lanes in one), and groups made on other flows in this browser. */
  function suggestions(key) {
    const touched = FlowKit.touchedLanes(FlowKit.flowOf(key, { plain: true })), order = stageOf(key).order, out = [], by = {};
    const inFlow = (ids) => ids.filter((m) => touched.has(m)).sort((a, b) => order.indexOf(a) - order.indexOf(b));
    for (const id of order) { const d = D.domains && D.domains[id]; if (d && d !== "No domain") (by[d] ||= []).push(id); }
    for (const [d, members] of Object.entries(by)) if (members.length >= 2) out.push({ name: d, members, why: "business area on the map" });
    for (const g of Settings.readJson(SAVED(), [], "your lane groups")) {
      const members = inFlow(g.members || []);
      if (g.flow !== key && members.length >= 2 && E[g.flow]) out.push({ name: g.name, members, why: `made on ${E[g.flow].title}` });
    }
    const have = new Set(stageOf(key).live.map((g) => g.members.join())), offered = [];
    for (const g of out) {  // not one that is already drawn, not one that would be every lane, and each set of lanes once
      if (g.members.length >= touched.size || have.has(g.members.join())) continue;
      have.add(g.members.join()); offered.push(g);
    }
    return offered;
  }

  /* What the header controls need to know. */
  const plain = (key) => FlowKit.flowOf(key, { plain: true });
  const hostsOf = (key) => foldHosts(key);
  const simplified = (key) => { const hosts = Object.keys(hostsOf(key)); return hosts.length > 0 && hosts.every((h) => choices(key).folded.has(h)); };
  const foldedLanes = (key) => Object.entries(hostsOf(key)).filter(([h]) => choices(key).folded.has(h)).flatMap(([, members]) => members);
  const startsOf = (key) => startsFor(plain(key));
  const startPicked = (key) => { const f = FlowKit.flowOf(key); return f.view ? f.view.start : "all"; };
  /* A step of the start the reader did not pick (dimmed on the stage; Next and Previous go past it). */
  const dimmedStep = (key, step) => { const f = FlowKit.flowOf(key); return !!f.view && f.view.start !== "all" && !!step.start && step.start !== f.view.start; };
  const isHidden = (key, lane) => choices(key).hidden.has(lane);
  const groupsFor = (key) => stageOf(key).live;
  const laneIds = (key) => stageOf(key).order;
  const groupName = (id) => (GROUPS[id] ? GROUPS[id].name : id.slice(4));
  const groupEnt = (id) => (GROUPS[id] ? { key: id, kind: "group", title: GROUPS[id].name, id: "" } : null);
  const saidAbout = (key) => stageOf(key).said;

  return { apply, hashPart, watch, setStart, toggleFold, hide, show, simplify, hostsOf, simplified, foldedLanes, startsOf, startPicked, dimmedStep, isHidden, choices, keepInHash,
    makeGroup, ungroup, renameGroup, suggestions, groupsFor, laneIds, groupName, groupEnt, saidAbout, pageGroups, groupedFlow };
})();
