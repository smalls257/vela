---
id: FLO-002
type: flow
title: A reader practises a trade
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-16, SRC-08, 2026-10-09-coach-tickertalk-journeys]
---

# A reader practises a trade

A reader who has opted in picks a stock from the list and places a paper order. [[tickertalk-building-blocks|TickerTalk]] draws the screens, [[coach-building-blocks|Coach]] keeps the paper record and sends the order to Brightwater's sandbox, and no real order or real money is involved. When the sandbox account is opened is [[11-unknowns-and-risks#UNK-050 When Coach opens a sandbox account|not decided]].

## Steps

1. The reader picks a stock from the list in TickerTalk over [[coach-building-blocks#CON-001 Lessons and track|Lessons and track]] and places a paper order. TickerTalk sends it to Coach over [[coach-building-blocks#CON-002 Paper trades|Paper trades]]. Uses [[CAP-002-paper-trade-a-stock|Paper-trade a stock]].
2. Coach opens a sandbox paper account for the reader if there is none, and sends the order to the sandbox over [[coach-building-blocks#CON-003 Brightwater sandbox|Brightwater sandbox]]. When the account is opened is still open, see [[11-unknowns-and-risks#UNK-050 When Coach opens a sandbox account|when Coach opens a sandbox account]].
3. TickerTalk shows the order as pending until the sandbox answers. If the sandbox is slow, Coach asks for the order's status later and never sends the order again, over [[coach-building-blocks#CON-002 Paper trades|Paper trades]].
4. When the order fills, Coach updates the reader's balance and positions together, and TickerTalk shows them over [[coach-building-blocks#CON-002 Paper trades|Paper trades]].
5. Coach shows cash and positions at fill price and computes no valued balance, until Quoteline answers whether [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|valuing paper trades on its quotes]] is display use. Uses [[coach-building-blocks#CON-004 Quoteline delayed quotes|Quoteline delayed quotes]] for display only.
