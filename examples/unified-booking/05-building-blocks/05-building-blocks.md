---
id: building-blocks
type: index
title: Building blocks
initiative: INI-002
arc42: "§5"
c4: context
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-28 Shape", "session 2026-09-09 Grill", "co-design sessions with each app's senior, 2026-09 to 2026-10"]
---

# Building blocks

Each application in scope has two pages: its building blocks and contracts (§5), and its runtime (§6). New and changed apps go one level in and show their main containers, co-designed with that app's senior. Components are never described here; they belong to each team's tech design.

## Who owns what, and how they relate

<!-- generated:context-map sha=3b5200eb: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_call_centre["Call centre desktop (changed)"]
  n_APP_customer_identity["Customer identity (unchanged)"]
  n_APP_ferrymaster["FERRYMASTER (integrated)"]
  n_APP_kiosks["Port kiosks (changed)"]
  n_APP_notifications["Notifications (changed)"]
  n_APP_pricing["Pricing (changed)"]
  n_APP_vessel_schedule["Vessel schedule (unchanged)"]
  n_APP_website["Public website (changed)"]
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
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  classDef unchanged fill:#eef1f5,stroke:#7a8494,color:#19212d
  class n_APP_call_centre,n_APP_kiosks,n_APP_notifications,n_APP_pricing,n_APP_website changed
  class x_tidepay__external_ external
  class n_APP_booking new
  class n_APP_customer_identity,n_APP_ferrymaster,n_APP_vessel_schedule unchanged
```

Key: green: new in this initiative · amber: changed by this initiative · grey: stays as it is · white, dashed: outside the initiative (a party or provider) · an arrow is a contract, labelled with its ID.
<!-- /generated:context-map -->

Each arrow is a contract, drawn from its provider to each consumer. Each contract lives on the provider's page.

How the apps relate, by contract:

- The Booking API: the website, the call centre desktop and the kiosks are customers of Booking.
- The Booking state changed event: Booking publishes events that Notifications reads.
- The fare quote: Booking is a customer of Pricing.
- The capacity check and the customer lookup: Booking conforms to the vessel schedule and to customer identity.
- The ledger transactions: Booking puts an anticorruption layer in front of FERRYMASTER, and Booking owns that layer.
- The Tidepay payment outcome: Tidepay sends payment outcomes to Booking.

## Apps

- [[booking-building-blocks|Booking]] · [[booking-runtime|runtime]]
- [[pricing-building-blocks|Pricing]] · [[pricing-runtime|runtime]]
- [[ferrymaster-building-blocks|FERRYMASTER]] · [[ferrymaster-runtime|runtime]]
- [[website-building-blocks|Public website]] · [[website-runtime|runtime]]
- [[call-centre-building-blocks|Call centre desktop]] · [[call-centre-runtime|runtime]]
- [[kiosks-building-blocks|Port kiosks]] · [[kiosks-runtime|runtime]]
- [[notifications-building-blocks|Notifications]] · [[notifications-runtime|runtime]]
- [[vessel-schedule-building-blocks|Vessel schedule]]
- [[customer-identity-building-blocks|Customer identity]]

## All contracts

- [[booking-building-blocks#CON-001 Booking API|CON-001 Booking API]]
- [[booking-building-blocks#CON-002 Booking state changed|CON-002 Booking state changed]]
- [[pricing-building-blocks#CON-003 Quote a fare|CON-003 Quote a fare]]
- [[vessel-schedule-building-blocks#CON-004 Capacity check|CON-004 Capacity check]]
- [[customer-identity-building-blocks#CON-005 Customer lookup|CON-005 Customer lookup]]
- [[ferrymaster-building-blocks#CON-006 Ledger transactions|CON-006 Ledger transactions]]
- [[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007 Tidepay payment outcome]]
