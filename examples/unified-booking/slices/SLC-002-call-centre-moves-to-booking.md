---
id: SLC-002
type: slice
title: The call centre books, amends and cancels through Booking
initiative: INI-002
authored: authored
sources: [2026-08-26-kiosks-and-rollout]
---

# The call centre books, amends and cancels through Booking

The call centre moves second, once the website has shown Booking under real load, and amend and cancel move onto Booking with it. An agent books, amends and cancels for a caller and sees exactly what the customer sees. No Grill has planned it yet.

- **Flows:** [[FLO-001-hold-pay-confirm|FLO-001]], [[FLO-002-amend-or-cancel|FLO-002]]
- **After:** SLC-001
- **Joins:** [[booking-building-blocks#CON-001 Booking API|Booking API]] (Call centre → Booking), [[vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check]] (Booking → Vessel schedule), [[customer-identity-building-blocks#CON-005 Customer lookup|Customer lookup]] (Booking → Customer identity), [[pricing-building-blocks#CON-003 Quote a fare|Quote a fare]] (Booking → Pricing), [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]] (Booking → FERRYMASTER), [[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]] (Tidepay → Booking), [[booking-building-blocks#CON-002 Booking state changed|Booking state changed]] (Booking → Notifications)
- **Ships switched off:** the call centre keeps its terminal adapter behind a switch for 4 weeks after cutover
- **Done when:** a call centre agent books, amends and cancels a crossing for a caller, and the caller is told each change
- **Owner:** @hl-solution-lead

## History

- 2026-11-20: written from the rollout page and the solution strategy's channel order. Not planned yet.
