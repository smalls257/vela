/* Waiting for a decision: the things the plan is ready to decide, or one answer away from ready, by who runs the grill. A
   card says what deciding it would settle, where the item stands, what it holds up and who owns it. Picking one opens it
   in the right-hand panel with two prompts to hand to Claude: "Settle <name>" for a lead who is sure, and
   `/vela:grill <name>` to test it first. A batch builds one grill prompt for several, in the order that unblocks the most.

   The Violation this exists to prevent is a Leaky Narrative on the page: whether an item is ready, whether the lead already
   said yes, who owns it and what it waits on are decided in vela/grills.py and arrive as fields. This file only filters
   and draws them. It also prevents a wall of everyone's work: "Mine" follows the person in "Viewing as", and the others'
   grills sit one click away behind a count, so the top bar, the sidebar and Needs you say how many are for you.

   Who "Mine" means is Viewer's (viewer.js), the one answer Needs you and the badge read too; this view has a menu that writes
   to it, and no lookup of its own. With nobody, it shows everyone's. Routes: #s=grills, #s=grills&as=agent-lead&scope=all&ready. */
const Grills = (() => {
  const rows = (D.grills && D.grills.rows) || [];
  const BY = Object.fromEntries(rows.map((r) => [r.id, r]));
  const BY_KEY = {};
  for (const r of rows) if (!BY_KEY[r.key]) BY_KEY[r.key] = r;
  const keyOf = (r) => "grill:" + r.id;
  const GROUPS = [
    ["said-yes", "You already said yes", "settle it, or grill it", "yes", "Items you said yes to and didn't settle. Settle one when you're sure, or grill it to test it first."],
    ["ready", "Ready to decide", "nothing in the way", "ready", "Items with a preferred option and no open question in the way."],
    ["one-away", "One thing away", "not ready yet", "wait", "Items with exactly one thing in the way. Each says what it is and who owes it."],
  ];
  const GROUP_ORDER = GROUPS.map(([id]) => id);
  const st = { scope: "mine", owner: "", app: "", holds: "", readyOnly: false, open: "", batch: [], copied: "" };
  const lower = (t) => String(t || "").toLowerCase();
  const handleOf = (t) => { const x = String(t || "").trim(); return x && x !== "*" && !x.startsWith("@") ? "@" + x : x; };

  /* ------------------------------------------------------------ who is viewing */
  const viewerHandles = () => Viewer.viewer().handles;
  const hasViewer = () => Viewer.hasPerson();
  const isYou = (handle) => Viewer.isYou(handle);
  const isMine = (r) => r.owner.some(isYou);
  const isAsked = (r) => !isMine(r) && r.join.some(isYou);
  const viewerName = () => (hasViewer() ? personName(viewerHandles()[0]) : "Everyone");
  const scopeNow = () => (hasViewer() ? st.scope : "all");
  const SCOPE_TEST = { mine: isMine, join: isAsked, all: () => true };
  const readyNow = (r) => r.group !== "one-away";
  const forYou = () => (hasViewer() ? rows.filter(isMine) : rows);
  function setViewer(handle) {
    st.scope = "mine"; st.owner = "";
    Viewer.set(handle);  // the one setting; it redraws the bar and the sidebar, and this view redraws itself below
    if (App.view === "grills") refresh();
  }

  /* ------------------------------------------------------------ the filters */
  const kindWord = (r) => (ent(r.key) ? KIND_WORD[ent(r.key).kind] || "Item" : "Item");
  const passesFilters = (r) => (!st.owner || r.owner.some((o) => lower(o) === lower(st.owner)))
    && (!st.app || r.apps.includes(st.app)) && (!st.holds || r.holdsUp.includes(st.holds)) && (!st.readyOnly || readyNow(r));
  const visible = () => rows.filter((r) => SCOPE_TEST[scopeNow()](r) && passesFilters(r));
  const countOf = (scope) => rows.filter(SCOPE_TEST[scope]).length;
  const options = (pick) => [...new Set(rows.flatMap(pick))];
  const people = () => [...new Set([...rows.flatMap((r) => [...r.owner, ...r.join]), ...Object.keys((D.onboard && D.onboard.roles) || {}).map(handleOf)])].sort((a, b) => cmp(personName(a), personName(b)));
  const youOrName = (handle) => (isYou(handle) ? "you" : personName(handle));

  /* ------------------------------------------------------------ the prompt for Claude */
  const SETTLE_PICKED = /\s*\(picked\)\s*$/i;
  function settleLine(text) {
    if (SETTLE_PICKED.test(text)) return `Proposed: ${text.replace(SETTLE_PICKED, "")}`;
    const [what, why] = text.split(/:\s*rejected,?\s*/i);
    return why !== undefined ? `Set aside: ${upFirst(what)}, because ${why.replace(/\.$/, "")}` : upFirst(text);
  }
  /* One line for a card: the option on the table and how many were set aside, or the one thing the item says it is. */
  function settleSummary(r) {
    const picked = r.settles.find((s) => SETTLE_PICKED.test(s)), others = r.settles.filter((s) => s !== picked);
    if (!picked) return settleLine(r.settles[0]).replace(/\.$/, "");
    return `${settleLine(picked)}${others.length ? `. ${plural(others.length, "other option")} set aside` : ""}`;
  }
  const listWords = (names, cap = 4) => {
    const shown = names.slice(0, cap), more = names.length - shown.length;
    const all = more > 0 ? [...shown, `${more} more`] : shown;
    return all.length > 1 ? `${all.slice(0, -1).join(", ")} and ${all[all.length - 1]}` : all[0] || "";
  };
  const holdsNames = (r) => r.holdsUp.map(titleOf);
  /* The prompt is plain words a person could have typed: the first line is the command with the item's name (the grill
     skill takes names, not IDs); the paragraph says what it settles, where it stands and what it holds up. */
  function promptBody(r) {
    const parts = [];
    if (r.settles.length) parts.push(`It settles: ${listWords(r.settles.map((s) => settleLine(s).replace(/\.$/, "")), 3)}.`);
    if (r.group === "said-yes") parts.push(`I said yes to this on ${dayYear(r.yes.date)}. Read my words back and confirm them before you decide.`);
    else if (r.group === "ready") parts.push("Nothing is in the way, so it's ready to decide.");
    else parts.push(`One thing is in the way: ${waitingSentence(r)} Start with a recap of that, then grill what is settled.`);
    if (r.holdsUp.length) parts.push(`It holds up ${listWords(holdsNames(r))}.`);
    const joiners = r.join.map(personName);
    if (joiners.length) parts.push(`${listWords(joiners)} ${joiners.length > 1 ? "have" : "has"} been asked to join, so check what they need to confirm.`);
    return parts.join(" ");
  }
  const prompt = (r) => `/vela:grill ${r.name}\n\n${promptBody(r)}`;
  /* The settle prompt is the same facts without the grill's last sentences: no slash command, so with no session running
     Claude opens whatever takes "settle an item" (the grill skill; the owner said to keep that default). To open a different skill, change SETTLE_OPENS_WITH and nothing else. */
  const SETTLE_OPENS_WITH = (r) => `Settle ${r.name}.`;
  function settleBody(r) {
    const parts = [];
    if (r.settles.length) parts.push(`It settles: ${listWords(r.settles.map((s) => settleLine(s).replace(/\.$/, "")), 3)}.`);
    if (r.group === "said-yes") parts.push(`I said yes to this on ${dayYear(r.yes.date)}. Read it back to me before you write it.`);
    else if (r.group === "ready") parts.push("Nothing is in the way, so it's ready to decide.");
    else parts.push(`One thing is in the way: ${waitingSentence(r)} Ask me about it first.`);
    if (r.holdsUp.length) parts.push(`It holds up ${listWords(holdsNames(r))}.`);
    const joiners = r.join.map(personName);
    if (joiners.length) parts.push(`${listWords(joiners)} ${joiners.length > 1 ? "have" : "has"} been asked to join, so check what they need to confirm.`);
    return parts.join(" ");
  }
  const settlePrompt = (r) => `${SETTLE_OPENS_WITH(r)}\n\n${settleBody(r)}`;
  function byUnblocked(list) { return list.slice().sort((a, b) => b.holdsUp.length - a.holdsUp.length || GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group) || cmp(a.name, b.name)); }
  function batchPrompt(list) {
    const ordered = byUnblocked(list);
    const lines = ordered.map((r, i) => `${i + 1}. ${r.name}. ${promptBody(r)}`);
    return `/vela:grill ${ordered.map((r) => r.name).join("; ")}\n\nGrill these in one session, in this order. The first holds up the most.\n\n${lines.join("\n\n")}`;
  }
  async function copy(text, what) {
    st.copied = text;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(text);
      else throw new Error("no clipboard");
      toast(`Copied ${what}. Paste it into Claude.`);
    } catch (e) {
      console.warn("[grills] the clipboard was not available:", e.message);
      toast(`This page can't use the clipboard. Select the ${what} text and copy it yourself.`);
    }
  }

  /* ------------------------------------------------------------ words for a card */
  const dueWords = (iso) => (isDate(iso) ? `, due ${day(iso)}` : "");
  const answerWords = (m) => {
    const who = m.ask || (m.owed_by[0] ? personName(m.owed_by[0]) : "");
    return `${who ? `${who}'s` : "an"} answer to "${m.question.replace(/\?$/, "")}"${dueWords(m.due)}`;
  };
  function waitingSentence(r) {
    const m = r.missing;
    if (!m || !m.rule) return "";
    return m.question ? `${answerWords(m)}. Then this is ready.` : m.plain;
  }
  const pillOf = (r) => (r.group === "said-yes" ? [`yes on ${day(r.yes.date)}`, "yes"] : r.group === "ready" ? ["ready", "ready"]
    : [r.missing && r.missing.question ? "waits on 1 answer" : "one thing away", "wait"]);
  function contextLine(r) {
    const c = CONTRACT[r.key], e = ent(r.key);
    const where = c ? `${titleOf(c.provider)} → ${c.consumers.map(titleOf).join(", ")}` : r.apps.length === 1 && e && e.kind !== "app" ? titleOf(r.apps[0]) : "";
    return [kindWord(r), where, r.state ? stateWord(r.state).toLowerCase() : ""].filter(Boolean).join(" · ");
  }
  function ownerLine(r) {
    const asked = isAsked(r);
    const joined = r.join.map(youOrName);
    return h("div", { class: "g-owner" }, "Owner: ", h("b", {}, listWords(r.owner.map(youOrName), 3) || "not recorded"),
      r.ownerSet ? h("span", { class: "muted", title: "Someone set the grill's owner; it isn't the item's own owner" }, " (set for this grill)") : null,
      joined.length ? ` · with ${listWords(joined)}` : null, asked ? [" · ", h("b", { class: "g-asked" }, "you're asked to join")] : null);
  }
  /* A chip that opens the thing in the panel: a button, so the keyboard has it. */
  function chipButton(key, text, title) {
    return h("button", { class: "g-chip", type: "button", "data-ref-chip": key, title: title || null, onclick: (ev) => { ev.stopPropagation(); DetailsPanel.show(key, { reset: true, quiet: true }); } }, text);
  }
  function holdChips(r) {
    const out = r.holdsUp.slice(0, 3).map((k) => chipButton(k, `holds up: ${titleOf(k)}`, `${titleOf(k)} waits on this`));
    if (r.holdsUp.length > 3) out.push(h("span", { class: "g-chip g-more" }, `+${r.holdsUp.length - 3} more`));
    if (r.sources.length) out.push(chipButton(r.sources[0], plural(r.sources.length, "source"), r.sources.map(titleOf).join(", ")));
    return out;
  }

  function card(r) {
    const [pillText, tone] = pillOf(r), key = keyOf(r), on = st.open === key;
    const open = () => select(key);
    const body = [h("div", { class: "g-row" }, h("div", {}, h("div", { class: "g-t" }, r.name), h("div", { class: "g-m" }, contextLine(r))),
      h("span", { class: `g-pill ${tone}` }, pillText)), ownerLine(r)];
    if (r.group !== "one-away" && r.settles.length) body.push(h("div", { class: "g-need" }, h("b", {}, "Settles: "), settleSummary(r)));
    if (r.group === "one-away") body.push(h("div", { class: "g-need" }, h("b", { class: "g-wait" }, r.missing.question ? "Waiting on: " : "In the way: "), waitingSentence(r)));
    if (r.openQuestion && r.openQuestion.question) body.push(h("div", { class: "g-need g-openq" }, h("b", {}, "Still open: "), `${answerWords(r.openQuestion)}. Settling it notes that.`));
    const chips = holdChips(r);
    return h("div", { class: "g-card" + (on ? " on" : ""), "data-grill": r.id, "data-group": r.group, "data-owner": r.owner.join(" "), onclick: open },
      h("button", { class: "g-open", type: "button", "aria-pressed": String(on), "aria-label": `${r.name}: ${pillText}. Show the details`, onclick: (ev) => { ev.stopPropagation(); open(); } }, ...body),
      chips.length ? h("div", { class: "g-chips" }, chips) : null);
  }

  /* ------------------------------------------------------------ the page */
  function viewerMenu() {
    const item = (id, label, say, run, checked) => ({ id, label, say, run, checked });
    return Menus.menu({ id: "grills-as", label: "Viewing as", current: viewerName(), extraClass: "g-as", items: () => [
      item("follow", "Follow my role", "The people the plan records for the role in the sidebar", () => setViewer(""), !Viewer.pick()),
      ...people().map((p) => item("p:" + p, personName(p), lower(p) === lower(Viewer.pick()) ? "Showing this person's grills" : null, () => setViewer(p), lower(Viewer.pick()) === lower(p))),
      item("everyone", "Everyone", "No one in particular: show every grill", () => setViewer("*"), Viewer.pick() === Viewer.EVERYONE)] });
  }
  function scopeChips() {
    if (!hasViewer()) return [h("span", { class: "g-scope-note muted" }, `Showing everyone's grills. Pick a person above to see theirs.`)];
    const scopes = [["mine", "Mine", "Grills you run"], ["join", "I'm asked to join", "Grills someone asked you to join"], ["all", "Everyone's", "Every grill that is waiting"]];
    return scopes.map(([id, label, title]) => h("button", { class: "chip g-scope" + (scopeNow() === id ? " on" : ""), type: "button", "aria-pressed": String(scopeNow() === id), "data-scope": id, title,
      onclick: () => { st.scope = id; refresh(); } }, label, h("span", { class: "g-n" }, String(countOf(id)))));
  }
  function select2(id, label, current, opts, onChange) {
    const sel = h("select", { class: "g-select", "data-filter": id, "aria-label": label, onchange: () => onChange(sel.value) },
      h("option", { value: "" }, `${label}: any`), ...opts.map(([v, t]) => h("option", { value: v, selected: v === current ? "" : null }, `${label}: ${t}`)));
    sel.value = current;
    return sel;
  }
  function filterBar() {
    const holds = options((r) => r.holdsUp).map((k) => [k, titleOf(k)]).sort((a, b) => cmp(a[1], b[1]));
    const apps = options((r) => r.apps).map((k) => [k, titleOf(k)]).sort((a, b) => cmp(a[1], b[1]));
    const owners = options((r) => r.owner).map((o) => [o, isYou(o) ? "you" : personName(o)]).sort((a, b) => cmp(a[1], b[1]));
    return h("div", { class: "g-bar" }, h("div", { class: "g-bar-top" }, viewerMenu(), h("div", { class: "g-scopes", role: "group", "aria-label": "Whose grills" }, scopeChips())),
      h("div", { class: "g-filters", role: "group", "aria-label": "Narrow the list" },
        select2("owner", "Owner", st.owner, owners, (v) => { st.owner = v; if (v) st.scope = "all"; refresh(); }),
        select2("app", "App", st.app, apps, (v) => { st.app = v; refresh(); }),
        select2("holds", "Holds up", st.holds, holds, (v) => { st.holds = v; refresh(); }),
        h("button", { class: "chip g-ready-only" + (st.readyOnly ? " on" : ""), type: "button", "aria-pressed": String(st.readyOnly), title: "Leave out the ones that still have something in the way", onclick: () => { st.readyOnly = !st.readyOnly; refresh(); } }, "Ready only")));
  }
  function summary(list) {
    const scope = scopeNow(), tile = (n, text, id) => h("div", { class: "g-tile", "data-tile": id }, h("b", {}, String(n)), text);
    const ready = list.filter(readyNow).length;
    if (!hasViewer()) return h("div", { class: "g-sum" }, tile(list.length, "waiting", "waiting"), tile(ready, "ready now", "ready"), tile(list.length - ready, "one thing away", "away"));
    const hidden = rows.length - countOf(scope === "all" ? "all" : scope);
    return h("div", { class: "g-sum" }, tile(countOf("mine"), "yours to run", "mine"), tile(countOf("join"), "you're asked to join", "join"), tile(ready, "ready now", "ready"),
      scope === "all" ? null : tile(hidden, "hidden: other owners' grills", "hidden"));
  }
  function otherOwners() {
    if (!hasViewer() || scopeNow() === "all") return null;
    const more = rows.length - countOf(scopeNow());
    if (!more) return null;
    return h("p", { class: "g-note" }, `${plural(more, "more grill")} ${more === 1 ? "belongs" : "belong"} to other owners. `,
      h("button", { class: "linkish g-show-all", type: "button", onclick: () => { st.scope = "all"; refresh(); } }, "Show everyone's"));
  }
  function groups(list) {
    const out = [];
    for (const [id, label, pill, tone, say] of GROUPS) {
      const here = list.filter((r) => r.group === id);
      if (!here.length) continue;
      out.push(h("section", { class: "g-group", "data-group": id }, h("h2", { title: say }, label, h("span", { class: `g-pill ${tone}` }, pill), h("span", { class: "g-gn" }, ` · ${here.length}`)), here.map(card)));
    }
    return out;
  }
  function batchBox() {
    const picked = st.batch.map((id) => BY[id]).filter(Boolean);
    if (!picked.length) return null;
    const ordered = byUnblocked(picked), text = batchPrompt(picked);
    return h("section", { class: "g-batch", "aria-label": "Batch of grills" },
      h("h2", {}, `Batch: ${plural(picked.length, "grill")}`, h("span", { class: "g-hint" }, " in the order that unblocks the most")),
      h("ol", { class: "g-batch-list" }, ordered.map((r) => h("li", {}, r.name, h("span", { class: "muted" }, r.holdsUp.length ? ` · holds up ${r.holdsUp.length}` : ""),
        h("button", { class: "linkish g-unbatch", type: "button", "aria-label": `Take ${r.name} out of the batch`, onclick: () => toggleBatch(r.id) }, "Remove")))),
      h("pre", { class: "g-prompt", "data-prompt": "batch" }, text),
      h("div", { class: "g-btns" }, h("button", { class: "btn g-primary", type: "button", "data-act": "copy-batch", onclick: () => copy(text, "the batch prompt") }, "Copy batch prompt"),
        h("button", { class: "btn", type: "button", "data-act": "clear-batch", onclick: () => { st.batch = []; refresh(); repaintPanel(); } }, "Clear the batch")));
  }
  function render(main) {
    main.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Waiting for a decision"),
      h("p", {}, "These are the things the plan is ready to decide, or nearly ready. Pick one to see what deciding it would settle and what it holds up. Then copy a prompt into Claude: settle it if you're sure, or grill it to test it first.")),
      h("div", { class: "spacer" })));
    if (!rows.length) { main.append(emptyState("Nothing is waiting for a decision.", "An item shows here once it has a preferred option and nothing in the way, or you said yes to it and didn't settle it.")); return; }
    main.append(h("div", { class: "g-wrap" }, h("div", { class: "g-barhost" }, filterBar()), h("div", { class: "g-stage" })));
    paint();
  }
  function paint() {
    const stage = $(".g-stage");
    if (!stage) return;
    const list = visible();
    stage.innerHTML = "";
    const problems = D.grills.problems && D.grills.problems.length ? h("p", { class: "g-problems muted" }, D.grills.problems.join(" ")) : null;
    stage.append(...[h("div", { class: "g-sumhost" }, summary(list)), batchBox(), ...(list.length ? groups(list) : [emptyNone()]), otherOwners(), problems].filter(Boolean));
  }
  function emptyNone() {
    const everyone = rows.length > 0 && scopeNow() !== "all";
    return h("div", { class: "g-none" }, h("b", {}, hasViewer() && scopeNow() === "mine" ? "No grill is waiting for you." : "Nothing matches."),
      " ", everyone ? "Others' grills are one click away. " : "Clear a filter to see more. ",
      everyone ? h("button", { class: "linkish", type: "button", onclick: () => { st.scope = "all"; st.owner = ""; st.app = ""; st.holds = ""; st.readyOnly = false; refresh(); } }, "Show everyone's") : null);
  }
  function refresh() {
    const host = $(".g-barhost");
    if (host) host.replaceChildren(filterBar());
    paint();
    syncRefocus();
  }
  function syncRefocus() {
    if (st.refocus) { const el = $(`.g-card[data-grill="${CSS.escape(st.refocus)}"] .g-open`); st.refocus = ""; if (el) el.focus({ preventScroll: true }); }
  }
  function select(key) {
    st.open = key; st.refocus = key.slice(6);
    DetailsPanel.show(key, { reset: true, quiet: true });
    paint(); syncRefocus();
    const on = $(".g-card.on");
    if (on) on.scrollIntoView({ block: "nearest" });
  }
  document.addEventListener("keydown", (ev) => {
    if (App.view !== "grills" || (ev.target.closest && ev.target.closest("input, select, textarea"))) return;
    const at = ev.target.closest && ev.target.closest(".g-open");
    if (!at || (ev.key !== "ArrowDown" && ev.key !== "ArrowUp")) return;
    const all = $$(".g-open"), next = all[all.indexOf(at) + (ev.key === "ArrowDown" ? 1 : -1)];
    if (next) { ev.preventDefault(); next.focus(); }
  });

  /* ------------------------------------------------------------ the batch */
  function toggleBatch(id) {
    const at = st.batch.indexOf(id);
    if (at >= 0) st.batch.splice(at, 1); else st.batch.push(id);
    if (App.view === "grills") paint();
    repaintPanel();
  }
  function repaintPanel() { Panel.render(); }

  /* ------------------------------------------------------------ one grill, in the right-hand panel */
  const bulletList = (items) => h("ul", { class: "g-list" }, items.map((t) => h("li", {}, t)));
  function standsLines(r) {
    const out = [];
    if (r.since && r.since.date) out.push(r.since.kept ? `${stateWord(r.state)} since ${dayYear(r.since.date)}` : `First named on ${dayYear(r.since.date)}`);
    else out.push(`${stateWord(r.state)}. Nobody has named it yet.`);
    if (r.sources.length) out.push(`Rests on ${plural(r.sources.length, "source")}: ${r.sources.map(titleOf).join(", ")}`);
    out.push(r.group === "one-away" ? `One thing is in the way: ${waitingSentence(r)}` : "No open question is in the way");
    if (r.group === "said-yes") out.push(h("button", { class: "linkish", type: "button", "data-act": "open-receipt", onclick: () => openItem(r) }, `You said yes on ${dayYear(r.yes.date)}`));
    return out;
  }
  function chip(key) {
    const a = refChip(key);
    a.tabIndex = 0; a.setAttribute("role", "link");
    a.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); a.click(); } });
    return a;
  }
  function openItem(r) {
    const section = D.sections.find((s) => s.page === r.key);
    if (section) Nav.open(section.id); else go(r.key, { reset: true, reveal: true });
  }
  function changeOwnerPrompt(r) {
    return `Change who runs the grill on ${r.name}. ${listWords(r.owner.map(personName), 3) || "Nobody"} runs it now${r.join.length ? `, with ${listWords(r.join.map(personName))} asked to join` : ""}. Ask me who should run it and who to ask to join.`;
  }
  function nodes(key) {
    const r = BY[key.slice(6)], [pillText, tone] = pillOf(r), inBatch = st.batch.includes(r.id), text = prompt(r), settle = settlePrompt(r);
    const head = h("div", { class: "p-head" }, h("div", { class: "kind" }, `${kindWord(r)} · ${r.group === "said-yes" ? "you said yes" : r.group === "ready" ? "ready to decide" : "one thing away"}`),
      h("h2", {}, r.name), h("div", { class: "p-meta" }, h("span", { class: `g-pill ${tone}` }, r.group === "ready" ? "nothing in the way" : pillText)));
    const ownerRows = [h("li", {}, listWords(r.owner.map((o) => (isYou(o) ? `You (${personName(o)})` : personName(o))), 3) || "Not recorded", ": runs it and decides ",
      h("button", { class: "linkish g-change", type: "button", title: "Copies a request for Claude, who sets it with a command", onclick: () => copy(changeOwnerPrompt(r), "the request") }, "(change)"))];
    return [head, h("div", { class: "p-body g-detail", "data-grill": r.id },
      r.settles.length ? Panel.section("What the grill settles", null, bulletList(r.settles.map(settleLine))) : Panel.section("What the grill settles", null, Panel.empty("Not recorded: nothing says yet what this settles.")),
      Panel.section("Where it stands", null, bulletList(standsLines(r))),
      Panel.section("What it holds up", r.holdsUp.length || null, r.holdsUp.length ? h("div", { class: "g-panelchips" }, r.holdsUp.map(chip)) : Panel.empty("Nothing is recorded as waiting on it.")),
      Panel.section("Owner", null, bulletList(ownerRows)),
      Panel.section("Asked to join", r.join.length || null, r.join.length ? bulletList(r.join.map((j) => (isYou(j) ? `You (${personName(j)})` : personName(j)))) : Panel.empty("Nobody is asked to join.")),
      Panel.section("Prompt for Claude", null, h("p", { class: "p-note" }, "Sure of it? Settle it:"),
        h("pre", { class: "g-prompt", "data-prompt": "settle" }, settle),
        h("div", { class: "g-btns" }, h("button", { class: "btn g-primary", type: "button", "data-act": "copy-settle", onclick: () => copy(settle, "the settle prompt") }, "Copy settle prompt")),
        h("p", { class: "p-note" }, "Want it tested first? Grill it:"),
        h("pre", { class: "g-prompt", "data-prompt": "one" }, text),
        h("div", { class: "g-btns" }, h("button", { class: "btn", type: "button", "data-act": "copy", onclick: () => copy(text, "the prompt") }, "Copy prompt"),
          h("button", { class: "btn", type: "button", "data-act": "batch", "aria-pressed": String(inBatch), onclick: () => toggleBatch(r.id) }, inBatch ? "In the batch (remove)" : "Add to a batch"),
          h("button", { class: "btn", type: "button", "data-act": "open-item", onclick: () => openItem(r) }, `Open the ${kindWord(r).toLowerCase()}`)),
        h("p", { class: "p-note" }, "Add to a batch builds one prompt that grills several items in one session, in the order that unblocks the most.")))];
  }

  /* On an item's own details: a small line when it is ready for a grill, with the same Copy button. */
  function readyLine(key) {
    const r = BY_KEY[key];
    if (!r || r.group === "one-away") return null;
    return Panel.section("Ready for a grill", null, h("div", { class: "g-ready-line", "data-ready-for": r.id },
      h("span", {}, r.group === "said-yes" ? "You said yes to this. Settle it when you're sure, or copy the grill prompt to test it." : "Nothing is in the way. Settle it when you're sure, or copy the grill prompt to test it."),
      h("button", { class: "btn tiny g-primary", type: "button", "data-act": "copy-ready-settle", onclick: () => copy(settlePrompt(r), "the settle prompt") }, "Copy settle prompt"),
      h("button", { class: "btn tiny", type: "button", "data-act": "copy-ready", onclick: () => copy(prompt(r), "the prompt") }, "Copy grill prompt"),
      h("button", { class: "btn tiny", type: "button", "data-act": "see-grill", onclick: () => { open(); select(keyOf(r)); } }, "See it in Waiting for a decision")));
  }

  /* ------------------------------------------------------------ the Details panel (detailspanel.js) */
  function summaryNodes() {
    const mine = forYou(), next = byUnblocked(mine.filter(readyNow))[0];
    return [PlanDetails.head("Waiting for a decision", plural(rows.length, "item")),
      h("div", { class: "p-body" }, Panel.section(hasViewer() ? `For ${viewerName()}` : "For everyone", mine.length || null, mine.length
        ? PlanDetails.bullets(byUnblocked(mine).slice(0, 5).map((r) => PlanDetails.link(keyOf(r), r.name))) : PlanDetails.quiet("No grill is waiting for this person.")),
      next ? h("div", { class: "p-note" }, `Start with ${next.name}${next.holdsUp.length ? `: it holds up ${plural(next.holdsUp.length, "thing")}` : ""}.`) : null,
      h("div", { class: "p-note" }, "Pick one to see what deciding it would settle, then copy a prompt into Claude."))];
  }
  DetailsPanel.register("grills", {
    view: "grills", live: () => rows.length > 0, rootLabel: "Waiting for a decision", summary: summaryNodes,
    owns: (k) => k.startsWith("grill:") || PlanDetails.owns(k), detail: (k) => (k.startsWith("grill:") ? nodes(k) : PlanDetails.detail(k, "grills")),
    label: (k) => (k.startsWith("grill:") ? (BY[k.slice(6)] || { name: k }).name : PlanDetails.label(k)), open: (k) => (k.startsWith("grill:") ? null : PlanDetails.openFor(k, "grills")),
    focus: (k) => { const was = st.open; st.open = k && k.startsWith("grill:") ? k : ""; if (was !== st.open && App.view === "grills") paint(); },
  });

  /* ------------------------------------------------------------ the rest of the page: sidebar and top bar */
  const exists = () => rows.length > 0;
  const count = () => forYou().length;
  const badgeWords = () => (hasViewer() ? "grills for you" : "grills waiting");
  const badgeTip = () => `${plural(count(), "grill")} ${hasViewer() ? `for ${viewerName()}` : "waiting"}, ${forYou().filter(readyNow).length} ready now. Click to see them.`;
  function open() {
    if (App.view !== "grills") Grills.from = Nav.where();
    App.section = "grills"; App.root = "lights"; App.trail = []; App.focus = null;
    showView("grills"); Panel.render();
  }
  function boot() {
    readHash();
    open();
    if (HASH.get("open") && BY[HASH.get("open")]) select(keyOf(BY[HASH.get("open")]));
    return true;
  }
  function readHash() {
    if (HASH.has("as")) Viewer.fromLink(HASH.get("as"));
    if (HASH.get("scope") && SCOPE_TEST[HASH.get("scope")]) st.scope = HASH.get("scope");
    if (HASH.has("ready")) st.readyOnly = true;
  }
  function hashParts() {
    const p = [];
    if (Viewer.pick()) p.push("as=" + (Viewer.pick() === Viewer.EVERYONE ? "everyone" : encodeURIComponent(Viewer.pick().replace(/^@/, ""))));
    if (st.scope !== "mine") p.push("scope=" + st.scope);
    if (st.readyOnly) p.push("ready");
    if (st.open) p.push("open=" + encodeURIComponent(st.open.slice(6)));
    return p;
  }
  readHash();  // a link names who is viewing (#s=grills&as=agent-lead), and the top bar and sidebar count for them from the first paint
  const entry = (key) => (BY[key.slice(6)] ? { key, kind: "grill", title: BY[key.slice(6)].name, id: "" } : null);
  return { rows, exists, count, forYou, badgeWords, badgeTip, open, boot, readHash, hashParts, entry, nodes, readyLine, render, select, st, visible, countOf, hasViewer, viewerHandles,
    isMine, isAsked, prompt, settlePrompt, batchPrompt, byUnblocked, setViewer, toggleBatch, keyOf, waitingSentence, from: null };
})();
View("grills", { label: "Waiting for a decision", title: "What the plan is ready to decide, by who runs the grill", render: Grills.render, count: () => String(Grills.count()) });
