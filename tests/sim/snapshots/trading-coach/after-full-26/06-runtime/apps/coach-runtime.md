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

This page says how Coach behaves when something fails. Its part in each flow is not written yet, because no flow names it.

## On failure

If Coach is down, TickerTalk hides the coach screens and the news works as before. If Brightwater's sandbox is down, lessons still open, paper trades pause with a message to the reader, and nothing is queued. If Quoteline is down, lessons show no price and no paper trade fills on a stale price.

## History

- **Options considered:** Coach service behind TickerTalk (picked); Coach inside TickerTalk: rejected, the product lead says "news app stays news"; Coach plus a paper-trading gateway: rejected, two new services for a January demo and a seam that only pays off once real orders exist
