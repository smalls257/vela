---
title: Write tickets
minutes: 15
summary: The team lead designs and breaks down the work; vela turns it into tickets
---
The team lead takes it from here, in three sessions on the app's own branch: a technical design, a breakdown into stories and tasks, and the ticket list. You can run them yourself to see the result.

::: sequence
skills: tickets
Claude > vela: `tickets check`
Claude > You: What doesn't line up, four at a time
You > Claude: Fix it, or go on and say so
Claude > You: A Markdown list or a Jira CSV?
You > Claude: Your pick
vela > plan: `tickets write` makes tickets.md
:::

::: type
```
/vela:design Desktop agent
/vela:breakdown
/vela:tickets
```
:::

::: asks
Tickets first checks the plan against the plan, then asks:

> I'd write one Markdown file with a section per story. Or a CSV for Jira import. Which one?
:::

::: see
`vela tickets check` on the Heron plan:

```
Needs fixing: Story S-06 isn't linked to an epic's acceptance criterion or to a requirement the app owns, so nothing in the plan says when it's done
...
10 stories, 49 tasks, 3 flagged
```

The ticket file it writes:

```
## S-01 A person sees a first follow-up list
- Slice: tracer, SLC-005 A person gets their first follow-up list
- Traces to: CAP-022.FR1@APP-desktop-agent, CON-021, CON-022, CON-025, EPC-036.AC1, ...
- Release fit: cannot tell for 2027-02-02.
```
:::

::: checkpoint
`docs/work/tickets.md` lists every story with its criteria, size and what it waits on, and each one traces to a goal.
:::

::: fold Why this step
The plan is the source of truth and tickets are copies. See [breakdown and tickets][m-tickets] and [how every story traces back][m-trace].
:::

::: fold Stuck?
- A plan that is still moving gets no ticket list. Tickets stops and offers `/vela:breakdown`.
- `vela tickets check` exits 1 when it flags something. That's a result, not a failure.
- `vela export jira-csv --out epics.csv` writes one row per epic for Jira's CSV import. Nothing is read back.
:::
