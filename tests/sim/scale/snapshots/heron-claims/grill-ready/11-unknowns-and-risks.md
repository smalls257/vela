---
id: unknowns-and-risks
type: index
title: Unknowns and risks
arc42: "§11"
authored: mixed
---

# Unknowns and risks

Three questions hold up the requirements for claiming an expense: whether [[#UNK-001 The flat meal allowance and tax|the flat meal allowance can be paid as an expense]], [[#UNK-002 How UK claims are paid|how UK claims are paid within five days]], and whether [[#UNK-003 Cost centers in two systems|the cost centers in the two systems match]]. Each is with Finance Operations. No risks are recorded yet.

<!-- generated:unknowns-index sha=086987af: do not edit, run vela render -->
**Questions**

| Question | Who answers | Status | Answer needed by |
|---|---|---|---|
| [[#UNK-001 The flat meal allowance and tax\|The flat meal allowance and tax (UNK-001)]] | @fin-ops | open | 2026-10-30 |
| [[#UNK-002 How UK claims are paid\|How UK claims are paid (UNK-002)]] | @fin-ops | open | 2026-10-30 |
| [[#UNK-003 Cost centers in two systems\|Cost centers in two systems (UNK-003)]] | @fin-ops | open | 2026-10-30 |
<!-- /generated:unknowns-index -->

## Unknowns

### UNK-001 The flat meal allowance and tax

Nobody knows whether the flat overnight meal allowance the partners agreed can be paid as an expense, or whether some of it counts as pay. Until it is known, the meal allowance requirement can't be settled.

- **Question:** Can the flat overnight meal allowance be paid through claims as it stands, or does part of it have to go through pay?
- **Owner:** @fin-ops
- **State:** open
- **Blocks:** [[CAP-001-claim-an-expense#CAP-001.FR9 Overnight meal allowance|the overnight meal allowance]]
- **Ask by:** 2026-10-30
- **Opened:** 2026-10-12

### UNK-002 How UK claims are paid

UK claims are paid with salary today. Nobody knows how an approved claim reaches a UK bank account within five working days instead.

- **Question:** How is an approved UK claim paid within five working days, when claims are paid with salary today?
- **Owner:** @fin-ops
- **State:** open
- **Blocks:** [[CAP-001-claim-an-expense#CAP-001.FR10 When a claim is paid|when a claim is paid]]
- **Ask by:** 2026-10-30
- **Opened:** 2026-10-12

### UNK-003 Cost centers in two systems

Cost centers come from the human resources system every night, and nobody has checked that they match the general ledger's. A split line booked to a cost center the ledger doesn't know would fail at export.

- **Question:** Do the human resources system's cost centers match the general ledger's, and who keeps them matched?
- **Owner:** @fin-ops
- **State:** open
- **Blocks:** [[CAP-001-claim-an-expense#CAP-001.FR11 Split a claim across cost centers|splitting a claim across cost centers]]
- **Ask by:** 2026-10-30
- **Opened:** 2026-10-12

## Risks

## Question ledger
