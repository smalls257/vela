---
id: concern-ownership
type: concern
title: Ownership
initiative: INI-002
arc42: "§8"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-28 Grill", "session 2026-10-07 Grill"]
---

# Ownership


## Strategy

Every app keeps its current owner. INI-002 adds one team and moves one responsibility. The new Booking team owns Booking, including the Ledger adapter, so one team answers for what "confirmed" means ([[ADR-0001-one-booking-context|ADR-0001]]). Before this, three teams each owned an adapter into FERRYMASTER and each answered the question differently.

Each front-end team owns its Booking API client and its consumer contract tests. The Booking team does not write channel code. When a channel needs something new from the API, the front-end team changes its contract test and the Booking team sees it fail in Booking's pipeline.

The mainframe team owns FERRYMASTER and the MQ transactions, and gives 8 weeks' notice of changes. The Ledger adapter belongs to the Booking team, so the mainframe team never has to support a client it did not write.

## Per app

| App | State | Owner team | Owns in INI-002 |
|---|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Booking team (new) | Booking API, Hold store, Ledger adapter, Event publisher |
| [[pricing-building-blocks\|Pricing]] | unchanged | Revenue team | Quote service, Fare rules store |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | unchanged | Mainframe team | Ledger and MQ transactions |
| [[website-building-blocks\|Website]] | addressed | Digital team | Booking API client in Booking pages |
| [[call-centre-building-blocks\|Call centre]] | addressed | Contact Centre Systems team | Booking API client, amend and cancel screens |
| [[kiosks-building-blocks\|Kiosks]] | addressed | Port Systems team | Booking API v1 client in the kiosk app: hold, confirm, get. No amend or cancel in the March 2027 image. |
| [[notifications-building-blocks\|Notifications]] | addressed | Platform team | Booking event consumer |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | Marine Ops Systems team | Capacity read API |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | Platform team | Customer read API |

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-007 Booking on-call|UNK-007]], [[11-unknowns-and-risks#UNK-003 Mainframe capacity in Q1|UNK-003]]
- Decisions: [[ADR-0001-one-booking-context|ADR-0001]]
- Epics: [[EPC-031-holds-and-confirms|EPC-031]], [[EPC-032-ledger-adapter|EPC-032]], [[EPC-033-website-to-booking|EPC-033]], [[EPC-034-call-centre-to-booking|EPC-034]], [[EPC-035-kiosks-to-booking|EPC-035]], [[EPC-037-events-and-notifications|EPC-037]]
