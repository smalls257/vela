/* The layout: which cell each box stands in, and how a reader moves one.

   The vault's pins file is the layout (pins.py, <vault>/.planner/explorer-pins.json, tracked in git). This module
   holds those pins, the moves a reader makes on top of them, and the one rule that keeps a move from drawing a box
   over another. The rule is pins.check_move's, written again here because a drop is refused or nudged before any
   request is made: two boxes of one row stand at least one column apart, and an outside party never sits above an
   app. #selftest plays the same cases against both.

   Where a move goes depends on how the page was opened:
   - served (`planner explore --serve`) by the vault's owner: the move is saved to the vault at once, by POST /pins
     on the helper (serve.py), and the page says "Layout saved to the vault";
   - a file, or a reader's copy: the move stays in this browser (localStorage, scoped by vault id) and the page
     offers "Copy layout" and "Download pins", the JSON the owner commits. A reader's move changes nothing in the
     vault unless the reader sends it on.
   "Reset layout" returns to the pins the vault gave the page. A box being dragged is held in `live` as a fractional
   cell and written into D.nodes, so the cockpit, the line map and the minimap all draw it where the pointer is. */
const Layout = (() => {
  const STORE = `explorer.layout.${D.vaultId}`, GROUP = "grp:", MIN_APART = 1, PIXEL_ASPECT = 2.5, REACH = 6;
  const clone = (pins) => Object.fromEntries(Object.entries(pins).map(([k, v]) => [k, v.slice()]));
  const same = (a, b) => !!a && !!b && a[0] === b[0] && a[1] === b[1];
  const isCell = (v) => Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === "number" && isFinite(x));
  let base = clone((D.pins && D.pins.all) || {});  // the vault's pins as the helper last said, or as the page was built
  let built = clone(base);                          // as the page was built: what Reset returns to when saving to the vault
  let mine = {};                                    // this reader's moves not yet in the vault
  let live = null;                                  // a box being dragged: { key, col, row, spot }
  let note = "", copyFn = null;
  const net = { fetch: (...a) => fetch(...a) };     // #selftest swaps in a fake

  const kindOf = (key) => (NODE[key] && NODE[key].kind === "app" ? "app" : "partner");
  const cells = () => Object.assign({}, base, mine);
  const cell = (key) => (cells()[key] || [0, 0]);
  const canSave = () => typeof Ask !== "undefined" && Ask.served() && D.role !== "reader";

  /* Why this layout cannot be drawn without overlap, or "": pins.check_move. `cs` is {key: [col, row]}. */
  function check(cs) {
    const placed = Object.entries(cs).filter(([k]) => NODE[k]).map(([k, [c, r]]) => ({ k, c, r })).sort((a, b) => a.r - b.r || a.c - b.c || cmp(a.k, b.k));
    for (let i = 1; i < placed.length; i++) {
      const p = placed[i - 1], q = placed[i];
      if (p.r === q.r && q.c - p.c < MIN_APART - 1e-9) return `${titleOf(p.k)} and ${titleOf(q.k)} would overlap: boxes in one row stand at least ${MIN_APART} column apart`;
    }
    const low = Math.max(-Infinity, ...placed.filter((x) => kindOf(x.k) === "app").map((x) => x.r));
    const high = placed.find((x) => kindOf(x.k) !== "app" && x.r < low);
    return high ? `${titleOf(high.k)} is an outside party and would sit above the apps; parties stay in the band below them` : "";
  }
  /* Why `key` cannot stand at (col, row) given where everything else is, or "". */
  function blocker(key, col, row) {
    if (!(col >= 0) || !(row >= 0)) return "that is off the board";
    const cs = cells();
    delete cs[key];
    cs[key] = [col, row];
    return check(cs);
  }
  /* The free cell nearest (col, row), measured as drawn (a column is wider than a row is tall), or null. */
  function nearestFree(key, col, row) {
    let best = null, bestD = Infinity;
    for (let c = Math.max(0, Math.round(col) - REACH); c <= Math.round(col) + REACH; c++) {
      for (let r = Math.max(0, Math.round(row) - REACH); r <= Math.round(row) + REACH; r++) {
        const d = Math.hypot((c - col) * PIXEL_ASPECT, r - row);
        if (d < bestD - 1e-9 && !blocker(key, c, r)) { best = [c, r]; bestD = d; }
      }
    }
    return best;
  }

  function apply() {
    const cs = cells();
    for (const n of D.nodes) {
      const at = live && live.key === n.key ? [live.col, live.row] : cs[n.key];
      if (at) { n.col = at[0]; n.row = at[1]; }
    }
  }

  /* ------------------------------------------------------------ dragging */
  function drag(key, col, row) {
    live = { key, col, row, spot: nearestFree(key, col, row) };
    apply();
    return live;
  }
  function endDrag() { const was = live; live = null; apply(); return was; }

  /* ------------------------------------------------------------ keeping a move */
  function say(text) { note = text; const el = $("#layout-say"); if (el) el.textContent = text; }
  function remember() {
    Settings.write(STORE, JSON.stringify({ pins: mine }));
  }
  /* The moves of an earlier visit, if they still fit the layout the vault holds now. */
  function recall() {
    const raw = Settings.read(STORE);
    if (!raw) return;
    let saved;
    try { saved = JSON.parse(raw).pins; } catch (e) { console.warn("[layout] the moves kept in this browser cannot be read, so they were dropped:", e.message); return; }
    const kept = Object.fromEntries(Object.entries(saved || {}).filter(([k, v]) => k in base && isCell(v) && !same(v, base[k])));
    if (!Object.keys(kept).length) return;
    const problem = check(Object.assign({}, base, kept));
    if (problem) { console.warn(`[layout] the moves kept in this browser no longer fit the vault's layout (${problem}), so they were dropped`); note = "Your earlier moves no longer fit this vault's layout and were dropped."; remember(); return; }
    mine = kept;
  }
  function pinsBody() {
    const cs = cells();
    return JSON.stringify({ pins: cs, kinds: Object.fromEntries(Object.keys(cs).filter((k) => NODE[k]).map((k) => [k, kindOf(k)])) });
  }
  /* POST /pins; the vault's file is the answer, so a failure is said and the move is kept here instead of lost. */
  async function saveToVault(said = "") {
    try {
      const res = await net.fetch("/pins", { method: "POST", headers: { "Content-Type": "application/json" }, body: pinsBody() });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `the helper answered ${res.status}`);
      base = clone(body.pins); mine = {}; remember();
      say(`${said}Layout saved to the vault`);
      return true;
    } catch (e) {
      console.warn("[layout] the helper did not save the layout:", e.message);
      remember();
      say(`${said}Not saved to the vault: ${e.message}. The move is kept in this browser.`);
      return false;
    }
  }
  async function keep(said = "") {
    if (canSave()) { await saveToVault(said); refreshTools(); return; }
    remember();
    say(`${said}Kept in this browser only; Copy layout or Download pins sends it on.`);
  }

  /* ------------------------------------------------------------ moving */
  /* Put `key` in `spot`. {ok, why}: a refused move changes nothing. */
  function move(key, spot) {
    const why = blocker(key, spot[0], spot[1]);
    if (why) { say(`${titleOf(key)} stays where it is: ${why}.`); return { ok: false, why }; }
    if (same(cell(key), spot)) return { ok: true, same: true };
    if (same(base[key], spot)) delete mine[key]; else mine[key] = spot.slice();
    apply();
    keep(`${titleOf(key)} moved to column ${spot[0] + 1}, row ${spot[1] + 1}. `);
    return { ok: true };
  }
  /* One cell in a direction, for the arrow keys; the neighbouring cell must be free. */
  function step(key, dc, dr) {
    const [c, r] = cell(key);
    return move(key, [c + dc, r + dr]);
  }
  function drop(key) {
    const was = endDrag();
    if (!was || !was.spot) { say(`${titleOf(key)} stays where it is: no free cell near there.`); return { ok: false }; }
    return move(key, was.spot);
  }

  /* Clusters of the grouped map keep an order, not a cell: `grp:<cluster key>` pins [place, 0]. Clusters with no pin
     follow the ones that have one, in the order the map would give them. */
  function ordered(items, keyOf) {
    const cs = cells(), at = (it) => cs[GROUP + keyOf(it)];
    const pinned = items.filter((it) => at(it)).sort((a, b) => at(a)[0] - at(b)[0] || cmp(keyOf(a), keyOf(b)));
    return [...pinned, ...items.filter((it) => !at(it))];
  }
  function reorder(keys) {
    keys.forEach((k, i) => { const spot = [i, 0]; if (same(base[GROUP + k], spot)) delete mine[GROUP + k]; else mine[GROUP + k] = spot; });
    keep("Clusters reordered. ");
    rerender();
  }

  /* ------------------------------------------------------------ resetting, copying, downloading */
  const moved = () => (canSave() ? JSON.stringify(cells()) !== JSON.stringify(built) : Object.keys(mine).length > 0);
  async function reset() {
    live = null;
    mine = {};
    if (canSave()) {
      base = clone(built);
      apply();
      if (await saveToVault()) say("Layout reset to the pins this page was built with, and saved to the vault");
    } else { apply(); remember(); say("Layout reset to the vault's pins"); }
    rerender();
  }
  const layoutJson = () => JSON.stringify(Object.fromEntries(Object.entries(cells()).sort(([a], [b]) => cmp(a, b))), null, 2) + "\n";
  async function copy() {
    try { await (copyFn || ((t) => navigator.clipboard.writeText(t)))(layoutJson()); say("Layout copied. Commit it as .planner/explorer-pins.json."); }
    catch (e) { console.warn("[layout] could not copy:", e.message); say(`Could not copy (${e.message}); use Download pins.`); }
    refreshTools();
  }
  function download() {
    const url = URL.createObjectURL(new Blob([layoutJson()], { type: "application/json" }));
    const a = h("a", { href: url, download: "explorer-pins.json" });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    say("Pins downloaded. Commit the file as .planner/explorer-pins.json.");
    refreshTools();
  }

  /* ------------------------------------------------------------ the map's toolbar */
  function tools(what = "box") {
    const saving = canSave(), dirty = moved();
    const grab = `Drag a ${what}, or focus it and press an arrow key, to move it.`;
    const hint = saving ? `Drag a ${what} or use arrow keys. Saved to the vault.` : "Drag a box or use arrow keys. Kept in this browser; commit the downloaded pins.";
    toolsFor = what;
    return h("span", { class: "tool-unit layout-tools", title: `${grab} ${saving ? "A move is saved to the vault's pins file." : "A move stays in this browser; Copy layout or Download pins gives the owner a file to commit as .planner/explorer-pins.json."}` },
      h("span", { class: "tool-label sep" }, "Layout"),
      h("button", { class: "chip", "data-layout": "reset", disabled: dirty ? null : true, title: "Put every box back where the vault's pins have it", onclick: reset }, "Reset layout"),
      saving ? null : h("button", { class: "chip", "data-layout": "copy", title: "Copy the layout as JSON, for .planner/explorer-pins.json", onclick: copy }, "Copy layout"),
      saving ? null : h("button", { class: "chip", "data-layout": "download", title: "Download the layout as explorer-pins.json", onclick: download }, "Download pins"),
      h("span", { class: "tool-hint layout-say", id: "layout-say", role: "status", "aria-live": "polite" }, note || hint));
  }
  let toolsFor = "box";
  function refreshTools() {
    const old = $(".layout-tools"), fresh = tools(toolsFor);
    if (old) old.replaceWith(fresh);
  }

  /* A served page asks the helper for the layout it holds now: the page file is as old as its build. */
  async function boot() {
    if (!canSave()) return;
    try {
      const res = await net.fetch("/pins");
      if (!res.ok) throw new Error(`/pins answered ${res.status}`);
      const body = await res.json();
      if (JSON.stringify(body.pins) === JSON.stringify(base)) return;
      base = clone(body.pins); mine = {}; apply();
      if ($("#main").childNodes.length && App.view === "map") rerender();
    } catch (e) { console.warn("[layout] served from this machine, but the helper did not give its layout; the page keeps the one it was built with:", e.message); }
  }

  recall();
  apply();
  /* For #selftest: a page played as served against a fake fetch, then put back as it was. */
  const snapshot = () => ({ base: clone(base), built: clone(built), mine: clone(mine), note });
  function restore(s) { base = s.base; built = s.built; mine = s.mine; note = s.note; live = null; apply(); remember(); }
  return { cell, cells, blocker, check, nearestFree, drag, endDrag, drop, move, step, ordered, reorder, reset, copy, download, tools, boot, say, moved, canSave, net,
    get live() { return live; }, get note() { return note; }, layoutJson, snapshot, restore, setCopy: (fn) => { copyFn = fn; }, KIND: kindOf };
})();
