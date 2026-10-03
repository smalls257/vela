---
id: APP-customer-identity
type: app-building-blocks
title: Customer identity
initiative: INI-002
arc42: "§5"
c4: context
state: fact
change: unchanged
owner: "@harbourline/platform-team"
authored: mixed
sources: [SRC-07]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / Customer identity

# Customer identity

Customer identity holds Harbourline's customer records and answers who a customer is. Booking looks the customer up when it places a hold and keeps only the customer ID.

Customer identity does not know about bookings. Booking holds the link from booking reference to customer ID.

| Change in INI-002 | Owner team |
|---|---|
| Unchanged. Booking becomes a new caller of the existing read API. | Platform team |

```mermaid
flowchart LR
  bk["Booking"]
  ci["<b>Customer identity</b><br/>unchanged"]
  bk -->|"CON-005 lookup"| ci
  classDef focus fill:#1f4e79,color:#fff
  class ci focus
```

Customer identity is a black box on this page. Nothing inside it changes, so its containers belong to the Platform team's own documentation.

## Contracts this app provides

### CON-005 Customer lookup

- **Crosses the boundary:** a customer ID in; the customer record out. Booking stores only the ID ([[concern-data|Data]]).
- **Consumers:** [[booking-building-blocks|Booking]]
- **Change policy:** the existing read API, no change.
- **Change:** new consumers
- **Tested by:** Booking runs a contract test on its side. The Platform team adds no test, because the API does not change and Booking's test fails first if it does. Booking's test runs on every Booking build, and a failure blocks the Booking release.
- **State:** fact
- **Source:** SRC-07

## Contracts this app consumes

<!-- generated: do not edit -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| none | | | |
<!-- /generated -->

## Concerns this team carries

None for this app. The Platform lead owns [[concern-security|Security]], and that work sits at the Platform gateway and in Booking.

## Epics

<!-- generated: do not edit -->
- none
<!-- /generated -->

Next: [[customer-identity-runtime|Customer identity runtime]]
