---
id: EPC-034
type: epic
title: Call centre moves to Booking
initiative: INI-002
state: decided
owner: "@harbourline/contact-centre-systems"
authored: mixed
apps: [APP-call-centre, APP-booking]
delivers: [CAP-013, CAP-021, CAP-023, G1, G2]
consumes: [CON-001]
flows: [FLO-001, FLO-002]
depends_on: [EPC-031, EPC-036]
sources: ["session 2026-10-07 Grill", "session 2026-11-18 Grill"]
---

# EPC-034 Call centre moves to Booking

- **Decision:** [[2026-11-18-epics]]

The call centre desktop client becomes a Booking API client, gets new amend and cancel screens, and loses its terminal adapter. Agents then see the same booking state as the website and the kiosks, because all three ask Booking instead of reading FERRYMASTER through their own cache.

The manual fix queue goes too. It exists because the website's confirm can fail after payment, leaving agents to repair bookings the next morning. Booking now retries the ledger write and keeps the hold, so nothing is left to repair. The Head of Contact Centre agreed the queue closes when the old adapter is removed.

**Owning team:** Contact Centre Systems team.

## Epic acceptance criteria

1. Agents hold, confirm, amend, cancel and look up bookings through CON-001 only. Every call carries the desktop's service token and a trace ID the desktop created. [security] [observability]
2. For any booking reference, the desktop shows the same state as the website and the kiosks.
3. An amendment shows the agent the re-quoted fare from Booking before the agent commits it.
4. A booking still waiting for the ledger shows as `confirming` on the desktop. Agents get no fix task for it. [operations]
5. The desktop's consumer-driven contract tests for CON-001 pass in Booking's provider verification. [testing]
6. Flipping the call centre's switch back sends bookings through the terminal adapter without a release, for 4 weeks after cutover. [rollout]
7. After those 4 weeks the terminal adapter and the manual fix screens are removed from the desktop. [data]

## Traces to

<!-- generated:traces-to sha=a2a5873d: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[call-centre-building-blocks\|Call centre desktop]], [[booking-building-blocks\|Booking]] |
| Delivers | [[CAP-013-reserve-a-crossing\|CAP-013 Reserve a crossing]], [[CAP-021-amend-or-cancel\|CAP-021 Amend or cancel a booking]], [[CAP-023-fix-failed-bookings\|CAP-023 Fix failed bookings by hand]], [[01-goals\|G1]], [[01-goals\|G2]] |
| Consumes | [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] |
| Flows | [[FLO-001-hold-pay-confirm\|FLO-001 Hold, pay, confirm]], [[FLO-002-amend-or-cancel\|FLO-002 Amend or cancel]] |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]], [[EPC-036-amend-cancel-online\|EPC-036 Amend and cancel online]] |
| Concerns | [[concern-data\|Data]], [[concern-observability\|Observability]], [[concern-operations\|Operations]], [[concern-rollout\|Rollout]], [[concern-security\|Security]], [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]]: hold, confirm and get.
- [[EPC-036-amend-cancel-online|EPC-036]]: amend and cancel on CON-001.

## Rollout notes

Second channel, March 2027, after the website. Rollback is flipping the call centre's switch back during the 4 weeks.

## Out of scope

- Changes to how agents find crossings ([[CAP-011-find-a-crossing|CAP-011]] is unchanged).
- Customer messages after an agent's change ([[EPC-037-events-and-notifications|EPC-037]]).

The Contact Centre Systems team breaks this epic into stories after their tech design session.
