---
title: Shape
minutes: 15
summary: Two or three options to react to, and a pick that stays not decided
---
Shape gives you something concrete to react to. Claude lays out two or three options, never one and never more than three, and records the ones you turn down with the reason. What you pick stays "not decided yet" until a grill decides it.

::: type
```
/vela:shape the first release
```
:::

::: asks
Each option comes with what it does, costs and rules out, and what must be true for it to work. Then:

> Which of these would you pick, and what would make you drop it?

For the pick, Claude takes each "what must be true" line in turn: is it known (with a source), a belief, or an open question for someone?
:::

::: see
The Heron strategy page, with the options and the reasons for turning two down:

```
- **Options considered:** Follow-ups owed after client calls (picked); morning calendar briefing on the laptop: rejected, Sam's team would only use Heron if it works on client calls; briefing by invitation: rejected, people who have to hand things over by hand won't, so it is dead.
```

The page is still at `inkling`, so the lead recorded an override to go on to requirements anyway:

```
- **Override:** "If 04-solution-strategy.md is not decided, say so: requirements written against it may be written again." by @sim-lead on 2026-10-19: Go on—requirements will show us what questions the grill needs to ask anyway.
```
:::

::: checkpoint
The strategy page has an `Options considered` line naming what you picked and each option you rejected with its reason. Its state is still not decided.
:::

::: fold Why this step
Giving someone three choices gets better reactions than asking for requirements cold, and the rejected options keep the reason on the page. See [Shape][m-shape]. The override is how you're never blocked: you can go on, and the rule you set aside is named on the page ([overrides][m-over]).
:::

::: fold Stuck?
- `vela check --gate shape` warns `W806` for each question still marked assumed. A warning, not a stop: you may go on.
- `E303` means a page says decided with no grill behind it. Set it back to assumption.
:::
