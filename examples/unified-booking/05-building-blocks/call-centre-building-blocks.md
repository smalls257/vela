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

<!-- generated:app-context sha=054ecdeb: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_call_centre["Call centre desktop (changed)"]
  n_APP_booking -->|"CON-001"| n_APP_call_centre
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_call_centre focus
  class n_APP_booking new
```

Key: dark blue: the app this page is about · green: new in this initiative · an arrow is a contract, labelled with its ID.
<!-- /generated:app-context -->

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


## Contracts this app provides

None. The desktop only consumes.

## Contracts this app consumes

<!-- generated:contracts-consumed sha=730b0a4e: do not edit, run planner render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] | [[booking-building-blocks\|Booking]] | versioned. Each version is kept at least 6 months because kiosks update twice a year ([[ADR-0003-versioned-booking-api\|ADR-0003]]). | decided |
<!-- /generated:contracts-consumed -->

## Epics

<!-- generated:epics-for-app sha=21f098f6: do not edit, run planner render -->
| Epic | Owner | State |
|---|---|---|
| [[EPC-034-call-centre-to-booking\|EPC-034 Call centre moves to Booking]] | @harbourline/contact-centre-systems | decided |
<!-- /generated:epics-for-app -->

Next: [[call-centre-runtime|Call centre desktop runtime]]
