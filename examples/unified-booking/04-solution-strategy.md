---
id: solution-strategy
type: initiative-section
title: Solution strategy
initiative: INI-002
arc42: "§4"
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-14 Shape", "session 2026-07-28 Shape", "session 2026-08-12 Grill"]
---

# Solution strategy

- **Decision:** [[2026-07-28-solution-strategy]]

## The core move

Put one application, Booking, in front of FERRYMASTER and make it the only thing that decides a booking's state. Every channel asks Booking. Booking asks the ledger. The details of what changes per capability are on the [[04a-capability-delta|Capability delta]] page.

We looked at a shared adapter library first. It would have been quicker, but it would have left three teams each deciding what "confirmed" means, which is half the problem we are solving. See [[ADR-0001-one-booking-context|the one-application decision]].

## How it works with a mainframe we can't touch

FERRYMASTER stays the ledger of record ([[ADR-0002-ferrymaster-ledger-of-record|the ledger-of-record decision]]). Booking keeps short-lived state, such as a ten-minute hold while the customer pays, but the ledger always has the final word.

Booking talks to the ledger through FERRYMASTER's existing MQ transactions, not by scraping screens ([[ADR-0004-mq-not-screen-scraping|the MQ decision]]). We found those transactions during Discover: the mainframe team already exposes them for the finance job. That one finding removed the main reason the old adapters kept breaking.

When a ledger write is slow or fails, Booking keeps the hold and retries. The customer sees "confirming" rather than an error, and the call centre sees exactly what the customer sees. That replaces the next-morning manual fixes.

## How the channels move

Channels move one at a time, so a problem only ever affects one of them:

1. **Website** first, in February 2027. It has the most traffic and the fastest release cycle.
2. **Call centre** second, in March 2027, with amend and cancel moving onto Booking at the same time.
3. **Kiosks** last, with the March 2027 image, because they can only change twice a year.

Each channel keeps its old adapter behind a switch for four weeks after it moves. Rollback is flipping the switch. Once the four weeks pass cleanly, the adapter is deleted. The Booking API is versioned, and each version lives at least six months so the kiosks never get stranded ([[ADR-0003-versioned-booking-api|the versioning decision]]). The full plan is on [[concern-rollout|Rollout]].

## What we chose not to do

- Rebuild the ledger. That is the Mainframe Exit initiative, and this initiative gives it a single door to replace.
- Let channels keep a direct line to Pricing "just in case". One caller is the point.
- Build our own payment page. Tidepay's hosted page keeps us out of PCI scope.
