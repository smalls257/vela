---
id: APP-notifications
type: app-building-blocks
title: Notifications
initiative: INI-002
arc42: "§5"
c4: container
state: decided
change: changed
stage: epics
owner: "@harbourline/platform-team"
authored: mixed
sources: ["Platform lead review of CON-002", "UNK-005 event bus readiness 2026-11-03"]
---

[[README|Harbourline]] / [[05-building-blocks|05 Building blocks]] / Notifications

# Notifications

- **Decision:** [[2026-07-28-solution-strategy]]

Notifications tells customers when their booking changes, by email or SMS. Today only the website sends booking emails. After this initiative Notifications reads every Booking state change from the event bus, so a booking made or changed in any channel produces the same message.

Notifications does not decide a booking's state. It reports what Booking published.

| Change in INI-002 | Owner team |
|---|---|
| Changed: a new Booking event consumer. The existing email and SMS sender is reused. | Platform team |

```mermaid
flowchart LR
  bk["Booking"]
  bus["Harbourline event bus"]
  nt["<b>Notifications</b><br/>changed"]
  cust["Customer<br/>email or SMS"]
  bk -->|"CON-002"| bus
  bus -->|"CON-002"| nt
  nt --> cust
  classDef focus fill:#1f4e79,color:#fff
  class nt focus
```

## Inside Notifications: main containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Booking event consumer | Reads Booking state changed, picks email or SMS, and hands the message to the sender. | Uses CON-002 | Platform lead | confirmed |
| Message sender | Sends email and SMS. Looks up the customer's address and mobile number from the customer ID, as it does for website emails today. | none | existing | unchanged |

```mermaid
flowchart LR
  bus["Harbourline event bus"]
  subgraph notif["Notifications"]
    cons["Booking event consumer<br/>new"]
    send["Message sender<br/>existing"]
  end
  cust["Customer"]
  bus -->|"CON-002"| cons
  cons --> send
  send -->|"email, SMS"| cust
```

Components inside these containers belong to the Platform team's tech design.

## Contracts this app provides

None. Notifications only consumes.

## Contracts this app consumes

<!-- generated: do not edit -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[booking-building-blocks#CON-002 Booking state changed\|CON-002 Booking state changed]] | Booking | Additive changes only | decided |
<!-- /generated -->

## Concerns this team carries

- [[concern-testing|Testing]]: the consumer test for CON-002 runs in Notifications' pipeline.
- [[concern-operations|Operations]]: Booking joins the Platform team's on-call rota, so the same people answer for Booking and Notifications.

## Epics

<!-- generated: do not edit -->
- [[EPC-037-events-and-notifications|EPC-037 Booking events and customer notifications]] (HB-107)
<!-- /generated -->

Next: [[notifications-runtime|Notifications runtime]]
