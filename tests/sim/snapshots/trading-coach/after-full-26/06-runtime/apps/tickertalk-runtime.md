---
id: RUN-tickertalk
type: app-runtime
title: TickerTalk runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [2026-10-09-first-release-apps]
---

# TickerTalk runtime

This page says how TickerTalk behaves when something fails. Its part in each flow is not written yet, because no flow names it.

## On failure

If Coach is down or slow, the coach screens show a short message or hide, and the news is unaffected. If TickerTalk is down, Coach loses its readers and loses nothing else, and the paper record stays in Coach if the record lands there. If TickerTalk cannot say who the reader is, the coach is not shown.

## History

- **Options considered:** Coach service behind TickerTalk (picked); Coach inside TickerTalk: rejected, the product lead says "news app stays news"; Coach plus a paper-trading gateway: rejected, two new services for a January demo and a seam that only pays off once real orders exist
