---
id: EPC-037
type: epic
title: Booking events and customer notifications
initiative: INI-002
state: decided
owner: "@harbourline/booking-team @harbourline/platform-team"
authored: authored
apps: [APP-booking, APP-notifications]
delivers: [CAP-022, CON-002, G2, G3]
consumes: []
flows: [FLO-003, FLO-001, FLO-002]
depends_on: [EPC-031]
sources: ["session 2026-11-03 Grill"]
---

# EPC-037 Booking events and customer notifications

- **Decision:** [[2026-11-18-epics]]

Booking publishes Booking state changed (CON-002) to the Harbourline event bus on every change of state, as the transformation programme requires of new applications (CST-4). Notifications adds a consumer for that event and sends email or SMS through its existing message sender. Today only the website sends emails, so a customer who books at a kiosk or by phone hears nothing, and once customers can amend online they need to hear about it wherever the change came from.

The event bus has been production-ready since 2026-11-01 ([[11-unknowns-and-risks#UNK-005|UNK-005]]). Finance reconciliation may read these events later ([[11-unknowns-and-risks#UNK-006|UNK-006]], deferred to INI-005), so the event only ever grows by adding fields.

**Owning teams:** Booking team (events) and Platform team (Notifications consumer).

## Epic acceptance criteria

1. Every change of booking state (held, confirmed, amended, cancelled, released) produces one Booking state changed event on the bus, carrying the booking reference, the new state and the time of the change.
2. A hold that isn't confirmed within 10 minutes is released, and Booking publishes a state-changed event.
3. A confirmed, amended or cancelled booking produces one message to the customer, by email or SMS as Notifications decides, whichever channel made the change.
4. An event carries the customer ID and no card data or other personal data.
5. A change to the event schema that removes or renames a field fails Booking's pipeline.
6. Once Notifications sends booking messages, the website stops sending its own, so a customer gets one message per change.

## Traces to

- Capabilities: [[CAP-022-notify-customer|CAP-022 Notify customer of changes]]
- Contracts: [[booking-building-blocks#CON-002|CON-002 Booking state changed]]
- Concerns: [[concern-data|Data]], [[concern-testing|Testing]] (schema check, Notifications consumer test)
- Goals: [[01-goals|G2]], [[01-goals|G3]]
- Flows: [[FLO-003-notify-on-change|FLO-003]], [[FLO-001-hold-pay-confirm|FLO-001]], [[FLO-002-amend-or-cancel|FLO-002]]
- Apps: [[booking-building-blocks|Booking]], [[notifications-building-blocks|Notifications]]

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]]: the state changes to publish.

## Rollout notes

Events flow from the first production booking. Notifications takes over a channel's messages when that channel cuts over.

## Out of scope

- Finance reconciliation reading events ([[11-unknowns-and-risks#UNK-006|UNK-006]]).
- Changes to how messages are sent.

The Booking and Platform teams break this epic into stories after their tech design session.
