---
id: goals
type: initiative-section
title: Unified Booking
initiative: INI-002
arc42: "§1"
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-06 Dump & Diverge", "session 2026-08-12 Grill", SRC-01]
last_verified: 2026-11-18
verified_by: "@hl-solution-lead"
---

# Unified Booking

- **Decision:** [[2026-08-12-goals-and-data]]

## Where it stands

<!-- generated:where-it-stands sha=970d4f76: do not edit, run vela render -->
**Where each app has got to**

| App | Step reached | Open questions holding it up | Topics nobody has looked at | Contracts settled |
|---|---|---|---|---|
| [[booking-building-blocks\|Booking]] | writing epics | 0 | 0 | 7 of 7 |
| [[call-center-building-blocks\|Call center desktop]] | writing epics | 0 | 0 | 1 of 1 |
| [[kiosks-building-blocks\|Port kiosks]] | writing epics | 0 | 0 | 1 of 1 |
| [[notifications-building-blocks\|Notifications]] | writing epics | 0 | 0 | 1 of 1 |
| [[pricing-building-blocks\|Pricing]] | writing epics | 0 | 0 | 1 of 1 |
| [[website-building-blocks\|Public website]] | writing epics | 0 | 0 | 1 of 1 |

**Handed to its team:** [[booking-building-blocks|Booking]] (Booking senior, 2026-11-10, PR #23)

**Open questions**

| Question | Who answers | Answer needed by | Holds up |
|---|---|---|---|
| [[11-unknowns-and-risks#UNK-006 Finance on Booking events\|Finance on Booking events (UNK-006)]] | @hl-platform-lead (Platform lead) | 2027-03-01 | nothing yet |
| [[11-unknowns-and-risks#UNK-008 Review of the customer data Booking holds\|Review of the customer data Booking holds (UNK-008)]] | @hl-solution-lead (solution lead) | 2026-12-15 | nothing yet |

**Last session:** 2026-11-19

**Gaps in the planned work:** 0, listed on [[13-epics|Epics]]

**Build progress:** tracked in each team's tickets, not in this vault
<!-- /generated:where-it-stands -->

## Progress by app

<!-- generated:progress-map sha=231431df: do not edit, run vela render -->
**How sure each app's items are,** as of 2026-11-19 (the last session)

| App | Step reached | Early ideas | Assumed | Confirmed | Decided | Oldest open question | Next session |
|---|---|---|---|---|---|---|---|
| [[booking-building-blocks\|Booking]] | writing epics | 0 | 0 | 1 | 4 | none | none |
| [[call-center-building-blocks\|Call center desktop]] | writing epics | 0 | 0 | 0 | 2 | none | none |
| [[kiosks-building-blocks\|Port kiosks]] | writing epics | 0 | 0 | 0 | 2 | none | none |
| [[notifications-building-blocks\|Notifications]] | writing epics | 0 | 0 | 0 | 2 | none | none |
| [[pricing-building-blocks\|Pricing]] | writing epics | 0 | 0 | 0 | 3 (1 by override) | none | none |
| [[website-building-blocks\|Public website]] | writing epics | 0 | 0 | 0 | 2 | none | none |
| [[customer-identity-building-blocks\|Customer identity]] | - | 0 | 0 | 2 | 0 | none | none |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | - | 0 | 0 | 3 | 0 | none | none |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | - | 0 | 0 | 2 | 0 | none | none |
<!-- /generated:progress-map -->

## Why now

Harborline sells crossings through three front ends: the public website, the call center desktop and the port kiosks. Each one talks to FERRYMASTER through its own screen-scraping adapter, so when the mainframe changes a screen, all three break. That happened eleven times in the last twelve months, usually just before a bank holiday weekend.

It also means nobody agrees on what "confirmed" means. The kiosks and the call center cache FERRYMASTER's replies differently, and customers notice. Worst of all, if the website's confirm step fails after payment, the customer has paid for nothing until someone in the call center fixes it by hand the following day.

This initiative puts one application, Booking, between the front ends and the ledger. Only Booking talks to FERRYMASTER about bookings, and only Booking decides what state a booking is in.

## Goals

| ID | Goal | Measure | State |
|---|---|---|---|
| G1 | Stop mainframe changes breaking booking | Adapter incidents: 11 a year → 0 | decided |
| G2 | One answer to "is it confirmed?" in every channel | No channel disagrees on booking state | decided |
| G3 | Customers amend and cancel without phoning | 60% of amendments done online within 6 months of go-live | decided |

## Capabilities this introduces

Each capability page says what changes and which software provides it before and after.

- [[CAP-014-hold-a-seat|Hold a seat during payment]], serving G1 and G2
- [[CAP-022-notify-customer|Notify customer of changes]], serving G3
- [[CAP-021-amend-or-cancel|Amend or cancel a booking]], serving G3
- [[CAP-013-reserve-a-crossing|Reserve a crossing]], serving G1 and G2
- [[CAP-012-quote-a-fare|Quote a fare]], serving G1
- [[CAP-023-fix-failed-bookings|Fix failed bookings by hand]], serving G1

Full detail, including which software provides each capability before and after: [[04a-capability-delta|Capability delta]].

## Who cares about this

| Stakeholder | What they need from it |
|---|---|
| CIO | Fewer outages, and no surprise mainframe cost |
| Head of Contact Center | No more next-morning manual fixes; amendments move online |
| Port Operations | Kiosks change only on the March and September image cycle |
| Revenue | Pricing keeps its rules; only its callers change |
| Mainframe team lead | No change to FERRYMASTER, and support limited to 2 days a week in Q1 |

## Reading paths

- **CIO / CTO:** this page → [[03-context-and-scope|Context & scope]] → [[11-unknowns-and-risks|Unknowns & risks]]
- **Product:** this page → [[04a-capability-delta|Capability delta]] → [[06-flows|Flows]]
- **Architects:** [[03-context-and-scope|Context & scope]] → [[04-solution-strategy|Strategy]] → [[05-building-blocks|Building blocks]] → [[09-decisions|Decisions]]
- **Team seniors:** your app under [[05-building-blocks|Building blocks]] → [[13-epics|Epics]]
- **QA:** [[concern-testing|Testing strategy]] → [[06-flows|Flows]] → [[13-epics|Epics]]
