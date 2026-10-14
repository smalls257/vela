# Harborline example: fact sheet and writing conventions

This is the single source of truth for the mock "completed" initiative. Every page in
`examples/unified-booking/` must agree with it. It is not part of the vault.

Everything here is made up. Harborline is a fictional regional ferry operator.

## Status of the mock

- Initiative: **INI-002 Unified Booking**. Every app on the ladder has reached stage 6 (Epics) and its epics are written. Delivery is not tracked in the vault.
- Mock dates: started 2026-07-06, finished 2026-11-20. The fixture is checked with `--today 2026-11-20`.
- People are named by role only: solution lead, Booking senior, Pricing senior, QA lead, Head of Contact Center, Platform lead, mainframe team lead, Port Systems senior, Digital senior, Contact Center Systems senior.

## Why the initiative exists

- The three front ends (website, call center desktop, port kiosks) each talk to FERRYMASTER through their own screen-scraping adapter.
- When the mainframe changes a screen, all three break. That happened 11 times in the last 12 months, usually before a bank holiday.
- The call center and the kiosks cache FERRYMASTER replies differently, so they disagree about whether a booking is confirmed.
- If the website's second scrape (the confirm) fails after payment, the customer has paid for nothing. The call center fixes it by hand the next morning.

## Goals

| ID | Goal | Measure | State |
|---|---|---|---|
| G1 | Stop mainframe changes breaking booking | Adapter incidents: 11 a year → 0 | decided |
| G2 | One answer to "is it confirmed?" in every channel | No channel disagrees on booking state | decided |
| G3 | Customers amend and cancel without phoning | 60% of amendments done online within 6 months of go-live | decided |

## Constraints (not chosen by us)

- CST-1 FERRYMASTER cannot be changed. The vendor contract ends in 2028. Two people understand its COBOL.
- CST-2 Payment stays with the existing provider, Tidepay. PCI scope must not grow. Card data never enters Booking.
- CST-3 Kiosks run a locked-down image updated twice a year (March and September). Whatever they call must stay stable for at least six months.
- CST-4 The transformation program requires every new application to publish events to the Harborline event bus.
- CST-5 Mainframe processing must stay within the existing MIPS budget.

## Applications in scope (9)

| App | Page folder | Change | Owner team | Notes |
|---|---|---|---|---|
| Booking | `apps/booking/` | new | Booking team (new) | Decides held, confirmed, amended, canceled. Only thing that talks to FERRYMASTER about bookings. |
| Pricing | `apps/pricing/` | changed | Revenue team | Same job; callers narrowed from 3 front ends to Booking only. No container changes. |
| FERRYMASTER | `apps/ferrymaster/` | integrated, unchanged | Mainframe team (2 people) | 1990s mainframe ledger, ledger of record. Black box. Booking uses its existing MQ transactions BKHOLD, BKCONF, BKAMND, BKCANC. |
| Public website | `apps/website/` | changed | Digital team | Calls Booking API. Its FERRYMASTER screen adapter is retired. |
| Call center desktop | `apps/call-center/` | changed | Contact Center Systems team | Calls Booking API. Its terminal adapter is retired. Manual fix screens retired. |
| Port kiosks | `apps/kiosks/` | changed | Port Systems team | Booking API v1 client ships in the March 2027 image. Old adapter removed in the September 2027 image. Device certificates for auth. |
| Notifications | `apps/notifications/` | changed (new consumer) | Platform team | New Booking event consumer; existing email/SMS sender reused. |
| Vessel schedule | `apps/vessel-schedule/` | unchanged | Marine Ops Systems team | Booking reads capacity through the existing read API. |
| Customer identity | `apps/customer-identity/` | unchanged | Platform team | Booking looks up customers through the existing read API. |

External, not in scope: **Tidepay** (payment provider), **Harborline event bus** (Platform; production-ready since 2026-11-01).
Out of scope, still reading FERRYMASTER directly: data warehouse feed, finance reconciliation job, loyalty scheme (INI-004 and INI-005 deal with those).

Outside parties, on `03-context-and-scope.md`: PTY-01 Tidepay and PTY-02 the FERRYMASTER vendor, both suppliers. Value held for customers: SV-01 loyalty points, earned at reservation and held by the loyalty scheme, which Finance carries and INI-004 owns.

