/* ------------------------------------------------------------ Requirements section (reqview.js)
   The list and the focus draw D.requirements and nothing else: these checks hold the page to what the data says, and
   that every box and chip is a button that opens its own details in the panel. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 40));
  const R = D.requirements, ROWS = R.rows;
  const press = (el, k) => el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  const SIX = ["carried", "release", "epic", "designed", "stories", "open"];
  const names = (row) => row.checks.map((c) => c.k).join();

  /* The data: six checks in the order the work goes, a count that is the yeses, and filters that add up. */
  function reasons(ok) {
    const bad = [];
    for (const r of ROWS) {
      if (names(r) !== SIX.join()) bad.push(`${r.id}: checks ${names(r)}`);
      if (r.met !== r.checks.filter((c) => c.v === "yes").length) bad.push(`${r.id}: met ${r.met}`);
      if (r.checks.some((c) => !c.short || !c.long)) bad.push(`${r.id}: a check has no words`);
      if (!r.in.includes("all")) bad.push(`${r.id}: not in All`);
      if (r.questions.some((u) => !UNKNOWN[u])) bad.push(`${r.id}: a question the plan does not hold`);
    }
    for (const f of ["all", "gap", "held", "design"]) if (R.counts[f] !== ROWS.filter((r) => r.in.includes(f)).length) bad.push(`count ${f}`);
    ok(!bad.length, `requirements: ${ROWS.length} rows, six checks each in order, the count is the yeses, the filter counts add up`, `requirements: ${bad.slice(0, 4).join(" | ")}`);
    ok(/Built and tested/.test(R.notKnown) && !/\bmet\b/i.test(R.lede.replace(/\bmet so far\b/i, "")) , "requirements: the page says what the plan cannot know and never claims a requirement is met", `requirements: lede "${R.lede}"`);
  }

  async function listView(ok) {
    Nav.open("requirements"); await tick();
    const rows = $$("#main .rv-row");
    ok(App.view === "reqs" && rows.length === ROWS.length && rows.every((r) => r.tabIndex >= 0 && r.getAttribute("role") === "link"), `requirements list: one keyboard-reachable row for each of the ${ROWS.length} requirements`, `requirements list: ${rows.length} rows for ${ROWS.length} in ${App.view}`);
    const wrong = ROWS.filter((r) => { const tr = $(`#main .rv-row[data-req="${r.key}"]`); return !tr || $$(".rv-cell", tr).length < 5 || !$$(".rv-cell span", tr).every((s) => s.textContent.trim().length); });
    ok(!wrong.length, "requirements list: each row says its five checks in words and shows its open questions", `requirements list: rows without words ${wrong.map((r) => r.id).join(",")}`);
    const chips = $$("#main .rv-q");
    ok(chips.every((c) => c.tagName === "BUTTON" && c.tabIndex >= 0) && chips.length === ROWS.reduce((n, r) => n + r.questions.length, 0), `requirements list: ${chips.length} open-question chips, each a button`, "requirements list: a question chip is not a button");
    for (const [f] of [["all"], ["gap"], ["held"], ["design"]]) {
      $(`#main [data-filter="${f}"]`).click(); await tick();
      const n = $$("#main .rv-row").length;
      ok(n === R.counts[f] && $(`#main [data-filter="${f}"]`).getAttribute("aria-pressed") === "true", `requirements list: the ${f} filter shows ${n}, the count on its chip`, `requirements list: ${f} shows ${n}, its chip says ${R.counts[f]}`);
    }
    $('#main [data-filter="all"]').click(); await tick();
    for (const g of ["release", "app", "none", "capability"]) {
      const sel = $("#main .rv-controls select"); sel.value = g; sel.dispatchEvent(new Event("change", { bubbles: true })); await tick();
      const heads = $$("#main .rv-group").length, n = $$("#main .rv-row").length;
      ok(g === "app" ? n >= ROWS.length : n === ROWS.length && (g === "none" ? heads === 0 : heads >= 1), `requirements list: grouped by ${g}, ${heads} headings over ${n} rows`, `requirements list: group ${g} gave ${heads} headings and ${n} rows`);
    }
  }

  async function focusView(ok) {
    const r = ROWS.find((x) => x.checks.some((c) => c.v !== "yes")) || ROWS[0];
    Nav.open("requirements"); await tick();
    const row = $(`#main .rv-row[data-req="${r.key}"]`);
    press(row, "Enter"); await tick();
    const cols = $$("#main .rv-cols .rv-col");
    ok(App.view === "reqs" && Nav.st.child === r.key && cols.length === 6 && $$("h3", $("#main .rv-cols")).length >= 6, `requirements focus: Enter on ${r.name} draws six columns`, `requirements focus: ${cols.length} columns, child ${Nav.st.child}`);
    ok($("#panel-body h2") && $("#panel-body h2").textContent === r.name && $$("#panel-body .rv-checks li").length === 7, "requirements focus: the panel opens the requirement with the six checks and Decided", `requirements focus: panel says ${$("#panel-body h2") && $("#panel-body h2").textContent}`);
    const hero = $("#main .rv-hero");
    ok(!!hero && hero.textContent.includes(`${r.met} of 6`) && $$(".rv-seg", hero).length === 6, "requirements focus: the hero says how many of six checks are met, with a segment for each", "requirements focus: hero is wrong");
    const gaps = r.designs.filter((d) => !d.designed).length, drawn = $$(".rv-col:nth-child(5) .rv-node.gap", $("#main .rv-cols")).length;
    ok(drawn === (r.apps.length ? gaps : 1), `requirements focus: ${drawn} red dashed box${drawn === 1 ? "" : "es"} for the apps with no design`, `requirements focus: ${drawn} dashed design boxes, the data has ${gaps}`);
    const boxes = $$("#main .rv-cols .rv-main, #main .rv-cols .rv-comp"), loose = boxes.filter((b) => b.tagName !== "BUTTON" || b.tabIndex < 0 || !b.dataset.key);
    ok(boxes.length >= 6 && !loose.length, `requirements focus: all ${boxes.length} boxes and chips are buttons the keyboard reaches`, `requirements focus: ${loose.length} are not`);
    const target = $$("#main .rv-cols .rv-main").find((b) => ent(b.dataset.key) && !isReq(b.dataset.key));
    if (target) {
      target.click(); await tick();
      ok(!!$("#panel-body h2") && $("#panel-body h2").textContent.includes(titleOf(target.dataset.key)), `requirements focus: clicking ${titleOf(target.dataset.key)} opens its own details in the panel`, `requirements focus: panel says ${$("#panel-body h2") && $("#panel-body h2").textContent}`);
      ok(target.classList.contains("picked"), "requirements focus: the picked box is marked", "requirements focus: the picked box is not marked");
    } else ok(true, "skip requirements focus: no box here has details of its own");
    function isReq(k) { return ReqView.isReq(k); }
    const q = $("#main .rv-cols ~ .rv-before, #main .rv-before");
    ok(r.checks.every((c) => c.v === "yes") ? !q : !!q && $$("li", q).length === r.checks.filter((c) => c.v !== "yes").length, "requirements focus: it lists what is missing, one line for each check not met", "requirements focus: the missing list is wrong");
    $('#main [data-rv="list"]').click(); await tick();
    ok(App.view === "reqs" && !Nav.st.child && $$("#main .rv-row").length === ROWS.length, "requirements focus: List returns to the list", "requirements focus: List did not return");
  }

  async function sidebar(ok) {
    const s = D.sections.find((x) => x.id === "requirements");
    ok(!!s && s.children.length === ROWS.length && !!$('#side [data-section="requirements"]'), "requirements: the sidebar has a Requirements entry with a child for each requirement", "requirements: no sidebar entry");
    Nav.home(); await tick();
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try {
      if (ROWS.length) { reasons(ok); await sidebar(ok); await listView(ok); await focusView(ok); } else ok(true, "skip requirements: no functional requirements in this vault");
    } catch (e) { lines.push(`FAIL the requirements check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the requirements checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
