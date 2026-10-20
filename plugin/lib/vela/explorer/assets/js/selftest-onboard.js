/* ------------------------------------------------------------ Getting up to speed (onboard.js)
   For every role: the path lists exactly the modules D.onboard says (the five core parts first, the lead's hidden ones
   absent, a person's own path in place of the standard one when the build carried it), the lead's note shows, and a
   module the plan is silent on says so. Every "↗" link and every item's link, in every module, follows its real route
   and lands on the view it names with the thing it names in the panel (no dead link, no link to the wrong item). Every
   item opens the panel by click and by Enter, in cards and in the diagram. Progress is kept per role and restored, Next
   ticks and Start over clears, the depth switch changes how much shows, the diagram's key matches what is drawn, and
   no label is cut or sticks out. */
(() => {
  const base = SelfTest.run, frames = () => Promise.resolve();
  const O = D.onboard, roles = O.audiences.map((a) => a.id), allKeys = Object.keys(O.modules);
  const heading = () => { const b = $("#panel-body"), head = b && $(".p-head h2", b); if (!head) return ""; const c = head.cloneNode(true); c.querySelectorAll("svg").forEach((x) => x.remove()); return c.textContent.trim(); };  // an app's icon carries its own title text
  const press = (el, how) => (how === "Enter" ? el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })) : el.click());
  const listed = () => $$(".onb-mod").map((b) => b.dataset.module);
  const sameList = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
  const wanted = (role) => (O.mine && O.mine.audience === role ? O.mine.keys : O.paths[role].modules);
  /* Follows a route as a pasted link would: the address's parameters are read the way Nav.followHash reads them. The history
     API is left alone because a browser stops honoring it after about 200 calls in 10 seconds, and the earlier checks use many. */
  function follow(href) {
    for (const k of [...HASH.keys()]) HASH.delete(k);
    new URLSearchParams(href.slice(1)).forEach((v, k) => HASH.append(k, v));
    Flows.closePresent();
    if (!Nav.boot()) { const open = HASH.get("open"); if (open && ent(open)) { App.trail = [open]; App.focus = open; } Panel.render(); rerender(); }
  }
  const links = () => {
    const out = [];
    for (const k of allKeys) { const m = O.modules[k]; for (const l of m.links) out.push([k, l.label, l.href]); for (const it of m.items) if (it.href) out.push([k, it.label, it.href]); }
    return out;
  };
  /* Where a route must land: its section or view, and the thing it opens in the panel. "" when it does. */
  function missed(href) {
    const p = new URLSearchParams(href.slice(1)), open = p.get("open"), s = p.get("s");
    if (open) {
      if (!ent(open)) return `${open} is not in the page`;
      if (App.focus !== open) return `opened ${App.focus || "nothing"} where ${open} was named`;
      if (heading() !== titleOf(open)) return `the panel shows "${heading()}", not "${titleOf(open)}"`;
    }
    if (s) return App.section === s ? "" : `landed in ${App.section}, wanted ${s}`;
    if (p.has("asks")) return App.view === "asks" ? "" : `landed on ${App.view}, wanted the questions`;
    if (p.has("map")) return App.view === "map" ? "" : `landed on ${App.view}, wanted the map`;
    if (p.has("home")) return App.section === "home" ? "" : `landed in ${App.section}, wanted home`;
    if (p.has("role")) return App.section === "role:" + p.get("role") ? "" : `landed in ${App.section}, wanted the ${p.get("role")} door`;
    return `no rule for ${href}`;
  }
  async function paths(ok) {
    const bad = [];
    for (const role of roles) {
      Nav.onboard(role); await frames();
      const got = listed(), want = wanted(role);
      if (!sameList(got, want)) bad.push(`${role}: the page lists ${got.join(", ")} but the data says ${want.join(", ")}`);
      const hidden = O.paths[role].hidden;
      if (!mine(role) && hidden.some((name) => $$(".onb-mod .onb-mt").some((el) => el.firstChild.textContent === name))) bad.push(`${role}: a module the lead hid is on the path`);
      const note = O.paths[role].note, shown = $(".onb-lead");
      if (!mine(role) && note && (!shown || !shown.textContent.includes(note))) bad.push(`${role}: the lead's note is not shown`);
      if (!mine(role) && !note && shown) bad.push(`${role}: a lead's note is shown that nobody wrote`);
      if (!mine(role) && !sameList(want.slice(0, 5).map((k) => k.split("@")[0]), ["goal", "approach", "standing", "fit", "people"])) bad.push(`${role}: the five core parts are not first, in order`);
    }
    ok(!bad.length, `onboarding: each of the ${roles.length} roles lists its path as the data says, the five core parts first, the lead's hidden modules left out and the lead's note shown`, `onboarding paths: ${bad.slice(0, 6).join(" | ")}`);
    if (O.mine) {
      Nav.onboard(O.mine.audience); await frames();
      const own = sameList(listed(), O.mine.keys) && $(".onb-path h2").textContent === "Your path";
      ok(own, `onboarding: ${O.mine.handle}'s own path is what the ${O.mine.audience} role shows, headed "Your path"`, `onboarding: the personal path is not shown (${listed().join(", ")})`);
      const toggle = $$(".onb-path button").find((b) => b.textContent === "Show the standard path");
      if (toggle) { toggle.click(); await frames(); ok(sameList(listed(), O.paths[O.mine.audience].modules) && $(".onb-path h2").textContent === "The standard path", "onboarding: Show the standard path brings the standard path back", "onboarding: the toggle did not bring the standard path back"); $$(".onb-path button").find((b) => b.textContent === "Show my path").click(); await frames(); }
    } else ok($(".onb-path h2").textContent === "The standard path", "onboarding: with no path of their own, a person sees the standard path", "onboarding: the heading is not the standard path's");
  }
  const mine = (role) => !!O.mine && O.mine.audience === role && $(".onb-path h2") && $(".onb-path h2").textContent === "Your path";
  async function silent(ok) {
    const quiet = allKeys.filter((k) => O.modules[k].notRecorded);
    if (!quiet.length) { ok(true, "onboarding: every module has something to show in this plan (none is silent)"); return; }
    const bad = [];
    for (const role of roles) {
      const ks = wanted(role), k = ks.find((x) => O.modules[x].notRecorded);
      if (!k) continue;
      Nav.onboard(role, k); await frames();
      const m = O.modules[k];
      const said = $(".onb-stage").textContent;  // the gist says it whatever the depth; the view always names who to ask
      if (!said.includes("Not recorded yet") || !said.includes(m.notRecorded.ask)) bad.push(`${role}/${m.title}: it does not say "Not recorded yet" and who to ask`);
      if (!$(".onb-view .empty-state")) bad.push(`${role}/${m.title}: the view is empty with no note`);
    }
    ok(!bad.length, `onboarding: ${quiet.length} modules the plan is silent on say "Not recorded yet" and who to ask, and stay on the path`, `onboarding silent modules: ${bad.slice(0, 5).join(" | ")}`);
  }
  /* A kept term (slice, tracer) is defined where a person first meets it on their path, and only there. */
  /* Who the reader is: the plan's record for the handle wins, then the person's own choice, then the role door; none is "". */
  async function whoAmI(ok) {
    const was = [O.me, O.roles], bad = [], door = "exec";
    const cases = [["record beats choice and door", { handle: "zed", role: "eng" }, { zed: "qa" }, "qa", "record"], ["choice beats the door", { handle: "zed", role: "eng" }, {}, "eng", "choice"],
      ["the door when no one is named", null, {}, door, "door"], ["a role the page does not have is not used", { handle: "zed", role: "nonsense" }, { zed: "nonsense" }, door, "door"]];
    try {
      for (const [what, me, record, role, source] of cases) {
        O.me = me; O.roles = record; Nav.role(door); await frames();
        const got = Onboard.myRole();
        if (got.role !== role || got.source !== source) bad.push(`${what}: ${got.role}/${got.source}, wanted ${role}/${source}`);
      }
      O.me = { handle: "zed", role: "mgr" }; O.roles = {}; Nav.home(); Settings.write(`onboard:${D.vaultId}:role`, "exec");
      const wanted = O.mine ? O.mine.audience : "mgr";  // a person's own page opens on their path's role; the shared copy on the best guess
      if (Onboard.defaultRole() !== wanted) bad.push(`the door in the sidebar opened as ${Onboard.defaultRole()}, wanted ${wanted}`);
    } finally { [O.me, O.roles] = was; Nav.home(); go("lights", { reset: true }); }
    ok(!bad.length, "onboarding: who the reader is comes from the plan's record first, then their own choice, then the role door", `onboarding who: ${bad.join(" | ")}`);
  }
  async function backToThePart(ok) {
    const role = roles[0], ks = Onboard.keys(role), key = ks[Math.min(2, ks.length - 1)];
    Nav.onboard(role, key, false); await frames();
    const left = Nav.where();
    Nav.home(); await frames();
    Nav.back(left); await frames();
    ok(Onboard.current() === key && App.section === "onboard:" + role, "onboarding: Back from somewhere else returns to the part the reader left, not the first unfinished one", `onboarding back: returned to ${Onboard.current()}, wanted ${key}`);
  }
  async function termsOnce(ok) {
    const bad = [];
    for (const role of roles) {
      const seen = new Set();
      for (const k of wanted(role)) {
        Nav.onboard(role, k); await frames();
        const shown = $$(".ob-term").map((p) => p.textContent), want = O.modules[k].terms.filter((t) => !seen.has(t)).map((t) => D.terms[t]);
        if (!sameList(shown, want)) bad.push(`${role}/${O.modules[k].title}: shows ${shown.length} definitions, wanted ${want.length}`);
        O.modules[k].terms.forEach((t) => seen.add(t));
      }
    }
    ok(!bad.length, "onboarding: a kept term is defined on its first use along each role's path and not again", `onboarding terms: ${bad.slice(0, 5).join(" | ")}`);
  }
  async function linksLand(ok) {
    const all = links(), bad = [], seen = new Set(), at = location.hash;
    for (const [k, label, href] of all) {
      if (seen.has(href)) continue;
      seen.add(href);
      Nav.home(); follow(href); await frames();
      const why = missed(href);
      if (why) bad.push(`"${label}" in ${O.modules[k].title} (${href}): ${why}`);
    }
    follow(at || "#map"); Nav.home(); go("lights", { reset: true });
    ok(!bad.length && seen.size > 0, `onboarding: all ${seen.size} different links in ${allKeys.length} modules land on the view they name, with what they open in the panel`, `onboarding links: ${bad.length} of ${seen.size} miss: ${bad.slice(0, 5).join(" | ")}`);
  }
  async function itemsOpen(ok) {
    const bad = [];
    for (const role of ["eng", "exec"].filter((r) => roles.includes(r))) for (const shape of ["cards", "diagram"]) {
      Onboard.st.shape = shape;
      for (const k of wanted(role).filter((x) => O.modules[x].items.length)) {
        Nav.onboard(role, k); await frames();
        const nodes = $$(".onb-view [data-node]").slice(0, 3);
        if (!nodes.length) bad.push(`${role}/${k}/${shape}: no item is a node`);
        for (const el of nodes) for (const how of ["click", "Enter"]) {
          go("lights", { reset: true }); const before = heading();
          press(el, how); await frames();
          if (!heading() || heading() === before) bad.push(`${how} on "${el.dataset.node}" in ${role}/${k}/${shape}`);
        }
      }
    }
    Onboard.st.shape = null;
    ok(!bad.length, "onboarding: the first items of every module open the panel by click and by Enter, as cards and as a diagram", `onboarding items: ${bad.slice(0, 5).join(" | ")}`);
  }
  /* A progress value the browser holds that is not what this page wrote (hand-edited, from an older page, a path that has
     since changed) is read as no progress, never as a break: the path still draws, and a stale key ticks nothing. */
  async function oddProgress(ok) {
    const role = roles[0], key = `onboard:${D.vaultId}:${O.mine ? O.mine.handle : "reader"}:${role}`, bad = [];
    for (const [what, value] of [["not JSON", "{oops"], ["wrong shape", '{"done":"goal"}'], ["a key no module has", '{"done":["no-such-module"]}'], ["null", "null"]]) {
      localStorage.setItem(key, value); Onboard.st.role = ""; Nav.onboard(role); await frames();
      if (!sameList(listed(), wanted(role))) bad.push(`${what}: the path did not draw`);
      if (+$(".onb-bar").getAttribute("aria-valuenow") !== 0) bad.push(`${what}: it counted progress that was not there`);
    }
    localStorage.removeItem(key); localStorage.removeItem(key + ".unreadable");
    ok(!bad.length, "onboarding: a progress value that is not JSON, the wrong shape or names a part that is gone is read as no progress and the path still draws", `onboarding odd progress: ${bad.join(" | ")}`);
  }
  async function progressAndDepth(ok) {
    const role = roles.includes("eng") ? "eng" : roles[0], ks = wanted(role), key = `onboard:${D.vaultId}:${O.mine ? O.mine.handle : "reader"}:${role}`;
    localStorage.removeItem(key); Nav.onboard(role); await frames();
    const next = () => $$(".onb-nav .btn").find((b) => b.textContent.startsWith("Next") || b.textContent === "Finish");
    const ticks = Math.min(2, ks.length), resting = ks[Math.min(ticks, ks.length - 1)];
    for (let i = 0; i < ticks; i++) { next().click(); await frames(); }
    const bar = () => +$(".onb-bar").getAttribute("aria-valuenow");
    const first = bar() === ticks && $$(".onb-mod.done").length === ticks && $(".onb-mod.on").dataset.module === resting;
    Nav.onboard(role); await frames();
    const kept = bar() === ticks && $(".onb-mod.on").dataset.module === (ticks < ks.length ? resting : ks[0]);
    $$(".onb-mod")[0].click(); await frames();
    const skipped = bar() === ticks && $(".onb-mod.on").dataset.module === ks[0];
    $$(".onb-path button").find((b) => b.textContent === "Start over").click(); await frames();
    const cleared = bar() === 0 && !$$(".onb-mod.done").length;
    ok(first && kept && skipped && cleared, `onboarding: Next ticks a part and moves on, progress is kept for the role and restored, a click in the list skips without ticking, Start over clears it`,
      `onboarding progress: after ${ticks} Nexts ${first}, restored ${kept}, skip ${skipped}, start over ${cleared}`);
    localStorage.removeItem(key);
    const big = ks.find((k) => O.modules[k].items.length > O.depths.normal.items) || ks.find((k) => O.modules[k].items.length > O.depths.gist.items);
    if (!big) { ok(true, "onboarding: no module has more items than the gist depth shows, so the depth switch has nothing to trim here"); return; }
    const count = async (d) => { st_depth(d); Nav.onboard(role, big); await frames(); return $$(".onb-view .ob-row, .onb-view .ob-cell").length; };
    const gist = await count("gist"), everything = await count("everything");
    const pars = async (d) => { st_depth(d); Nav.onboard(role, big); await frames(); return $$(".onb-explain > p").length; };
    ok(gist === O.depths.gist.items && everything === O.modules[big].items.length, `onboarding: the depth switch shows ${gist} items at "Just the gist" and all ${everything} at "Everything"`, `onboarding depth: gist showed ${gist} (wanted ${O.depths.gist.items}), everything ${everything} (wanted ${O.modules[big].items.length})`);
    st_depth(null);
  }
  const st_depth = (d) => { Onboard.st.depth = d; const k = `onboard:${D.vaultId}:${O_who()}:depth`; if (d) localStorage.setItem(k, d); else localStorage.removeItem(k); };
  const O_who = () => (D.onboard.mine ? D.onboard.mine.handle : "reader");
  /* A click on an item is the real Details of that kind of thing, the same ones its own page shows, never a generic summary:
     one section each kind must carry, and no code shown as text. Releases and people have no page of their own, so theirs are
     the shared Details builders'. Every kind the plan has an item for, across every role's path, is clicked. */
  const DETAILS = { unknown: ["Open question", "Who to ask", "It holds up"], app: ["App", "In these flows"], contract: ["Contract", "Who provides it, who calls it"],
    flow: ["Journey", "Steps"], slice: ["Slice", "Where it stands"], decision: ["Decision", "What was chosen"], owner: ["Who to ask", "Their open questions"], release: ["Release", "What it ships"] };
  const sections = () => $$("#panel-body h3").map((x) => x.firstChild.textContent.trim());
  async function itemKinds(ok) {
    const bad = [], seen = new Set(), asked = [];
    st_depth("everything");  // a long list shows its questions only past the first few items
    for (const role of roles) for (const k of wanted(role)) {
      Onboard.st.shape = "cards"; Nav.onboard(role, k); await frames();
      for (const el of $$(".onb-view [data-opens]")) {
        const key = el.dataset.opens, e = ent(key);
        if (!e) continue;
        const kind = decided(key) ? "decision" : e.kind, want = DETAILS[kind];
        if (!want || seen.has(kind + "|" + (kind === "owner" ? (D.asks.some((u) => u.ask.key === key.slice(6) && u.state === "open") ? "asked" : "quiet") : ""))) continue;
        seen.add(kind + "|" + (kind === "owner" ? (D.asks.some((u) => u.ask.key === key.slice(6) && u.state === "open") ? "asked" : "quiet") : ""));
        asked.push(kind);
        go("lights", { reset: true }); el.click(); await frames();
        const body = $("#panel-body"), text = body.textContent, got = sections();
        if (heading() !== (kind === "decision" ? decided(key).name : kind === "owner" ? PlanDetails.label(key) : titleOf(key))) bad.push(`${kind}: the panel shows "${heading()}"`);
        if (!$(".dp-trail", body) || !$(".dp-tabs", body)) bad.push(`${kind}: it is not the shared Details panel`);
        for (const sec of want.slice(1)) if (!got.includes(sec) && !(kind === "owner" && sec === "Their open questions" && !D.asks.some((u) => u.ask.key === key.slice(6)))) bad.push(`${kind}: no "${sec}" section (has ${got.join(", ")})`);
        if (kind === "unknown" && !$(".big-q", body)) bad.push("unknown: the question is not in plain words");
        if (kind === "unknown" && !$$(".dp-open-row", body).length && !$(".dp-open", body)) bad.push("unknown: nothing to Open");
        if (/\b(UNK|CAP|ADR|SLC|FLO|CON|EPC|APP)-\d/.test(text.replace(/CAP-\d+\.FR\d+/g, "")) && kind === "unknown") bad.push(`unknown: a code is shown as text`);
      }
    }
    Onboard.st.shape = null; go("lights", { reset: true });
    ok(!bad.length && asked.includes("unknown"), `onboarding: clicking an item opens its real Details (${[...new Set(asked)].join(", ")}), the same as on its own page`, `onboarding details: ${bad.slice(0, 5).join(" | ") || "no question item was clicked"}`);
    st_depth(null);
  }
  const decided = (k) => (k.startsWith("decision:") && typeof Decisions !== "undefined" ? Decisions.entries.find((x) => x.id === k.slice(9)) || null : null);
  async function keyAndFit(ok) {
    const keyBad = [], fitBad = [];
    const roleList = roles.filter((r) => ["eng", "exec", "mgr"].includes(r));
    for (const role of roleList) for (const shape of ["cards", "diagram"]) {
      Onboard.st.shape = shape;
      for (const k of wanted(role)) {
        Nav.onboard(role, k); await frames();
        if (shape === "diagram") for (const p of Legend.audit().filter((x) => x.startsWith("onboard"))) keyBad.push(`${role}/${k}: ${p}`);
        const root = $(".onb");
        for (const b of [...TextFit.textFits(root), ...TextFit.clippedText(root)]) fitBad.push(`${role}/${k}/${shape}: "${b.text}" ${b.why}`);
        if (document.documentElement.scrollWidth > innerWidth + 1) fitBad.push(`${role}/${k}/${shape}: the page scrolls sideways`);
      }
    }
    Onboard.st.shape = null;
    ok(!keyBad.length, "onboarding: in the diagram, every look drawn is in the key and every look in the key is drawn", `onboarding key: ${keyBad.slice(0, 4).join(" | ")}`);
    ok(!fitBad.length, "onboarding: in cards and in the diagram, every label fits and nothing makes the page scroll sideways", `onboarding fit: ${fitBad.slice(0, 5).join(" | ")}`);
  }
  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length, at = location.hash;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await paths(ok); await silent(ok); await whoAmI(ok); await backToThePart(ok); await termsOnce(ok); await linksLand(ok); await itemsOpen(ok); await itemKinds(ok); await progressAndDepth(ok); await oddProgress(ok); await keyAndFit(ok); } catch (e) { lines.push("FAIL the onboarding checks threw: " + e.message + " " + (e.stack || "").split("\n")[1]); }
    history.replaceState(null, "", at); Nav.home(); go("lights", { reset: true });
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the onboarding checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    console.log(lines.join("\n"));
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