## Containers (one level in, co-designed)

- **Booking**: Booking API (requests from every channel; also receives Tidepay payment outcome), Hold store (unpaid holds for 10 minutes), Ledger adapter (only writer to FERRYMASTER via MQ; retries and keeps the hold if a write fails), Event publisher (publishes Booking state changed to the event bus). All four confirmed by the Booking senior.
- **Pricing**: Quote service, Fare rules store. No changes. Access to Quote service restricted to Booking at the Platform gateway.
- **Public website**: Booking pages (changed to call Booking API), FM screen adapter (retired).
- **Call center desktop**: Desktop client (changed: Booking API client, new amend/cancel screens), Terminal adapter (retired), Manual fix queue (retired).
- **Port kiosks**: Kiosk app (Booking API v1 client), FM adapter (retired with the September 2027 image).
- **Notifications**: Booking event consumer (new), Message sender (existing, email and SMS).
- FERRYMASTER, Vessel schedule, Customer identity: black box only.

## Contracts (each lives on the provider app's building-blocks page)

| ID | Contract | Provider | Consumers | Change policy | Tested by |
|---|---|---|---|---|---|
| CON-001 | Booking API: hold, confirm, amend, cancel, get | Booking | Website, Call center, Kiosks | Versioned. Each version kept at least 6 months (ADR-0003). | Consumer-driven contract tests, each channel; provider verification in Booking's pipeline |
| CON-002 | Booking state changed (event) | Booking | Notifications; Finance later (UNK-006) | Additive changes only | Schema check in Booking's pipeline; Notifications consumer test |
| CON-003 | Quote a fare | Pricing | Booking | Existing; callers narrowed | Contract test, Booking side; Pricing provider verification |
| CON-004 | Capacity check | Vessel schedule | Booking | Existing read API, no change | Contract test, Booking side |
| CON-005 | Customer lookup | Customer identity | Booking | Existing read API, no change | Contract test, Booking side |
| CON-006 | Ledger transactions (BKHOLD, BKCONF, BKAMND, BKCANC over MQ) | FERRYMASTER | Booking (Ledger adapter) | FERRYMASTER cannot change; mainframe team announces any MQ change 8 weeks ahead | Ledger simulator in Booking's contract tests; one weekly end-to-end run against the FERRYMASTER test region |
| CON-007 | Payment outcome (webhook) | Tidepay | Booking | Tidepay's published API; versioned by Tidepay | Tidepay sandbox in Booking's pipeline |

Booking hold expires after 10 minutes. Ledger write latency p95 is 2.1 s (measured, UNK-001).

## Capabilities (shared model, `capabilities/`)

| ID | File | Capability | Domain | Change in INI-002 | Today | After |
|---|---|---|---|---|---|---|
| CAP-011 | `CAP-011-find-a-crossing.md` | Find a crossing | Sell | unchanged | Website, Call center, Kiosks + Vessel schedule | same |
| CAP-012 | `CAP-012-quote-a-fare.md` | Quote a fare | Sell | narrow | Pricing, 3 callers | Pricing, called by Booking only |
| CAP-013 | `CAP-013-reserve-a-crossing.md` | Reserve a crossing | Sell | replace | 3 front-end adapters into FERRYMASTER | Booking |
| CAP-014 | `CAP-014-hold-a-seat.md` | Hold a seat during payment | Sell | new | nothing; overbooking fixed by hand | Booking, 10-minute hold |
| CAP-015 | `CAP-015-take-payment.md` | Take payment | Sell | unchanged | Tidepay via each front end | Tidepay; outcome reported to Booking |
| CAP-021 | `CAP-021-amend-or-cancel.md` | Amend or cancel a booking | Serve | extend | Call center only, via mainframe screen | Booking, used by website and call center; kiosks show state only |
| CAP-022 | `CAP-022-notify-customer.md` | Notify customer of changes | Serve | new | website emails only | Notifications, triggered by Booking events |
| CAP-023 | `CAP-023-fix-failed-bookings.md` | Fix failed bookings by hand | Serve | retire | call center next-morning fixes | nobody: Booking retries and keeps the hold |

