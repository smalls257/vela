---
id: EPC-031
type: epic
title: Booking holds and confirms crossings
initiative: INI-002
state: decided
owner: "@harbourline/booking-team"
authored: mixed
apps: [APP-booking]
delivers: [CAP-013, CAP-014, CON-001, CON-007, G1, G2]
consumes: [CON-003, CON-004, CON-005]
flows: [FLO-001]
depends_on: [EPC-032]
sources: ["session 2026-07-28 Shape", "session 2026-11-18 Grill", "ADR-0001", "ADR-0002"]
---

# EPC-031 Booking holds and confirms crossings

- **Decision:** [[2026-11-18-epics]]

Booking becomes the one place that decides whether a crossing is held, confirmed or released. Today each front end works that out from whatever its own adapter scraped, which is why the call centre and the kiosks can disagree about the same booking. This epic builds the hold, confirm and get operations of the Booking API, takes Tidepay's payment outcome, and keeps an unpaid seat for 10 minutes.

The hold is new. Today nothing stops a second channel selling the last seat while a customer is on Tidepay's page, and the call centre sorts out the overbooking by hand. FERRYMASTER stays the ledger of record ([[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]]), so Booking reports a booking as confirmed only after the ledger has accepted it. Customers pay on Tidepay's hosted page and card data never reaches Booking.

**Owning team:** Booking team.

## Epic acceptance criteria

1. A channel that asks to hold a seat through CON-001 gets back a booking reference and an expiry time 10 minutes ahead, and no other channel can sell that seat until the hold ends.
2. When Tidepay reports a successful payment through CON-007, get on CON-001 returns `confirmed` only after FERRYMASTER has accepted the booking.
3. If the ledger write fails after payment, get returns `confirming`, the seat stays held past the 10 minutes, and the booking reaches `confirmed` without anyone at Harbourline touching it.
4. A failed or abandoned payment releases the hold, and the seat is available to every channel again.
5. Two channels asking about the same booking reference at the same moment get the same state.
6. A call to CON-001 without a valid service token is refused at the Platform gateway. [security]
7. No request or response on CON-001 or CON-007 carries card data. [security] [data]

## Traces to

<!-- generated:traces-to sha=0fde9efa: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[booking-building-blocks\|Booking]] |
| Delivers | [[CAP-013-reserve-a-crossing\|CAP-013 Reserve a crossing]], [[CAP-014-hold-a-seat\|CAP-014 Hold a seat during payment]], [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]], [[booking-building-blocks#CON-007 Tidepay payment outcome\|CON-007 Tidepay payment outcome]], [[01-goals\|G1]], [[01-goals\|G2]] |
| Consumes | [[pricing-building-blocks#CON-003 Quote a fare\|CON-003 Quote a fare]], [[vessel-schedule-building-blocks#CON-004 Capacity check\|CON-004 Capacity check]], [[customer-identity-building-blocks#CON-005 Customer lookup\|CON-005 Customer lookup]] |
| Flows | [[FLO-001-hold-pay-confirm\|FLO-001 Hold, pay, confirm]] |
| Depends on | [[EPC-032-ledger-adapter\|EPC-032 Ledger adapter on FERRYMASTER's MQ transactions]] |
| Concerns | [[concern-data\|Data]], [[concern-security\|Security]] |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-032-ledger-adapter|EPC-032]]: confirm needs ledger writes.

## Rollout notes

No channel traffic reaches Booking until that channel's own epic cuts over. Booking runs in production with test bookings only before the website cutover in February 2027.

## Out of scope

- Amend and cancel ([[EPC-036-amend-cancel-online|EPC-036]]).
- Publishing state-changed events ([[EPC-037-events-and-notifications|EPC-037]]).
- How writes reach FERRYMASTER ([[EPC-032-ledger-adapter|EPC-032]]).
- Any channel's Booking API client.

The Booking team breaks this epic into stories after their tech design session.
