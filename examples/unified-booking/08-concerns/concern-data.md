---
id: concern-data
type: concern
title: Data
initiative: INI-002
arc42: "§8"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-08-12 Grill", "ADR-0002"]
---

# Data


## Strategy

FERRYMASTER stays the ledger of record ([[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]]). The data warehouse feed, the finance reconciliation job and the loyalty scheme all read it directly, and INI-002 does not move them. If Booking became the record, those three would read a ledger that no longer matched the bookings customers see.

Booking stores two things. The Hold store keeps unpaid holds for 10 minutes. The booking-state cache, keyed by booking reference, holds the last state FERRYMASTER accepted, so channels can read state without a mainframe call. Booking changes that state only after a ledger write succeeds. When the cache and FERRYMASTER disagree, FERRYMASTER wins and the cache is refreshed.

Booking holds no card data and no contact details. The only personal data is the customer ID. Notifications resolves contact details at send time from Customer identity. The channels used to cache FERRYMASTER replies, each in its own way, and that is why the call centre and the kiosks disagreed about confirmations. Those caches go when each channel moves to Booking.

## Per app

| App | State | Data it holds for bookings |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Holds (10 minutes), booking-state cache by booking reference, customer ID. No card data and no other personal data. |
| [[pricing-building-blocks\|Pricing]] | unchanged | Fare rules |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | addressed | Ledger of record for every booking |
| [[website-building-blocks\|Website]] | addressed | Nothing. Its FERRYMASTER reply cache is removed with the screen adapter. |
| [[call-centre-building-blocks\|Call centre]] | addressed | Nothing. Its cache and the manual fix queue are retired. |
| [[kiosks-building-blocks\|Kiosks]] | addressed | Nothing after cutover. Its cache goes with the old adapter. |
| [[notifications-building-blocks\|Notifications]] | addressed | Record of messages sent per booking reference and state, used to drop duplicates |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | Sailings and capacity |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | Customer records and contact details |

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-006 Finance on Booking events|UNK-006]] (Finance reading Booking events, open, deferred to INI-005)
- Decisions: [[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[ADR-0001-one-booking-context|ADR-0001]]
- Epics: [[EPC-031-holds-and-confirms|EPC-031]], [[EPC-032-ledger-adapter|EPC-032]], [[EPC-037-events-and-notifications|EPC-037]]
