---
title: Grill a decision
minutes: 15
summary: A grill is the only way something becomes decided
---
A grill is a working session where vela asks you questions one at a time until a part of the plan is settled. Only a grill can mark something decided, and only after your explicit yes.

::: type
```
/vela:grill Admin console
```
Name the thing by its name, as the plan calls it.
:::

::: asks
Each question comes with a recommended answer and a reason. Claude picks an edge case, not the happy path, and reads back what it would write:

> Record consent: the desktop agent asks for both choices, the calendar and the chosen folder, and keeps each with the time it was given. If saving doesn't answer within two seconds, the agent says "Couldn't save your choice, so nothing was switched on" and asks again at the next start. That's what I'll write as decided. Right?

Only a plain yes counts. "Looks fine" doesn't.
:::

::: see
A decision from the Heron plan. The state is `decided`, and the page links the grill session that decided it:

```
state: decided
...
## Decision
The Admin console is its own app. It shows what the Consent and identity service holds and keeps no consent record of its own.
...
- **Decision:** [[2026-10-19-tracer-slice-first-path]]
```
:::

::: checkpoint
The item says decided and has a `**Decision:**` line pointing at a grill session. No open question blocks it.
:::

::: fold Why this step
Without a gate, "decided" means whoever wrote it last. Here it means a named person said yes in a session that's on record. See [how only a grill decides][m-grill] and [what Claude may never do][m-never].
:::

::: fold Stuck?
- `E303` decided with no grill. Real output: `04-solution-strategy.md:6: E303 solution-strategy is decided, but no **Decision:** bullet links a Grill session. Fix: Add '- **Decision:** [[<grill session>]]', or set the state back to assumption.`
- `E316` decided while an open question blocks it. Answer the question first, or override the rule and say why.
- You can always override. Claude says once what the rule protects, does what you asked and records your reason. It never blocks you.
:::
