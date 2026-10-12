---
id: concern-testing
type: concern
title: Testing
initiative: INI-002
arc42: "§8"
owner: "@hl-qa-lead"
authored: mixed
sources: ["session 2026-09-16 Grill", "UNK-002 test data", SRC-04]
---

# Testing


## Strategy

Every Booking boundary has a contract test, and every contract test has a named team on each side. The old adapters broke because nobody tested the joins between apps; each front end tested itself against a mainframe screen that could change without warning. Consumer-driven contract tests move that check to the provider. Each channel publishes what it expects from the Booking API, and Booking's pipeline verifies every published expectation before a release. If Booking would break the website, the Booking build fails before anything ships. Kiosk v1 expectations stay in Booking's verification for as long as v1 is live, which is at least six months ([[ADR-0003-versioned-booking-api|the versioning decision]]).

FERRYMASTER cannot run in a pipeline, and its test region refreshes once a year, so its data goes stale ([[11-unknowns-and-risks#UNK-002 Repeatable test data|Repeatable test data]]). The Booking team built a ledger simulator that answers BKHOLD, BKCONF, BKAMND and BKCANC from the MQ mapping in [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]]. Contract tests and staging end-to-end runs use the simulator. A simulator only proves Booking agrees with the simulator, so once a week the QA lead runs the end-to-end suites against the FERRYMASTER test region. A difference between the weekly run and the simulator is a defect in the simulator, and the Booking team fixes it before the next release. The mainframe team announces MQ changes 8 weeks ahead, which gives time to update the simulator first.

End-to-end tests are kept to the two flows that move money and write the ledger: [[FLO-001-hold-pay-confirm|Hold, pay, confirm]] and [[FLO-002-amend-or-cancel|Amend or cancel]]. They are slow and they depend on Tidepay's sandbox, so adding more would slow every release for little gain. [[FLO-003-notify-on-change|Notify on change]] relies on contract tests for the Booking state changed event. Vessel schedule and Customer identity do not change in this initiative and do not run provider tests, so Booking's consumer-side tests are the only check on the capacity check and the customer lookup. If either team changes its read API, Booking's next build catches it. That gap is accepted because both APIs have been stable for years and serve other callers.

## Per app

| App | State | Why |
|---|---|---|
| [[booking-building-blocks\|Booking]] | addressed | Builds the ledger simulator and runs provider verification for CON-001 |
| [[pricing-building-blocks\|Pricing]] | addressed | Provider verification for CON-003 in Pricing's pipeline |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | addressed | Keeps the test region available for the weekly end-to-end run |
| [[website-building-blocks\|Website]] | addressed | Consumer-driven contract tests for CON-001 in its own pipeline |
| [[call-centre-building-blocks\|Call centre]] | addressed | Consumer-driven contract tests for CON-001 in its own pipeline |
| [[kiosks-building-blocks\|Kiosks]] | addressed | Consumer-driven contract tests for CON-001 v1 in the image build |
| [[notifications-building-blocks\|Notifications]] | addressed | Consumer test for CON-002 in Notifications' pipeline |
| [[vessel-schedule-building-blocks\|Vessel schedule]] | unchanged | Booking's consumer-side test is the only check on CON-004 |
| [[customer-identity-building-blocks\|Customer identity]] | unchanged | Booking's consumer-side test is the only check on CON-005 |

## Per contract

Who tests each contract, from each side, is written once on the contract under **Tested by:**.

- [[booking-building-blocks#CON-001 Booking API|CON-001 Booking API]]
- [[booking-building-blocks#CON-002 Booking state changed|CON-002 Booking state changed]]
- [[pricing-building-blocks#CON-003 Quote a fare|CON-003 Quote a fare]]
- [[vessel-schedule-building-blocks#CON-004 Capacity check|CON-004 Capacity check]]
- [[customer-identity-building-blocks#CON-005 Customer lookup|CON-005 Customer lookup]]
- [[ferrymaster-building-blocks#CON-006 Ledger transactions|CON-006 Ledger transactions]]
- [[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007 Tidepay payment outcome]]

## End-to-end suites

| Flow | Paths | Environment | When | Owner |
|---|---|---|---|---|
| [[FLO-001-hold-pay-confirm\|FLO-001]] | Website, call centre desktop; kiosk on a test kiosk | Staging with ledger simulator and Tidepay sandbox; FERRYMASTER test region weekly | Every Booking release candidate; weekly; kiosk before March 2027 image sign-off | QA lead; kiosk run by Port Systems senior |
| [[FLO-002-amend-or-cancel\|FLO-002]] | Website, call centre desktop: amend up, amend down, cancel. No kiosk path; kiosks do not amend or cancel in the March 2027 image. | Same as FLO-001 | Every Booking release candidate; weekly | QA lead |
| [[FLO-003-notify-on-change\|FLO-003]] | None. Covered by CON-002 contract tests. | n/a | n/a | QA lead |

## Related

- Unknowns: [[11-unknowns-and-risks#UNK-002 Repeatable test data|Repeatable test data]] (test data), [[11-unknowns-and-risks#UNK-001 Ledger write latency|Ledger write latency]] (ledger latency behind the "confirming" screen the suites check)
- Decisions: [[ADR-0003-versioned-booking-api|the versioning decision]], [[ADR-0004-mq-not-screen-scraping|the MQ decision]]
- Epics: [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]], [[EPC-032-ledger-adapter|Ledger adapter on FERRYMASTER's MQ transactions]] (ledger simulator), [[EPC-033-website-to-booking|Website moves to Booking]], [[EPC-034-call-centre-to-booking|Call centre moves to Booking]], [[EPC-035-kiosks-to-booking|Kiosks move to Booking in the March image]], [[EPC-036-amend-cancel-online|Amend and cancel online]], [[EPC-037-events-and-notifications|Booking events and customer notifications]], [[EPC-038-pricing-serves-booking|Pricing serves Booking only]]
