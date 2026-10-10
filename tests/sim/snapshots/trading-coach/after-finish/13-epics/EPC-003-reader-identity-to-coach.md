---
id: EPC-003
type: epic
title: Reader identity to Coach
state: draft
owner: "@sim-lead"
authored: mixed
apps: [APP-tickertalk]
delivers: [CON-005]
consumes: []
flows: [FLO-001]
depends_on: []
---

# Reader identity to Coach

**Owning team:** @sim-lead (Mobile)

This epic makes TickerTalk send Coach each opted-in reader's opaque reader ID, through the [[tickertalk-building-blocks#CON-005 Reader identity|reader identity contract]], and nothing else of the reader's data. Coach builds a reader's record from that ID, so the epic ships first. The coach screens inside the app are not part of it: they read the lessons and paper trades contracts and ship with the mobile rollout. Whether the ID stays the same across a change of email or device, and whether TickerTalk checks the opt-in before it sends, are still open.

## Epic acceptance criteria

1. For a signed-in reader with a current opt-in, [[tickertalk-building-blocks#CON-005 Reader identity|reader identity contract]] sends Coach that reader's opaque reader ID and nothing else of TickerTalk's data.
2. For a reader with no opt-in, or who has withdrawn it, nothing crosses [[tickertalk-building-blocks#CON-005 Reader identity|reader identity contract]].
3. The reader ID sent over [[tickertalk-building-blocks#CON-005 Reader identity|reader identity contract]] for one reader is the same after a change of email and after signing in on a new device, and is never sent for any other reader.
4. When the reader ID does not reach Coach, [[tickertalk-building-blocks#CON-005 Reader identity|reader identity contract]] sends it again the next time the reader opens the coach, and the reader is not asked to opt in a second time, as [[FLO-001-reader-starts-learning|the reader-starts-learning flow]] describes.
5. A change to the reader ID sent over [[tickertalk-building-blocks#CON-005 Reader identity|reader identity contract]] is not made until Coach says it has moved, and until then the old ID keeps being sent.

## Traces to

<!-- generated:traces-to sha=3eec9c8e: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[tickertalk-building-blocks\|TickerTalk]] |
| Delivers | [[tickertalk-building-blocks#CON-005 Reader identity\|CON-005 Reader identity]] |
| Consumes | none |
| Flows | [[FLO-001-reader-starts-learning\|FLO-001 A reader starts learning]] |
| Depends on | none |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

- None. [[coach-building-blocks|Coach]] depends on this epic, because it creates a reader's record from the ID.

## Rollout notes

Ships first, so Coach can build against the contract. The coach screens that read [[coach-building-blocks#CON-001 Lessons and track|lessons and track]] and [[coach-building-blocks#CON-002 Paper trades|paper trades]] have no epic of their own. They are the consumer side of those contracts and are part of the mobile rollout, the opt-in beta. Criteria 1 to 3 hold only if the questions on whether the ID is stable ([[11-unknowns-and-risks#UNK-047 Is the reader ID stable across email and device changes|the stability of the reader ID]]) and whether TickerTalk checks the opt-in before it sends ([[11-unknowns-and-risks#UNK-048 Does mobile's plan cover sending the ID only for opted-in readers|mobile's plan for opted-in readers]]) are answered as planned.

## Out of scope

- The coach screens and the release switch behaviour on the mobile side.
- What Coach does with a reader's record after withdrawal: UNK-054.

## History

- **Options considered:** One identity epic delivering CON-005 only (picked, [[2026-10-09-epics-coach-mobile#^c01]]); one mobile epic holding identity and the coach screens: rejected, identity could not ship ahead of the screens and the screens have no contract of their own to hold a criterion to; two mobile epics, identity then screens: rejected, the screens epic delivers nothing of its own and would fail T6 ([[2026-10-09-epics-coach-mobile#^c02]])
