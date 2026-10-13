---
id: 2026-10-11-prep-note-requirements
type: session
title: "Requirements: prep note requirements"
date: 2026-10-11
modes: [requirements]
status: closed
summary: Wrote CAP-001's five requirements at assumption, opened UNK-021 to UNK-025, and recorded the review's findings in the question ledger.
---

# 2026-10-11 Requirements: prep note requirements

## Captures

- [thought] (@sim-lead) "Yes to override. Just CAP-001. prep-note-requirements." agrees to write requirements against the strategy at `assumption`, and limits the capabilities in scope to CAP-001 → drop: recorded as the Override bullet under History ^c01

- [thought] (@sim-lead) "Yes to that timing—build as soon as it's known, show at ten." confirms the timing of the note, built when the call is known and shown ten minutes before the start → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR1 Note before a client call|CAP-001.FR1]] (assumption) ^c02
- [thought] (@sim-lead) "I don't know how Sam marks a client call on the calendar." how a call is marked as a client call is not known; Sam Hadley (`@pilot-lead`) runs the team's calendars → keep: [[11-unknowns-and-risks#UNK-021 How a client call is marked|UNK-021]] (open) ^c03
- [thought] (@sim-lead) "Yes to FR1. Sam's the right call—he runs the team's calendars. I'll get him the question this week." says yes to CAP-001.FR1 as read back and names `@pilot-lead` as the person to ask → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR1 Note before a client call|CAP-001.FR1]] (assumption) ^c04
- [thought] (@sim-lead) "Write it like that. Calendar's the source of truth—declines out, late joiners don't show, lists expand only if the calendar names them, name and org is right. That's the DPO constraint." says yes to CAP-001.FR2 as read back: the calendar entry is the only source of who is on the call, and the note shows name and organisation only (CST-6) → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR2 Who is on the call|CAP-001.FR2]] (assumption) ^c05
- [thought] (@sim-lead) "Yes to all of that. That's the right boundary. Next." says yes to CAP-001.FR3 as read back: last time is the most recent earlier call with the same client, open points come only from a call tool record or a file in the chosen folder, and nothing is reached back to when the last call left nothing readable → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR3 Last time and what is open|CAP-001.FR3]] (assumption) ^c06
- [thought] (@sim-lead) "Yes, record it—fold it in with Sam when you ask UNK-021." the way an earlier call is matched to the same client is not known; to be asked of `@pilot-lead` together with UNK-021 → keep: [[11-unknowns-and-risks#UNK-022 How an earlier call is matched to the same client|UNK-022]] (open) ^c07
- [thought] (@sim-lead) "On FR4, yes, write it like that." says yes to CAP-001.FR4 as read back: no note until a folder is chosen, a missing or empty folder is named in the note, and mixed folders are used only for the call's client → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR4 The person chooses the folder|CAP-001.FR4]] (assumption) ^c08
- [thought] (@sim-lead) "Yes to all of it. Show late, marked clearly. Next." says yes to CAP-001.FR5 as read back: every client call gets a note or a reason for none, and a late note is shown, clearly marked as late → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR5 A note, or the reason for none|CAP-001.FR5]] (assumption) ^c09
- [thought] (claude) Rules left out of CAP-001's requirements because they are concerns, not functions: no text leaves the laptop (CST-3), the note must be plainer and not sent to a hosted model if no model on the laptop writes it well enough, and the note must be ready in time on the pilot team's laptops. For [[concern-data]], [[concern-security]] and [[concern-operations]]. → park ^c10
- [thought] (@sim-lead) "Yes to the DPO unknowns, block both." the invitee list and the reach of the DPO's name rule are open with the DPO, and each blocks its requirement (F1.12 and F1.6) → keep: [[11-unknowns-and-risks#UNK-023 Invitees and the DPO rule|UNK-023]] (open) ^c11
- [thought] (@sim-lead) "Yes to the DPO unknowns, block both." the reach of the DPO's name rule over the whole note blocks CAP-001.FR3 (F1.6) → keep: [[11-unknowns-and-risks#UNK-024 DPO rule across the whole note|UNK-024]] (open) ^c12
- [thought] (@sim-lead) "the reuse question is critical, not wait-and-grill—I'll get that with Legal this week alongside the engagement letters." the lawful basis and client notice for reusing call records and naming client attendees go to Legal this week (F1.5, F1.13) → keep: [[11-unknowns-and-risks#UNK-025 Reusing call records and client names|UNK-025]] (open) ^c13
- [thought] (@sim-lead) "F1.18 links to UNK-008." the share of calls with a readable record depends on which call tools are in use, so FR3 links the existing unknown → keep: [[CAP-001-prepare-a-client-for-a-call#CAP-001.FR3 Last time and what is open|CAP-001.FR3]] (assumption) ^c14

## Reviews

### 1. After the requirements are written, CAP-001, 2026-10-11

- **Coverage:** FIN found 3; DAT found 5; PTN found 1, 4 dropped; REG found 4, 1 dropped; OPS found 7, 2 dropped
- **Dropped:** PTN: What notice does a change to the Zoom agreement need, and who must give it? If no agreement is known, who will find out? (its quote '**Agreements:** none known' has fewer than 4 words, too few to show where it came from); PTN: Do the call tool terms (Teams, Zoom) and the clients' engagement letters allow Heron to read and summarise records and files from client calls? Who will confirm this before FR3 is relied on? (it names R-PTN-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own); PTN: Which Microsoft agreement covers Heron's calendar read, and does reading attendee names and organisations stay inside it? (it names R-PTN-04, which this vault does not owe and has no open reviewer question for; write new for a question of your own); PTN: Who owns, operates and pays for Heron, and under what agreement? Does CAP-001 assume an owner or supplier that is not yet named? (its quote '[[heron-building-blocks|Heron]] delivers it.' has fewer than 4 words, too few to show where it came from); REG: Is any part of the prep note regulated or licensed: client call records, client attendee data, or the calendar read? Who confirms that, and by when? (its quote 'what the engagement letters allow Heron to do with them' is not in the written text of [[11-unknowns-and-risks]]); OPS: Has the solution lead told the product owner and the CIO that the digest and the adoption dashboard are out of the first release, and do they agree? (it names R-OPS-04, which this vault does not owe and has no open reviewer question for; write new for a question of your own); OPS: ”@sim-lead”' has fewer than 4 words, too few to show where it came from: Which team owns the prep note once it is live, including support when a note is late or missing, and who chases UNK-021 and UNK-022 with Sam by 16 October? (its quote 'owner)
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | R-FIN-02 | Where does the prep note get written and where is its data kept: on the laptop, or in a hosted service? Who pays for that compute or hosting, and who carries the risk if it fails or is refused? | "the note must be plainer and not sent to a hosted model if no model on the laptop writes it well enough" in [[2026-10-11-prep-note-requirements]] |
| F1.2 | FIN | normal | new | Does reading what each call tool leaves behind need a licence, API access or agreement, and who holds and pays for it? | "It draws only on what the call tool left behind and on the one folder the person chose." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.3 | FIN | normal | new | Can the pilot team's laptops write the note on the device in time? If not, who pays for hardware, a lighter design or a delay? | "the note must be ready in time on the pilot team's laptops" in [[2026-10-11-prep-note-requirements]] |
| F1.4 | DAT | normal | R-DAT-05 | Does the last-time account read only transcripts of meetings the pilot user organised, or all they attended? Who grants the tenant admin approval for reading transcripts, and on what scope? | "It says Teams transcripts exist only where the meeting's organiser turned them on, and that they sit in the organiser's OneDrive." in [[03-context-and-scope]] |
| F1.5 | DAT | high | new | Were the clients and attendees of past calls told their call records could be reused to prepare later calls? On what lawful basis does Heron reuse them, for both Teams and Zoom calls? | "The account uses only what the call tool left behind about that call and the files in the chosen folder." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.6 | DAT | high | new | Does the DPO's rule that only people in the meeting may be named apply to the whole prep note, including the last-time account and open points? If so, how are other people's names kept out of the text drawn from calls and files? | "The note carries no remark about anyone's mood, tone or performance." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.7 | DAT | normal | new | What kinds of file may be in the chosen folder, and what data in them (client data under engagement letters, other staff's personal data) may Heron lawfully use for a prep note? | "From a folder that holds files for several clients, the note uses only the files that relate to the call's client, matched as for CAP-001.FR3." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.8 | DAT | normal | new | Where is a built note stored, how long is it kept, and is a withdrawn or past note deleted? Does the data protection impact assessment need to cover this? | "The note is built as soon as the call is known and shown at ten minutes before the start." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.9 | PTN | normal | Q-PTN-03@PTY-02 | Is Zoom in use at the firm, and if so who holds the agreement with Zoom, when does it end, and what does leaving or changing it cost? | "Whether Zoom is in use at the firm is not recorded." in [[03-context-and-scope]] |
| F1.10 | REG | normal | Q-REG-05@INI-001 | If the prep note is wrong or missing, or a call tool or Microsoft read fails, who answers to the person and to the client? Does any contract say so? | "so the person is never left with silence" in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.11 | REG | high | R-REG-05 | Has the DPO been asked whether CST-6 applies to the prep note, and does the impact assessment cover the prep note? Who owns that, and by when? | "The rest of the DPO's view waits for the impact assessment" in [[02-constraints]] |
| F1.12 | REG | high | new | Does the DPO's rule that a note names only people who were in the meeting allow a pre-call list of invitees who have not declined? If not, how does FR2 change? | "Everyone invited on the calendar entry appears, except those who have declined." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.13 | REG | high | new | What lawful basis and what client notice cover Heron using client attendees' names, organisations and past call records? Does Legal need to clear this before FR2 and FR3 are accepted? | "It shows each one's name and organisation, and no one who was not in the meeting." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.14 | OPS | normal | Q-OPS-04@INI-001 | Do any people, assistants, tools or team-specific practices already prepare pilot staff for client calls, and are there other desk-helper or briefing efforts in the firm? Name them. | "Today they piece it together themselves." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.15 | OPS | normal | Q-OPS-05@INI-001 | Does the prep note retire anything, such as the team's manual preparation routine, shared briefing files or an assistant's task? If so, who still depends on it? | "Today they piece it together themselves." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.16 | OPS | normal | R-OPS-02 | Who runs and supports the helper during the pilot, who in IT will package it (the 18 January slot is booked but unconfirmed), and who set the 10 November pack deadline? | "The security pack goes to the CISO's review by 10 November 2026" in [[02-constraints]] |
| F1.17 | OPS | normal | R-OPS-03 | What is the plan for Frankfurt and other sites between the London pilot and the CIO's firm-wide summer target, and who tells the CIO? | "Frankfurt stays out of the pilot" in [[02-constraints]] |
| F1.18 | OPS | high | Q-OPS-07@INI-001 | Which call tools leave a readable record on Mac and Windows for the pilot team's client calls, and what share of client calls will therefore get the 'last time' content and not the 'nothing readable' message? | "It draws only on what the call tool left behind and on the one folder the person chose." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.19 | OPS | normal | Q-OPS-06@INI-001 | Who else is affected by the note naming them (clients, Frankfurt colleagues, assistants who manage calendars) and has anyone asked them? | "It shows each one's name and organisation, and no one who was not in the meeting." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.20 | OPS | normal | new | What must be running on the laptop for the note to appear on time, and who supports the pilot team when it does not? | "A note that is not ready by ten minutes before the call is shown as soon as it is ready, clearly marked as late, and is not dropped." in [[CAP-001-prepare-a-client-for-a-call]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| CAP-001.FR1 | - | assumption | [[2026-10-11-prep-note-requirements#^c04]] |
| UNK-021 | - | open | [[2026-10-11-prep-note-requirements#^c03]] |
| CAP-001.FR2 | - | assumption | [[2026-10-11-prep-note-requirements#^c05]] |
| CAP-001.FR3 | - | assumption | [[2026-10-11-prep-note-requirements#^c06]] |
| UNK-022 | - | open | [[2026-10-11-prep-note-requirements#^c07]] |
| CAP-001.FR4 | - | assumption | [[2026-10-11-prep-note-requirements#^c08]] |
| CAP-001.FR5 | - | assumption | [[2026-10-11-prep-note-requirements#^c09]] |
| UNK-023 | - | open | [[2026-10-11-prep-note-requirements#^c11]] |
| UNK-024 | - | open | [[2026-10-11-prep-note-requirements#^c12]] |
| UNK-025 | - | open | [[2026-10-11-prep-note-requirements#^c13]] |
| Q-OPS-07@INI-001 | unknown | unknown | [[2026-10-11-prep-note-requirements#^c14]] |
| R-DAT-06 | - | unknown | [[2026-10-11-prep-note-requirements#^c13]] |
| R-DAT-07 | - | unknown | [[2026-10-11-prep-note-requirements#^c11]] |
| R-REG-06 | - | unknown | [[2026-10-11-prep-note-requirements#^c11]] |
| R-REG-07 | - | unknown | [[2026-10-11-prep-note-requirements#^c13]] |
| R-FIN-07 | - | open | [[2026-10-11-prep-note-requirements#1. After the requirements are written, CAP-001, 2026-10-11]] |
| R-FIN-08 | - | open | [[2026-10-11-prep-note-requirements#1. After the requirements are written, CAP-001, 2026-10-11]] |
| R-DAT-08 | - | open | [[2026-10-11-prep-note-requirements#1. After the requirements are written, CAP-001, 2026-10-11]] |
| R-DAT-09 | - | open | [[2026-10-11-prep-note-requirements#1. After the requirements are written, CAP-001, 2026-10-11]] |
| R-OPS-05 | - | open | [[2026-10-11-prep-note-requirements#1. After the requirements are written, CAP-001, 2026-10-11]] |

## History

- **Override:** "Requirements: the strategy is not `decided`" by @sim-lead on 2026-10-11: "Yes to override." (no reason given, the earlier boundary override gave: "If the strategy flips, we recut.") [[2026-10-11-prep-note-requirements#^c01]]
