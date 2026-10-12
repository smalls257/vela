---
id: APP-ferrymaster
type: app-building-blocks
title: FERRYMASTER
initiative: INI-002
arc42: "§5"
c4: context
state: fact
change: integrated
owner: "@harbourline/mainframe-team"
authored: mixed
sources: [SRC-04, "UNK-003 mainframe capacity 2026-08-14", "UNK-002 test data decision 2026-09-16"]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / FERRYMASTER

# FERRYMASTER

FERRYMASTER is the 1990s mainframe that holds Harbourline's booking ledger. It stays the ledger of record ([[ADR-0002-ferrymaster-ledger-of-record|the ledger-of-record decision]]). Booking writes to it through four MQ transactions the mainframe team already exposes for the finance job ([[ADR-0004-mq-not-screen-scraping|the MQ decision]]).

FERRYMASTER is not responsible for holds during payment or for telling channels a booking's state. Booking does both.

| Change in INI-002 | Owner team |
|---|---|
| Integrated, unchanged. The vendor contract ends in 2028 and the code cannot change (CST-1). | Mainframe team (2 people) |

<!-- generated:app-context sha=24c277df: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_ferrymaster["FERRYMASTER (integrated)"]
  n_APP_ferrymaster -->|"CON-006"| n_APP_booking
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_ferrymaster focus
  class n_APP_booking new
```
<!-- /generated:app-context -->

FERRYMASTER is a black box on this page. Nobody in this initiative changes it, and only two people understand its COBOL, so we describe the transactions it exposes and stop there.

## Contracts this app provides

### CON-006 Ledger transactions

- **Crosses the boundary:** four MQ transactions. BKHOLD reserves a seat, BKCONF confirms a paid booking, BKAMND changes a booking, BKCANC cancels one or releases an expired hold. Each reply carries the ledger reference or a return code. The full field mapping is documented with this contract, which is how R-01 is mitigated.
- **Consumers:** [[booking-building-blocks|Booking]], through its Ledger adapter only.
- **Change policy:** FERRYMASTER cannot change. The mainframe team announces any MQ change 8 weeks ahead.
- **Change:** new consumers
- **Tested by:** Booking runs a ledger simulator in its contract tests, because the FERRYMASTER test region refreshes only once a year. One weekly end-to-end run goes against the test region. The mainframe team does not run tests of its own for this contract. The simulator tests run on every Booking build, the QA lead owns the weekly run, and a failure blocks the Booking release.
- **State:** fact
- **Source:** SRC-04

## Contracts this app consumes

<!-- generated:contracts-consumed sha=140bedbf: do not edit, run planner render -->
none
<!-- /generated:contracts-consumed -->

## Concerns

This app's cell on each concern is in the [[08-concerns|concern matrix]]. The concern pages say what each cell means.

The mainframe team gives 2 days a week from January to March 2027 ([[11-unknowns-and-risks#UNK-003 Mainframe capacity in Q1|Mainframe capacity in Q1]]) and pairs with the Booking team in that time.

## Epics

<!-- generated:epics-for-app sha=496df681: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-032-ledger-adapter\|EPC-032 Ledger adapter on FERRYMASTER's MQ transactions]] | @harbourline/booking-team | decided |
<!-- /generated:epics-for-app -->

Next: [[ferrymaster-runtime|FERRYMASTER runtime]]
