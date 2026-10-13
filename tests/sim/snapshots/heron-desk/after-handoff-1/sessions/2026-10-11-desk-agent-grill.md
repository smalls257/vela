---
id: 2026-10-11-desk-agent-grill
type: session
title: "Grill: desk agent handover"
date: 2026-10-11
modes: [grill]
status: closed
summary: UNK-010 blocks EPC-001 to EPC-004 and R-FIN-10 waits on it; seven reviewer questions and UNK-028 opened; the epics stay draft.
---

# 2026-10-11 Grill: desk agent handover

## Captures

- [instruction] (@sim-lead) "Carry it untouched—good call, it's generated. The grill is on the epics: EPC-001 through EPC-004, and which ones actually hand over to @agent-lead once the constraints firm up." → drop: a process instruction, nothing to keep ^c01

- [instruction] (@sim-lead) "Yes to the agenda." Agenda confirmed for EPC-001, EPC-002, EPC-003, EPC-004. → drop: a process instruction, nothing to keep ^c02
- [thought] (@sim-lead) "The CTO named @agent-lead on the 9th—they take it from handoff." Stated as a belief with no source in the vault; no date, document or channel yet. → keep: [[11-unknowns-and-risks#UNK-028 Where the CTO named @agent-lead|UNK-028]] (open) ^c03
- [thought] (@sim-lead) "we don't have a budget holder for Heron. That's the gate—R-FIN-10." Take R-FIN-10 first. → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-10]] (unknown) ^c04
- [decision] (@sim-lead) "Yes to the gate—UNK-010 blocks the epics." R-FIN-10 waits on UNK-010 and UNK-010 blocks EPC-001, EPC-002, EPC-003, EPC-004; the four epics stay draft. → keep: [[11-unknowns-and-risks#UNK-010 Who owns Heron|UNK-010]] (open) ^c05
- [thought] (@sim-lead) "The CTO's 9 October message named them; I'll get the exact channel when I'm back at the desk." Channel not yet given, so @agent-lead's naming stays a belief, not a fact. → keep: [[11-unknowns-and-risks#UNK-028 Where the CTO named @agent-lead|UNK-028]] (open) ^c06
- [thought] (@sim-lead) waits on UNK-010: R-FIN-10 → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-10]] (unknown) ^c07

## Changes

