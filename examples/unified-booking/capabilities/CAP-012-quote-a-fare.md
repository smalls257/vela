---
id: CAP-012
type: capability
title: Quote a fare
state: proposed
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-012 Quote a fare

Lets a customer or an agent know the price of a crossing before they commit to it.

**Domain:** Sell

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

<!-- generated: do not edit -->
| Application | Today | After |
|---|---|---|
| [[pricing-building-blocks\|Pricing]] | quotes for the website, call centre and kiosks | quotes for [[booking-building-blocks\|Booking]] only |
| [[website-building-blocks\|Public website]], [[call-centre-building-blocks\|Call centre desktop]], [[kiosks-building-blocks\|Port kiosks]] | call Pricing directly | get fares through Booking |
<!-- /generated -->

## Initiatives that touch this

<!-- generated: do not edit -->
- [[04a-capability-delta|INI-002 Unified Booking]] (narrow)
<!-- /generated -->

## Flows

- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]: re-quote on amend.

## Delivered by

- [[EPC-038-pricing-serves-booking|EPC-038 Pricing serves Booking only]]
