---
id: concern-rollout
type: concern
title: Rollout
initiative: INI-002
arc42: "§8"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-08-26 Grill", SRC-03]
---

# Rollout


## Strategy

Channels move one at a time. The website goes first in February 2027 because the Digital team releases weekly and can roll back in minutes. The call centre follows in March 2027, once the website has shown Booking under real load. Kiosks move with the March 2027 image, because their image changes only in March and September.

Each channel keeps its old adapter behind a switch for 4 weeks after cutover. Rollback means flipping that channel's switch back; nothing else moves. After 4 weeks without a rollback, the old adapter is removed. Kiosks cannot remove code between images, so their old adapter is switched off after 4 weeks and deleted in the September 2027 image.

If the March image slips, kiosks keep their old adapter until September ([[11-unknowns-and-risks#R-02 The March 2027 kiosk image slips|The March 2027 kiosk image slips]]). Booking API v1 stays supported for at least six months ([[ADR-0003-versioned-booking-api|the versioning decision]]), so a late kiosk image still has an API to call. Pricing's gateway restriction to Booking goes on after the last channel's switch period ends, because each old adapter still quotes fares directly.

## Per app

| App | State | Cutover | Rollback |
|---|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Live before the website cutover, February 2027 | Channels flip back; Booking stays up |
| [[pricing-building-blocks\|Pricing]] | addressed | Gateway restriction after the last channel's 4-week switch period | Remove the gateway rule |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | n/a | No change | n/a |
| [[website-building-blocks\|Website]] | addressed | February 2027 | Switch back to FM screen adapter for 4 weeks |
| [[call-centre-building-blocks\|Call centre]] | addressed | March 2027 | Switch back to terminal adapter for 4 weeks |
| [[kiosks-building-blocks\|Kiosks]] | addressed | March 2027 image | Switch back to FM adapter for 4 weeks; removed in September 2027 image. If the March image slips, kiosks keep the FM adapter until the next one. |
| [[notifications-building-blocks\|Notifications]] | addressed | Booking event consumer live with Booking | Pause the consumer; events wait on the bus |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | n/a | No change | n/a |
| [[customer-identity-building-blocks\|Customer identity]] | n/a | No change | n/a |

## Related

- Unknowns and risks: [[11-unknowns-and-risks#UNK-005 Event bus readiness|Event bus readiness]], [[11-unknowns-and-risks#R-02 The March 2027 kiosk image slips|The March 2027 kiosk image slips]]
- Decisions: [[ADR-0003-versioned-booking-api|the versioning decision]]
- Epics: [[EPC-033-website-to-booking|Website moves to Booking]], [[EPC-034-call-centre-to-booking|Call centre moves to Booking]], [[EPC-035-kiosks-to-booking|Kiosks move to Booking in the March image]], [[EPC-038-pricing-serves-booking|Pricing serves Booking only]]
