---
id: RUN-coach
type: app-runtime
title: Coach runtime
state: decided
owner: "@sim-lead"
authored: authored
sources: [SRC-10, SRC-11, 2026-10-09-first-release-apps]
---

# Coach runtime

This page says what a reader sees and what Coach does when Coach, TickerTalk's call, the Brightwater sandbox or Quoteline fails, and which limits decide when each counts as failed. The Coach lead confirmed [[11-unknowns-and-risks#UNK-043 When Coach's on-call rota starts|when the on-call rota starts]], [[11-unknowns-and-risks#UNK-044 How long a paper order may stay pending|how long a paper order may stay pending]] and [[11-unknowns-and-risks#UNK-045 Timeouts for Coach and Quoteline calls|the timeouts]] in [[sources#SRC-20|the Coach channel message]] on 9 October. They stay assumptions because Coach is not built.

## On failure

If Coach is down or answers too slowly, TickerTalk hides the coach screens and the news works as before. The same holds when TickerTalk's call that tells Coach who the reader is fails or is slow: Coach serves nothing to a reader it cannot identify, and there is no anonymous fallback. If Brightwater's sandbox is down or slow, lessons still open and new paper orders pause with a message to the reader, and nothing is queued. An order already sent stays pending. When the sandbox answers, Coach asks it for the order's status and applies the answer, never sends the order again, and moves the reader's balance only when the order fills. If Quoteline is down, late or older than its 15-minute delay, lessons show no price, no paper trade fills on a stale price, and nothing is valued on that quote.

Four numbers on this page are assumptions, because Coach is not built, and the Coach lead confirmed each on 9 October in [[sources#SRC-20|the Coach channel message]] ([[2026-10-09-coach-runtime-failures#^c07]]). Coach's on-call rota goes live on 1 March, before the first beta reader. A paper order may stay pending in the sandbox for 15 minutes, after which Coach marks it failed and asks the sandbox for its status once. Calls to Coach time out after 3 seconds, and calls to Quoteline after 2.

The Brightwater sandbox sets the fill price of a paper order, and Coach uses Quoteline's quotes for display only, never to fill an order. That is an assumption too, from the product lead ([[2026-10-09-coach-runtime-failures#^c04]]), and it is why a stale Quoteline price cannot fill a trade. [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|Valuing paper trades on Quoteline quotes]] stays open for balances and positions.

## Flows

Coach takes part in these journeys, all at assumption.

- [[FLO-001-reader-starts-learning|A reader starts learning]]
- [[FLO-002-reader-practices-a-trade|A reader practices a trade]]
- [[FLO-003-reader-passes-the-ready-track|A reader passes the ready track]]

## History

- **Decision:** [[2026-10-09-coach-runtime-failures]]
- **Options considered:** Coach service behind TickerTalk (picked); Coach inside TickerTalk: rejected, the product lead says "news app stays news"; Coach plus a paper-trading gateway: rejected, two new services for a January demo and a seam that only pays off once real orders exist
