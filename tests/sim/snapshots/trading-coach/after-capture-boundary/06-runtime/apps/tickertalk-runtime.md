---
id: RUN-tickertalk
type: app-runtime
title: TickerTalk runtime
state: decided
owner: "@sim-lead"
authored: authored
sources: [2026-10-09-first-release-apps]
---

# TickerTalk runtime

This page says how TickerTalk behaves when something fails.

## On failure

If Coach is down or slow, a screen the reader is already on shows a short message that the coach is not available, and the coach's entry points on the news screens are hidden. Slow is treated as down, and [[11-unknowns-and-risks#UNK-045 Timeouts for Coach and Quoteline calls|how long counts as slow]] is not recorded. The news is unaffected. If the release switch is off, or TickerTalk cannot say who the reader is, the coach is not shown. If TickerTalk is down, Coach loses its readers and loses nothing else, because the paper record stays in Coach, [[sources#SRC-16|per the Coach lead]].

## Flows

TickerTalk takes part in these journeys, all at assumption.

- [[FLO-001-reader-starts-learning|A reader starts learning]]
- [[FLO-002-reader-practises-a-trade|A reader practises a trade]]
- [[FLO-003-reader-passes-the-ready-track|A reader passes the ready track]]

## History

- **Decision:** [[2026-10-09-tickertalk-reader-identity#^c19]]
- **Options considered:** Coach service behind TickerTalk (picked); Coach inside TickerTalk: rejected, the product lead says "news app stays news"; Coach plus a paper-trading gateway: rejected, two new services for a January demo and a seam that only pays off once real orders exist
