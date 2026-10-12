---
id: RUN-coach
type: app-runtime
title: Coach runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-10, SRC-11, 2026-10-09-first-release-apps]
---

# Coach runtime

This page says how Coach behaves when something fails. It stays at assumption until the Coach lead confirms [[11-unknowns-and-risks#UNK-043 When Coach's on-call rota starts|when the on-call rota starts]], [[11-unknowns-and-risks#UNK-044 How long a paper order may stay pending|how long a paper order may stay pending]] and [[11-unknowns-and-risks#UNK-045 Timeouts for Coach and Quoteline calls|the timeouts]].

## On failure

If Coach is down or answers too slowly, TickerTalk hides the coach screens and the news works as before. The same holds when TickerTalk's call that tells Coach who the reader is fails or is slow: Coach serves nothing to a reader it cannot identify, and there is no anonymous fallback. If Brightwater's sandbox is down or slow, lessons still open and new paper orders pause with a message to the reader, and nothing is queued. An order already sent stays pending. When the sandbox answers, Coach asks it for the order's status and applies the answer, never sends the order again, and moves the reader's balance only when the order fills. If Quoteline is down, late or older than its 15-minute delay, lessons show no price, no paper trade fills on a stale price, and nothing is valued on that quote. How long an order may stay pending and how late is too late are for the Coach lead to fill in.

## Flows

Coach takes part in these journeys, all at assumption.

- [[FLO-001-reader-starts-learning|A reader starts learning]]
- [[FLO-002-reader-practises-a-trade|A reader practises a trade]]
- [[FLO-003-reader-passes-the-ready-track|A reader passes the ready track]]

## History

- **Options considered:** Coach service behind TickerTalk (picked); Coach inside TickerTalk: rejected, the product lead says "news app stays news"; Coach plus a paper-trading gateway: rejected, two new services for a January demo and a seam that only pays off once real orders exist
