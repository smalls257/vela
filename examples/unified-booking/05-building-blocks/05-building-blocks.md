---
id: building-blocks
type: index
title: Building blocks
initiative: INI-002
arc42: "§5"
c4: context
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-28 Shape", "session 2026-09-09 Grill", "co-design sessions with each app's senior, 2026-09 to 2026-10"]
---

# Building blocks

Each application in scope has two pages: its building blocks and contracts (§5), and its runtime (§6). New and changed apps go one level in and show their main containers, co-designed with that app's senior. Components are never described here; they belong to each team's tech design.

## Who owns what, and how they relate

```mermaid
flowchart TB
  B["Booking<br/>Booking team · new"]
  P["Pricing<br/>Revenue · changed"]
  VS["Vessel schedule<br/>Marine Ops Systems"]
  CI["Customer identity<br/>Platform"]
  N["Notifications<br/>Platform · new consumer"]
  FM[("FERRYMASTER<br/>Mainframe team · can't change")]
  CH["Website · Call centre · Kiosks<br/>channel teams · changed"]
  CH -- "customer of" --> B
  B -- "customer of" --> P
  B -- "conforms to" --> VS
  B -- "conforms to" --> CI
  B -- "anticorruption layer, owned by Booking" --> FM
  B -. "publishes events" .-> N
```

Each line is a contract, and each contract lives on the provider's page.

## Apps

- [[booking-building-blocks|Booking]] · [[booking-runtime|runtime]]
- [[pricing-building-blocks|Pricing]] · [[pricing-runtime|runtime]]
- [[ferrymaster-building-blocks|FERRYMASTER]] · [[ferrymaster-runtime|runtime]]
- [[website-building-blocks|Public website]] · [[website-runtime|runtime]]
- [[call-centre-building-blocks|Call centre desktop]] · [[call-centre-runtime|runtime]]
- [[kiosks-building-blocks|Port kiosks]] · [[kiosks-runtime|runtime]]
- [[notifications-building-blocks|Notifications]] · [[notifications-runtime|runtime]]
- [[vessel-schedule-building-blocks|Vessel schedule]]
- [[customer-identity-building-blocks|Customer identity]]

## All contracts

- [[booking-building-blocks#CON-001 Booking API|CON-001 Booking API]]
- [[booking-building-blocks#CON-002 Booking state changed|CON-002 Booking state changed]]
- [[pricing-building-blocks#CON-003 Quote a fare|CON-003 Quote a fare]]
- [[vessel-schedule-building-blocks#CON-004 Capacity check|CON-004 Capacity check]]
- [[customer-identity-building-blocks#CON-005 Customer lookup|CON-005 Customer lookup]]
- [[ferrymaster-building-blocks#CON-006 Ledger transactions|CON-006 Ledger transactions]]
- [[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007 Tidepay payment outcome]]
