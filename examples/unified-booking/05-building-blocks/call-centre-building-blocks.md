---
id: APP-call-centre
type: app-building-blocks
title: Call centre desktop
initiative: INI-002
arc42: "§5"
c4: container
state: decided
change: changed
stage: epics
owner: "@harbourline/contact-centre-systems"
authored: mixed
sources: ["Contact Centre Systems senior container review", "Head of Contact Centre review of retired fix screens"]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / Call centre desktop

# Call centre desktop

- **Decision:** [[2026-07-28-solution-strategy]]

The call centre desktop is what agents use to book, amend and cancel crossings for customers who phone. Today it reaches FERRYMASTER through a terminal adapter, and agents spend the morning fixing bookings that were paid for on the website but never confirmed. After this initiative the desktop asks Booking for every booking action, and that morning queue goes away.

The desktop no longer decides whether a booking is confirmed and no longer caches FERRYMASTER replies.

| Change in INI-002 | Owner team |
|---|---|
| Changed: Booking API client and new amend and cancel screens. Terminal adapter and manual fix queue retired. | Contact Centre Systems team |

```mermaid
flowchart LR
  agent["Call centre agent"]
  cc["<b>Call centre desktop</b><br/>changed"]
  bk["Booking"]
  vs["Vessel schedule"]
  tp["Tidepay"]
  fm["FERRYMASTER"]
  pr["Pricing"]
  agent --> cc
  cc -->|"CON-001"| bk
  cc -->|"find a crossing"| vs
  cc -->|"take payment, as today"| tp
  cc -.->|"terminal adapter, retired"| fm
  cc -.->|"direct quote, retired"| pr
  classDef focus fill:#1f4e79,color:#fff
  class cc focus
```

## Inside Call centre desktop: main containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Desktop client | Agent screens. Calls the Booking API for hold, confirm, amend, cancel and get. New amend and cancel screens. | Uses CON-001 | Contact Centre Systems senior | confirmed |
| Terminal adapter | Drove FERRYMASTER's terminal screens. Kept behind a switch for 4 weeks after the March 2027 cutover, then removed. | none | existing | retired |
| Manual fix queue | Listed paid but unconfirmed website bookings for next-morning fixes. Booking now retries and keeps the hold, so nothing lands here. | none | existing | retired |

```mermaid
flowchart LR
  agent["Agent"]
  subgraph desk["Call centre desktop"]
    client["Desktop client"]
    term["Terminal adapter<br/>retired"]
    fix["Manual fix queue<br/>retired"]
  end
  bk["Booking API"]
  vs["Vessel schedule"]
  tp["Tidepay"]
  fm["FERRYMASTER"]
  agent --> client
  client -->|"CON-001"| bk
  client --> vs
  client --> tp
  client -.->|"rollback switch, 4 weeks"| term
  term -.-> fm
```

Components inside these containers belong to the Contact Centre Systems team's tech design.

## Contracts this app provides

None. The desktop only consumes.

## Contracts this app consumes

<!-- generated: do not edit -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] | Booking | Versioned; each version kept at least 6 months | decided |
<!-- /generated -->

## Concerns this team carries

- [[concern-testing|Testing]]: the desktop's consumer-driven contract tests for CON-001 run in its own pipeline.
- [[concern-rollout|Rollout]]: the call centre cuts over second, in March 2027. Rollback is flipping its switch back to the terminal adapter during the 4 weeks before removal.

## Epics

<!-- generated: do not edit -->
- [[EPC-034-call-centre-to-booking|EPC-034 Call centre moves to Booking]] (HB-104)
<!-- /generated -->

Next: [[call-centre-runtime|Call centre desktop runtime]]
