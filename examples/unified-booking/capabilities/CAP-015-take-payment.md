---
id: CAP-015
type: capability
title: Take payment
origin: proposed
change: unchanged
domain: Payments
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-015 Take payment

- **Decision:** [[2026-08-12-goals-and-data]]

Takes a customer's card payment for a crossing by card without Harbourline ever handling the card.

**Domain:** Sell

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

| Application | Today | After |
|---|---|---|
| Tidepay (external) | hosted payment page, called by each front end | same page; outcome reported to [[booking-building-blocks\|Booking]] |

## Initiatives that touch this

- [[04a-capability-delta|INI-002 Unified Booking]] (unchanged)

## Flows

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]: take payment.

## Delivered by

<!-- generated:delivered-by sha=140bedbf: do not edit, run planner render -->
none
<!-- /generated:delivered-by -->

No epic changes this capability. [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]] receives the payment outcome on [[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]].
