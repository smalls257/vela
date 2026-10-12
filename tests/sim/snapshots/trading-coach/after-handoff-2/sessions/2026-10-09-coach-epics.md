---
id: 2026-10-09-coach-epics
type: session
title: "Epics: Coach team"
date: 2026-10-09
modes: [epics, shape, grill]
status: closed
summary: EPC-001 decided with three questions open; EPC-002 drafted; E805 overridden; UNK-039 and R-12 written.
---

# 2026-10-09 Epics: Coach team

## Captures

- [decision] (@sim-lead) "Cut one. Lessons ship in January, paper trading follows when we've got the Brightwater terms locked down—that's the whole point." Chosen cut for the Coach team: two epics split by contract, lessons, track and list (CAP-001, CAP-003, CAP-004, CON-001) and paper trading (CAP-002, CON-002, consuming CON-003 and CON-004). Paper trading follows once the Brightwater terms are settled. → keep: [[EPC-001-coach-lessons-and-list#Epic acceptance criteria|EPC-001]] (draft), → keep: [[EPC-002-coach-paper-trading#Epic acceptance criteria|EPC-002]] (draft) ^c01
- [thought] (claude) Rejected cuts. Three epics with the ready track on its own: rejected because it splits CON-001's "whether ready" output from the epic that delivers CON-001. One Coach epic: rejected because lessons could not ship without paper trading, and 4 to 7 criteria cannot cover six items. → drop: recorded as **Options considered:** on EPC-001 and EPC-002 ^c02

- [decision] (@sim-lead) "Park \"ready\"—we're not showing it till after January anyway." No requirement on CAP-003 is written now; the meaning of ready ([[11-unknowns-and-risks#UNK-018 Who writes the lessons and defines ready|UNK-018]]) waits until after January, and EPC-001 lists it under Out of scope. → keep: [[EPC-001-coach-lessons-and-list#Out of scope|EPC-001]] (decided) ^c03

- [decision] (@sim-lead) "Override them. Counsel cleared the stock list in writing, we know Brightwater's review is ten days per their response, and the CFO holds the budget. R-FIN-02 and R-DAT-10 belong to compliance and legal." Override of E805 for the high-severity questions the epics gate lists. The reasons are the lead's belief: counsel's clearance of the stock list in writing, Brightwater's ten-day review (SRC-13), the CFO holding the budget, and R-FIN-02 and R-DAT-10 being compliance's and legal's. None is a sourced fact yet. → drop: carried by the page-level **Override:** under ## History on 11-unknowns-and-risks.md ^c04

- [decision] (@sim-lead) "1 yes. 2 yes, cut \"which still counts toward ready\"—not showing that yet. 3, 4, 5 yes." Explicit yes to each of EPC-001's criteria 1 to 5, with criterion 2 reworded to drop "which still counts toward ready". Awaiting the yes to the read-back. → keep: [[EPC-001-coach-lessons-and-list#Epic acceptance criteria|EPC-001]] (decided) ^c05
- [decision] (@sim-lead) "Agenda confirmed, I'm @sim-lead." GATE-3 yes for the agenda of EPC-001 and EPC-002. The epic's owner is present. → drop: recorded in ## Agenda ^c06
- [decision] (@sim-lead) "On the three open: Q-OPS-03 goes to the Coach team's lead. Q-REG-01 and Q-REG-05 go to compliance and counsel—lock it, those become owned risks for the build team." Q-OPS-03 goes to the Coach team's lead; Q-REG-01 and Q-REG-05 go to compliance and counsel; EPC-001 is decided with Q-OPS-03, Q-REG-01 and Q-REG-05 open (W807), the lead's word. No handle is named for the Coach team's lead. → keep: [[EPC-001-coach-lessons-and-list#Epic acceptance criteria|EPC-001]] (decided), → keep: [[11-unknowns-and-risks#R-12 Sold-across-parties questions rest with the build team|R-12]] (open) ^c07

- [decision] (@sim-lead) "Coach team lead—honestly not sure the handle yet, that's on the CTO. Yes to EPC-001, lock it. I'll get the name to you today." Explicit yes to the read-back of EPC-001's five criteria. The Coach team lead's handle is not known; the CTO is to name them, and the lead will bring the name today. Q-OPS-03 waits on that name. → keep: [[EPC-001-coach-lessons-and-list#Epic acceptance criteria|EPC-001]] (decided), → keep: [[11-unknowns-and-risks#UNK-039 Who leads the Coach team|UNK-039]] (open) ^c08

## Changes

| ID | From | To | Source |
|---|---|---|---|
| EPC-001 | - | draft | [[2026-10-09-coach-epics#^c01]] |
| EPC-001 | draft | decided | [[2026-10-09-coach-epics#^c08]]; decided with Q-OPS-03, Q-REG-01 and Q-REG-05 open (W807) |
| EPC-002 | - | draft | [[2026-10-09-coach-epics#^c01]] |
| UNK-039 | - | open | [[2026-10-09-coach-epics#^c08]] |
| R-12 | - | open | [[2026-10-09-coach-epics#^c07]] |

## Agenda

- EPC-001: GATE-3 confirmed yes, status decided
- EPC-002: GATE-3 confirmed yes, status open
