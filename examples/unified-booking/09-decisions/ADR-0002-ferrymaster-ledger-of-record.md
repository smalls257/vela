---
id: ADR-0002
type: decision
title: FERRYMASTER stays the ledger of record
initiative: INI-002
arc42: "§9"
state: decided
owner: solution lead
authored: authored
last_verified: 2026-11-20
sources: ["session 2026-08-12 Grill"]
---

# ADR-0002 FERRYMASTER stays the ledger of record

## Status

Accepted, 2026-08-12, in a Grill session with the Booking senior and the mainframe team lead.

## Context

FERRYMASTER cannot change before its vendor contract ends in 2028 (C1). The data warehouse feed, the finance reconciliation job and the loyalty scheme read it directly, and they stay out of scope until INI-004 and INI-005. Booking needs some state of its own to hold seats for 10 minutes and to answer channels quickly.

## Decision

FERRYMASTER remains the ledger of record for every booking. Booking keeps holds and a booking-state cache. Booking changes a booking's state only after FERRYMASTER accepts the write. If the two disagree, FERRYMASTER is right and Booking refreshes its cache.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Booking becomes the record and syncs to FERRYMASTER | The three direct readers would see a copy that lags the record. Moving them is INI-005's job. |
| Write to both and reconcile nightly | Two records that can disagree is the problem INI-002 exists to remove (G2). |
| Booking reads FERRYMASTER on every request, no cache | Every channel read becomes an MQ call, which costs MIPS (C5) and adds 2 s to screens that only display state. |

## Consequences

- Confirmation waits for the ledger write. The customer sees "confirming" for about 2.1 s at p95 ([[FLO-001-hold-pay-confirm|FLO-001]]).
- A failed ledger write after payment leaves a booking paid and unconfirmed until the Ledger adapter's retry succeeds. Booking keeps the hold while it retries, and on-call is alerted if retries run out.
- When INI-005 retires FERRYMASTER, this decision is the one it supersedes.

## Assumptions it depends on

- Ledger write latency is low enough for customers to wait on: [[11-unknowns-and-risks#UNK-001|UNK-001]], resolved at 2.1 s p95.
- Finance keeps reading FERRYMASTER for now: [[11-unknowns-and-risks#UNK-006|UNK-006]], open, deferred to INI-005.

Delivered by [[EPC-031-holds-and-confirms|EPC-031]] and [[EPC-032-ledger-adapter|EPC-032]]. See [[concern-data|Data]].
