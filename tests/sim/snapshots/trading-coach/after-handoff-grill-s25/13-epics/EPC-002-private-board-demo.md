---
id: EPC-002
type: epic
title: Private board demo
state: decided
owner: "@sim-lead"
authored: mixed
apps: [APP-coach]
delivers: [CON-001]
consumes: []
flows: []
depends_on: []
---

# Private board demo

- **Decision:** [[2026-10-08-coach-team-epics]]
- **Owning team:** @sim-lead (Coach team)
- **Options considered:** Cut 2, two epics split by audience (picked, [[2026-10-08-coach-team-epics#^c01]]); Cut 1, one epic for everything: rejected, it ties the January demo to the customer path ([[2026-10-08-coach-team-epics#^c02]]); Cut 3, two epics split by build slice: rejected, the board demo has no home ([[2026-10-08-coach-team-epics#^c03]])

This epic builds the private January board demo, which opens through [[coach-building-blocks#CON-001 Coach entry|CON-001]]. A named list of board members, kept by the board owner (the CEO until it is known who manages it), is offered a trade-ideas view when they open the coach. No one else is offered it, and no customer can open it. The view places no live order, and the user buys themselves. The demo is built alongside [[EPC-001-customer-coach-entry|EPC-001]] and ships on its own date. What the ideas are, and where they come from, is not recorded.

## Epic acceptance criteria

1. A board member on the board owner's named list who asks to open the coach over [[coach-building-blocks#CON-001 Coach entry|CON-001]] is offered the trade-ideas view as well as the lesson and practice screens.
2. A signed-in user who is not on the named list is never offered the trade-ideas view in any answer over [[coach-building-blocks#CON-001 Coach entry|CON-001]], and no customer can open it.
3. The trade-ideas view places no live order, and nothing sent over [[coach-building-blocks#CON-001 Coach entry|CON-001]] prepares one: the user buys themselves.
4. A person the board owner takes off the named list is no longer offered the trade-ideas view on their next request over [[coach-building-blocks#CON-001 Coach entry|CON-001]].

## Traces to

<!-- generated:traces-to sha=312728ff: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[coach-building-blocks\|Coach]] |
| Delivers | [[coach-building-blocks#CON-001 Coach entry\|CON-001 Coach entry]] |
| Consumes | none |
| Flows | none |
| Depends on | none |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

None. The demo and EPC-001 are parallel builds that ship on their own dates ([[2026-10-08-coach-team-epics#^c18]]).

## Rollout notes

The demo is the private January board demo. The board owner is the CEO until it is known who manages the list ([[coach-building-blocks#Coach|APP-coach]]).

## Out of scope

- What trade ideas the view shows and where they come from: not recorded (Signal's place is not decided); waiting on @sim-lead, with [[11-unknowns-and-risks|R-REG-16]] open.
- The customer path: EPC-001.
