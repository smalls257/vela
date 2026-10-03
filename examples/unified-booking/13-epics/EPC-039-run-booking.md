---
id: EPC-039
type: epic
title: "Run Booking: on-call, runbooks, dashboards"
initiative: INI-002
state: handed-off
owner: Booking team
authored: authored
jira: HB-109
last_verified: 2026-11-20
sources: ["session 2026-10-07 Grill", "concern-operations", "concern-observability"]
---

# EPC-039 Run Booking: on-call, runbooks, dashboards

Booking becomes the one thing every channel depends on for bookings, so it has to be run like it from the first real customer. The Booking team joins the Platform on-call rota from go-live ([[11-unknowns-and-risks#UNK-007|UNK-007]]) and writes runbooks for the two failures that hurt customers most: ledger writes failing and Booking losing its holds.

Today a stuck booking shows up as a call centre fix the next morning. After go-live the same problem has to show up on a dashboard within minutes. Per-channel request and error rates, booking state transitions, ledger write latency, hold expiry rate and one trace ID from channel to ledger write give the on-call engineer what they need without a debugger or a release.

**Owning team:** Booking team. **Jira:** HB-109.

## Epic acceptance criteria

1. From the day the website cuts over, a Booking alert pages a Booking engineer through the Platform on-call rota.
2. The on-call engineer can see per-channel request and error rate, booking state transitions, p95 ledger write latency and hold expiry rate without a release.
3. One trace ID follows a request from the channel's call on CON-001 to the write on CON-006.
4. An alert fires when ledger writes keep failing and bookings stay in `confirming`.
5. Both runbooks have been walked through in a rehearsal with the on-call rota before the website cutover.

## Traces to

- Concerns: [[concern-operations|Operations]], [[concern-observability|Observability]]
- Contracts observed: [[booking-building-blocks#CON-001|CON-001]], [[ferrymaster-building-blocks#CON-006|CON-006]]
- Unknowns: [[11-unknowns-and-risks#UNK-007|UNK-007]]
- Goals: [[01-goals|G2]]

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]] and [[EPC-032-ledger-adapter|EPC-032]]: there is nothing to watch until they exist.

## Rollout notes

Must be done before [[EPC-033-website-to-booking|EPC-033]] cuts over in February 2027.

## Out of scope

- Dashboards for Pricing, Notifications or the channels. Their owners keep their own.

The Booking team breaks this epic into stories after their tech design session.
