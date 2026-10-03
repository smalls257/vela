---
name: shape
description: Shape session for an initiative vault. Offers 2 or 3 strawman options with trade-offs for one area, records the rejected ones with reasons, and leaves the chosen one at assumption for a later Grill. Use when the user roughly knows what they want.
argument-hint: "<area, app or item>"
disable-model-invocation: true
---

# Shape

Give the user something concrete to react to. Shape never decides: what it settles is an `assumption` until a Grill.

1. Run the steps in `.claude/skills/planner/references/START.md` with mode `shape`. Read the Shape row of `.claude/skills/planner/references/MODES.md`.
2. Read the area's pages, the ADRs that touch it, and parked captures about it.
3. Offer 2 or 3 strawman options, never one and never more than three. For each, give what it does, what it costs and what it rules out, in two or three lines. Say which one you prefer and why.
4. Capture the user's reaction to each option, with their name as origin.
5. When the user picks one, capture it. Each rejected option gets a capture with its reason. If they reject all of them, capture why and offer a new Shape with different options.
6. If the user says "that's decided", capture it as `[thought] (<name>) that's decided, grill to confirm`. The item stays at `assumption`. Tell the user a Grill makes it `decided`, and offer `/planner:grill <ID>`.
7. Write nothing to a page during the session. At close the picked option becomes an `assumption` item with an "Options considered" list naming each rejected option and its reason.
8. Tell the user: "Run `/planner:close` to finish the session and open the PR."
