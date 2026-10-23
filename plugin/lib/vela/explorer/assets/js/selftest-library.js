/* ------------------------------------------------------------ The Library view (view-library.js), driven as a person would:
   rows grouped by what they are, the four filters, the search box, a row opening in the right-hand panel, a relates-to chip
   leading to the thing it names, that thing listing the item back, and the keyboard reaching every row. A vault whose
   register has no rows has no Library section, and these checks say so and stop. A block of its own after the details
   checks, so it merges apart from them. */
(() => {
  const base = SelfTest.run, tick = () => new Promise((r) => setTimeout(r, 30));
  const click = (el) => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  const key = (el, k) => el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  const rowsShown = () => $$(".lb-row");
  const head = () => { const h2 = $("#panel-body .p-head h2"); return h2 ? h2.textContent.trim() : ""; };
  const sections = () => $$("#panel-body .p-sec h3").map((x) => x.textContent.replace(/\s+\d+$/, "").trim());
  const groupLine = () => $$(".lb-group").map((g) => g.dataset.group + " " + $$(".lb-row", g).length).join(", ");

  async function library(ok) {
    const rows = Library.rows;
    if (!rows.length) { ok(!D.sections.some((s) => s.id === "library"), "library: a register with no rows has no Library section", "library: an empty register still lists a Library section"); return; }
    Nav.open("library"); Library.st.q = ""; Library.st.filter = "all"; Library.st.open = ""; showView("library"); await tick();

    // grouping: by type, in the view's order, every item once
    const expected = Library.groups(rows).map(([label, items]) => `${label} ${items.length}`).join(", ");
    ok(App.view === "library" && groupLine() === expected && rowsShown().length === rows.length,
      `library: ${rows.length} items group by what they are (${groupLine()}), each once`, `library: groups read "${groupLine()}", expected "${expected}", ${rowsShown().length} rows for ${rows.length}`);
    ok($$(".lb-group h3").map((x) => x.textContent.split(" · ")[0]).every((t) => ["API specs", "Designs", "Documents", "Wiki and tracker", "Other links"].includes(t)),
      "library: the group headings are API specs, Designs, Documents, Wiki and tracker, Other links", `library: group headings ${$$(".lb-group h3").map((x) => x.textContent).join(" | ")}`);

    // each row: icon, title, meta line, tag
    const bare = rowsShown().filter((r) => !$(".lb-ic svg", r) || !$(".lb-t", r).textContent.trim() || !$(".lb-m", r).textContent.trim() || !$(".lb-where", r).textContent.trim());
    ok(!bare.length, "library: every row has a type icon, a title, a meta line and a tag", `library: ${bare.length} rows miss a part: ${bare.map((r) => r.dataset.library).join(", ")}`);
    const tagFor = (r) => $(`.lb-row[data-library="${r.id}"] .lb-where`).textContent;
    const tagBad = rows.filter((r) => !(r.where === "newer" ? tagFor(r) === "newer version out" : r.where === "both" ? /^link \+ \S/.test(tagFor(r)) : r.where === "vault" ? tagFor(r) === "in the vault" : r.where === "link" ? tagFor(r) === "link" : tagFor(r) === "listed only"));
    ok(!tagBad.length, "library: the tags say newer version out, link + a file, in the vault, link or listed only, from where the item is kept", `library: wrong tag on ${tagBad.map((r) => `${r.id} ${r.where} "${tagFor(r)}"`).join("; ")}`);
    const when = rows.find((r) => r.date && isDate(r.date));
    ok(!when || $(`.lb-row[data-library="${when.id}"] .lb-m`).textContent.includes(dayYear(when.date)), "library: the meta line says the date in words", `library: meta "${when && $(`.lb-row[data-library="${when.id}"] .lb-m`).textContent}" lacks ${when && dayYear(when.date)}`);
    const leaked = $$(".lb-m, .lb-where, .lb-rel, .lb-gn").filter((x) => /SRC-\d/.test(x.textContent));  // a title is the owner's words and may hold one; the lines vela writes may not
    ok(!leaked.length, "library: the list says names, never register codes", "library: a register code shows in the list");

    // filters
    const filterBad = [];
    for (const [id, test] of [["vault", (r) => !!r.stored], ["links", (r) => !r.stored && r.web], ["cited", (r) => r.citedBy.length > 0], ["all", () => true]]) {
      click($(`.lb-filters [data-filter="${id}"]`)); await tick();
      const want = rows.filter(test).map((r) => r.id).sort().join(","), got = rowsShown().map((r) => r.dataset.library).sort().join(",");
      if (want !== got) filterBad.push(`${id}: wanted ${want} got ${got}`);
      const chip = $(`.lb-filters [data-filter="${id}"]`);
      if (id !== "all" && $(".lb-n", chip).textContent !== String(rows.filter(test).length)) filterBad.push(`${id}: the chip counts ${$(".lb-n", chip).textContent}`);
    }
    ok(!filterBad.length, "library: In the vault, Links and Cited by the plan each show exactly their items, and their chips count them", `library: ${filterBad.join("; ")}`);

    // search
    const input = $(".lb-find"), word = rows[0].title.split(/\s+/).find((w) => w.length > 3) || rows[0].title;
    input.value = word; input.dispatchEvent(new Event("input", { bubbles: true })); await tick();
    const hit = rowsShown().map((r) => r.dataset.library);
    ok(hit.includes(rows[0].id) && hit.every((id) => Library.matching(true).some((r) => r.id === id)) && $("#lb-count").textContent.startsWith("Showing"),
      `library: searching "${word}" keeps the matching items and says how many`, `library: search "${word}" gave ${hit.join(",")} and "${$("#lb-count").textContent}"`);
    input.value = "zzzz nothing like this"; input.dispatchEvent(new Event("input", { bubbles: true })); await tick();
    ok(rowsShown().length === 0 && /Nothing matches/.test($(".lb-none") ? $(".lb-none").textContent : ""), "library: a search that matches nothing says so and offers to clear", "library: no empty message for a search that matches nothing");
    click($(".lb-none .linkish")); await tick();
    ok(rowsShown().length === rows.length && Library.st.q === "", "library: Clear filters brings every item back", `library: ${rowsShown().length} rows after clearing`);

    // the detail panel
    const item = rows.find((r) => r.stored && r.relates.some((k) => ent(k) && !k.startsWith("lib:")) && r.citedBy.length) || rows.find((r) => r.stored) || rows[0];
    click($(`.lb-row[data-library="${item.id}"]`)); await tick();
    ok(head() === item.title && Library.st.open === item.key && $(`.lb-row.on`).dataset.library === item.id, `library: clicking ${shorten(item.title, 36)} opens it in the right-hand panel and marks the row`, `library: panel head "${head()}", open ${Library.st.open}`);
    const panel = $("#panel-body").textContent;
    ok(/Stored/.test(panel) && /From/.test(panel) && /Added by/.test(panel) && /Relates to/.test(panel) && /Cited by/.test(panel) && (item.type !== "spec" || /Version/.test(panel)),
      "library: the panel says where it is stored, its version, the original, who added it, what it relates to and what cites it", `library: panel reads "${panel.slice(0, 200)}"`);
    const file = $("#panel-body .lb-actions a.btn"), isFile = item.stored && file && file.textContent === "Open the file";
    ok(!item.stored || (isFile && decodeURIComponent(file.getAttribute("href")).endsWith(item.stored) && file.target === "_blank"), `library: Open the file links to ${item.stored || "nothing (a link only)"}, relative to the page`, `library: Open the file is "${file && file.getAttribute("href")}"`);
    const orig = $$("#panel-body .lb-actions a.btn").find((a) => a.textContent === "Open the original");
    ok(item.web ? !!orig && orig.getAttribute("href") === item.location && /noopener/.test(orig.rel) : !orig, "library: Open the original opens a web address in a new tab, and is left out when the original is not one", `library: original link ${orig && orig.getAttribute("href")} for "${item.location}"`);
    const cites = $("#panel-body .lb-cites");
    ok(!cites || $$("a.ref-chip", cites).length === item.citedBy.filter((k) => ent(k)).length, `library: what cites it lists the ${item.citedBy.length} pages and items that name it`, `library: ${cites && $$("a.ref-chip", cites).length} chips for ${item.citedBy.length}`);
    const act = $("#panel-body [data-act=cites]");
    if (cites && act) { click(act); await tick(); ok(cites.classList.contains("flash") && cites.contains(document.activeElement), "library: Show what cites it brings the list into view and focuses it", "library: Show what cites it did nothing"); }

    // relates to: a chip leads to the thing, and the thing lists the item back
    const target = item.relates.find((k) => ent(k) && !k.startsWith("lib:"));
    if (target) {
      const chip = $$("#panel-body .lb-kv a.ref-chip").find((a) => a.dataset.ref === target);
      ok(!!chip, `library: the relates-to chip names ${titleOf(target)}`, `library: no chip for ${target} in the panel`);
      if (chip) {
        click(chip); await tick();
        ok(head() === titleOf(target) && /›.*›/.test($("#panel-body .dp-trail") ? $("#panel-body .dp-trail").textContent : ""), `library: the chip opens ${titleOf(target)} with the trail back to the item`, `library: chip opened "${head()}"`);
        const back = $("#panel-body .lb-back");
        ok(sections().includes("Library") && !!back && !!$(`[data-ref="${item.key}"]`, back), `library: ${titleOf(target)} has a Library section that lists ${shorten(item.title, 30)}`, `library: ${titleOf(target)} shows sections ${sections().join(", ")}`);
        click($(`[data-ref="${item.key}"]`, back)); await tick();
        ok(head() === item.title, "library: a Library entry on that panel opens the item again", `library: entry opened "${head()}"`);
      }
    }

    // keyboard: rows are buttons, arrows walk them, Escape returns to the summary
    showView("library"); DetailsPanel.clear(); await tick();
    const first = rowsShown()[0], second = rowsShown()[1];
    first.focus(); key(first, "ArrowDown");
    ok(!second || document.activeElement === second, "library: the down arrow moves from one row to the next", `library: focus is on ${document.activeElement && document.activeElement.className}`);
    ok(rowsShown().every((r) => r.tagName === "BUTTON" && r.tabIndex >= 0), "library: every row is a button the keyboard reaches", "library: a row is not a keyboard stop");
    click(first); await tick();
    key(document.body, "Escape"); await tick();
    ok(!$("#panel-body .dp-trail") && !$(".lb-row.on"), "library: Escape returns the panel to the summary and unmarks the row", `library: after Escape the trail is ${!!$("#panel-body .dp-trail")} and a row is marked ${!!$(".lb-row.on")}`);

    // the search box at the top finds an item by name and by its code
    const hits = Search.type(item.title.split(/\s+/).slice(0, 3).join(" "));
    ok(hits.includes(item.key), `library: the top search finds ${shorten(item.title, 36)} by its name`, `library: top search gave ${hits.join(",")}`);
    ok(Search.type(item.id).includes(item.key), "library: the top search finds an item by its code", "library: the code finds nothing");
    Search.type("");
    Nav.home(); go("lights", { reset: true });
  }

  SelfTest.run = async () => {
    const report = await base(), lines = [], errors = window.__errors.length;
    const ok = (cond, good, bad) => { lines.push(cond ? "ok " + good : "FAIL " + (bad || good)); if (HASH.has("trace")) console.log("[selftest] " + lines[lines.length - 1]); };
    try { await library(ok); } catch (e) { lines.push(`FAIL the library check threw: ${e.message} ${(e.stack || "").split("\n")[1]}`); }
    if (window.__errors.length > errors) lines.push("FAIL JS ERRORS in the library checks: " + window.__errors.slice(errors).join(" | "));
    const body = report.slice(1).concat(lines), fails = body.filter((l) => l.startsWith("FAIL")).length;
    const out = [fails ? `SELFTEST FAIL: ${fails} of ${body.length} checks failed` : `SELFTEST OK: ${body.length} checks passed`, ...body];
    document.body.setAttribute("data-selftest", out.join(" || "));
    return out;
  };
})();
