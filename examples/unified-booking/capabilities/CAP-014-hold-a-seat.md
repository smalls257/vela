---
id: CAP-014
type: capability
title: Hold a seat during payment
origin: proposed
change: new
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-014 Hold a seat during payment

- **Decision:** [[2026-08-12-goals-and-data]]

Lets a customer keep a seat on a crossing for 10 minutes while they pay, so no other channel can sell it.

**Domain:** Sell

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

<!-- generated: do not edit -->
| Application | Today | After |
|---|---|---|
| [[booking-building-blocks\|Booking]] | nothing holds a seat; overbooking fixed by hand | 10-minute hold, released if unpaid |
<!-- /generated -->

## Initiatives that touch this

<!-- generated: do not edit -->
- [[04a-capability-delta|INI-002 Unified Booking]] (new)
- INI-005 Mainframe Exit (writes to FERRYMASTER; no pages yet)
<!-- /generated -->

## Flows

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]: hold a seat.

## Delivered by

- [[EPC-031-holds-and-confirms|EPC-031 Booking holds and confirms crossings]]
