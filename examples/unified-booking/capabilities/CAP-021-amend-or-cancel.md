---
id: CAP-021
type: capability
title: Amend or cancel a booking
state: proposed
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-021 Amend or cancel a booking

Lets a customer change or cancel a booking they already have.

**Domain:** Serve

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

<!-- generated: do not edit -->
| Application | Today | After |
|---|---|---|
| [[call-centre-building-blocks\|Call centre desktop]] | only channel, through a mainframe screen | amend and cancel screens on the Booking API |
| [[website-building-blocks\|Public website]] | none | amend and cancel pages |
| [[kiosks-building-blocks\|Port kiosks]] | none | shows booking state only; no amend or cancel |
| [[booking-building-blocks\|Booking]] | did not exist | checks the change, re-quotes, writes to FERRYMASTER |
<!-- /generated -->

## Initiatives that touch this

<!-- generated: do not edit -->
- [[04a-capability-delta|INI-002 Unified Booking]] (extend)
- INI-005 Mainframe Exit (writes to FERRYMASTER; no pages yet)
<!-- /generated -->

## Flows

- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]

## Delivered by

- [[EPC-036-amend-cancel-online|EPC-036 Amend and cancel online]]
- [[EPC-034-call-centre-to-booking|EPC-034 Call centre moves to Booking]]
