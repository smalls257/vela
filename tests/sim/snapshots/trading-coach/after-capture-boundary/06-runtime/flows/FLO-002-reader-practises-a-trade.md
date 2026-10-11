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

1. [[tickertalk-building-blocks|TickerTalk]] → [[coach-building-blocks|Coach]]: sends the paper order over [[coach-building-blocks#CON-002 Paper trades|Paper trades]], after the reader picks a stock from the list over [[coach-building-blocks#CON-001 Lessons and track|Lessons and track]] and places the order. Uses [[CAP-002-paper-trade-a-stock|Paper-trade a stock]].
2. [[coach-building-blocks|Coach]] → [[03-context-and-scope#PTY-01 Brightwater|Brightwater]]: opens a sandbox paper account for the reader if there is none, and sends the order to the sandbox over [[coach-building-blocks#CON-003 Brightwater sandbox|Brightwater sandbox]]. When the account is opened is still open, see [[11-unknowns-and-risks#UNK-050 When Coach opens a sandbox account|when Coach opens a sandbox account]].
3. [[coach-building-blocks|Coach]] → [[tickertalk-building-blocks|TickerTalk]]: sends the order as pending until the sandbox answers, over [[coach-building-blocks#CON-002 Paper trades|Paper trades]]. If the sandbox is slow, Coach asks for the order's status later and never sends the order again.
4. [[coach-building-blocks|Coach]] → [[tickertalk-building-blocks|TickerTalk]]: when the order fills, Coach updates the reader's balance and positions together and sends them, over [[coach-building-blocks#CON-002 Paper trades|Paper trades]].
5. [[03-context-and-scope#PTY-02 Quoteline|Quoteline]] → [[coach-building-blocks|Coach]]: sends delayed quotes for display only, over [[coach-building-blocks#CON-004 Quoteline delayed quotes|Quoteline delayed quotes]]. Coach shows cash and positions at fill price and computes no valued balance, until Quoteline answers whether [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|valuing paper trades on its quotes]] is display use.
