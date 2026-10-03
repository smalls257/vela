---
id: session-history
type: index
title: Session history
initiative: INI-002
state: handed-off
owner: solution lead
authored: generated
last_verified: 2026-11-20
sources: ["session log 2026-07-06 to 2026-11-18"]
---

# Session history

Every working session on Unified Booking, oldest first. Each row is written when the session closes.

<!-- generated: do not edit -->
| Date | Mode | Area | What changed | Items promoted |
|---|---|---|---|---|
| 2026-07-06 | Dump & Diverge | Whole initiative | Raw dump of the pain: three screen adapters, 11 breakages in 12 months, paid-for-nothing bookings fixed the next morning. | G1, G2, G3 (inkling) |
| 2026-07-09 | Discover | Baseline and constraints | Mapped the 9 apps, today's adapters and the five constraints. Found the data warehouse feed, finance job and loyalty scheme also read FERRYMASTER; put them out of scope. | C1 to C5; context diagram |
| 2026-07-14 | Discover | FERRYMASTER | Mainframe team lead showed the MQ transactions already exposed for the finance job. | ADR-0004; CON-006 (draft); UNK-003 (owner: solution lead) |
| 2026-07-14 | Shape | Capabilities | Proposed the capability set and the delta for INI-002. No official capability map exists yet. | CAP-011 to CAP-023; capability delta |
| 2026-07-28 | Shape | Boundaries | Drew the boundary between Booking and each channel, and which app provides each contract. | CON-001, CON-002, CON-003, CON-007 (draft) |
| 2026-07-28 | Grill | Solution strategy | Chose one Booking application over a shared adapter library. Each app keeps its owner. | ADR-0001; Ownership concern |
| 2026-08-12 | Grill | Goals and data | Put numbers on the goals. FERRYMASTER stays the ledger of record; Booking holds state only. Unpaid seats are held for 10 minutes. | G1, G2, G3 (decided); ADR-0002; 10-minute hold; Data concern |
| 2026-08-14 | Grill | Mainframe capacity | Mainframe team confirmed 2 days a week, January to March 2027, and checked MQ use against the MIPS budget. | UNK-003 resolved; R-01; Cost concern |
| 2026-08-19 | Probe | Ledger writes | Timed MQ writes against the FERRYMASTER test region and found the region refreshes yearly. | UNK-001 (owner: Booking senior), UNK-002 (owner: QA lead) |
| 2026-08-26 | Grill | Kiosks and rollout | Kiosk image cycle forces a stable API for six months. Set the channel order and the 4-week switch. | ADR-0003; UNK-004 (owner: Port Systems senior); R-02; Rollout concern |
| 2026-09-02 | Grill | Hold-pay-confirm | p95 of 2.1 s accepted: the customer sees "confirming" while Booking retries. | UNK-001 resolved; FLO-001; Observability concern |
| 2026-09-09 | Grill | Building blocks | Booking senior confirmed all four Booking containers. | Booking containers (decided) |
| 2026-09-30 | Shape | Channel containers | Co-designed the website, call centre and kiosk containers with the Digital, Contact Centre Systems and Port Systems seniors. | Channel containers (decided) |
| 2026-09-16 | Grill | Testing and amend | Ledger simulator for contract tests, weekly end-to-end against the test region. Amend-or-cancel flow agreed. | UNK-002 resolved; FLO-002; Testing concern |
| 2026-09-23 | Grill | Security | Kiosks use device certificates from Platform's existing PKI. | UNK-004 resolved; Security concern |
| 2026-10-07 | Grill | Concerns | Went through all eight concerns. Booking joins the Platform on-call rota. | UNK-007 resolved; Operations concern; all concerns addressed |
| 2026-10-14 | Shape | Pricing and Notifications containers | Co-designed with the Pricing senior and Platform lead: Pricing unchanged behind the gateway, new Booking event consumer in Notifications. | Pricing and Notifications containers (decided); UNK-005 (owner: Platform lead) |
| 2026-10-21 | Shape | Epics | Cut the work into nine epics with one owning team each. | EPC-031 to EPC-039 (draft) |
| 2026-11-03 | Grill | Events | Platform lead confirmed the event bus production-ready since 2026-11-01. | UNK-005 resolved; FLO-003 |
| 2026-11-18 | Grill | Epics | Tightened acceptance criteria to the boundary. Kiosks show booking state only. Deferred finance reading events to INI-005. Exported to Jira. | EPC-031 to EPC-039 (decided); HB-101 to HB-109; UNK-006 deferred (owner: Platform lead) |
<!-- /generated -->
