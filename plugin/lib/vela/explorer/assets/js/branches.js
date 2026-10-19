/* Error cases on the Flows view (design 19, decision D8). One diagram: a flow whose checked sequence diagram has alt
   branches gets a "Show" picker in its header row, beside the flow picker. "Happy path" is first and chosen, and is
   the played flow as it always was; any other choice redraws the same lane view with that branch's steps (FlowKit
   reads them through flowOf), the steps that leave the happy path outlined in amber, later steps that follow from
   the branch drawn, and the ones it skips gone. An option cannot hold an icon, so each says the flow check's word on
   it in its label ("finding", "not fully checked"); nothing is shown as passed unless the check ran to the end. The
   summary line sits under the header row, the chosen branch's finding under the diagram, in plain words. The branch
   rides in the address (#flows&open=FLO&branch=CON-004.timeout). Everything comes from branches_data.py, which reads
   the diagram through the flow checker's own readers; nothing here parses mermaid. */
const Branches = (() => {
  const chosen = {}, seen = {};  // flow key -> option id; and the branch the address last named

  const data = (key) => (D.branches || {})[key];
  const options = (d) => [d.happy, ...d.groups.flatMap((g) => g.options)];
  function current(key) {
    const d = data(key);
    if (!d || d.state !== "drawn") return null;
    const named = HASH.get("branch"), mine = named && (HASH.get("open") || Flows.st.key) === key && options(d).some((o) => o.id === named);
    if (mine && named !== seen[key]) { chosen[key] = named; seen[key] = named; }  // a pasted link or Back brings its own branch
    if (!(key in chosen)) chosen[key] = "happy";
    return options(d).find((o) => o.id === chosen[key] && o.drawn !== false) || d.happy;
  }
  /* What Flows.select and Nav.syncHash add to the address, so the branch survives a step change and a reload. */
  const hashPart = (key) => { const o = current(key); return o && o.id !== "happy" ? `&branch=${encodeURIComponent(o.id)}` : ""; };
  function keepInHash(key) {
    const kept = (location.hash || "#").slice(1).split("&").filter((p) => p && !p.startsWith("branch="));
    history.replaceState(null, "", "#" + kept.join("&") + hashPart(key));
  }
  const words = (o) => o.label + (o.marks.length ? ` (${o.marks.join(", ")})` : "");

  /* The played flow for the chosen branch, in the shape FlowKit draws; null for the happy path, which is the flow as
     its page writes it. Open questions keep their place on the first step over the contract the page pins them to. */
  function flowFor(key) {
    const d = data(key), o = current(key);
    if (!o || o.id === "happy") return null;
    const lane = (pid) => {
      const p = d.participants.find((x) => x.id === pid);
      if (!p) return undefined;
      if (p.key && LANE_INDEX[p.key] !== undefined) return p.key;
      const named = D.lanes.find((l) => l.name.toLowerCase() === p.title.toLowerCase());
      return named ? named.id : undefined;
    };
    const pins = {}, pinned = new Set();
    for (const stp of FLOW[key].steps) for (const c of stp.contracts) if (!pins[c]) pins[c] = stp.unknowns;
    const steps = o.steps.map((x) => {
      const from = lane(x.from), to = lane(x.to), arrow = !!(x.item && CONTRACT[x.item] && from && to && from !== to);
      const unknowns = arrow && !pinned.has(x.item) ? (pins[x.item] || []) : [];
      if (arrow) pinned.add(x.item);
      // the ending is a band across the flow, as the page's own last step is; any other step inside one app loops on its lane
      const self = arrow || x.kind === "end" ? null : lane(x.from) || (x.over || []).map(lane).find(Boolean) || null;
      return { n: x.n, short: x.short, text: x.short, html: esc(x.short), differs: !!x.differs, ref: null, unknowns, linked: [], named: [], fromTable: false,
        contracts: x.item && CONTRACT[x.item] ? [x.item] : [], self,
        messages: arrow ? [{ from, to, contract: x.item, direction: "stated", kind: x.kind === "request" ? "request" : x.kind === "answer" ? "answer" : "send" }] : [] };
    });
    const e = E[key];
    return { key, id: e.id, title: e.title, state: e.state || "", steps, unknowns: FLOW[key].unknowns, branch: o.id };
  }

  /* The answer first: "One of the 5 ways this flow can go wrong has a problem; pick it under Show to see what and who
     owns it." Then what the check couldn't see: branches it didn't finish, replies nobody drew. */
  function countLine(d) {
    const n = d.counts.branches, f = d.counts.withFindings, gap = d.counts.notDrawn, unchecked = d.counts.notChecked;
    const ways = `${n === 1 ? "way" : "ways"} this flow can go wrong`;
    const lead = f ? `${f === 1 ? "One" : f} of the ${n} ${ways} ${f === 1 ? "has a problem" : "have problems"}; pick ${f === 1 ? "it" : "one"} under Show to see what and who owns it.`
      : `This flow can go wrong ${plural(n, "way")}, and ${n === 1 ? "it doesn't" : "none of them"} ${n === 1 ? "break" : "breaks"} the flow.`;
    const more = [unchecked ? `${unchecked} ${unchecked === 1 ? "wasn't" : "weren't"} fully checked` : "", gap ? `${gap} ${gap === 1 ? "reply isn't" : "replies aren't"} drawn yet` : ""].filter(Boolean);
    const tail = !unchecked && d.check.status === "passes" ? " The flow check passes." : "";
    return `${lead}${more.length ? " " + upFirst(more.join(", and ")) + "." : ""}${tail}`;
  }

  /* The picker, for the header row, styled as the flow picker's button is. */
  function picker(key, onPick) {
    const d = data(key);
    if (!d || d.state !== "drawn") return null;
    const id = `br-pick-${key}`, o = current(key);
    const sel = h("select", { class: "br-pick", id },
      h("option", { value: "happy", selected: o.id === "happy" ? "" : null }, words(d.happy)),
      d.groups.map((g) => h("optgroup", { label: g.label }, g.options.map((x) => h("option", { value: x.id, disabled: x.drawn ? null : "", selected: o.id === x.id ? "" : null }, words(x))))));
    sel.value = o.id;
    sel.addEventListener("change", () => { chosen[key] = sel.value; keepInHash(key); onPick(key); });
    return h("div", { class: "br-picker", "data-branches": key }, h("label", { for: id, class: "fp-kind" }, "Show"), sel);
  }

  /* Under the header row: how many ways the flow can go, or that its error cases are not drawn yet; and the limits
     the check rests on that the chosen branch runs into, in the checker's own words. */
  function summary(key) {
    const d = data(key);
    if (!d) return null;
    if (d.state !== "drawn") return h("p", { class: "br-note", "data-branches-note": key }, d.note);
    const o = current(key), limits = (o.limits || []).map((i) => d.limits[i]);
    return h("div", { class: "br-summary", "data-branches-summary": key }, h("p", { class: "br-sum" }, countLine(d)),
      limits.length ? h("ul", { class: "br-limits", "aria-label": "What this check rests on" }, limits.map((l) => h("li", {}, l))) : null);
  }

  /* Under the diagram: the chosen branch's findings (the happy path also carries the ones about the whole flow), in
     plain words with their owners; the checker's own expression, when the sentence was written around it, and the
     trace sit behind "Details". Each opens in the panel. */
  function findings(key) {
    const d = data(key), o = current(key);
    if (!o) return null;
    const ix = [...o.findings, ...(o.id === "happy" ? d.flowWide : [])];
    const unchecked = o.marks.includes("not fully checked");
    if (!ix.length && !unchecked) return null;
    const title = E[key] ? E[key].title : key;
    return h("div", { class: "br-findings", "data-branches-findings": key },
      ix.map((i) => findingNote(d.findings[i], title, d.flowWide.includes(i))),
      unchecked ? h("p", { class: "br-unchecked" }, "The flow check stopped partway, so we can't say this branch works yet.") : null);
  }
  function findingNote(f, title, wide) {
    const head = wide ? "Problem with the whole flow" : "Problem";
    const owners = f.owners.length ? ` ${f.owners.length === 1 ? "Owner" : "Owners"}: ${f.owners.join(", ")}.` : "";
    const trace = f.trace.length ? h("ol", { class: "br-trace" }, f.trace.map((t) => h("li", {}, t))) : null;
    const note = Nodes.note({ diagram: `Flow ${title}, error cases`, name: `${head}: ${shorten(f.summary, 60)}`, kind: "Problem the flow check found",
      text: f.summary, facts: [["Owners", f.owners.join(", ") || "not named"], ...(f.trace.length ? [["How it happens", h("ol", { class: "br-trace" }, f.trace.map((t) => h("li", {}, t)))]] : []),
        ...(f.covered ? [["Accepted for now", `until ${isDate(f.covered) ? day(f.covered) : f.covered}`]] : [])],
      relates: f.items.filter((k) => ent(k)) });
    const open = Nodes.wire(h("button", { class: "linkish br-open", type: "button" }, "Open in the panel"), { label: `${head}: ${f.title}`, note });
    return h("div", { class: "br-finding " + f.severity },
      h("p", {}, h("b", {}, head + ":"), " ", f.summary + owners, " ", open),
      f.expression || trace ? h("details", { class: "br-details" }, h("summary", {}, "Details"), f.expression ? h("p", { class: "br-expr" }, f.expression) : null, trace) : null);
  }

  /* A branch picked from the panel rather than the Show menu. */
  function choose(key, id) { chosen[key] = id; keepInHash(key); }
  const say = (key) => { const d = data(key); return d && d.state === "drawn" ? countLine(d) : d ? d.note : null; };

  return { choose, say, picker, summary, findings, flowFor, hashPart, current, data, words };
})();
