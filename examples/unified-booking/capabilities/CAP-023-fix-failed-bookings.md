---
id: CAP-023
type: capability
title: Fix failed bookings by hand
origin: proposed
change: retire
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-023 Fix failed bookings by hand

- **Decision:** [[2026-08-12-goals-and-data]]

Lets an agent repair a booking that was paid for but never confirmed.

**Domain:** Serve

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

| Application | Today | After |
|---|---|---|
| [[call-centre-building-blocks\|Call centre desktop]] | manual fix queue, worked the next morning | retired: nobody, [[booking-building-blocks\|Booking]] retries the ledger write and keeps the hold |

## Initiatives that touch this

- [[04a-capability-delta|INI-002 Unified Booking]] (retire)

## Flows

None after INI-002. The retry path in [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]] replaces it.

## Delivered by

- [[EPC-034-call-centre-to-booking|EPC-034 Call centre moves to Booking]] retires the manual fix queue.
