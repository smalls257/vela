---
id: EPC-032
type: epic
title: Ledger adapter on FERRYMASTER's MQ transactions
initiative: INI-002
state: decided
owner: "@harborline/booking-team"
authored: mixed
apps: [APP-booking, APP-ferrymaster]
delivers: [ADR-0004, G1]
consumes: [CON-006]
flows: []
depends_on: []
sources: ["session 2026-07-14 Discover", "session 2026-08-19 Probe", "session 2026-09-16 Grill", SRC-04]
---

# EPC-032 Ledger adapter on FERRYMASTER's MQ transactions

- **Decision:** [[2026-11-18-epics]]

Booking writes to FERRYMASTER through the four message queue (MQ) transactions the mainframe team already exposes for the finance reconciliation job: BKHOLD, BKCONF, BKAMND and BKCANC ([[ADR-0004-mq-not-screen-scraping|the MQ decision]]). Screen scraping is what broke 11 times last year.

Still open: nothing.

**Owning team:** Booking team, with mainframe team support.

## Who this is for and what changes

The MQ transactions stay the same when a screen changes, and FERRYMASTER itself cannot change before 2028 (its vendor contract runs that long), so Booking adapts to what is already there.

Two people understand FERRYMASTER's mainframe programming. The mainframe team gives 2 days a week from January to March 2027 ([[11-unknowns-and-risks#UNK-003 Mainframe capacity in Q1|Mainframe capacity in Q1]]). A Booking engineer pairs with them and the MQ mapping goes into the Ledger transactions contract, so the knowledge no longer sits with two people (the mainframe knowledge risk). The ledger simulator built here is what Booking's contract tests run against ([[11-unknowns-and-risks#UNK-002 Repeatable test data|Repeatable test data]]).

## Done when

### The four ledger writes work against the test region

Booking sends BKHOLD, BKCONF, BKAMND and BKCANC in the format the Ledger transactions contract documents, and the FERRYMASTER test region accepts each one in the weekly end-to-end run.

- Trace: CON-006  ·  AC1  ·  [testing]

### A rejected write keeps the hold

When FERRYMASTER rejects a write or does not answer, Booking retries and the booking keeps its hold. No channel sees `confirmed` until FERRYMASTER has accepted.

- Trace: AC2  ·  [data]

### The same write is applied once

The same write sent twice is applied once in FERRYMASTER.

- Trace: AC3

### Ledger writes stay as fast as today

p95 ledger write latency in the weekly end-to-end run is no worse than the 2.1 s measured for [[11-unknowns-and-risks#UNK-001 Ledger write latency|Ledger write latency]].

- Trace: AC4

### Mainframe volume stays within the budget

Booking's MQ volume stays within the existing millions of instructions per second (MIPS) budget agreed with the mainframe team lead.

- Trace: CST-5  ·  AC5  ·  [cost]

### Contract tests run against the simulator

Booking's contract tests run against the ledger simulator with no connection to FERRYMASTER, and the simulator gives the replies the Ledger transactions contract documents for every transaction.

- Trace: CON-006  ·  AC6  ·  [testing]

## Traces to

<!-- generated:traces-to sha=32c664bb: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[booking-building-blocks\|Booking]], [[ferrymaster-building-blocks\|FERRYMASTER]] |
| Delivers | [[ADR-0004-mq-not-screen-scraping\|ADR-0004 Use FERRYMASTER's existing MQ transactions instead of screen scraping]], [[01-goals\|G1]] |
| Consumes | [[ferrymaster-building-blocks#CON-006 Ledger transactions\|CON-006 Ledger transactions]] |
| Flows | none |
| Depends on | none |
| Concerns | [[concern-cost\|Cost]], [[concern-data\|Data]], [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

Also related:

- [[ADR-0002-ferrymaster-ledger-of-record|the ledger-of-record decision]]
- [[11-unknowns-and-risks#UNK-001 Ledger write latency|Ledger write latency]]
- [[11-unknowns-and-risks#UNK-002 Repeatable test data|Repeatable test data]]
- [[11-unknowns-and-risks#UNK-003 Mainframe capacity in Q1|Mainframe capacity in Q1]]

## Depends on

No other epic. It depends on the mainframe team's Q1 2027 time.

## Rollout notes

The adapter is proven against the FERRYMASTER test region during the January to March 2027 pairing window. Its first production writes come with the website cutover in [[EPC-033-website-to-booking|Website moves to Booking]].

## Out of scope

- Any change to FERRYMASTER or its MQ transactions.
- The data warehouse feed, the finance reconciliation job and the loyalty scheme, which keep reading FERRYMASTER directly (the Loyalty Revamp and Mainframe Exit initiatives).

