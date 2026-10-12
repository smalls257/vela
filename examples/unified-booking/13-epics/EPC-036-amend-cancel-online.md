---
id: EPC-036
type: epic
title: Amend and cancel online
initiative: INI-002
state: decided
owner: "@harbourline/booking-team @harbourline/digital-team"
authored: mixed
apps: [APP-booking, APP-website]
delivers: [CAP-021, CON-001, G3]
consumes: [CON-003, CON-006]
flows: [FLO-002]
depends_on: [EPC-031, EPC-032, EPC-033]
sources: ["session 2026-09-16 Grill", "session 2026-11-18 Grill"]
---

# EPC-036 Amend and cancel online

- **Decision:** [[2026-11-18-epics]]

Today a customer who wants to change or cancel a crossing has to phone, because only the call centre can do it, through a mainframe screen. [[01-goals|G3]] asks for 60% of amendments to be done online within 6 months of go-live. This epic adds amend and cancel to the Booking API and gives the website pages for both.

Booking checks whether the change is allowed, asks Pricing for a new fare when the crossing changes, and writes BKAMND or BKCANC to FERRYMASTER. The Booking team builds the API side; the Digital team builds the pages. The call centre's new screens in [[EPC-034-call-centre-to-booking|EPC-034]] use the same operations, so an amendment means the same thing on the website and in the call centre. Kiosks show booking state only and do not amend or cancel.

**Owning teams:** Booking team (API) and Digital team (pages).

## Epic acceptance criteria

1. A customer can change the date or time of a crossing on the website and sees the re-quoted fare before they accept it.
2. A customer can cancel a booking on the website, and every channel, kiosks included, shows it as `cancelled` once FERRYMASTER has accepted the cancellation.
3. A change that is not allowed is refused with a reason the channel can show the customer, and nothing reaches FERRYMASTER.
4. An amendment that costs more is confirmed only after Tidepay reports the extra payment and FERRYMASTER accepts the change. [testing]
5. The share of amendments made online is reported each month from go-live, so G3 can be tracked.

## Traces to

<!-- generated:traces-to sha=0a8a663a: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[booking-building-blocks\|Booking]], [[website-building-blocks\|Public website]] |
| Delivers | [[CAP-021-amend-or-cancel\|CAP-021 Amend or cancel a booking]], [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]], [[01-goals\|G3]] |
| Consumes | [[pricing-building-blocks#CON-003 Quote a fare\|CON-003 Quote a fare]], [[ferrymaster-building-blocks#CON-006 Ledger transactions\|CON-006 Ledger transactions]] |
| Flows | [[FLO-002-amend-or-cancel\|FLO-002 Amend or cancel]] |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]], [[EPC-032-ledger-adapter\|EPC-032 Ledger adapter on FERRYMASTER's MQ transactions]], [[EPC-033-website-to-booking\|EPC-033 Website moves to Booking]] |
| Concerns | [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]]: booking state and CON-001.
- [[EPC-032-ledger-adapter|EPC-032]]: BKAMND and BKCANC writes.
- [[EPC-033-website-to-booking|EPC-033]]: the website's new booking pages.

## Rollout notes

The amend and cancel operations are ready before the call centre cutover in March 2027. The website pages go live after the website's 4-week switch window closes. G3's 6-month clock starts on that date.

## Out of scope

- Amend and cancel at kiosks. Kiosks show booking state only in the March 2027 image ([[EPC-035-kiosks-to-booking|EPC-035]]).
- Customer messages about the change ([[EPC-037-events-and-notifications|EPC-037]]).

The Booking and Digital teams break this epic into stories after their tech design session.
