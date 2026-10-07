---
id: solution-strategy
type: initiative-section
title: Solution strategy
arc42: "§4"
state: decided
owner: "@solution-lead"
authored: authored
---

# Solution strategy

## The core move

- **Picked option:** Option B, a linked household account, B-household with explicit linking only. A customer signs in once. Ferry and rail records stay in each system and are linked to the person, a household holds the people under it, and loyalty balances stay separate with one view over both. B stands until challenged. Central IT is building Option B, not a placeholder.
- **Two readings of it:** B-household makes one household at ferry login for each shared family email, and the rail account stays separate until that person proves who they are and links it themselves. Nothing auto-joins on an email match. B-matched, which matches each ferry record to a person before the link goes live, is not the reading picked. The Data Protection Officer's view is still owed: [[11-unknowns-and-risks#UNK-010 Data Protection Officer|UNK-010]].
- **Options considered:** Option B, a linked household account (picked); Option A, one sign-in: rejected, "A leaves the family email for later which just delays the problem."; Option C, one merged customer and wallet: rejected, it needs Finance to settle points and needs the two FERRYMASTER people, who are leaving, so a migration could start with nowhere to land.
- **Decision:** [[2026-10-06-what-one-account-means-2]]
- **Decided by:** @sim-lead, on behalf of @solution-lead
- **Override:** GATE-4, GATE-5 by @sim-lead on 2026-10-06: I can't wait for Legal to confirm terms that don't exist yet. The legal owner will tell us what the customer terms allow, but the terms themselves depend on what we're building. If we wait for the legal read before we decide, we're stalled indefinitely. The legal check on Monday is not optional, it's a gate on build, but it can't block the decision. If the terms say we can't do matching, we have a problem to solve then, not a reason to wait now.
- **Still owed:** DPO sign-off still owed, UNK-010 open. [[11-unknowns-and-risks#UNK-028 Customer terms and contracting party|UNK-028]] stays open.
## Loyalty in one account

- **Picked option:** Option L1, one view, two balances (assumption). The account shows Tidemiles and Northway Plus side by side. Each balance is earned and spent only in its own scheme at its own rate, with no conversion. It sits on top of the linked household account, which is itself an assumption on another session branch.
- **Open conditions:** none of the conditions for L1 is taken yet. They wait on the Data Protection Officer's answer on households: [[11-unknowns-and-risks#UNK-010 Data Protection Officer|UNK-010]]. The first two are which system holds each balance ([[03-context-and-scope#SV-01 Tidemiles|SV-01]], [[03-context-and-scope#SV-02 Northway Plus|SV-02]]) and who covers support for a view that reads both sides.
- **Options considered:** Option L1, one view, two balances (picked); Option L2, two schemes with a bridge: rejected, it needs a Northway Plus redemption value that no source gives ([[11-unknowns-and-risks#UNK-022 Loyalty points one for one|UNK-022]]) and a rate set by Finance; Option L3, one new scheme, one balance: rejected, it needs that value and the two FERRYMASTER people, who are leaving, to stay.
