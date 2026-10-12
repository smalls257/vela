---
id: EPC-037
type: epic
title: Booking events and customer notifications
initiative: INI-002
state: decided
owner: "@harbourline/booking-team @harbourline/platform-team"
authored: mixed
apps: [APP-booking, APP-notifications]
delivers: [CAP-022, CON-002, G2, G3]
consumes: []
flows: [FLO-003, FLO-001, FLO-002]
depends_on: [EPC-031]
sources: ["session 2026-11-03 Grill"]
---

# EPC-037 Booking events and customer notifications

- **Decision:** [[2026-11-18-epics]]

Booking publishes the Booking state changed event to the Harbourline event bus on every change of state, as the transformation programme requires of new applications. Notifications adds a consumer for that event and sends email or SMS through its existing message sender.

Still open: whether Finance reads these events later, which is deferred to the Mainframe Exit initiative and blocks nothing here.

**Owning teams:** Booking team (events) and Platform team (Notifications consumer).

## Who this is for and what changes

Today only the website sends emails, so a customer who books at a kiosk or by phone hears nothing, and once customers can amend online they need to hear about it wherever the change came from.

The event bus has been production-ready since 2026-11-01 ([[11-unknowns-and-risks#UNK-005 Event bus readiness|Event bus readiness]]). Finance reconciliation may read these events later ([[11-unknowns-and-risks#UNK-006 Finance on Booking events|Finance on Booking events]], deferred to the Mainframe Exit initiative), so the event only ever grows by adding fields.

## Done when

### Every state change publishes one event

Every change of booking state (held, confirmed, amended, cancelled, released) produces one Booking state changed event on the bus, carrying the booking reference, the new state and the time of the change.

- Trace: AC1

### An unconfirmed hold is released

A hold that isn't confirmed within 10 minutes is released, and Booking publishes a state-changed event.

- Trace: AC2

### One message to the customer for each change

A confirmed, amended or cancelled booking produces one message to the customer, by email or SMS as Notifications decides, whichever channel made the change.

- Trace: AC3

### The event carries no card data

An event carries the customer ID and no card data or other personal data.

- Trace: AC4

### A schema break fails the pipeline

A change to the event schema that removes or renames a field fails Booking's pipeline, and the Notifications consumer test for the event runs in Notifications' pipeline.

- Trace: CON-002  ·  AC5  ·  [testing]

### The website stops sending its own messages

Once Notifications sends booking messages, the website stops sending its own, so a customer gets one message per change.

- Trace: AC6  ·  [data]

### A paused consumer loses nothing

Pausing the Notifications consumer leaves events waiting on the bus, and each one is sent once the consumer starts again.

- Trace: AC7  ·  [rollout]

## Traces to

<!-- generated:traces-to sha=d54b1193: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[booking-building-blocks\|Booking]], [[notifications-building-blocks\|Notifications]] |
| Delivers | [[CAP-022-notify-customer\|CAP-022 Notify customer of changes]], [[booking-building-blocks#CON-002 Booking state changed\|CON-002 Booking state changed]], [[01-goals\|G2]], [[01-goals\|G3]] |
| Consumes | none |
| Flows | [[FLO-003-notify-on-change\|FLO-003 Notify on change]], [[FLO-001-hold-pay-confirm\|FLO-001 Hold, pay, confirm]], [[FLO-002-amend-or-cancel\|FLO-002 Amend or cancel]] |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]] |
| Concerns | [[concern-data\|Data]], [[concern-rollout\|Rollout]], [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]]: the state changes to publish.

## Rollout notes

Events flow from the first production booking. Notifications takes over a channel's messages when that channel cuts over.

## Out of scope

- Finance reconciliation reading events ([[11-unknowns-and-risks#UNK-006 Finance on Booking events|Finance on Booking events]]).
- Changes to how messages are sent.

