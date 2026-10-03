---
id: EPC-038
type: epic
title: Pricing serves Booking only
initiative: INI-002
state: decided
owner: "@harbourline/revenue-team"
authored: authored
apps: [APP-pricing, APP-booking]
delivers: [CAP-012, CON-003]
consumes: []
flows: []
depends_on: [EPC-031, EPC-033, EPC-034, EPC-035]
sources: ["session 2026-07-28 Shape", "session 2026-11-18 Grill"]
---

# EPC-038 Pricing serves Booking only

- **Decision:** [[2026-11-18-epics]]

Pricing keeps the same job and the same containers. What changes is who calls it: today the website, the call centre and the kiosks each ask the Quote service for fares, and after this epic only Booking does. The Platform gateway enforces that.

One caller means the Revenue team changes fare rules against one consumer and one contract test. Today a change to a quote has to be checked against three front ends that each call Pricing their own way. The restriction goes on last, after the September 2027 kiosk image removes the final direct caller.

**Owning team:** Revenue team.

## Epic acceptance criteria

1. Booking's contract test for CON-003 passes against Pricing's provider verification, in both teams' pipelines. [testing]
2. For the same crossing and fare rules, Booking gets the same quote the front ends get today.
3. Once the restriction is on, a quote request from any caller other than Booking is refused at the Platform gateway. [security]
4. Before the restriction goes on, the gateway shows no direct quote requests from the website, the call centre or the kiosks. [rollout]

## Traces to

- Capabilities: [[CAP-012-quote-a-fare|CAP-012 Quote a fare]]
- Contracts: [[pricing-building-blocks#CON-003 Quote a fare|CON-003 Quote a fare]]
- Concerns: [[concern-security|Security]] (gateway restriction), [[concern-testing|Testing]]
- Decisions: [[ADR-0001-one-booking-context|ADR-0001]]
- Apps: [[pricing-building-blocks|Pricing]], [[booking-building-blocks|Booking]]

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]]: Booking asks for quotes.
- [[EPC-033-website-to-booking|EPC-033]], [[EPC-034-call-centre-to-booking|EPC-034]], [[EPC-035-kiosks-to-booking|EPC-035]]: each front end stops calling Pricing directly.

## Rollout notes

The contract test runs from the start. The gateway restriction is switched on after the September 2027 kiosk image is rolled out.

## Out of scope

- Fare rules and the Fare rules store.
- Any change inside Pricing.

The Revenue team breaks this epic into stories after their tech design session.
