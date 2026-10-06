---
id: unknowns-and-risks
type: index
title: Unknowns and risks
initiative: INI-900
authored: mixed
---

# Unknowns and risks

<!-- generated:unknowns-index sha=14efe937: do not edit, run planner render -->
| ID | Name | Owner | State | Ask by |
|---|---|---|---|---|
| [[#UNK-001 Till test rig\|UNK-001]] | Till test rig | @mini-qa | open | 2026-02-01 |
| [[#UNK-002 Receipt format\|UNK-002]] | Receipt format | @mini-lead | resolved |  |
| [[#R-01 One till only\|R-01]] | One till only | @mini/till-team | open |  |
<!-- /generated:unknowns-index -->

## Unknowns

### UNK-001 Till test rig

- **Question:** Is there a test till we can use?
- **Owner:** @mini-qa
- **Opened:** 2026-01-10
- **State:** open
- **Ask by:** 2026-02-01
- **Blocks:** nothing

### UNK-002 Receipt format

- **Question:** Does the receipt need a VAT line?
- **Owner:** @mini-lead
- **State:** resolved
- **Blocks:** [[shop-building-blocks#CON-001 Sale API|CON-001]]
- **Outcome:** Yes, one VAT line per receipt.
- **Resolved in:** [[2026-01-10-shop-api]]

## Risks

### R-01 One till only

- **Owner:** @mini/till-team
- **State:** open
- **Mitigation:** keep the old till for a month.

## Question ledger

| Copy | State | Evidence | By | Date |
|---|---|---|---|---|
| Q-DAT-01@INI-900 | not-applicable | reason: the shop uses no data in a new way or for a new party | @mini-lead | 2026-01-10 |
| Q-DAT-05@INI-900 | not-applicable | reason: the shop and the till keep no customer data, so none is used for a second purpose | @mini-lead | 2026-01-10 |
| Q-DAT-02@APP-* | not-applicable | reason: the shop and the till take payment at the counter and keep no customer data | @mini-lead | 2026-01-10 |
| Q-FIN-01@INI-900 | not-applicable | reason: the shop holds no value for customers | @mini-lead | 2026-01-10 |
| Q-PTN-01@INI-900 | not-applicable | reason: nothing changes owner, operator or payer | @mini-lead | 2026-01-10 |
