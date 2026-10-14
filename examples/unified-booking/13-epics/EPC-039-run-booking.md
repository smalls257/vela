---
id: EPC-039
type: epic
title: "Run Booking: on-call, runbooks, dashboards"
initiative: INI-002
state: decided
owner: "@harborline/booking-team"
authored: mixed
apps: [APP-booking]
delivers: [G2]
consumes: []
flows: []
depends_on: [EPC-031, EPC-032]
sources: ["session 2026-10-07 Grill", "concern-operations", "concern-observability"]
---

# EPC-039 Run Booking: on-call, runbooks, dashboards

- **Decision:** [[2026-11-18-epics]]

Booking becomes the one thing every channel depends on for bookings, so it has to be run like it from the first real customer. The Booking team joins the Platform on-call rota from go-live ([[11-unknowns-and-risks#UNK-007 Booking on-call|Booking on-call]]) and writes runbooks for the two failures that hurt customers most: ledger writes failing and Booking losing its holds.

Still open: nothing.

**Owning team:** Booking team.

## Who this is for and what changes

Today a stuck booking shows up as a call center fix the next morning. After go-live the same problem has to show up on a dashboard within minutes. Per-channel request and error rates, booking state transitions, ledger write latency, hold expiry rate and one trace ID from channel to ledger write give the on-call engineer what they need without a debugger or a release.

## Done when

### An alert pages the on-call engineer

From the day the website cuts over, a Booking alert pages a Booking engineer through the Platform on-call rota.

- Trace: AC1  ·  [operations]

### The dashboards show what the engineer needs

The on-call engineer can see per-channel request and error rate, booking state transitions, p95 ledger write latency and hold expiry rate without a release.

- Trace: AC2  ·  [observability]

### One trace ID follows a request

One trace ID follows a request from the channel's call on the Booking API to the write on the ledger.

- Trace: CON-001, CON-006  ·  AC3  ·  [observability]

### Stuck bookings raise an alert

An alert fires when ledger writes keep failing and bookings stay in `confirming`.

- Trace: AC4

### The runbooks are rehearsed

Both runbooks have been walked through in a rehearsal with the on-call rota before the website cutover.

- Trace: AC5  ·  [operations]

## Traces to

<!-- generated:traces-to sha=7709ed8f: do not edit, run vela render -->
| Traces to | Items |
|---|---|
| Apps | [[booking-building-blocks\|Booking]] |
| Delivers | [[01-goals\|G2]] |
| Consumes | none |
| Flows | none |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]], [[EPC-032-ledger-adapter\|EPC-032 Ledger adapter on FERRYMASTER's MQ transactions]] |
| Concerns | [[concern-observability\|Observability]], [[concern-operations\|Operations]] |
<!-- /generated:traces-to -->

Also related: contracts observed [[booking-building-blocks#CON-001 Booking API|Booking API]] and [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]], and [[11-unknowns-and-risks#UNK-007 Booking on-call|Booking on-call]].

## Depends on

- [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]] and [[EPC-032-ledger-adapter|Ledger adapter on FERRYMASTER's MQ transactions]]: there is nothing to watch until they exist.

## Rollout notes

Must be done before [[EPC-033-website-to-booking|Website moves to Booking]] cuts over in February 2027.

## Out of scope

- Dashboards for Pricing, Notifications or the channels. Their owners keep their own.

