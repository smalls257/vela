---
# The model may start close, on purpose: "we're done" or "switch to requirements" must be able to start it
# without the lead typing /vela:close. The description's "Never start it unprompted" is the guard.
name: close
description: 'File the session when the lead says they''re done ("close", "we''re done", "switch to …"): notes into pages, prose in the house voice, then the branch sent for review after a yes. Never start it unprompted.'
argument-hint: "[session id, if more than one is open]"
---

# Close a session

Before your first command and your first question, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` (the first step of `${CLAUDE_PLUGIN_ROOT}/references/START.md`); write page prose through `house-voice`.

Close files the session and sends it for review. The steps, in order: find the session (1), mark the captures (2), write the items (3), draft the prose (4), check who still says yes, then read back what goes on record in the lead's name (5), bring in main and check (6), finish and send (7), open the pull request (8), the dashboard (9). Commands do the filing; you do the talking. Never report a step as done when it failed.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). Use `--for-lead` when you'll tell the lead the result and `--json` when you need to reason over it, and say it in your own words, in the voice: names, not codes or IDs. Never pass raw git or `gh` error text on: say in one sentence that it didn't work and what you'll do. A failure you fix isn't news. When a command can't express what the lead wants, say so and stop; never fall back to doing its steps by hand.

## Starting a close

Close starts on the lead's word, never by yours (START, "Closing a session"): `/vela:close`, "close", "we're done" or "switch to requirements" is the yes to filing. Say in one line what will happen ("I'll file your notes, write the pages and send the branch for review") and go on.

One confirmation stays, because sending is the only step that leaves the machine and a hard stop forbids sending company material without consent. Before section 7 pushes, `vela close push` says what will be sent; say it to the lead and wait for a yes. A bare "close" is consent to file, not to send.

## Reader copy

Run `vela role`. If it says `reader`, every close command takes the reader path itself, so nothing is committed, pushed or sent; read `${CLAUDE_PLUGIN_ROOT}/skills/close/READER.md` for what to say. Never say a PR exists in a reader copy.

## 1. Find the session

Run `vela session open --switch --for-lead`. With one open session it switches to its branch (an answer session's is its challenge's) and says which; go on. Exit 3: several are open; ask which, by topic and date, then run `vela session open --switch --id <the one they picked>`. Exit 1: none is open; say so in one line, change no page, and go straight to section 9, which has its own path for a close with no session.

## 2. Mark every capture

Run `vela marks plan --json`. It gives every capture its default mark without asking, drafts the decision files under `.vela/decisions/<session>/`, and exits 0 once they're written, with what only the lead can settle in `needs_lead`, most blocking first. Filing is the tool's work, not the lead's: never show the lead the marks, a capture number or a list to approve. Fill each field it leaves for you (`for_model`, such as which page an idea belongs on) from what was said.

Ask the leftovers in one message: at most three items, each one plain sentence with your recommended answer. For example: "I'd write the January 18 slot down as a constraint, from your account. Right?" and "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and chase it on November 6. Is that the right person?" When more are left, say how many and offer them ("There are four more; want them?"). An unknown or a deferral Claude raised is never Claude's to keep or drop: the lead chooses.

Capture each answer with `vela record add --origin <their handle> --tag <tag> "<their words>"` and point the draft's judgment field at that capture ("^c31"), never at the words. Then run `vela apply <file> --for-lead` for each draft. If it stops, fix what it names, or ask the lead what it needs. Say in two or three sentences what you filed, by group and in the lead's words, from its counts: "I kept the 8 fixed limits as constraints, set aside 12 what-ifs and dropped 5 that repeat other lines." Don't ask "anything to change?" a second time.

## 3. Write the items

Write each new item with `vela add unknown`, `vela add constraint`, `vela add subject`, `vela add source` or another type `vela add --help` lists; each type's `--help` lists its fields. It numbers past every open session branch, so never number an item by hand. Facts come from the lead: never fill one from general knowledge, and when nobody knows a required fact, write an unknown that asks for it. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written. A capture an earlier mode marked keeps its mark.

When `marks plan` leaves a ledger row's state to you, or the lead said the catalog missed a question, read `${CLAUDE_PLUGIN_ROOT}/skills/close/LEDGER.md`.

## 4. Draft the prose

Run `vela close drafts --json`. It lists every paragraph this session owes, each with why. Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it for each. Keep the owner's wording wherever its facts still hold, because a later close harvests their edits. A page has one opening: the one you rewrite replaces the old one, and you never write a new opening beside it.

- Before you rewrite a merged paragraph whole, run `vela prose replace --page 05-building-blocks/till.md --line 12` with its page and any line of it, so no edit of the owner's is lost.
- A decision record starts as `vela add adr --state decided --decision <the deciding session id> --decides <ID> --title "<what was decided>"`; then draft its sections.
- A sentence that leaves a matter for a grill, or for later, is never kept as prose: write the question with `vela add unknown --blocks <ID>` and link it.
- Add a glossary entry for each term a newcomer wouldn't know.
- When it owes more than about twenty paragraphs, ask whether to split the pull request by page group.

Then run `vela style <each drafted page>` and fix what it prints until it prints nothing. Never delete an `**Ask:**`, `**Target:**` or `**Owning team:**` line, or a `- Trace:` line, to quiet it: vela reads them. Then run `vela close stage --draft`.

### Voice review

Skip it if nothing was drafted. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/close/VOICE-REVIEW.md`: a fresh reader checks the drafts, because the drafter can't judge its own voice.

