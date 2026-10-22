---
title: Dump
minutes: 20
summary: Get everything out of your head, ideas and worries and unknowns alike
---
A dump is the first session. You talk, Claude writes each point down as its own numbered line in your words, and pushes back on nothing. Nothing reaches the plan's pages until you close the session.

::: type
In Claude Code, in the plan folder:

```
/vela:dump
```

Say the CIO's sentence, then what you're unsure of. When you're done: `/vela:close`.
:::

::: asks
Claude adds one "what if" per idea and labels it as its own. After a while it runs a pre-mortem:

> Imagine it's six months from now and Heron has failed. What went wrong?

Then it shows the questions nobody has asked yet, and you choose which to take.
:::

::: see
Captures from the Heron dump, after close. Each line says who said it, and where it went:

```
- [thought] (solution lead) The CIO wants "a desk helper for Mac and Windows that sets up in two minutes, ..." → keep: [[01-goals#Goals|goals]] (inkling) ^c01
- [worry] (solution lead) I've been made solution lead and it's a blank page. I don't know where to start. → keep: UNK-052 (open) ^c02
- [idea] (claude) What if the morning briefing came first and alone, built from just the calendar, ... → park ^c04
- [unknown] (solution lead) The CIO just gave me the one-liner and nothing since. Honestly not sure what morning they were picturing. → keep: UNK-055 (open) ^c08
```
:::

::: checkpoint
You have a session record under `sessions/` with your lines in it, and Claude's ideas are labeled `(claude)`. After close, each line ends in `keep`, `park` or `drop`, and every unknown you kept has an owner.
:::

::: fold Why this step
The vague intent becomes a recorded unknown with an owner, so it can't turn into a decision nobody made. Dump is the first rung of [the ladder][m-dump]. The plan marks the CIO's sentence `inkling`, a hunch: see [how sure each thing is][m-cert].
:::

::: fold Stuck?
- I said something and it isn't on any page yet. That's right: a dump writes nothing outside `sessions/` until `/vela:close`.
- `E207` means an ID reference resolves to nothing, usually a mistyped `UNK-` number in a capture.
- `E201` means a link goes to a page that doesn't exist. Real output: `01-goals.md:124: E201 [[no-such-page]] links to a page that does not exist. Fix: Fix the basename, or create the page.`
:::
