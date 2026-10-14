---
id: EPC-001
type: epic
title: Coach lessons, ready track and stock list
state: decided
owner: "@sim-lead"
authored: mixed
apps: [APP-coach]
delivers: [CAP-001, CAP-003, CAP-004, CON-001]
consumes: []
flows: []
depends_on: []
---

# Coach lessons, ready track and stock list

**Owning team:** @sim-lead (Coach)

This epic builds the lesson side of Coach, the part that is meant to ship for the January demo. It lets the coach screens in TickerTalk read the lessons, a reader's progress and the list of about 50 stocks from Coach through the [[coach-building-blocks#CON-001 Lessons and track|lessons and track contract]], and it keeps the list as data, so a ruling from counsel changes the list and not the build. It does not take paper trades, which are the paper-trading epic's work, and it does not define when a reader counts as ready, which waits until after January. Who owns this work after the change and whether anything is sold across parties are still open, and the Coach team's lead is not yet named.

## Epic acceptance criteria

1. A request over [[coach-building-blocks#CON-001 Lessons and track|lessons and track contract]] for a reader returns the lessons for each stock on the list of stocks and that reader's progress through them.
2. When a stock leaves the list of stocks, [[coach-building-blocks#CON-001 Lessons and track|lessons and track contract]] still returns that stock's lesson and the reader's completed progress on it, and offers no new lesson on it.
3. A change to the list of stocks, made as data, shows in the next [[coach-building-blocks#CON-001 Lessons and track|lessons and track contract]] response with no new build of Coach or of the TickerTalk app.
4. Every field and value [[coach-building-blocks#CON-001 Lessons and track|lessons and track contract]] has served keeps being served, in its old shape, until mobile says the last app version that uses it is retired.
5. The coach screens in TickerTalk render lessons, list and progress from Coach's example responses for [[coach-building-blocks#CON-001 Lessons and track|lessons and track contract]].

## Traces to

<!-- generated:traces-to sha=cc250ab3: do not edit, run vela render -->
| Traces to | Items |
|---|---|
| Apps | [[coach-building-blocks\|Coach]] |
| Delivers | [[CAP-001-teach-a-stock-lesson\|CAP-001 Teach a stock lesson]], [[CAP-003-pass-the-ready-track\|CAP-003 Pass the ready track]], [[CAP-004-keep-the-stock-list\|CAP-004 Keep the stock list]], [[coach-building-blocks#CON-001 Lessons and track\|CON-001 Lessons and track]] |
| Consumes | none |
| Flows | none |
| Depends on | none |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

None. This epic is the first of the two and the list of stocks it holds is what the paper trades of the next epic start from.

## Rollout notes

Targets the January demo. It does not need the [[11-unknowns-and-risks#UNK-009 Signed broker agreement terms|Brightwater terms]] or Quoteline's [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|answer on valuing paper trades]].

## Out of scope

- What "ready" means for the track: waiting on a requirement on CAP-003 ([[11-unknowns-and-risks#UNK-018 Who writes the lessons and defines ready|who defines ready]]). The product is not showing ready before January ([[2026-10-09-coach-epics#^c03]]). Criterion 2 covers only that completed progress is kept and counts.
- Paper trades and the release switch, which are EPC-002.

## History

- **Decision:** [[2026-10-09-coach-epics]]
- **Options considered:** Two epics split by contract, lessons, track and list against paper trading (picked, [[2026-10-09-coach-epics#^c01]]); three epics with the ready track on its own: rejected, it splits CON-001's "whether ready" output from the epic that delivers CON-001; one Coach epic: rejected, lessons could not ship without paper trading, and 4 to 7 criteria cannot cover six items ([[2026-10-09-coach-epics#^c02]])
