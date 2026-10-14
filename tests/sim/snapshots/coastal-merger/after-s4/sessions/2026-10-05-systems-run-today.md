---
id: 2026-10-05-systems-run-today
type: session
title: "Discover: systems run today"
date: 2026-10-05
modes: [discover, dump]
status: closed
summary: "Systems today: 11 facts from the Harborline list, the Northway slide and the lead, plus unknowns on the FERRYMASTER end date and mainframe cover."
---

# 2026-10-05 Discover: systems run today

## Captures

- [fact] (claude, from SRC-01) SeaBook is the web booking engine, 99.9% availability target May to September, 24/7 on-call. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c01
- [fact] (claude, from SRC-01) FERRYMASTER is the mainframe reservation system and ledger of record, vendor contract to March 2029, 18-month notice. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c02
- [fact] (claude, from SRC-01) Halyard CRM serves the Kestrel Bay contact center. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c03
- [fact] (claude, from SRC-01) Tidepay takes card payments for web, contact center and port kiosks. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c04
- [fact] (claude, from SRC-01) Tidemiles loyalty earns 1 point per pound and 100 points redeem for 1 pound. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c05
- [fact] (claude, from SRC-01) The customer database holds about 1.2 million records, owner not confirmed after the reorganization. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c06
- [fact] (claude, from SRC-02) Northway ID is the login for every rail customer, emails unique. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c07
- [fact] (claude, from SRC-02) Northway Plus loyalty earns 5 points per pound, Northway Assist handles assisted travel bookings. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c08
- [fact] (claude, from SRC-02) Rail payments go through the RailCore gateway today. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c09
- [unknown] (solution lead) "I've heard December 2027, SRC-01 says March 2029" for the FERRYMASTER end. → keep: [[11-unknowns-and-risks#UNK-008 FERRYMASTER end date|UNK-008]] (unknown) ^c10
- [unknown] (solution lead) The ferry customer database owner needs recording. → keep: [[11-unknowns-and-risks#UNK-003 Ferry customer data owner|UNK-003]] (unknown) ^c11
- [thought] (solution lead) "it's all silos as expected, ferry mainframe with two people, rail externally hosted" → drop: covered by the facts already written (^c14, SRC-02) ^c12
- [thought] (solution lead) "Honestly not sure there's anything else to discover here until the CIO answers on the 19th about what 'one account' actually means. That's what changes everything." → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c13
- [fact] (solution lead, first-hand) Two people run the FERRYMASTER mainframe. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c14
- [unknown] (solution lead) "If we lose either of them before April, we're locked out of FERRYMASTER, and that's game over given the freeze." → keep: [[11-unknowns-and-risks#UNK-009 Mainframe key-person cover|UNK-009]] (unknown) ^c15
- [fact] (solution lead, first-hand) The two FERRYMASTER mainframe people have no cover. "zero cover—I checked with the ops guys weeks ago and they said don't ask." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c16
- [thought] (solution lead) "Move the ask-by to this week, not November. Ferry Ops director needs to know this is a blocker and we need an answer before the CIO even defines one account." → keep: [[11-unknowns-and-risks#UNK-009 Mainframe key-person cover|UNK-009]] (unknown) ^c17

## Changes

| ID | From | To | Source |
|---|---|---|---|
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c01]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c02]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c03]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c04]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c05]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c06]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c07]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c08]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c09]] |
| UNK-008 | - | open | [[2026-10-05-systems-run-today#^c10]] |
| UNK-003 | open | open | [[2026-10-05-systems-run-today#^c11]] |
| context-and-scope | - | fact | [[2026-10-05-systems-run-today#^c14]] |
| UNK-009 | - | open | [[2026-10-05-systems-run-today#^c15]] |
| context-and-scope | fact | fact | [[2026-10-05-systems-run-today#^c16]] |
| UNK-009 | open | open | [[2026-10-05-systems-run-today#^c17]] |
| UNK-001 | open | open | [[2026-10-05-systems-run-today#^c13]] |
