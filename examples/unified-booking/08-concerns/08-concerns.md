---
id: concerns
type: index
title: Cross-cutting concerns
initiative: INI-002
arc42: "§8"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-09-16 Grill", "session 2026-10-07 Grill"]
---

# Cross-cutting concerns

A concern is something every app has to answer for, such as testing or rollback. Each concern has one owner and one page with the strategy. The matrix shows where INI-002 had to decide something.

- **addressed**: INI-002 decided something for this app under this concern. The concern page says what.
- **unchanged**: the app's existing practice still holds. INI-002 checked and changed nothing.
- **n/a**: the concern does not touch this app in INI-002. The cell says why.
- **unknown**: an open unknown has to be answered first. The cell links it.
- **unexamined**: nobody has looked yet. An app with no cell on a concern page shows as `unexamined (no row)`.

<!-- generated:concern-matrix sha=411ef3bb: do not edit, run planner render -->
| App | [[concern-cost\|Cost]] | [[concern-data\|Data]] | [[concern-observability\|Observability]] | [[concern-operations\|Operations]] | [[concern-ownership\|Ownership]] | [[concern-rollout\|Rollout]] | [[concern-security\|Security]] | [[concern-testing\|Testing]] |
|---|---|---|---|---|---|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | addressed | addressed | addressed | addressed | addressed | addressed | addressed |
| [[call-centre-building-blocks\|Call centre desktop]] | unchanged | addressed | addressed | addressed | addressed | addressed | addressed | addressed |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | unchanged | unchanged | unchanged | unchanged | n/a | unchanged | unchanged |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | addressed | addressed | n/a | addressed | unchanged | n/a | unchanged | addressed |
| [[kiosks-building-blocks\|Port kiosks]] | unchanged | addressed | addressed | unchanged | addressed | addressed | addressed | addressed |
| [[notifications-building-blocks\|Notifications]] | unchanged | addressed | unchanged | addressed | addressed | addressed | unchanged | addressed |
| [[pricing-building-blocks\|Pricing]] | unchanged | unchanged | unchanged | unchanged | unchanged | addressed | addressed | addressed |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | unchanged | unchanged | unchanged | unchanged | n/a | unchanged | unchanged |
| [[website-building-blocks\|Public website]] | unchanged | addressed | addressed | unchanged | addressed | addressed | addressed | addressed |
<!-- /generated:concern-matrix -->

## Concern pages

Each page names its owner.

- [[concern-testing|Testing]]
- [[concern-security|Security]]
- [[concern-data|Data]]
- [[concern-rollout|Rollout]]
- [[concern-operations|Operations]]
- [[concern-observability|Observability]]
- [[concern-ownership|Ownership]]
- [[concern-cost|Cost]]
