/* Boot: the top bar, the master lamps, assets if the build carried any, the deep link, and the first view.
   Deep links: #map, #flows&open=FLO-002&step=2, #present=FLO-001&step=3, #asks&open=UNK-065, #map&q=paper%20order,
   #decisions&open=ADR-0002 (the old #garden still works), #map&lens=transit; add &still for screenshots (no transitions), &selftest to run the checks. */
$("#brand-title").textContent = D.title || "Vault";
/* The initiative's ID is a tag, not a name: it rides in the tooltip, and the line under the title says what date the plan is read at. */
$("#brand-sub").textContent = `Plan as of ${day(D.today)}`;
$("#brand-title").title = $("#brand-title").textContent; $("#brand-sub").title = `The plan as it stood on ${day(D.today)}`;  // both cut with an ellipsis when the sidebar is narrow
/* A copy opened a few days after it was built says so, quietly, above everything: when it was built. A fresh copy says
nothing, because a second date beside "Plan as of" with no reason only puzzles the reader (label sweep). The commit is
for whoever maintains the plan, so it rides in a data attribute, never in text or a tooltip a reader reads. */
const STALE_AFTER_DAYS = 3;  // a copy shared on Monday and read on Wednesday is still this week's plan
if (D.built) {
  const built = $("#built");
  const on = isDate(D.built.date) ? day(D.built.date) : D.built.date;
  built.textContent = `Built ${on}. Anything changed after that isn't here.`;
  if (D.built.commit) built.dataset.commit = D.built.commit;
  const age = isDate(D.built.date) ? (Date.now() - Date.parse(D.built.date)) / 86400000 : Infinity;
  built.hidden = age < STALE_AFTER_DAYS;
}
$("#brand").addEventListener("click", () => Nav.home());
if (STILL) document.documentElement.classList.add("still");

function renderMasters() {
  const box = $("#masters"), counts = Queue.counts();  // a question counts once however many things it holds
  // "need you" is shown as a number here and only here (label sweep: the same 21 showed four times on Home); overdue is
  // the part of it that is late. A lamp at zero is noise on every screen, so overdue and not-reviewed hide at zero.
  const need = Queue.needsYou(), count = (lv) => (lv === "caution" ? need.n : counts[lv] || 0);
  const QUANTITY = { warning: "overdue", caution: "needsYou", unexamined: "unreviewed" };
  const tip = (lv, n) => (lv === "caution" ? `${n ? Queue.needsYouParts() + ". " : "Nothing needs you. "}Click to see them, most urgent first.`
    : lv === "warning" ? `${plural(n, "question")} past the date ${n === 1 ? "it" : "they"} needed an answer by. Something goes red when a question blocking it misses its answer date.`
    : `${plural(n, "thing")} with something nobody has reviewed yet. Each turns gray once someone has.`);
  box.innerHTML = "";
  for (const [lv, word] of [["warning", "overdue"], ["caution", "need you"], ["unexamined", LIGHT.unexamined.word.toLowerCase()]]) {
    const n = count(lv);
    if (lv !== "caution" && !n) continue;
    box.append(h("button", { class: `master ${lv}${n ? " on" : ""}`, title: tip(lv, n), onclick: () => { if (App.section !== "home") Nav.home(); go("lights", { reset: true }); } },
      h("b", { "data-quantity": QUANTITY[lv], "data-n": n }, n), h("span", {}, word)));
  }
}
/* The things set once and left: the theme, in one gear at the far right (the sound button and the Animation switch are gone). */
$("#settings").append(Menus.menu({ id: "settings", kind: "icon", glyph: "gear", label: "Settings: theme", align: "right",
  items: () => [{ heading: "Theme" }, ...Theme.LIST.map((t) => ({ id: t.id, label: t.label, say: t.say, checked: Theme.id === t.id, run: () => Theme.set(t.id) }))] }));
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
if (HASH.get("from") && ent(HASH.get("from"))) Nav.trace(HASH.get("from"));
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
  if (typeof SelfTest === "undefined") { console.warn("[selftest] this page was built without its checks; rebuild with vela explore --selftest"); document.body.setAttribute("data-selftest", "SELFTEST FAIL: this page was built without its checks (vela explore --selftest)"); }
  else setTimeout(() => SelfTest.run(), 60);
}
