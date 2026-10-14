---
id: concern-cost
type: concern
title: Cost
initiative: INI-002
arc42: "§8"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-08-14 Grill", "mainframe team lead MIPS check"]
---

# Cost


## Strategy

Booking runs on the standard Harborline service footprint and needs no new licenses. Its stores and API are the same size as other Platform-hosted services. Pricing, Vessel schedule and Customer identity see the same or fewer calls, because Booking makes the calls three front ends used to make.

The cost that mattered was mainframe processing, because millions of instructions per second (MIPS) is capped. Screen scraping drives whole terminal sessions for one booking. BKHOLD, BKCONF, BKAMND and BKCANC are single message queue (MQ) transactions that the finance job already uses. The mainframe team lead checked the expected volume against the existing budget and confirmed it fits.

Retiring three adapters removes upkeep that used to cost each front-end team a fix every time FERRYMASTER changed a screen. That was 11 incidents last year. This initiative does not count that saving in money.

## Per app

| App | State | Cost change |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | no work (@hl-solution-lead, review 2027-03-01): standard service footprint, no new licenses |
| [[pricing-building-blocks\|Pricing]] | unchanged | Same calls from one caller |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | addressed | MQ use within the existing MIPS budget (CST-5), checked with the mainframe team lead |
| [[website-building-blocks\|Website]] | unchanged | Adapter removed |
| [[call-center-building-blocks\|Call center]] | unchanged | Adapter and manual fix queue removed |
| [[kiosks-building-blocks\|Kiosks]] | unchanged | Change ships in the planned March 2027 image |
| [[notifications-building-blocks\|Notifications]] | unchanged | Existing sender reused |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | No change |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | No change |

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-003 Mainframe capacity in Q1|Mainframe capacity in Q1]]
- Decisions: [[ADR-0004-mq-not-screen-scraping|the MQ decision]]
- Epics: [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]], [[EPC-032-ledger-adapter|Ledger adapter on FERRYMASTER's MQ transactions]]
