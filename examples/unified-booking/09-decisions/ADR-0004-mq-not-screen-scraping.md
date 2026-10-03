---
id: ADR-0004
type: decision
title: Use FERRYMASTER's existing MQ transactions instead of screen scraping
initiative: INI-002
arc42: "§9"
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-14 Discover", SRC-04]
---

# ADR-0004 Use FERRYMASTER's existing MQ transactions instead of screen scraping

- **Decision:** [[2026-07-28-solution-strategy]]

## Status

Accepted, 2026-07-14. It came out of a Discover session with the mainframe team lead. The team planned to build one shared screen scraper inside Booking until the mainframe team lead mentioned that FERRYMASTER already exposes BKHOLD, BKCONF, BKAMND and BKCANC over MQ for the finance reconciliation job.

## Context

Every adapter today scrapes FERRYMASTER screens. A screen change broke all three front ends 11 times in the last 12 months (G1). FERRYMASTER itself cannot change (CST-1), and its processing must stay within the MIPS budget (CST-5).

## Decision

Booking's Ledger adapter writes to FERRYMASTER only through the existing MQ transactions ([[ferrymaster-building-blocks#CON-006|CON-006]]). It does not scrape screens. The Ledger adapter is the only Booking component that talks to FERRYMASTER.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| One screen scraper inside Booking | Cuts three breakages to one. Still breaks on every screen change, so G1 stays unmet. |
| New MQ transactions built for Booking | Needs FERRYMASTER changes (CST-1) and COBOL time from a two-person team. |
| Read and write FERRYMASTER's files directly | Bypasses the mainframe's own rules and the vendor contract forbids it. |

## Consequences

- Screen changes no longer affect booking. MQ changes are announced 8 weeks ahead, so Booking has time to adapt.
- Booking depends on MQ transactions designed for a batch job. Latency had to be measured before design ([[11-unknowns-and-risks#UNK-001|UNK-001]]).
- The MQ mapping had to be written down, which also reduces the risk that only two people understand it ([[11-unknowns-and-risks#R-01|R-01]]).
- MQ transactions use less mainframe processing than terminal sessions. The mainframe team lead confirmed the volume fits the MIPS budget ([[concern-cost|Cost]]).

## Assumptions it depends on

- MQ write latency is acceptable for a customer waiting on a confirm: [[11-unknowns-and-risks#UNK-001|UNK-001]], resolved.
- Booking can test against the MQ transactions without fresh test data from the mainframe: [[11-unknowns-and-risks#UNK-002|UNK-002]], resolved with a ledger simulator.
- The mainframe team has time to support Booking's first MQ client: [[11-unknowns-and-risks#UNK-003|UNK-003]], resolved.

Delivered by [[EPC-032-ledger-adapter|EPC-032]].
