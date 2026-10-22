---
title: Hand off an app
minutes: 10
summary: Give an app to its team lead, with what isn't settled said out loud
---
When an app is ready for its team, you grill its handoff. It records what the team lead accepts, and what isn't settled yet, so nobody finds out later.

::: sequence
skills: grill, grill/HANDOFF
You > Claude: Grill the app's handoff
Claude > vela: `vela handoff preview`
Claude > You: What the team takes and what's open
You > Claude: A yes to send it
vela > plan: `vela handoff` writes the record
:::

::: type
```
/vela:grill the Desktop agent's handoff
/vela:close
```
:::

::: asks
Claude reads back what the team is taking and what stays open, then asks:

> Hand the Desktop agent to its team lead, with these items not decided yet and this question still open. Yes to send it?
:::

::: see
The handoff record Heron wrote. It lists what the team accepted:

```
- **App:** APP-desktop-agent
- **Commit:** 8e30fa9
- **Items:** 7
| APP-desktop-agent | app | 05-building-blocks/desktop-agent-building-blocks.md | assumption | ec4c4412c80b |
| CON-021 | consumes | ... | assumption | 8eed90afa9ff |
```

Later, `vela handoff verify` says what moved since:

```
vela handoff verify APP-desktop-agent: since Desktop agent was handed off on 2026-10-19 at 8e30fa9, 2 things changed, 2 added and 0 removed.
changed: app Desktop agent (APP-desktop-agent): its wording changed
added: epic Setting Heron up in two minutes (EPC-038), ..., draft
```
:::

::: checkpoint
`handoffs/<app>.md` exists, the app page says who has it and when, and a "Not settled at handoff" list says what's still open.
:::

::: fold Why this step
A team that finds an undecided contract halfway through blames the plan. A team told on day one plans around it. See [handoff, challenge and answer][m-hand].
:::

::: fold Stuck?
- `W386` an item in the handoff list isn't decided. Decide it in a grill, or tell the team it isn't settled.
- `W388` the handoff record points at a commit this repository doesn't have. Commit your changes, then `vela handoff <app> --replace`.
- `vela handoff verify` exits 1 when something the team accepted has changed. That's a signal, not a failure.
:::
