---
id: epics
type: index
title: Epics
initiative: INI-002
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-10-21 Shape", "session 2026-11-18 Grill"]
---

# Epics

Nine epics deliver Unified Booking. Each one names its owning team. The solution lead wrote every epic down to its acceptance criteria; the teams write the stories after their own tech design sessions.

Booking's own epics come first because every channel cutover needs a working Booking API and ledger writes. The channels then move in the order the rollout concern sets: website in February 2027, call centre in March 2027, kiosks with the March 2027 image. Pricing closes the gateway to other callers last, once no front end calls it directly.

- [[EPC-031-holds-and-confirms|EPC-031]] Booking holds and confirms crossings
- [[EPC-032-ledger-adapter|EPC-032]] Ledger adapter on FERRYMASTER's MQ transactions
- [[EPC-033-website-to-booking|EPC-033]] Website moves to Booking
- [[EPC-034-call-centre-to-booking|EPC-034]] Call centre moves to Booking
- [[EPC-035-kiosks-to-booking|EPC-035]] Kiosks move to Booking in the March image
- [[EPC-036-amend-cancel-online|EPC-036]] Amend and cancel online
- [[EPC-037-events-and-notifications|EPC-037]] Booking events and customer notifications
- [[EPC-038-pricing-serves-booking|EPC-038]] Pricing serves Booking only
- [[EPC-039-run-booking|EPC-039]] Run Booking: on-call, runbooks, dashboards


## Sequencing

```mermaid
flowchart LR
  E032[EPC-032 Ledger adapter] --> E031[EPC-031 Holds and confirms]
  E032 --> E039[EPC-039 Run Booking]
  E031 --> E039
  E039 --> E033[EPC-033 Website, Feb 2027]
  E031 --> E033
  E033 --> E036[EPC-036 Amend and cancel online]
  E036 --> E034[EPC-034 Call centre, Mar 2027]
  E031 --> E035[EPC-035 Kiosks, March image]
  E031 --> E037[EPC-037 Events and notifications]
  E033 --> E038[EPC-038 Pricing serves Booking]
  E034 --> E038
  E035 --> E038
```
