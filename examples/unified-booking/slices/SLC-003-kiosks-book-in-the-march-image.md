---
id: SLC-003
type: slice
title: Kiosks book through Booking in the March image
initiative: INI-002
authored: authored
sources: [2026-08-26-kiosks-and-rollout]
---

# Kiosks book through Booking in the March image

Kiosks move last, with the March 2027 image, because their software changes only in March and September. If the image slips, kiosks keep their old adapter until September, and the versioned Booking API still serves them. No Grill has planned it yet.

- **Flows:** [[FLO-001-hold-pay-confirm|FLO-001]]
- **After:** SLC-002
- **Joins:** [[booking-building-blocks#CON-001 Booking API|Booking API]] (Kiosks → Booking), [[vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check]] (Booking → Vessel schedule), [[customer-identity-building-blocks#CON-005 Customer lookup|Customer lookup]] (Booking → Customer identity), [[pricing-building-blocks#CON-003 Quote a fare|Quote a fare]] (Booking → Pricing), [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]] (Booking → FERRYMASTER), [[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]] (Tidepay → Booking), [[booking-building-blocks#CON-002 Booking state changed|Booking state changed]] (Booking → Notifications)
- **Ships switched off:** the kiosks' old FERRYMASTER adapter is switched off after 4 weeks and deleted in the September 2027 image
- **Done when:** a customer holds, pays for and confirms a crossing at a kiosk running the March 2027 image
- **Owner:** @hl-solution-lead

## Not in this slice

- [[FLO-002-amend-or-cancel|Amend and cancel at a kiosk]]: kiosks do not amend or cancel in the March 2027 image

## History

- 2026-11-20: written from the rollout page and the solution strategy's channel order. Not planned yet.
