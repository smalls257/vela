---
id: CAP-015
type: capability
title: Take payment
origin: proposed
change: unchanged
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-015 Take payment

- **Decision:** [[2026-08-12-goals-and-data]]

Lets a customer pay for a crossing by card without Harbourline ever handling the card.

**Domain:** Sell

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

<!-- generated: do not edit -->
| Application | Today | After |
|---|---|---|
| Tidepay (external) | hosted payment page, called by each front end | same page; outcome reported to [[booking-building-blocks\|Booking]] |
<!-- /generated -->

## Initiatives that touch this

<!-- generated: do not edit -->
- [[04a-capability-delta|INI-002 Unified Booking]] (unchanged)
<!-- /generated -->

## Flows

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]: take payment.

## Delivered by

No epic changes this capability. [[EPC-031-holds-and-confirms|EPC-031]] receives the payment outcome on [[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007]].
