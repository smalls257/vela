---
id: concern-testing
type: concern
title: Testing
initiative: INI-002
arc42: "§8"
state: addressed
owner: QA lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-09-16 Grill", "UNK-002 test data", "CON-006 MQ spec from mainframe team"]
---

# Testing

**State:** addressed. **Owner:** QA lead.

## Strategy

Every Booking boundary has a contract test, and every contract test has a named team on each side. The old adapters broke because nobody tested the joins between apps; each front end tested itself against a mainframe screen that could change without warning. Consumer-driven contract tests move that check to the provider. Each channel publishes what it expects from the Booking API, and Booking's pipeline verifies every published expectation before a release. If Booking would break the website, the Booking build fails before anything ships. Kiosk v1 expectations stay in Booking's verification for as long as v1 is live, which is at least six months ([[ADR-0003-versioned-booking-api|ADR-0003]]).

FERRYMASTER cannot run in a pipeline, and its test region refreshes once a year, so its data goes stale ([[11-unknowns-and-risks#UNK-002|UNK-002]]). The Booking team built a ledger simulator that answers BKHOLD, BKCONF, BKAMND and BKCANC from the MQ mapping in [[ferrymaster-building-blocks#CON-006|CON-006]]. Contract tests and staging end-to-end runs use the simulator. A simulator only proves Booking agrees with the simulator, so once a week the QA lead runs the end-to-end suites against the FERRYMASTER test region. A difference between the weekly run and the simulator is a defect in the simulator, and the Booking team fixes it before the next release. The mainframe team announces MQ changes 8 weeks ahead, which gives time to update the simulator first.

End-to-end tests are kept to the two flows that move money and write the ledger: [[FLO-001-hold-pay-confirm|FLO-001]] and [[FLO-002-amend-or-cancel|FLO-002]]. They are slow and they depend on Tidepay's sandbox, so adding more would slow every release for little gain. [[FLO-003-notify-on-change|FLO-003]] relies on CON-002 contract tests. Vessel schedule and Customer identity do not change in INI-002 and do not run provider tests, so Booking's consumer-side tests are the only check on CON-004 and CON-005. If either team changes its read API, Booking's next build catches it. That gap is accepted because both APIs have been stable for years and serve other callers.

## Per contract

<!-- generated: do not edit -->
| Contract | Provider-side test | Consumer-side test | Runs | Blocks |
|---|---|---|---|---|
| [[booking-building-blocks#CON-001\|CON-001 Booking API]] | Provider verification of every channel's published contract, per live version. Booking team. | Consumer-driven contract tests. Digital team (website), Contact Centre Systems team (call centre), Port Systems team (kiosks). | Every build on both sides | Booking release |
| [[booking-building-blocks#CON-002\|CON-002 Booking state changed]] | Schema check and additive-only rule. Booking team. | Notifications consumer test. Platform team. | Every build on both sides | Booking release, Notifications release |
| [[pricing-building-blocks#CON-003\|CON-003 Quote a fare]] | Pricing provider verification. Revenue team. | Contract test. Booking team. | Every build on both sides | Pricing release |
| [[vessel-schedule-building-blocks#CON-004\|CON-004 Capacity check]] | None. Existing API, unchanged in INI-002. | Contract test. Booking team. | Every Booking build | Booking release |
| [[customer-identity-building-blocks#CON-005\|CON-005 Customer lookup]] | None. Existing API, unchanged in INI-002. | Contract test. Booking team. | Every Booking build | Booking release |
| [[ferrymaster-building-blocks#CON-006\|CON-006 Ledger transactions]] | None possible (FERRYMASTER cannot change). Mainframe team gives 8 weeks' notice of MQ changes. | Ledger simulator contract tests, Booking team. Weekly run against the FERRYMASTER test region, QA lead. | Every Booking build; weekly | Booking release |
| [[booking-building-blocks#CON-007\|CON-007 Payment outcome]] | Tidepay's own, versioned by Tidepay. | Tidepay sandbox tests. Booking team. | Every Booking build | Booking release |
<!-- /generated -->

## End-to-end suites

<!-- generated: do not edit -->
| Flow | Paths | Environment | When | Owner |
|---|---|---|---|---|
| [[FLO-001-hold-pay-confirm\|FLO-001]] | Website, call centre desktop; kiosk on a test kiosk | Staging with ledger simulator and Tidepay sandbox; FERRYMASTER test region weekly | Every Booking release candidate; weekly; kiosk before March 2027 image sign-off | QA lead; kiosk run by Port Systems senior |
| [[FLO-002-amend-or-cancel\|FLO-002]] | Website, call centre desktop: amend up, amend down, cancel. No kiosk path; kiosks do not amend or cancel in the March 2027 image. | Same as FLO-001 | Every Booking release candidate; weekly | QA lead |
| [[FLO-003-notify-on-change\|FLO-003]] | None. Covered by CON-002 contract tests. | n/a | n/a | QA lead |
<!-- /generated -->

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-002|UNK-002]] (test data), [[11-unknowns-and-risks#UNK-001|UNK-001]] (ledger latency behind the "confirming" screen the suites check)
- Decisions: [[ADR-0003-versioned-booking-api|ADR-0003]], [[ADR-0004-mq-not-screen-scraping|ADR-0004]]
- Epics: [[EPC-031-holds-and-confirms|EPC-031]], [[EPC-032-ledger-adapter|EPC-032]] (ledger simulator), [[EPC-033-website-to-booking|EPC-033]], [[EPC-034-call-centre-to-booking|EPC-034]], [[EPC-035-kiosks-to-booking|EPC-035]], [[EPC-036-amend-cancel-online|EPC-036]], [[EPC-037-events-and-notifications|EPC-037]], [[EPC-038-pricing-serves-booking|EPC-038]]
