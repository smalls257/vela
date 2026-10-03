---
id: EPC-035
type: epic
title: Kiosks move to Booking in the March image
initiative: INI-002
state: decided
owner: "@harbourline/port-systems"
authored: authored
apps: [APP-kiosks, APP-booking]
delivers: [CAP-013, G1, G2]
consumes: [CON-001]
flows: [FLO-001]
depends_on: [EPC-031]
sources: ["session 2026-08-26 Grill", "session 2026-09-23 Grill", "ADR-0003"]
---

# EPC-035 Kiosks move to Booking in the March image

- **Decision:** [[2026-11-18-epics]]

The kiosk app becomes a Booking API v1 client and ships in the March 2027 image. Kiosks run a locked-down image that changes only in March and September (CST-3), so whatever they call has to stay the same for at least six months. That is why the Booking API is versioned and each version is kept at least 6 months ([[ADR-0003-versioned-booking-api|ADR-0003]]).

Kiosks have no user to log in, so each kiosk authenticates with a device certificate from Platform's existing PKI ([[11-unknowns-and-risks#UNK-004 Kiosk authentication|UNK-004]]). The old FM adapter ships in the March image behind a switch and leaves with the September 2027 image. If the March image slips, kiosks keep their old adapter until September and Booking API v1 is still there when they arrive (R-02).

**Owning team:** Port Systems team.

## Epic acceptance criteria

1. A kiosk on the March 2027 image holds, confirms and looks up bookings through CON-001 v1 with a trace ID it created on every call, and shows the same booking state as every other channel. [observability]
2. A request from a kiosk without a valid device certificate is refused at the Platform gateway. [security]
3. Booking API v1 answers kiosk requests unchanged for at least 6 months after the March 2027 image ships, whatever later versions add.
4. Flipping the kiosk switch back sends kiosk bookings through the old FM adapter without a new image. [rollout]
5. The kiosks' consumer-driven contract tests are pinned to v1 and pass in Booking's provider verification. [testing]
6. Once the September 2027 image is rolled out, FERRYMASTER sees no direct sessions from any kiosk. [data]

## Traces to

- Capabilities: [[CAP-013-reserve-a-crossing|CAP-013 Reserve a crossing]] (kiosks)
- Contracts: [[booking-building-blocks#CON-001 Booking API|CON-001 Booking API]] v1 (client)
- Decisions: [[ADR-0003-versioned-booking-api|ADR-0003]]
- Concerns: [[concern-security|Security]] (device certificates), [[concern-rollout|Rollout]], [[concern-testing|Testing]]
- Goals: [[01-goals|G1]], [[01-goals|G2]]
- Unknowns: [[11-unknowns-and-risks#UNK-004 Kiosk authentication|UNK-004]]
- Apps: [[kiosks-building-blocks|Port kiosks]], [[booking-building-blocks|Booking]]

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]]: CON-001 v1 must be frozen before the March image is built.

## Rollout notes

Kiosks cut over with the March 2027 image. The switch stays usable until the September 2027 image removes the old adapter, because a locked image cannot drop code after 4 weeks the way the website and call centre can.

## Out of scope

- Amend and cancel at the kiosk. In the March 2027 image kiosks show booking state only; customers amend or cancel on the website or through the call centre.
- Any change to the kiosk image cycle.

The Port Systems team breaks this epic into stories after their tech design session.
