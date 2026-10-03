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
---

# Unified Booking

- **Decision:** [[2026-08-12-goals-and-data]]

## Why now

Harbourline sells crossings through three front ends: the public website, the call centre desktop and the port kiosks. Each one talks to FERRYMASTER through its own screen-scraping adapter, so when the mainframe changes a screen, all three break. That happened eleven times in the last twelve months, usually just before a bank holiday weekend.

It also means nobody agrees on what "confirmed" means. The kiosks and the call centre cache FERRYMASTER's replies differently, and customers notice. Worst of all, if the website's confirm step fails after payment, the customer has paid for nothing until someone in the call centre fixes it by hand the next morning.

This initiative puts one application, Booking, between the front ends and the ledger. Only Booking talks to FERRYMASTER about bookings, and only Booking decides what state a booking is in.

## Goals

| ID | Goal | Measure | State |
|---|---|---|---|
| G1 | Stop mainframe changes breaking booking | Adapter incidents: 11 a year → 0 | decided |
| G2 | One answer to "is it confirmed?" in every channel | No channel disagrees on booking state | decided |
| G3 | Customers amend and cancel without phoning | 60% of amendments done online within 6 months of go-live | decided |

## Capabilities this introduces

<!-- generated: do not edit -->
| Capability | Change | Serves |
|---|---|---|
| [[CAP-014-hold-a-seat\|Hold a seat during payment]] | new | G1, G2 |
| [[CAP-022-notify-customer\|Notify customer of changes]] | new | G3 |
| [[CAP-021-amend-or-cancel\|Amend or cancel a booking]] | extended to the website and call centre | G3 |
| [[CAP-013-reserve-a-crossing\|Reserve a crossing]] | replaced by one implementation | G1, G2 |
| [[CAP-012-quote-a-fare\|Quote a fare]] | narrowed to one caller | G1 |
| [[CAP-023-fix-failed-bookings\|Fix failed bookings by hand]] | retired | G1 |
<!-- /generated -->

Full detail, including which software provides each capability before and after: [[04a-capability-delta|Capability delta]].

## Who cares about this

| Stakeholder | What they need from it |
|---|---|
| CIO | Fewer outages, and no surprise mainframe cost |
| Head of Contact Centre | No more next-morning manual fixes; amendments move online |
| Port Operations | Kiosks change only on the March and September image cycle |
| Revenue | Pricing keeps its rules; only its callers change |
| Mainframe team lead | No change to FERRYMASTER, and support limited to 2 days a week in Q1 |

## Reading paths

- **CIO / CTO:** this page → [[03-context-and-scope|Context & scope]] → [[11-unknowns-and-risks|Unknowns & risks]]
- **Product:** this page → [[04a-capability-delta|Capability delta]] → [[06-flows|Flows]]
- **Architects:** [[03-context-and-scope|Context & scope]] → [[04-solution-strategy|Strategy]] → [[05-building-blocks|Building blocks]] → [[09-decisions|Decisions]]
- **Team seniors:** your app under [[05-building-blocks|Building blocks]] → [[13-epics|Epics]]
- **QA:** [[concern-testing|Testing strategy]] → [[06-flows|Flows]] → [[13-epics|Epics]]
