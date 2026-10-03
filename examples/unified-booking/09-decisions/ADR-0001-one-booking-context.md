---
id: ADR-0001
type: decision
title: One Booking application rather than a shared adapter library
initiative: INI-002
arc42: "§9"
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-28 Grill"]
---

# ADR-0001 One Booking application rather than a shared adapter library

- **Decision:** [[2026-07-28-solution-strategy]]

## Status

Accepted, 2026-07-28, in a Grill session with the Booking senior, Digital senior, Contact Centre Systems senior and Port Systems senior.

## Context

The website, call centre desktop and kiosks each talk to FERRYMASTER through their own screen-scraping adapter. Each adapter decides for itself when a booking counts as confirmed, and each caches replies differently. That is why the call centre and the kiosks disagree about bookings (G2), and why a mainframe screen change breaks all three at once (G1).

## Decision

Build one Booking application. It is the only thing that talks to FERRYMASTER about bookings, and the only place that decides whether a booking is held, confirmed, amended or cancelled. Every channel calls the Booking API ([[booking-building-blocks#CON-001|CON-001]]).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Shared adapter library used by all three front ends | Quicker to build. Each team would still embed it and decide what "confirmed" means around it. Kiosks upgrade twice a year, so channels would run different library versions for months and disagree again. |
| Gateway facade over the three existing adapters | Puts one URL in front of three behaviours. Nothing would own booking state, so G2 stays unmet. |

## Consequences

- A new Booking team is needed, and it owns the service and the Ledger adapter ([[concern-ownership|Ownership]]).
- Every channel has to move, one at a time ([[concern-rollout|Rollout]]).
- Booking becomes a single point of failure for selling crossings, so it needs on-call and runbooks from day one ([[concern-operations|Operations]]).
- Booking can publish one state-change event that Notifications and, later, Finance consume ([[booking-building-blocks#CON-002|CON-002]]).

## Assumptions it depends on

- The mainframe team has time to support one new client in Q1 2027: [[11-unknowns-and-risks#UNK-003|UNK-003]], resolved.
- Someone runs Booking out of hours: [[11-unknowns-and-risks#UNK-007|UNK-007]], resolved.

Delivered by [[EPC-031-holds-and-confirms|EPC-031]].
