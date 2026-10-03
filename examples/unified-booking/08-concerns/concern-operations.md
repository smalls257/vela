---
id: concern-operations
type: concern
title: Operations
initiative: INI-002
arc42: "§8"
owner: "@hl-booking-senior"
authored: mixed
sources: ["session 2026-10-07 Grill"]
---

# Operations


## Strategy

Booking is a new team running a new service, so it joins the Platform on-call rota from go-live instead of building its own ([[11-unknowns-and-risks#UNK-007 Booking on-call|UNK-007]]). Platform already runs the gateway and the event bus Booking depends on, so one rota sees the whole path.

Two runbooks exist before go-live. The ledger-write failure runbook covers a booking that is paid and stuck in "confirming" after the Ledger adapter has run out of retries. This is the case the call centre used to fix by hand the next morning ([[CAP-023-fix-failed-bookings|CAP-023]]), and now on-call handles it the same night. The hold-store outage runbook covers Booking refusing new holds while the store is down; existing confirmed bookings are unaffected.

Mainframe knowledge sits with two people ([[11-unknowns-and-risks#R-01 Mainframe knowledge sits with two people|R-01]]). The MQ mapping is written down in [[ferrymaster-building-blocks#CON-006 Ledger transactions|CON-006]], and Booking engineers pair with the mainframe team from January to March 2027, so on-call does not depend on reaching one of them at night.

## Per app

| App | State | What changes |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Joins Platform on-call rota. Runbooks: ledger-write failure, hold-store outage. |
| [[pricing-building-blocks\|Pricing]] | unchanged | Revenue team support as today |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | addressed | Mainframe team announces MQ changes 8 weeks ahead; pairing January to March 2027 |
| [[website-building-blocks\|Website]] | unchanged | Digital team support as today, less one adapter |
| [[call-centre-building-blocks\|Call centre]] | addressed | Manual fix queue retired; next-morning fixes stop |
| [[kiosks-building-blocks\|Kiosks]] | unchanged | Port Systems support as today |
| [[notifications-building-blocks\|Notifications]] | addressed | no work (@hl-platform-lead, review 2027-03-01): new consumer covered by the Platform rota |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | As today |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | As today |

## Related

- Unknowns and risks: [[11-unknowns-and-risks#UNK-007 Booking on-call|UNK-007]], [[11-unknowns-and-risks#UNK-003 Mainframe capacity in Q1|UNK-003]], [[11-unknowns-and-risks#R-01 Mainframe knowledge sits with two people|R-01]]
- Decisions: [[ADR-0004-mq-not-screen-scraping|ADR-0004]]
- Epics: [[EPC-039-run-booking|EPC-039]], [[EPC-032-ledger-adapter|EPC-032]], [[EPC-034-call-centre-to-booking|EPC-034]]
