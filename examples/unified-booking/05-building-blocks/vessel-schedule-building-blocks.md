---
id: APP-vessel-schedule
type: app-building-blocks
title: Vessel schedule
initiative: INI-002
arc42: "§5"
c4: context
state: fact
change: unchanged
owner: "@harbourline/marine-ops-systems"
authored: authored
sources: [SRC-06]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / Vessel schedule

# Vessel schedule

Vessel schedule knows which sailings run and how much passenger and vehicle space each one has left. The front ends use it to find a crossing, and Booking uses it to check capacity before a hold.

Vessel schedule does not hold seats. Booking holds them and FERRYMASTER records them.

| Change in INI-002 | Owner team |
|---|---|
| Unchanged. Booking becomes a new caller of the existing read API. | Marine Ops Systems team |

```mermaid
flowchart LR
  bk["Booking"]
  web["Public website"]
  cc["Call centre desktop"]
  kio["Port kiosks"]
  vs["<b>Vessel schedule</b><br/>unchanged"]
  bk -->|"CON-004 capacity"| vs
  web -->|"find a crossing"| vs
  cc -->|"find a crossing"| vs
  kio -->|"find a crossing"| vs
  classDef focus fill:#1f4e79,color:#fff
  class vs focus
```

Vessel schedule is a black box on this page. Nothing inside it changes, so its containers belong to the Marine Ops Systems team's own documentation.

## Contracts this app provides

### CON-004 Capacity check

- **Crosses the boundary:** a sailing in; remaining passenger and vehicle capacity out.
- **Consumers:** [[booking-building-blocks|Booking]]
- **Change policy:** the existing read API, no change.
- **Change:** new consumers
- **Tested by:** Booking runs a contract test on its side. Marine Ops Systems adds no test, because the API does not change and Booking's test fails first if it does. Booking's test runs on every Booking build, and a failure blocks the Booking release.
- **State:** fact
- **Source:** SRC-06

## Concerns this team carries

None. [[concern-testing|Testing]] covers CON-004 from Booking's side.
