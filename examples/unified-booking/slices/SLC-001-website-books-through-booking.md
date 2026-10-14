---
id: SLC-001
type: slice
title: A customer books on the website through Booking
initiative: INI-002
authored: authored
sources: [2026-08-26-kiosks-and-rollout]
---

# A customer books on the website through Booking

The tracer: the website moves first because it has the most traffic and rolls back in minutes. A customer holds a seat, pays on Tidepay's page and gets the confirmation, with every write going through Booking to FERRYMASTER. The flows are drawn, but not yet in the form the flow check reads, so no Grill can plan the slice yet.

- **Flows:** [[FLO-001-hold-pay-confirm|FLO-001]], [[FLO-003-notify-on-change|FLO-003]]
- **Joins:** [[booking-building-blocks#CON-001 Booking API|Booking API]] (Website → Booking), [[vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check]] (Booking → Vessel schedule), [[customer-identity-building-blocks#CON-005 Customer lookup|Customer lookup]] (Booking → Customer identity), [[pricing-building-blocks#CON-003 Quote a fare|Quote a fare]] (Booking → Pricing), [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]] (Booking → FERRYMASTER), [[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]] (Tidepay → Booking), [[booking-building-blocks#CON-002 Booking state changed|Booking state changed]] (Booking → Notifications)
- **Ships switched off:** the website keeps its old FERRYMASTER screen adapter behind a switch for 4 weeks; flipping it back sends new bookings the old way
- **Done when:** a customer holds, pays for and confirms a crossing on the website, and the confirmation reaches them
- **Owner:** @hl-solution-lead

## Not in this slice

- [[FLO-002-amend-or-cancel|Amend and cancel online]]: the website pages go live after its 4-week switch window closes, in their own slice

## History

- 2026-11-20: written from the rollout page and the solution strategy's channel order. Not planned yet.
