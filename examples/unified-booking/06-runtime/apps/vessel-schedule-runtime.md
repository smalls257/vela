---
id: RUN-vessel-schedule
type: app-runtime
title: Vessel schedule runtime
initiative: INI-002
arc42: "§6"
state: decided
owner: "@harbourline/marine-ops-systems"
authored: authored
sources: [SRC-06]
---

[[README|Harbourline]] / [[06-flows|06 Flows]] / [[vessel-schedule-building-blocks|Vessel schedule]] / Runtime

# Vessel schedule runtime

Vessel schedule is unchanged. In [[FLO-001-hold-pay-confirm|FLO-001]] it answers the front ends' search for a crossing, as today, and Booking's capacity check before a hold. It has no part in FLO-002 or FLO-003.

```mermaid
sequenceDiagram
  participant API as Booking API
  participant VS as Vessel schedule
  API->>VS: capacity for sailing (CON-004)
  VS-->>API: passenger and vehicle space left
```

If Vessel schedule is down, Booking refuses the hold and tells the channel why. Booking does not assume there is space.
