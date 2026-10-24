---
name: grill
description: "Decide ready items one question at a time, each with a recommended answer held under pushback; the only session that sets decided. Offer it when someone wants an open question settled; start it only on a yes."
argument-hint: "<item IDs or page names to decide>"
---

# The grill

A grill is the only session that makes an item `decided` (say what the word means once, from `vela terms`). It takes the ready items, and any the lead decides anyway, one question at a time, and files each decision as its branch closes.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `grill`, and read the grill row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. A kind with no command of its own is filed with `vela apply` (`--schema <kind>` gives the file).

## 1. The questions

- Ask one question at a time, then *Recommended: <answer>. <one-line reason>.* Wait. Look things up in the plan rather than ask.
- Force a precise answer at the item's edge, not the happy path; frame it as a hypothetical ("Suppose it's 8:58, the call starts at nine, and the calendar service doesn't answer. What does the person see?"). Build it only from what the plan, the inbox or the lead has said. Never state a new dated event, or what a third party reported, as if it had happened.
- Check each answer against the plan and what the lead said earlier. Say so when they disagree.
- Recommend an answer, not "hold" or "keep it open", unless the gate says the item isn't ready.
- Keep your recommendation when the user pushes back without a reason. Change it only for a reason, and say what the reason was.
- Never answer your own question.

Say names, not IDs, in your own words too. A read-back by name:

> Record consent: the desktop agent asks for both choices, the calendar and the chosen folder, and keeps each with the time it was given. If saving doesn't answer within two seconds, the agent says "Couldn't save your choice, so nothing was switched on" and asks again at the next start. That's what I'll write as decided. Right?

Not: "CON-003 (Dock unlock): decided, GATE-5 overridden, see UNK-012." An app's share of a requirement reads the same way: "The rider app's part of 'unlock a bike with a card on file': it checks the card and sends the unlock. Right?"

**Acceptance.** Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance. Before you close a branch, ask for an explicit yes or an alternative; before anything is decided, read the final wording back and get a yes (items that close together can share one read-back of about five). Capture each answer and your read-back with `vela record add --tag thought "<words>"`.

## 2. Open with a ready item

Items the brief lists as ready to decide come first. Open the agenda with them, and still read each wording back for its own yes. On turn 1 run `vela check --gate grill --all --for-lead` and open with a ready item as a proposal: "I'd decide <item> as <answer>, because <reason>. OK?" Recaps and reading come after that, or only if needed. If nothing is ready, say so in one line and ask the question that would make the nearest item ready. When an answer settles an item that isn't ready, offer to decide it anyway in that same turn, with its read-back: "That settles <item>. It isn't ready because <reason>. Decide it anyway?" Never file a settling answer as a note without that offer.

Answering a challenge, START will take its "Answer a challenge" path (read the Answer row too): resolve its unknown with the team lead as owner, with the `resolve` kind; if the answer changes the item, reopen it (`vela decide --reopen <ID> --why ^cN`) and decide it again.

## 3. The gate and the agenda

Run `vela check-slice --changed --for-lead`, then `vela check --gate grill --item <ID> --for-lead`, repeating `--item` per item. Relay it in two or three sentences, never as a table: "The strategy page is ready. The three apps and their contracts aren't, because nobody knows yet when the registration request goes in and who builds consent and identity."

Left to you: a concern cell passes when the lead says what the initiative does for the app under it; one they call `unchanged` or `n/a` is written as they say. For a missing case table, write it here one case at a time with your recommendation, as the gate offers, or go back to Boundary.

**The agenda.** Show it with the open questions under each item, in groups past about seven (the lead may take it in two sessions), and get an explicit yes; capture both, and file it with the `agenda` kind; a yes right after the agenda is accepted in that turn, so never ask for it again. Each item's owner says yes in person, or their async answer is captured with them as origin, channel and date; otherwise offer to reschedule, collect it first, or decide on their behalf.

**Not ready, or decided anyway.** The gate says why an item isn't ready; it stays off the agenda until the lead chooses. Offer "Decide it anyway (I'll note that the open question was skipped)", ask the reason once and capture it. Never refuse, and never ask twice. The rest of the grill runs as normal, read-back and yes included. When the lead decides for an owner who isn't here, say how that ends: "Ines can confirm it later by adding a 'Confirmed by' line to the page, or challenge it with /vela:challenge if she disagrees."

If no item passes and the user overrides none after you offered it for each item their answers settled, do not start the grill: make no change to any page, say why, and offer Shape or stopping.

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md` "on the agenda" after the first decision or a natural pause, never on turn 1. An owed question is to ask, not a gate; if the lead decides with one still open, capture "decided with <copy IDs> open (W807)" with the lead as origin: that capture is the record.

## Handing an app over

When the lead grills an app's handoff, or `vela ladder` shows an app's pages reach `handoff`, read `${CLAUDE_PLUGIN_ROOT}/skills/grill/HANDOFF.md`.

## 4. File each decision as its branch closes

Before the next question:

- Ask why, once, naming the item: "Why this one, in your words?" "As you suggested" gets one more question: what in it persuaded them. A declined reason is captured as given.
- For a contract, ask where the provider stands (here, async with channel and date, asked in the PR, or not consulted and why) and capture it. Capture anyone's disagreement in their words; the item can still be decided.
- When the yes, or a disagreement, came from someone other than the lead, ask that person once: "May I put your words on the plan, or should I just say that you agreed? Say yes in your own words if I may." Capture the answer with them as origin, `--tag quote-yes`. A yes the lead passes on for them doesn't count; a no is fine, and the plan then says who agreed without their words.
- Run `vela decide <ID> --readback ^cN --yes ^cM --why ^cK --for-lead`; `--help` lists the flags for a contract, a dissent, an override and an absent owner, and the other kinds it takes (a requirement, a release, a slice, an epic, an app's share). Read an app's share back by name with the app's agenda.
- When the decision shapes the whole design (the strategy, an app, a flow), offer a decision record, optional: `vela add adr`.
- Draft the paragraph the item owes, as `START.md` says under "Draft the paragraph when the item is filed", and show it with the filed line.

A question nobody present can answer is an unknown: `vela add unknown --capture ^cN --blocks <ID> --for-lead`. Relay what it takes off the agenda, offer to decide those anyway, run `vela close stage --checkpoint`, and go on. If it blocks an item already decided, say plainly that the decision stands in doubt until it's answered, and capture a follow-up note.

## Ends when

The agenda is empty or the user stops; close as `START.md` says under "Closing a session".
