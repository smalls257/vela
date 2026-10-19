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

Coach is a new service, and the vault does not record [[11-unknowns-and-risks#UNK-028 Where a Coach service can run|where it can run]] or who runs it out of hours. If Coach is down, TickerTalk hides the coach screens and the news works as before. TickerTalk's own operations have not been examined.

The Coach lead wrote on 9 October, as relayed in [[sources#SRC-16|the answers the product lead gathered by 9 October]], that they will run Coach in business hours with an on-call rota from March. That is a plan, so it is an assumption.

[[sources#SRC-19|The Coach lead's channel message]] says the on-call rota goes live on 1 March, before the first beta reader. That is a plan, so it is an assumption, and it is the date asked in [[11-unknowns-and-risks#UNK-043 When Coach's on-call rota starts|the rota question]]. [[sources#SRC-20|The same message]] sets two limits: calls to Coach time out after 3 seconds and calls to Quoteline after 2. It also lets a paper order stay pending in the sandbox for 15 minutes, after which Coach marks it failed and asks the sandbox for its status once. Coach is not built yet, so these settings are assumptions. [[sources#SRC-19|The later answers]] add that Coach opens a reader's sandbox paper account at their first practice trade, and that if opening it fails the reader is told practice is unavailable and the lessons carry on. That is a design, so it is an assumption. For TickerTalk, [[sources#SRC-19|the platform engineer says]] the on-call rota already covers its backend, including the reader lookup, around the clock, and now lists Coach's dependence on it.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | unknown | [[11-unknowns-and-risks#UNK-028 Where a Coach service can run\|Where a Coach service can run]]: where a Coach service can run, and who runs it |

Not looked at yet: [[tickertalk-building-blocks\|TickerTalk]].
