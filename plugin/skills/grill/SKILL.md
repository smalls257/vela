---
name: grill
description: Decide ready items one question at a time, each with a recommended answer you hold under pushback. The only session that sets decided.
argument-hint: "<item IDs or page names to decide>"
disable-model-invocation: true
---

# The grill

Contents: 1 questions; acceptance; 2 start; 3 the gate; handing over; 4 write each decision; 5 a new unknown; ends; never.

A grill is the only session that makes an item `decided` (`vela terms` defines the word; say it once, the first time). It takes the items that are ready, or that the lead decides anyway, one question at a time, and files each decision as its branch closes.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). Read a format section with `vela conventions "<section>"`, never the whole file.

The conversation is yours; the writing is the CLI's. Relay `--for-lead` lines in your own voice and reason over `--json`. When a command can't express what the lead wants, say so and stop; never fall back to writing the page by hand. A kind with no command of its own is filed as `.vela/decisions/<session>/<n>-<kind>.json`, `{"version": 1, "kind": "<kind>", "session": "<id>", "items": [...]}` (`vela apply --schema <kind>` gives the fields), with `vela apply <file> --for-lead`.

## 1. The questions

This is what a grill is for; the other sections only set the agenda and file what was settled.

- Ask one question at a time. Wait for the answer.
- Give your recommended answer with each question, in the form: question, then *Recommended: <answer>. <one-line reason>.*
- Look things up in the plan rather than ask.
- Use a concrete scenario at the edge of the item to force a precise answer. Pick an edge case, not the happy path: "It's 8:58, the call starts at nine, and the calendar service doesn't answer. What does the person see?"
- Check each answer against what the plan already holds and what the lead said earlier. Say so when they disagree.
- Keep your recommendation when the user pushes back without a reason. Change it only for a reason, and say what the reason was.
- Never answer your own question.
- Answer first, then put about four things at most to the lead to judge. Show an agenda of more than about seven items in groups; the lead may take it in two sessions.

**Say names, not IDs, in your own words too.** Most codes a lead reads are ones the model typed in a parenthetical, not ones a command printed. IDs go in the commands; say one only where the lead must act on it (a PR to open, a page to find). A read-back by name:

> Record consent: the desktop agent asks for both choices, the calendar and the chosen folder, and keeps each with the time it was given. If saving doesn't answer within two seconds, the agent says "Couldn't save your choice, so nothing was switched on" and asks again at the next start. That's what I'll write as decided. Right?

Not: "CON-003 (Dock unlock): decided, GATE-5 overridden, see UNK-012." An app's share of a requirement reads the same way: "The rider app's part of 'unlock a bike with a card on file': it checks the card and sends the unlock. Right?"

A state said to the lead is a word: just an idea, not decided yet, proposed, decided, confirmed.

## Acceptance

Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance. Before you close a branch, ask for an explicit yes or for an alternative. Before you write `decided`, read the final wording back and get a yes; for several items that close together, one read-back of about five and one yes to them is enough (`START.md` defines a yes).

Capture each answer, and your read-back, with `vela record add --origin <who> --tag thought "<words>"`; it prints the number section 4 hands to `vela decide`. The user's own words take their name as origin; your recommendation accepted as it stands is `claude, from <name>`; your read-back is `claude`.

## 2. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `grill`. Read the grill row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

If the lead names a challenge to answer, by its PR number or the challenged item, START will take its "Answer a challenge" path, on the challenge's own branch, with `modes: [answer, grill]`; read the Answer row of `MODES.md` too. The agenda holds the challenge's unknown and the challenged item. Resolve the unknown with the team lead as its owner, with the `resolve` kind. If the answer changes the item, set it back first with `vela decide --reopen <ID> --why ^cN`, then decide it again through the gate below.

## 3. The gate, per item

Run `vela check-slice --changed --for-lead` first. A finding on the item's slice blocks it unless the lead overrides it with a reason and an end date, which you record under the slice page's `## Overrides`. 'Not fully checked' blocks it too, and no override covers that. (`vela conventions "Flow check"` shows the override line.)

Then run `vela check --gate grill --item <ID> --for-lead`, repeating `--item` per item (an ID not in the plan exits 2). Per item it says ready, or not ready with the plain reason and the one thing that would make it ready, and lists the owed questions that block it, skipping any the record already answers. Relay it in two or three sentences, never as a table or a gate name: "The strategy page is ready. The three apps and their contracts aren't, because nobody knows yet when the registration request goes in and who builds consent and identity."

