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

This page keeps every question nobody could answer when it was asked, and every risk the team watches. The table says which are still open and who must answer; each unknown and risk then has its own section.

<!-- generated:unknowns-index sha=dca6f859: do not edit, run planner render -->
| ID | Name | Owner | State | Ask by |
|---|---|---|---|---|
| [[#UNK-001 Ledger write latency\|UNK-001]] | Ledger write latency | @hl-booking-senior (Booking senior) | resolved |  |
| [[#UNK-002 Repeatable test data\|UNK-002]] | Repeatable test data | @hl-qa-lead (QA lead) | resolved |  |
| [[#UNK-003 Mainframe capacity in Q1\|UNK-003]] | Mainframe capacity in Q1 | @hl-solution-lead (solution lead) | resolved |  |
| [[#UNK-004 Kiosk authentication\|UNK-004]] | Kiosk authentication | @hl-port-senior (Port Systems senior) | resolved |  |
| [[#UNK-005 Event bus readiness\|UNK-005]] | Event bus readiness | @hl-platform-lead (Platform lead) | resolved |  |
| [[#UNK-006 Finance on Booking events\|UNK-006]] | Finance on Booking events | @hl-platform-lead (Platform lead) | open | 2027-03-01 |
| [[#UNK-007 Booking on-call\|UNK-007]] | Booking on-call | @hl-solution-lead (solution lead) | resolved |  |
| [[#UNK-008 Review of the customer data Booking holds\|UNK-008]] | Review of the customer data Booking holds | @hl-solution-lead (solution lead) | open | 2026-12-15 |
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
- **Outcome:** Measured p95 of 2.1 s over message queue (message queue (MQ)). The customer sees "confirming" while Booking retries. Fine.
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

### UNK-008 Review of the customer data Booking holds

- **Question:** Who reviews the customer ID Booking holds with each booking, for the basis it is used on and any regulation that applies to it?
- **Owner:** @hl-solution-lead (solution lead)
- **Opened:** 2026-11-19 Discover
- **State:** open
- **Ask by:** 2026-12-15
- **Blocks:** nothing in INI-002
- **Notes:** Nobody has been named to review it yet. The Data concern lists what Booking holds, and it says nothing about who checks that.

## Risks

### R-01 Mainframe knowledge sits with two people

Two people understand FERRYMASTER's mainframe programming and message queue (MQ) transactions. If both are away, nobody can diagnose a ledger write problem.

- **Owner:** @hl-solution-lead (solution lead)
- **State:** mitigated
- **Mitigation:** the MQ mapping is documented in [[ferrymaster-building-blocks#CON-006 Ledger transactions|CON-006]], and Booking engineers pair with the mainframe team from January to March 2027.

### R-02 The March 2027 kiosk image slips

Kiosk images ship in March and September. If March slips, kiosks wait six months for the next one.

- **Owner:** @hl-port-senior (Port Systems senior)
- **State:** mitigated
- **Mitigation:** kiosks keep their old adapter until their cutover, and Booking API v1 is kept for at least six months ([[ADR-0003-versioned-booking-api|ADR-0003]]).

## Question ledger

Catalog v1 owes these questions. Each row says where one stands. A wildcard row answers every copy it matches, and a copy with its own row is an exception to it.

<!-- generated:undisposed-questions sha=062a2ac9: do not edit, run planner render -->
**Questions:** 57 owed, 0 undisposed, 1 asked, 1 open reviewer question, against catalog v1.

| Copy | State | Area | Severity | Subject | Question |
|---|---|---|---|---|---|
| Q-FIN-02@INI-002 | asked | FIN | normal | INI-002 | Who pays for the change, and who carries its running cost once it is live? |
| R-FIN-01 | open | FIN | normal | reviewer | Points are earned at reservation, so does a canceled booking take its points back, and who tells the loyalty scheme? |
<!-- /generated:undisposed-questions -->

| Copy | State | Evidence | By | Date |
|---|---|---|---|---|
| Q-FIN-01@INI-002 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: "the loyalty scheme, which reads FERRYMASTER directly and stays out of scope until INI-004" in [[03-context-and-scope]]; answer: Yes, the loyalty scheme holds customers' points, and it reads FERRYMASTER directly until INI-004 | @hl-solution-lead | 2026-11-19 |
| Q-FIN-02@INI-002 | asked | capture: [[2026-11-19-owed-questions#^c01]] | @hl-solution-lead | 2026-11-19 |
| Q-FIN-03@SV-01 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: "Finance, through INI-004 Loyalty Revamp" in [[03-context-and-scope]]; answer: Finance owns the points, through INI-004 Loyalty Revamp | @hl-solution-lead | 2026-11-19 |
| Q-FIN-04@SV-01 | not-applicable | reason: INI-002 neither changes who holds the points nor combines two schemes | @hl-solution-lead | 2026-11-19 |
| Q-FIN-05@SV-01 | not-applicable | reason: the loyalty scheme holds the balances and stays out of scope until INI-004, so INI-002 sets no expiry or closure rule | @hl-solution-lead | 2026-11-19 |
| Q-FIN-06@SV-01 | not-applicable | reason: no balance converts between schemes under INI-002, so there is no rate to set | @hl-solution-lead | 2026-11-19 |
| Q-DAT-01@INI-002 | answered | item: [[customer-identity-building-blocks#CON-005 Customer lookup\|CON-005]]; source: SRC-07; answer: Booking becomes a new user of customer data, through the Customer lookup contract CON-005 | @hl-solution-lead | 2026-11-19 |
| Q-DAT-05@INI-002 | assumed | belief: no data is used for a new purpose, because the only personal data Booking holds is the customer ID, kept with the booking it belongs to; load-bearing: yes; signpost: a channel or team asking Booking for customer data it does not hold today | @hl-solution-lead | 2026-11-19 |
| Q-DAT-02@APP-* | assumed | belief: the website, the call center desktop and the kiosks hold no customer data once their FERRYMASTER reply caches go, so they need no basis of their own; load-bearing: no; signpost: any of them caching booking or customer data again | @hl-solution-lead | 2026-11-19 |
| Q-DAT-02@APP-booking | unknown | unknown: [[#UNK-008 Review of the customer data Booking holds\|UNK-008]] | @hl-solution-lead | 2026-11-19 |
| Q-DAT-02@APP-notifications | answered | item: [[concern-data\|Data]]; source: "Notifications resolves contact details at send time from Customer identity." in [[concern-data]]; answer: Notifications keeps a record of messages sent per booking reference and state, and reads contact details from Customer identity at send time | @hl-booking-senior | 2026-11-19 |
| Q-DAT-02@APP-pricing | not-applicable | reason: Pricing holds fare rules only, per the Data concern, so it holds no customer data | @hl-pricing-senior | 2026-11-19 |
| Q-DAT-03@CON-* | assumed | belief: customer data crosses a contract only where it carries a customer ID, and every consumer is a Harborline channel or service the customer already deals with; load-bearing: no; signpost: a new consumer added to any of these contracts | @hl-solution-lead | 2026-11-19 |
| Q-DAT-03@CON-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\|UNK-006]] | @hl-solution-lead | 2026-11-19 |
| Q-DAT-04@SV-01 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: "the loyalty scheme, which reads FERRYMASTER directly and stays out of scope until INI-004" in [[03-context-and-scope]]; answer: The loyalty scheme holds the balances | @hl-solution-lead | 2026-11-19 |
| Q-PTN-01@INI-002 | answered | item: [[concern-ownership\|Ownership]]; source: "The new Booking team owns Booking, including the Ledger adapter" in [[concern-ownership]]; answer: Yes, the new Booking team owns Booking and its Ledger adapter, which writes to FERRYMASTER | @hl-solution-lead | 2026-11-19 |
| Q-PTN-02@PTY-01 | assumed | belief: the Tidepay agreement lets Booking use and pass on the payment outcomes it receives by webhook (CON-007); load-bearing: yes; signpost: Tidepay objecting to a new consumer of its payment outcomes | @hl-booking-senior | 2026-11-19 |
| Q-PTN-02@PTY-02 | assumed | belief: the vendor contract (SRC-02) lets Booking's Ledger adapter write to FERRYMASTER and pass its data on to the channels; load-bearing: yes; signpost: the vendor querying who uses the MQ transactions during the January to March 2027 pairing | @hl-solution-lead | 2026-11-19 |
| Q-PTN-03@PTY-01 | assumed | belief: the Tidepay contract renews each year on today's terms; load-bearing: no; signpost: procurement's renewal notice each autumn | @hl-solution-lead | 2026-11-19 |
| Q-PTN-03@PTY-02 | assumed | belief: Procurement holds the vendor contract, it runs to 2028 (CST-1), and INI-002 neither changes nor leaves it, so nothing is owed for leaving; load-bearing: no; signpost: the INI-005 Mainframe Exit plan needing an exit before 2028 | @hl-solution-lead | 2026-11-19 |
| Q-PTN-05@PTY-* | assumed | belief: neither agreement is assigned or changes control, because INI-002 keeps both suppliers and their contracts as they are (CST-1, CST-2); load-bearing: no; signpost: an assignment or change-of-control notice from Tidepay or the FERRYMASTER vendor | @hl-solution-lead | 2026-11-19 |
| Q-PTN-06@PTY-01 | not-applicable | reason: payment stays with Tidepay under its existing contract (CST-2), so INI-002 asks for no change to the agreement | @hl-solution-lead | 2026-11-19 |
| Q-PTN-06@PTY-02 | assumed | belief: no notice is due, because Booking works around the mainframe and never inside it (CST-1), so the vendor contract stays as it is; load-bearing: no; signpost: procurement raising the vendor contract's 2028 end date in the INI-005 plan | @hl-solution-lead | 2026-11-19 |
| Q-REG-01@INI-002 | not-applicable | reason: Booking sells single ferry crossings, and nothing is sold with another party | @hl-solution-lead | 2026-11-19 |
| Q-REG-02@INI-002 | unknown | unknown: [[#UNK-008 Review of the customer data Booking holds\|UNK-008]] | @hl-solution-lead | 2026-11-19 |
| Q-REG-05@INI-002 | not-applicable | reason: no product is shared across parties, so no party's failure reaches a customer through one | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-booking | answered | item: [[#UNK-007 Booking on-call\|UNK-007]]; source: "joins the Platform on-call rota from go-live" in [[concern-operations]]; answer: The Booking team joins the Platform on-call rota from go-live | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-call-center | assumed | belief: the Contact Center Systems team keeps supporting the desktop on today's hours, without the manual fix queue; load-bearing: no; signpost: an agent unable to get a failed booking fixed out of hours after cutover | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-notifications | answered | item: [[concern-operations\|Operations]]; source: "new consumer covered by the Platform rota" in [[concern-operations]]; answer: Covered by the Platform rota, so the same people answer for Booking and Notifications | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-kiosks | answered | item: [[concern-operations\|Operations]]; source: "Port Systems support as today" in [[concern-operations]]; answer: Port Systems supports the kiosks as it does today | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-pricing | answered | item: [[concern-operations\|Operations]]; source: "Revenue team support as today" in [[concern-operations]]; answer: The Revenue team supports Pricing as it does today | @hl-solution-lead | 2026-11-19 |
| Q-OPS-01@APP-website | answered | item: [[concern-operations\|Operations]]; source: "Digital team support as today, less one adapter" in [[concern-operations]]; answer: The Digital team supports the website as it does today, less one adapter | @hl-solution-lead | 2026-11-19 |
| Q-OPS-02@CON-001 | answered | item: [[website-runtime#When a dependency is slow or down\|Website runtime]]; source: "The website says booking is unavailable and takes no payment." in [[website-runtime]]; answer: Each channel says booking is unavailable and takes no payment, and does not fall back to the old adapter on its own | @hl-booking-senior | 2026-11-19 |
| Q-OPS-02@CON-002 | answered | item: [[notifications-runtime#When a dependency is slow or down\|Notifications runtime]]; source: "Messages arrive late and none are lost." in [[notifications-runtime]]; answer: The Event publisher keeps the events and publishes them when the bus returns, so messages arrive late and none are lost | @hl-booking-senior | 2026-11-19 |
| Q-OPS-02@CON-003 | answered | item: [[pricing-runtime#When something is slow or down\|Pricing runtime]]; source: "Booking refuses the hold or the amendment and tells the channel why." in [[pricing-runtime]]; answer: Booking refuses the hold or the amendment and tells the channel why, and does not cache fares | @hl-booking-senior | 2026-11-19 |
| Q-OPS-02@CON-004 | answered | item: [[booking-runtime#When a dependency is slow or down\|Booking runtime]]; source: "Booking refuses the hold and says which dependency failed." in [[booking-runtime]]; answer: Booking refuses the hold and says which dependency failed | @hl-booking-senior | 2026-11-19 |
| Q-OPS-02@CON-005 | answered | item: [[booking-runtime#When a dependency is slow or down\|Booking runtime]]; source: "Booking refuses the hold and says which dependency failed." in [[booking-runtime]]; answer: Booking refuses the hold and says which dependency failed | @hl-booking-senior | 2026-11-19 |
| Q-OPS-02@CON-006 | answered | item: [[ferrymaster-runtime#When it is slow or down\|Ferrymaster runtime]]; source: "the Ledger adapter keeps the hold and retries, and the customer sees" in [[ferrymaster-runtime]]; answer: The Ledger adapter keeps the hold and retries, and the customer sees "confirming" | @hl-booking-senior | 2026-11-19 |
| Q-OPS-02@CON-007 | answered | item: [[website-runtime#When a dependency is slow or down\|Website runtime]]; source: "The customer cannot pay, and the hold expires after 10 minutes." in [[website-runtime]]; answer: The customer cannot pay, and the hold expires after 10 minutes | @hl-booking-senior | 2026-11-19 |
| Q-OPS-03@INI-002 | assumed | belief: CAP-012 stays with the Revenue team, because Pricing keeps its current owner; load-bearing: no; signpost: Pricing changing hands during INI-002; covers: capability | @hl-solution-lead | 2026-11-19 |
| Q-OPS-03@CAP-013 | answered | item: [[concern-ownership\|Ownership]]; source: "The new Booking team owns Booking, including the Ledger adapter" in [[concern-ownership]]; answer: The Booking team, which owns Booking and EPC-031, the epic that delivers CAP-013 | @hl-solution-lead | 2026-11-19 |
| Q-OPS-03@CAP-014 | answered | item: [[concern-ownership\|Ownership]]; source: "The new Booking team owns Booking, including the Ledger adapter" in [[concern-ownership]]; answer: The new Booking team, which owns the Hold store | @hl-solution-lead | 2026-11-19 |
| Q-OPS-03@CAP-021 | assumed | belief: the Contact Center Systems team and the Digital team each keep their own amend and cancel screens, and the Booking team owns the change check and the ledger write; load-bearing: yes; signpost: a failed amendment that no team picks up | @hl-solution-lead | 2026-11-19 |
| Q-OPS-03@CAP-022 | answered | item: [[concern-ownership\|Ownership]]; source: "sends email or SMS on Booking state changed events" in [[CAP-022-notify-customer]]; answer: The Platform team owns Notifications, which sends the messages, and the Digital team's website stops sending booking emails | @hl-solution-lead | 2026-11-19 |
| Q-OPS-03@CAP-023 | not-applicable | reason: the capability retires with the manual fix queue, so no team owns it after INI-002 | @hl-solution-lead | 2026-11-19 |
| Q-OPS-04@INI-002 | answered | item: [[ADR-0001-one-booking-context\|ADR-0001]]; source: SRC-01; answer: Three screen adapters each decided what a booking's state is, and Booking becomes the one place that does (ADR-0001) | @hl-solution-lead | 2026-11-19 |
| Q-OPS-05@INI-002 | answered | item: [[CAP-023-fix-failed-bookings\|CAP-023]]; source: "The data warehouse feed, the finance reconciliation job and the loyalty scheme." in [[03-context-and-scope]]; answer: The three screen adapters and the manual fix queue retire. The warehouse feed, the finance job and the loyalty scheme keep reading FERRYMASTER | @hl-solution-lead | 2026-11-19 |
| Q-OPS-06@INI-002 | unknown | unknown: [[#UNK-006 Finance on Booking events\|UNK-006]] | @hl-solution-lead | 2026-11-19 |
| Q-OPS-07@INI-002 | assumed | belief: customers amend online once they can; load-bearing: yes; signpost: the online share of amendments in the first two months after go-live | @hl-solution-lead | 2026-11-19 |
| R-FIN-01 | open | question: Points are earned at reservation, so does a canceled booking take its points back, and who tells the loyalty scheme?; quote: "because points are earned at reservation" in [[04a-capability-delta]]; severity: normal | @hl-solution-lead | 2026-11-19 |
