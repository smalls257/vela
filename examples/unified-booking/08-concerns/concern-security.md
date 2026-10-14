---
id: concern-security
type: concern
title: Security
initiative: INI-002
arc42: "§8"
owner: "@hl-platform-lead"
authored: mixed
sources: ["session 2026-09-23 Grill", SRC-08]
---

# Security


## Strategy

Payment Card Industry (PCI) scope must not grow. Card details go from the customer's browser or the agent's screen straight to Tidepay's hosted payment page. Booking only receives the payment outcome through [[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]], and that carries a payment ID and a result. Card data never reaches Booking, so Booking stays out of PCI scope.

The Booking API sits behind the Platform gateway. The website and call center desktop call it with Platform service tokens, as other Harborline services already do. Kiosks have no logged-in user and no safe place for a shared secret on a locked image ([[11-unknowns-and-risks#UNK-004 Kiosk authentication|Kiosk authentication]]). Each kiosk gets a device certificate from Platform's existing public key infrastructure (PKI), installed with the March 2027 image. A stolen kiosk is revoked by certificate without touching the others.

The gateway also restricts Pricing's Quote service to Booking. Before this initiative, three front ends could quote fares directly. Narrowing that to one caller removes two paths nobody needed to keep open.

## Per app

| App | State | What changes |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Booking API behind the Platform gateway. Verifies service tokens and kiosk certificates. No card data. |
| [[pricing-building-blocks\|Pricing]] | addressed | Quote service reachable by Booking only, enforced at the gateway rule set up with the Platform lead |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | unchanged | Existing MQ channel security. Ledger adapter is the only Booking component with MQ access. |
| [[website-building-blocks\|Website]] | addressed | Calls Booking with a service token. Tidepay hosted page as today. |
| [[call-center-building-blocks\|Call center]] | addressed | Desktop client calls Booking with a service token. Agents keep their existing sign-in. |
| [[kiosks-building-blocks\|Kiosks]] | addressed | Device certificate per kiosk from Platform PKI, in the March 2027 image, because a kiosk has no user to log in ([[11-unknowns-and-risks#UNK-004 Kiosk authentication\|UNK-004]]) |
| [[notifications-building-blocks\|Notifications]] | unchanged | Subscribes to the event bus with existing Platform credentials |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | Existing read API access |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | Existing read API access |

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-004 Kiosk authentication|Kiosk authentication]]
- Decisions: [[ADR-0001-one-booking-context|the one-application decision]], [[ADR-0003-versioned-booking-api|the versioning decision]]
- Epics: [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]], [[EPC-035-kiosks-to-booking|Kiosks move to Booking in the March image]], [[EPC-038-pricing-serves-booking|Pricing serves Booking only]]
