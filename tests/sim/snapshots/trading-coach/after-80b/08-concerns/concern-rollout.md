---
id: concern-rollout
type: concern
title: Rollout
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Rollout

The order apps cut over, and how each one rolls back.

## Strategy

Coach holds a release switch, and TickerTalk hides the coach when it is off, so the coach can ship dark. The switch waits on the [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|compliance ruling in writing]]. How a release rolls back, and in what order readers get the coach, is not recorded.

The product lead says, in [[sources#SRC-16|the answers the product lead gathered by 9 October]], that rollout is an opt-in beta for 2,000 watchlist readers in March and then everyone who opts in from April. That is a plan, so it is an assumption, and it is a paper-only rollout.

[[sources#SRC-19|The compliance consultant]] signs off two lessons a week and Brightwater reviews in ten business days, so the 24 beta lessons would be cleared by 15 February, in time for the March beta. That is a forecast, so it is an assumption, and the figure does not mention the clock restarting on a rejection or the limit of ten sandbox test accounts. [[sources#SRC-19|The mobile lead says]] TickerTalk's existing security, cost, testing and observability practice holds unchanged except for the new contract tests on the coach entry, and that its rollout is the coach's opt-in beta, owned by the mobile team. Both are plans, so they are assumptions.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | unchanged | the product lead says the existing rollout practice holds ([[2026-10-09-concern-cells#^c07]]); [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|the compliance ruling in writing]] stays open
| [[tickertalk-building-blocks\|TickerTalk]] | unchanged | the product lead says the existing rollout practice holds ([[2026-10-09-concern-cells#^c07]]); [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|the compliance ruling in writing]] stays open
