---
id: CAP-021
type: capability
title: Amend or cancel a booking
origin: proposed
change: extend
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-021 Amend or cancel a booking

- **Decision:** [[2026-08-12-goals-and-data]]

Lets a customer change or cancel a booking they already have.

**Domain:** Serve

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

| Application | Today | After |
|---|---|---|
| [[call-centre-building-blocks\|Call centre desktop]] | only channel, through a mainframe screen | amend and cancel screens on the Booking API |
| [[website-building-blocks\|Public website]] | none | amend and cancel pages |
| [[kiosks-building-blocks\|Port kiosks]] | none | shows booking state only; no amend or cancel |
| [[booking-building-blocks\|Booking]] | did not exist | checks the change, re-quotes, writes to FERRYMASTER |

## Initiatives that touch this

- [[04a-capability-delta|INI-002 Unified Booking]] (extend)
- INI-005 Mainframe Exit (writes to FERRYMASTER; no pages yet)

## Flows

- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]

## Delivered by

<!-- generated:delivered-by sha=f20e8bd8: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-034-call-centre-to-booking\|EPC-034 Call centre moves to Booking]] | @harbourline/contact-centre-systems | decided |
| [[EPC-036-amend-cancel-online\|EPC-036 Amend and cancel online]] | @harbourline/booking-team @harbourline/digital-team | decided |
<!-- /generated:delivered-by -->
