---
title: The problem: why plans go wrong
lede: Between one sentence from a boss and the first ticket, five things go wrong, and they usually go wrong together. Vela is built so each one fails in the open instead of in silence.
---

## Vague intent

"A desk helper that tells you what matters each morning" could be a calendar briefing, a list of promises made on client calls, or a reminder service. Each is a different product with different apps behind it, and nobody notices until someone builds one.

In the demo plan the lead wrote it down as it happened: "Honestly not sure what morning they were picturing." That became a recorded question with an owner. *Vela's answer:* [a first session that organizes nothing](ladder.md).

## Decisions nobody recorded

Someone agrees in a meeting that the admin view is its own app. Three weeks later a second team assumes it lives inside the main service. The decision was real but left no trace, so nobody can find it, question it or reverse it on purpose. *Vela's answer:* [only a grill decides, and it keeps the why](certainty.md).

## Guesses passed off as facts

The lead quotes "71 percent of staff missed a follow-up" from memory, and by page two everyone cites it. The demo plan's goals page says instead: "That's a belief, not a fact, because nobody has read the survey report." *Vela's answer:* [every item has a state, and a fact has a source](certainty.md).

## Apps that disagree on their edges

Team A thinks Team B's service never returns an empty answer. Team B thinks "empty" is normal and Team A will cope. Both are reasonable, and the product breaks at the join. *Vela's answer:* [contracts list every answer, and flows are checked](joins.md).

::: fold Where this story comes from
From the owner's philosophy notes (not in the repository): one team assumed an account already existed, the answer came back empty, the code read "empty" as "fine", later work built on it, and nobody owned the logic across teams.
:::

## Work with no traceable reason

Six months in, a developer asks why a story exists. If the answer is "someone said so", nobody can safely change it or drop it. *Vela's answer:* [every story traces back to a goal](trust.md).

::: fold Where these five are stated
The repository's own summary lists them: late questions, decisions never written down, open questions with no owner, beliefs treated as facts, work falling between teams, and stale notes ([PHILOSOPHY.md, "The problem, briefly"][phil]). The remedies are in [Certainty and sources][c-cert], [Questions and the ledger][c-q], [Fact bullets][c-facts] and [Epics and traceability][c-epic].
:::

## Three beliefs under everything

The owner's reasoning, which the design follows.

1. **Assumptions are made visible, or they become incidents.** Each is written down and checked, or recorded with an owner and a date. "Empty" and "missing" are never the same thing.
2. **Boundaries carry behavior, not just shape.** If a contract doesn't say what each answer means, it isn't agreed.
3. **Someone owns the whole.** The solution lead holds the logic between teams, and the plan is where it lives.

::: fold Where these are stated and enforced
The beliefs are from the philosophy notes. The repository turns them into rules: an assumption must carry an owner or a signpost ([ledger rows][c-q]), contracts list every answer ([Fact bullets][c-facts], pinned by [`test_cases.py`][t-cases]), and the lead holds the whole while teams hold their apps ([Handoff][c-hand], [PHILOSOPHY.md][phil]).
:::
