---
id: concern-security
type: concern
title: Security
initiative: INI-002
arc42: "§8"
state: addressed
owner: Platform lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-09-23 Grill", "Platform PKI runbook"]
---

# Security

**State:** addressed. **Owner:** Platform lead.

## Strategy

PCI scope must not grow (C2). Card details go from the customer's browser or the agent's screen straight to Tidepay's hosted payment page. Booking only receives the payment outcome through [[booking-building-blocks#CON-007|CON-007]], and that carries a payment ID and a result. Card data never reaches Booking, so Booking stays out of PCI scope.

The Booking API sits behind the Platform gateway. The website and call centre desktop call it with Platform service tokens, as other Harbourline services already do. Kiosks have no logged-in user and no safe place for a shared secret on a locked image ([[11-unknowns-and-risks#UNK-004|UNK-004]]). Each kiosk gets a device certificate from Platform's existing PKI, installed with the March 2027 image. A stolen kiosk is revoked by certificate without touching the others.

The gateway also restricts Pricing's Quote service to Booking. Before INI-002, three front ends could quote fares directly. Narrowing that to one caller removes two paths nobody needed to keep open.

## Per app

<!-- generated: do not edit -->
| App | State | What changes |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Booking API behind the Platform gateway. Verifies service tokens and kiosk certificates. No card data. |
| [[pricing-building-blocks\|Pricing]] | addressed | Quote service reachable by Booking only, enforced at the gateway |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | unchanged | Existing MQ channel security. Ledger adapter is the only Booking component with MQ access. |
| [[website-building-blocks\|Website]] | addressed | Calls Booking with a service token. Tidepay hosted page as today. |
| [[call-centre-building-blocks\|Call centre]] | addressed | Desktop client calls Booking with a service token. Agents keep their existing sign-in. |
| [[kiosks-building-blocks\|Kiosks]] | addressed | Device certificate per kiosk from Platform PKI, in the March 2027 image |
| [[notifications-building-blocks\|Notifications]] | unchanged | Subscribes to the event bus with existing Platform credentials |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | Existing read API access |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | Existing read API access |
<!-- /generated -->

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-004|UNK-004]]
- Decisions: [[ADR-0001-one-booking-context|ADR-0001]], [[ADR-0003-versioned-booking-api|ADR-0003]]
- Epics: [[EPC-031-holds-and-confirms|EPC-031]], [[EPC-035-kiosks-to-booking|EPC-035]], [[EPC-038-pricing-serves-booking|EPC-038]]