Left to you: a concern cell passes when the lead states what the initiative does for the app under it (`vela conventions "Concern cells and waivers"`); one they call `unchanged` or `n/a` is written as they say. For a missing case table, say it plainly ("Nobody has written down what Stock says back when the item is unknown") and offer to write it here, one case at a time with your recommendation, or to go back to Boundary (`vela conventions "Fact bullets"`).

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md` "on the agenda", and route its questions and the owed ones through REVIEW's digest (at most three questions at a time). An owed question is to ask, not a gate. If the lead decides with one still open, capture "decided with <copy IDs> open (W807)" with the lead as origin: that capture is the record.

**The agenda.** Show it with the open questions under each item and get an explicit yes. Capture the yes and file the agenda with the `agenda` kind; `decide` and `add unknown` keep it current, and START's resume reads it. Each item's owner says yes in person, or their async answer is captured with them as origin, channel and date; otherwise offer to reschedule, collect it first, or decide on their behalf.

**Not ready.** One sentence ("The Summarizer can't be decided yet: nobody has said how slow is too slow, and the product owner isn't here") and the one thing that would make it ready. For a blocking unknown, ask whether the lead knows the answer now (`MODES.md`, "Unknowns"). It stays off the agenda until the lead chooses. Never draft an ask, an email or a chase for the user to send.

**Deciding it anyway.** The lead may override anything (`START.md`). Offer "Decide it anyway (I'll note that the open question was skipped)", ask the reason once and capture it. Never refuse, and never ask twice. The rest of the grill runs as normal, read-back and yes included, and the override is filed with the decision in section 4. If the lead decides for an owner who isn't here, say how that ends. Tell the user the owner confirms later: "Ines can confirm it later by adding a 'Confirmed by' line to the page, or challenge it with /vela:challenge if she disagrees."

If no item passes and the user overrides none, do not start the grill: make no change to any page, say why, and offer Shape or stopping. If the lead takes neither, end as `MODES.md` says under "Unknowns".

## Handing an app over

When the lead grills an app's handoff, or `vela ladder` shows an app's pages reach `handoff`: in a reader copy (`vela role` says `reader`), stop and say "Only the plan's owner can hand an app to its team, because it records exactly what they accepted. Send <owner's name> a proposal instead.", taking the owner's name from `.vela/published.json`. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/grill/HANDOFF.md` and follow it.

## 4. Write each decision as its branch closes

When an item's branch closes, file it at once, before the next question.

1. Ask why, once, naming the item: "Why this one, in your words?" Capture the answer as said. If they say "as you suggested", ask what in it persuaded them. A declined reason is captured as given, and the check keeps warning, which is the honest record.
2. For a contract, ask where the provider stands and capture it: present, async with channel and date, asked in the PR, or "not consulted: <reason>" (`decide` won't file a contract without one). If anyone disagrees, capture their words; the item can still be decided.
3. Run `vela decide <ID> --readback ^cN --yes ^cM --why ^cK --for-lead`, adding `--provider ^cP` for a contract, `--dissent ^cJ` for a disagreement, and `--override <rule> --reason-from ^cR --until <date>` (with `--on-behalf @<owner>` for an absent owner) for anything the lead decided anyway. It runs the gate again, writes everything the decision needs (the reason word for word, the marker in a reader copy that the owner sees it before it counts), and commits. Relay its line.
4. Exit 3: it is already decided. Say so, and offer `vela decide --reopen <ID> --why ^cN` only if the lead wants to change their mind; that records the change of mind in the Changes table. Exit 1: relay the reasons and ask about the one that matters.

The same command takes a functional requirement, a release by its heading, a slice (it goes to `planned`, not decided; the later statuses are the teams', as `vela conventions "Slices"` says), an epic, and an app's allocated requirement as `CAP-nnn.FRn@APP-<slug>`, which you read back by name with the app's agenda.

If the decision shapes the whole design (the strategy, an app, a flow), also offer a decision record: say it is optional, and on a yes run `vela add adr --title "<what was decided>" --decides <ID> --capture ^cN`. Close fills it in.

## 5. A new unknown mid-grill

If a question turns up that nobody present can answer, run `vela add unknown --name "<short name>" --capture ^cN --owner <handle> --blocks <ID> --for-lead` (repeat `--blocks` for each item it holds up). It takes the items it blocks off the agenda and says which; relay that, offer to decide them anyway, commit the unknown at once with `vela close stage --checkpoint`, and go on with the rest.

If it blocks an item already decided, say plainly that the decision stands in doubt until the question is answered, and capture a follow-up note on it.

## Ends when

The agenda is empty or the user stops. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session".

## Never

- Never batch decisions to the end: each is filed as its branch closes.
- Never write `fact` from what someone said in the grill without a source; `decide` holds every other rule that used to be listed here.