### Harvest the owner's edits

Run `vela voice harvest list --json`, even when the review didn't run. With no candidates, say in a line why (the owner hasn't given samples of their writing yet, or none of their edits turned up) and go on. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/close/HARVEST.md`.

## 5. Still yes, then the read-back

Everything the lead said stays in notes on this machine. What goes into the plan and the pull request in their name is a short list of sentences, and the lead sees every one before it does. Do the two steps below in this order, so the read-back covers the final words.

**Still yes? Only when this session is a later part.** If the session was started on another machine (`vela close gate --json` lists decisions "decided on the other machine"), ask once, in one message, with the names the gate gives: "These were decided on the other machine: the booking API, and one question taken off the finance page. Still yes?" On a yes, capture it with the lead as origin (`vela record add --origin @<handle from vela whoami> --tag decision "<their words>"`) and run `vela close reconfirm --yes ^cNN <ID>` (more IDs may follow) with the IDs from the gate's `--json` detail. It points each item's receipt at this machine's capture. On a no, capture that too and run nothing: the gate keeps holding the item, and you offer to reopen it with the lead's word. Never reconfirm anything for them.

**The read-back.** Run `vela close readback --for-lead`. It lists each sentence that goes on record in the lead's name: the receipt of each decision they made (their words), each Why, and any line picked for the pull request. Read them in groups of about five, by item name, and for each the lead keeps it, rewords it or cuts it:

- Reword: `vela close readback --reword <ID> --line decision --words "<their words>"`, with `--line why` for a Why and `--line quote` for a picked quote. The new words must be part of what they said, or they must have said them and approved this wording; in that case add `--approved ^cNN`, the capture where they did.
- Cut: `vela close readback --cut <ID> --line why`, or `--line quote`, with the ID of the item whose page holds the line. A decision's own receipt can be reworded, never cut: their decision needs their words on record, and the command says so.
- Pick a line for the pull request's "In their words": `vela close readback --pick ^cNN`. It takes the lead's own words; someone else's only if they gave their own yes to being quoted, whatever the lead says they told them.

When they're done, run `vela close readback --done`. Changing a sentence after that reopens the read-back. If an item's owner is someone else and isn't here, their decision stays a name in the receipt with no words, and `close pr` lists it for them.

## 6. Bring in main and check

Run `vela close sync-main --for-lead`, so the checks see what will merge.

- Exit 0: go on.
- Exit 3 for uncommitted edits: run `vela close stage --checkpoint`, then sync-main again.
- Exit 3 because main couldn't be reached: tell the lead, and ask whether to go on without it. On a yes, run `vela close sync-main --accept-not-compared`; otherwise try again later.
- Exit 1: main changed lines this session changed too. Show the lead both sides in plain words and let them choose; make their choice, run `vela close stage --checkpoint`, and run sync-main again.

Then run `vela render`, `vela check --fix W326` and `vela check --for-lead`. Two warnings point at questions the ledger can't see, so ask about each in plain words; they count among the few things section 2 asks:

- a fact that names points, a clause, a license or the like, with no subject of that kind typed (W809): offer to type the subject with the facts the lead gives (`vela add subject`), or to answer the existence question in the ledger;
- a ledger row that no longer fits its subject, or covers nothing (W804): offer to fix the row or keep it as a record. Never delete it without a yes.

Flow steps whose sender or receiver is no app or party the plan knows (E351), an app written as plain text (W354) or two apps with no recorded sender (W374) get fixed with the lead before the session closes; an outside actor becomes a party only on their yes. Fix each error with the lead. An override the check can't read: fix its grammar, never delete it. Never delete a ledger row or an override to quiet the check; the gate stops a close that did. If the lead leaves an error in place, say CI will block the merge until it's fixed.

## 7. Finish and send

Run `vela check-slice --changed --for-lead`, which records what the gate reads (don't read its lines out), then `vela close gate --for-lead`. Say in your words which slices still run end to end and which break, and where. If the gate lists anything, group it by what holds the close up, about four at a time ("Three things before I can finish: two decisions have no yes from you yet, one note isn't sorted, and one page is waiting on seven open questions. One at a time?"), and take them one at a time with your view. Remind the lead they may keep any as it is: that's an override, noted with their reason (START, "The user may override any rule"). A decision with no yes needs the lead's own words: read the item back, capture their answer with them as origin (as step 2 below does, without the mark), and cite that capture in the item's `## Changes` row in the notes. Run the gate again until it says the session is ready.

