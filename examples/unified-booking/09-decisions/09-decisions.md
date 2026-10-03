---
id: decisions
type: index
title: Architecture decisions
initiative: INI-002
arc42: "§9"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Discover", "session 2026-07-28 Grill", "session 2026-08-12 Grill", "session 2026-08-26 Grill"]
---

# Architecture decisions

Four decisions shape INI-002. Each one records the options turned down and the unknowns it rests on, so that if an assumption fails, the decision to revisit is easy to find.

<!-- generated: do not edit -->
| ADR | Decision | Status | Decided | Session | Rests on |
|---|---|---|---|---|---|
| [[ADR-0001-one-booking-context\|ADR-0001]] | One Booking application owns booking state for every channel | accepted | 2026-07-28 | Grill | [[11-unknowns-and-risks#UNK-003\|UNK-003]], [[11-unknowns-and-risks#UNK-007\|UNK-007]] |
| [[ADR-0002-ferrymaster-ledger-of-record\|ADR-0002]] | FERRYMASTER stays the ledger of record | accepted | 2026-08-12 | Grill | [[11-unknowns-and-risks#UNK-001\|UNK-001]], [[11-unknowns-and-risks#UNK-006\|UNK-006]] |
| [[ADR-0003-versioned-booking-api\|ADR-0003]] | Version the Booking API and keep each version at least 6 months | accepted | 2026-08-26 | Grill | [[11-unknowns-and-risks#UNK-004\|UNK-004]] |
| [[ADR-0004-mq-not-screen-scraping\|ADR-0004]] | Use FERRYMASTER's existing MQ transactions | accepted | 2026-07-14 | Discover | [[11-unknowns-and-risks#UNK-001\|UNK-001]], [[11-unknowns-and-risks#UNK-002\|UNK-002]], [[11-unknowns-and-risks#UNK-003\|UNK-003]] |
<!-- /generated -->
