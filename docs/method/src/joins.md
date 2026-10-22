---
title: Hand-offs and slices
lede: A plan for several apps is mostly a map of hand-offs between apps, and between people. Who sends what to whom, what comes back, and what happens when it doesn't. Vela treats those joins as items with their own rules, and builds the product as thin end-to-end paths first.
---

## A contract lists every answer

A contract is the agreed interface between two apps: what crosses, who consumes it, a change policy, and a case table of every way the provider can answer.

In the Heron service's Call items contract, "nothing new" and "a call that couldn't be read" are separate answers from "new items." A consumer who read an empty list as "all clear" would be wrong when a call went unread. The table forces the question "and when it can't?" before anyone builds. It is the empty-versus-missing failure from [the problem](problem.md), written where both teams can see it.

::: fold The Call items case table, word for word
```
| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| new_items | | ok | redacted items from calls since the last sync, each with the call's name and date | | |
| nothing_new | | ok | an empty answer, because nothing has come in since the last sync | | |
| call_not_read | | ok | the name and date of a client call that couldn't be read, with no content, so the agent can show it as not checked | | |
| not_signed_in | | error | refused, because there is no valid token | | |
```
:::

::: fold Where this is stated and enforced
Stated in [Fact bullets][c-facts]. Enforced by W380 for a missing case table and W386 in the handoff list. Pinned by [`test_cases.py`][t-cases] and [`test_handoff_warnings.py`][t-handoff_warnings].
:::

## Flows are journeys across the joins

A flow lists who sends what to whom over which contract. Step through the demo plan's first one, or click an app to jump to its first step.

::: flow flo001 | The first flow, FLO-001
::: node ci | Consent and identity | 210 | 36
::: node da | Desktop agent | 72 | 130
::: node hs | Heron service | 348 | 130
::: node ac | Admin console | 210 | 214
::: step ci>da | Sign-in token | Sign in
The consent service sends a short-lived token when the desktop agent signs in.
::: end step
::: step da>ci | Opt-in choice | Opt in
The agent sends the person's choice to switch a source on. Nothing is read until the consent service has recorded it.
::: end step
::: step hs>ci | Read permission | Ask whether it may read
The Heron service and the consent service settle read permission, over the Read permission contract.
::: end step
::: step hs>ci | Access status report | Report access status
The Heron service sends the consent service its access status report.
::: end step
::: step hs>da | Call items | Hand over the call items
The Heron service sends the agent the call items, over the contract with the four answers above, so the agent can show a call as "not checked" instead of "all clear."
::: end step
::: step ci>ac | Consent overview | Beyond the first flow
Not one of the five steps. The admin console relies on the consent overview, so the join is on the map.
::: end step
::: end flow

The check holds each pair of apps to the contract it names (E350). Two apps named with no contract draw a warning (W374), because "who hands what to whom" isn't recorded.

