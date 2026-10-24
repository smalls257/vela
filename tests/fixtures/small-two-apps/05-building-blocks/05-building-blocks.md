---
id: building-blocks
type: index
title: Building blocks
arc42: "§5"
authored: mixed
---

# Building blocks

One page per app: what it does, its main parts, and the contracts (agreed interfaces) it offers other apps. Each contract sits on the page of the app that provides it.

<!-- generated:context-map sha=5b914ac1: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

```mermaid
flowchart LR
  n_APP_jobs_api["Jobs API (new)"]
  n_APP_scheduler["Scheduler (new)"]
  x_platform_event_bus["Platform event bus"]
  x_platform_event_bus -->|"Event bus"| n_APP_jobs_api
  n_APP_scheduler -->|"Job due"| n_APP_jobs_api
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class x_platform_event_bus external
  class n_APP_jobs_api,n_APP_scheduler new
```

Key: green: new in this initiative · white, dashed: outside this initiative (another company or system) · an arrow is a contract (an agreed interface), labeled with its name, pointing from the side that provides it to the app that uses it.
<!-- /generated:context-map -->
