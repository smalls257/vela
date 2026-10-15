---
# The model may start close, on purpose: "we're done" or "switch to requirements" must be able to start it
# without the lead typing /vela:close. The description's "Never start it unprompted" is the guard.
name: close
description: File the session when the lead says they're done ("close", "we're done", "switch to …"): notes into pages, prose in the house voice, then the branch sent for review after a yes. Never start it unprompted.
argument-hint: "[session id, if more than one is open]"
---

# Close a session

Before your first command and your first question, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` (step 6 of `${CLAUDE_PLUGIN_ROOT}/references/START.md`); write page prose through `house-voice`.

Close files the session and sends it for review. The steps, in order: find the session (1), mark the captures (2), write the items (3), draft the prose (4), read back decided wording (5), bring in main and check (6), finish and send (7), open the pull request (8), the dashboard (9). Commands do the filing; you do the talking. Never report a step as done when it failed.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). Use `--for-lead` when you'll tell the lead the result and `--json` when you need to reason over it, and say it in your own words, in the voice: names, not codes or IDs. Never pass raw git or `gh` error text on: say in one sentence that it didn't work and what you'll do. A failure you fix isn't news. When a command can't express what the lead wants, say so and stop; never fall back to doing its steps by hand.

## Starting a close

Close starts on the lead's word, never by yours (START, "Closing a session"): `/vela:close`, "close", "we're done" or "switch to requirements" is the yes to filing. Say in one line what will happen ("I'll file your notes, write the pages and send the branch for review") and go on.

One confirmation stays, because sending is the only step that leaves the machine and a hard stop forbids sending company material without consent. Before section 7 pushes, `vela close push` says what will be sent; say it to the lead and wait for a yes. A bare "close" is consent to file, not to send.

## Reader copy

Run `vela role`. If it says `reader`, every close command takes the reader path itself, so nothing is committed, pushed or sent; read `${CLAUDE_PLUGIN_ROOT}/skills/close/READER.md` for what to say. Never say a PR exists in a reader copy.

## 1. Find the session

Run `vela session open --switch --for-lead`. With one open session it switches to its branch (an answer session's is its challenge's) and says which; go on. Exit 3: several are open; ask which, by topic and date, then run `vela session open --switch --id <the one they picked>`. Exit 1: none is open; say so in one line, change no page, and go straight to section 9, which has its own path for a close with no session.

## 2. Mark every capture

Mark every capture that has none yet by the defaults below, without asking. Filing is the tool's work, not the lead's. Keep the full list of marks, each with its one-line reason, for the pull request body; never show it to the lead as a numbered list to approve. A new item gets its ID in section 3, and the marks are written into the lines at the end of it, once every ID exists.

Then show the lead only what the defaults could not settle: at most three items, each one plain sentence with your recommended answer, asked in one message. These are the kinds of thing that qualify, and nothing else does:

- a `claude`-origin line the lead might want kept, or an `unknown` of yours that needs a keep or a drop;
- an unknown with nobody who could answer it;
- a line you would copy word for word that the lead did not say themselves;
- a belief the plan seems to rest on, when you cannot tell whether it is load-bearing.

For example: "I'd write the 18 January slot down as a constraint, from your account. Right?" and "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and chase it on 6 November. Is that the right person?" If more than three are unsettled, ask the three that matter most and take your recommended answer for the rest, listing them in the pull request body. When the lead answers, write it, and say in two or three sentences what you filed, by group and in their words ("I kept the 8 hard limits as constraints, parked the 12 what-ifs and dropped 5 that repeat other lines"). Never show a capture number. Do not ask "anything to change?" a second time.

Never ask the lead for bookkeeping the record already holds or the tool can work out: not a handle (`START.md` says where it is kept), not the session's minutes (section 8), not whether a source document gets a row in `sources.md` (write the row for each document the lead brought in, and say so in the summary), not whether another gap turned up. Defaults:

- In a session whose `modes` include `shape`, the picked option is kept as an `assumption`, never an `inkling`. See section 3.
- A capture that names something the initiative cannot change, such as a date, a budget, a law, a contract term or a system it must keep, is kept as a constraint: a row on `02-constraints.md`, `| CST-n | <the constraint> | <where it comes from, as a link on the words> | <what it forces> |`. The link's label pipe is written `\|` there, because the link sits in a table cell.
- A person's `idea` or `thought` is kept as an `inkling` on the page it belongs to.
- A capture that says `type at close: PTY` or `type at close: SV` names a subject the lead said exists. It gets one mark, to the subject, `→ keep: [[03-context-and-scope#<heading>|<ID>]] (subject)`, because a party or stored value carries no state. That holds when its words also start with the existence question's copy ID: section 3 writes that copy's row, and the row's `## Changes` line cites the capture, so the capture needs no second mark. If section 3 leaves the subject untyped, mark it as a keep to the unknown section 3 writes instead, `→ keep: [[11-unknowns-and-risks#<heading>|UNK-nnn]] (open)`, so no mark links a heading that does not exist.
- Any other capture whose words start with a copy ID or a finding ID is kept as its ledger row, `→ keep: [[11-unknowns-and-risks#Question ledger|<copy>]] (<state>)`, with the state of the row. A finding the lead did not take has no capture, so it gets no mark. Section 3 says which of those still get a row.
- A capture that says how a concern touches an app, as `unchanged`, `n/a` with why, or `unknown` with its unknown, is kept as that concern cell, as `vela conventions "Concern cells and waivers"` says. Only a grill writes `addressed`.
- A capture that answers an open unknown, the lead's first-hand word or a source the session read, is kept as that unknown resolved, as `MODES.md` says under "Unknowns": `→ keep: [[11-unknowns-and-risks#<heading>|<ID>]] (resolved)`. A first-hand answer needs its own row in `sources.md` first.
- A person's `unknown` or `worry` is kept as an unknown, or as a concern cell. Its `**Owner:**` is the handle of the lead who is chasing it, and the person who would know goes on the `**Ask:**` line as the role the lead named ("CISO", "outside counsel"); never stop to ask for a handle. Its ask-by date is the date the lead gave, else the nearest hard date the vault holds (a constraint or a release target), else two weeks from today. Say the date you chose in the summary.
- An `unknown` capture is kept or dropped with a reason. It is never parked. For a `claude`-origin `unknown`, the user must choose, so it is one of the few items you ask about: kept as an UNK with an owner and an ask-by date, or dropped with a reason. Number each new UNK with `vela next-id UNK`, run again after each one is written, so the number is never guessed or reused from an open session branch. Claude never decides it alone. This rule wins over the park default for `claude` lines.
- A capture, or a sentence you are about to write on a page, that says something is left for a grill, or is decided later, is never kept as prose. It becomes an open unknown, `### UNK-nnn <short name>`: the question in the lead's words, an `**Owner:**` (the lead who will take it to the grill), an `**Ask by:**` date by the rule above, and `**Blocks:**` linking the item that is waiting. The sentence on the page then links that unknown, so the record says who will answer and by when. Say in the summary which deferrals you turned into questions. The check warns (W389) on page prose that leaves a matter for a grill and links no open question.
- A person's `wild` line is parked, never dropped.
- A `(claude)` line is parked unless the user picks it. This covers every origin that starts with `claude`, including `(claude, from <name>)`.
- Never propose `fact`. A capture becomes a fact only if the user names its source in this turn and the source has a row in `sources.md`.
- A line you will copy word for word onto a page is a lifted line. When the lead said it themselves, copy it and list it in the pull request body. When anyone else said it, or it is `claude`'s, it is one of the few items you confirm before you copy it.

A line a grill already marked `(decided)`, a Discover already marked `(fact)`, or a Boundary, Requirements, Allocate or Releases session already marked `(assumption)`, keeps its mark. Leave it alone. It still appears under "Promoted on a nod" when its origin starts with `claude`.

## 3. Write the promoted items

Write each kept item onto its page as structured content only: fact bullets, table rows and `### <ID> <short name>` headings, as `vela conventions "Fact bullets"` and `vela conventions "Fact tables"` say. A grill already wrote its decided items, Discover already wrote its facts, Boundary already wrote its app, contract and runtime pages, Requirements already wrote its functional requirements, Allocate already wrote its allocation rows and any contract it proposed, and Releases already wrote `04b-releases.md`, so leave those alone. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written, and never move, merge or reword one. If the user overrode a rule during the session and no bullet records it yet, write it now, in the grammar of `vela conventions "Overrides"`, with the handle, date and reason from the capture. If no rule was set aside, write no `**Override:**` bullet: something the lead wishes (who may reopen an item, and when) is a Notes line, not an override, and an `**Override:**` never names a rule that exists nowhere in the skills.

For a session whose `modes` include `epics`, the epic pages already exist, so write no `assumption` item for a picked cut, and skip the `shape` paragraph that follows. Still add the `## Changes` rows for every epic whose state changed, `| EPC-nnn | - | draft | [[<id>#^cNN]] |` and `| EPC-nnn | draft | decided | ... |`, or `| EPC-nnn | reopened | decided | ... |` for a reopened epic, if the session has not already. For any other session whose `modes` include `shape`, write the picked option as an `assumption` item with an `**Options considered:**` bullet, at page level or under the item's heading: `- **Options considered:** <picked option> (picked); <option>: rejected, <reason>; ...`. `vela next` reads it: an `assumption` without it still needs a Shape, and one with it is ready for a grill. If a capture says "that's decided", add a "grill to confirm" note to the item. The item must pass grill's GATE-2 afterwards: at `assumption`, with a preferred option and the rejected options with their reasons. Number each new item with `vela next-id <its prefix>` (`vela next-id CST`, `vela next-id UNK`), run again after each one is written: it counts this tree, `main` and every session branch, so another open session's number is never reused. Add one row to `## Changes` for each item whose state changed: `| ID | From | To | [[<id>#^cNN]] |`.

### Subjects, the question ledger and catalog gaps

Read `${CLAUDE_PLUGIN_ROOT}/skills/close/LEDGER.md` and follow it. It types the subjects Dump named (`type at close: PTY` or `SV` captures), writes a ledger row for every copy or finding the lead took (and for every row of the record's `## Reviews` tables), runs `vela check` on the ledger, and lists catalog gaps in the pull request body. Skip it only when the record holds no such capture and no `## Reviews` table.

### Write the marks

Every new item, subject, unknown and reviewer question now has its ID. Write each mark into the line: `→ keep: [[<page>#<heading>|<ID>]] (<state>)`, `→ park` or `→ drop: <reason>`, before the `^cNN`.

## 4. Draft the prose

Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it for every paragraph this session needs. Those are:

- the opening prose of every page this session changed (`git diff --name-only --diff-filter=d main...HEAD`, leaving out `sessions/` and `sources.md`), rewritten to say what is true now, as `vela conventions "Pages"` says. Keep the owner's own wording wherever the facts it states have not changed, because a later close harvests those edits; rewrite only what the session made untrue or left out. Never add a paragraph about what changed: that is the page's `## History`. A page has one opening: the one you rewrite replaces the old one, and you never write a new opening beside it. Two or more separate opening paragraphs above the first `##` heading, running past 150 words together, draw W371; keep one and fold what the others add under a heading. The opening is two or three plain sentences, at most about 80 words and three links: what is true now and the one thing that holds it up. It names threads, not items, and sends the reader to the block or table below for the items; a state is said once, in one sentence, and never added to each clause (`house-voice` rules 1, 3 and 7). A page of more than about 900 words with no such opening draws W363, an opening over 90 words or 3 links draws W365, and an opening that is still a line the template wrote draws W368. Run `vela check` for W363, W365, W368 and W371 on every page whose opening you wrote, and rewrite until none remains; do not list the warning in the pull request instead. An opening is never a changelog ("Five more unknowns came from the desks session..."). On a page that is mostly a list (unknowns and risks, concerns, decisions, sources), the opening counts and points and never enumerates the list, as `house-voice` says under "Pages that are mostly a list": "28 questions are open. Five hold up the first release; the most urgent is who owns Heron, due 23 October." The items go below it, grouped by what they hold up;
- the sentences on other pages that mention an item whose state this session changed. For each unknown this session resolved and each item it decided, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela query refs <ID>`, open each page it lists, and rewrite the sentence that links the item so it says what is true now: "the account opens at the first practice trade", not "when the account opens is still open". Leave `## History` alone. `vela check` reports W334 for a sentence still calling an answered question open;
- the `## Strategy` paragraph of each concern page whose cells this session changed;
- on a page that lists more than about seven unknowns, concerns or other items, the few that matter first, and the rest under `## Also open (n)` at the end of the list's section, which the viewer and the explorer fold. Group any other list of more than about seven under subheadings of about five, each line reading the plain name, who to ask and by when, and what it holds up;
- the opening sentence of each `### <ID>` item this session wrote or changed, before its fact bullets;
- a decision record for each page this session made `decided` whose decision shapes the whole design: the solution strategy or another initiative section, an app page, or a flow. Write it as `09-decisions/ADR-nnnn-<slug>.md`, with `id`, `type: decision`, `title`, `state: decided`, `owner`, `authored: authored` and `sources`, and these sections: `## Context` (what forced the choice), `## Decision` (what was chosen, linking the decided page), `## Alternatives considered` (a table, `| Alternative | Why rejected |`, from its `**Options considered:**`) and `## Consequences` (what it commits people to). Put its `**Decision:**` bullet, linking the grill, under `## History`, and link the record from `09-decisions/09-decisions.md`. Contracts and unknowns get no record of their own;
- a glossary entry for each term the session used that a newcomer to the initiative would not know, such as a product name or a word like "paper trading": one paragraph on `12-glossary.md`, the term in bold, then what it means here;
- the paragraphs below.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela style <each changed page>` and fix every line it prints: move a history bullet under `## History`; write a labeled bullet nothing reads as a sentence in its section, merged with any prose that already says it; open an item that has only bullets with a sentence; say a bracketed aside in the sentence; label a link with the thing's name; and give a page with no opening prose one. An ID in a sentence or a list item is moved to a `- Trace:` line under it and the sentence names the thing in plain words. Fix only what it names, and run it again until it prints nothing. It also lists each word of the lint list (`${CLAUDE_PLUGIN_ROOT}/references/lint-words.txt`) the page uses, with its count: say what the thing does in plain words. Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela check` and fix each W365 to W369 line on the pages you changed the same way: split a long paragraph at its second topic or move its pointers to a table, cut a table cell to a clause, say a repeated state once and put the rest on a Trace line or in the table, replace a template opening with what is true now, and spell an abbreviation out at its first use. Never delete an `**Ask:**`, `**Target:**` or `**Owning team:**` line, or a `- Trace:` line, to quiet it: vela reads them, and a line it still flags is a vela bug to report in the PR body. For a session whose `modes` include `epics`, each epic it drafted owes its summary, its `Still open:` line and its `## Who this is for and what changes` section, in the epic template's order, so list those epics under "Prose drafted" in the PR body. The epics session already wrote each `**Owning team:**` line; close leaves it as written. Prose is drafted here and nowhere else. When a merged paragraph is wrong as a whole, `house-voice` says to rewrite it: first copy the old paragraph word for word under `## Replaced prose` in the session record (page, date, then the paragraph), so no edit of the owner's is lost. Commit each drafted page, by exact path, with the message `draft: prose for <id>`. That commit holds each drafted page whole, including its structured section-3 edits, because a page cannot be committed in halves. The reviewer's later edits then show as a diff against it.

### Voice review

A fresh reader checks the drafts, because the drafter cannot judge its own voice. Skip this part if the session drafted no paragraph. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/close/VOICE-REVIEW.md` and follow it (the optional voicescore reading, the reviewer subagent, one rewrite per flagged paragraph, and the voicecheck that decides whether a rewrite stays), then go on to the harvest.

### Harvest the owner's edits

Only the vault's owner harvests, and only their own edits. The owner is the `author` of the `source: owner` examples in `voice/examples/` and `voice/local/`. If there are none, say "No owner examples yet, so nothing to harvest. `/vela:voice-seed` adds them." and go on to section 5, Read back decided wording. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/close/HARVEST.md` and follow it; it offers the owner's merged edits as voice examples, one at a time. Harvest does not depend on the voice review: run it even when the review did not run.

## 5. Read back decided wording

For each item that became `decided` in this session, show its final wording. If its owner is present, they confirm it. If not, list it in the PR body for them.


## 6. Bring in main and check

Run `vela close sync-main --for-lead`, so the checks see what will merge.

- Exit 0: go on.
- Exit 3 for uncommitted edits: run `vela close stage --checkpoint`, then sync-main again.
- Exit 3 because main couldn't be reached: tell the lead, and ask whether to go on without it. On a yes, run `vela close sync-main --accept-not-compared`; otherwise try again later.
- Exit 1: main changed lines this session changed too. Show the lead both sides in plain words and let them choose; make their choice, run `vela close stage --checkpoint`, and run sync-main again.

Then run `vela render`, `vela check --fix W326` and `vela check --for-lead`. Two warnings point at questions the ledger can't see, so ask about each in plain words; they count among the few things section 2 asks:

- a fact that names points, a clause, a license or the like, with no subject of that kind typed (W809): offer to type the subject with the facts the lead gives (`vela add subject`), or to answer the existence question in the ledger;
- a ledger row that no longer fits its subject, or covers nothing (W804): offer to fix the row or keep it as a record. Never delete it without a yes.

Fix each error with the lead. An override the check can't read: fix its grammar, never delete it. Never delete a ledger row or an override to quiet the check; the gate refuses a close that did. If the lead leaves an error in place, say CI will block the merge until it's fixed.

## 7. Finish and send

Run `vela check-slice --changed`, which records what the gate reads (don't read its lines out), then `vela close gate --for-lead`. Say in your words which slices still run end to end and which break, and where. If the gate lists anything, group it by what holds the close up, about four at a time ("Three things before I can finish: two decisions have no yes from you yet, one note isn't sorted, and one page is waiting on seven open questions. One at a time?"), and take them one at a time with your view. Remind the lead they may keep any as it is: that's an override, noted with their reason (START, "The user may override any rule"). A decision with no yes needs the lead's own words: read the item back, capture their answer with them as origin (as step 2 below does, without the mark), and cite that capture in the item's `## Changes` row. Run the gate again until it says the session is ready.

Then send, in this order: the yes must come after the notice and before the record closes.

1. Run `vela close push --for-lead`. It prints the send notice and exits 3. Say it ("I'll send this for review to Priya and the identity team. OK?") and wait.
2. Capture the lead's answer, whatever it is: `vela record add --origin <their handle> --tag decision --mark "drop: the yes to send this for review" "<their words>"`. It prints the capture's number. On a no, do step 3 and stop: the session is filed and nothing is sent.
3. Run `vela close finish --summary "<one line, in plain words>" --for-lead`. It closes the record, commits it from an allow-list (it never stages the inbox, `voice/local/` or `voice/corpus/`), writes and commits each handoff record, then rebuilds the dashboard. Say what it lists as not settled at handoff, so nobody hands an app over without knowing. If it stops because an app's handoff record exists, that app's team is accepting changes: run it with `--replace` only once they say so in this session.
4. Run `vela close push --consent ^cN --for-lead`, with the number from step 2. If it fails, say so in one sentence, give the branch and the retry it names, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the pull request

Write the two or three sentences a reviewer reads first to `.vela/close/prose.md`, as `${CLAUDE_PLUGIN_ROOT}/skills/close/PR-BODY.md` says. Then run `vela close pr --prose .vela/close/prose.md --for-lead`. It builds the title, the reviewers and every list in the body; for an answer session it comments on the challenge's pull request instead. Exit 0: show the URL. Exit 1: say the one sentence it gives. Exit 3: it doesn't know the lead's handle; ask once, run `vela whoami --set <handle>`, and run it again. Never say a PR exists unless `gh` printed its URL.

## What you tell the lead at the end

Three to six plain sentences: what was filed, by group and in the lead's words; what is waiting on someone, with the date; and the pull request link, or why there is none. No capture number, ID or check code. The pull request is the reviewer's record; the lead doesn't need to read it. For a switch, end with the one line that starts the next mode, by name ("/vela:grill Desktop agent").

## 9. The dashboard

`close finish` rebuilds the dashboard last and gives the line the lead hears. Say it, with each warning it adds, and nothing else from its output. A failed build never undoes the close, and the dashboard is never called up to date unless it built.

With no session (section 1 found none), run `vela close dashboard --for-lead`. It never commits to main. If it offers a branch of its own and the lead says yes, run `vela close dashboard --branch`. That commits the page on the new branch; close can't send it from there, so say so and stop.
