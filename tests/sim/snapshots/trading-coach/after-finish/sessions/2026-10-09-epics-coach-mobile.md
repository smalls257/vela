---
id: 2026-10-09-epics-coach-mobile
type: session
title: "Epics: Coach team and mobile team"
date: 2026-10-09
modes: [epics, shape, grill]
status: closed
summary: Decided EPC-002 (Coach paper trading) under a GATE-4 override with UNK-059 and UNK-060 open, due 16 Oct. Drafted EPC-003 (reader identity), and reopened CON-004 to assumption.
---

# 2026-10-09 Epics: Coach team and mobile team

## Captures

- [decision] (@sim-lead) "Go with A, unblocks Coach fast. Keep Coach as is, just grill EPC-002. Screens being invisible bugs me a bit, but you're right, they'll show in rollout." Chosen cut for the mobile team: one identity epic delivering CON-005 only. The coach screens get no epic; their consumer side is named in the rollout notes. The Coach cut stays as chosen in [[2026-10-09-coach-epics#^c01]], and EPC-002 is grilled in this session. → keep: [[EPC-003-reader-identity-to-coach#Epic acceptance criteria|EPC-003]] (draft) ^c01
- [thought] (claude) Rejected mobile cuts. B, one mobile epic holding identity and the coach screens: rejected, identity could not ship ahead of the screens and the screens have no contract of their own to hold a criterion to. C, two mobile epics, identity then screens: rejected, the screens epic delivers no capability or contract of its own and would fail T6. → drop: recorded as **Options considered:** on EPC-003 ^c02
- [decision] (@sim-lead) "Yes, confirmed." GATE-3 yes for the agenda of EPC-002 (the mobile epic EPC-003 is not on the agenda and stays draft). The lead asked what risk the open data questions carry to the brief before signing off the epic, and has not yet said which open questions to take. → drop: recorded in ## Agenda ^c03
- [decision] (@sim-lead) "Take them. Honestly not sure on both. Partnerships on Brightwater, @privacy-lead on lawful basis. Set ask-by dates and we move." The lead does not know the answers to Q-DAT-01 and Q-DAT-02. Q-DAT-01 (Brightwater and any new party) becomes UNK-059, asked of partnerships; Q-DAT-02 (lawful basis) becomes UNK-060, asked of @privacy-lead. Both block EPC-002, with ask-by 2026-10-16 proposed by Claude. "We move" is read as going on with the grill of EPC-002 with these two open, which is an override of GATE-4; the lead has not yet confirmed that reading. → drop: carried by UNK-059 and UNK-060 ^c04
- [decision] (@sim-lead) "Yes." Explicit yes to EPC-002 criterion 1, as written. Awaiting the yes to each other criterion and to the read-back. → drop: recorded when EPC-002 is decided ^c05
- [decision] (@sim-lead) "Yes." Explicit yes to EPC-002 criterion 2, as written, without the 15-minute limit. → drop: recorded when EPC-002 is decided ^c06
- [decision] (@sim-lead) "Yes." Explicit yes to EPC-002 criterion 3, as written. → drop: recorded when EPC-002 is decided ^c07
- [thought] (@sim-lead) "Partnerships confirmed the license terms in October—clause 9 lets us value positions on Quoteline's delayed quotes. Criterion 4 forbids what we're licensed to do. Change it." The lead's own account, second-hand from partnerships; no source is registered and no document is named, so it is not a fact and UNK-038 stays open. It contradicts CON-004, which is decided for display only. EPC-002 criterion 4 is not confirmed; a rewrite is proposed and waits on the lead's answers. → drop: waits on source and on CON-004 ^c08
- [decision] (@sim-lead) "Partnerships confirmed that clause 9 covers valuing positions on delayed quotes. You're right on CON-004 though—it's decided and this contradicts it, so reopen it and use the proposed wording. Valuation stays out of scope, that's CAP-002's job." The lead repeats the second-hand claim and names no document, so it stays the lead's account and UNK-038 stays open. CON-004 is set back from decided to assumption. The lead also asks for the proposed wording of criterion 4 and for valuation to stay out of scope; those two instructions conflict, and criterion 4 stays unconfirmed until the lead picks one. → keep: [[coach-building-blocks#CON-004 Quoteline delayed quotes|CON-004]] (assumption) ^c09
- [decision] (@sim-lead) "Yes, (a) is right. You walked me through the contradiction—valuation out of scope means no valuation in the criterion. Prices on CON-002 come from CON-004 labelled as delayed, that's it." Explicit yes to EPC-002 criterion 4 as reworded: prices on CON-002 come from CON-004 labelled as delayed by 15 minutes, with no statement on valuation. Valuation is listed under Out of scope, waiting on CAP-002 and UNK-038. → drop: recorded when EPC-002 is decided ^c10
- [decision] (@sim-lead) "Yes." Explicit yes to EPC-002 criterion 5, as written. → drop: recorded when EPC-002 is decided ^c11
- [decision] (@sim-lead) "Yes. You're right—we're holding the behaviour, not the switch design. Rewrite passes." Explicit yes to EPC-002 criterion 6 as reworded: while paper trading has not been released, CON-002 accepts no paper order and replies that paper trading is not yet available. The original named the release switch, a part of Coach's Stock list container. → drop: recorded when EPC-002 is decided ^c12
- [decision] (@sim-lead) "Yes. Coach holds the record by the partnership agreement, so that's locked in. The gap on Coach exiting Brightwater is fine—that's a different conversation if it even happens, and the epic's scope is Brightwater withdrawing." Explicit yes to EPC-002 criterion 7, as written, covering Brightwater's notice only. The claim that the partnership agreement makes Coach the record is the lead's account; the agreement's full text is not held (UNK-056), so UNK-029 stays open. → drop: recorded when EPC-002 is decided ^c13
- [decision] (@sim-lead) "Yes. All seven confirmed, unknowns owned with dates, override reason is right. That's the final set." Explicit yes to the read-back of EPC-002's seven criteria (criteria 4 and 6 as reworded in this session), and to the GATE-4 override for UNK-059 and UNK-060. EPC-002 is decided with Q-DAT-01, Q-DAT-02, Q-REG-01 and Q-REG-05 open (W807). → keep: [[EPC-002-coach-paper-trading#Epic acceptance criteria|EPC-002]] (decided) ^c14
- [decision] (@sim-lead) "Override—UNK-059 and 060 are owned and due the 16th. January demo is just the board seeing where we go—the rest don't block it. We need the team building." Override of E805 for the 31 high-severity questions the epics gate lists. The reasons are the lead's belief, not sourced facts: UNK-059 and UNK-060 are owned and due 2026-10-16, and the January demo is only the board seeing where the work goes. Only two of the 31 are those unknowns; the rest stay open and are not answered by this override. → drop: carried by the page-level **Override:** under ## History on 11-unknowns-and-risks.md ^c15
- [worry] (@sim-lead) "October 16th's tight—privacy especially. If they can't clear a lawful basis for holding the record, Coach's whole design breaks and we're reworking after the board demo. That's my one risk sitting right now." The lead's own worry about UNK-060 (the lawful basis for what Coach holds, asked of @privacy-lead, due 2026-10-16). It is their word that the date is tight and that a "no" would mean reworking Coach after the board demo; nothing in the vault sources either claim. → keep: [[11-unknowns-and-risks#UNK-060 Lawful basis for the data Coach holds|UNK-060]] (open) ^c16

## Changes

| ID | From | To | Source |
|---|---|---|---|
| EPC-003 | - | draft | [[2026-10-09-epics-coach-mobile#^c01]] |
| UNK-059 | - | open | [[2026-10-09-epics-coach-mobile#^c04]] |
| UNK-060 | - | open | [[2026-10-09-epics-coach-mobile#^c04]] |
| EPC-002 | draft | decided | [[2026-10-09-epics-coach-mobile#^c14]]; decided with Q-DAT-01, Q-DAT-02, Q-REG-01, Q-REG-05 open (W807) |
| CON-004 | decided | assumption | [[2026-10-09-epics-coach-mobile#^c09]] |
| Q-DAT-01@INI-001 | open | unknown | [[2026-10-09-epics-coach-mobile#^c04]] |
| Q-DAT-02@APP-coach | open | unknown | [[2026-10-09-epics-coach-mobile#^c04]] |

## Agenda

- EPC-002: GATE-3 confirmed yes, status decided, override: GATE-4
