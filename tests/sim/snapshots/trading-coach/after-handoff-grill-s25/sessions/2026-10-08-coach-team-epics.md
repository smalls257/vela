---
id: 2026-10-08-coach-team-epics
type: session
title: "Epics: Coach team"
date: 2026-10-08
modes: [epics, shape, grill]
status: closed
summary: "Split the Coach team's work into two decided epics: EPC-001 customer entry (March) and EPC-002 private board demo (January), both delivering CON-001."
---

# 2026-10-08 Epics: Coach team

## Captures

- [thought] (@sim-lead) "Cut 2. Keeps January and March separate—demo doesn't block customer work." Chosen cut for the Coach team: two epics split by audience, EPC-001 the customer entry and EPC-002 the private board demo, both delivering CON-001. Stays draft; Shape never decides. → drop: EPC-001 and EPC-002 hold the cut in their Options considered bullets ^c01
- [thought] (claude, from @sim-lead) Rejected Cut 1, one epic "Coach entry" for entry, lessons, practice and board gate: it ties the January demo to the customer path, so the demo cannot be called done until the customer path is. The lead's reason for picking Cut 2: "demo doesn't block customer work". → drop: the rejection and its reason sit in both epics' Options considered bullets ^c02
- [thought] (claude) Rejected Cut 3, two epics split by build slice (entry and lessons, then practice): the board demo has no home and would need a third epic. The lead gave no reason of their own for not picking it. → drop: the rejection sits in both epics' Options considered bullets ^c03
- [thought] (@sim-lead) "All three look fine. Read them back and I'll lock both epics." Keeps EPC-001 criterion 1 (ID only), EPC-002 criterion 4 (removal on next request) and the trade-ideas content under Out of scope as written. It is not a yes to each criterion on its own, so both epics stay draft until each has one. → drop: process; the epics hold the wordings it kept ^c04
- [thought] (@sim-lead) "Yes. None right now—those are all gated on the Brightwater agreement anyway. Go through the criteria and lock both." Confirms the agenda (GATE-3 yes). Takes none of Q-DAT-02@APP-coach, Q-DAT-02@APP-tickertalk, Q-FIN-01@INI-001, Q-REG-01@INI-001 now; they stay open (W807). → drop: the Agenda and the Changes rows' W807 notes carry it ^c05
- [thought] (claude, from @sim-lead) EPC-001 criterion 1: a signed-in user's request over CON-001 is sent the lesson and practice screens, and Coach reads only the user's ID. The lead said "Yes." → drop: the epic page holds the criterion; c12 is the deciding capture ^c06
- [thought] (claude, from @sim-lead) EPC-001 criterion 2: a user not on the board owner's named list is never offered the trade-ideas view over CON-001. The lead said "Yes." → drop: the epic page holds the criterion; c12 is the deciding capture ^c07
- [thought] (claude, from @sim-lead) EPC-001 criterion 3: a practice trade fills at the 15-minute-delayed quote shown on screen, from CON-002, and Coach keeps only the user's own practice record. The lead said "Yes." → drop: the epic page holds the criterion; c12 is the deciding capture ^c08
- [thought] (claude, from @sim-lead) EPC-001 criterion 4: when CON-002 gives no quote, practice trades pause and the lesson screens still open over CON-001. The lead said "Yes." → drop: the epic page holds the criterion; c12 is the deciding capture ^c09
- [thought] (claude, from @sim-lead) EPC-001 criterion 5: when the coach cannot answer a request over CON-001, TickerTalk shows no coach entry and its news screens work as before. The lead said "Yes." → drop: the epic page holds the criterion; c12 is the deciding capture ^c10
- [thought] (claude, from @sim-lead) EPC-001 criterion 6: nothing over CON-001 or CON-002 prepares or places a real order, and lessons and practice cover individual US-listed stocks only. The lead said "Yes." → drop: the epic page holds the criterion; c12 is the deciding capture ^c11
- [thought] (@sim-lead) "Yes. Lock it and move to EPC-002." Read-back of the six EPC-001 criteria accepted; each had its own yes (c06 to c11). Owner of the epic: @sim-lead, present. → keep: [[EPC-001-customer-coach-entry#Customer coach entry|EPC-001]] (decided) ^c12
- [thought] (@sim-lead) Decided with Q-DAT-02@APP-coach, Q-DAT-02@APP-tickertalk, Q-FIN-01@INI-001 and Q-REG-01@INI-001 open (W807), after "None right now—those are all gated on the Brightwater agreement anyway" (c05). → drop: the Changes row carries the decided-with-open note ^c13
- [thought] (claude, from @sim-lead) EPC-002 criterion 1: a board member on the named list who opens the coach over CON-001 is offered the trade-ideas view as well as the lesson and practice screens. The lead said "Yes." → drop: the epic page holds the criterion; c18 is the deciding capture ^c14
- [thought] (claude, from @sim-lead) EPC-002 criterion 2: a signed-in user not on the named list is never offered the trade-ideas view over CON-001, and no customer can open it. The lead said "Yes." → drop: the epic page holds the criterion; c18 is the deciding capture ^c15
- [thought] (claude, from @sim-lead) EPC-002 criterion 3: the trade-ideas view places no live order and nothing over CON-001 prepares one; the user buys themselves. The lead said "Yes." → drop: the epic page holds the criterion; c18 is the deciding capture ^c16
- [thought] (claude, from @sim-lead) EPC-002 criterion 4: a person the board owner takes off the named list is no longer offered the trade-ideas view on their next request over CON-001. The wording is Claude's; no page records how a removal takes effect. The lead said "Yes." → drop: the epic page holds the criterion; c18 is the deciding capture ^c17
- [thought] (@sim-lead) "Yes. No dependency—parallel builds that ship on their dates." Read-back of the four EPC-002 criteria accepted; each had its own yes (c14 to c17). Settles the open dependency question: EPC-002 depends on no epic. Owner of the epic: @sim-lead, present. → keep: [[EPC-002-private-board-demo#Private board demo|EPC-002]] (decided) ^c18
- [thought] (@sim-lead) Decided with Q-DAT-02@APP-coach, Q-FIN-01@INI-001 and Q-REG-01@INI-001 open (W807), after "None right now—those are all gated on the Brightwater agreement anyway" (c05). → drop: the Changes row carries the decided-with-open note ^c19
- [thought] (@sim-lead) "Override all of it. The Brightwater agreement is the gate on every one of these—once I read it tomorrow, we know what sticks. Can't answer data, stored value or Quoteline terms until I've got that." Override of E805 for all 35 undisposed high-severity questions, written at page level under the Question ledger on 11-unknowns-and-risks. → drop: the Override bullet carries it ^c20

## Agenda

- EPC-001: GATE-3 confirmed yes, status decided
- EPC-002: GATE-3 confirmed yes, status decided

## Changes

| ID | From | To | Source |
|---|---|---|---|
| EPC-001 | - | draft | [[2026-10-08-coach-team-epics#^c01]] |
| EPC-002 | - | draft | [[2026-10-08-coach-team-epics#^c01]] |
| EPC-001 | draft | decided | [[2026-10-08-coach-team-epics#^c12]]; decided with Q-DAT-02@APP-coach, Q-DAT-02@APP-tickertalk, Q-FIN-01@INI-001, Q-REG-01@INI-001 open (W807) |
| EPC-002 | draft | decided | [[2026-10-08-coach-team-epics#^c18]]; decided with Q-DAT-02@APP-coach, Q-FIN-01@INI-001, Q-REG-01@INI-001 open (W807) |
