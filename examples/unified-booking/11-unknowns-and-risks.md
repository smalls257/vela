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

## Question ledger

Catalogue v1 owes these questions. Each row says where one stands. A wildcard row answers every copy it matches, and a copy with its own row is an exception to it.

| Copy | State | Evidence | By | Date |
|---|---|---|---|---|
| Q-FIN-01@INI-002 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: "the loyalty scheme, which reads FERRYMASTER directly and stays out of scope until INI-004" in [[03-context-and-scope]] | @hl-solution-lead | 2026-11-19 |
| Q-FIN-02@INI-002 | asked | capture: [[2026-11-19-owed-questions#^c01]] | @hl-solution-lead | 2026-11-19 |
| Q-FIN-03@SV-01 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: "Finance, through INI-004 Loyalty Revamp" in [[03-context-and-scope]] | @hl-solution-lead | 2026-11-19 |
| Q-FIN-04@SV-01 | not-applicable | reason: INI-002 neither changes who holds the points nor combines two schemes | @hl-solution-lead | 2026-11-19 |
| Q-FIN-05@SV-01 | not-applicable | reason: INI-002 neither expires nor closes any points balance, and INI-004 owns any expiry rule | @hl-solution-lead | 2026-11-19 |
| Q-FIN-06@SV-01 | not-applicable | reason: no balance converts between schemes under INI-002, so there is no rate to set | @hl-solution-lead | 2026-11-19 |
| Q-DAT-01@INI-002 | answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\|CON-005]]; source: SRC-07 | @hl-solution-lead | 2026-11-19 |
| Q-DAT-05@INI-002 | answered | item: [[concern-data\|Data]]; source: "The only personal data is the customer ID." in [[concern-data]] | @hl-solution-lead | 2026-11-19 |
| Q-DAT-02@APP-* | answered | item: [[concern-data\|Data]]; source: "Booking holds no card data and no contact details." in [[concern-data]] | @hl-solution-lead | 2026-11-19 |
| Q-DAT-02@APP-pricing | not-applicable | reason: Pricing quotes from route, date and fare rules and never receives a customer ID | @hl-pricing-senior | 2026-11-19 |
| Q-DAT-03@CON-* | answered | item: [[concern-data\|Data]]; source: "Notifications resolves contact details at send time from Customer identity." in [[concern-data]] | @hl-solution-lead | 2026-11-19 |
| Q-DAT-03@CON-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\|UNK-006]] | @hl-solution-lead | 2026-11-19 |
| Q-DAT-04@SV-01 | answered | item: [[ADR-0002-ferrymaster-ledger-of-record\|ADR-0002]]; source: "the loyalty scheme, which reads FERRYMASTER directly" in [[03-context-and-scope]] | @hl-solution-lead | 2026-11-19 |
| Q-PTN-01@INI-002 | answered | item: [[03-context-and-scope#PTY-02 FERRYMASTER vendor\|PTY-02]]; source: SRC-02 | @hl-solution-lead | 2026-11-19 |
| Q-PTN-02@PTY-01 | answered | item: [[booking-building-blocks#CON-007 Tidepay payment outcome\|CON-007]]; source: SRC-05 | @hl-booking-senior | 2026-11-19 |
| Q-PTN-02@PTY-02 | answered | item: [[ADR-0002-ferrymaster-ledger-of-record\|ADR-0002]]; source: SRC-02 | @hl-solution-lead | 2026-11-19 |
| Q-PTN-03@PTY-01 | assumed | belief: the Tidepay contract renews each year on today's terms; load-bearing: no; signpost: procurement's renewal notice each autumn | @hl-solution-lead | 2026-11-19 |
| Q-PTN-03@PTY-02 | answered | item: [[02-constraints\|CST-1]]; source: SRC-02 | @hl-solution-lead | 2026-11-19 |
| Q-PTN-05@PTY-* | assumed | belief: neither agreement is assigned or changes control, because INI-002 keeps both suppliers and their contracts as they are (CST-1, CST-2); load-bearing: no; signpost: an assignment or change-of-control notice from Tidepay or the FERRYMASTER vendor | @hl-solution-lead | 2026-11-19 |
| Q-PTN-06@PTY-01 | not-applicable | reason: payment stays with Tidepay under its existing contract (CST-2), so INI-002 asks for no change to the agreement | @hl-solution-lead | 2026-11-19 |
| Q-PTN-06@PTY-02 | assumed | belief: no notice is due, because Booking works around the mainframe and never inside it (CST-1), so the vendor contract stays as it is; load-bearing: no; signpost: procurement raising the vendor contract's 2028 end date in the INI-005 plan | @hl-solution-lead | 2026-11-19 |
| Q-REG-01@INI-002 | not-applicable | reason: Booking sells single ferry crossings, and nothing is sold with another party | @hl-solution-lead | 2026-11-19 |
| Q-REG-02@INI-002 | not-applicable | reason: no new product, activity or licence, and card data stays with Tidepay | @hl-solution-lead | 2026-11-19 |
| Q-REG-05@INI-002 | not-applicable | reason: no product is shared across parties, so no party's failure reaches a customer through one | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-* | answered | item: [[concern-operations\|Operations]]; source: "Digital team support as today, less one adapter" in [[concern-operations]] | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-booking | answered | item: [[#UNK-007 Booking on-call\|UNK-007]]; source: "joins the Platform on-call rota from go-live" in [[concern-operations]] | @hl-solution-lead | 2026-11-19 |
| Q-OPS-02@CON-* | answered | item: [[booking-runtime#When a dependency is slow or down\|Booking runtime]]; source: SRC-04 | @hl-booking-senior | 2026-11-19 |
| Q-OPS-03@INI-002 | answered | item: [[concern-ownership\|Ownership]]; source: "Every app keeps its current owner." in [[concern-ownership]]; covers: capability | @hl-solution-lead | 2026-11-19 |
| Q-OPS-04@INI-002 | answered | item: [[ADR-0001-one-booking-context\|ADR-0001]]; source: SRC-01 | @hl-solution-lead | 2026-11-19 |
| Q-OPS-05@INI-002 | answered | item: [[CAP-023-fix-failed-bookings\|CAP-023]]; source: "EPC-034 retires the manual fix queue." in [[CAP-023-fix-failed-bookings]] | @hl-solution-lead | 2026-11-19 |
| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\|UNK-006]] | @hl-solution-lead | 2026-11-19 |
| Q-OPS-07@INI-002 | assumed | belief: customers amend online once they can; load-bearing: yes; signpost: the online share of amendments in the first two months after go-live | @hl-solution-lead | 2026-11-19 |
| R-FIN-01 | open | question: Points are earned at reservation, so does a cancelled booking take its points back, and who tells the loyalty scheme?; quote: "because points are earned at reservation" in [[04a-capability-delta]]; severity: normal | @hl-solution-lead | 2026-11-19 |
