/* Boot: the top bar, the master lamps, assets if the build carried any, the deep link, and the first view.
   Deep links: #map, #flows&open=FLO-002&step=2, #present=FLO-001&step=3, #asks&open=UNK-065, #map&q=paper%20order,
   #garden&open=ADR-0002, #map&lens=transit; add &still for screenshots (no transitions), &selftest to run the checks. */
$("#brand-title").textContent = D.title || "Vault";
$("#brand-sub").textContent = `${D.initiative} · as of ${day(D.today)}`;
$("#brand").addEventListener("click", () => Nav.home());
if (STILL) document.documentElement.classList.add("still");

function renderMasters() {
  const lit = litSubjects(), box = $("#masters");
  const count = (lv) => lit.filter((x) => x.light.level === lv).length + D.above.filter((a) => ASK[a.unknown] && ASK[a.unknown].light.level === lv).length;
  box.innerHTML = "";
  for (const [lv, word] of [["warning", "overdue"], ["caution", "need you"], ["unexamined", "unexamined"]]) {
    const n = count(lv);
    if (lv === "unexamined" && !n) continue;
    box.append(h("button", { class: `master ${lv}${n ? " on" : ""}`, title: `${n} ${LIGHT[lv].word.toLowerCase()}: ${LIGHT[lv].say}`, onclick: () => { if (App.section !== "home") Nav.home(); go("lights", { reset: true }); } },
      h("b", {}, n), h("span", {}, word)));
  }
}
renderMasters();

const open = HASH.get("open");
// #home, #role=qa and #s=<section> are the sidebar's (nav.js); the old view links (#map, #flows&open=...) still work.
if (!Nav.boot()) {
  if (open && ent(open)) { App.trail = [open]; App.focus = open; }
  if (App.view === "flows" && open && FLOW[open]) { Flows.st.key = open; Flows.st.cur = HASH.has("step") ? +HASH.get("step") - 1 : -1; }
  if (App.view === "garden" && open) Garden.showFor(open);
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
if (HASH.get("q")) { $("#q").value = HASH.get("q"); $("#q").focus(); $("#q").dispatchEvent(new Event("input")); }
if (HASH.get("present") && FLOW[HASH.get("present")]) Flows.present(HASH.get("present"), (+HASH.get("step") || 1) - 1);
if (HASH.has("rehearse") && FLOW[HASH.get("rehearse")]) Rehearse.open(HASH.get("rehearse"));
// #flows&clip records the open flow's clip in the browser and writes the outcome to <body data-clip>, for checks.
if (HASH.has("clip") && App.view === "flows") {
  window.__selftestClip = true;
  Flows.saveClip().then(() => document.body.setAttribute("data-clip", JSON.stringify(window.__clipResult || { ok: false })));
}
else if (HASH.has("selftest")) setTimeout(() => SelfTest.run(), 60);
