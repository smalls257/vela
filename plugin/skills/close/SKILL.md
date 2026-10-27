---
# The model may start close, on purpose: "we're done" or "switch to requirements" must be able to start it
# without the lead typing /vela:close. The description's "Never start it unprompted" is the guard.
name: close
description: 'File the session when the lead says they''re done ("close", "we''re done", "switch to …"): notes into pages, prose in the house voice, then the branch sent for review after a yes. Never start it unprompted.'
argument-hint: "[session id, if more than one is open]"
---

# Close a session

Close files the session and sends it for review. Commands do the filing; you do the talking. Before your first command, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, and relay every command as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Relaying a command". Close starts on the lead's word, never yours. When a command can't express what the lead wants, say so and stop; never fall back to doing its steps by hand.

Four stops no override reaches; say which one applies and offer what you can do instead:

- Never edit anything under `~/.claude`.
- Never commit or push company material, or anything from `.inbox/`, `voice/local/` or `voice/corpus/`, without the owner's explicit consent in this session.
- Never say a PR, comment, push or commit exists unless the tool printed it, and never report a failed step as done.
- Never invent what a person said, a source, or an ID the vault does not hold.

Everything the lead said stays in notes on this machine. What goes into the plan and the pull request in their name is a short list of sentences, and the lead sees every one before it leaves. Sending is the only step that leaves the machine, and it takes its own yes.

Run `vela role`. In a reader copy, read `${CLAUDE_PLUGIN_ROOT}/skills/close/READER.md`.

## 1. Find the session and mark the captures

Run `vela session open --switch --for-lead`. If several are open, ask which, by topic and date. If none is open, change no page and go to section 6.

Run `vela marks plan --json`. Filing is the tool's work, not the lead's: never show the lead marks, capture numbers or a list to approve. Fill each field it leaves you from what was said. Ask its `needs_lead` leftovers in one message, at most three, each one plain sentence with your recommendation ("I'd write the January 18 slot down as a constraint, from your account. Right?" or "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and chase it on November 6. Is that the right person?"). An unknown or a deferral Claude raised is never Claude's to keep or drop: the lead chooses. Capture each answer, point the draft's field at that capture, and `vela apply <file> --for-lead` each draft. Say what you filed in two or three sentences, by group and in the lead's words: "I kept the 8 fixed limits as constraints, set aside 12 what-ifs and dropped 5 that repeat other lines." Don't ask "anything to change?" twice.

## 2. Write the items and the prose

Write each new item with `vela add unknown`, `vela add constraint` or another type `vela add --help` lists. Facts come from the lead, never from general knowledge; when nobody knows a required fact, write an unknown that asks for it. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written. When `marks plan` leaves a ledger row's state to you, or the lead says the catalog missed a question, read `${CLAUDE_PLUGIN_ROOT}/skills/close/LEDGER.md`.

Run `vela close drafts --json` and draft only its `paragraphs`, through `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md`. A sentence that leaves a matter for later is never kept as prose: write the question with `vela add unknown --blocks <ID>` and link it. Add a glossary entry for each term a newcomer wouldn't know. When it owes more than about twenty paragraphs, ask whether to split the pull request by page group. Then run `vela style` on each drafted page, fix its mechanical findings once, and go on. Never delete an `**Ask:**`, `**Target:**` or `**Owning team:**` line, or a `- Trace:` line, to quiet it. Then run `vela close stage --draft`.

If the session touched prose and `vela close drafts` says a review is due, run the voice review once as `${CLAUDE_PLUGIN_ROOT}/skills/close/VOICE-REVIEW.md` says; show the lead only new or changed paragraphs. Then `vela voice harvest list --json`; with candidates, read `${CLAUDE_PLUGIN_ROOT}/skills/close/HARVEST.md`.

## 3. The read-back

Run `vela close readback --for-lead`. It lists only quotes picked for the pull request; read them back for keep, reword or cut, then `vela close readback --done`. When it lists nothing, say nothing and go on.

## 4. Check, then finish and send

Run `vela close sync-main --for-lead`; where main changed the same lines, show the lead both sides in plain words and make their choice. Then `vela render`, `vela check --fix auto`, `vela check --for-lead` and `vela check-slice --changed --for-lead`. Say its count lines as they are ("There are also 41 wording notes; want them?", "I'll fix 26 more myself when we close"). Fix errors and flow-step findings with the lead; an outside actor becomes a party only on their yes. Never delete a ledger row or an override to quiet a check. Ask about a possibly untyped subject or a ledger row that no longer fits in plain words; they count among the few things section 1 asks.

Run `vela close gate --for-lead` and say which slices still run end to end and which break. Take what it lists one at a time with your view, grouped by what holds the close up ("Three things before I can finish: two decisions have no yes from you yet, one note isn't sorted, and one page is waiting on seven open questions. One at a time?"); the lead may keep any as it is: record it as START's override rule says, with their reason. A decision with no yes needs the lead's own words: read the item back and capture their answer. Run the gate again until it says the session is ready.

Then send, in this order:

1. Run `vela close push --for-lead` and say its notice ("I'll send this for review to Ines and the payments team. OK?"); wait. If it says the session is on main and a review needs its own branch, ask now, while the session is still open; on a yes run `vela session branch --for-lead`, `vela close sync-main` and `vela close stage`, then start this list again.
2. Capture the lead's answer, whatever it is, while the session is open: `vela record add --tag decision --mark "drop: the yes to send this for review" "<their words>"`. On a no, do step 3 and stop: the session is filed and nothing is sent.
3. Run `vela close finish --summary "<one line>" --for-lead`. The notes stay on this machine. The summary opens the pull request and nobody reads it back, so it quotes no one: say what was filed, never what anyone said. Say what it lists as not settled at handoff.
4. Run `vela close push --consent ^cN --for-lead` with the capture from step 2. If it fails, say so in one sentence and stop.

## 5. The pull request, and what you tell the lead

Write the two or three sentences a reviewer reads first to `.vela/close/prose.md`, as `${CLAUDE_PLUGIN_ROOT}/skills/close/PR-BODY.md` says, then run `vela close pr --prose .vela/close/prose.md --for-lead` and show the URL it prints. Never say a PR exists unless `gh` printed its URL.

End with three to six plain sentences: what was filed, by group; what was settled, as close finish says it; what waits on someone, with the date; the pull request link, or why there is none; and the dashboard line `close finish` gave. If the notes aren't backed up, add: "Your notes for this session are only on this computer. Want me to copy them somewhere safe?" On a yes, ask for a folder outside the plan and run `vela records backup --to <folder>`. For a switch, end with the line that starts the next mode, by name ("/vela:grill Desktop agent").

## 6. No session open

Run `vela close dashboard --for-lead` and do what it offers. If the lead turns its branch down, or the close ends without an answer, run `vela close dashboard --put-back --for-lead`, so nothing is left changed on main.
