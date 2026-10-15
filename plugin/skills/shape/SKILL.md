---
name: shape
description: Offer 2 or 3 options with trade-offs and what must be true for each, record the rejected ones, and keep the chosen one as not decided yet until a grill decides it. Use when the user roughly knows what they want.
argument-hint: "<area, app or item>"
disable-model-invocation: true
---

# Shape

Give the user something concrete to react to. Shape never decides: what it settles stays an `assumption` (to the lead, "not decided yet") until a grill decides it.

1. Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `shape`. Read the Shape row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.
2. Read the area's pages, its ADRs and parked captures.
3. Draft 2 or 3 strawman options, never one and never more than three. For each, write in two or three lines what it does, costs and rules out, and where the work is done: on the person's device, in a shared service, in an admin or support view, and who keeps consent and identity. Each option also says which flow would prove it first, end to end. If the user or a source named separately run or owned parts, an option that merges them says so as a cost.

   Capture each option for the reviewers: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela record add --origin claude --tag thought "<the option>"`.
4. Before you show them, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "before options" and this focus: for each option, what must be true for it to work, about customers, capabilities, money, data, partners, regulators, counterparties and the teams that run it. Each reviewer quotes the option's capture, so every finding stays tied to its option. The findings quoting an option are its "what must be true" set.
5. Show the options. Name each by its plain name, never its ID. For each, give what it does, costs and rules out, and only the top few conditions from its "what must be true" set, each with its focus area. Say the merge's coverage line in plain words: which areas found something, which ran and found nothing, and which did not run and why. Send the rest of the conditions through the one digest (REVIEW section 5). Say which option you prefer and why.

   > **Agent on each laptop.** Reads the calendar on the device, so client data stays there; IT supports an install. Holds only if the works council accepts local reading (data). My pick: consent stays with the person.

6. Capture the user's reaction to each option, with their name as origin.
7. When the user picks one, capture it. If they accept your preferred option as it stands, the origin is `claude, from <name>`. Each rejected option gets a capture with its reason. If they reject all, capture why and offer new options.
   For the picked option, take each line of its "what must be true" set in turn. The user says it is known, with a source; is a belief, and whether the plan rests on it; or is an open question for someone. Capture each answer starting with its finding ID. Close writes a belief as an `assumed` ledger row with `load-bearing:` and a signpost.
8. On "that's decided", capture `[thought] (<name>) that's decided, grill to confirm`. The item stays at `assumption`. Tell the user a grill decides it: "After close, run `/vela:grill <name>`" by the item's name ("/vela:grill Desktop agent").
9. Write nothing to a page during the session. At close the picked option becomes an `assumption` item with an `**Options considered:**` bullet naming the picked option and each rejected one with its reason.
10. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Close runs `vela check --gate shape`; tell the lead only that close will list what is still assumed.
