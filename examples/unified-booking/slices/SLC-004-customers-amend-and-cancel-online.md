---
id: SLC-004
type: slice
title: Customers amend and cancel on the website
initiative: INI-002
authored: authored
sources: [2026-09-16-testing-and-amend]
---

# Customers amend and cancel on the website

Customers change or cancel their own booking online instead of phoning, which is what the goal of 60% of amendments online measures. The amend and cancel operations are ready before the call centre cutover; the website pages go live once the website's 4-week switch window closes. No Grill has planned it yet.

- **Flows:** [[FLO-002-amend-or-cancel|FLO-002]]
- **After:** SLC-001
- **Joins:** [[booking-building-blocks#CON-001 Booking API|Booking API]] (Website → Booking), [[customer-identity-building-blocks#CON-005 Customer lookup|Customer lookup]] (Booking → Customer identity), [[vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check]] (Booking → Vessel schedule), [[pricing-building-blocks#CON-003 Quote a fare|Quote a fare]] (Booking → Pricing), [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]] (Booking → FERRYMASTER), [[booking-building-blocks#CON-002 Booking state changed|Booking state changed]] (Booking → Notifications)
- **Ships switched off:** the website pages stay hidden until the website's 4-week switch window closes
- **Done when:** a customer amends a booking up and down and cancels one on the website, and is told each change
- **Owner:** @hl-solution-lead

## History

- 2026-11-20: written from the amend and cancel epic and the rollout page. Not planned yet.
