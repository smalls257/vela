---
id: CAP-022
type: capability
title: Notify customer of changes
origin: proposed
change: new
domain: Customer contact
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-022 Notify customer of changes

- **Decision:** [[2026-08-12-goals-and-data]]

Lets a customer hear about a change to their booking, wherever the change was made.

**Domain:** Serve

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

| Application | Today | After |
|---|---|---|
| [[website-building-blocks\|Public website]] | sends emails for its own bookings | stops sending booking emails |
| [[notifications-building-blocks\|Notifications]] | not used for bookings | sends email or SMS on Booking state changed events |

## Initiatives that touch this

- [[04a-capability-delta|INI-002 Unified Booking]] (new)

## Flows

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]: notify customer.
- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]: notify customer.
- [[FLO-003-notify-on-change|FLO-003 Notify on change]]

## Delivered by

<!-- generated:delivered-by sha=89ec5c52: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-037-events-and-notifications\|EPC-037 Booking events and customer notifications]] | @harborline/booking-team @harborline/platform-team | decided |
<!-- /generated:delivered-by -->
