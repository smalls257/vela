/* ------------------------------------------------------------ Needs you (needs.js, viewer.js), driven as a person would:
   every role overview opens with the block; the block, the "N for you" badge and Grills waiting ("Mine") agree for each
   person because they all ask Viewer; the first five lines show and "N more" opens the rest; a vault with nothing for
   the viewer says so in one line and has no badge; nobody viewing is never called "you"; a line opens its item in the
   panel; the badge jumps to the block; the What's waiting page, its sidebar entry and its "waiting" badge are gone.
   Seven made-up lines for a made-up person are added for the length of the checks, so the five-line cut is exercised
   in every vault, and they are taken away again. A block of its own, so it merges apart from the others. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const click = (el) => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  const refs = () => $$("#needs-you .ny-line").map((b) => b.dataset.ref + ":" + b.dataset.kind);
  const badgeN = () => { const b = $("#for-you-badge b"); return b ? +b.textContent : 0; };
  const FAKE = "@selftest-person", EMPTY = "@selftest-nobody";

  async function needs(ok) {
    const lines = D.needs.lines, was = lines.length, apps = D.map.apps.map((a) => a.key);
    // 1. the data arrives most urgent first: tiers never go back
    const tiers = lines.map((l) => l.tier);
    ok(tiers.every((t, i) => i === 0 || t >= tiers[i - 1]), `needs you: ${was} lines in the data, most urgent tier first`, `needs you: the tiers go back: ${tiers.join(",")}`);

    // 2. every role overview opens with the block, whoever is viewing
    Viewer.set(EMPTY);
    const bad = [];
    for (const [id] of Roles.ROLES) {
      Nav.role(id); await tick();
      const door = $(".door"), kids = door ? [...door.children].map((c) => c.id || c.className.split(" ")[0]) : [];
      if (!door || kids[1] !== "needs-you") bad.push(`${id}: ${kids.join(",")}`);
    }
    ok(!bad.length, `needs you: all ${Roles.ROLES.length} role overviews open with Needs you, right under their heading`, `needs you: ${bad.join(" | ")}`);

    // 3. made-up lines for a made-up person: five show, the rest sit behind "N more"
    if (apps.length) {
      for (let i = 0; i < 7; i++) lines.push({ kind: "handed", key: apps[i % apps.length], for: [FAKE], words: "", date: D.today, standing: "new", days: 0, tier: 3 });
      Viewer.set(FAKE); Nav.role("exec"); await tick();
      const shown = refs().length, more = $("#needs-you .ny-more");
      ok(shown === Needs.SHOWN && !!more && /^2 more$/.test(more.textContent) && badgeN() === 7 && $("#needs-you").dataset.n === "7",
        "needs you: seven lines show five, \"2 more\" is behind a link and the badge says 7", `needs you: ${shown} lines, more "${more && more.textContent}", badge ${badgeN()}`);
      click(more); await tick();
      ok(!/null|undefined/.test($("#needs-you").textContent), "needs you: the block has no stray null or undefined text", `needs you: "${$("#needs-you").textContent}"`);
      ok(refs().length === 7 && /^Show the first 5$/.test($("#needs-you .ny-more").textContent), "needs you: \"2 more\" opens the other two, and the link folds them back", `needs you: ${refs().length} lines after More`);
      click($("#needs-you .ny-more")); await tick();
      ok(refs().length === Needs.SHOWN, "needs you: Show the first 5 folds them back", `needs you: ${refs().length} lines after folding`);

      // 4. a line opens its item in the right-hand panel
      const first = $("#needs-you .ny-line");
      click(first); await tick();
      ok(App.focus === first.dataset.ref && !!$("#panel-body") && $("#panel").textContent.length > 0, `needs you: a line opens ${titleOf(first.dataset.ref)} in the panel`, `needs you: focus is ${App.focus}`);

      // 5. the badge jumps to the block, from any page
      Nav.open("goals"); await tick();
      click($("#for-you-badge")); await tick();
      ok(App.view === "role" && document.activeElement === $("#needs-you"), "needs you: the \"7 for you\" badge, clicked from another page, lands on the viewer's overview with Needs you focused", `needs you: view ${App.view}, focus ${document.activeElement && document.activeElement.id}`);
    }

    // 5b. a late question reads late, one due soon reads soon, with the ask-by date; it holds the question's own words
    const open = Object.keys(ASK).find((id) => isOpen(ASK[id]));
    if (open) {
      lines.unshift({ kind: "question", key: open, for: [FAKE], words: "", date: "2000-01-01", standing: "late", days: -9, tier: 0 });
      Viewer.set(FAKE); Nav.role("qa"); await tick();
      const line = $("#needs-you .ny-line[data-kind=question]"), when = line && $(".ny-when", line);
      ok(!!line && when.classList.contains("late") && when.textContent === "due " + day("2000-01-01") && $(".ny-t", line).textContent === ASK[open].question && /^You were asked/.test($(".ny-m", line).textContent),
        "needs you: a late question says \"due\" and its date in red, shows the question itself and says you were asked", `needs you: late line "${line && line.textContent}"`);
      lines.shift();
    }

    // 6. one viewer for the block, the badge, Grills waiting and the question filter
    const people = [...new Set(lines.flatMap((l) => l.for).concat(Grills.rows.flatMap((r) => r.owner)))].filter((p) => p !== FAKE);
    const disagree = [];
    for (const p of people) {
      Viewer.set(p); Nav.role("mgr"); await tick();
      const label = personName(p).toLowerCase();
      const want = lines.filter((l) => l.for.some((x) => x.toLowerCase() === p.toLowerCase()) || (l.named && l.named === label)).length; 
      const mine = Grills.rows.filter((r) => r.owner.some((o) => o.toLowerCase() === p.toLowerCase())).length;
      const blockN = +$("#needs-you").dataset.n;
      if (blockN !== want || badgeN() !== blockN || Needs.count() !== blockN || Grills.count() !== mine || Grills.viewerHandles().join() !== Viewer.viewer().handles.join() || !Viewer.isYou(p)) {
        disagree.push(`${p}: block ${blockN}, want ${want}, badge ${badgeN()}, grills ${Grills.count()} want ${mine}`);
      }
    }
    ok(!disagree.length, `needs you: for each of ${people.length} people the block, the badge, Grills waiting and the viewer give the same answer`, `needs you: ${disagree.join(" | ")}`);

    // 7. nothing for the viewer: one line, no badge, the next date when there is one
    Viewer.set(EMPTY); Nav.role("exec"); await tick();
    const quiet = $("#needs-you .ny-quiet");
    ok(!refs().length && !$("#for-you-badge") && !!quiet && /^Nothing needs you right now\./.test(quiet.textContent) && $("#needs-you").classList.contains("empty"),
      "needs you: with nothing for the viewer it is one line, \"Nothing needs you right now.\", and there is no badge", `needs you: "${quiet && quiet.textContent}", badge ${!!$("#for-you-badge")}`);
    const row = { key: "UNK-SELFTEST", for: [EMPTY], words: "", date: "2999-01-02", askedName: "Identity lead", askedKey: "@identity-lead" };
    D.needs.dates.push(row); Nav.role("exec"); await tick();
    ok(/The next date on your side is Identity lead's answer, due Jan 2\.$/.test($("#needs-you .ny-quiet").textContent), "needs you: with a date on their side the empty line names it", `needs you: "${$("#needs-you .ny-quiet").textContent}"`);
    D.needs.dates.splice(D.needs.dates.indexOf(row), 1);

    // 8. nobody viewing: never "you", no badge
    Viewer.set(Viewer.EVERYONE); Nav.role("exec"); await tick();
    ok(!$("#for-you-badge") && /Pick who is viewing/.test($("#needs-you").textContent) && !/\byou\b|\byour\b/i.test($("#needs-you").textContent.replace("Pick who is viewing", "")),
      "needs you: with nobody viewing the block says how to pick someone and does not say \"you\"", `needs you: "${$("#needs-you").textContent}"`);

    // 9. the What's waiting page, its sidebar entry and its "waiting" badge are gone
    Viewer.set(""); Nav.home(); await tick();
    ok(!$$("#side .side-label").some((x) => x.textContent === "What's waiting") && !$(".q-card") && !$$("#masters .master").some((m) => m.textContent.includes("waiting")),
      "needs you: no What's waiting in the sidebar, no queue card on the map, no \"waiting\" badge in the top bar", "needs you: What's waiting is still there");
    Nav.open("goals"); go("lights", { reset: true }); await tick();
    const wide = $$("#for-you-badge, #grills-badge").length;
    ok(!/What's waiting|\d+ waiting/.test($("#panel").textContent + $("#side").textContent + $("#masters").textContent) && !$(".dp-tabs") && wide === (Needs.count() ? 1 : 0) && !$("#grills-badge"),
      "needs you: no What's waiting title, tab or count in the panel, sidebar or top bar, and the one badge is \"for you\" (no separate grills badge)", `needs you: panel "${$("#panel").textContent.slice(0, 80)}", badges ${wide}`);

    lines.length = was; Viewer.set(""); Nav.home(); go("lights", { reset: true });
  }

  SelfTest.run = async () => {
    const report = await base(), out0 = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { out0.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + out0[out0.length - 1]); };
    try { await needs(ok); } catch (e) { out0.push(`FAIL the needs-you check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) out0.push("FAIL JS ERRORS in the needs-you checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(out0), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
