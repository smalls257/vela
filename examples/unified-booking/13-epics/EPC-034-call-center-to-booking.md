---
id: EPC-034
type: epic
title: Call center moves to Booking
initiative: INI-002
state: decided
owner: "@harborline/contact-center-systems"
authored: mixed
apps: [APP-call-center, APP-booking]
delivers: [CAP-013, CAP-021, CAP-023, G1, G2]
consumes: [CON-001]
flows: [FLO-001, FLO-002]
depends_on: [EPC-031, EPC-036]
sources: ["session 2026-10-07 Grill", "session 2026-11-18 Grill"]
---

# EPC-034 Call center moves to Booking

- **Decision:** [[2026-11-18-epics]]

The call center desktop client becomes a Booking API client, gets new amend and cancel screens, and loses its terminal adapter. Agents then see the same booking state as the website and the kiosks, because all three ask Booking instead of reading FERRYMASTER through their own cache.

Still open: nothing.

**Owning team:** Contact Center Systems team.

## Who this is for and what changes

The manual fix queue goes too. It exists because the website's confirm can fail after payment, leaving agents to repair bookings the next day. Booking now retries the ledger write and keeps the hold, so nothing is left to repair. The Head of Contact Center agreed the queue closes when the old adapter is removed.

## Done when

### Agents work through Booking only

Agents hold, confirm, amend, cancel and look up bookings through the Booking API only. Every call carries the desktop's service token and a trace ID the desktop created.

- Trace: CON-001  ·  AC1  ·  [security] [observability]

### The same state as the website and the kiosks

For any booking reference, the desktop shows the same state as the website and the kiosks.

- Trace: AC2

### An amendment shows the new fare first

An amendment shows the agent the re-quoted fare from Booking before the agent commits it.

- Trace: AC3

### A waiting booking shows as confirming

A booking still waiting for the ledger shows as `confirming` on the desktop. Agents get no fix task for it.

- Trace: AC4  ·  [operations]

### The desktop's contract tests pass

The desktop's consumer-driven contract tests for the Booking API pass in Booking's provider verification.

- Trace: CON-001  ·  AC5  ·  [testing]

### The old path can be switched back

Flipping the call center's switch back sends bookings through the terminal adapter without a release, for 4 weeks after cutover.

- Trace: AC6  ·  [rollout]

### The old screens are removed after four weeks

After those 4 weeks the terminal adapter and the manual fix screens are removed from the desktop.

- Trace: AC7  ·  [data]

## Traces to

<!-- generated:traces-to sha=56f9a61d: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

| Traces to | Items |
|---|---|
| Apps | [[call-center-building-blocks\|Call center desktop]], [[booking-building-blocks\|Booking]] |
| Delivers | [[CAP-013-reserve-a-crossing\|CAP-013 Reserve a crossing]], [[CAP-021-amend-or-cancel\|CAP-021 Amend or cancel a booking]], [[CAP-023-fix-failed-bookings\|CAP-023 Fix failed bookings by hand]], [[01-goals\|G1]], [[01-goals\|G2]] |
| Consumes | [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] |
| Flows | [[FLO-001-hold-pay-confirm\|FLO-001 Hold, pay, confirm]], [[FLO-002-amend-or-cancel\|FLO-002 Amend or cancel]] |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]], [[EPC-036-amend-cancel-online\|EPC-036 Amend and cancel online]] |
| Concerns | [[concern-data\|Data]], [[concern-observability\|Observability]], [[concern-operations\|Operations]], [[concern-rollout\|Rollout]], [[concern-security\|Security]], [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]]: hold, confirm and get.
- [[EPC-036-amend-cancel-online|Amend and cancel online]]: amend and cancel on the Booking API.

## Rollout notes

Second channel, March 2027, after the website. Rollback is flipping the call center's switch back during the 4 weeks.

## Out of scope

- Changes to how agents find crossings ([[CAP-011-find-a-crossing|Find a crossing]] is unchanged).
- Customer messages after an agent's change ([[EPC-037-events-and-notifications|Booking events and customer notifications]]).

