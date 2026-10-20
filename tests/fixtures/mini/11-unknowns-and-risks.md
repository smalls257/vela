---
id: unknowns-and-risks
type: index
title: Unknowns and risks
initiative: INI-900
authored: mixed
---

# Unknowns and risks

<!-- generated:unknowns-index sha=1ce543ee: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

**Questions**

| Question | Who answers | Status | Answer needed by |
|---|---|---|---|
| [[#UNK-001 Till test rig\|Till test rig (UNK-001)]] | @mini-qa | open | 2026-02-01 |
| [[#UNK-002 Receipt format\|Receipt format (UNK-002)]] | @mini-lead | answered |  |

**Risks**

| Risk | Owner | Status |
|---|---|---|
| [[#R-01 One till only\|One till only (R-01)]] | @mini/till-team | open |
<!-- /generated:unknowns-index -->

## Unknowns

### UNK-001 Till test rig

- **Question:** Is there a test till we can use?
- **Owner:** @mini-qa
- **Opened:** 2026-01-10
- **State:** open
- **Ask by:** 2026-02-01

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
| Q-DAT-05@INI-900 | not-applicable | reason: this vault records no customer data held or used, so none is recorded as used for a second purpose | @mini-lead | 2026-01-10 |
| Q-DAT-02@APP-* | not-applicable | reason: this vault records no customer data held by the shop or the till | @mini-lead | 2026-01-10 |
| Q-FIN-01@INI-900 | not-applicable | reason: the shop holds no value for customers | @mini-lead | 2026-01-10 |
| Q-PTN-01@INI-900 | not-applicable | reason: nothing changes owner, operator or payer | @mini-lead | 2026-01-10 |
