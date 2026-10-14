---
id: context-and-scope
type: initiative-section
title: Context and scope
arc42: "§3"
state: assumption
owner: "@solution-lead"
authored: mixed
sources: [SRC-01, SRC-02, SRC-04, SRC-05]
---

# Context and scope

Each bullet below carries its own state word and source. The page state is the weakest of them, because the rail side and the CIO's wishes come from documents that describe intent.

## Today

### Ferry side today

Harborline, from its IT operations systems list. Each bullet is a `fact`, source SRC-02.

- **SeaBook** (fact, SRC-02): the web booking engine. It has an availability target of 99.9% from May to September and is on call round the clock.
- **FERRYMASTER** (fact, SRC-02): a mainframe reservation system, and the ledger of record.
- **FERRYMASTER contract notice** (fact, SRC-02): the vendor contract needs 18 months' notice. Its end date is disputed, so it is held in [[11-unknowns-and-risks#UNK-021 FERRYMASTER contract end date|UNK-021]] and not stated here.
- **Halyard CRM** (fact, SRC-02): used by the Kestrel Bay contact center.
- **Tidepay** (fact, SRC-02): takes card payments for the web, the contact center and the port kiosks.
- **Tidemiles** (fact, SRC-02): the ferry loyalty scheme, 1 point per pound spent, and 100 points redeem for 1 pound. See [[#SV-01 Tidemiles]].
- **Customer database** (fact, SRC-02): about 1.2 million records. Its owner is to be confirmed after the reorganization: [[11-unknowns-and-risks#UNK-016 Ferry customer DB owner|UNK-016]].
- **Partner hotel feed** (fact, SRC-02): a nightly file of package bookings goes to about 40 partner hotels. See [[#PTY-01 Partner hotels]].

### Rail side today

Northway Rail, from a target-architecture slide. Each bullet is an `assumption`, source SRC-04, because the slide is a plan and not a record of what runs.

- **RailCore** (assumption, SRC-04): the booking engine, hosted by its vendor. The vendor SLA is 99.5%, and support runs 08:00 to 18:00 on weekdays. See [[#PTY-03 RailCore vendor]].
- **Northway ID** (assumption, SRC-04): the login for every rail customer, and emails are unique.
- **Signal CRM** (assumption, SRC-04): used in the Dunmere contact center.
- **Northway Plus** (assumption, SRC-04): the rail loyalty scheme, 5 points per pound spent. See [[#SV-02 Northway Plus]].
- **Northway Assist** (assumption, SRC-04): handles assisted travel bookings.
- **Payments** (assumption, SRC-04): through the RailCore gateway today, with a move to Tidepay planned for 2027.

The slide points to a capability map in an appendix that has not been read: [[11-unknowns-and-risks#UNK-023 Rail capability map appendix|UNK-023]].

### What Sarah Chen has said

Sarah Chen, named second-hand as the Data Protection Officer ([[11-unknowns-and-risks#UNK-010 Data Protection Officer|UNK-010]]), from the solution lead's own account of a phone call (SRC-05), which the lead dates Friday 2026-10-07. The calendar shows that date as a Wednesday, and the lead knows it does not add up and asked for it as given. It is recalled, not recorded or written, and she has not said herself that she holds the role. Each bullet records what she said to the lead, not an approval.

- **Household** (fact, SRC-05): she told the lead that one household per shared email, where people link their own accounts, works, and that she needs to see it in the design.
- **Matching** (fact, SRC-05): she asked to be shown how the right person is matched when an email is shared, where consent is collected, and what happens if the match is wrong.
- **Asking families who is who** (fact, SRC-05): she told the lead it is allowed if consent covers it, meaning the family is shown what data is being linked and agrees. She wants that in the design too.
- **Loyalty view** (fact, SRC-05): she wants to see the loyalty view separately, with what data it holds and who sees it, and said it is not the same as the household.
- **Who writes the matching design** (fact, SRC-05): she told the lead that is not her concern, and that whoever builds the design owns it. She did not say who that is: [[11-unknowns-and-risks#UNK-036 Who writes the matching design|UNK-036]].
- **When she reviews** (assumption, SRC-05): she wants to see the design two weeks before go-live. No go-live date is set: [[11-unknowns-and-risks#UNK-002 Meaning of next summer|UNK-002]].

## After

What the CIO has asked for. Each bullet is an `assumption`, source SRC-01, because the memo states intent.

- **One identity** (assumption, SRC-01): Northway ID becomes the single identity for every group customer by next summer. What that means is open: [[11-unknowns-and-risks#UNK-001 Meaning of the mandate|UNK-001]].
- **One loyalty scheme** (assumption, SRC-01): Tidemiles and Northway Plus are combined. The marketing draft that promises one-for-one points is not recorded here: [[11-unknowns-and-risks#UNK-022 Loyalty points one for one|UNK-022]].

<!-- generated:system-context sha=140bedbf: do not edit, run vela render -->
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
- **Agreements:** the FERRYMASTER vendor contract, with 18 months' notice (SRC-02). Its end date is in [[11-unknowns-and-risks#UNK-021 FERRYMASTER contract end date|UNK-021]].

### PTY-03 RailCore vendor

- **Relationship:** supplier
- **Agreements:** a vendor SLA for RailCore (SRC-04, assumption), and no other agreement known.

## Value held for customers

### SV-01 Tidemiles

- **Holder:** not recorded: SRC-02 names Tidemiles as a ferry scheme but not which system keeps the balances
- **Owner:** not known yet: [[11-unknowns-and-risks#UNK-022 Loyalty points one for one|UNK-022]]

### SV-02 Northway Plus

- **Holder:** not recorded: SRC-04 names Northway Plus as a rail scheme but not which system keeps the balances
- **Owner:** not known yet: [[11-unknowns-and-risks#UNK-022 Loyalty points one for one|UNK-022]]
