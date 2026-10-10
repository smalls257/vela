---
id: concern-operations
type: concern
title: Operations
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Operations

Who is on call, and the runbooks for the failures that hurt customers.

## Strategy

Coach runs as a new service on Kestrel's AWS account, where TickerTalk's backend already runs. The Coach team runs it, with the platform engineer's help for the first month, and from 1 March the Coach team's on-call rota takes any out-of-hours page. If Coach is down, TickerTalk hides the coach screens and the news works as before. The rota starts only in March, so [[11-unknowns-and-risks#UNK-067 Who covers Coach on demo week|who covers Coach in the January demo week]] is still open. [[sources#SRC-19|The platform engineer's rota]] covers TickerTalk's own operations, as the last paragraph here says.

The Coach lead wrote on 9 October, as relayed in [[sources#SRC-16|the answers the product lead gathered by 9 October]], that they will run Coach in business hours with an on-call rota from March. That is a plan, so it is an assumption.

[[sources#SRC-19|The Coach lead's channel message]] says the on-call rota goes live on 1 March, before the first beta reader. That is a plan, so it is an assumption, and it is the date asked in [[11-unknowns-and-risks#UNK-043 When Coach's on-call rota starts|the rota question]]. [[sources#SRC-20|The same message]] sets two limits: calls to Coach time out after 3 seconds and calls to Quoteline after 2. It also lets a paper order stay pending in the sandbox for 15 minutes, after which Coach marks it failed and asks the sandbox for its status once. Coach is not built yet, so these settings are assumptions. [[sources#SRC-19|The later answers]] add that Coach opens a reader's sandbox paper account at their first practice trade, and that if opening it fails the reader is told practice is unavailable and the lessons carry on. That is a design, so it is an assumption. For TickerTalk, [[sources#SRC-19|the platform engineer says]] the on-call rota already covers its backend, including the reader lookup, around the clock, and now lists Coach's dependence on it.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | addressed | Coach runs as a new service on Kestrel's AWS account, where TickerTalk's backend already runs. The Coach team runs it, with the platform engineer's help for the first month, and from 1 March the Coach team's on-call rota takes any out-of-hours page. If Coach is down, TickerTalk hides the coach screens and the news app works as before. Cover for the January demo week is [[11-unknowns-and-risks#UNK-067 Who covers Coach on demo week\|the demo-week cover question]], not this cell |
| [[tickertalk-building-blocks\|TickerTalk]] | unchanged | the platform engineer's 24/7 rota already covers TickerTalk's backend, including the reader lookup, and now lists Coach's dependence on it ([[sources#SRC-19|the later answers]]) |

## History

#### Coach
- **Decision:** [[2026-10-09-concern-cells]]
- **Options considered:** Putting the coach inside TickerTalk instead of a new service. Rejected: the news app stays a news app, and Coach can move to live orders later without dragging TickerTalk along.
- **Override:** GATE-5 by @sim-lead on 2026-10-09: the owner is not present and the product lead decides on their behalf
- **Decided by:** @sim-lead, on behalf of @coach-lead
- **Confirmed by:** @coach-lead on 2026-10-09
