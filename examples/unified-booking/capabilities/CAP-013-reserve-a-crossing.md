---
id: CAP-013
type: capability
title: Reserve a crossing
origin: proposed
change: replace
domain: Booking
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-013 Reserve a crossing

- **Decision:** [[2026-08-12-goals-and-data]]

Lets a customer turn a chosen crossing into a confirmed booking that every sales channel agrees on.

**Domain:** Sell

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

| Application | Today | After |
|---|---|---|
| [[website-building-blocks\|Public website]] | FM screen adapter into FERRYMASTER | Booking API client |
| [[call-centre-building-blocks\|Call centre desktop]] | terminal adapter into FERRYMASTER | Booking API client |
| [[kiosks-building-blocks\|Port kiosks]] | FM adapter into FERRYMASTER | Booking API v1 client (March 2027 image) |
| [[booking-building-blocks\|Booking]] | did not exist | decides held, confirmed, amended, cancelled |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | ledger of record | ledger of record, written only by Booking |

## Initiatives that touch this

- [[04a-capability-delta|INI-002 Unified Booking]] (replace)
- INI-004 Loyalty Revamp (overlap; no pages yet)
- INI-005 Mainframe Exit (writes to FERRYMASTER; no pages yet)

## Flows

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]: confirm booking.

## Delivered by

<!-- generated:delivered-by sha=63e70d5e: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]] | @harbourline/booking-team | decided |
| [[EPC-033-website-to-booking\|EPC-033 Website moves to Booking]] | @harbourline/digital-team | decided |
| [[EPC-034-call-centre-to-booking\|EPC-034 Call centre moves to Booking]] | @harbourline/contact-centre-systems | decided |
| [[EPC-035-kiosks-to-booking\|EPC-035 Kiosks move to Booking in the March image]] | @harbourline/port-systems | decided |
<!-- /generated:delivered-by -->
