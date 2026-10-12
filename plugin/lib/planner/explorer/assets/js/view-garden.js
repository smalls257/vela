/* Why it is this way: every recorded decision grown as a plant on a specimen sheet. What was picked grows on as the
   living leader; the options turned down are pruned branches, each with the reason it was cut; items whose own
   History repeats the decision are twigs; open questions it still waits on are buds in their lamp colour; answered
   ones are flowers. Every part comes from a typed field (asks_data.decisions): an Options considered line, an ADR's
   Alternatives table and Assumptions section, and Blocks lines. Prose that merely mentions a decision is not drawn.
   Ported from prototypes/gallery/asks/garden.html. */
const Garden = (() => {
  const trees = [...D.garden.trees, ...D.garden.bare];
  let current = Math.max(0, trees.findIndex((t) => t.adr));
  const sessionTitle = (id) => (D.sessions[id] && D.sessions[id].title) || id;
  function treeTitle(t) { const w = t.carriedBy[0]; return w.type === "concern" && w.under ? `${w.pageTitle}, ${w.under}` : t.picked.label; }
  function recordedOn(t) {
    const seen = new Set(), out = [];
    for (const w of t.carriedBy) { const label = w.item || (w.under ? `${w.pageTitle}, ${w.under}` : w.pageTitle); if (!seen.has(label)) { seen.add(label); out.push({ label, w }); } }
    return out;
  }
  function deciders(t) {
    const by = new Set(), conf = new Set(), sessions = new Set(); let overrides = 0;
    for (const w of t.carriedBy) {
      w.decidedBy.forEach((x) => by.add(x)); w.confirmedBy.forEach((x) => conf.add(x));
      w.decision.forEach((x) => { const m = x.match(/^\d{4}-\d{2}-\d{2}-[a-z0-9-]+/); if (m) sessions.add(m[0]); });
      overrides += w.overrides || 0;
    }
    return { by: [...by], conf: [...conf], sessions: [...sessions], overrides, owner: t.carriedBy.map((w) => w.owner).find(Boolean) || "" };
  }
  /* A reader's decision the owner has not reviewed: on the decision record, or on any page or item that carries it. */
  function pendingOf(t) {
    const keys = [t.adr && t.adr.key, ...t.carriedBy.flatMap((w) => [w.key, w.page])].filter(Boolean);
    const hit = keys.find((k) => E[k] && E[k].pending);
    return hit ? E[hit].pending : null;
  }
  const staked = (t) => { const d = deciders(t); return d.overrides > 0 && !d.conf.length; };
  function wrapWords(text, n) { const words = String(text).split(/\s+/), out = []; let cur = ""; for (const w of words) { if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); } if (cur) out.push(cur); return out; }
  const clip = (lines, max) => { if (lines.length <= max) return lines; const l = lines.slice(0, max); l[max - 1] = l[max - 1].replace(/[,;.]?$/, "…"); return l; };
  function rng(seed) { let x = 2166136261; for (const c of seed) x = Math.imul(x ^ c.charCodeAt(0), 16777619); return () => { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return ((x >>> 0) % 10000) / 10000; }; }
  function bez(p0, p1, p2, p3, t) { const m = 1 - t; return [m * m * m * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t * t * t * p3[0], m * m * m * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t * t * t * p3[1]]; }
  function taper(c, w0, w1, n = 28) {
    const pts = [], L = [], R = [];
    for (let i = 0; i <= n; i++) pts.push(bez(...c, i / n));
    for (let i = 0; i <= n; i++) {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1, w = (w0 + (w1 - w0) * Math.pow(i / n, 0.8)) / 2;
      L.push([pts[i][0] - (dy / len) * w, pts[i][1] + (dx / len) * w]); R.push([pts[i][0] + (dy / len) * w, pts[i][1] - (dx / len) * w]);
    }
    const f = (p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
    return `M${f(L[0])} ` + L.slice(1).map((p) => "L" + f(p)).join(" ") + ` L${f(R[n])} ` + R.reverse().map((p) => "L" + f(p)).join(" ") + "Z";
  }
  const cpath = (c) => { const f = (p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`; return `M${f(c[0])} C${f(c[1])} ${f(c[2])} ${f(c[3])}`; };
  const leafPath = (len, wid) => `M0 0 C ${wid} ${-len * 0.25}, ${wid * 0.8} ${-len * 0.75}, 0 ${-len} C ${-wid * 0.8} ${-len * 0.75}, ${-wid} ${-len * 0.25}, 0 0Z`;
  function flower(g, x, y, r, rot) {
    const f = s("g", { transform: `translate(${x} ${y}) rotate(${rot})` }, g);
    for (let i = 0; i < 5; i++) s("ellipse", { rx: r * 0.5, ry: r, cy: -r * 0.95, transform: `rotate(${i * 72})`, fill: "#e5b02b", stroke: "#b8861a", "stroke-width": 0.6 }, f);
    s("circle", { r: r * 0.48, fill: "#8a5f0e" }, f);
    return f;
  }
  function bud(g, x, y, k, rot, colour) {
    const b = s("g", { transform: `translate(${x} ${y}) rotate(${rot})` }, g);
    s("path", { d: `M0 0 C ${k * 0.7} ${-k * 0.5}, ${k * 0.55} ${-k * 1.25}, 0 ${-k * 1.7} C ${-k * 0.55} ${-k * 1.25}, ${-k * 0.7} ${-k * 0.5}, 0 0Z`, fill: colour }, b);
    s("path", { d: `M0 ${-k * 0.1} C ${k * 0.25} ${-k * 0.6}, ${k * 0.2} ${-k * 1.2}, 0 ${-k * 1.6}`, stroke: "rgba(255,255,255,.55)", "stroke-width": k * 0.12, fill: "none", "stroke-linecap": "round" }, b);
    s("path", { d: `M0 0 C ${k * 0.45} ${-k * 0.1}, ${k * 0.6} ${-k * 0.45}, ${k * 0.5} ${-k * 0.7} M0 0 C ${-k * 0.45} ${-k * 0.1}, ${-k * 0.6} ${-k * 0.45}, ${-k * 0.5} ${-k * 0.7}`, stroke: "#3b6a33", "stroke-width": k * 0.2, fill: "none", "stroke-linecap": "round" }, b);
    return b;
  }
  /* Lay out one plant in its own space: base at (0,0), growing up. Seeded by the tree's own ID, so it never changes shape. */
  function layout(t, H) {
    const r = rng(t.id + t.picked.label), lean = (r() - 0.5) * 60;
    const stem = [[0, 0], [lean * 0.2, -H * 0.35], [lean * 1.1 + (r() - 0.5) * 30, -H * 0.7], [lean, -H]];
    const P = { stem, branches: [], twigs: [], buds: [], blooms: [] }, nRej = t.rejected.length;
    t.rejected.forEach((o, i) => {
      const side = i % 2 ? 1 : -1, at = 0.12 + (nRej > 1 ? i * (0.22 / (nRej - 1)) : 0.08) + r() * 0.04, p0 = bez(...stem, at);
      const len = H * (0.34 + r() * 0.08), ang = ((60 + r() * 12) * Math.PI) / 180;
      const p3 = [p0[0] + side * Math.sin(ang) * len, p0[1] - Math.cos(ang) * len * 0.75];
      P.branches.push({ o, side, c: [p0, [p0[0] + side * len * 0.25, p0[1] - len * 0.12], [p3[0] - side * len * 0.25, p3[1] + len * 0.05], p3] });
    });
    const items = recordedOn(t), twigs = items.length > 1 ? items : [];
    twigs.forEach((it, i) => {
      const side = i % 2 ? 1 : -1, at = 0.5 + (twigs.length > 1 ? i * (0.42 / (twigs.length - 1)) : 0.1) + (r() - 0.5) * 0.03, p0 = bez(...stem, Math.min(at, 0.95));
      const len = 64 + r() * 52 - i * 2, lift = 0.35 + r() * 0.45, p3 = [p0[0] + side * len, p0[1] - len * lift];
      P.twigs.push({ it, side, c: [p0, [p0[0] + side * len * 0.35, p0[1] + 2 - r() * 8], [p3[0] - side * len * (0.2 + r() * 0.2), p3[1] + 12 * r()], p3], rot: side * (55 + r() * 35) });
    });
    t.buds.forEach((id, i) => {
      const n = t.buds.length, spread = Math.min(1, n / 4), fan = n > 3 ? 150 : 110, ang = ((-fan / 2 + (n > 1 ? i * (fan / (n - 1)) : fan / 2)) * spread * Math.PI) / 180;
      const tip = stem[3], len = 38 + (i % 2) * 26 + (n > 3 ? 10 : 0);
      P.buds.push({ id, c: [tip, [tip[0] + Math.sin(ang) * len * 0.3, tip[1] - len * 0.5], [tip[0] + Math.sin(ang) * len * 0.9, tip[1] - Math.cos(ang) * len * 0.8], [tip[0] + Math.sin(ang) * len, tip[1] - Math.cos(ang) * len]], ang });
    });
    t.leaves.forEach((id, i) => {
      const n = t.leaves.length, at = 0.3 + (n > 1 ? i / (n - 1) : 0.5) * 0.26, p = bez(...stem, at), side = i % 2 ? 1 : -1;
      P.blooms.push({ id, at, x: p[0] + side * (26 + (i % 3) * 14), y: p[1] - 10 - (i % 3) * 7 });
    });
    return P;
  }
  let uid = 0;
  const grow = (path, len, delay, dur) => { if (reducedMotion()) return; path.style.strokeDasharray = len; path.style.strokeDashoffset = len; path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: dur, delay, fill: "forwards", easing: "cubic-bezier(.3,.6,.2,1)" }); };
  const pop = (node, delay) => { if (reducedMotion()) return; node.classList.add("grow"); node.animate([{ transform: "scale(0)", opacity: 0 }, { transform: "scale(1.12)", opacity: 1, offset: 0.7 }, { transform: "scale(1)", opacity: 1 }], { duration: 520, delay, fill: "backwards", easing: "ease-out" }); };
  function stemShape(g, c, w0, w1, fill, delay, dur, defs, id) {
    const mask = s("mask", { id, maskUnits: "userSpaceOnUse", x: -3000, y: -3000, width: 6000, height: 6000 }, defs);
    const m = s("path", { d: cpath(c), stroke: "#fff", "stroke-width": Math.max(w0, w1) * 3 + 8, fill: "none", "stroke-linecap": "round" }, mask);
    const shape = s("path", { d: taper(c, w0, w1), fill, mask: `url(#${id})` }, g);
    let len = 400;
    try { len = m.getTotalLength(); } catch (e) { console.warn("[garden] stem not laid out yet, growing over a nominal length:", e.message); }
    grow(m, len + 20, delay, dur);
    return shape;
  }
  const budColour = (id) => { const lv = unknownLevel(id); return lv === "warning" ? "#ff5a48" : lv === "caution" ? "#f0a21a" : "#c3456c"; };
  function drawPlant(svg, t, x, y, scale, labels, defs) {
    const g = s("g", { transform: `translate(${x} ${y}) scale(${scale})` }, svg);
    const H = labels ? 455 : 470, P = layout(t, t.bare ? H * 0.55 : H), id = t.id + (labels ? "s" : "b") + uid++;
    s("ellipse", { cx: 0, cy: 6, rx: 92, ry: 9, fill: "#c9cfbb", opacity: 0.8 }, g);
    s("path", { d: "M-90 4 C-40 -3 40 -3 90 4", stroke: "#8f9a80", "stroke-width": 1.5, fill: "none", opacity: 0.7 }, g);
    const rg = rng(t.id + "grass");
    for (let i = 0; i < 9; i++) { const gx = -80 + i * 20 + rg() * 8; if (Math.abs(gx) < 14) continue; s("path", { d: `M${gx} 3 q ${2 + rg() * 3} -8 ${4 + rg() * 5} -${10 + rg() * 9}`, stroke: "#7e9a62", "stroke-width": 1.2, fill: "none", opacity: 0.8 }, g); }
    if (staked(t)) {
      const sx = 30, top = -Math.min(H * 0.55, 300), stk = s("g", { class: "part" }, g);
      s("path", { d: `M${sx} 14 L${sx + 3} ${top}`, stroke: "#b59658", "stroke-width": 5, "stroke-linecap": "round" }, stk);
      const tie = bez(...P.stem, 0.42);
      s("path", { d: `M${tie[0]} ${tie[1]} Q ${(tie[0] + sx) / 2} ${tie[1] + 6} ${sx + 2} ${tie[1] - 2}`, stroke: "#6a5530", "stroke-width": 1.3, fill: "none" }, stk);
      stk._tip = () => `<b>Staked by an override</b>${deciders(t).overrides} override(s) let this be decided before its gates passed, and nobody has confirmed it since.`;
    }
    P.branches.forEach((b, i) => {
      const bg = s("g", { class: "part" }, g), fill = b.o.forNow ? "#9ea585" : "#8e8170", d = labels ? 500 + i * 220 : 0;
      stemShape(bg, b.c, 9, 4.2, fill, d, labels ? 700 : 1, defs, id + "b" + i);
      const tip = b.c[3], prev = b.c[2], ang = (Math.atan2(tip[1] - prev[1], tip[0] - prev[0]) * 180) / Math.PI;
      const cut = s("g", { transform: `translate(${tip[0]} ${tip[1]}) rotate(${ang})` }, bg);
      s("ellipse", { rx: 1.6, ry: 2.4, fill: "#d9ccb0", stroke: "#6a6152", "stroke-width": 0.7 }, cut);
      if (!b.o.forNow) s("path", { d: "M5 -9 L-3 9", stroke: "#6a6152", "stroke-width": 1.3, "stroke-linecap": "round" }, cut); else s("circle", { cx: 3, cy: 0, r: 3, fill: "#9aa27c" }, cut);
      if (labels) {
        pop(cut, d + 650);
        const lx = tip[0] + b.side * 14, anchor = b.side < 0 ? "end" : "start", tg = s("g", {}, bg);
        const t1 = s("text", { x: lx, y: tip[1] - 6, "text-anchor": anchor, class: "lab opt" }, tg), lines = clip(wrapWords(b.o.label, 26), 2);
        lines.forEach((ln, j) => { s("tspan", { x: lx, dy: j ? 19 : 0 }, t1).textContent = ln; });
        const t2 = s("text", { x: lx, y: tip[1] - 6 + lines.length * 19, "text-anchor": anchor, class: "lab why" }, tg);
        clip(wrapWords(b.o.forNow ? "set aside for now: " + (b.o.reason || "no reason recorded") : "cut: " + (b.o.reason || "no reason recorded"), 32), 3).forEach((ln, j) => { s("tspan", { x: lx, dy: j ? 17 : 0 }, t2).textContent = ln; });
        if (!reducedMotion()) tg.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, delay: d + 700, fill: "backwards" });
      }
      bg._tip = () => `<b>${esc(b.o.label)}</b>${b.o.forNow ? "Set aside for now, kept as a fallback" : "Rejected"}: ${esc(b.o.reason || "no reason recorded")}.`;
    });
    const sg = s("g", { class: "part" }, g);
    stemShape(sg, P.stem, t.bare ? 8 : 12, 3, "#3b6a33", 0, labels ? 1100 : 1, defs, id + "s");
    s("path", { d: cpath(P.stem), stroke: "#6f9b4c", "stroke-width": 1.4, fill: "none", opacity: 0.55, transform: "translate(-1.6 0)" }, sg);
    sg._tip = () => `<b>${esc(t.picked.label)}</b>${t.picked.condition ? `<i>${esc(t.picked.condition)}</i><br>` : ""}${esc(shorten(t.adr ? t.adr.decision : t.carriedBy[0].text, 260))}`;
    const rl = rng(t.id + "leaf"), nLeaves = t.bare ? 2 : 5;
    for (let i = 0; i < nLeaves; i++) {
      const at = 0.16 + i * (0.64 / nLeaves) + rl() * 0.05, p = bez(...P.stem, at), side = i % 2 ? 1 : -1, rot = side * (52 + rl() * 18);
      const lf = s("path", { d: leafPath(30 + rl() * 12, 9), fill: i % 2 ? "#5d8b45" : "#4c7a3b", transform: `translate(${p[0]} ${p[1]}) rotate(${rot})`, opacity: 0.9 }, g);
      if (labels) pop(lf, 300 + at * 900);
    }
    P.twigs.forEach((tw, i) => {
      const tg = s("g", { class: "part" }, g), d = labels ? 900 + i * 110 : 0;
      stemShape(tg, tw.c, 3.4, 1.4, "#3b6a33", d, labels ? 420 : 1, defs, id + "t" + i);
      const tip = tw.c[3], lf = s("g", { transform: `translate(${tip[0]} ${tip[1]}) rotate(${tw.rot})` }, tg);
      s("path", { d: leafPath(30, 10), fill: "#6f9b4c", stroke: "#3b6a33", "stroke-width": 0.8 }, lf);
      s("path", { d: leafPath(22, 7), fill: "#5d8b45", transform: `rotate(${-tw.side * 50})` }, lf);
      if (labels) { pop(lf, d + 380); const tx = s("text", { x: tip[0] + tw.side * 30, y: tip[1] + 5, "text-anchor": tw.side < 0 ? "end" : "start", class: "lab item" }, tg); tx.textContent = tw.it.label; }
      tg._tip = () => `<b>${esc(tw.it.label)}</b>Its History carries this decision. State: ${esc(tw.it.w.state || "not set")}.`;
      tg._key = tw.it.w.key;
    });
    P.blooms.forEach((b, i) => {
      const fg = s("g", { class: "part" }, g), base = bez(...P.stem, b.at);
      s("path", { d: `M${base[0]} ${base[1]} Q ${(base[0] + b.x) / 2} ${b.y + 6} ${b.x} ${b.y}`, stroke: "#4c7a3b", "stroke-width": 1.3, fill: "none" }, fg);
      const f = flower(fg, b.x, b.y, 5.2, i * 23); if (labels) pop(f, 1300 + i * 70);
      fg._tip = () => tipUnknown(b.id); fg._key = b.id;
    });
    P.buds.forEach((b, i) => {
      const bg = s("g", { class: "part" }, g);
      s("path", { d: cpath(b.c), stroke: "#3b6a33", "stroke-width": 2, fill: "none", "stroke-linecap": "round" }, bg);
      const tip = b.c[3], bd = bud(bg, tip[0], tip[1], 11, (b.ang * 180) / Math.PI, budColour(b.id));
      if (labels) {
        pop(bd, 1500 + i * 120);
        const side = Math.sin(b.ang) < 0 || (Math.abs(Math.sin(b.ang)) < 0.01 && i % 2) ? -1 : 1;
        const col = P.buds.filter((q2, j) => j < i && ((Math.sin(q2.ang) < 0 || (Math.abs(Math.sin(q2.ang)) < 0.01 && j % 2)) ? -1 : 1) === side).length;
        const lx = P.stem[3][0] + side * 120, ly = P.stem[3][1] - 70 + col * 21, bt = [tip[0] + Math.sin(b.ang) * 16, tip[1] - Math.cos(b.ang) * 16];
        s("path", { d: `M${bt[0]} ${bt[1]} L${lx - side * 6} ${ly - 4}`, stroke: "#c98aa0", "stroke-width": 0.8, fill: "none" }, bg);
        s("text", { x: lx, y: ly, "text-anchor": side < 0 ? "end" : "start", class: "lab bud" }, bg).textContent = `${b.id}, ${day(ASK[b.id] ? ASK[b.id].askBy : "")}`;
      }
      bg._tip = () => tipUnknown(b.id); bg._key = b.id;
    });
    if (labels) {
      const tip = P.stem[3], lines = clip(wrapWords(treeTitle(t), 34), 2);
      const crownTop = P.buds.length ? Math.max(...P.buds.map((b) => Math.cos(b.ang) * 70)) + 40 : 30;
      const tx = s("text", { x: tip[0], y: tip[1] - crownTop - (lines.length - 1) * 24, "text-anchor": "middle", class: "lab title" }, g);
      lines.forEach((ln, j) => { s("tspan", { x: tip[0], dy: j ? 24 : 0 }, tx).textContent = ln; });
      if (!reducedMotion()) tx.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 600, delay: 1000, fill: "backwards" });
    }
    return g;
  }
  function tipUnknown(id) {
    const u = ASK[id]; if (!u) return id;
    return `<b>${id} ${esc(E[id] ? E[id].title : "")}</b>${esc(u.state === "open" ? u.question : u.outcome || u.question)}<br><span class="muted">${u.state === "open" ? `Open. Ask ${esc(u.ask.name)}${u.ask.inferred ? " (a guess)" : ""} by ${day(u.askBy)}.` : "Answered."}</span>`;
  }
  function bindTips(svg) {
    svg.addEventListener("pointermove", (e) => { const p = e.target.closest(".part"); if (p && p._tip) showTip(e, p._tip()); else hideTip(); });
    svg.addEventListener("pointerleave", hideTip);
    svg.addEventListener("click", (e) => { const p = e.target.closest(".part"); if (p && p._key) go(p._key, {}); });
  }

  function render(main) {
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Why it is this way"),
      h("p", {}, "Each decision grown as a plant. What was picked grows on; options turned down are pruned, with the reason they were cut. Open questions it still waits on are buds, in their lamp colour; answered ones are flowers.")),
      h("div", { class: "spacer" }), h("div", { class: "garden-key", html:
        `<span><svg width="22" height="14"><path d="M1 12 C8 10 14 6 21 2" stroke="#6f9b4c" stroke-width="4" fill="none" stroke-linecap="round"/></svg>picked</span>
         <span><svg width="22" height="14"><path d="M1 12 C8 10 13 7 18 5" stroke="#a89a86" stroke-width="3" fill="none"/><path d="M16 1 L21 8" stroke="#d9ccb0" stroke-width="1.5"/></svg>pruned</span>
         <span><svg width="14" height="14"><path d="M7 1 C11 5 11 10 7 13 C3 10 3 5 7 1Z" fill="#f0a21a"/></svg>open question</span>
         <span><svg width="16" height="16"><g transform="translate(8 8)" fill="#e5b02b"><circle r="2.4" fill="#9a6c10"/><ellipse rx="2.3" ry="4.6" cy="-4.4"/><ellipse rx="2.3" ry="4.6" cy="-4.4" transform="rotate(72)"/><ellipse rx="2.3" ry="4.6" cy="-4.4" transform="rotate(144)"/><ellipse rx="2.3" ry="4.6" cy="-4.4" transform="rotate(216)"/><ellipse rx="2.3" ry="4.6" cy="-4.4" transform="rotate(288)"/></g></svg>answered</span>` })));
    if (!trees.length) { main.append(emptyState("No decision records its options yet.", "An Options considered line, or a decision record with an Alternatives considered table, grows here.", "/planner:shape")); return; }
    const sheetWrap = h("div", { class: "garden-main" });
    const sheet = s("svg", { class: "sheet", viewBox: "0 0 1000 720", preserveAspectRatio: "xMidYMid meet", role: "img", "aria-label": "The selected decision drawn as a plant" });
    const card = h("aside", { class: "label-card", id: "label-card", "aria-live": "polite" });
    const tex = Assets.texture("garden");
    const paper = h("div", { class: "sheet-paper" + (tex ? " textured" : ""), style: tex ? `--texture:url("${tex}")` : null }, sheet);
    sheetWrap.append(paper, card);
    const bedBox = h("footer", { class: "bed" }, h("div", { class: "bedline", id: "bedline" }));
    const bed = s("svg", { class: "bed-svg", preserveAspectRatio: "xMinYMid meet", role: "list", "aria-label": "Every decision with its options recorded" }, bedBox);
    main.append(sheetWrap, bedBox);
    bindTips(sheet); bindTips(bed);
    renderBed(bed);
    show(current);
  }
  function show(i) {
    current = i;
    const t = trees[i], sheet = $(".sheet");
    if (!sheet) return;
    sheet.innerHTML = "";
    const defs = s("defs", {}, sheet);
    s("rect", { x: 14, y: 10, width: 972, height: 700, fill: "none", stroke: "#b9c0ad", "stroke-width": 1 }, sheet);
    drawPlant(sheet, t, 500, 676, 1, true, defs);
    card(t);
    $$(".plot").forEach((p, j) => p.classList.toggle("current", j === i));
    Sound.bell(i);
  }
  function card(t) {
    const d = deciders(t), w = t.carriedBy[0], on = recordedOn(t), box = $("#label-card");
    const prose = t.adr ? t.adr.decision : w.type === "concern" ? t.picked.label : w.text;
    box.innerHTML = "";
    box.append(h("div", { class: "num" }, t.bare ? "Decided, no options recorded" : t.fromTable ? `Decision record ${t.adr.id}` : `Decision ${t.id.replace("D", "")} of ${D.garden.trees.length}`),
      h("h2", {}, treeTitle(t)), prose ? h("p", { class: "prose" }, shorten(prose, 420)) : h("p", { class: "prose muted" }, "The page gives no prose for this decision."),
      h("dl", {},
        t.picked.condition ? [h("dt", {}, "On condition"), h("dd", {}, t.picked.condition.replace(/^on condition that\s*/i, ""))] : null,
        h("dt", {}, "Pruned"), h("dd", {}, t.rejected.length ? t.rejected.map((o) => o.label + (o.forNow ? " (kept as a fallback)" : "")).join("; ") : "nothing recorded"),
        h("dt", {}, "Decided by"), h("dd", {}, d.by.length ? d.by.join("; ") : d.owner ? d.owner + ", the owner" : "not recorded"),
        pendingOf(t) ? [h("dt", {}, "Review"), h("dd", {}, pendingPill(pendingOf(t)), ` ${pendingOf(t).by}, ${pendingOf(t).date}: the owner has not reviewed it`)] : null,
        h("dt", {}, "Confirmed"), h("dd", {}, d.conf.length ? d.conf.join("; ") : h("span", { class: "warn" }, `not yet${d.overrides ? `, and it stands on ${plural(d.overrides, "override")}` : ""}`)),
        h("dt", {}, "Where"), h("dd", {}, d.sessions.map(sessionTitle).join("; ") || (w.status || "no session linked")),
        h("dt", {}, "Recorded on"), h("dd", {}, [...new Set((t.adr ? [t.adr.key] : []).concat(on.map((o) => o.w.key)))].map((k) => refChip(k))),
        h("dt", {}, "Waiting on"), h("dd", {}, t.buds.length ? t.buds.map((id) => refChip(id)) : "no open question names it"),
        h("dt", {}, "Answered"), h("dd", {}, t.leaves.length ? t.leaves.map((id) => refChip(id)) : "none recorded")),
      h("p", { class: "note-small" }, t.fromTable ? "Drawn from the decision record's Alternatives considered table and the questions its Assumptions section links. Their state comes from the unknowns page." :
        "Pruned branches are the History's Options considered line. Twigs are the items whose own History repeats it. Buds and flowers are unknowns whose Blocks line names the page or item."));
    go(t.adr ? t.adr.key : w.key, { reset: true, quiet: true });
  }
  function group(t) { return { "initiative-section": "Goals and strategy", index: "Apps", "app-building-blocks": "Apps", concern: "Concerns", epic: "Epics", flow: "Flows", decision: "Decision records" }[t.carriedBy[0].type] || "Other"; }
  function renderBed(bed) {
    bed.innerHTML = "";
    const W = 120, defs = s("defs", {}, bed);
    const groups = [...new Set(trees.map(group))].length;
    bed.setAttribute("viewBox", `0 0 ${trees.length * W + groups * 28 + 60} 140`);
    let prev = "", x = 30;
    trees.forEach((t, i) => {
      const grp = group(t);
      if (grp !== prev) { if (prev) x += 28; s("text", { x: x + 4, y: 136, class: "lab small" }, bed).textContent = grp; prev = grp; }
      const g = s("g", { class: "plot", tabindex: 0, role: "listitem", "aria-label": `${t.id}: ${treeTitle(t)}` }, bed);
      s("rect", { x, y: 0, width: W - 10, height: 122, rx: 4, class: "hit" }, g);
      drawPlant(g, t, x + (W - 10) / 2, 100, 0.18, false, defs);
      s("text", { x: x + (W - 10) / 2, y: 117, "text-anchor": "middle", class: "pid" }, g).textContent = `${t.adr ? t.adr.id : t.id}${t.buds.length ? `, ${t.buds.length} open` : ""}${pendingOf(t) ? ", pending" : ""}`;
      if (pendingOf(t)) {  // a ring with clock hands, and the word above: never colour alone
        const ring = s("g", { class: "pend-ring", transform: `translate(${x + W - 24} 14)` }, g);
        s("circle", { r: 8 }, ring); s("path", { d: "M0 -4.5V0H3.5" }, ring);
        s("title", {}, ring).textContent = "Pending approval: a reader decided this and the owner has not reviewed it";
      }
      g.addEventListener("click", () => show(i));
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(i); } });
      g.addEventListener("pointerenter", (e) => showTip(e, `<b>${esc(treeTitle(t))}</b>${plural(t.rejected.length, "option")} pruned, ${plural(t.buds.length, "open question")}`));
      g.addEventListener("pointerleave", hideTip);
      x += W;
    });
    const pruned = trees.reduce((n, t) => n + t.rejected.length, 0), waiting = new Set(trees.flatMap((t) => t.buds)).size;
    $("#bedline").innerHTML = `<b>The bed</b> <span>${plural(trees.length, "decision")}, ${plural(pruned, "option")} pruned, ${plural(waiting, "open question")} still held by them.${D.garden.bare.length ? ` ${plural(D.garden.bare.length, "decided page")} record no options and grow as bare stems.` : ""} Repeated lines are drawn once. Click a plant to lift it onto the sheet; the arrow keys walk the bed.</span>`;
  }
  document.addEventListener("keydown", (e) => {
    if (App.view !== "garden" || (e.target.closest && e.target.closest("input")) || !trees.length) return;
    if (e.key === "ArrowRight") show((current + 1) % trees.length);
    if (e.key === "ArrowLeft") show((current - 1 + trees.length) % trees.length);
  });
  function showFor(key) {
    const i = trees.findIndex((t) => (t.adr && t.adr.key === key) || t.carriedBy.some((w) => w.key === key || w.page === key) || t.buds.includes(key) || t.leaves.includes(key));
    if (i >= 0) { current = i; if (App.view === "garden") show(i); }
    return i;
  }
  function here() {
    if (App.view !== "garden" || !trees[current]) return null;
    const keys = trees[current].carriedBy.map((w) => w.key).flatMap(mapAnchors);
    return keys.length ? keys : null;
  }
  return { render, show, showFor, here, highlight: (k) => { if (showFor(k) >= 0 && App.view === "garden") {} }, trees };
})();
View("garden", { label: "Why", title: "Why it is this way: the decisions, grown as plants", render: Garden.render, here: Garden.here, highlight: Garden.highlight,
  count: () => String(Garden.trees.length) });
