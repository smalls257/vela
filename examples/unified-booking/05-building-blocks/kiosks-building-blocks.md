---
id: APP-kiosks
type: app-building-blocks
title: Port kiosks
initiative: INI-002
arc42: "§5"
c4: container
state: decided
change: changed
stage: epics
owner: "@harbourline/port-systems"
authored: mixed
sources: ["Port Systems senior container review", "UNK-004 kiosk authentication 2026-09-23"]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / Port kiosks

# Port kiosks

- **Decision:** [[2026-07-28-solution-strategy]]

Port kiosks let customers at the terminal buy a crossing and check a booking without queueing. They run a locked-down image that changes twice a year, in March and September (CST-3). After this initiative the kiosk app asks Booking for every booking action.

Kiosks no longer decide whether a booking is confirmed and no longer cache FERRYMASTER replies.

| Change in INI-002 | Owner team |
|---|---|
| Changed: Booking API v1 client ships in the March 2027 image. The FM adapter is removed in the September 2027 image. | Port Systems team |

<!-- generated:app-context sha=f0b55cab: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_kiosks["Port kiosks (changed)"]
  n_APP_booking -->|"CON-001"| n_APP_kiosks
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_kiosks focus
  class n_APP_booking new
```
<!-- /generated:app-context -->

## Inside Port kiosks: main containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Kiosk app | Search, hold, pay, confirm and get. Calls Booking API v1 with the kiosk's device certificate. | Uses CON-001 v1 | Port Systems senior | confirmed |
| FM adapter | Talked to FERRYMASTER directly. Switched off 4 weeks after the March 2027 cutover; the code leaves with the September 2027 image. | none | existing | retired |

```mermaid
flowchart LR
  cust["Customer"]
  subgraph kiosk["Port kiosks"]
    app["Kiosk app"]
    fma["FM adapter<br/>retired"]
  end
  gw["Platform gateway"]
  bk["Booking API"]
  vs["Vessel schedule"]
  tp["Tidepay"]
  fm["FERRYMASTER"]
  cust --> app
  app -->|"device certificate"| gw
  gw -->|"CON-001 v1"| bk
  app --> vs
  app --> tp
  app -.->|"rollback switch, 4 weeks"| fma
  fma -.-> fm
```

Components inside these containers belong to the Port Systems team's tech design.

## Contracts this app provides

None. The kiosks only consume.

## Contracts this app consumes

<!-- generated:contracts-consumed sha=730b0a4e: do not edit, run planner render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] | [[booking-building-blocks\|Booking]] | versioned. Each version is kept at least 6 months because kiosks update twice a year ([[ADR-0003-versioned-booking-api\|ADR-0003]]). | decided |
<!-- /generated:contracts-consumed -->

Version 1 must stay available until at least the September 2027 image, and longer if that image slips (R-02, [[ADR-0003-versioned-booking-api|ADR-0003]]).

## Concerns

This app's cell on each concern is in the [[08-concerns|concern matrix]]. The concern pages say what each cell means.

## Epics

<!-- generated:epics-for-app sha=a7b528a3: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-035-kiosks-to-booking\|EPC-035 Kiosks move to Booking in the March image]] | @harbourline/port-systems | decided |
<!-- /generated:epics-for-app -->

Next: [[kiosks-runtime|Port kiosks runtime]]
