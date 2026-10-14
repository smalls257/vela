---
id: EPC-035
type: epic
title: Kiosks move to Booking in the March image
initiative: INI-002
state: decided
owner: "@harborline/port-systems"
authored: mixed
apps: [APP-kiosks, APP-booking]
delivers: [CAP-013, G1, G2]
consumes: [CON-001]
flows: [FLO-001]
depends_on: [EPC-031]
sources: ["session 2026-08-26 Grill", "session 2026-09-23 Grill", "ADR-0003"]
---

# EPC-035 Kiosks move to Booking in the March image

- **Decision:** [[2026-11-18-epics]]

The kiosk app becomes a Booking API v1 client and ships in the March 2027 image. Kiosks run a locked-down image that changes only twice a year, so whatever they call has to stay the same for at least six months.

Still open: nothing.

**Owning team:** Port Systems team.

## Who this is for and what changes

That is why the Booking API is versioned and each version is kept at least 6 months ([[ADR-0003-versioned-booking-api|the versioning decision]]).

Kiosks have no user to log in, so each kiosk authenticates with a device certificate from Platform's existing public key infrastructure (PKI) ([[11-unknowns-and-risks#UNK-004 Kiosk authentication|Kiosk authentication]]). The old FERRYMASTER adapter ships in the March image behind a switch and leaves with the September 2027 image. If the March image slips, kiosks keep their old adapter until September and Booking API v1 is still there when they arrive (the kiosk image slip risk).

## Done when

### Kiosks book through version 1

A kiosk on the March 2027 image holds, confirms and looks up bookings through version 1 of the Booking API with a trace ID it created on every call, and shows the same booking state as every other channel.

- Trace: CON-001  ·  AC1  ·  [observability]

### A kiosk needs a valid certificate

A request from a kiosk without a valid device certificate is refused at the Platform gateway.

- Trace: AC2  ·  [security]

### Version 1 stays for six months

Booking API v1 answers kiosk requests unchanged for at least 6 months after the March 2027 image ships, whatever later versions add.

- Trace: AC3

### The old path can be switched back

Flipping the kiosk switch back sends kiosk bookings through the old FERRYMASTER adapter without a new image.

- Trace: AC4  ·  [rollout]

### Kiosk contract tests are pinned to v1

The kiosks' consumer-driven contract tests are pinned to v1 and pass in Booking's provider verification.

- Trace: AC5  ·  [testing]

### No direct kiosk sessions after September

Once the September 2027 image is rolled out, FERRYMASTER sees no direct sessions from any kiosk.

- Trace: AC6  ·  [data]

## Traces to

<!-- generated:traces-to sha=311354eb: do not edit, run vela render -->
| Traces to | Items |
|---|---|
| Apps | [[kiosks-building-blocks\|Port kiosks]], [[booking-building-blocks\|Booking]] |
| Delivers | [[CAP-013-reserve-a-crossing\|CAP-013 Reserve a crossing]], [[01-goals\|G1]], [[01-goals\|G2]] |
| Consumes | [[booking-building-blocks#CON-001 Booking API\|CON-001 Booking API]] |
| Flows | [[FLO-001-hold-pay-confirm\|FLO-001 Hold, pay, confirm]] |
| Depends on | [[EPC-031-holds-and-confirms\|EPC-031 Booking holds and confirms crossings]] |
| Concerns | [[concern-data\|Data]], [[concern-observability\|Observability]], [[concern-rollout\|Rollout]], [[concern-security\|Security]], [[concern-testing\|Testing]] |
<!-- /generated:traces-to -->

Also related: [[ADR-0003-versioned-booking-api|the versioning decision]], [[11-unknowns-and-risks#UNK-004 Kiosk authentication|Kiosk authentication]].

## Depends on

- [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]]: version 1 of the Booking API must be frozen before the March image is built.

## Rollout notes

Kiosks cut over with the March 2027 image. The switch stays usable until the September 2027 image removes the old adapter, because a locked image cannot drop code after 4 weeks the way the website and call center can.

## Out of scope

- Amend and cancel at the kiosk. In the March 2027 image kiosks show booking state only; customers amend or cancel on the website or through the call center.
- Any change to the kiosk image cycle.

