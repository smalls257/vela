---
id: 2026-10-12-claim-requirements
type: session
title: "Shape: the requirements for claiming an expense"
date: 2026-10-12
modes: [shape]
status: closed
summary: Wrote CAP-001's eleven requirements at assumption, each with the options weighed and the one picked, and opened UNK-001 to UNK-003.
---

# 2026-10-12 Shape: the requirements for claiming an expense

## Captures

- [thought] (@sim-lead) "Photo in the app. One way in." the receipt is a photo taken in the app; forwarding email receipts was weighed and set aside → keep: [[CAP-001-claim-an-expense#CAP-001.FR1 Hand in a receipt|CAP-001.FR1]] (assumption) ^c01
- [thought] (@sim-lead) "Let them type the miles." mileage is typed with its purpose; a route calculator was weighed and set aside → keep: [[CAP-001-claim-an-expense#CAP-001.FR2 Claim mileage|CAP-001.FR2]] (assumption) ^c02
- [thought] (@sim-lead) "Claim in what you paid, convert at the card rate." each line is claimed in the currency paid and converted at the card rate → keep: [[CAP-001-claim-an-expense#CAP-001.FR3 Claim in the currency paid|CAP-001.FR3]] (assumption) ^c03
- [thought] (@sim-lead) "The line manager, they know if the trip happened." the line manager approves each claim → keep: [[CAP-001-claim-an-expense#CAP-001.FR4 The line manager approves|CAP-001.FR4]] (assumption) ^c04
- [thought] (@sim-lead) "Over 500 goes to Finance as well." a claim over 500 pounds needs a second approval by Finance Operations → keep: [[CAP-001-claim-an-expense#CAP-001.FR5 A second approval for large claims|CAP-001.FR5]] (assumption) ^c05
- [thought] (@sim-lead) "Warn at 60, refuse at 90." a line over 60 days old gets a warning and one over 90 is refused → keep: [[CAP-001-claim-an-expense#CAP-001.FR6 Late claims|CAP-001.FR6]] (assumption) ^c06
- [thought] (@sim-lead) "Send it back with a comment." an approver sends a wrong claim back with a comment → keep: [[CAP-001-claim-an-expense#CAP-001.FR7 Send a claim back|CAP-001.FR7]] (assumption) ^c07
- [thought] (@sim-lead) "Tell them every time it moves." the person sees each claim's step and gets a message when it moves → keep: [[CAP-001-claim-an-expense#CAP-001.FR8 Where my claim is|CAP-001.FR8]] (assumption) ^c08
- [thought] (@sim-lead) "The flat rate is what the partners agreed." the overnight meal allowance is a flat daily rate with no receipt → keep: [[CAP-001-claim-an-expense#CAP-001.FR9 Overnight meal allowance|CAP-001.FR9]] (assumption) ^c09
- [thought] (@sim-lead) "Five working days, that's the mandate." an approved claim is paid within five working days → keep: [[CAP-001-claim-an-expense#CAP-001.FR10 When a claim is paid|CAP-001.FR10]] (assumption) ^c10
- [thought] (@sim-lead) "Split by percentage." a claim line can be split across cost centers by percentage → keep: [[CAP-001-claim-an-expense#CAP-001.FR11 Split a claim across cost centers|CAP-001.FR11]] (assumption) ^c11
- [thought] (@sim-lead) "Honestly not sure the flat rate is allowed as an expense; Ruth will know." whether the flat meal allowance can be paid as an expense is open with Finance Operations → keep: [[11-unknowns-and-risks#UNK-001 The flat meal allowance and tax|UNK-001]] (open) ^c12
- [thought] (@sim-lead) "UK claims go out with salary today. I don't know how that changes." how UK claims are paid within five days is open with Finance Operations → keep: [[11-unknowns-and-risks#UNK-002 How UK claims are paid|UNK-002]] (open) ^c13
- [thought] (@sim-lead) "Nobody has checked the cost centers line up." whether the human resources system's cost centers match the ledger's is open with Finance Operations → keep: [[11-unknowns-and-risks#UNK-003 Cost centers in two systems|UNK-003]] (open) ^c14