Overlap: INI-004 Loyalty Revamp also touches CAP-013. INI-005 Mainframe Exit touches everything that writes to FERRYMASTER.

## Flows (`flows/`)

- `FLO-001-hold-pay-confirm.md`: Find a crossing → Hold a seat → Take payment → Confirm booking → Notify customer.
- `FLO-002-amend-or-cancel.md`: Find booking → Check change allowed → Re-quote (amend) → Write to ledger → Notify customer.
- `FLO-003-notify-on-change.md`: Booking state changes → Event published → Notifications decides channel → Message sent.

## Decisions (`decisions/`)

- `ADR-0001-one-booking-context.md`: One Booking application rather than a shared adapter library. The library was quicker but would have left three teams each deciding what "confirmed" means.
- `ADR-0002-ferrymaster-ledger-of-record.md`: FERRYMASTER stays the ledger of record. Booking holds state, not truth.
- `ADR-0003-versioned-booking-api.md`: Version the Booking API; keep each version at least 6 months because of the kiosk image cycle.
- `ADR-0004-mq-not-screen-scraping.md`: Use FERRYMASTER's existing MQ transactions, not screen scraping. Found in Discover on 2026-07-14: the mainframe team already exposes them for the finance job. Decided in the Grill on 2026-07-28.

## Unknowns and risks

| ID | Question | Outcome | State |
|---|---|---|---|
| UNK-001 | Is ledger write latency good enough for hold-pay-confirm? | Measured p95 2.1 s. Customer sees "confirming" with retry. Fine. | resolved 2026-09-02 |
| UNK-002 | How do we get repeatable test data when the FERRYMASTER test region refreshes yearly? | Booking team builds a ledger simulator for contract tests; weekly end-to-end against the test region. | resolved 2026-09-16 |
| UNK-003 | Does the mainframe team have capacity in Q1? | Yes: 2 days a week, January to March 2027. | resolved 2026-08-14 |
| UNK-004 | How do kiosks authenticate? They have no user. | Device certificates from Platform's existing PKI. | resolved 2026-09-23 |
| UNK-005 | Is the event bus production-ready? | Yes, since 2026-11-01. | resolved 2026-11-03 |
| UNK-006 | Should Finance reconciliation read Booking events instead of FERRYMASTER? | Deferred to INI-005. Not blocking. | open, owner: Platform lead, ask by 2027-03-01 |
| UNK-007 | Who is on call for Booking? | Booking team joins the Platform on-call rota from go-live. | resolved 2026-10-07 |

Risks: R-01 mainframe knowledge sits with two people (mitigation: MQ mapping documented in CON-006, pairing in Q1). R-02 if the March kiosk image slips, kiosks wait six months for the next one (mitigation: kiosks keep their old adapter until their cutover; API v1 kept 6+ months).

## Question ledger (catalog v1)

The ledger on `11-unknowns-and-risks.md` disposes every one of the 57 copies catalog v1 owes, so `planner check --gate epics` passes. Its rows show every state. Who pays Booking's running cost (Q-FIN-02) was asked of the finance business partner on 2026-11-19 and has no answer yet. That customers amend online once they can (Q-OPS-07) is a load-bearing assumption, with the online share of amendments as its signpost. Pricing is an exception to the data question, because it holds fare rules only. Where the vault does not say (lawful basis for customer data, who owns each capability, who runs unchanged apps out of hours) the row is an assumption with a signpost, never an answer. One reviewer question, R-FIN-01, on points and canceled bookings, is open.

## Concerns (all eight addressed or N/A)

