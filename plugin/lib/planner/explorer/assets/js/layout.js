/* The layout: where each box stands, and how a reader moves one.

   The vault's pins file is the layout (pins.py, <vault>/.planner/explorer-pins.json, tracked in git). This module
   holds those pins, the moves a reader makes on top of them, and the one rule that keeps a move from drawing a box
   over another. A box stays where it is dropped, between cells if that is where the pointer let go. The only rule is
   pins.check_move's, written again here because a drop is placed before any request is made: two boxes, as drawn,
   keep pins.GAP pixels between their edges, an outside party measured a band below its row. Both copies measure in
   the frame the build hands over (D.pins.frame), and #selftest plays pins.MOVE_CASES, with check_move's answers,
   against this copy. A drop that would overlap lands at the nearest clear point on the line it was dragged along,
   and the page's status line says so.

   Where a move goes depends on how the page was opened:
   - served (`planner explore --serve`) by the vault's owner: the move is saved to the vault at once, by POST /pins
     on the helper (serve.py), and the page says "Layout saved to the vault";
   - a file, or a reader's copy: the move stays in this browser (localStorage, scoped by vault id) and the page
     offers "Copy layout" and "Download pins", the JSON the owner commits. A reader's move changes nothing in the
     vault unless the reader sends it on.
   "Reset layout" returns to the pins the vault gave the page. A box being dragged is held in `live` and written into
   D.nodes, so the cockpit, the line map and the minimap all draw it where the pointer is. */
