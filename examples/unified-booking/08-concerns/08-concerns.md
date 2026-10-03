---
id: concerns
type: index
title: Cross-cutting concerns
initiative: INI-002
arc42: "§8"
state: addressed
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-09-16 Grill", "session 2026-10-07 Grill"]
---

# Cross-cutting concerns

A concern is something every app has to answer for, such as testing or rollback. Each concern has one owner and one page with the strategy. The matrix shows where INI-002 had to decide something.

- **addressed**: INI-002 decided something for this app under this concern. The concern page says what.
- **unchanged**: the app's existing practice still holds. INI-002 checked and changed nothing.
- **N/A**: the concern does not touch this app in INI-002.

All eight concerns are addressed. No cell is open.

<!-- generated: do not edit -->
| Concern | [[booking-building-blocks\|Booking]] | [[pricing-building-blocks\|Pricing]] | [[ferrymaster-building-blocks\|FERRYMASTER]] | [[website-building-blocks\|Website]] | [[call-centre-building-blocks\|Call centre]] | [[kiosks-building-blocks\|Kiosks]] | [[notifications-building-blocks\|Notifications]] | [[vessel-schedule-building-blocks\|Vessel schedule]] | [[customer-identity-building-blocks\|Customer identity]] |
|---|---|---|---|---|---|---|---|---|---|
| [[concern-testing\|Testing]] | addressed | addressed | addressed | addressed | addressed | addressed | addressed | unchanged | unchanged |
| [[concern-security\|Security]] | addressed | addressed | unchanged | addressed | addressed | addressed | unchanged | unchanged | unchanged |
| [[concern-data\|Data]] | addressed | unchanged | addressed | addressed | addressed | addressed | addressed | unchanged | unchanged |
| [[concern-rollout\|Rollout]] | addressed | addressed | N/A | addressed | addressed | addressed | addressed | N/A | N/A |
| [[concern-operations\|Operations]] | addressed | unchanged | addressed | unchanged | addressed | unchanged | addressed | unchanged | unchanged |
| [[concern-observability\|Observability]] | addressed | unchanged | N/A | addressed | addressed | addressed | unchanged | unchanged | unchanged |
| [[concern-ownership\|Ownership]] | addressed | unchanged | unchanged | addressed | addressed | addressed | addressed | unchanged | unchanged |
| [[concern-cost\|Cost]] | addressed | unchanged | addressed | unchanged | unchanged | unchanged | unchanged | unchanged | unchanged |
<!-- /generated -->

## Concern pages

| Concern | Owner |
|---|---|
| [[concern-testing\|Testing]] | QA lead |
| [[concern-security\|Security]] | Platform lead |
| [[concern-data\|Data]] | solution lead |
| [[concern-rollout\|Rollout]] | solution lead |
| [[concern-operations\|Operations]] | Booking senior |
| [[concern-observability\|Observability]] | Booking senior |
| [[concern-ownership\|Ownership]] | solution lead |
| [[concern-cost\|Cost]] | solution lead |
