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

<!-- generated:app-context sha=5d9b057a: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_customer_identity["Customer identity (unchanged)"]
  n_APP_customer_identity -->|"CON-005"| n_APP_booking
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_customer_identity focus
  class n_APP_booking new
```

Key: dark blue: the app this page is about · green: new in this initiative · an arrow is a contract, labelled with its ID.
<!-- /generated:app-context -->

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
