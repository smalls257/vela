---
id: concern-observability
type: concern
title: Observability
initiative: INI-002
arc42: "§8"
owner: "@hl-booking-senior"
authored: mixed
sources: ["session 2026-09-02 Grill", "session 2026-10-07 Grill"]
---

# Observability


## Strategy

The old adapters failed with no signal. A customer paid, the confirm scrape failed, and the first anyone knew was a complaint the next morning. Booking measures each hand-off so a failure shows up at the stage where it happens.

One trace ID runs from the channel to the Ledger adapter. Each channel creates it and passes it on every Booking API call, and Booking carries it into the MQ write. When a booking is stuck, on-call can see whether the delay was in the channel, Booking, Pricing or the ledger without reading four sets of logs.

The dashboards track per-channel request and error rate, booking state transitions, ledger write latency at p95 and the hold expiry rate. Ledger latency was measured at 2.1 s p95 before design started ([[11-unknowns-and-risks#UNK-001 Ledger write latency|Ledger write latency]]), so a rise has a baseline to compare against. A rising hold expiry rate usually means payments are failing at Tidepay, which no other metric would show.

## Per app

| App | State | What is measured |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Booking senior owns it. Per-channel request and error rate, state transitions, ledger write latency p95, hold expiry rate, one trace ID from channel to Ledger adapter |
| [[pricing-building-blocks\|Pricing]] | unchanged | Existing service metrics |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | n/a | Black box; latency is measured at the Ledger adapter |
| [[website-building-blocks\|Website]] | addressed | Creates and passes the trace ID |
| [[call-centre-building-blocks\|Call centre]] | addressed | Creates and passes the trace ID |
| [[kiosks-building-blocks\|Kiosks]] | addressed | Creates and passes the trace ID from the March 2027 image |
| [[notifications-building-blocks\|Notifications]] | unchanged | Existing sender metrics |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | Existing service metrics |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | Existing service metrics |

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-001 Ledger write latency|Ledger write latency]]
- Decisions: [[ADR-0004-mq-not-screen-scraping|the MQ decision]]
- Epics: [[EPC-039-run-booking|Run Booking: on-call, runbooks, dashboards]], [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]]
