---
id: unknowns-and-risks
type: index
title: Unknowns and risks
initiative: INI-002
arc42: "§11"
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Discover"]
---

# Unknowns and risks

<!-- generated:unknowns-index sha=8e05ec76: do not edit, run planner render -->
| ID | Name | Owner | State | Ask by |
|---|---|---|---|---|
| [[#UNK-001 Ledger write latency\|UNK-001]] | Ledger write latency | @hl-booking-senior (Booking senior) | resolved |  |
| [[#UNK-002 Repeatable test data\|UNK-002]] | Repeatable test data | @hl-qa-lead (QA lead) | resolved |  |
| [[#UNK-003 Mainframe capacity in Q1\|UNK-003]] | Mainframe capacity in Q1 | @hl-solution-lead (solution lead) | resolved |  |
| [[#UNK-004 Kiosk authentication\|UNK-004]] | Kiosk authentication | @hl-port-senior (Port Systems senior) | resolved |  |
| [[#UNK-005 Event bus readiness\|UNK-005]] | Event bus readiness | @hl-platform-lead (Platform lead) | resolved |  |
| [[#UNK-006 Finance on Booking events\|UNK-006]] | Finance on Booking events | @hl-platform-lead (Platform lead) | open | 2027-03-01 |
| [[#UNK-007 Booking on-call\|UNK-007]] | Booking on-call | @hl-solution-lead (solution lead) | resolved |  |
| [[#R-01 Mainframe knowledge sits with two people\|R-01]] | Mainframe knowledge sits with two people | @hl-solution-lead (solution lead) | mitigated |  |
| [[#R-02 The March 2027 kiosk image slips\|R-02]] | The March 2027 kiosk image slips | @hl-port-senior (Port Systems senior) | mitigated |  |
<!-- /generated:unknowns-index -->

## Unknowns

### UNK-001 Ledger write latency

- **Question:** Is ledger write latency good enough for hold-pay-confirm?
- **Owner:** @hl-booking-senior (Booking senior)
- **Opened:** 2026-07-28 Grill
- **State:** resolved
- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, [[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]
- **Outcome:** Measured p95 of 2.1 s over MQ. The customer sees "confirming" while Booking retries. Fine.
- **Resolved in:** [[2026-09-02-hold-pay-confirm]]

### UNK-002 Repeatable test data

- **Question:** How do we get repeatable FERRYMASTER test data? The test region refreshes once a year, so its data goes stale.
- **Owner:** @hl-qa-lead (QA lead)
- **Opened:** 2026-08-12 Grill
- **State:** resolved
- **Blocks:** [[concern-testing|Testing]], [[EPC-032-ledger-adapter|EPC-032]]
- **Outcome:** The Booking team builds a ledger simulator for contract tests. End-to-end suites run weekly against the test region.
- **Resolved in:** [[2026-09-16-testing-and-amend]]

### UNK-003 Mainframe capacity in Q1

- **Question:** Does the mainframe team have capacity in Q1?
- **Owner:** @hl-solution-lead (solution lead)
- **Opened:** 2026-07-14 Discover
- **State:** resolved
- **Blocks:** [[EPC-032-ledger-adapter|EPC-032]] scheduling, [[ADR-0004-mq-not-screen-scraping|ADR-0004]]
- **Outcome:** Yes. Two days a week, January to March 2027, confirmed by the mainframe team lead.
- **Resolved in:** [[2026-08-14-mainframe-capacity]]

### UNK-004 Kiosk authentication

- **Question:** How do kiosks authenticate? Kiosks have no user, so there is nobody to sign in.
- **Owner:** @hl-port-senior (Port Systems senior)
- **Opened:** 2026-08-26 Grill
- **State:** resolved
- **Blocks:** [[EPC-035-kiosks-to-booking|EPC-035]], [[concern-security|Security]]
- **Outcome:** Device certificates from Platform's existing PKI, installed with the March 2027 image.
- **Resolved in:** [[2026-09-23-security]]

### UNK-005 Event bus readiness

- **Question:** Is the event bus production-ready?
- **Owner:** @hl-platform-lead (Platform lead)
- **Opened:** 2026-07-28 Grill
- **State:** resolved
- **Blocks:** [[booking-building-blocks#CON-002 Booking state changed|CON-002]], [[EPC-037-events-and-notifications|EPC-037]]
- **Outcome:** Yes, production-ready since 2026-11-01.
- **Resolved in:** [[2026-11-03-events]]

### UNK-006 Finance on Booking events

- **Question:** Should the finance reconciliation job read Booking events instead of FERRYMASTER?
- **Owner:** @hl-platform-lead (Platform lead)
- **Opened:** 2026-10-07 Grill
- **State:** open
- **Ask by:** 2027-03-01
- **Blocks:** nothing in INI-002
- **Notes:** Deferred to INI-005. CON-002 is additive-only, so Finance can subscribe later without a Booking change.

### UNK-007 Booking on-call

- **Question:** Who is on call for Booking?
- **Owner:** @hl-solution-lead (solution lead)
- **Opened:** 2026-09-16 Grill
- **State:** resolved
- **Blocks:** [[EPC-039-run-booking|EPC-039]], [[concern-operations|Operations]]
- **Outcome:** The Booking team joins the Platform on-call rota from go-live.
- **Resolved in:** [[2026-10-07-concerns]]

## Risks

### R-01 Mainframe knowledge sits with two people

Two people understand FERRYMASTER's COBOL and MQ transactions. If both are away, nobody can diagnose a ledger write problem.

- **Owner:** @hl-solution-lead (solution lead)
- **State:** mitigated
- **Mitigation:** the MQ mapping is documented in [[ferrymaster-building-blocks#CON-006 Ledger transactions|CON-006]], and Booking engineers pair with the mainframe team from January to March 2027.

### R-02 The March 2027 kiosk image slips

Kiosk images ship in March and September. If March slips, kiosks wait six months for the next one.

- **Owner:** @hl-port-senior (Port Systems senior)
- **State:** mitigated
- **Mitigation:** kiosks keep their old adapter until their cutover, and Booking API v1 is kept for at least six months ([[ADR-0003-versioned-booking-api|ADR-0003]]).
