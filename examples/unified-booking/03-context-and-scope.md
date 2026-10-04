---
id: context-and-scope
type: initiative-section
title: Context & scope
initiative: INI-002
arc42: "§3"
c4: context
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-09 Discover", "session 2026-07-14 Shape", "session 2026-08-12 Grill"]
---

# Context & scope

- **Decision:** [[2026-08-12-goals-and-data]]

Systems only. Anything inside a box belongs to that app's own pages under [[05-building-blocks|Building blocks]].

## Today

```mermaid
flowchart LR
  Web[Public website] -- screen-scrape --> FM[(FERRYMASTER)]
  CC[Call centre desktop] -- screen-scrape --> FM
  K[Port kiosks] -- screen-scrape --> FM
  Web -- quote --> P[Pricing]
  CC -- quote --> P
  K -- quote --> P
  Web -- pay --> T[Tidepay]
  K -- pay --> T
```

Three channels, three adapters, three opinions about what a booking's state is. Each channel also calls Pricing on its own.

## After

<!-- generated:system-context sha=ea819ab2: do not edit, run planner render -->
```mermaid
flowchart LR
  subgraph scope["Unified Booking"]
    n_APP_booking["Booking"]
    n_APP_call_centre["Call centre desktop"]
    n_APP_customer_identity["Customer identity"]
    n_APP_ferrymaster["FERRYMASTER"]
    n_APP_kiosks["Port kiosks"]
    n_APP_notifications["Notifications"]
    n_APP_pricing["Pricing"]
    n_APP_vessel_schedule["Vessel schedule"]
    n_APP_website["Public website"]
  end
  x_tidepay__external_["Tidepay (external)"]
  n_APP_booking -->|"CON-001"| n_APP_call_centre
  n_APP_booking -->|"CON-001"| n_APP_kiosks
  n_APP_booking -->|"CON-001"| n_APP_website
  n_APP_booking -->|"CON-002"| n_APP_notifications
  n_APP_pricing -->|"CON-003"| n_APP_booking
  n_APP_vessel_schedule -->|"CON-004"| n_APP_booking
  n_APP_customer_identity -->|"CON-005"| n_APP_booking
  n_APP_ferrymaster -->|"CON-006"| n_APP_booking
  x_tidepay__external_ -->|"CON-007"| n_APP_booking
  classDef app fill:#eef1f5,stroke:#2448b8,color:#19212d
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  class n_APP_booking,n_APP_call_centre,n_APP_customer_identity,n_APP_ferrymaster,n_APP_kiosks,n_APP_notifications,n_APP_pricing,n_APP_vessel_schedule,n_APP_website app
  class x_tidepay__external_ external
```
<!-- /generated:system-context -->

The channels stop knowing FERRYMASTER exists. Booking is the only thing that writes bookings to the ledger, and it tells everyone else what changed through the event bus.

## In scope

Each app page says what changes and which team owns it.

- [[booking-building-blocks|Booking]] · [[booking-runtime|runtime]]
- [[pricing-building-blocks|Pricing]] · [[pricing-runtime|runtime]]
- [[ferrymaster-building-blocks|FERRYMASTER]] · [[ferrymaster-runtime|runtime]]
- [[website-building-blocks|Public website]] · [[website-runtime|runtime]]
- [[call-centre-building-blocks|Call centre desktop]] · [[call-centre-runtime|runtime]]
- [[kiosks-building-blocks|Port kiosks]] · [[kiosks-runtime|runtime]]
- [[notifications-building-blocks|Notifications]] · [[notifications-runtime|runtime]]
- [[vessel-schedule-building-blocks|Vessel schedule]]
- [[customer-identity-building-blocks|Customer identity]]

External: Tidepay (payment provider) and the Harbourline event bus (Platform).

## Out of scope

- **Retiring FERRYMASTER.** That is INI-005 Mainframe Exit. This initiative makes it easier by putting a single door in front of the ledger.
- **The data warehouse feed, the finance reconciliation job and the loyalty scheme.** They keep reading FERRYMASTER directly. Whether finance should read Booking's events instead is [[11-unknowns-and-risks#UNK-006 Finance on Booking events|UNK-006]], deferred to INI-005.
- **Changing how customers search for crossings.** Find a crossing stays as it is.
