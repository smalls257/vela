---
id: CAP-023
type: capability
title: Fix failed bookings by hand
state: proposed
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-023 Fix failed bookings by hand

Lets an agent repair a booking that was paid for but never confirmed.

**Domain:** Serve

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

<!-- generated: do not edit -->
| Application | Today | After |
|---|---|---|
| [[call-centre-building-blocks\|Call centre desktop]] | manual fix queue, worked the next morning | retired: nobody, [[booking-building-blocks\|Booking]] retries the ledger write and keeps the hold |
<!-- /generated -->

## Initiatives that touch this

<!-- generated: do not edit -->
- [[04a-capability-delta|INI-002 Unified Booking]] (retire)
<!-- /generated -->

## Flows

None after INI-002. The retry path in [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]] replaces it.

## Delivered by

- [[EPC-034-call-centre-to-booking|EPC-034 Call centre moves to Booking]] retires the manual fix queue.
