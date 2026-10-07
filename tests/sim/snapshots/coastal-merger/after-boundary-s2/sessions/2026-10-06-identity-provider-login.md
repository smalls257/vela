---
id: 2026-10-06-identity-provider-login
type: session
title: "Shape: identity provider login"
date: 2026-10-06
modes: [shape]
status: closed
summary: Picked Northway ID as the shared login (assumption), with ownership and contract terms open; options and the grill-to-confirm note are on 04b-identity-provider.
---

# 2026-10-06 Shape: identity provider login

## Captures

- [thought] (@sim-lead) "Shape it. But honestly, the decision's already made: Northway ID. The vault's got it as the assumption (SRC-04), and if Option B is buying us one sign-in, Northway ID is how we do it. The rail side already has it. Ferry customers get it too." → keep: [[04b-identity-provider#The shared login|identity-provider]] (assumption) ^c01
- [thought] (@sim-lead) "I need to know who owns it and whether their contract lets us add ferry customers, but that's a contract question, not an identity-provider question." → keep: [[11-unknowns-and-risks#UNK-037 Northway ID terms for ferry customers|UNK-037]] (open) ^c02
- [thought] (claude) Option 1, Northway ID as the shared login: ferry customers get a Northway ID, rail customers keep theirs. Cheapest, because rail already uses it and nothing is built new. It depends on who owns Northway ID and whether its terms allow ferry customers (UNK-012), and on SeaBook and FERRYMASTER being able to sign in through it. → keep: [[04b-identity-provider#The shared login|identity-provider]] (assumption) ^c03
- [thought] (claude) Option 2, a new identity service for both sides: both sets of customers move to it. It avoids the Northway ID ownership and contract question. It costs a build and a move for rail customers, who have a working login, and it lands in the May-to-September freeze window. → park ^c04
- [thought] (claude) Option 3, each side keeps its own login: SeaBook and Northway ID stay, and the link joins the two. Nothing moves. It gives two sign-ins, so it does not deliver "a customer signs in once" from [[04-solution-strategy#The core move|solution-strategy]]. → park ^c05
- [thought] (@sim-lead) "Yes. Option 1, Northway ID as the shared login, with ownership and contract as the open condition." Picks Option 1. Options 2 and 3 rejected. → keep: [[04b-identity-provider#The shared login|identity-provider]] (assumption) ^c06

## Changes

| ID | From | To | Source |
|---|---|---|---|
| identity-provider | - | assumption | [[2026-10-06-identity-provider-login#^c06]] |
| UNK-037 | - | open | [[2026-10-06-identity-provider-login#^c02]] |
