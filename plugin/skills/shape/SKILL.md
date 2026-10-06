---
name: shape
description: Shape session for an initiative vault. Offers 2 or 3 strawman options with trade-offs for one area, each with what must be true for it to work, records the rejected ones with reasons, and leaves the chosen one at assumption for a later Grill. Use when the user roughly knows what they want.
argument-hint: "<area, app or item>"
disable-model-invocation: true
---

# Shape

Give the user something concrete to react to. Shape never decides: what it settles is an `assumption` until a Grill.

1. Run the steps in `.claude/skills/planner/references/START.md` with mode `shape`. Read the Shape row of `.claude/skills/planner/references/MODES.md`.
2. Read the area's pages, the ADRs that touch it, and parked captures about it.
3. Draft 2 or 3 strawman options, never one and never more than three. For each, write what it does, what it costs and what it rules out, in two or three lines, as captures with origin `(claude)` under a `[thought]` tag, one per option, so the reviewers can read them.
4. Before you show them, run the review checkpoint in `.claude/skills/planner/references/REVIEW.md`, with the checkpoint "before options" and this focus: for each option, what must be true for it to work, about customers, capabilities, money, data, partners, regulators, counterparties and the teams that run it. Each reviewer quotes the option's capture, so every finding stays tied to its option. The findings quoting an option are its "what must be true" set.
5. Show the options. For each, give what it does, what it costs, what it rules out, and only the top few conditions from its "what must be true" set, each with its focus area. Say the merge's coverage line in plain words: which areas found something, which ran and found nothing, and which did not run and why. Send the rest of the conditions through the digest in REVIEW section 5 and name the command: `python3 .claude/skills/planner/bin/planner questions --open --digest`. A long digest shows its high and blocking lines in full and counts the rest by area; `--all` prints every line. Say which option you prefer and why.
6. Capture the user's reaction to each option, with their name as origin.
7. When the user picks one, capture it. If they accept your preferred option as it stands, the origin is `claude, from <name>`, per START. Each rejected option gets a capture with its reason. If they reject all of them, capture why and offer a new Shape with different options.
   For the picked option, take each line of its "what must be true" set in turn. The user says it is known, with a source; is a belief, and whether the plan rests on it; or is an open question for someone. Capture each answer starting with its finding ID. Close writes a belief as an `assumed` ledger row with `load-bearing:` and a signpost.
8. If the user says "that's decided", capture it as `[thought] (<name>) that's decided, grill to confirm`. The item stays at `assumption`. Tell the user a Grill makes it `decided`, and say: "After close, run `/planner:grill <ID>`", or name the page and heading if the item has no ID yet.
9. Write nothing to a page during the session. At close the picked option becomes an `assumption` item with an `**Options considered:**` bullet naming the picked option and each rejected one with its reason.
10. Tell the user: "Run `/planner:close` to finish the session and open the PR." Close runs `planner check --gate shape`, which warns on each question still `assumed`: an assumption clears into a decision, a requirement or a constraint the shape gate will warn until it does.
