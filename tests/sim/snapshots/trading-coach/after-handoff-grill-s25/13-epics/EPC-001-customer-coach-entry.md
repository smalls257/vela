---
id: EPC-001
type: epic
title: Customer coach entry
state: decided
owner: "@sim-lead"
authored: mixed
apps: [APP-coach, APP-tickertalk]
delivers: [CON-001]
consumes: [CON-002]
flows: []
depends_on: []
---

# Customer coach entry

- **Decision:** [[2026-10-08-coach-team-epics]]
- **Owning team:** @sim-lead (Coach team)
- **Options considered:** Cut 2, two epics split by audience (picked, [[2026-10-08-coach-team-epics#^c01]]); Cut 1, one epic for everything: rejected, it ties the January demo to the customer path ([[2026-10-08-coach-team-epics#^c02]]); Cut 3, two epics split by build slice: rejected, the board demo has no home ([[2026-10-08-coach-team-epics#^c03]])

This epic builds the provider side of [[coach-building-blocks#CON-001 Coach entry|CON-001]], the way a signed-in TickerTalk user gets into Coach. TickerTalk sends the user's ID and the request to open the coach, and Coach answers with the lesson and practice screens. Practice trades fill at the 15-minute-delayed quote Coach takes from [[coach-building-blocks#CON-002 Delayed quotes|CON-002]], and Coach keeps only the user's own practice record. If the quotes stop, practice pauses and the lessons go on. If Coach is down, TickerTalk hides the entry and the news carries on. This is the customer release planned for March. It teaches individual US-listed stocks only and places no real order.

## Epic acceptance criteria

1. A signed-in TickerTalk user who asks to open the coach over [[coach-building-blocks#CON-001 Coach entry|CON-001]] is sent the lesson and practice screens, and Coach reads the user's ID from that request and no other sign-in detail.
2. A user who is not on the board owner's named list is never offered the trade-ideas view in any answer over [[coach-building-blocks#CON-001 Coach entry|CON-001]].
3. A practice trade fills at the 15-minute-delayed quote shown on the user's screen, taken from [[coach-building-blocks#CON-002 Delayed quotes|CON-002]], and Coach keeps only that user's own practice record.
4. When [[coach-building-blocks#CON-002 Delayed quotes|CON-002]] gives no quote, practice trades pause and the lesson screens still open over [[coach-building-blocks#CON-001 Coach entry|CON-001]].
5. When the coach cannot answer a request over [[coach-building-blocks#CON-001 Coach entry|CON-001]], TickerTalk shows no coach entry and its news screens work as before.
6. Nothing sent over [[coach-building-blocks#CON-001 Coach entry|CON-001]] or [[coach-building-blocks#CON-002 Delayed quotes|CON-002]] prepares or places a real order, and the lessons and practice cover individual US-listed stocks only, no ETFs and no options.

## Traces to

<!-- generated:traces-to sha=00f2055d: do not edit, run vela render -->
| Traces to | Items |
|---|---|
| Apps | [[coach-building-blocks\|Coach]], [[tickertalk-building-blocks\|TickerTalk]] |
| Delivers | [[coach-building-blocks#CON-001 Coach entry\|CON-001 Coach entry]] |
| Consumes | [[coach-building-blocks#CON-002 Delayed quotes\|CON-002 Delayed quotes]] |
| Flows | none |
| Depends on | none |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

None. The customer entry does not wait on the board demo ([[2026-10-08-coach-team-epics#^c01]]).

## Rollout notes

Customer release is the March plan; the January demo is EPC-002. Every lesson and screen change needs the Brightwater ten-business-day review, and how it runs is open in [[11-unknowns-and-risks#UNK-033 Brightwater's review time against counsel's launch condition|UNK-033]].

## Out of scope

- The private board demo and its named list: EPC-002.
- Real orders, ETFs and options: release two.
- Where lesson progress and practice positions are kept: not decided.
