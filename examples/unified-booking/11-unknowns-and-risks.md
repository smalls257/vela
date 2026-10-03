---
id: unknowns-and-risks
type: index
title: Unknowns and risks
initiative: INI-002
arc42: "§11"
state: addressed
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session-history", "session 2026-07-14 Discover"]
---

# Unknowns and risks

Six of seven unknowns are resolved. UNK-006 is open and blocks nothing in INI-002. Sessions are listed in [[session-history|Session history]].

<!-- generated: do not edit -->
| ID | Question | Owner | State | Resolved |
|---|---|---|---|---|
| [[#UNK-001\|UNK-001]] | Ledger write latency | Booking senior | resolved | 2026-09-02 |
| [[#UNK-002\|UNK-002]] | Repeatable test data | QA lead | resolved | 2026-09-16 |
| [[#UNK-003\|UNK-003]] | Mainframe capacity in Q1 | solution lead | resolved | 2026-08-14 |
| [[#UNK-004\|UNK-004]] | Kiosk authentication | Port Systems senior | resolved | 2026-09-23 |
| [[#UNK-005\|UNK-005]] | Event bus readiness | Platform lead | resolved | 2026-11-03 |
| [[#UNK-006\|UNK-006]] | Finance on Booking events | Platform lead | open, review 2027-03-01 | |
| [[#UNK-007\|UNK-007]] | Booking on-call | solution lead | resolved | 2026-10-07 |
| [[#R-01\|R-01]] | Mainframe knowledge | solution lead | mitigated | |
| [[#R-02\|R-02]] | Kiosk image slip | Port Systems senior | mitigated | |
<!-- /generated -->

## Unknowns

### UNK-001 Is ledger write latency good enough for hold-pay-confirm?

- **Owner:** Booking senior. **Opened:** 2026-07-28 Grill. **State:** resolved 2026-09-02.
- **Outcome:** Measured p95 of 2.1 s over MQ. The customer sees "confirming" while Booking retries. Fine.
- **Blocked:** [[FLO-001-hold-pay-confirm|FLO-001]] design, [[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]].
- **Resolved in:** session 2026-09-02 Grill.

### UNK-002 How do we get repeatable FERRYMASTER test data?

- **Owner:** QA lead. **Opened:** 2026-08-12 Grill. **State:** resolved 2026-09-16.
- **Question:** The FERRYMASTER test region refreshes once a year, so its data goes stale.
- **Outcome:** The Booking team builds a ledger simulator for contract tests. End-to-end suites run weekly against the test region.
- **Blocked:** [[concern-testing|Testing]], [[EPC-032-ledger-adapter|EPC-032]].
- **Resolved in:** session 2026-09-16 Grill.

### UNK-003 Does the mainframe team have capacity in Q1?

- **Owner:** solution lead. **Opened:** 2026-07-14 Discover. **State:** resolved 2026-08-14.
- **Outcome:** Yes. Two days a week, January to March 2027, confirmed by the mainframe team lead.
- **Blocked:** [[EPC-032-ledger-adapter|EPC-032]] scheduling, [[ADR-0004-mq-not-screen-scraping|ADR-0004]].
- **Resolved in:** session 2026-08-14 Grill.

### UNK-004 How do kiosks authenticate?

- **Owner:** Port Systems senior. **Opened:** 2026-08-26 Grill. **State:** resolved 2026-09-23.
- **Question:** Kiosks have no user, so there is nobody to sign in.
- **Outcome:** Device certificates from Platform's existing PKI, installed with the March 2027 image.
- **Blocked:** [[EPC-035-kiosks-to-booking|EPC-035]], [[concern-security|Security]].
- **Resolved in:** session 2026-09-23 Grill.

### UNK-005 Is the event bus production-ready?

- **Owner:** Platform lead. **Opened:** 2026-07-28 Grill. **State:** resolved 2026-11-03.
- **Outcome:** Yes, production-ready since 2026-11-01.
- **Blocked:** [[booking-building-blocks#CON-002|CON-002]], [[EPC-037-events-and-notifications|EPC-037]].
- **Resolved in:** session 2026-11-03 Grill.

### UNK-006 Should Finance reconciliation read Booking events?

- **Owner:** Platform lead. **Opened:** 2026-10-07 Grill. **State:** open, review 2027-03-01.
- **Question:** Should the finance reconciliation job read Booking events instead of FERRYMASTER?
- **Outcome so far:** Deferred to INI-005. CON-002 is additive-only, so Finance can subscribe later without a Booking change.
- **Blocks:** nothing in INI-002.

### UNK-007 Who is on call for Booking?

- **Owner:** solution lead. **Opened:** 2026-09-16 Grill. **State:** resolved 2026-10-07.
- **Outcome:** The Booking team joins the Platform on-call rota from go-live.
- **Blocked:** [[EPC-039-run-booking|EPC-039]], [[concern-operations|Operations]].
- **Resolved in:** session 2026-10-07 Grill.

## Risks

### R-01 Mainframe knowledge sits with two people

Two people understand FERRYMASTER's COBOL and MQ transactions. If both are away, nobody can diagnose a ledger write problem. **Mitigation:** the MQ mapping is documented in [[ferrymaster-building-blocks#CON-006|CON-006]], and Booking engineers pair with the mainframe team from January to March 2027. **Owner:** solution lead.

### R-02 The March 2027 kiosk image slips

Kiosk images ship in March and September. If March slips, kiosks wait six months for the next one. **Mitigation:** kiosks keep their old adapter until their cutover, and Booking API v1 is kept for at least six months ([[ADR-0003-versioned-booking-api|ADR-0003]]). **Owner:** Port Systems senior.
