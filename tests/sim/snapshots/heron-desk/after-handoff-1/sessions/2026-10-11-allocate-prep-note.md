---
id: 2026-10-11-allocate-prep-note
type: session
title: "Allocate: allocate prep note"
date: 2026-10-11
modes: [allocate]
status: closed
summary: Allocated CAP-001.FR1 to FR5 to Heron and its three contracts as assumptions, opened UNK-026, and tied twelve ledger rows to the unknowns that gate them.
---

# 2026-10-11 Allocate: allocate prep note

## Captures

- [thought] (@sim-lead) "Yes to lines one through four as written." says yes to Heron's share of CAP-001.FR1: it builds the note when the call is known, shows it ten minutes before the start, handles a move or cancellation, and notes only client calls → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR1@APP-heron]] (assumption) ^c01
- [thought] (@sim-lead) "Yes to lines one through four as written." says yes to the obligation CON-001 carries for CAP-001.FR1: Microsoft's calendar sends each entry with its time and attendees, and any move or cancellation, in time for Heron to act → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR1@CON-001]] (assumption) ^c02
- [thought] (@sim-lead) "The CISO's the gate on CON-001; I'll get that sorted today." the CISO decides whether the calendar read over CON-001 may go ahead; the lead takes it up today → keep: [[11-unknowns-and-risks#UNK-020 Calendar read and the device line|UNK-020]] (open) ^c03
- [thought] (@sim-lead) "UNK-021 goes to Sam this week." how a client call is marked stays open as UNK-021, to be asked of `@pilot-lead` this week → keep: [[11-unknowns-and-risks#UNK-021 How a client call is marked|UNK-021]] (open) ^c04
- [thought] (@sim-lead) "Yes to one through three." says yes to Heron's share of CAP-001.FR2: it lists the people on the call from the calendar entry only, leaves out those who declined and uninvited joiners, expands a list only when the entry names its members, and shows name and organization only → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR2@APP-heron]] (assumption) ^c05
- [thought] (@sim-lead) "Yes to one through three." says yes to the obligation CON-001 carries for CAP-001.FR2: each calendar entry carries every invitee's name and organization, their replies, and the members of a list when the entry names them → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR2@CON-001]] (assumption) ^c06
- [thought] (@sim-lead) "Honestly not sure if the organization field comes through—that's @endpoint-lead's territory. I'll ask him alongside the CISO question about whether a calendar read counts as text off the device." whether the calendar entry carries an attendee's organization is not known; `@endpoint-lead` would know → keep: [[11-unknowns-and-risks#UNK-026 Whether the calendar entry carries an attendee's organization|UNK-026]] (open) ^c07
- [thought] (@sim-lead) "Yes to lines one through four." says yes to Heron's share of CAP-001.FR3: it finds the most recent earlier call with the same client, gives a short account and the open points from call tool records and chosen-folder files only, adds none of its own, says so when nothing is readable, and makes no remark on mood, tone or performance → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR3@APP-heron]] (assumption) ^c08
- [thought] (@sim-lead) "Yes to lines one through four." says yes to the obligation CON-003 carries for CAP-001.FR3: for each call the call tool leaves a readable record tied to that call → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR3@CON-003]] (assumption) ^c09
- [thought] (@sim-lead) "Yes to lines one through four." says yes to the obligation CON-002 carries for CAP-001.FR3: the files in the chosen folder can be read and nothing is written back → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR3@CON-002]] (assumption) ^c10
- [thought] (@sim-lead) "Yes to lines one through four." says yes to the obligation CON-001 carries for CAP-001.FR3: past calendar entries come with their attendees → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR3@CON-001]] (assumption) ^c11
- [thought] (@sim-lead) "CON-001 will need to say it includes the past entries, and that's on the CISO when he calls—it feeds into the calendar question. UNK-022 and UNK-024 are already owned, so we're good." CON-001's wording must later say it includes past entries, which depends on the CISO's answer on the calendar read; no new unknown, as UNK-022 and UNK-024 are already owned → keep: [[11-unknowns-and-risks#UNK-020 Calendar read and the device line|UNK-020]] (open) ^c12
- [thought] (@sim-lead) "Yes to lines one through four as written. Folder scope's clean, and CON-002 handles it. That's exactly what keeps it safe." says yes to Heron's share of CAP-001.FR4: the person names and changes one folder, Heron reads nothing else of theirs apart from the calendar and call tool records, and the note says when no folder is set or the folder is missing or empty → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR4@APP-heron]] (assumption) ^c13
- [thought] (@sim-lead) "Yes to lines one through four as written. Folder scope's clean, and CON-002 handles it. That's exactly what keeps it safe." says yes to the obligation CON-002 carries for CAP-001.FR4: the person can name a folder on the same laptop and change it later, and Heron can tell whether it is missing or empty → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR4@CON-002]] (assumption) ^c14
- [thought] (@sim-lead) "Yes to lines one through four as written. That's all five done then—commit it and we're through CAP-001." says yes to Heron's share of CAP-001.FR5: every client call gets a note or a reason for none, a first call still lists who is on it, an unreadable call tool record is said so, a late note is shown marked as late, and a message never replaces the list of people → keep: [[heron-building-blocks#Requirements allocated|CAP-001.FR5@APP-heron]] (assumption) ^c15
- [thought] (@sim-lead) "UNK-020's the one for F1.8 and F1.9—CISO call today." waits on UNK-020: F1.8, F1.9 (the calendar read counting as text off the device, and the lawful basis and Frankfurt filter for past entries; ask by 2026-10-15) → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-10]] (unknown); [[11-unknowns-and-risks#Question ledger|R-DAT-11]] (unknown) ^c16
- [thought] (@sim-lead) "F1.4 and F1.16 rest on UNK-016, the Microsoft agreement holder, I'll have by the 23rd." waits on UNK-016: F1.4, F1.16 (the Microsoft agreement holder and the registration timing; ask by 2026-10-23) → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-09]] (unknown); [[11-unknowns-and-risks#Question ledger|R-REG-08]] (unknown) ^c17
- [thought] (@sim-lead) "UNK-017 for the call tools, but Legal also needs the Microsoft terms for Teams—we don't hold the client Zoom agreement." waits on UNK-017: F1.12 (whose terms allow the call tool records CON-003 relies on; Legal also needs the Microsoft terms for Teams, which UNK-017 does not yet name) → keep: [[11-unknowns-and-risks#Question ledger|R-PTN-05]] (unknown) ^c18
- [thought] (@sim-lead) "Yes to the mapping. All five fit." waits on UNK-017: Q-PTN-03@PTY-02, F1.10, Q-PTN-06@PTY-02, F1.11 (the Zoom agreement and its notice; the lead says the firm does not hold the client Zoom agreement) → keep: [[11-unknowns-and-risks#Question ledger|Q-PTN-03@PTY-02]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-06@PTY-02]] (unknown) ^c19
- [thought] (@sim-lead) "Yes to the mapping. All five fit." waits on UNK-012: R-FIN-02, F1.1 (where Heron processes and keeps text, and who carries the laptop compute) → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-02]] (unknown) ^c20
- [thought] (@sim-lead) "Yes to the mapping. All five fit." waits on UNK-008: R-FIN-07, F1.2 (whether reading call tool records needs a license or agreement, which depends on which tools are in use) → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-07]] (unknown) ^c21
- [thought] (@sim-lead) "Yes to the mapping. All five fit." waits on UNK-025: R-DAT-08, F1.6 (what the chosen folder may hold and what Heron may lawfully use from it) → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-08]] (unknown) ^c22
- [thought] (@sim-lead) "Yes to the mapping. All five fit." waits on UNK-011: R-OPS-02, F1.19 (the 10 November deadline, pilot support and IT packaging) → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-02]] (unknown) ^c23
- [thought] (@sim-lead) "R-REG-05 waits on UNK-024." waits on UNK-024: R-REG-05, F1.15 (whether the DPO's name and mood rule applies to the prep note) → keep: [[11-unknowns-and-risks#Question ledger|R-REG-05]] (unknown) ^c24
- [thought] (@sim-lead) "Leave the rest visible. F1.5 about tenant admin approval for transcripts goes to the endpoint lead alongside my other asks this week. F1.20 is the CIO's roadmap gap, not a blocker I own." the remaining findings stay open and visible, with no unknown written; the lead will ask `@endpoint-lead` about F1.5 (R-DAT-05) this week, and F1.20 (R-OPS-03) is the CIO's roadmap gap and not a blocker the lead owns → park ^c25
- [thought] (@sim-lead) "Widen UNK-017 to Teams. One conversation with Legal." the question of UNK-017 now also asks what the Microsoft terms for Teams allow Heron to read of Teams call records, and Legal takes both in one conversation → keep: [[11-unknowns-and-risks#UNK-017 Client Zoom transcripts and engagement letters|UNK-017]] (open) ^c26

## Reviews

### 1. After the rows are written, CAP-001, 2026-10-11

- **Coverage:** FIN found 4; DAT found 5; PTN found 3, 3 dropped; REG found 4, 2 dropped; OPS found 5, 2 dropped
- **Dropped:** PTN: Which Microsoft agreement or API terms cover the calendar read in CON-001, and does it let Heron read past entries, attendee organization and list members? Who holds the agreement (UNK-016)? (it names R-PTN-04, which this vault does not owe and has no open reviewer question for; write new for a question of your own); PTN: If CON-001 needs an app registration, does its six-week review start only after the 4 December outcome? Is the 2 February 2027 pilot start still achievable, and who confirms that with the identity team and the CISO's office? (it names R-PTN-02, which this vault does not owe and has no open reviewer question for; write new for a question of your own); PTN: Do client agreements or engagement letters allow notes, transcripts and client files from the chosen folder to be read and summarized by Heron? Who checks, and by when? (it names R-PTN-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own); REG: Do the FR2 attendee list and the FR3 account have to leave out Frankfurt staff? If so, who owns the filter and the works council's agreement, before FR2 and FR3 are accepted? (the quote does not mention what the finding is about); REG: Does limiting Heron to one chosen folder answer the DPO, Legal and the works council, or must they also agree what the folder files may contain, such as client documents and third-party names? (it is a new question about something already decided, and it is not high severity); OPS: Which team will build Heron and the work behind CON-001 to CON-003, and which team runs it once the pilot starts? (its quote "No epic delivers CAP-001 (new), so nobody is planned to build it." is not in the written text of [[13-epics]]); OPS: How quickly does the calendar read pick up a moved or canceled call, and what does the person see if the change arrives after the note is shown? (it is a new question about something already decided, and it is not high severity)
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | R-FIN-02 | Where does Heron process and keep data, and who pays for and carries the risk of the laptop compute? UNK-012 is still open, so should the page say so? | "It builds the note on the person's own laptop from their calendar and one folder they point it at, then shows it." in [[heron-building-blocks]] |
| F1.2 | FIN | normal | R-FIN-07 | Does reading each call tool's notes or transcript need a license, API access or an agreement, and who holds and pays for it? Can CON-003 stay an assumption without that answer? | "the call tools the pilot team and its clients use, not yet known" in [[heron-building-blocks]] |
| F1.3 | FIN | normal | R-FIN-08 | Can the pilot team's laptops build the note on the device in time? If not, who pays for hardware, a lighter design or a delay? | "If no model on the laptop writes a good enough note, the note is plainer, and there is no hosted fallback." in [[heron-building-blocks]] |
| F1.4 | FIN | high | new | Who holds the Microsoft 365 agreement, does it allow and price Heron's calendar read, and who pays if a registration or extra license is needed? | "Not agreed with Microsoft; whether a registration is needed is open as [[11-unknowns-and-risks#UNK-013 Registration or sign-in\|registration or sign-in]]." in [[heron-building-blocks]] |
| F1.5 | DAT | normal | R-DAT-05 | Can Heron read transcripts only for meetings the pilot user organized, or for all they attended? Who gives the tenant admin approval, and for what scope? | "the call tool leaves notes or a transcript, and Heron reads them. Nothing goes back." in [[heron-building-blocks]] |
| F1.6 | DAT | normal | R-DAT-08 | What kinds of file may be in the chosen folder, and what data in them may Heron lawfully use for a prep note? | "Heron reads the files in the one folder the person points it at, on the same laptop." in [[heron-building-blocks]] |
| F1.7 | DAT | normal | R-DAT-09 | Where is a built note stored, for how long, and is a withdrawn or past note deleted? Does the data protection impact assessment need to cover this? | "for a canceled call it shows no note and withdraws one already built" in [[heron-building-blocks]] |
| F1.8 | DAT | high | new | Does the calendar read over CON-001 count as text leaving the device? Until the CISO answers, should the Heron page keep saying no text leaves the device? | "no text leaves the device in the first release" in [[heron-building-blocks]] |
| F1.9 | DAT | high | new | What lawful basis and what Frankfurt-staff filtering apply to reading past calendar entries and their attendees to find the last call? Does the CON-001 wording and the works council data list need to say so? | "past calendar entries come with their attendees, as well as coming ones" in [[heron-building-blocks]] |
| F1.10 | PTN | normal | Q-PTN-03@PTY-02 | Does the firm have a Zoom agreement? If so, who holds it, when does it end, and what would leaving or changing it cost? Or is Zoom only the clients' tool, with no agreement of ours? | "Whether Zoom is in use at the firm is not recorded." in [[03-context-and-scope]] |
| F1.11 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to a Zoom agreement need, and who must give it? If there is no firm agreement, say so, so the question can be closed. | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.12 | PTN | high | new | Which parties' terms (Microsoft for Teams, Zoom or the clients for client-hosted calls) would have to allow the call tool records CON-003 relies on? What must be agreed before FR3 and FR5 can rely on it? | "obligation of CON-003: for each call the call tool leaves a readable record, such as notes or a transcript, that can be tied to that call; where it leaves none, Heron says so" in [[heron-building-blocks]] |
| F1.13 | REG | normal | Q-REG-02@INI-001 | Is anything Heron does regulated or licensed, such as employee monitoring, processing client call content, or the tenant app registration? Who confirms each, and by when? | "Not agreed with Microsoft; whether a registration is needed is open as [[11-unknowns-and-risks#UNK-013 Registration or sign-in\|registration or sign-in]]." in [[heron-building-blocks]] |
| F1.14 | REG | normal | Q-REG-05@INI-001 | If Microsoft's calendar or a call tool's record is wrong, late or missing and the prep note misleads the person, who carries the liability, and does any Microsoft or call-tool term limit it? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.15 | REG | high | R-REG-05 | Has the DPO been asked whether the name and mood rule, given for a digest, applies to the prep note, and has an impact assessment been started for the prep note? Who asks, and by when? | "A digest may name only people who were in the meeting, and may carry no remark about anyone's mood, tone or performance" in [[02-constraints]] |
| F1.16 | REG | high | new | Does reading past calendar entries need a separate or larger Graph registration and review than reading coming ones? Does the 4 December outcome leave time before 2 February 2027? | "Not agreed with Microsoft; whether a registration is needed is open as" in [[heron-building-blocks]] |
| F1.17 | OPS | normal | Q-OPS-05@INI-001 | What do the pilot team do today to prepare for a client call, such as notes, shared folders or an assistant? Does Heron retire or replace any of it, and who still depends on it? | "Today they piece it together themselves." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.18 | OPS | normal | Q-OPS-04@INI-001 | Which tools, schemes or teams already do the same job (call recording or transcripts, per-client note-keeping, a team calendar convention)? Name them and say which ones Heron must work alongside. | "Whether Zoom is in use at the firm is not recorded." in [[03-context-and-scope]] |
| F1.19 | OPS | normal | R-OPS-02 | Who sets the 10 November deadline, and does a CISO or CISO's-office document confirm it? Who runs and supports Heron during the pilot, and has IT's endpoint lead agreed to package it? | "The solution lead says there are 30 days" in [[02-constraints]] |
| F1.20 | OPS | normal | R-OPS-03 | What happens at Frankfurt and the other sites between the London pilot and the CIO's firm-wide summer target, and who tells the CIO that the plan differs? | "and that it is in use firm-wide by the summer" in [[03-context-and-scope]] |
| F1.21 | OPS | normal | R-OPS-05 | What must be running and signed in on the laptop for the note to arrive on time? What does the person see if the laptop is asleep, offline or locked? Who supports the pilot team, and in what hours? | "Shows the note ten minutes before the call, or says why there is none" in [[heron-building-blocks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| CAP-001.FR1@APP-heron | - | assumption | [[2026-10-11-allocate-prep-note#^c01]] |
| CAP-001.FR1@CON-001 | - | assumption | [[2026-10-11-allocate-prep-note#^c02]] |
| CAP-001.FR2@APP-heron | - | assumption | [[2026-10-11-allocate-prep-note#^c05]] |
| CAP-001.FR2@CON-001 | - | assumption | [[2026-10-11-allocate-prep-note#^c06]] |
| UNK-026 | - | open | [[2026-10-11-allocate-prep-note#^c07]] |
| CAP-001.FR3@APP-heron | - | assumption | [[2026-10-11-allocate-prep-note#^c08]] |
| CAP-001.FR3@CON-003 | - | assumption | [[2026-10-11-allocate-prep-note#^c09]] |
| CAP-001.FR3@CON-002 | - | assumption | [[2026-10-11-allocate-prep-note#^c10]] |
| CAP-001.FR3@CON-001 | - | assumption | [[2026-10-11-allocate-prep-note#^c11]] |
| CAP-001.FR4@APP-heron | - | assumption | [[2026-10-11-allocate-prep-note#^c13]] |
| CAP-001.FR4@CON-002 | - | assumption | [[2026-10-11-allocate-prep-note#^c14]] |
| CAP-001.FR5@APP-heron | - | assumption | [[2026-10-11-allocate-prep-note#^c15]] |
| UNK-017 | open | open | [[2026-10-11-allocate-prep-note#^c26]] |
| R-DAT-10 | - | unknown | [[2026-10-11-allocate-prep-note#^c16]] |
| R-DAT-11 | - | unknown | [[2026-10-11-allocate-prep-note#^c16]] |
| R-FIN-09 | - | unknown | [[2026-10-11-allocate-prep-note#^c17]] |
| R-REG-08 | - | unknown | [[2026-10-11-allocate-prep-note#^c17]] |
| R-PTN-05 | - | unknown | [[2026-10-11-allocate-prep-note#^c18]] |
| Q-PTN-03@PTY-02 | - | unknown | [[2026-10-11-allocate-prep-note#^c19]] |
| Q-PTN-06@PTY-02 | - | unknown | [[2026-10-11-allocate-prep-note#^c19]] |
| R-FIN-02 | open | unknown | [[2026-10-11-allocate-prep-note#^c20]] |
| R-FIN-07 | open | unknown | [[2026-10-11-allocate-prep-note#^c21]] |
| R-DAT-08 | open | unknown | [[2026-10-11-allocate-prep-note#^c22]] |
| R-OPS-02 | open | unknown | [[2026-10-11-allocate-prep-note#^c23]] |
| R-REG-05 | open | unknown | [[2026-10-11-allocate-prep-note#^c24]] |
