---
id: context-and-scope
type: initiative-section
title: Context and scope
arc42: "§3"
state: inkling
owner: "@solution-lead"
authored: mixed
---

# Context and scope

## Today

## After

<!-- generated:system-context sha=4a287cad: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

```mermaid
flowchart LR
  subgraph scope["Scheduled jobs"]
    n_APP_jobs_api["Jobs API"]
    n_APP_scheduler["Scheduler"]
  end
  x_platform_event_bus["Platform event bus"]
  x_platform_event_bus -->|"Event bus"| n_APP_jobs_api
  n_APP_scheduler -->|"Job due"| n_APP_jobs_api
  classDef app fill:#eef1f5,stroke:#2448b8,color:#19212d
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  class n_APP_jobs_api,n_APP_scheduler app
  class x_platform_event_bus external
```

Key: blue outline: an app in the initiative · white, dashed: outside this initiative (another company or system) · an arrow is a contract (an agreed interface), labeled with its name, pointing from the side that provides it to the app that uses it.
<!-- /generated:system-context -->

## In scope

## Out of scope