| ID | From | To | Source |
|---|---|---|---|
| R-FIN-10 | open | unknown | [[2026-10-11-desk-agent-grill#^c07]] |
| UNK-028 | - | open | [[2026-10-11-desk-agent-grill#^c06]] |
| R-FIN-11 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |
| R-DAT-15 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |
| R-DAT-16 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |
| R-PTN-08 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |
| R-PTN-09 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |
| R-REG-09 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |
| R-OPS-08 | - | open | [[2026-10-11-desk-agent-grill#1. On the agenda (EPC-001 to EPC-004), 2026-10-11]] |

## Agenda

- EPC-001: GATE-3 confirmed yes, status off-agenda: UNK-010
- EPC-002: GATE-3 confirmed yes, status off-agenda: UNK-010
- EPC-003: GATE-3 confirmed yes, status off-agenda: UNK-010
- EPC-004: GATE-3 confirmed yes, status off-agenda: UNK-010

## Reviews

### 1. On the agenda (EPC-001 to EPC-004), 2026-10-11

- **Coverage:** FIN found 2, 1 dropped; DAT found 4, 2 dropped; PTN found 3, 5 dropped; REG found 3, 6 dropped; OPS found 7, 3 dropped
- **Dropped:** 17 findings dropped by the merge: 6 because the quote did not mention what the finding is about (1 FIN, 2 DAT, 1 PTN, 1 OPS, and 1 more PTN), and 11 because they named a reviewer-question ID the vault does not hold (PTN R-PTN-02, R-PTN-04, R-PTN-05, R-PTN-06; REG R-REG-02, R-REG-04, R-REG-05, R-REG-06, R-REG-07, R-REG-08; OPS R-OPS-04, R-OPS-06).
- **Merged:** [OPS] into F1.9: Is @agent-lead one person or a team, and does that team accept ownership of all four epics and of running Heron after the pilot? Who answers UNK-010 (who owns, operates and pays for Heron)?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | R-FIN-08 | If the pilot laptops cannot build the note ten minutes before a call, who pays for better hardware, a lighter design or a later pilot? Is the 'late, marked as late' behaviour in EPC-004 accepted as the fallback? | "Whether the pilot laptops can build the note in time is open as UNK-027." in [[EPC-004-note-or-reason]] |
| F1.2 | FIN | high | new | Has @agent-lead's budget holder agreed to carry the build and running cost and the support liability for EPC-001 to EPC-004, given that nobody has said who pays for Heron? | "- **Owning team:** @agent-lead" in [[EPC-001-calendar]] |
| F1.3 | DAT | normal | R-DAT-05 | Can Heron read transcripts only for meetings the pilot user organised, or for all they attended? Who grants the tenant admin approval, and on what scope? Which acceptance criterion in EPC-003 records the answer? | "drawn only from what the call tool left behind about that call (CON-003)" in [[EPC-003-call-tool-records]] |
| F1.4 | DAT | normal | R-DAT-09 | Where is a built note stored, how long is it kept, and is a withdrawn or past note deleted? Which epic owns that, and does the impact assessment cover it? | "no note is shown for that call and a note already built for it is withdrawn" in [[EPC-001-calendar]] |
| F1.5 | DAT | high | new | What lawful basis and what limits apply to personal and client data in the chosen folder? Should EPC-002 name the unknown that gates it, and does the works council data list need to cover the folder? | "the note uses only the files that relate to the call's client" in [[EPC-002-chosen-folder]] |
| F1.6 | DAT | high | new | If the DPO says invitees who never join cannot be named, which EPC-001 criterion changes? Should the epic be held until UNK-023 and UNK-025 answer? | "everyone invited appears except those who have declined" in [[EPC-001-calendar]] |
| F1.7 | PTN | normal | R-PTN-07 | Who runs the April review, what must be agreed with Microsoft, the call-tool parties and the works councils before the 1 June general release, and which year is meant? | "The works council takes Heron at its December meeting and will not agree before it has read the full list of data Heron reads" in [[02-constraints]] |
| F1.8 | PTN | normal | new | If Legal or the call-tool terms refuse reuse of call records, does EPC-003 drop or change, and what then happens to EPC-004's dependency on it? | "It waits on Legal and on which call tools are in use." in [[EPC-003-call-tool-records]] |
| F1.9 | PTN, OPS | high | new | Who owns, operates and pays for Heron after handover, under what agreement, and is @agent-lead's team confirmed to take it on? | "- **Owning team:** @agent-lead" in [[EPC-001-calendar]] |
| F1.10 | REG | normal | Q-REG-02@INI-001 | Is anything Heron reads or does (calendar entries, call records, folder files, names of client attendees) regulated or licensed? Who is checking, and is the DPO's impact assessment needed before the Grill accepts the epics? | "The rest of the DPO's view waits for the impact assessment" in [[02-constraints]] |
| F1.11 | REG | normal | Q-REG-05@INI-001 | If the calendar read, the call tool records or the client engagement terms do not permit what Heron does, who is liable to the client and to the pilot user, and which agreement says so? | "what do the engagement letters allow Heron to do with them?" in [[11-unknowns-and-risks]] |
| F1.12 | REG | high | new | Which is the committed read scope: meetings, email and documents (goals), or only calendar entries, the chosen folder and call tool records (EPC-002)? Which page owns the value that goes to the works council and the CISO? | "quietly watches meetings, email and documents" in [[01-goals]] |
| F1.13 | OPS | high | new | Can EPC-001 and EPC-002 really start before the CISO's answer on UNK-020 and the review outcome due 4 December? If not, which epics can be handed to @agent-lead now? | "None. This epic can start without waiting on another epic." in [[EPC-001-calendar]] |
| F1.14 | OPS | high | R-OPS-07 | Who asks the DPO about UNK-023 and UNK-024, and who asks Legal about UNK-025? Has Sam Hadley agreed to the pilot and to answering UNK-008, UNK-021 and UNK-022 by the ask-by dates? | "Whether Legal allows the call records to be reused, and client attendees named, is open as UNK-025 and gates this epic." in [[EPC-003-call-tool-records]] |
| F1.15 | OPS | normal | R-OPS-05 | What must be running on the pilot laptops for the note to appear on time, and who supports the pilot team, in hours and out of hours, when it does not? | "Whether the pilot laptops can build the note in time is open as UNK-027." in [[EPC-004-note-or-reason]] |
| F1.16 | OPS | normal | R-OPS-07 | Who asks Sam Hadley's team about the daily folder habit before the epics are handed over, and what is the plan if they will not do it? | "Nobody has asked them." in [[11-unknowns-and-risks]] |
| F1.17 | OPS | normal | Q-OPS-04@INI-001 | Is any other tool, team or scheme already doing this prep job, and which of EPC-002 and EPC-003 owns the use of the folder files in the note? | "the note gives a short account of the most recent earlier call, drawn only from what the call tool left behind about that call (CON-003) and from files in the chosen folder (CON-002)" in [[EPC-003-call-tool-records]] |
| F1.18 | OPS | normal | Q-OPS-05@INI-001 | Does Heron replace anything people use today, and who still depends on it (for example assistants, shared notes or call-tool summaries)? | "Today they piece it together themselves." in [[CAP-001-prepare-a-client-for-a-call]] |
