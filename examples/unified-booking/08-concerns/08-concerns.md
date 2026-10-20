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

A concern is something every app has to answer for, such as testing or rollback. Each concern has one owner and one page with the strategy. The matrix shows where this initiative had to decide something.

- **addressed**: this initiative decided something for this app under this concern. The concern page says what.
- **unchanged**: the app's existing practice still holds. this initiative checked and changed nothing.
- **n/a**: the concern does not touch this app in this initiative. The cell says why.
- **unknown**: an open unknown has to be answered first. The cell links it.
- **unexamined**: nobody has looked yet. An app with no cell on a concern page shows as `unexamined (no row)`.

<!-- generated:concern-matrix sha=1cb28fd7: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

| App | [[concern-cost\|Cost]] | [[concern-data\|Data]] | [[concern-observability\|Observability]] | [[concern-operations\|Operations]] | [[concern-ownership\|Ownership]] | [[concern-rollout\|Rollout]] | [[concern-security\|Security]] | [[concern-testing\|Testing]] |
|---|---|---|---|---|---|---|---|---|
| [[booking-building-blocks\|Booking]] | covered | covered | covered | covered | covered | covered | covered | covered |
| [[call-center-building-blocks\|Call center desktop]] | unchanged | covered | covered | covered | covered | covered | covered | covered |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | unchanged | unchanged | unchanged | unchanged | doesn't apply | unchanged | unchanged |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | covered | covered | doesn't apply | covered | unchanged | doesn't apply | unchanged | covered |
| [[kiosks-building-blocks\|Port kiosks]] | unchanged | covered | covered | unchanged | covered | covered | covered | covered |
| [[notifications-building-blocks\|Notifications]] | unchanged | covered | unchanged | covered | covered | covered | unchanged | covered |
| [[pricing-building-blocks\|Pricing]] | unchanged | unchanged | unchanged | unchanged | unchanged | covered | covered | covered |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | unchanged | unchanged | unchanged | unchanged | doesn't apply | unchanged | unchanged |
| [[website-building-blocks\|Public website]] | unchanged | covered | covered | unchanged | covered | covered | covered | covered |
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
