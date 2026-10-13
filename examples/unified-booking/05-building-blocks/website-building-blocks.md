---
id: APP-website
type: app-building-blocks
title: Public website
initiative: INI-002
arc42: "§5"
c4: container
state: decided
change: changed
stage: epics
owner: "@harbourline/digital-team"
authored: mixed
sources: ["Digital senior container review", "rollout plan with solution lead"]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / Public website

# Public website

- **Decision:** [[2026-07-28-solution-strategy]]

The public website is where most customers find a crossing, book it and pay for it. Once this lands it also lets them amend and cancel without phoning, which is goal G3. It asks Booking for every booking action and shows whatever state Booking returns.

The website no longer decides whether a booking is confirmed and no longer talks to FERRYMASTER.

| Change in INI-002 | Owner team |
|---|---|
| Changed: calls the Booking API. The FM screen adapter is retired. | Digital team |

<!-- generated:app-context sha=8d58fc7c: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_website["Public website (changed)"]
  n_APP_booking -->|"CON-001"| n_APP_website
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_website focus
  class n_APP_booking new
```

Key: dark blue: the app this page is about · green: new in this initiative · an arrow is a contract, labelled with its ID.
<!-- /generated:app-context -->

## Inside Public website: main containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Booking pages | Search, hold, pay, confirm, and the new amend and cancel pages. Calls the Booking API for every booking action. | Uses CON-001 | Digital senior | confirmed |
| FM screen adapter | Scraped FERRYMASTER screens to book. Kept behind a switch for 4 weeks after the February 2027 cutover, then removed. | none | existing | retired |

```mermaid
flowchart LR
  cust["Customer"]
  subgraph website["Public website"]
    pages["Booking pages"]
    fma["FM screen adapter<br/>retired"]
  end
  bk["Booking API"]
  vs["Vessel schedule"]
  tp["Tidepay"]
  fm["FERRYMASTER"]
  cust --> pages
  pages -->|"CON-001"| bk
  pages --> vs
  pages --> tp
  pages -.->|"rollback switch, 4 weeks"| fma
  fma -.-> fm
```


## Contracts this app provides

None. The website only consumes.

## Contracts this app consumes

<!-- generated:contracts-consumed sha=730b0a4e: do not edit, run planner render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] | [[booking-building-blocks\|Booking]] | versioned. Each version is kept at least 6 months because kiosks update twice a year ([[ADR-0003-versioned-booking-api\|ADR-0003]]). | decided |
<!-- /generated:contracts-consumed -->

## Epics

<!-- generated:epics-for-app sha=dc376978: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-033-website-to-booking\|EPC-033 Website moves to Booking]] | @harbourline/digital-team | decided |
| [[EPC-036-amend-cancel-online\|EPC-036 Amend and cancel online]] | @harbourline/booking-team @harbourline/digital-team | decided |
<!-- /generated:epics-for-app -->

Next: [[website-runtime|Public website runtime]]
