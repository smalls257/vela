---
title: A worked example
lede: One sentence from a CIO, followed through the ladder on the Heron demo plan, with the plan's real words at each step.
---

## What this is, and isn't

Heron is a desktop helper for the 4,200-person company Marlowe. The session simulator made the plan, so it demonstrates the format and its real check output. It isn't evidence from a real initiative, and its handles read `@sim-lead`.

::: fold Where the excerpts come from
The excerpts are word for word, shortened with "...". The demo plan isn't in this repository: it was generated at `/tmp/demo-vault`, and its numbers were read from it and its dashboard on October 21, 2026, on the `release-0.5` branch at commit `77940a68`. The committed worked example is [`examples/unified-booking/`](../../../examples/unified-booking/); run `vela check` and `vela explore` on it to see the same behavior.
:::

## Step through it

Use Next and Back, or the arrow keys.

::: steps heron | The Heron plan, step by step

::: step The ask
> The CIO wants "a desk helper for Mac and Windows that sets up in two minutes, quietly watches your meetings, email and documents, and tells you what matters each morning".

That's the only input. Everything after it is the ladder.
::: end step

::: step Dump: get it out of your head
The lead's thoughts, worries and unknowns are filed in their own words, and Claude's what-ifs are parked.

```
- [idea] (claude) What if the morning briefing came first and alone, built from just the calendar, ... → park ^c04
- [unknown] (solution lead) The CIO just gave me the one-liner and nothing since. Honestly not sure what morning they were picturing. → keep: UNK-055 (open) ^c08
```

The vague intent is now a recorded unknown with an owner. Nothing was decided.
::: end step

::: step Discover: what exists, and who disagrees
Each document goes into the Library with a kind.

```
| SRC-006 | Microsoft 365 tenant note | IT endpoint lead | 2026-10-02 | exists | document | ... |
| SRC-007 | CIO brief on Heron | CIO | 2026-09-30 | intends | document | ... |
```

Lines from the tenant note (`exists`) became facts, and lines from the CIO brief (`intends`) became assumptions. Where they disagreed, Discover didn't pick a side:

```
- [unknown] (claude) The CIO brief says staff install the helper themselves, while the tenant note says staff cannot install software and everything is pushed from Intune or Jamf. Two sources disagree; ... → keep: UNK-086 (open) ^c06
```
::: end step

::: step Shape, and an override
Shape recorded the pick, with the options it rejected and why.

> **Options considered:** Follow-ups owed after client calls (picked); morning calendar briefing on the laptop: rejected, Sam's team would only use Heron if it works on client calls; ...

The strategy page is still at `inkling`. The lead chose to write requirements against it anyway, which is an override on the page:

> **Override:** "If 04-solution-strategy.md is not decided, say so: requirements written against it may be written again." by @sim-lead on 2026-10-19: Go on—requirements will show us what questions the grill needs to ask anyway.

The rule was named, the person chose, the reason is on the page.
::: end step

::: step Requirements: what the business needs
```
### CAP-023.FR1 Summarize only fully opted-in calls

- **State:** assumption
- Heron summarizes a call only when every participant on it has opted in to Heron.
  - Trace: UNK-093
- A call with even one participant who hasn't opted in gets no summary.
```

No app, screen or technology. Its first criterion traces to the open question about whether clients can opt in, so the plan shows what this depends on.
::: end step

::: step Boundary, allocation, and an honest gap
The cut was four apps; the two- and three-app cuts were recorded with reasons. The first journey is drawn as a flow, FLO-001, in [five steps across the apps](joins.md#flows-are-journeys-across-the-joins).

This plan didn't get as far as allocation, so the check says so for each requirement, with the command to run:

```
W505 Delete data from a switched-off source (CAP-023.FR3) is not decided yet, but no app has taken it on (no Requirements allocated row), so no team owns it. Fix: Run /vela:allocate CAP-023, or add a row for CAP-023.FR3 to the app page that delivers it.
```
::: end step

::: step Releases and the tracer
Release one, the February pilot, is dated, points at the tracer slice (SLC-005), and says what waits:

```
- **Target:** 2027-02-02
- **Slices:** SLC-005

| Delivers | Criteria | Note |
|---|---|---|
| ... CAP-022.FR2 Close a follow-up | AC1, AC2, AC3 | AC4 and AC5 in release two, no date yet |
```

"Done" for the tracer means: "a pilot user signs in, switches meetings on, the tenant admin has approved transcript access, and the next morning the user sees what they promised on a client call."
::: end step

::: step A grill, and a hold
Claude read back what the Admin console is, and the lead said why and said yes:

```
- [thought] (@sim-lead) Out of hours is a service desk constraint anyway, and they're eight to six with no cover—doesn't change what the console is. → keep: APP-admin-console (decided) ^c02
- [thought] (@sim-lead) Yes. → keep: APP-admin-console (decided) ^c03
- [thought] (claude) Lead decided with Q-DAT-02@APP-admin-console and Q-OPS-01@APP-admin-console still open (W807). → park ^c05
- [thought] (@sim-lead) Hold it. The services aren't named and the flow isn't drawn → drop: The lead's hold on the Desktop agent; ... ^c06
```

The lead held the Desktop agent back and Claude didn't push it through. The console was decided with two catalog questions still open, and the session recorded that as W807.
::: end step

::: step Handoff, with what isn't settled
The Desktop agent was handed to its team before its contracts were decided, as a recorded override. The record lists what the team accepted:

```
## Not settled at handoff

- Desktop agent (APP-desktop-agent) is not decided yet: nobody has said yes to it.
- Sign-in token (CON-021) is not decided yet: nobody has said yes to it.
- Desktop agent calls Call items (CON-025) on Heron service, but no team has taken Heron service or designed it yet, so there is no design behind those calls to build against.
```
::: end step

::: step Epics, and the stricter check
The epic's criteria are things a tester could read over the phone, each with a trace line:

```
Each morning a person sees every promise they made on a client call that they haven't marked done or dropped. ...

- Trace: CAP-022.FR1, CON-025  ·  AC1
```

Then the stricter check refuses to call the epics finished:

```
E805 A high-priority question hasn't been dealt with yet (it has no row in the question ledger), so the epics can't be called finished: What customer data does it hold or receive, and on what lawful basis may it use that data? (Q-DAT-02@APP-desktop-agent) ...
```

A plain `vela check` on the same plan says "0 errors, 54 warnings." The stricter one says 29 errors. Both are true, and they answer different questions.
::: end step

::: step Design, breakdown and tickets
The team's design is `complete-with-gaps` and names each guess as a guess. The breakdown puts the tracer first, and says where it rests on less than it should: "S-06, S-07 and S-08 rest on the design alone: no requirement in the vault says when they are done." The ticket for S-01 says "Release fit: cannot tell for 2027-02-02," with its reason.
::: end step

::: step What a reader sees
The dashboard shows the map of the four apps, the flow playing step by step, "2 of 18 items settled and 0 of 49 questions answered," and who holds each answer. The plan doesn't claim to be further along than it is. That is the whole point.
::: end step

::: end steps

## What to notice

- **Every rule showed up as a recorded line.** The override, the on-behalf decision, the disagreeing sources: each is on a page with a name and a date.
- **The plan names its own holes,** and the command that closes each.
- **Two checks, two meanings.** Well formed is not finished.
- **Numbers carry a date.** Counts here were read October 21, 2026, and will drift.

## Try it on a committed plan

Run `vela check` and `vela explore` on [`examples/unified-booking/`](../../../examples/unified-booking/), then read [from idea to tickets](ladder.md) with the dashboard open beside it.
