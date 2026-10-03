---
id: epics
type: index
title: Epics
initiative: INI-002
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-10-21 Shape", "session 2026-11-18 Grill"]
---

# Epics

Nine epics deliver Unified Booking. Each one names its owning team. The solution lead wrote every epic down to its acceptance criteria; the teams write the stories after their own tech design sessions.

Booking's own epics come first because every channel cutover needs a working Booking API and ledger writes. The channels then move in the order the rollout concern sets: website in February 2027, call centre in March 2027, kiosks with the March 2027 image. Pricing closes the gateway to other callers last, once no front end calls it directly.

<!-- generated: do not edit -->
| ID | Epic | Owning team | Jira | Capabilities | Contracts | Depends on |
|---|---|---|---|---|---|---|
| [[EPC-031-holds-and-confirms\|EPC-031]] | Booking holds and confirms crossings | Booking | HB-101 | [[CAP-013-reserve-a-crossing\|CAP-013]], [[CAP-014-hold-a-seat\|CAP-014]] | [[booking-building-blocks#CON-001\|CON-001]], [[booking-building-blocks#CON-007\|CON-007]] | EPC-032 |
| [[EPC-032-ledger-adapter\|EPC-032]] | Ledger adapter on FERRYMASTER's MQ transactions | Booking (+ mainframe team support) | HB-102 | none | [[ferrymaster-building-blocks#CON-006\|CON-006]] | none |
| [[EPC-033-website-to-booking\|EPC-033]] | Website moves to Booking | Digital | HB-103 | [[CAP-013-reserve-a-crossing\|CAP-013]] | [[booking-building-blocks#CON-001\|CON-001]] (client) | EPC-031, EPC-032, EPC-039 |
| [[EPC-034-call-centre-to-booking\|EPC-034]] | Call centre moves to Booking | Contact Centre Systems | HB-104 | [[CAP-013-reserve-a-crossing\|CAP-013]], [[CAP-021-amend-or-cancel\|CAP-021]], [[CAP-023-fix-failed-bookings\|CAP-023]] | [[booking-building-blocks#CON-001\|CON-001]] (client) | EPC-031, EPC-036 |
| [[EPC-035-kiosks-to-booking\|EPC-035]] | Kiosks move to Booking in the March image | Port Systems | HB-105 | [[CAP-013-reserve-a-crossing\|CAP-013]] | [[booking-building-blocks#CON-001\|CON-001]] v1 (client) | EPC-031 |
| [[EPC-036-amend-cancel-online\|EPC-036]] | Amend and cancel online | Booking + Digital | HB-106 | [[CAP-021-amend-or-cancel\|CAP-021]] | [[booking-building-blocks#CON-001\|CON-001]] | EPC-031, EPC-032, EPC-033 |
| [[EPC-037-events-and-notifications\|EPC-037]] | Booking events and customer notifications | Booking + Platform | HB-107 | [[CAP-022-notify-customer\|CAP-022]] | [[booking-building-blocks#CON-002\|CON-002]] | EPC-031 |
| [[EPC-038-pricing-serves-booking\|EPC-038]] | Pricing serves Booking only | Revenue | HB-108 | [[CAP-012-quote-a-fare\|CAP-012]] | [[pricing-building-blocks#CON-003\|CON-003]] | EPC-031, EPC-033, EPC-034, EPC-035 |
| [[EPC-039-run-booking\|EPC-039]] | Run Booking: on-call, runbooks, dashboards | Booking | HB-109 | none | none | EPC-031, EPC-032 |
<!-- /generated -->

## Traceability check

<!-- generated: do not edit -->
**Result: all green.** Every capability-delta row, every new or changed contract and every concern with work lands in at least one epic. No epic traces to nothing.

| Check | Item | Delivered by | Status |
|---|---|---|---|
| Capability delta | [[CAP-012-quote-a-fare\|CAP-012]] narrow | EPC-038 | pass |
| Capability delta | [[CAP-013-reserve-a-crossing\|CAP-013]] replace | EPC-031, EPC-033, EPC-034, EPC-035 | pass |
| Capability delta | [[CAP-014-hold-a-seat\|CAP-014]] new | EPC-031 | pass |
| Capability delta | [[CAP-021-amend-or-cancel\|CAP-021]] extend | EPC-034, EPC-036 | pass |
| Capability delta | [[CAP-022-notify-customer\|CAP-022]] new | EPC-037 | pass |
| Capability delta | [[CAP-023-fix-failed-bookings\|CAP-023]] retire | EPC-034 | pass |
| Contract | [[booking-building-blocks#CON-001\|CON-001]] new | EPC-031, EPC-036 (provider); EPC-033, EPC-034, EPC-035 (clients) | pass |
| Contract | [[booking-building-blocks#CON-002\|CON-002]] new | EPC-037 | pass |
| Contract | [[pricing-building-blocks#CON-003\|CON-003]] changed | EPC-038 | pass |
| Contract | [[ferrymaster-building-blocks#CON-006\|CON-006]] new use | EPC-032 | pass |
| Contract | [[booking-building-blocks#CON-007\|CON-007]] new use | EPC-031 | pass |
| Concern | [[concern-testing\|Testing]] | EPC-031, EPC-032, EPC-033, EPC-034, EPC-035, EPC-036, EPC-037, EPC-038 | pass |
| Concern | [[concern-security\|Security]] | EPC-031, EPC-035, EPC-038 | pass |
| Concern | [[concern-data\|Data]] | EPC-031, EPC-037 | pass |
| Concern | [[concern-rollout\|Rollout]] | EPC-033, EPC-034, EPC-035 | pass |
| Concern | [[concern-operations\|Operations]] | EPC-039 | pass |
| Concern | [[concern-observability\|Observability]] | EPC-039 | pass |
| Concern | [[concern-ownership\|Ownership]] | no work: recorded as each epic's owning team | n/a |
| Concern | [[concern-cost\|Cost]] | no work: standard footprint, MQ within MIPS budget | n/a |
| Orphan epics | EPC-031 to EPC-039 | each traces to at least one capability, contract or concern | pass |
<!-- /generated -->

## Sequencing

```mermaid
flowchart LR
  E032[EPC-032 Ledger adapter] --> E031[EPC-031 Holds and confirms]
  E032 --> E039[EPC-039 Run Booking]
  E031 --> E039
  E039 --> E033[EPC-033 Website, Feb 2027]
  E031 --> E033
  E033 --> E036[EPC-036 Amend and cancel online]
  E036 --> E034[EPC-034 Call centre, Mar 2027]
  E031 --> E035[EPC-035 Kiosks, March image]
  E031 --> E037[EPC-037 Events and notifications]
  E033 --> E038[EPC-038 Pricing serves Booking]
  E034 --> E038
  E035 --> E038
```
