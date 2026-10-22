---
title: Releases and epics
minutes: 20
summary: When people first see it, what must hold that day, and each team's work
---
Releases come first: a date someone outside the team will see, and the requirements, or only some of their checks, that must hold that day. Epics then cut the work for each team, each with a "done when" a tester can check.

::: sequence
skills: releases
Claude > vela: `vela releases brief`
Claude > You: "When do outsiders first see this?"
You > Claude: A date, and who they are
Claude > You: Must, can wait, or part?
You > Claude: Your answer for each
Claude > plan: Writes 04b-releases.md
:::

::: type
```
/vela:releases
/vela:epics
```
:::

::: asks
Releases asks one question at a time, date first:

> When does anyone outside the team first use this, and who are they?

Then, requirement by requirement: must be there, can wait, or only part. Epics reads back the checks a tester will use, with a recommended tightening, for example "within two minutes" in place of "as soon as it can be built".
:::

::: see
The first Heron release. Some requirements only come in part:

```
## Release one: February pilot, Client Delivery London
- **Target:** 2027-02-02
- **State:** assumption
- **Slices:** SLC-005

| Close a follow-up | AC1, AC2, AC3 | AC4 and AC5 in release two, no date yet |
```

`vela releases brief` says it back:

```
- Release one: February pilot, Client Delivery London: aimed at February 2, 2027, not decided yet; slices on by then: A person gets their first follow-up list; ...
- Release two: what the pilot leaves for later: with no date yet, early idea; slices on by then: none; ...
```
:::

::: checkpoint
`04b-releases.md` names each release with a date or "no date yet", and says which requirements it delivers. Each epic lists its owning team and its "done when" checks.
:::

::: fold Why this step
Nothing waits for a release; a release is a promise about a date. Writing it down is how a team learns that a requirement it thought was whole is only half due. See [Releases][m-releases] and [Epics][m-epics].
:::

::: fold Stuck?
- `W343` a requirement isn't decided yet and no release delivers it, so nothing says when it ships. Add it to the release that will deliver it, once nothing holds it back.
- `W347` a slice passes through an app that the release delivers no share of, so its journey can't run end to end by that date. The Heron plan has seven of these.
- `E805` a high-severity question is still pending at the epics gate. Answer it, or override with a reason under `## Question ledger`; the error then prints as `W805`.
:::
