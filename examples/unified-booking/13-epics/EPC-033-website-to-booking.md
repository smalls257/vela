---
id: EPC-033
type: epic
title: Website moves to Booking
initiative: INI-002
state: decided
owner: "@harbourline/digital-team"
authored: authored
apps: [APP-website, APP-booking]
delivers: [CAP-013, G1, G2]
consumes: [CON-001]
flows: [FLO-001]
depends_on: [EPC-031, EPC-032, EPC-039]
sources: ["session 2026-10-07 Grill", "session 2026-11-18 Grill"]
---

# EPC-033 Website moves to Booking

- **Decision:** [[2026-11-18-epics]]

The website's booking pages call the Booking API (CON-001) and the FM screen adapter is retired. The website goes first because it has the worst failure today: if the second scrape, the confirm, fails after payment, the customer has paid for nothing and the call centre fixes it by hand the next morning. With Booking, Tidepay's payment outcome goes to Booking, which keeps the hold and retries the ledger write.

Cutover is February 2027. The old adapter stays behind a switch for 4 weeks so the Digital team can send bookings back to it without a release. After 4 weeks it is removed and the website no longer depends on any FERRYMASTER screen.

**Owning team:** Digital team.

## Epic acceptance criteria

1. Every booking the website makes after cutover goes through CON-001 hold, confirm and get, with the website's service token and a trace ID the website created on every call. [security] [observability]
2. A customer whose payment succeeds sees "confirming" until Booking returns `confirmed`, and then sees the confirmed booking. No customer is left with a payment and no booking.
3. The website's consumer-driven contract tests for CON-001 pass in Booking's provider verification. [testing]
4. Flipping the website's switch back sends new bookings through the FM screen adapter without a release. [rollout]
5. Four weeks after cutover the FM screen adapter is removed, and FERRYMASTER sees no screen sessions from the website. [data]

## Traces to

- Capabilities: [[CAP-013-reserve-a-crossing|CAP-013 Reserve a crossing]] (website)
- Contracts: [[booking-building-blocks#CON-001 Booking API|CON-001 Booking API]] (client)
- Concerns: [[concern-rollout|Rollout]], [[concern-testing|Testing]]
- Goals: [[01-goals|G1]], [[01-goals|G2]]
- Flow: [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]
- Apps: [[website-building-blocks|Public website]], [[booking-building-blocks|Booking]]

## Depends on

- [[EPC-031-holds-and-confirms|EPC-031]]: hold, confirm and get on CON-001.
- [[EPC-032-ledger-adapter|EPC-032]]: ledger writes in production.
- [[EPC-039-run-booking|EPC-039]]: on-call, runbooks and dashboards live before real traffic.

## Rollout notes

First channel to cut over, February 2027. Rollback is flipping the website's switch back during the 4 weeks.

## Out of scope

- Amend and cancel pages ([[EPC-036-amend-cancel-online|EPC-036]]).
- Booking emails, which move to Notifications in [[EPC-037-events-and-notifications|EPC-037]].

The Digital team breaks this epic into stories after their tech design session.
