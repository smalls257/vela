---
id: EPC-002
type: epic
title: Coach paper trading
state: decided
owner: "@sim-lead"
authored: mixed
apps: [APP-coach]
delivers: [CAP-002, CON-002]
consumes: [CON-003, CON-004]
flows: []
depends_on: [EPC-001]
---

# Coach paper trading

**Owning team:** @sim-lead (Coach)

This epic builds the paper-trading side of Coach. It lets a reader place simulated orders through the [[coach-building-blocks#CON-002 Paper trades|paper trades contract]], answered by Brightwater's sandbox accounts, with Quoteline's delayed prices shown beside them and no real order ever placed. It follows the lessons epic and ships behind a release switch, once the Brightwater terms are settled. Where the record of a reader's paper trades lives is still open, and so is whether valuing those trades on Quoteline's quotes needs a licence addendum, so the quotes are for display only until it is answered. Two data questions are also open, whether reader data may go to Brightwater and on what lawful basis Coach holds it, and the team builds with both open until they are answered on 16 October.

## Epic acceptance criteria

1. A paper order sent over [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] for a stock pick is answered with an order status, and no real order crosses [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] or [[coach-building-blocks#CON-003 Brightwater sandbox|Brightwater sandbox contract]].
2. When [[coach-building-blocks#CON-003 Brightwater sandbox|Brightwater sandbox contract]] has not answered, [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] returns the order as pending and refuses a second identical order while the first is pending.
3. When [[coach-building-blocks#CON-003 Brightwater sandbox|Brightwater sandbox contract]] answers, the order status and the balance returned over [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] change together, or neither changes.
4. Prices on [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] come from [[coach-building-blocks#CON-004 Quoteline delayed quotes|Quoteline delayed quotes contract]] labelled as delayed by 15 minutes.
5. A position in a stock that has left the list of stocks is returned over [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] as sold or marked stale, never dropped without a trace.
6. While paper trading has not been released, [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] accepts no paper order and replies that paper trading is not yet available.
7. When Brightwater gives notice under [[coach-building-blocks#CON-003 Brightwater sandbox|Brightwater sandbox contract]], [[coach-building-blocks#CON-002 Paper trades|paper trades contract]] returns each reader's last known positions and balance marked frozen and refuses new paper orders.

## Traces to

<!-- generated:traces-to sha=3abb9a95: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[coach-building-blocks\|Coach]] |
| Delivers | [[CAP-002-paper-trade-a-stock\|CAP-002 Paper-trade a stock]], [[coach-building-blocks#CON-002 Paper trades\|CON-002 Paper trades]] |
| Consumes | [[coach-building-blocks#CON-003 Brightwater sandbox\|CON-003 Brightwater sandbox]], [[coach-building-blocks#CON-004 Quoteline delayed quotes\|CON-004 Quoteline delayed quotes]] |
| Flows | none |
| Depends on | [[EPC-001-coach-lessons-and-list\|EPC-001 Coach lessons, ready track and stock list]] |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-001-coach-lessons-and-list|The lessons epic]]: paper trades start from a stock on the list of stocks that the lessons epic holds.

## Rollout notes

Follows the lessons epic. It ships once the Brightwater terms are settled ([[11-unknowns-and-risks#UNK-009 Signed broker agreement terms|signed broker agreement terms]]), and it ships behind the release switch. Criterion 4 covers prices only. Valuing a position on Quoteline's quotes is not in this epic ([[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|the question on valuing paper trades]] is still open), and the Quoteline delayed quotes contract is an assumption again. Criterion 7 holds only if Coach is the record of paper trades ([[11-unknowns-and-risks#UNK-029 Where the paper record lives|where the paper record lives]]).

## Out of scope

- Real orders, options, and advice to a particular reader.
- Where the paper record lives: UNK-029.
- Valuing a reader's balance or positions on Quoteline's delayed quotes: waiting on [[CAP-002-paper-trade-a-stock|the paper-trade capability]], and on [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|the question on valuing paper trades]].

## History

- **Options considered:** Two epics split by contract, lessons, track and list against paper trading (picked, [[2026-10-09-coach-epics#^c01]]); three epics with the ready track on its own: rejected, it splits CON-001's "whether ready" output from the epic that delivers CON-001; one Coach epic: rejected, lessons could not ship without paper trading, and 4 to 7 criteria cannot cover six items ([[2026-10-09-coach-epics#^c02]])
- **Decision:** [[2026-10-09-epics-coach-mobile]]; decided with Q-DAT-01@INI-001, Q-DAT-02@APP-coach, Q-REG-01@INI-001 and Q-REG-05@INI-001 open (W807)
- **Override:** GATE-4 by @sim-lead on 2026-10-09: "Honestly not sure on both. Partnerships on Brightwater, @privacy-lead on lawful basis. Set ask-by dates and we move." UNK-059 and UNK-060 stay open, owned with ask-by 2026-10-16.
