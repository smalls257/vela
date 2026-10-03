---
id: decisions
type: index
title: Architecture decisions
initiative: INI-002
arc42: "§9"
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-14 Discover", "session 2026-07-28 Grill", "session 2026-08-12 Grill", "session 2026-08-26 Grill"]
---

# Architecture decisions

Four decisions shape INI-002. Each one records the options turned down and the unknowns it rests on, so that if an assumption fails, the decision to revisit is easy to find.

- [[ADR-0001-one-booking-context|ADR-0001]] One Booking application rather than a shared adapter library
- [[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]] FERRYMASTER stays the ledger of record
- [[ADR-0003-versioned-booking-api|ADR-0003]] Version the Booking API and keep each version at least 6 months
- [[ADR-0004-mq-not-screen-scraping|ADR-0004]] Use FERRYMASTER's existing MQ transactions instead of screen scraping
