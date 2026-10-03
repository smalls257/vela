---
id: flows
type: index
title: Flows
initiative: INI-002
arc42: "§6"
state: decided
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-09-02 Grill", "session 2026-09-16 Grill"]
---

# Flows

A flow follows one capability across every application it touches, from the customer's first click to the message they receive. App runtime pages show what happens inside one app. These pages show the hand-offs between apps, which is where the old adapters broke.

Three flows cover INI-002. Hold-pay-confirm and amend-or-cancel carry money and ledger writes, so they get end-to-end tests. Notify-on-change is one event and one consumer, so contract tests cover it.

<!-- generated: do not edit -->
| Flow | Capabilities | Apps involved | Epics | Tested end to end |
|---|---|---|---|---|
| [[FLO-001-hold-pay-confirm\|FLO-001 Hold, pay, confirm]] | [[CAP-011-find-a-crossing\|CAP-011]], [[CAP-014-hold-a-seat\|CAP-014]], [[CAP-012-quote-a-fare\|CAP-012]], [[CAP-015-take-payment\|CAP-015]], [[CAP-013-reserve-a-crossing\|CAP-013]], [[CAP-022-notify-customer\|CAP-022]] | [[website-building-blocks\|Website]], [[call-centre-building-blocks\|Call centre]], [[kiosks-building-blocks\|Kiosks]], [[booking-building-blocks\|Booking]], [[vessel-schedule-building-blocks\|Vessel schedule]], [[customer-identity-building-blocks\|Customer identity]], [[pricing-building-blocks\|Pricing]], [[ferrymaster-building-blocks\|FERRYMASTER]], [[notifications-building-blocks\|Notifications]], Tidepay | [[EPC-031-holds-and-confirms\|EPC-031]], [[EPC-032-ledger-adapter\|EPC-032]], [[EPC-033-website-to-booking\|EPC-033]], [[EPC-034-call-centre-to-booking\|EPC-034]], [[EPC-035-kiosks-to-booking\|EPC-035]], [[EPC-037-events-and-notifications\|EPC-037]], [[EPC-038-pricing-serves-booking\|EPC-038]] | yes |
| [[FLO-002-amend-or-cancel\|FLO-002 Amend or cancel]] | [[CAP-021-amend-or-cancel\|CAP-021]], [[CAP-012-quote-a-fare\|CAP-012]], [[CAP-015-take-payment\|CAP-015]], [[CAP-022-notify-customer\|CAP-022]] | [[website-building-blocks\|Website]], [[call-centre-building-blocks\|Call centre]], [[booking-building-blocks\|Booking]], [[customer-identity-building-blocks\|Customer identity]], [[vessel-schedule-building-blocks\|Vessel schedule]], [[pricing-building-blocks\|Pricing]], [[ferrymaster-building-blocks\|FERRYMASTER]], [[notifications-building-blocks\|Notifications]], Tidepay | [[EPC-036-amend-cancel-online\|EPC-036]], [[EPC-034-call-centre-to-booking\|EPC-034]], [[EPC-032-ledger-adapter\|EPC-032]], [[EPC-037-events-and-notifications\|EPC-037]], [[EPC-038-pricing-serves-booking\|EPC-038]] | yes |
| [[FLO-003-notify-on-change\|FLO-003 Notify on change]] | [[CAP-022-notify-customer\|CAP-022]] | [[booking-building-blocks\|Booking]], [[notifications-building-blocks\|Notifications]], [[customer-identity-building-blocks\|Customer identity]] | [[EPC-037-events-and-notifications\|EPC-037]] | no, contract tests only |
<!-- /generated -->

## Flow pages

- [[FLO-001-hold-pay-confirm|FLO-001 Hold, pay, confirm]]
- [[FLO-002-amend-or-cancel|FLO-002 Amend or cancel]]
- [[FLO-003-notify-on-change|FLO-003 Notify on change]]
