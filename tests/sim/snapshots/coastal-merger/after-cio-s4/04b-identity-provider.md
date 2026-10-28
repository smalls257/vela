---
id: identity-provider
type: initiative-section
title: Identity provider
arc42: "§4"
state: decided
owner: "@solution-lead"
authored: authored
sources: [SRC-01, SRC-04]
---

# Identity provider

## The shared login

- **Picked option:** Option 1, Northway ID as the shared login. Ferry customers get a Northway ID and rail customers keep theirs. Nothing is built new, because rail already uses it. It carries "a customer signs in once" from [[04-solution-strategy#The core move|solution-strategy]]. It depends on SeaBook and FERRYMASTER being able to sign in through it.
- **Options considered:** Option 1, Northway ID as the shared login (picked); Option 2, a new identity service for both sides: rejected, it costs a build and a move for rail customers who have a working login, and it lands in the May-to-September freeze window; Option 3, each side keeps its own login: rejected, it leaves two sign-ins, so a customer does not sign in once.
- **Open condition:** who owns Northway ID ([[11-unknowns-and-risks#UNK-012 Northway ID ownership|UNK-012]]), whether its terms allow ferry customers ([[11-unknowns-and-risks#UNK-037 Northway ID terms for ferry customers|UNK-037]]), and whether ferry customers are meant to get it at all ([[11-unknowns-and-risks#UNK-031 Ferry customers and Northway ID|UNK-031]]). Northway ID itself is an assumption from the rail slide (SRC-04): [[03-context-and-scope#Rail side today]].
- **Note:** grill to confirm. The solution lead called this already made in [[2026-10-06-identity-provider-login#^c01]]. This section is not decided in this session and stays an assumption until a Grill decides it, though the page state is `decided` for [[#Login owner and offer]].

## Login owner and offer

- **Picked option:** Owner option 1, Northway ID owns the login and offers sign-in only: a customer signs in once and proves who they are, and Northway ID hands each system one person key. The household, the link and the loyalty view stay outside it. The CIO's reply says the sign-in links the accounts and does not merge them (SRC-06, an assumption, with [[11-unknowns-and-risks#UNK-045 One sign-in or one identity|UNK-045]] still open), which is the link reading: [[2026-10-06-login-owner-and-offer#^c05]].
- **Options considered:** Owner option 1, Northway ID owns the login and offers sign-in only (picked); Owner option 2, Northway ID owns the login and the household: rejected, "Sam said the contract doesn't cover ferry, so that's a negotiation I don't know will land" ([[2026-10-06-login-owner-and-offer#^c07]]); Owner option 3, SeaBook owns the login and the household for ferry customers: rejected, "Option 3 is in the freeze, and Ferry Ops made clear nothing touches SeaBook from May through September", which is the lead's recall of Ferry Ops, with the freeze still open in [[11-unknowns-and-risks#UNK-007 May freeze scope and end|UNK-007]] ([[2026-10-06-login-owner-and-offer#^c08]]).
- **Decision:** [[2026-10-07-one-account-login-owner]]
- **Decided by:** @sim-lead, on behalf of @solution-lead
- **Override:** E316, GATE-5 by @sim-lead on 2026-10-07: the CIO said open questions should not hold the start; they go to the build team as named risks with owners (SRC-06, [[2026-10-07-cio-dpo-replies#^c12]]).
- **Carried as named risks:** [[11-unknowns-and-risks#R-01 FERRYMASTER sign-in after the two leave|R-01]], FERRYMASTER's sign-in once the two people who understand it have gone; who owns Northway ID and whether its terms allow ferry customers ([[11-unknowns-and-risks#UNK-012 Northway ID ownership|UNK-012]], [[11-unknowns-and-risks#UNK-037 Northway ID terms for ferry customers|UNK-037]]); whether ferry customers are meant to get Northway ID at all ([[11-unknowns-and-risks#UNK-031 Ferry customers and Northway ID|UNK-031]]). The household has no home, so who funds it, which system and contract hold it, who is its controller and which team runs it stay open, and it waits on the Data Protection Officer: [[11-unknowns-and-risks#UNK-044 Households in release one|UNK-044]], [[11-unknowns-and-risks#Question ledger|R-PTN-13]], [[11-unknowns-and-risks#Question ledger|R-REG-02]], [[11-unknowns-and-risks#Question ledger|R-OPS-10]]. The ferry customer key is [[11-unknowns-and-risks#UNK-033 Ferry customer key|UNK-033]].
- **Note:** the options here are named Owner option 1 to 3 so they do not clash with Option 1 to 3 under [[#The shared login]], which asks whether Northway ID is the shared login at all. Whether the two lists should be one is [[11-unknowns-and-risks#Question ledger|R-DAT-19]].
