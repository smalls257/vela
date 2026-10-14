/* Boot: the top bar, the master lamps, assets if the build carried any, the deep link, and the first view.
   Deep links: #map, #flows&open=FLO-002&step=2, #present=FLO-001&step=3, #asks&open=UNK-065, #map&q=paper%20order,
   #decisions&open=ADR-0002 (the old #garden still works), #map&lens=transit; add &still for screenshots (no transitions), &selftest to run the checks. */
$("#brand-title").textContent = D.title || "Vault";
/* The initiative's ID is a tag, not a name: it rides in the tooltip, and the line under the title says what date the plan is read at. */
$("#brand-sub").textContent = `Plan as of ${day(D.today)}`;
$("#brand-title").title = $("#brand-title").textContent; $("#brand-sub").title = `${D.initiative ? D.initiative + ": " : ""}the plan as it stood on ${day(D.today)}`;  // both cut with an ellipsis when the sidebar is narrow
/* A copy opened long after it was built says so, quietly, above everything: when it was built. The commit is for whoever
maintains the plan, so it rides in the tooltip rather than in the sentence every reader reads. */
if (D.built) {
  const built = $("#built");
  const on = isDate(D.built.date) ? `${day(D.built.date)} ${D.built.date.slice(0, 4)}` : D.built.date;
  built.textContent = `Built ${on}. If the plan has changed since then, this page won't show it.`;
  if (D.built.commit) built.title = `Built from commit ${D.built.commit}`;
  built.hidden = false;
}
$("#brand").addEventListener("click", () => Nav.home());
if (STILL) document.documentElement.classList.add("still");

function renderMasters() {
  const box = $("#masters"), counts = Queue.counts();  // a question counts once however many things it holds
  const need = Queue.needsYou(), count = (lv) => (lv === "caution" ? need.n : counts[lv] || 0);  // "need you" is the one count the side door and the panel give; overdue is the part of it that is late
  box.innerHTML = "";
  for (const [lv, word] of [["warning", "overdue"], ["caution", "need you"], ["unexamined", "not reviewed"]]) {
    const n = count(lv);
    if (lv === "unexamined" && !n) continue;
    box.append(h("button", { class: `master ${lv}${n ? " on" : ""}`, title: lv === "caution" ? `${Queue.needsYouSays()}. Something needs you when it is ${LIGHT[lv].say}.` : lv === "warning" ? `${n ? n + " overdue" : "Nothing overdue"}. Something is overdue when ${LIGHT[lv].say}.` : `${n} not reviewed: ${LIGHT[lv].say}.`, onclick: () => { if (App.section !== "home") Nav.home(); go("lights", { reset: true }); } },
      h("b", {}, n), h("span", {}, word)));
  }
}
renderMasters();
Drafts.badges();
Freshness.start();

const open = HASH.get("open");
// #home, #role=qa and #s=<section> are the sidebar's (nav.js); the old view links (#map, #flows&open=...) still work.
if (!Nav.boot()) {
  if (open && ent(open)) { App.trail = [open]; App.focus = open; }
  if (App.view === "flows" && open && FLOW[open]) { Flows.st.key = open; Flows.st.cur = HASH.has("step") ? +HASH.get("step") - 1 : -1; }
  if (App.view === "decisions" && open) Decisions.showFor(open);
  Panel.render();
  rerender();
  Nav.syncHash();
  if (open && viewDef(App.view).highlight) viewDef(App.view).highlight(open);
} else if (open && App.section === "flows" && HASH.has("step") && FLOW[open]) Flows.select(open, +HASH.get("step") - 1);
if (HASH.get("from") && ent(HASH.get("from"))) (FX.motion === "ripple" ? Nav.ripple : Nav.trace)(HASH.get("from"));
// Assets arrive after the first paint; redraw with them and keep whatever the view was showing in focus.
Assets.load().then(() => {
  if (!Assets.R) return;
  rerender(); Panel.render();
  const v = viewDef(App.view);
  if (App.focus && v.highlight) v.highlight(App.focus);
});
Ask.ready = Ask.detect().then(Layout.boot);  // a file asks nothing of the network; a page served from this machine asks /health once, then for the layout the helper holds
if (HASH.get("q")) { $("#q").value = HASH.get("q"); $("#q").focus(); $("#q").dispatchEvent(new Event("input")); }
if (HASH.get("present") && FLOW[HASH.get("present")]) Flows.present(HASH.get("present"), (+HASH.get("step") || 1) - 1);
if (HASH.has("rehearse") && FLOW[HASH.get("rehearse")]) Rehearse.open(HASH.get("rehearse"));
// #flows&clip records the open flow's clip in the browser and writes the outcome to <body data-clip>, for checks.
if (HASH.has("clip") && App.view === "flows") {
  window.__selftestClip = true;
  Flows.saveClip().then(() => document.body.setAttribute("data-clip", JSON.stringify(window.__clipResult || { ok: false })));
}
else if (HASH.has("selftest")) {
  if (typeof SelfTest === "undefined") { console.warn("[selftest] this page was built without its checks; rebuild with planner explore --selftest"); document.body.setAttribute("data-selftest", "SELFTEST FAIL: this page was built without its checks (planner explore --selftest)"); }
  else setTimeout(() => SelfTest.run(), 60);
}
