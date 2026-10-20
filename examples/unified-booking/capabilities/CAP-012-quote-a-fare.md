---
id: CAP-012
type: capability
title: Quote a fare
origin: proposed
change: narrow
domain: Sales
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "04a-capability-delta"]
---

# CAP-012 Quote a fare

- **Decision:** [[2026-08-12-goals-and-data]]

Gives a customer or an agent the price of a crossing before they commit to it.

**Domain:** Sell

**Source:** proposed in session 2026-07-14 Shape. To be reconciled when an official capability map arrives.

## Provided by

| Application | Today | After |
|---|---|---|
| [[pricing-building-blocks\|Pricing]] | quotes for the website, call center and kiosks | quotes for [[booking-building-blocks\|Booking]] only |
| [[website-building-blocks\|Public website]], [[call-center-building-blocks\|Call center desktop]], [[kiosks-building-blocks\|Port kiosks]] | call Pricing directly | get fares through Booking |

## Initiatives that touch this

- [[04a-capability-delta|INI-002 Unified Booking]] (narrow)

## Flows

- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]: re-quote on amend.

## Delivered by

<!-- generated:delivered-by sha=e697d08e: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

| Epic | Owner | State |
|---|---|---|
| [[EPC-038-pricing-serves-booking\|EPC-038 Pricing serves Booking only]] | @harborline/revenue-team | decided |
<!-- /generated:delivered-by -->
