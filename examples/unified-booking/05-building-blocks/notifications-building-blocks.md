---
id: APP-notifications
type: app-building-blocks
title: Notifications
initiative: INI-002
arc42: "§5"
c4: container
state: decided
change: changed
owner: "@harborline/platform-team"
authored: mixed
sources: ["Platform lead review of CON-002", "UNK-005 event bus readiness 2026-11-03"]
---

[[README|Harborline]] / [[05-building-blocks|05 Building blocks]] / Notifications

# Notifications

- **Decision:** [[2026-07-28-solution-strategy]]

Notifications tells customers when their booking changes, by email or SMS. Today only the website sends booking emails. After this initiative Notifications reads every Booking state change from the event bus, so a booking made or changed in any channel produces the same message.

Notifications does not decide what state a booking is in. It reports what Booking published.

| Change in INI-002 | Owner team |
|---|---|
| Changed: a new Booking event consumer. The existing email and SMS sender is reused. | Platform team |

<!-- generated:app-context sha=8966e2a0: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

```mermaid
flowchart LR
  n_APP_booking["Booking (new)"]
  n_APP_notifications["Notifications (changed)"]
  n_APP_booking -->|"Booking state changed"| n_APP_notifications
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_notifications focus
  class n_APP_booking new
```

Key: dark blue: the app this page is about · green: new in this initiative · an arrow is a contract (an agreed interface), labeled with its name, pointing from the side that provides it to the app that uses it.
<!-- /generated:app-context -->

## Inside Notifications: main containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Booking event consumer | Reads Booking state changed, picks email or SMS, and hands the message to the sender. | Uses CON-002 | Platform lead | confirmed |
| Message sender | Sends email and SMS. Looks up the customer's address and mobile number from the customer ID, as it does for website emails today. | none | existing | unchanged |

```mermaid
flowchart LR
  bus["Harborline event bus"]
  subgraph notif["Notifications"]
    cons["Booking event consumer<br/>new"]
    send["Message sender<br/>existing"]
  end
  cust["Customer"]
  bus -->|"CON-002"| cons
  cons --> send
  send -->|"email, SMS"| cust
```


## Contracts this app provides

None. Notifications only consumes.

## Contracts this app consumes

<!-- generated:contracts-consumed sha=cc076497: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

| Contract | Provided by | Who can change it, and how | How sure |
|---|---|---|---|
| [[booking-building-blocks#CON-002 Booking state changed\|Booking state changed (CON-002)]] | [[booking-building-blocks\|Booking]] | additive changes only. | decided |
<!-- /generated:contracts-consumed -->

## Epics

<!-- generated:epics-for-app sha=24b6ba43: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

| Epic | Owner | State |
|---|---|---|
| [[EPC-037-events-and-notifications\|EPC-037 Booking events and customer notifications]] | @harborline/booking-team @harborline/platform-team | decided |
<!-- /generated:epics-for-app -->

Next: [[notifications-runtime|Notifications runtime]]
