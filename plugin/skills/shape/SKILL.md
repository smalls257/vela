---
name: shape
description: "Lay out 2 or 3 options with trade-offs, record the rejected ones, keep the chosen one as not decided yet unless the lead settles it. Offer it when someone roughly knows what they want; start it only on a yes."
argument-hint: "<area, app or item>"
---

# Shape

Give the user something concrete to react to. What it settles stays an `assumption` (to the lead, "not decided yet") unless the lead settles it.

1. Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `shape`. Read the Shape row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.
2. Read the area's pages, its ADRs and parked captures.
3. Draft 2 or 3 strawman options, never one and never more than three. For each, write in two or three lines what it does, costs and rules out, and where the work is done: on the person's device, in a shared service, in an admin or support view, and who keeps consent and identity. Each option also says which flow would prove it first, end to end. If the user or a source named separately run or owned parts, an option that merges them says so as a cost.

   Capture each option for the reviewers: `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela record add --origin claude --tag thought "<the option>"`.
4. Before you show them, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "before options" and this focus: for each option, what must be true for it to work, about customers, capabilities, money, data, partners, regulators, counterparties and the teams that run it. Each reviewer quotes the option's capture, so every finding stays tied to its option. The findings quoting an option are its "what must be true" set.
5. Show the options. Name each by its plain name, never its ID. For each, give what it does, costs and rules out, and only the top few conditions from its "what must be true" set, each with its focus area. Say the merge's coverage line in plain words: which areas found something, which ran and found nothing, and which did not run and why. Send the rest of the conditions through the one digest (REVIEW section 5). Say which option you prefer and why.

   > **Unlock at the dock.** The dock reads the rider's card itself, so it works when the phone signal drops; every dock needs a reader fitted. Holds only if the card processor certifies the dock readers (partners). My pick: riders without a phone can still ride.

6. Capture the user's reaction to each option, with their name as origin.
7. When the user picks one, capture it. If they accept your preferred option as it stands, the origin is `claude, from <name>`. Each rejected option gets a capture with its reason. If they reject all, capture why and offer new options.
   For the picked option, take each line of its "what must be true" set in turn. The user says it is known, with a source; is a belief, and whether the plan rests on it; or is an open question for someone. Capture each answer starting with its finding ID. Close writes a belief as an `assumed` ledger row with `load-bearing:` and a signpost.
8. On "that's decided" or "settle it", settle it as `${CLAUDE_PLUGIN_ROOT}/references/SETTLE.md` says.
9. On a plain yes to a pick, offer once to settle it (SETTLE.md).
10. Write nothing to a page during the session, except a pick the lead settles: `vela decide` files it then. At close the picked option becomes an `assumption` item with an `**Options considered:**` bullet naming the picked option and each rejected one with its reason. When the lead picks an option, draft the paragraph its item will carry now, as `START.md` says under "Draft the paragraph when the item is filed", and show it with the pick; close writes it to the page.
11. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Close runs `vela check --gate shape`; tell the lead only that close will list what is still assumed.