Three problems are about the words on record, not about a missing yes:

- *"I haven't read back the wording that goes on record in your name yet."* Do section 5's read-back, then `--done`.
- *"The decision on <name> has none of your words on record yet."* The lead's decisions carry the lead's own words. Reword it with `vela close readback --reword <ID> --line decision --words "<their words>" --approved ^cNN`, where that capture is a yes they gave in the session. If there is no such yes, ask for one now and capture it.
- *"<Name>'s decision quotes someone who hasn't said yes to being quoted."* Ask that person once, if they're in the session (`grill` step 3 has the question), and capture their answer with them as origin and the tag `quote-yes`. Otherwise take their words out of the line at the read-back, by cutting it or rewording it. A yes the lead relays doesn't count.

If it lists decisions "decided on the other machine", go back to section 5's first step: reconfirm comes before the read-back, so a finished read-back is never reopened by it.

Then send, in this order: the yes must come after the notice and before the record closes.

1. Run `vela close push --for-lead`. It prints the send notice and exits 3. Say it ("I'll send this for review to Ines and the payments team. OK?") and wait.
2. Capture the lead's answer, whatever it is: `vela record add --origin @<handle from vela whoami> --tag decision --mark "drop: the yes to send this for review" "<their words>"`. It prints the capture's number. Never another name or an email address: close push sends only on the lead's own handle. On a no, do step 3 and stop: the session is filed and nothing is sent.
3. Run `vela close finish --summary "<one line, in plain words>" --for-lead`. It closes the session, fingerprints this machine's notes, and commits the stub and the pages from an allow-list (it never stages the notes, which stay on this machine, nor the inbox, `voice/local/` or `voice/corpus/`), writes and commits each handoff record, then rebuilds the dashboard. Say what it lists as not settled at handoff, so nobody hands an app over without knowing. If it stops because an app's handoff record exists, that app's team is accepting changes: run it with `--replace` only once they say so in this session.
4. Run `vela close push --consent ^cN --for-lead`, with the number from step 2. If it says a review needs its own branch, ask the lead; on a yes run `vela session branch --for-lead` and start this section again. If it fails, say so in one sentence, give the branch and the retry it names, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the pull request

Write the two or three sentences a reviewer reads first to `.vela/close/prose.md`, as `${CLAUDE_PLUGIN_ROOT}/skills/close/PR-BODY.md` says. Then run `vela close pr --prose .vela/close/prose.md --for-lead`. It builds the title, the reviewers and every list in the body; for an answer session it comments on the challenge's pull request instead. Exit 0: show the URL. Exit 1: say the one sentence it gives. Exit 3: it doesn't know the lead's handle; ask once, run `vela whoami --set <handle>`, and run it again. Never say a PR exists unless `gh` printed its URL.

## What you tell the lead at the end

Three to six plain sentences: what was filed, by group and in the lead's words; what is waiting on someone, with the date; and the pull request link, or why there is none. If the lead hasn't backed up their notes, add one line: "Your notes for this session are only on this computer. Want me to copy them somewhere safe?" On a yes, ask for a folder outside the plan and run `vela records backup --to <folder>`. No capture number, ID or check code. The pull request is the reviewer's record; the lead doesn't need to read it. For a switch, end with the one line that starts the next mode, by name ("/vela:grill Desktop agent").

## 9. The dashboard

`close finish` rebuilds the dashboard last and gives the line the lead hears. Say it, with each warning it adds, and nothing else from its output. A failed build never undoes the close, and the dashboard is never called up to date unless it built.

With no session (section 1 found none), run `vela close dashboard --for-lead`. It never commits to main. If it offers a branch of its own and the lead says yes, run `vela close dashboard --branch`. That commits the page on the new branch; close can't send it from there, so say so and stop. If the lead turns it down, or the close ends without an answer, run `vela close dashboard --put-back --for-lead` and say its line, so nothing is left changed on main.
