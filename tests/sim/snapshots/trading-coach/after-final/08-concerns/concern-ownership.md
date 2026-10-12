---
id: concern-ownership
type: concern
title: Ownership
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Ownership

Which team owns each app and each piece of new work.

## Strategy

@coach-lead owns Coach and its epics, and the Coach team runs the service. The product lead owns the lessons and the stock list, and Fieldnote Learning writes the lessons from 12 October. If Brightwater's review rejects a lesson, Fieldnote rewrites it and the product lead answers Brightwater for the first two rounds, but [[11-unknowns-and-risks#UNK-068 Who owns escalation after two rejected rounds|who owns the escalation after two rejected rounds]] is open. TickerTalk's existing ownership practice holds.

[[sources#SRC-16|the answers the product lead gathered by 9 October]] say the Coach team runs the Coach service on Kestrel's AWS account, with the platform engineer's help for the first month, according to the CTO; the help is a plan, so it is an assumption. The Coach lead, @coach-lead, wrote in the Coach channel on 9 October that the four containers are right as written (Lessons, Paper practice, Quote display and Board demo) and that they own Coach's epics. Fieldnote Learning is the contracted lesson writer, starting 12 October, which is also an assumption until it starts.

[[sources#SRC-19|The Coach lead says]] they own the review of Coach's failure cases during the build. [[sources#SRC-22|The product lead recalls]] the mobile lead saying that two engineers can build it by March, but is mixed up on the date and has nothing in writing. That looks ahead and is unconfirmed, so it is an assumption, and the mobile lead is to confirm it in [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|the capacity question]].

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | addressed | @coach-lead owns Coach and its epics. The product lead owns the lessons and the stock list, and defines "ready" as three graded paper trades plus the lessons for them. Fieldnote Learning writes the lessons from 12 October. If Brightwater's review rejects a lesson, Fieldnote rewrites it and the product lead answers Brightwater, for the first two rounds; who owns the escalation after two rejected rounds is [[11-unknowns-and-risks#UNK-068 Who owns escalation after two rejected rounds\|the escalation question]], not this cell |
| [[tickertalk-building-blocks\|TickerTalk]] | unchanged | the product lead says the existing ownership practice holds ([[2026-10-09-concern-cells#^c07]]) |

## History

#### Coach
- **Decision:** [[2026-10-09-concern-cells]]
- **Options considered:** The product lead owning Coach as well as the lessons, as the Coach page says for now. Rejected: @coach-lead runs the team and the service, and that is where the ownership lives.
- **Override:** GATE-5 by @sim-lead on 2026-10-09: the owner is not present and the product lead decides on their behalf
- **Decided by:** @sim-lead, on behalf of @coach-lead
- **Confirmed by:** @coach-lead on 2026-10-09