- Testing: consumer-driven contract tests on every Booking boundary; end-to-end only for hold-pay-confirm and amend-or-cancel; ledger simulator. Owner: QA lead.
- Security: no new PCI scope (Tidepay hosted payment page); kiosk device certificates; Booking API behind the Platform gateway with service tokens. Owner: Platform lead.
- Data: FERRYMASTER is the ledger of record (ADR-0002). Booking stores holds for 10 minutes and a booking-state cache keyed by booking reference; no card data; personal data limited to customer ID. Owner: solution lead.
- Rollout: website first (Feb 2027), call center second (Mar 2027), kiosks with the March 2027 image. Each channel keeps its old adapter behind a switch for 4 weeks after cutover, then it is removed. Rollback = flip the channel's switch back. Owner: solution lead.
- Operations: Booking joins the Platform on-call rota; runbooks for ledger-write failures and hold-store outage. Owner: Booking senior.
- Observability: per-channel request and error rate; booking state transitions; ledger write latency p95; hold expiry rate; one trace ID from channel to ledger adapter. Owner: Booking senior.
- Ownership: each app keeps its owner; Booking team owns Booking and the ledger adapter; front-end teams own their Booking API clients. Owner: solution lead.
- Cost: addressed. Standard service footprint, no new licenses, MQ use within the existing MIPS budget (checked with the mainframe team lead). Owner: solution lead.

## Epics (`13-epics/`)

| ID | File | Epic | Owning app/team | Delivers |
|---|---|---|---|---|
| EPC-031 | `EPC-031-holds-and-confirms.md` | Booking holds and confirms crossings | Booking | CAP-013, CAP-014; CON-001, CON-007 |
| EPC-032 | `EPC-032-ledger-adapter.md` | Ledger adapter on FERRYMASTER's MQ transactions | Booking (+ mainframe team support) | CON-006; ADR-0004 |
| EPC-033 | `EPC-033-website-to-booking.md` | Website moves to Booking | Digital | CAP-013 (website); retires FM screen adapter |
| EPC-034 | `EPC-034-call-center-to-booking.md` | Call center moves to Booking | Contact Center Systems | CAP-013, CAP-021 (call center); retires CAP-023 |
| EPC-035 | `EPC-035-kiosks-to-booking.md` | Kiosks move to Booking in the March image | Port Systems | CAP-013 (kiosks); ADR-0003; device certs |
| EPC-036 | `EPC-036-amend-cancel-online.md` | Amend and cancel online | Booking + Digital | CAP-021; G3 |
| EPC-037 | `EPC-037-events-and-notifications.md` | Booking events and customer notifications | Booking + Platform | CAP-022; CON-002 |
| EPC-038 | `EPC-038-pricing-serves-booking.md` | Pricing serves Booking only | Revenue | CAP-012; CON-003 |
| EPC-039 | `EPC-039-run-booking.md` | Run Booking: on-call, runbooks, dashboards | Booking | Operations and observability concerns |

## Full file list (links must resolve to these basenames)

The vault root is the initiative: `examples/unified-booking/`.

```
README.md
01-goals.md  02-constraints.md  03-context-and-scope.md  04-solution-strategy.md  04a-capability-delta.md
05-building-blocks/05-building-blocks.md  +  <app>-building-blocks.md for each of the 9 apps
06-runtime/06-flows.md  +  flows/FLO-001..003  +  apps/<app>-runtime.md for the 7 apps that are not unchanged
08-concerns/08-concerns.md  +  concern-*.md (8)
09-decisions/09-decisions.md  +  ADR-0001..0004
11-unknowns-and-risks.md  12-glossary.md
13-epics/13-epics.md  +  EPC-031..039
sources.md  +  sessions/ (one record per deciding Grill)
capabilities/CAP-011..023 (8)
```

## Page conventions

The vault format lives in `template/CONVENTIONS.md`, and the fixture carries a byte-identical copy. This file keeps the facts and the house voice.

## Voice (house voice)

Write the way a senior engineer explains something to a peer they respect:
- Plain words, short sentences, active voice. Say what happens and why.
- Concrete over abstract: name the system, the number, the date.
- No filler or hype: never "robust", "seamless", "leverage", "delve", "crucial", "comprehensive", "ensure", "streamline", "it's worth noting", "in order to".
- No em-dash asides, no "not X, but Y" constructions, no rhetorical questions, no closing summaries that repeat the page.
- Tables for facts, prose for reasons. If a sentence explains nothing, cut it.

Example passage in the house voice:

> Harborline sells crossings through three front ends. Each one talks to FERRYMASTER through its own screen-scraping adapter, so when the mainframe changes a screen, all three break. That happened eleven times last year, usually just before a bank holiday weekend.
