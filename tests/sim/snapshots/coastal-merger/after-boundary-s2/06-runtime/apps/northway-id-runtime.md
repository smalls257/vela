---
id: RUN-northway-id
type: app-runtime
title: Northway ID runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-04, 2026-10-07-login-owner-and-offer]
---

# Northway ID runtime

## On failure

If Northway ID is down or slow, nobody can sign in on the ferry side or the rail side.

Not recorded: whether SeaBook lets a customer book without signing in. Ask Ferry Ops.

Not recorded: Northway ID's availability target and who answers out of hours. Ask its owner through Rail Product ([[11-unknowns-and-risks#UNK-012 Northway ID ownership|UNK-012]]). SeaBook's own target is 99.9% from May to September (SRC-02), so the sign-in link may be its weakest part.

FERRYMASTER's sign-in through this login has no builder once the two people who understand it leave: [[11-unknowns-and-risks#R-01 FERRYMASTER sign-in after the two leave|R-01]].

- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen; Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app
