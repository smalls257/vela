/* Error cases on the Flows view (design 19, decision D8). A flow whose checked sequence diagram has alt branches shows
   its happy path by default, and one picker above the drawing swaps in one branch at a time: "Happy path" first, then
   each answer a call can give, grouped by the call it branches at. An option cannot hold an icon, so each says the
   flow check's word on it in its label ("finding", "not fully checked"); nothing is ever shown as passed unless the
   check ran to the end. The chosen branch rides in the address (#flows&open=FLO&branch=CON-004.timeout).
   Everything drawn comes from branches_data.py, which reads the diagram through the flow checker's own readers;
   nothing here parses mermaid. Every drawn part opens the panel (Nodes.wire). */
const Branches = (() => {
  const LW = 180, RH = 30, TOP = 44;
  const chosen = {}, seen = {};  // flow key -> option id; and the branch the address last named
  const { ln, bx } = Legend;
  const def = (id, parts, text) => Legend.define(id, parts, text);
  def("br.lane", [ln({ stroke: "rule-3", w: 1, dash: "2 4" })], "Dotted line down a column: that app's or party's lifeline");
  def("br.call", [ln({ stroke: "ink-3", w: 1.6, head: "fill" })], "Solid arrow: a call over a contract");
  def("br.reply", [ln({ stroke: "ink-3", w: 1.6, head: "fill", dash: "4 3" })], "Dashed arrow: the answer coming back");
  def("br.event", [ln({ stroke: "ink-3", w: 1.6, head: "open" })], "Open arrow: an event, sent and not waited on");
  def("br.note", [bx({ fill: "note-text", stroke: "note-text", w: 0.8, opacity: 0.6, y: 4, height: 8, rx: 2 })], "Tinted band: a step inside one app, such as a state it sets");
  def("br.end", [bx({ stroke: "ink-2", w: 1.4, y: 4, height: 8, rx: 4 })], "Outlined band: where the journey ends");
  def("br.timeout", [bx({ stroke: "warning", w: 1.4, dash: "3 2", y: 4, height: 8, rx: 2 })], "Dashed red band: no answer in time, or giving up");
  def("br.alt", [ln({ stroke: "caution", w: 2.6, head: "fill" })], "Amber: differs from the happy path, this branch's own steps");
  def("br.click", [bx({ stroke: "ink-3", w: 1.2, rx: 4 })], "Click any box or step: it opens in the panel");
  const PROBES = { "br.lane": ".br-lane", "br.call": ".br-msg.call", "br.reply": ".br-msg.reply", "br.event": ".br-msg.event",
    "br.note": ".br-band.plain", "br.end": ".br-band.end", "br.timeout": ".br-band.timeout", "br.alt": ".br-step.alt", "br.click": ".br-step, .br-party" };

  const data = (key) => (D.branches || {})[key];
  const options = (d) => [d.happy, ...d.groups.flatMap((g) => g.options)];
  function current(key) {
    const d = data(key);
    if (!d || d.state !== "drawn") return null;
    const named = HASH.get("branch"), linked = named && (HASH.get("open") || Flows.st.key) === key && options(d).some((o) => o.id === named) ? named : null;  // a pasted link or Back brings its own branch
    if (linked && linked !== seen[key]) { chosen[key] = linked; seen[key] = linked; }
    if (!(key in chosen)) chosen[key] = "happy";
    return options(d).find((o) => o.id === chosen[key] && o.drawn !== false) || d.happy;
  }
  /* What Flows.select adds to the address, so the chosen branch survives a step change and a reload. */
  const hashPart = (key) => { const o = current(key); return o && o.id !== "happy" ? `&branch=${encodeURIComponent(o.id)}` : ""; };
  function keepInHash(key) {
    const kept = (location.hash || "#").slice(1).split("&").filter((p) => p && !p.startsWith("branch="));
    history.replaceState(null, "", "#" + kept.join("&") + hashPart(key));
  }
  const words = (o) => o.label + (o.marks.length ? ` (${o.marks.join(", ")})` : "");

  /* "6 ways this flow can go: the happy path and 5 branches. 1 has a finding, and 1 wasn't fully checked." */
  function countLine(d) {
    const n = d.counts.branches, f = d.counts.withFindings, gap = d.counts.notDrawn, unchecked = d.counts.notChecked;
    const said = [f ? `${f} ${f === 1 ? "has" : "have"} a finding` : "None has a finding", unchecked ? `${unchecked} ${unchecked === 1 ? "wasn't" : "weren't"} fully checked` : "",
      gap ? `${gap} ${gap === 1 ? "answer isn't" : "answers aren't"} drawn at all` : ""].filter(Boolean);
    const tail = !unchecked && d.check.status === "passes" ? " The flow check passes." : "";
    return `${n + 1} ways this flow can go: the happy path and ${plural(n, "branch", "branches")}. ${said.length > 1 ? said.slice(0, -1).join(", ") + ", and " + said[said.length - 1].replace(/^N/, "n") : said[0]}.${tail}`;
  }

  /* The section under the played flow. A flow with nothing to branch on gets one line and no drawing. */
  function section(key) {
    const d = data(key);
    if (!d) return null;
    if (d.state !== "drawn") return h("p", { class: "br-note", "data-branches": key }, d.note);
    const box = h("section", { class: "br", "data-branches": key, "aria-label": "Error cases" });
    const pick = h("select", { class: "br-pick", id: `br-pick-${key}` },
      h("option", { value: "happy", selected: current(key).id === "happy" ? "" : null }, words(d.happy)),
      d.groups.map((g) => h("optgroup", { label: g.label }, g.options.map((o) => h("option", { value: o.id, disabled: o.drawn ? null : "", selected: current(key).id === o.id ? "" : null }, words(o))))));
    pick.value = current(key).id;
    const body = h("div", { class: "br-body" });
    pick.addEventListener("change", () => { chosen[key] = pick.value; keepInHash(key); paint(key, body); });
    box.append(h("div", { class: "br-head" }, h("label", { for: pick.id }, "Show"), pick), h("p", { class: "br-sum" }, countLine(d)), body);
    paint(key, body);
    return box;
  }

  function paint(key, body) {
    const d = data(key), o = current(key), title = E[key] ? E[key].title : key;
    body.replaceChildren();
    const lg = Legend.open("branches", { root: () => body.querySelector(".br-scroll"), probes: PROBES, instance: key });
    const says = o.id === "happy" ? "Every call answers the way the flow hopes."
      : `${o.label}${o.status ? ` (${o.status})` : ""}${o.says ? `: ${o.says}` : ""}.`;
    const findings = [...o.findings, ...(o.id === "happy" ? d.flowWide : [])].map((i) => findingButton(d.findings[i], title, d.flowWide.includes(i)));
    body.append(...[h("p", { class: "br-says" }, says), h("div", { class: "br-scroll" }, drawing(d, o, title, lg)),
      findings.length ? h("div", { class: "br-findings" }, findings) : null,
      o.marks.includes("not fully checked") ? h("p", { class: "br-unchecked" }, "Not fully checked: the flow check stopped before the end, so this branch is not shown as passing.") : null,
      lg.el()].filter(Boolean));
    lg.paint();
  }

  function findingButton(f, title, wide) {
    const trace = f.trace.length ? h("ol", { class: "br-trace" }, f.trace.map((t) => h("li", {}, t))) : "none written";
    const name = `${f.severity === "warning" ? "Warning" : "Finding"}${wide ? ", about the whole flow" : ""}`;
    const note = Nodes.note({ diagram: `Flow ${title}, error cases`, name: `${f.title}: ${f.summary.slice(0, 60)}`, kind: f.severity === "warning" ? "Flow-check warning" : "Flow-check finding",
      text: f.summary, facts: [["Where", f.where], ["Owners", f.owners.join(", ") || "not named"], ["Trace", trace], ...(f.covered ? [["Covered", `by an override until ${f.covered}`]] : [])],
      relates: f.items.filter((k) => ent(k)) });
    const owners = f.owners.length ? ` ${f.owners.length === 1 ? "Owner" : "Owners"}: ${f.owners.join(", ")}.` : "";
    return Nodes.wire(h("button", { class: "br-finding " + f.severity, type: "button" }, h("b", {}, name + ":"), " ", f.summary + owners), { label: `${name}: ${f.title}`, note });
  }

  /* ------------------------------------------------------------ the drawing */
  let ctx2d = null;
  function fit(text, width, size) {
    ctx2d = ctx2d || document.createElement("canvas").getContext("2d");
    ctx2d.font = `${size}px ${getComputedStyle(document.documentElement).getPropertyValue("--ui") || "system-ui"}`;
    if (ctx2d.measureText(text).width <= width) return text;
    let cut = text;
    while (cut.length > 1 && ctx2d.measureText(cut + "…").width > width) cut = cut.slice(0, -1);
    return cut.trimEnd() + "…";
  }
  const partyKey = (p) => (p.key && ent(p.key) ? p.key : ((D.nodes || []).find((n) => n.title.toLowerCase() === p.title.toLowerCase()) || {}).key || "");

  function drawing(d, o, title, lg) {
    const parts = d.participants, steps = o.steps, diagram = `Flow ${title}, ${o.id === "happy" ? "happy path" : o.label}`;
    const W = Math.max(parts.length, 1) * LW, H = TOP + steps.length * RH + 14;
    const at = (id) => Math.max(0, parts.findIndex((p) => p.id === id)) * LW + LW / 2;
    const name = (id) => (parts.find((p) => p.id === id) || { title: id }).title;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: "br-svg", role: "img", "aria-label": `${title}: ${o.id === "happy" ? "the happy path" : o.label}` });
    const defs = s("defs", {}, svg);
    for (const [id, cls] of [["br-head", "br-head-fill"], ["br-head-alt", "br-head-fill alt"]]) {
      const m = s("marker", { id: `${id}-${o.id}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, defs);
      s("path", { d: "M0,0L10,5L0,10z", class: cls }, m);
    }
    parts.forEach((p) => {
      const cx = at(p.id), k = partyKey(p);
      s("line", { x1: cx, x2: cx, y1: TOP - 8, y2: H - 6, class: "br-lane" }, svg); lg.saw("br.lane"); lg.saw("br.click");
      const g = s("g", { class: "seq-head br-party" }, svg);
      s("rect", { x: cx - LW / 2 + 6, y: 6, width: LW - 12, height: 28, rx: 6 }, g);
      s("text", { x: cx, y: 24, "text-anchor": "middle" }, g).textContent = fit(p.title, LW - 22, 11.5);
      s("title", {}, g).textContent = p.title;
      const tells = steps.filter((x) => x.from === p.id || x.to === p.id || (x.over || []).includes(p.id)).slice(0, 6).map((x) => x.text);
      Nodes.wire(g, k ? { label: p.title, key: k } : { label: p.title, note: Nodes.note({ diagram, name: p.title, kind: "Who takes part", text: `${p.title} takes part in this flow. The vault has no page of its own for it.`, relates: tells }) });
    });
    steps.forEach((x, i) => {
      const y = TOP + i * RH + RH / 2, g = s("g", { class: "seq-step br-step" + (x.alt ? " alt" : ""), "data-i": i }, svg);
      if (x.kind === "note" || x.kind === "answer") {
        const xs = (x.over && x.over.length ? x.over : parts.map((p) => p.id)).map(at), x0 = Math.max(4, Math.min(...xs) - LW * 0.8), x1 = Math.min(W - 4, Math.max(...xs) + LW * 0.8);
        const band = x.tag === "end" ? "end" : x.tag === "timeout" ? "timeout" : "plain";
        s("rect", { x: x0, y: y - 10, width: x1 - x0, height: 20, rx: band === "end" ? 10 : 4, class: `br-band ${band}` }, g);
        lg.saw(band === "end" ? "br.end" : band === "timeout" ? "br.timeout" : "br.note");
        s("text", { x: (x0 + x1) / 2, y: y + 4, "text-anchor": "middle", class: "br-text" }, g).textContent = fit(x.text, x1 - x0 - 12, 11);
      } else {
        const x0 = at(x.from), x1 = at(x.to), kind = x.kind === "reply" ? "reply" : x.kind === "event" ? "event" : "call";
        lg.saw("br." + kind);
        const head = `url(#${x.alt ? "br-head-alt" : "br-head"}-${o.id})`;
        if (x0 === x1) {
          s("path", { d: `M${x0},${y - 6}h28v12h-26`, class: `br-msg ${kind}`, "marker-end": head }, g);
          s("text", { x: x0 + 34, y: y + 4, class: "br-text" }, g).textContent = fit(x.text, LW + 20, 11);
        } else {
          const dir = Math.sign(x1 - x0);
          s("line", { x1: x0, x2: x1 - dir * 2, y1: y + 6, y2: y + 6, class: `br-msg ${kind}`, "marker-end": head }, g);
          s("text", { x: (x0 + x1) / 2, y: y + 1, "text-anchor": "middle", class: "br-text" }, g).textContent = fit(x.text, Math.max(Math.abs(x1 - x0), LW * 1.3) - 12, 11);
        }
      }
      if (x.alt) lg.saw("br.alt");
      const said = describe(x, name);
      s("title", {}, g).textContent = `${i + 1}. ${said}`;
      Nodes.wire(g, stepTarget(x, i, said, diagram, parts));
    });
    return svg;
  }
  function describe(x, name) {
    if (x.kind === "note" || x.kind === "answer") return `${(x.over || []).map(name).join(" and ")}: ${x.text}`;
    return `${name(x.from)} ${x.kind === "reply" ? "answers" : x.kind === "event" ? "tells" : "asks"} ${name(x.to)}: ${x.text}`;
  }
  /* A call opens its contract, as a click on a chip would; any other step gets a short
     panel entry saying what it is and what it touches. */
  function stepTarget(x, i, said, diagram, parts) {
    const label = `Step ${i + 1}: ${said}`;
    if (x.item && ent(x.item)) return { label, key: x.item };
    const ends = [x.from, x.to, ...(x.over || [])].filter(Boolean).map((id) => parts.find((p) => p.id === id)).filter(Boolean);
    const kind = x.tag === "end" ? "Where the journey ends" : x.tag === "timeout" ? "No answer in time" : x.kind === "reply" ? "An answer" : "A step in the flow";
    return { label, note: Nodes.note({ diagram, name: `Step ${i + 1}: ${x.text}`, kind, text: said + (x.alt ? ". This step is on this branch only, off the happy path." : "."),
      relates: [...(x.key && ent(x.key) ? [x.key] : []), ...ends.map((p) => partyKey(p) || p.title)] }) };
  }

  return { section, hashPart, current, data, words };
})();
