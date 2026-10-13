---
id: EPC-038
type: epic
title: Pricing serves Booking only
initiative: INI-002
state: decided
owner: "@harbourline/revenue-team"
authored: mixed
apps: [APP-pricing, APP-booking]
delivers: [CAP-012, CON-003]
consumes: []
flows: []
depends_on: [EPC-031, EPC-033, EPC-034, EPC-035]
sources: ["session 2026-07-28 Shape", "session 2026-11-18 Grill"]
---

# EPC-038 Pricing serves Booking only

- **Decision:** [[2026-11-18-epics]]

Pricing keeps the same job and the same containers. What changes is who calls it: today the website, the call centre and the kiosks each ask the Quote service for fares, and after this epic only Booking does.

Still open: nothing.

**Owning team:** Revenue team.

## Who this is for and what changes

The Platform gateway enforces that.

One caller means the Revenue team changes fare rules against one consumer and one contract test. Today a change to a quote has to be checked against three front ends that each call Pricing their own way. The restriction goes on last, after the September 2027 kiosk image removes the final direct caller.

## Done when

### Both teams' contract tests pass

Booking's contract test for the fare quote passes against Pricing's provider verification, in both teams' pipelines.

- Trace: CON-003  ·  AC1  ·  [testing]

### The quote is the same as today

For the same crossing and fare rules, Booking gets the same quote the front ends get today.

- Trace: AC2

### Only Booking may ask for a quote

Once the restriction is on, a quote request from any caller other than Booking is refused at the Platform gateway.

- Trace: AC3  ·  [security]

### No direct callers before the restriction

Before the restriction goes on, the gateway shows no direct quote requests from the website, the call centre or the kiosks.

- Trace: AC4  ·  [rollout]

## Traces to

<!-- generated:traces-to sha=3f3e7f6d: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[pricing-building-blocks\|Pricing]], [[booking-building-blocks\|Booking]] |
| Delivers | [[CAP-012-quote-a-fare\|CAP-012 Quote a fare]], [[pricing-building-blocks#CON-003 Quote a fare\|CON-003 Quote a fare]] |
| Consumes | none |
| Flows | none |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]], [[EPC-033-website-to-booking\|EPC-033 Website moves to Booking]], [[EPC-034-call-centre-to-booking\|EPC-034 Call centre moves to Booking]], [[EPC-035-kiosks-to-booking\|EPC-035 Kiosks move to Booking in the March image]] |
| Concerns | [[concern-rollout\|Rollout]], [[concern-security\|Security]], [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

Also related: [[ADR-0001-one-booking-context|the one-application decision]].

## Depends on

- [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]]: Booking asks for quotes.
- [[EPC-033-website-to-booking|Website moves to Booking]], [[EPC-034-call-centre-to-booking|Call centre moves to Booking]], [[EPC-035-kiosks-to-booking|Kiosks move to Booking in the March image]]: each front end stops calling Pricing directly.

## Rollout notes

The contract test runs from the start. The gateway restriction is switched on after the September 2027 kiosk image is rolled out.

## Out of scope

- Fare rules and the Fare rules store.
- Any change inside Pricing.

