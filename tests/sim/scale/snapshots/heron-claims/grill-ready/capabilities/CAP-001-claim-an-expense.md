---
id: CAP-001
type: capability
title: Claim an expense
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Finance
sources: [2026-10-12-claim-requirements]
---

# Claim an expense

A member of staff who spent their own money on firm business gets it back: they hand in the receipt, their manager approves it, and Finance pays them. Today it is a paper form typed into a spreadsheet by Finance Operations.

## Functional requirements

### CAP-001.FR1 Hand in a receipt

A person hands in each receipt as a photo taken in the app, attached to the claim line it backs.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c01
- **Options considered:** Photograph it in the app (picked); Forward an email receipt: rejected, most receipts are paper and two ways in double the support.

- A claim line without a receipt photo cannot be sent for approval, unless the person marks it as a lost receipt and says why.
- A photo that the app cannot read is kept, and the person types the amount and the date.

### CAP-001.FR2 Claim mileage

A person claims mileage by typing the miles and the purpose of the journey.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c02
- **Options considered:** The person types the miles and the purpose (picked); A route calculator works out the miles: rejected, a second service to buy for a few hundred claims a month.

- The claim shows the rate per mile used and the total.
- A mileage line needs a purpose before it can be sent.

### CAP-001.FR3 Claim in the currency paid

A person claims each line in the currency they paid in, and the claim converts it at the rate on their card statement.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c03
- **Options considered:** The currency they paid in, converted at the card rate (picked); They convert it themselves: rejected, people get conversions wrong and the statement is the evidence.

- The claim shows both the amount paid and the converted amount.
- When no card rate is known, the claim uses the day's published rate and says so.

### CAP-001.FR4 The line manager approves

Each claim goes to the person's line manager to approve.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c04
- **Options considered:** The person's line manager (picked); The cost center's owner: rejected, the owner often does not know whether the trip happened.

- A manager cannot approve their own claim; it goes to their own manager.
- When the manager is away, the claim goes to the person they named as cover.

### CAP-001.FR5 A second approval for large claims

A claim over 500 pounds needs a second approval by Finance Operations after the manager's.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c05
- **Options considered:** A second approval by Finance (picked); It is blocked until the person splits it: rejected, splitting a large claim is a workaround, not a control.

- The threshold is the claim's total in pounds after conversion.
- The person sees that their claim is waiting for Finance, not for their manager.

### CAP-001.FR6 Late claims

A claim line more than 60 days old is sent with a warning, and one more than 90 days old is refused.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c06
- **Options considered:** A warning at 60 days, refused at 90 (picked); Refused at 90 days with no warning: rejected, the warning saves the argument.

- The age is counted from the date on the receipt.
- A refused line says why, and the rest of the claim goes on.

### CAP-001.FR7 Send a claim back

An approver who finds a claim wrong sends it back to the person with a comment saying what to fix.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c07
- **Options considered:** Send it back with a comment (picked); Reject it outright: rejected, most wrong claims are a missing receipt, not a refusal.

- A claim sent back keeps every line the approver did not question.
- The person sees the comment next to the line it is about.

### CAP-001.FR8 Where my claim is

A person sees where each of their claims is, and gets a message each time it moves.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c08
- **Options considered:** Its status at each step, with a message when it changes (picked); A status page they check themselves: rejected, most calls to Finance today ask where a claim is.

- The steps are: sent, with the manager, with Finance, approved, paid, or sent back.
- A message names the claim and the step it moved to.

### CAP-001.FR9 Overnight meal allowance

A person who stays away overnight in the UK claims a flat daily meal allowance with no receipt.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c09
- **Options considered:** A flat daily rate with no receipt (picked); Actual meals with receipts: rejected, the partners agreed the flat rate last spring.

- The allowance is claimed per night away, with the place stayed.
- Whether the rate can be paid as an expense at all is open as [[11-unknowns-and-risks#UNK-001 The flat meal allowance and tax|the meal allowance and tax]].

### CAP-001.FR10 When a claim is paid

An approved claim is paid into the person's bank account within five working days of approval.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c10
- **Options considered:** Within five working days of approval (picked); In the next monthly run: rejected, it breaks the CFO's mandate.

- The person sees the date it was paid.
- How UK claims are paid at all is open as [[11-unknowns-and-risks#UNK-002 How UK claims are paid|how UK claims are paid]].

### CAP-001.FR11 Split a claim across cost centers

A person can split a claim line across two or more cost centers, by percentage.

- **State:** assumption
- **Source:** [[2026-10-12-claim-requirements]] c11
- **Options considered:** Yes, by percentage (picked); No, one claim, one cost center: rejected, client work often spans two practices.

- The percentages add up to a hundred before the line can be sent.
- Each cost center's owner sees only their share.
- Whether the cost centers can be trusted is open as [[11-unknowns-and-risks#UNK-003 Cost centers in two systems|cost centers in two systems]].
