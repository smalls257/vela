---
id: CAP-022
type: capability
title: Notify customer of changes
state: proposed
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-022 Notify customer of changes

Lets a customer hear about a change to their booking, wherever the change was made.

**Domain:** Serve

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

<!-- generated: do not edit -->
| Application | Today | After |
|---|---|---|
| [[website-building-blocks\|Public website]] | sends emails for its own bookings | stops sending booking emails |
| [[notifications-building-blocks\|Notifications]] | not used for bookings | sends email or SMS on Booking state changed events |
<!-- /generated -->

## Initiatives that touch this

<!-- generated: do not edit -->
- [[04a-capability-delta|INI-002 Unified Booking]] (new)
<!-- /generated -->

## Flows

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]: notify customer.
- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]: notify customer.
- [[FLO-003-notify-on-change|FLO-003 Notify on change]]

## Delivered by

- [[EPC-037-events-and-notifications|EPC-037 Booking events and customer notifications]]