::: fold The dashboard's version of this map
![The dashboard's map of the four Heron apps and the contracts between them](dashboard-map.png)

![A flow played step by step in the dashboard](dashboard-flows.png)
:::

::: fold Where this is stated and enforced
Stated in [Flow steps][c-fsteps]. Enforced by E350, E351, W351 and W374 ([rules.py][rules]). Pinned by [`test_capture_rules.py`][t-capture_rules], [`test_flow_ends.py`][t-flow_ends].
:::

## The flow check finds gaps before anyone builds

When a flow is drawn as a strict sequence diagram and its contracts have case tables, `vela check-slice` can prove things about the plan: every answer a provider can give is handled, every event has a consumer, nothing is left half done. It reads the plan, never the code, and runs in seconds.

It is strict about input. A line it can't read makes the slice "not fully checked," which blocks deciding it until the lead overrides with a reason and an end date. The demo plan's first slice is there ("SLC-005 ... not fully checked"), because its flow isn't drawn strictly yet. The tool says what it couldn't check.

::: fold Where this is stated and enforced
Stated in [Flow check][c-fcheck] and the grill skill's gate step ([grill][s-grill]). Enforced by `vela check-slice` ([flowcheck/][flowcheck-dir]). Pinned by [`test_flowcheck.py`][t-flowcheck], [`test_flowcheck_changed.py`][t-flowcheck_changed].
:::

## Slices: thin and end to end, first

Most plans are built a layer at a time: each team finishes its app, the apps meet at the end, and contract surprises arrive when they cost most. A **slice** is one thin piece of the product built end to end, so it can ship and be tried alone. The **tracer** is the first: one path through every app and contract it needs, built first and kept. The name comes from *The Pragmatic Programmer* [4], the one-system version is Cockburn's "walking skeleton" [5], and putting the tracer first is vela's own design choice, not a measured result.

- **The riskiest joins get proved early.** If the consent check or the call-items contract is wrong, the tracer shows it in the first weeks.
- **Every team gets a first story that matters.** Story one is the team's piece of the tracer. A story that is only a layer (a gate, a schema, a screen with nothing behind it) is flagged and folded into the slice that needs it.
- **Slices are the unit of done, and a release is a milestone.** "Nothing waits for a release; a slice switches on when its journey passes."

The demo plan's tracer (SLC-005) walks the flow above: it cuts across three apps and uses each of their contracts once. It does very little, but it runs.

::: fold Not ready? Say so. And the gap the check points at
Sometimes a piece isn't ready, such as transcripts waiting on a legal ruling. The slice page has a `## Not in this slice` section with one bullet and reason per piece. Nothing stops the session.

Vela also warns when the tracer passes through an app that release one delivers nothing of (W347). On October 21, 2026, it gave the demo plan that warning eight times. The tool points at the gap and doesn't hide it.
:::

::: fold Where this is stated and enforced
Stated in [Slices][c-slice], [Releases][c-rel] and the explainer [`tracer-bullets.html`][tracer-explainer]. Enforced by W345, W347, W348 ([rules.py][rules]) and the [breakdown skill][s-breakdown]. Pinned by [`test_slices.py`][t-slices] and [`test_tracer.py`][t-tracer].
:::

## Two roles, one rule

**The solution lead** owns the whole: boundaries, contracts, flows, edge behavior and slices. "Solution design is mine; app design is theirs." They run the sessions, decide in grills, and write the handoff.

**The team lead**, a senior engineer, takes one app: its page, contracts, allocated requirements, epics, slices and the open questions blocking any of them. They design and plan inside it with `/vela:design`, `/vela:breakdown` and `/vela:tickets`.

Neither reads the other's whole world. Access decides role: an **owner** works in the vault's git clone, and a **reader** works in a published copy with no git, whose decisions stay pending until an owner clears them. Vela never sends anything; people move the files.

::: fold Where this is stated and enforced
Stated in [Roles and published copies][c-roles], [Pending approval][c-pend] and [Handoff][c-hand]. Enforced by `vela role`, which reads access and never a title. Pinned by [`test_roles.py`][t-roles] and [`test_pending.py`][t-pending]. The quotation is from the owner's philosophy notes (not in the repository).
:::

## Handoff, challenge and answer

The hand-off between people is recorded, and so is disagreement. A challenge is how a team lead disagrees without it being a complaint filed somewhere. Step through one.

::: steps challenge | A hand-off and a challenge
::: step The lead decides the app
The solution lead decides the app and its contracts in a grill.
::: end step
::: step The lead hands it over
The lead names the team lead who takes it, and `vela handoff` records everything accepted with a fingerprint of each item's text. Re-rendering a page changes no fingerprint.
::: end step
::: step The team designs inside
The team lead designs inside the app and traces every component to the list.
::: end step
::: step The team lead challenges
`/vela:challenge` quotes their words and writes one open question they own that blocks the item, plus a `**Dissent:**` line. It leaves the item's state and text alone.
::: end step
::: step The check stays red
The check fails (E316) until the solution lead answers, on purpose: a challenge shouldn't merge while main still says "decided" with an open blocker.
::: end step
::: step The lead answers
The lead answers on the challenge's own branch, either by deciding in a grill or by setting the item back. Close pushes to that branch and doesn't open a second pull request.
::: end step
::: step Everyone sees what changed
`vela handoff verify` shows exactly which accepted item changed.
::: end step
::: end steps

An owner whose item was decided on their behalf has the same two answers: a `Confirmed by:` line, or a challenge. The dashboard's "Needs you" list shows each role up to five things to act on. Frequent stepping in by the solution lead is, in the owner's reasoning, "a capacity problem to escalate, not absorb."

::: fold Where this is stated and enforced
Stated in [the challenge skill][s-challenge], [ANSWER-A-CHALLENGE.md][answer], [Handoff][c-hand] and [Overrides][c-over]. Enforced by `vela handoff verify`, E316, E322 and W324. Pinned by [`test_handoff.py`][t-handoff], [`test_challenge.py`][t-challenge], [`test_answer.py`][t-answer], [`test_override.py`][t-override], [`test_needsyou.py`][t-needsyou].

The plan records decisions and their reasons, not runtime state: "we switched the slice on, here's who and why" belongs in it, "the flag is on right now" belongs to the flag tool (from the owner's philosophy notes).
:::
