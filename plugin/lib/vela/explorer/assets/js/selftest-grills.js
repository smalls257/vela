/* ------------------------------------------------------------ Waiting for a decision (view-grills.js), driven as a person would:
   the three groups in their order, who is viewing and what each person sees (the chips, the sidebar
   count and the ready ones in Needs you must all give the same number), every filter, the "more belong to other owners" link, a card
   opening in the right-hand panel, the prompt for Claude and its Copy button, the batch in the order that unblocks the
   most, the small "Ready for a grill" line on an item's own details, and the keyboard reaching everything. A vault with
   no grill waiting has no Waiting for a decision entry, and these checks say so and stop. A block of its own after the details
   checks, so it merges apart from them. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const click = (el) => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  const key = (el, k) => el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  const cards = () => $$(".g-card");
  const shownIds = () => cards().map((c) => c.dataset.grill).sort().join(",");
  const idsOf = (list) => list.map((r) => r.id).sort().join(",");
  const head = () => { const h2 = $("#panel-body .p-head h2"); return h2 ? h2.textContent.trim() : ""; };
  // a requirement opens in its own focus view, which has its own sections, so a grill's panel is checked on another kind
  const isRequirement = (r) => (ent(r.key) || {}).kind === "requirement";
  const sections = () => $$("#panel-body .p-sec h3").map((x) => x.textContent.replace(/\s+\d+$/, "").trim());
  const nums = (sel) => $$(sel).map((x) => x.textContent.replace(/\D+/g, ""));
  const chipN = (scope) => { const c = $(`.g-scope[data-scope="${scope}"] .g-n`); return c ? +c.textContent : -1; };
  const IDLIKE = /\b(?:UNK|CAP|CON|EPC|APP|RUN|FLO|SLC|ADR|SRC)-\d|@[\w-]+|\^c\d/;

  async function grills(ok) {
    const rows = Grills.rows;
    if (!rows.length) { ok(!$$("#side .side-grills-door").length && !$("#grills-badge"), "grills: a vault with nothing waiting has no Waiting for a decision entry and no badge", "grills: an empty list still shows an entry"); return; }
    Nav.home(); Viewer.set(""); Grills.st.scope = "mine"; Grills.st.owner = ""; Grills.st.app = ""; Grills.st.holds = ""; Grills.st.readyOnly = false; Grills.st.batch = [];
    const everyone = () => { Grills.setViewer("*"); };

    // everyone: no person, so every grill shows, in the three groups' order
    Grills.open(); everyone(); await tick();
    const order = ["said-yes", "ready", "one-away"], seen = $$(".g-group").map((g) => g.dataset.group);
    ok(App.view === "grills" && seen.join() === order.filter((g) => rows.some((r) => r.group === g)).join() && cards().length === rows.length && shownIds() === idsOf(rows),
      `grills: with nobody viewing, all ${rows.length} grills show once, in the groups ${seen.join(", ")}`, `grills: groups ${seen.join(",")}, ${cards().length} cards for ${rows.length}; shown ${shownIds()}`);
    ok(["You already said yes", "Ready to decide", "One thing away"].some((t) => $$(".g-group h2").some((x) => x.textContent.startsWith(t))) && $$(".g-group h2").every((x) => ["You already said yes", "Ready to decide", "One thing away"].some((t) => x.textContent.startsWith(t))),
      "grills: the group headings say You already said yes, Ready to decide and One thing away", `grills: headings ${$$(".g-group h2").map((x) => x.textContent).join(" | ")}`);
    ok(!$(".g-scope") && /everyone's grills/.test($(".g-scope-note").textContent) && !$("#grills-badge") && $(".side-grills-door .side-n").textContent === String(rows.length),
      "grills: with nobody viewing there is no Mine chip, the sidebar counts every grill waiting, and the top bar has no grills badge (Needs you's \"for you\" is the one badge)", `grills: top-bar badge ${!!$("#grills-badge")}, sidebar "${($(".side-grills-door .side-n") || {}).textContent}"`);

    // each person sees their own, and the badge, the sidebar, the chips and the ready grills in Needs you all agree
    const people = Grills.rows.flatMap((r) => [...r.owner, ...r.join]).filter((p, i, all) => all.indexOf(p) === i);
    const lower = (t) => t.toLowerCase(), owns = (p) => rows.filter((r) => r.owner.some((o) => lower(o) === lower(p))), joins = (p) => rows.filter((r) => !r.owner.some((o) => lower(o) === lower(p)) && r.join.some((j) => lower(j) === lower(p)));
    const perPerson = [];
    for (const p of people) {
      Grills.setViewer(p); Grills.st.scope = "mine"; Grills.open(); await tick();
      const mine = owns(p), asked = joins(p);
      const side = $(".side-grills-door .side-n"), fromNeeds = Needs.lines().filter((l) => l.kind === "grill").length;
      Grills.open(); await tick();
      const chips = [chipN("mine"), chipN("join"), chipN("all")].join("/"), want = [mine.length, asked.length, rows.length].join("/");
      const sideN = side ? +side.textContent : 0;
      if (chips !== want || sideN !== mine.length || fromNeeds !== mine.filter((r) => r.group !== "one-away").length || !!$("#grills-badge") || shownIds() !== idsOf(mine)) {
        perPerson.push(`${p}: chips ${chips} want ${want}, sidebar ${sideN}, needs-you grills ${fromNeeds}, shown ${shownIds()} want ${idsOf(mine)}`);
      }
      // I'm asked to join shows exactly the grills someone asked this person to join
      click($('.g-scope[data-scope="join"]')); await tick();
      if (shownIds() !== idsOf(asked)) perPerson.push(`${p}: asked-to-join shows ${shownIds()} want ${idsOf(asked)}`);
      click($('.g-scope[data-scope="mine"]')); await tick();
    }
    ok(!perPerson.length, `grills: for each of ${people.length} people the Mine, I'm asked to join and Everyone's chips, the sidebar count and the ready grills in Needs you agree (${people.map((p) => `${personName(p)} ${owns(p).length} + ${joins(p).length}`).join("; ")})`, `grills: ${perPerson.join(" | ")}`);

    // the others' grills sit behind a count, one click away
    const who = people.find((p) => owns(p).length && rows.length > owns(p).length);
    if (who) {
      Grills.setViewer(who); Grills.st.scope = "mine"; Grills.open(); await tick();
      const more = rows.length - owns(who).length, note = $(".g-note");
      ok(!!note && note.textContent.startsWith(`${plural(more, "more grill")}`) && /belong/.test(note.textContent) && $$(".g-tile").some((t) => t.dataset.tile === "hidden" && t.firstChild.textContent === String(more)),
        `grills: "${note && note.textContent.trim()}" and the hidden tile say ${more}`, `grills: note "${note && note.textContent}"`);
      click($(".g-show-all")); await tick();
      ok(shownIds() === idsOf(rows) && Grills.st.scope === "all", "grills: Show everyone's brings the other owners' grills in", `grills: after Show everyone's ${shownIds()}`);
    }

    // follows the sidebar's Viewing as: nobody until a role is picked or recorded, then the people the plan records for it
    Grills.setViewer(""); await tick();
    ok(!Grills.viewerHandles().length || !!D.me, "grills: with no role picked and no page built for one person, nobody is viewing and everyone's grills show", `grills: handles ${Grills.viewerHandles().join(",")} with no role picked`);
    Onboard.rememberDoor("eng"); await tick();
    const eng = Grills.viewerHandles().map((x) => x.replace(/^@/, "").toLowerCase()).sort().join(), recorded = Object.entries(D.onboard.roles).filter(([, r]) => r === "eng").map(([k]) => k.replace(/^@/, "").toLowerCase()).sort().join();
    ok(!!D.me || eng === recorded, `grills: choosing Engineering in Viewing as makes Mine follow the people the plan records for it (${eng ? eng.split(",").map((x) => personName("@" + x)).join(", ") : "nobody: everyone's show"})`, `grills: Engineering gave ${eng}, the plan records ${recorded}`);
    Roles.st.chosen = false; Roles.st.role = "exec";

    // filters: owner, app, holds up, ready only
    Grills.setViewer("*"); Grills.open(); await tick();
    const bad = [];
    const owner = $('.g-select[data-filter="owner"]'), ownerChoice = [...owner.options].find((o) => o.value);
    if (ownerChoice) { owner.value = ownerChoice.value; owner.dispatchEvent(new Event("change", { bubbles: true })); await tick(); const want = idsOf(rows.filter((r) => r.owner.includes(ownerChoice.value))); if (shownIds() !== want) bad.push(`owner ${ownerChoice.value}: ${shownIds()} want ${want}`); }
    Grills.st.owner = ""; Grills.open(); await tick();
    const app = $('.g-select[data-filter="app"]'), appChoice = [...app.options].find((o) => o.value);
    if (appChoice) { app.value = appChoice.value; app.dispatchEvent(new Event("change", { bubbles: true })); await tick(); const want = idsOf(rows.filter((r) => r.apps.includes(appChoice.value))); if (shownIds() !== want) bad.push(`app ${appChoice.value}: ${shownIds()} want ${want}`); }
    Grills.st.app = ""; Grills.open(); await tick();
    const holds = $('.g-select[data-filter="holds"]'), holdChoice = [...holds.options].find((o) => o.value);
    if (holdChoice) { holds.value = holdChoice.value; holds.dispatchEvent(new Event("change", { bubbles: true })); await tick(); const want = idsOf(rows.filter((r) => r.holdsUp.includes(holdChoice.value))); if (shownIds() !== want) bad.push(`holds up ${holdChoice.value}: ${shownIds()} want ${want}`); }
    Grills.st.holds = ""; Grills.open(); await tick();
    click($(".g-ready-only")); await tick();
    if (shownIds() !== idsOf(rows.filter((r) => r.group !== "one-away")) || $(".g-group[data-group=one-away]")) bad.push(`ready only: ${shownIds()}`);
    click($(".g-ready-only")); await tick();
    const exercised = [ownerChoice && "owner", appChoice && "app", holdChoice && "holds up"].filter(Boolean).join(", ");  // a plan whose grills sit on no app, or hold nothing up, has no choice to try
    ok(!bad.length, `grills: Owner, App and Holds up each narrow the list to exactly their grills, and Ready only drops the group one thing away (exercised: ${exercised})`, `grills: ${bad.join("; ")}`);
    ok(["owner", "app", "holds"].every((id) => /: any$/.test($(`.g-select[data-filter="${id}"] option`).textContent)), "grills: each filter starts at any", "grills: a filter does not start at any");

    // cards: owner line, group parts
    const parts = [];
    for (const r of rows) {
      const c = $(`.g-card[data-grill="${r.id}"]`);
      if (!c) { parts.push(`${r.id} has no card`); continue; }
      if (!/^Owner: /.test($(".g-owner", c).textContent)) parts.push(`${r.name}: no owner line`);
      if (r.group === "said-yes" && ($(".g-quote", c) || c.textContent.includes("Yes,"))) parts.push(`${r.name}: the lead's words show on the card`);
      if (r.group === "one-away" && !/^(Waiting on|In the way): /.test($(".g-need", c).textContent)) parts.push(`${r.name}: no word on what is in the way`);
      if (r.group === "one-away" && r.missing.due && !$(".g-need", c).textContent.includes(day(r.missing.due))) parts.push(`${r.name}: no due date`);
      const q = r.openQuestion && r.openQuestion.question ? r.openQuestion : null, line = $(".g-openq", c);
      if (q && (!line || !line.textContent.includes(q.question.replace(/\?$/, "")) || (q.due && !line.textContent.includes(day(q.due))))) parts.push(`${r.name}: its open question is not on the card`);
      if (!q && line) parts.push(`${r.name}: a card says an open question that is not there`);
      if (IDLIKE.test([".g-t", ".g-owner", ".g-need", ".g-agrees"].map((q) => ($(q, c) ? $(q, c).textContent : "")).join(" "))) parts.push(`${r.name}: an ID or handle shows`);
    }
    for (const r of rows) {
      const c = $(`.g-card[data-grill="${r.id}"]`), box = c && $(".g-agrees", c);
      const said = r.agrees.lead || r.agrees.picked || r.agrees.choosing;
      if (!said && !box) continue;  // a page with no opening paragraph has nothing of the plan's to copy, so no box
      if (!box || $(".g-agrees-lab", box).textContent !== "Settling this agrees that") { parts.push(`${r.name}: no box saying what settling agrees to`); continue; }
      if (r.group === "one-away" && !(box.compareDocumentPosition($(".g-wait", c)) & Node.DOCUMENT_POSITION_FOLLOWING)) parts.push(`${r.name}: the Waiting on line is not below the box`);
      if (r.agrees.lead && !box.textContent.includes(r.agrees.lead)) parts.push(`${r.name}: the plan's words are not in the box`);
      const btn = $(".g-more-btn", box), list = $(".g-more-list", box);
      if (!!btn !== r.agrees.more.length > 0) parts.push(`${r.name}: the more-details button does not match what is left over`);
      if (btn) {
        if (list.querySelectorAll("li").length !== r.agrees.more.length || btn.textContent !== `+${plural(r.agrees.more.length, "more detail")}`) parts.push(`${r.name}: the count on the button is not the number held back`);
        if (btn.tagName !== "BUTTON" || !list.hidden) parts.push(`${r.name}: the extra details are not behind a button`);
        btn.click();
        if (list.hidden || btn.getAttribute("aria-expanded") !== "true") parts.push(`${r.name}: the button does not show the extra details`);
        btn.click();
      }
      if (r.agrees.page !== !!$(".g-whole", box)) parts.push(`${r.name}: the whole-page link does not match the kind of item`);
      if (/^Settles: /.test(c.textContent) || c.textContent.includes("Settles:")) parts.push(`${r.name}: the old Settles line is still there`);
    }
    ok(!parts.length, "grills: each card has an owner line; a said-yes card shows no words, a one-away card says what it waits on and by when, and a card with an open question under it names it", `grills: ${parts.join("; ")}`);

    // a card opens in the right-hand panel
    const pick = rows.find((r) => r.group === "ready" && !isRequirement(r)) || rows[0];
    click($(`.g-card[data-grill="${pick.id}"] .g-open`)); await tick();
    ok(head() === pick.name && Grills.st.open === `grill:${pick.id}` && $(`.g-card.on`).dataset.grill === pick.id, `grills: clicking ${shorten(pick.name, 36)} opens it in the right-hand panel and marks the card`, `grills: panel head "${head()}", open ${Grills.st.open}`);
    const want = ["What the grill settles", "Where it stands", "What it holds up", "Owner", "Asked to join", "Prompt for Claude"], got = sections();
    ok(want.every((w) => got.includes(w)) && want.map((w) => got.indexOf(w)).every((x, i, a) => !i || x > a[i - 1]), "grills: the panel gives what it settles, where it stands, what it holds up, the owner, who is asked to join and the prompt, in that order", `grills: sections ${got.join(", ")}`);
    const prompt = $("#panel-body [data-prompt=one]").textContent;
    ok(prompt.startsWith(`/vela:grill ${pick.name}\n`) && !IDLIKE.test(prompt) && prompt === Grills.prompt(pick), "grills: the prompt starts /vela:grill with the item's name and is plain words, no IDs or handles", `grills: prompt "${prompt.slice(0, 120)}"`);
    click($("#panel-body [data-act=copy]")); await tick();
    ok(Grills.st.copied === prompt, "grills: Copy prompt copies exactly the prompt shown", `grills: copied "${Grills.st.copied.slice(0, 80)}"`);
    const settle = $("#panel-body [data-prompt=settle]").textContent;
    ok(settle.startsWith(`Settle ${pick.name}.\n`) && !IDLIKE.test(settle) && !/grill/i.test(settle) && settle === Grills.settlePrompt(pick),
       "grills: the panel also has a settle prompt that starts Settle with the item's name and is plain words", `grills: settle "${settle.slice(0, 120)}"`);
    click($("#panel-body [data-act=copy-settle]")); await tick();
    ok(Grills.st.copied === settle, "grills: Copy settle prompt copies exactly the settle prompt shown", "grills: the settle copy differs");
    const open = $("#panel-body [data-act=open-item]");
    ok(!!open && /^Open the /.test(open.textContent), `grills: the panel has "${open && open.textContent}" to go to the item itself`, "grills: no Open the item button");
    const held = $$("#panel-body .g-panelchips a.ref-chip");
    ok(held.length === pick.holdsUp.filter((k) => ent(k)).length && held.every((a) => a.tabIndex === 0), `grills: what it holds up lists ${held.length} things as keyboard chips`, `grills: ${held.length} chips for ${pick.holdsUp.length}`);
    if (held[0]) { key(held[0], "Enter"); await tick(); ok(head() === titleOf(held[0].dataset.ref), `grills: Enter on the chip ${titleOf(held[0].dataset.ref)} opens it in the panel`, `grills: Enter opened "${head()}"`); }
    click($("#panel-body .dp-trail .linkish")); await tick();

    // a chip on a card opens the thing in the panel too
    const chipCard = cards().find((c) => $(".g-chip[data-ref-chip]", c));
    if (chipCard) { const chip = $(".g-chip[data-ref-chip]", chipCard); click(chip); await tick(); ok(head() === titleOf(chip.dataset.refChip), `grills: the chip "${chip.textContent}" on a card opens ${titleOf(chip.dataset.refChip)} in the panel`, `grills: chip opened "${head()}"`); }
    DetailsPanel.clear(); await tick();

    // the batch: one prompt, the item that unblocks the most first
    Grills.st.batch = []; Grills.open(); await tick();
    const sorted = rows.slice().sort((a, b) => b.holdsUp.length - a.holdsUp.length || order.indexOf(a.group) - order.indexOf(b.group) || cmp(a.name, b.name));  // the order, worked out here on its own
    const trio = rows.length > 3 ? [sorted[0], sorted[1], sorted[sorted.length - 1]] : sorted.slice(0, 3), reverse = trio.slice().reverse();  // the most held up, the next, and the least: added the other way round
    for (const r of reverse) { click($(`.g-card[data-grill="${r.id}"] .g-open`)); await tick(); click($("#panel-body [data-act=batch]")); await tick(); }
    const listed = $$(".g-batch-list li").map((li) => li.firstChild.textContent), batch = $(".g-batch .g-prompt") && $(".g-batch .g-prompt").textContent;
    const counts = trio.map((r) => r.holdsUp.length);
    ok(listed.join("|") === trio.map((r) => r.name).join("|") && counts.every((n, i) => !i || counts[i - 1] >= n) && batch === Grills.batchPrompt(trio),
      `grills: a batch of ${trio.length} lists them by what they unblock (${counts.join(", ")} things held up) and builds one prompt`, `grills: batch lists ${listed.join(" | ")}; wanted ${trio.map((r) => r.name).join(" | ")}`);
    ok(batch.startsWith(`/vela:grill ${trio.map((r) => r.name).join("; ")}\n`) && /\n1\. /.test(batch) && !IDLIKE.test(batch), "grills: the batch prompt starts /vela:grill with every name and numbers the grills in order, in plain words", `grills: batch "${batch.slice(0, 160)}"`);
    click($("[data-act=copy-batch]")); await tick();
    ok(Grills.st.copied === batch, "grills: Copy batch prompt copies exactly the batch shown", "grills: the batch copy differs");
    click($(".g-unbatch")); await tick();
    ok($$(".g-batch-list li").length === trio.length - 1, "grills: Remove takes one grill out of the batch", `grills: ${$$(".g-batch-list li").length} left`);
    const clear = $("[data-act=clear-batch]");  // a batch of one is already empty after Remove
    if (clear) { click(clear); await tick(); }
    ok(!$(".g-batch") && !Grills.st.batch.length, "grills: Clear the batch empties it", "grills: the batch is still there");
    DetailsPanel.clear();

    // a said-yes grill shows the date as a link, never the words; the link opens the item itself
    const yesRow = rows.find((r) => r.group === "said-yes");
    if (yesRow) {
      Grills.setViewer("*"); Grills.open(); await tick();
      click($(`.g-card[data-grill="${yesRow.id}"] .g-open`)); await tick();
      const receipt = $("#panel-body [data-act=open-receipt]");
      ok(!!receipt && receipt.tagName === "BUTTON" && /^You said yes on /.test(receipt.textContent) && !$("#panel-body .g-quote"), "grills: a said-yes panel shows the date as a link and none of the words", `grills: receipt link ${receipt && receipt.textContent}, words ${!!$("#panel-body .g-quote")}`);
      if (receipt) { click(receipt); await tick(); ok(!$("#panel-body [data-act=open-receipt]"), "grills: the You said yes link opens the item itself", "grills: the link left the grill panel showing"); }
    }

    // an item's own details: a small Ready for a grill line, only when a grill could decide it
    const ready = rows.find((r) => r.group !== "one-away" && ent(r.key) && !isRequirement(r)), away = rows.find((r) => r.group === "one-away" && ent(r.key));
    Nav.home(); await tick();
    if (ready) {
      go(ready.key, { reset: true }); await tick();
      const line = $("#panel-body [data-ready-for]");
      ok(!!line && sections().includes("Ready for a grill") && !!$("[data-act=copy-ready]", line), `grills: ${titleOf(ready.key)}'s own details carry a Ready for a grill line with Copy prompt`, `grills: sections ${sections().join(", ")}`);
      if (line) { click($("[data-act=copy-ready]", line)); await tick(); ok(Grills.st.copied === Grills.prompt(ready), "grills: that Copy prompt copies the same prompt", "grills: the line copied something else"); }
    }
    if (away) { go(away.key, { reset: true }); await tick(); ok(!$("#panel-body [data-ready-for]"), `grills: ${titleOf(away.key)}, one thing away, has no Ready for a grill line`, "grills: a one-away item says it is ready"); }
    Nav.home(); go("lights", { reset: true });

    // keyboard: every card's control is a button, arrows walk them, Escape returns to the summary
    Grills.setViewer("*"); Grills.open(); await tick();
    const opens = $$(".g-open"), first = opens[0], second = opens[1];
    ok(opens.length === rows.length && opens.every((b) => b.tagName === "BUTTON" && b.tabIndex >= 0) && $$(".g-chip[data-ref-chip], .g-scope, .g-select, .g-ready-only").every((b) => b.tabIndex >= 0), "grills: every card, chip and filter is a keyboard stop", "grills: something is not a keyboard stop");
    if (first && second) { first.focus(); key(first, "ArrowDown"); ok(document.activeElement === second, "grills: the down arrow moves from one card to the next", `grills: focus is on ${document.activeElement && document.activeElement.className}`); }
    click(first); await tick();
    ok(document.activeElement === $(".g-card.on .g-open"), "grills: after picking a card, focus stays on it", `grills: focus is on ${document.activeElement && document.activeElement.className}`);
    key(document.body, "Escape"); await tick();
    ok(!$("#panel-body .dp-trail") && !$(".g-card.on"), "grills: Escape returns the panel to the summary and unmarks the card", `grills: after Escape the trail is ${!!$("#panel-body .dp-trail")} and a card is marked ${!!$(".g-card.on")}`);
    const door = $(".side-grills-door");
    ok(!!door && door.tagName === "BUTTON" && /Waiting for a decision/.test(door.textContent), "grills: the sidebar has a Waiting for a decision button", "grills: no sidebar entry");
    Grills.setViewer(""); Nav.home(); go("lights", { reset: true });
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await grills(ok); } catch (e) { lines.push(`FAIL the grills check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the grills checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
