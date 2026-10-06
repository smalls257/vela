---
id: context-and-scope
type: initiative-section
title: Context and scope
arc42: "§3"
state: inkling
owner: "@solution-lead"
authored: mixed
sources: [SRC-01, SRC-02, SRC-03, SRC-04]
---

# Context and scope

## Today

- **Systems:** Ferry runs SeaBook and FERRYMASTER and rail runs RailCore, with separate customer databases and logins. Inkling, [[2026-10-06-one-customer-mandate#^c11]]. See [[11-unknowns-and-risks#UNK-016 What each system does|UNK-016]].
- **Loyalty:** Tidemiles is on the ferry side and Northway Plus on the rail side. Which system holds the balances is not known. Inkling, [[2026-10-06-one-customer-mandate#^c58]]. See [[11-unknowns-and-risks#UNK-018 Loyalty balance holder|UNK-018]].
- **Companies:** Kestrel Bay and Dunmere merged three months ago, and ferry and rail operations are still separate. Inkling, [[2026-10-06-one-customer-mandate#^c20]]. See [[11-unknowns-and-risks#UNK-017 Kestrel Bay and Dunmere|UNK-017]].
- **Ferry booking:** SeaBook is the web booking engine, with an availability target for May to September and round-the-clock on-call. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c01]].
- **FERRYMASTER:** a mainframe reservation system and the ledger of record. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c02]]. Its contract end date is in dispute, see [[11-unknowns-and-risks#UNK-019 FERRYMASTER contract end|UNK-019]].
- **Ferry contact centre:** Halyard CRM is used by the Kestrel Bay contact centre. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c03]]. The rail side runs a different CRM, Signal, see below, [[2026-10-06-what-two-companies-run#^c13]].
- **Ferry payments:** Tidepay takes card payments for web, the contact centre and port kiosks. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c04]].
- **Tidemiles:** loyalty scheme earning 1 point per pound, with 100 points redeeming for 1 pound. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c05]]. See [[#SV-01 Tidemiles|SV-01]].
- **Customer database:** about 1.2 million records. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c06]]. Who owns it after the reorganisation is not known, see [[11-unknowns-and-risks#UNK-022 Customer database owner|UNK-022]].
- **Partner hotel feed:** a nightly file of package bookings goes to about 40 partner hotels. Fact, SRC-02, [[2026-10-06-what-two-companies-run#^c07]]. See [[#PTY-01 Partner hotels|PTY-01]].
- **Rail booking:** RailCore is the booking engine, hosted by its vendor, with a vendor service level and support on weekdays in office hours. Assumption, SRC-04 (a slide), [[2026-10-06-what-two-companies-run#^c11]]. How this fits SeaBook's round-the-clock cover is in [[11-unknowns-and-risks#UNK-021 Service levels across ferry and rail|UNK-021]]. See [[#PTY-03 RailCore vendor|PTY-03]].
- **Rail identity:** Northway ID is used for every customer login, and emails are unique. Assumption, SRC-04, [[2026-10-06-what-two-companies-run#^c12]].
- **Rail contact centre:** Signal CRM runs in the Dunmere contact centre. Assumption, SRC-04, [[2026-10-06-what-two-companies-run#^c13]].
- **Northway Plus:** rail loyalty scheme earning 5 points per pound. Assumption, SRC-04, [[2026-10-06-what-two-companies-run#^c14]]. See [[#SV-02 Northway Plus|SV-02]].
- **Assisted travel:** Northway Assist handles assisted travel bookings. Assumption, SRC-04, [[2026-10-06-what-two-companies-run#^c15]].
- **Rail payments:** RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027. Assumption, SRC-04, [[2026-10-06-what-two-companies-run#^c16]].
- **Planned: one identity:** Northway ID becomes the single identity for every customer of the group. Assumption, SRC-01, [[2026-10-06-what-two-companies-run#^c08]].
- **Planned: FERRYMASTER:** nothing new should be built on it. Assumption, SRC-01, [[2026-10-06-customer-identity-ferry-rail#^c01]]. The retirement date is in dispute, see [[11-unknowns-and-risks#UNK-019 FERRYMASTER contract end|UNK-019]].
- **Planned: loyalty:** Tidemiles and Northway Plus are combined, one for one into a single balance. Assumption, SRC-01 and SRC-03, [[2026-10-06-what-two-companies-run#^c09]] and [[2026-10-06-what-two-companies-run#^c17]]. The differing earning rates make one for one doubtful, see [[11-unknowns-and-risks#UNK-020 Loyalty combining rates|UNK-020]].
- **Planned: date:** all of this is due by next summer. Assumption, SRC-01 and SRC-03, [[2026-10-06-what-two-companies-run#^c10]]. See [[11-unknowns-and-risks#UNK-004 Next summer date|UNK-004]].

## After

<!-- generated:system-context sha=140bedbf: do not edit, run planner render -->
none
<!-- /generated:system-context -->

## In scope

## Out of scope

## Outside parties

### PTY-01 Partner hotels

- **Relationship:** partner
- **Agreements:** none known

### PTY-02 FERRYMASTER vendor

- **Relationship:** supplier
- **Agreements:** the FERRYMASTER vendor contract. Its end date and notice period are in dispute, see [[11-unknowns-and-risks#UNK-019 FERRYMASTER contract end|UNK-019]] (SRC-02, SRC-01).

### PTY-03 RailCore vendor

- **Relationship:** supplier
- **Agreements:** the RailCore vendor service level (SRC-04).

## Value held for customers

### SV-01 Tidemiles

- **Holder:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder|UNK-018]]
- **Owner:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder|UNK-018]]

### SV-02 Northway Plus

- **Holder:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder|UNK-018]]
- **Owner:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder|UNK-018]]