const Layout = (() => {
  const STORE = `explorer.layout.${D.vaultId}`, GROUP = "grp:";
  const F = D.pins.frame;                           // pins.FRAME, BOX, GAP and SLACK, from the build
  const FRAME = { cw: F.cw, rh: F.rh, bandGap: F.bandGap };
  const STEP = 0.25;                                // an arrow key moves a quarter of a cell; Shift and an arrow, a whole cell
  const PLACES = 1000;                              // a position is kept to a thousandth of a cell (0.4 px), so the file stays readable
  const clone = (pins) => Object.fromEntries(Object.entries(pins).map(([k, v]) => [k, v.slice()]));
  const same = (a, b) => !!a && !!b && a[0] === b[0] && a[1] === b[1];
  const isCell = (v) => Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === "number" && isFinite(x));
  const tidy = (v) => Math.round(v * PLACES) / PLACES;
  let base = clone((D.pins && D.pins.all) || {});  // the vault's pins as the helper last said, or as the page was built
  let built = clone(base);                          // as the page was built: what Reset returns to when saving to the vault
  let mine = {};                                    // this reader's moves not yet in the vault
  let live = null;                                  // a box being dragged: { key, col, row, land }
  let note = "", copyFn = null;
  const net = { fetch: (...a) => fetch(...a) };     // #selftest swaps in a fake

  const kindOf = (key) => (NODE[key] && NODE[key].kind === "app" ? "app" : "partner");
  const cells = () => Object.assign({}, base, mine);
  const cell = (key) => (cells()[key] || [0, 0]);
  const canSave = () => typeof Ask !== "undefined" && Ask.served() && D.role !== "reader";
  const nameOf = (k) => (NODE[k] ? titleOf(k) : k);

  /* ------------------------------------------------------------ the rule: pins.check_move */
  /* Where a box's center is drawn, in the frame's pixels: an outside party a band below its row (pins.drawn). */
  const drawn = (at, kind) => ({ x: at[0] * F.cw, y: at[1] * F.rh + (kind === "app" ? 0 : F.bandGap) });
  function clash(a, ka, b, kb) {
    const p = drawn(a, ka), q = drawn(b, kb);
    return Math.abs(p.x - q.x) < F.boxW + F.gap - F.slack && Math.abs(p.y - q.y) < F.boxH + F.gap - F.slack;
  }
  /* Why this layout cannot be drawn without overlap, or "": pins.check_move, pair for pair. `cs` is {key: [col, row]},
     `kinds` {key: "app" | "partner"}; keys beyond `kinds` (clusters) are not boxes. */
  function verdict(cs, kinds) {
    const boxes = Object.entries(cs).filter(([k]) => k in kinds).map(([k, [c, r]]) => ({ k, c, r })).sort((a, b) => a.c - b.c || a.r - b.r || cmp(a.k, b.k));
    const reach = (F.boxW + F.gap) / F.cw;  // columns: past this, nothing further right can touch
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length && boxes[j].c - boxes[i].c < reach; j++) {
        const p = boxes[i], q = boxes[j];
        if (clash([p.c, p.r], kinds[p.k], [q.c, q.r], kinds[q.k])) return `${nameOf(p.k)} and ${nameOf(q.k)} would overlap: boxes keep ${F.gap} px apart as drawn`;
      }
    }
    return "";
  }
  const kindsOf = (cs) => Object.fromEntries(Object.keys(cs).filter((k) => NODE[k]).map((k) => [k, kindOf(k)]));
  const check = (cs) => verdict(cs, kindsOf(cs));
  /* Why `key` cannot stand at (col, row) given where everything else is, or "". */
  function blocker(key, col, row) {
    if (!(col >= 0) || !(row >= 0)) return "that is off the board";
    const cs = cells();
    delete cs[key];
    cs[key] = [col, row];
    return check(cs);
  }

  /* ------------------------------------------------------------ stopping short of a box */
  /* Along the line from `a` to `b` (a moving box's centers, px), the point nearest `b` where the box, w by h, keeps
     `gap` from every one of `others` ({x, y, w, h, key}, centers) and `ok(point)` holds: { at, t, hit }, where t = 1
     is `b` itself, t < 1 stopped short of `hit` and t > 1 went just past it; null when no point on the line is clear.
     Shared with the grouped map's clusters (mapgroups.js). Measured with the whole gap, so a point rounded to a
     thousandth of a cell still passes the rule, which allows F.slack. */
  function along(a, b, w, h, others, gap, ok = () => true) {
    const dx = b.x - a.x, dy = b.y - a.y, spans = [];
    const span = (p0, d, c, reach) => {
      if (Math.abs(d) < 1e-9) return Math.abs(p0 - c) < reach ? [-Infinity, Infinity] : null;
      const t1 = (c - reach - p0) / d, t2 = (c + reach - p0) / d;
      return [Math.min(t1, t2), Math.max(t1, t2)];
    };
    for (const o of others) {
      const sx = span(a.x, dx, o.x, (w + o.w) / 2 + gap), sy = span(a.y, dy, o.y, (h + o.h) / 2 + gap);
      if (!sx || !sy) continue;
      const lo = Math.max(sx[0], sy[0]), hi = Math.min(sx[1], sy[1]);
      if (lo < hi) spans.push({ lo, hi, o });
    }
    const inside = (t) => spans.find((sp) => sp.lo < t - 1e-9 && t + 1e-9 < sp.hi);
    const point = (t) => ({ x: a.x + dx * t, y: a.y + dy * t });
    const hit = inside(1);
    if (!hit && ok(point(1))) return { at: point(1), t: 1, hit: null };
    const tries = spans.flatMap((sp) => [sp.lo, sp.hi]).filter((t) => isFinite(t) && t >= 0 && !inside(t) && ok(point(t)));
    if (!tries.length) return null;
    const t = tries.sort((p, q) => Math.abs(p - 1) - Math.abs(q - 1) || p - q)[0];
    return { at: point(t), t, hit: hit ? hit.o.key : null };
  }
  /* Where `key` lands when moved from `from` toward `to` (cells): `to` when it is clear, else the nearest clear point
     on that line, short of the box in the way or just past it: { spot, hit, past }, or null when nothing on it is clear. */
  function landing(key, from, to) {
    const kind = kindOf(key), band = kind === "app" ? 0 : F.bandGap;
    const others = Object.entries(cells()).filter(([k]) => NODE[k] && k !== key).map(([k, at]) => ({ ...drawn(at, kindOf(k)), w: F.boxW, h: F.boxH, key: k }));
    const onBoard = (p) => p.x >= -1e-6 && p.y - band >= -1e-6;
    const got = along(drawn(from, kind), drawn(to, kind), F.boxW, F.boxH, others, F.gap, onBoard);
    if (!got) return null;
    return { spot: [tidy(Math.max(0, got.at.x / F.cw)), tidy(Math.max(0, (got.at.y - band) / F.rh))], hit: got.hit, past: got.t > 1 };
  }
  const where = (spot) => `column ${+(spot[0] + 1).toFixed(2)}, row ${+(spot[1] + 1).toFixed(2)}`;
  const nudged = (key, land) => (!land.hit ? "" : `${titleOf(key)} would have overlapped ${nameOf(land.hit)}, so it ${land.past ? "went just past" : "stopped just short of"} it. `);

  function apply() {
    const cs = cells();
    for (const n of D.nodes) {
      const at = live && live.key === n.key ? [live.col, live.row] : cs[n.key];
      if (at) { n.col = at[0]; n.row = at[1]; }
    }
  }

  /* ------------------------------------------------------------ dragging */
  /* The box follows the pointer; `land` is where it will stand when let go, drawn as a dashed outline when it differs. */
  function drag(key, col, row) {
    live = { key, col, row, land: landing(key, cell(key), [col, row]) };
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
    return JSON.stringify({ pins: cs, kinds: kindsOf(cs) });
  }
  /* POST /pins; the vault's file is the answer, so a failure is said and the move is kept here instead of lost. */
  async function saveToVault(said = "") {
    try {
      const res = await net.fetch("/pins", { method: "POST", headers: { "Content-Type": "application/json" }, body: pinsBody() });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `the helper answered ${res.status}`);
      base = clone(body.pins); mine = {}; remember();
      say(`${said}Layout saved to the plan`);
      return true;
    } catch (e) {
      console.warn("[layout] the helper did not save the layout:", e.message);
      remember();
      say(`${said}Not saved to the plan: ${e.message}. The move is kept in this browser.`);
      return false;
    }
  }
  async function keep(said = "") {
    if (canSave()) { await saveToVault(said); refreshTools(); return; }
    remember();
    say(`${said}Kept in this browser only. To share it, download the layout and send it to the plan's owner.`);
  }

  /* ------------------------------------------------------------ moving */
  /* Put `key` at `spot` exactly. {ok, why}: a move onto another box is refused and changes nothing. */
  function move(key, spot, said = "") {
    const why = blocker(key, spot[0], spot[1]);
    if (why) { say(`${said}${titleOf(key)} stays where it is: ${why}.`); return { ok: false, why }; }
    if (same(cell(key), spot)) { if (said) say(`${said}${titleOf(key)} stays where it is.`); return { ok: true, same: true }; }
    if (same(base[key], spot)) delete mine[key]; else mine[key] = spot.slice();
    apply();
    keep(`${said}${titleOf(key)} moved to ${where(spot)}. `);
    return { ok: true };
  }
  /* Move toward `to`, stopping at the nearest clear point on the way, and say so when it had to. */
  function moveToward(key, to) {
    if (!(to[0] >= 0) || !(to[1] >= 0)) {
      const edge = [Math.max(0, to[0]), Math.max(0, to[1])];
      if (same(edge, cell(key))) { say(`${titleOf(key)} stays where it is: that is off the board.`); return { ok: false, why: "that is off the board" }; }
      to = edge;
    }
    const land = landing(key, cell(key), to);
    if (!land) { say(`${titleOf(key)} stays where it is: there is no clear place on that line.`); return { ok: false, why: "no clear place" }; }
    return move(key, land.spot, nudged(key, land));
  }
  /* An arrow key: a quarter of a cell in a direction, or a whole cell with Shift. */
  function step(key, dc, dr, whole = false) {
    const [c, r] = cell(key), by = whole ? 1 : STEP;
    return moveToward(key, [tidy(c + dc * by), tidy(r + dr * by)]);
  }
  function drop(key) {
    const was = endDrag();
    if (!was || !was.land) { say(`${titleOf(key)} stays where it is: there is no clear place on the line it was dragged along.`); return { ok: false }; }
    return move(key, was.land.spot, nudged(key, was.land));
  }

  /* ------------------------------------------------------------ clusters of the grouped map */
  /* A cluster stands where a reader put it: `grp:<cluster key>` pins its top left corner, in cells of FRAME on the
     grouped board. A cluster with no pin is shelved (mapgroups.js). Dropping one pins every cluster drawn at that
     moment, so the others stay exactly where they are. An earlier version kept [place, 0] as an order; read as a
     corner, such pins put the clusters in one row in that order, pushed apart where they would overlap. */
  const clusterAt = (key) => cells()[GROUP + key];
  function placeClusters(spots, said) {
    const minX = Math.min(...spots.map((s) => s.at[0])), minY = Math.min(...spots.map((s) => s.at[1]));  // a pin is never left of or above the board
    for (const { key, at } of spots) {
      const spot = [tidy(at[0] - Math.min(0, minX)), tidy(at[1] - Math.min(0, minY))];
      if (same(base[GROUP + key], spot)) delete mine[GROUP + key]; else mine[GROUP + key] = spot;
    }
    keep(said);
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
      if (await saveToVault()) say("Layout reset to how this page was built, and saved to the plan");
    } else { apply(); remember(); say("Layout reset to how this page was built"); }
    rerender();
  }
  const layoutJson = () => JSON.stringify(Object.fromEntries(Object.entries(cells()).sort(([a], [b]) => cmp(a, b))), null, 2) + "\n";
  async function copy() {
    try { await (copyFn || ((t) => navigator.clipboard.writeText(t)))(layoutJson()); say("Layout copied. Send it to the plan's owner to keep it for everyone."); }
    catch (e) { console.warn("[layout] could not copy:", e.message); say(`Could not copy (${e.message}); use Download pins.`); }
    refreshTools();
  }
  function download() {
    const url = URL.createObjectURL(new Blob([layoutJson()], { type: "application/json" }));
    const a = h("a", { href: url, download: "explorer-pins.json" });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    say("Layout downloaded. Send the file to the plan's owner to keep it for everyone.");
    refreshTools();
  }

  /* ------------------------------------------------------------ the map's toolbar */
  function tools(what = "box") {
    const saving = canSave(), dirty = moved();
    const grab = `Drag a ${what} anywhere, or focus it and press an arrow key to nudge it a quarter of a cell (Shift and an arrow key: a whole cell). It stays where you put it; it stops short of another box rather than cover it.`;
    const hint = saving ? `Drag a ${what} anywhere or use the arrow keys (Shift for a whole cell). Saved to the plan.` : `Drag a ${what} anywhere or use the arrow keys (Shift for a whole cell). Changes stay in this browser.`;
    toolsFor = what;
    return h("span", { class: "tool-unit layout-tools", title: `${grab} ${saving ? "A move is saved to the plan for everyone." : "A move stays in this browser. To share it, download the layout and send it to the plan's owner."}` },
      h("span", { class: "tool-label sep" }, "Arrange"),
      h("button", { class: "chip", "data-layout": "reset", disabled: dirty ? null : true, title: "Put every box back where this page was built with it", onclick: reset }, "Reset layout"),
      saving ? null : h("button", { class: "chip", "data-layout": "copy", title: "Copy the layout, to send to the plan's owner", onclick: copy }, "Copy layout"),
      saving ? null : h("button", { class: "chip", "data-layout": "download", title: "Download the layout as a file, to send to the plan's owner", onclick: download }, "Download layout"),
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
  return { cell, cells, blocker, check, verdict, landing, along, drag, endDrag, drop, move, moveToward, step, clusterAt, placeClusters, reset, copy, download, tools, boot, say, moved, canSave, net,
    get live() { return live; }, get note() { return note; }, layoutJson, snapshot, restore, setCopy: (fn) => { copyFn = fn; }, KIND: kindOf, FRAME, BOX: { w: F.boxW, h: F.boxH }, GAP: F.gap, STEP, tidy };
})();
