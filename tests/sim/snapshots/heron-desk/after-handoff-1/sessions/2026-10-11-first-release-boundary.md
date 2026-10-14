---
id: 2026-10-11-first-release-boundary
type: session
title: "Boundary: first release boundary"
date: 2026-10-11
modes: [boundary]
status: closed
summary: Cut the first release as one laptop app, Heron, with the calendar read held open on UNK-020 as the gate.
---

# 2026-10-11 Boundary: first release boundary

## Captures

- [thought] (@sim-lead) "Yes, go ahead on the assumption—the app boundaries won't change if text stays on the laptop or moves to the cloud, and we need to unblock the team. If the strategy flips, we recut." → drop: recorded as the Override bullet under History ^c01
- [thought] (@sim-lead) "What I'm actually waiting on is the CISO template for UNK-012. Nothing I cut today changes that it needs to come back, and the pack goes in on the 10th." waits on UNK-007 (the CISO's pack template) and UNK-012 → drop: names no copy IDs, and UNK-007 and UNK-012 are already open ^c02

- [thought] (claude) Cut 1, one laptop app: Heron (new) does everything on the laptop, reading the calendar and the chosen folder and showing the note. Microsoft stays an outside party. Rests on [[04-solution-strategy#The core move|the prep note]] and CST-3. → park ^c03
- [thought] (claude) Cut 2, collector and note builder: Heron Collector (new) reads the calendar and folder, and Prep Notes (new) builds and shows the note, linked by one contract; both on the laptop. Rests on [[04-solution-strategy#The core move|the prep note]] and CST-3. → park ^c04
- [thought] (claude) Cut 3, laptop agent and cloud summarizer: Heron Agent (new) collects, Heron Summary Service (new, cloud) writes the text with a hosted model. Rests on [[sources#SRC-04|the one-pager]] and conflicts with CST-3 and UNK-012. → park ^c05

- [thought] (@sim-lead) "Cut 1." picks cut 1, one laptop app → keep: [[05-building-blocks#One laptop app|cut]] (assumption) ^c06
- [thought] (@sim-lead) "No text off the device in release one, that's the line we hold for the pack." rejects cut 3 (cloud summarizer) → park ^c07
- [thought] (@sim-lead) "Capture is everything that reads sources on the laptop—that's Heron. Insight is the note builder, it works out and shows what matters. Trust is consent, identity and admin." names three areas, Capture, Insight and Trust; which app sits in which is still to be confirmed → park ^c08

- [thought] (@sim-lead) "Heron takes Capture, the note work is inside it and that's Insight—one ship unit. Trust stays a concern, it sits across all three areas." confirms domain Capture for Heron, with Insight inside it and Trust a concern across apps → park ^c09
- [thought] (@sim-lead) "Cut 2 lost because I don't own anyone yet, and two apps means two ownership questions when I can't answer one." rejects cut 2 → park ^c10
- [thought] (claude) Heron stub written at inkling, with an unexamined row on each concern page → keep: [[heron-building-blocks|APP-heron]] (assumption) ^c11

- [thought] (@sim-lead) "Yes on 1 through 4. On 5, calendar and folder yes, call tools yes (that's on Sam), skip the API specs. Yes on 6 and 7. On 8, yes—Microsoft sends the calendar. Yes on 9. On 10, skip—@agent-lead hasn't got ownership yet." confirms Heron's sheet lines 1 to 9 and skips the API specs and the links → keep: [[heron-building-blocks|APP-heron]] (assumption) ^c12
- [thought] (claude, from @sim-lead) Heron's page, containers and concern cells written → keep: [[heron-building-blocks|APP-heron]] (assumption) ^c13
- [thought] (claude, from @sim-lead) Heron's runtime page and its failure line → keep: [[heron-runtime#On failure|RUN-heron]] (assumption) ^c14
- [thought] (claude, from @sim-lead) Calendar entries, read from Microsoft → keep: [[heron-building-blocks#CON-001 Calendar entries|CON-001]] (assumption) ^c15
- [thought] (claude, from @sim-lead) The chosen folder → keep: [[heron-building-blocks#CON-002 Chosen folder|CON-002]] (assumption) ^c16
- [thought] (claude, from @sim-lead) Call tool records, "that's on Sam" → keep: [[heron-building-blocks#CON-003 Call tool records|CON-003]] (assumption) ^c17
- [thought] (claude, from @sim-lead) Prepare a client for a call → keep: [[CAP-001-prepare-a-client-for-a-call|CAP-001]] (assumption) ^c18
- [thought] (claude, from @sim-lead) A person gets a prep note before a client call, Microsoft sends the calendar → keep: [[FLO-001-prep-note-before-a-client-call|FLO-001]] (assumption) ^c19
- [thought] (@sim-lead) "that's on Sam" asks @pilot-lead about the call tools → keep: [[11-unknowns-and-risks#UNK-008 Call tools in use|UNK-008]] (open) ^c20

- [thought] (@sim-lead) "CISO—honestly not sure if the message even went out with back-to-back sessions. I'll ring this afternoon and get a date by the 15th, or I'll know it's not coming." waits on UNK-007 (the CISO's pack template); no answer yet → keep: [[11-unknowns-and-risks#UNK-007 CISO security pack requirements|UNK-007]] (open) ^c21
- [thought] (@sim-lead) "The calendar question is the gate though. If a calendar read counts as text off the device, I've lost my line and it breaks the pack." F1.29: Does reading calendars from Microsoft count as text leaving the device under the CISO's rule? waits on the CISO's office → keep: [[11-unknowns-and-risks#Question ledger|R-REG-04]] (unknown) ^c22

- [thought] (@sim-lead) "Write the calendar unknown with the 15th. Everything else stays open until the CISO tells me if the read counts as text off the device. That's the gate." waits on UNK-020: Q-DAT-02@APP-heron, Q-PTN-02@PTY-01, Q-PTN-05@PTY-01, Q-PTN-05@PTY-02, R-DAT-03, R-PTN-01, R-PTN-03, R-REG-01, R-REG-02, Q-DAT-03@CON-001, Q-DAT-03@CON-002, Q-DAT-03@CON-003, Q-OPS-01@APP-heron, Q-OPS-02@CON-001, Q-OPS-02@CON-002, Q-OPS-02@CON-003, Q-OPS-03@CAP-001, Q-PTN-04@CON-001, Q-PTN-04@CON-002, Q-PTN-04@CON-003 → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-03]] (unknown); [[11-unknowns-and-risks#Question ledger|R-PTN-01]] (unknown); [[11-unknowns-and-risks#Question ledger|R-PTN-03]] (unknown); [[11-unknowns-and-risks#Question ledger|R-REG-01]] (unknown); [[11-unknowns-and-risks#Question ledger|R-REG-02]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-DAT-02@APP-heron]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-02@PTY-01]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-05@PTY-01]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-05@PTY-02]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-DAT-03@CON-001]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-DAT-03@CON-002]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-DAT-03@CON-003]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-OPS-01@APP-heron]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-OPS-02@CON-001]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-OPS-02@CON-002]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-OPS-02@CON-003]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-OPS-03@CAP-001]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-04@CON-001]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-04@CON-002]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-04@CON-003]] (unknown) ^c23
- [unknown] (claude, from @sim-lead) Does reading a person's calendar from Microsoft count as text leaving the device? Ask: the CISO's office, by 2026-10-15. → keep: [[11-unknowns-and-risks#UNK-020 Calendar read and the device line|UNK-020]] (open) ^c24
- [thought] (@sim-lead) "Yes to moving UNK-007 to the 15th—that's when I need the answer anyway." moves UNK-007's ask-by from 2026-10-16 to 2026-10-15 → keep: [[11-unknowns-and-risks#UNK-007 CISO security pack requirements|UNK-007]] (open) ^c25
- [thought] (@sim-lead) "No lifted lines, everything I said stays off the page." → drop: a ruling on this close, not content for a page ^c26
- [thought] (@sim-lead) "One and three as unknown on the existing—UNK-010 and UNK-004 respectively. Two as open; I need the DPO on the prep note." F1.3: who is the accountable owner and budget holder for Heron; F1.38: who tells the product owner and the CIO the digest and dashboard are out; F1.28: does the DPO's content rule apply to the prep note → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-05]] (unknown); [[11-unknowns-and-risks#Question ledger|R-OPS-04]] (unknown); [[11-unknowns-and-risks#Question ledger|R-REG-05]] (open) ^c27

## Reviews

### 1. After the pages are written, 2026-10-11

- **Coverage:** FIN found 5; DAT found 8; PTN found 10, 1 dropped; REG found 6; OPS found 9, 2 dropped
- **Dropped:** [PTN] its quote "- **Relationship:** supplier" has fewer than 4 words, too few to show where it came from: Do the Microsoft terms allow assignment, or a change of who controls the agreement or Heron? Who is to check them?; [OPS] the quote does not mention what the finding is about: Does Heron retire anything, such as the current manual prep or any note-taking habit? If so, who relies on it?; [OPS] the quote does not mention what the finding is about: Who is actually accountable for running Heron if @sim-lead owns no team? Who takes it before the pilot starts?
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | R-FIN-02 | If text stays on the laptop, who carries the compute and storage cost and risk on the pilot laptops? If UNK-012 flips to a cloud summarizer, who would fund and carry the hosting and model cost? | "It runs on the person's own laptop and holds nothing off the device." in [[heron-runtime]] |
| F1.2 | FIN | normal | new | Who pays to build Heron and who carries its running cost once the pilot is live? Is that funded, and from which budget? | "\| [[heron-building-blocks\|Heron]] \| unexamined \| \|" in [[concern-cost]] |
| F1.3 | FIN | high | new | Who is the accountable owner and budget holder for Heron: a team, not only the planning lead? Does that owner accept the running cost and support liability? | "\| [[heron-building-blocks\|Heron]] \| unknown \| [[11-unknowns-and-risks#UNK-010 Who owns Heron\|UNK-010]] \|" in [[concern-ownership]] |
| F1.4 | FIN | normal | new | Who pays for IT's packaging, deployment and ongoing support of Heron on Mac and Windows? Has IT committed to the 18 January slot and to ongoing support? | "\| [[heron-building-blocks\|Heron]] \| unknown \| [[11-unknowns-and-risks#UNK-011 IT packaging\|UNK-011]] \|" in [[concern-rollout]] |
| F1.5 | FIN | normal | new | Once the pilot's call tools are known, does reading what each one leaves behind need a license, an agreement or a paid tier? Who holds it and who pays? | "Not agreed. Which tools are in use is open as [[11-unknowns-and-risks#UNK-008 Call tools in use\|UNK-008]]" in [[heron-building-blocks]] |
| F1.6 | DAT | high | Q-DAT-02@APP-heron | What customer, client and colleague data does Heron hold or receive, and on what lawful basis may it use each kind? Who decides, and does the DPO agree? | "Heron reads the person's calendar entries from Microsoft, with the person's own sign-in." in [[heron-building-blocks]] |
| F1.7 | DAT | normal | Q-DAT-03@CON-001 | Does attendee data in calendar entries cross this boundary, and were Heron-type consumers named when it was collected? Does anything in the staff or client notices cover it? | "Microsoft sends the entries with their times, titles and attendees." in [[heron-building-blocks]] |
| F1.8 | DAT | normal | Q-DAT-03@CON-002 | What kind of files will be in the chosen folder, who collected them and for what purpose, and may Heron use them for the prep note? Is the person limited to firm-held files? | "the person names a folder, and Heron reads the files in it." in [[heron-building-blocks]] |
| F1.9 | DAT | high | Q-DAT-03@CON-003 | Were clients and attendees told, when the call was recorded or transcribed, that a tool like Heron could read it? What do the engagement letters allow? | "the call tool leaves notes or a transcript, and Heron reads them." in [[heron-building-blocks]] |
| F1.10 | DAT | high | R-DAT-03 | Who writes the impact assessment, by what date, and must it be finished before the 10 November pack and the December works council meeting? | "The rest of the DPO's view waits for the impact assessment" in [[02-constraints]] |
| F1.11 | DAT | normal | R-DAT-05 | Can Heron read transcripts only for meetings the pilot user organized, or all they attended? Who grants the tenant admin approval, and on what scope? | "reading transcripts needs tenant admin approval" in [[03-context-and-scope]] |
| F1.12 | DAT | normal | new | Which data does each step of the prep note flow read, and should the flow show the folder and call tool records so the data list is complete? | "2. [[03-context-and-scope#PTY-01 Microsoft\|Microsoft]] → [[heron-building-blocks\|Heron]]: sends the person's calendar entries" in [[FLO-001-prep-note-before-a-client-call]] |
| F1.13 | DAT | normal | new | Does Heron keep the notes or the text it reads on the laptop, for how long, and who (IT, the firm, the user) can reach that store? | "It runs on the person's own laptop and holds nothing off the device." in [[heron-runtime]] |
| F1.14 | PTN | high | Q-PTN-02@PTY-01 | Do the Microsoft 365 agreement and the Graph terms allow Heron to pass calendar data on to another owner or user, for example if ownership of Heron changes? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.15 | PTN | normal | Q-PTN-03@PTY-02 | Does the firm hold any Zoom agreement, who holds it, when does it end, and what would changing it cost? Or is Zoom to be dropped as a party until UNK-008 is answered? | "Whether Zoom is in use at the firm is not recorded." in [[03-context-and-scope]] |
| F1.16 | PTN | normal | Q-PTN-04@CON-001 | Which Microsoft agreement or Graph terms cover Heron reading calendar entries with the person's own sign-in, and does the first release stay inside them? | "Not agreed with Microsoft; whether a registration is needed is open as" in [[heron-building-blocks]] |
| F1.17 | PTN | normal | Q-PTN-04@CON-002 | Which firm policy or agreement covers Heron reading a user-chosen folder, which may hold client documents, and does the change stay inside it? | "- **Provider:** the pilot user, on their own laptop" in [[heron-building-blocks]] |
| F1.18 | PTN | high | Q-PTN-04@CON-003 | Which call-tool terms, and which client engagement letters, allow Heron to read call notes or transcripts, and does the first release stay inside them? | "- **Provider:** the call tools the pilot team and its clients use, not yet known" in [[heron-building-blocks]] |
| F1.19 | PTN | high | Q-PTN-05@PTY-02 | Do any Zoom terms allow assignment or a change of control? Or should Zoom be removed as a party until the call tools are known? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.20 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to a Zoom agreement need, and who must give it? | "[[sources#SRC-04\|The product one-pager]] expects Heron to read Zoom meetings." in [[03-context-and-scope]] |
| F1.21 | PTN | high | R-PTN-01 | Which platform terms govern Heron reading call-tool records, and do client engagement letters allow notes or transcripts from client calls to be processed on the laptop? | "Heron reads what each call tool leaves behind about a call, such as notes or a transcript." in [[heron-building-blocks]] |
| F1.22 | PTN | high | R-PTN-03 | Is the cloud and language-model vendor dropped from the party list given the CISO's ban and the rejected cut 3, or recorded now with the agreement that would govern it for a later release? | "with a cloud service writing the summaries using a hosted language model" in [[03-context-and-scope]] |
| F1.23 | PTN | normal | new | Should FLO-001 show where call tool records enter, so the party and agreement behind that step are named? Or does the first release work without call tool records? | "2. [[03-context-and-scope#PTY-01 Microsoft\|Microsoft]] → [[heron-building-blocks\|Heron]]: sends the person's calendar entries over [[heron-building-blocks#CON-001 Calendar entries\|Calendar entries]]." in [[FLO-001-prep-note-before-a-client-call]] |
| F1.24 | REG | normal | Q-REG-02@INI-001 | Is any data Heron reads (client call transcripts, calendar attendees, folder files) or any activity it performs regulated or licensed, and who checks that? | "Heron reads what each call tool leaves behind about a call, such as notes or a transcript." in [[heron-building-blocks]] |
| F1.25 | REG | normal | Q-REG-05@INI-001 | If the calendar feed, a call tool's record or Heron's note is wrong or missing, who is liable to the person and to the client, and under what agreement? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.26 | REG | high | R-REG-01 | Do client engagement letters and call-tool terms allow Heron to read call transcripts and notes for a prep note, and who is liable to the client if they do not? | "Heron reads what each call tool leaves behind about a call, such as notes or a transcript." in [[heron-building-blocks]] |
| F1.27 | REG | high | R-REG-02 | What employee-monitoring, notice or consultation duties apply to Heron reading London staff's calendars and files, and who owns that check? | "Microsoft sends the entries with their times, titles and attendees." in [[heron-building-blocks]] |
| F1.28 | REG | high | new | Does the DPO's content rule (names only people in the meeting, no remark on mood, tone or performance) apply to the prep note, and has the DPO been asked about the prep note and the impact assessment for it? | "one note on who is on the call, what was said last time and what is still open" in [[FLO-001-prep-note-before-a-client-call]] |
| F1.29 | REG | high | new | Does reading calendars from Microsoft count as text leaving the device under the CISO's rule, and does Heron need a Graph registration (six-week review) before the 2 February 2027 pilot? | "It runs on the person's own laptop and holds nothing off the device." in [[heron-runtime]] |
| F1.30 | OPS | normal | Q-OPS-01@APP-heron | Who supports Heron for the roughly 60 pilot users, who handles a failed note or a stuck install, and who is the contact outside office hours? | "It runs on the person's own laptop and holds nothing off the device." in [[heron-runtime]] |
| F1.31 | OPS | normal | Q-OPS-02@CON-001 | What does the user see, and who is told, when Microsoft is slow or unavailable for the calendar read? Is there a retry or a time limit? | "When the calendar cannot be read, the folder is missing or the note is late, Heron shows no note and says why." in [[heron-runtime]] |
| F1.32 | OPS | normal | Q-OPS-02@CON-002 | What does Heron show when the chosen folder is empty, stale or unreachable, and who tells the user to re-point it? | "Not agreed. Whether the pilot team keeps pointing Heron at a folder every day is open as" in [[heron-building-blocks]] |
| F1.33 | OPS | normal | Q-OPS-02@CON-003 | When the call tool leaves nothing to read, does Heron show a partial note, no note, or a reason? Should FLO-001 include the call tool records step? | "the call tool leaves notes or a transcript, and Heron reads them. Nothing goes back." in [[heron-building-blocks]] |
| F1.34 | OPS | high | Q-OPS-03@CAP-001 | Which team owns Prepare a client for a call, and Heron, after the change? Who accepts that ownership and who answers for it in the pilot? | "Which team owns each app and each piece of new work." in [[concern-ownership]] |
| F1.35 | OPS | normal | Q-OPS-04@INI-001 | How do the pilot team prepare for calls today? Name any tool, scheme, shared notes or person doing the same job. | "Today they piece it together themselves." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.36 | OPS | high | R-OPS-02 | Who runs and supports Heron during the pilot, who in IT packages it, and who sets the 10 November pack deadline? Has @endpoint-lead agreed to the 18 January slot? | "The solution lead says IT's packaging slot of 18 January is booked but has not heard @endpoint-lead say yes, and will ask directly." in [[11-unknowns-and-risks]] |
| F1.37 | OPS | high | R-OPS-03 | What is the rollout path for Frankfurt and other council sites between the London pilot and the CIO's summer target, and who tells the CIO it will not be firm-wide? | "and that it is in use firm-wide by the summer." in [[03-context-and-scope]] |
| F1.38 | OPS | high | new | Who tells the product owner and the CIO that the digest and the adoption dashboard are out of the first release, and have they agreed? | "Nobody keeps the digest or the dashboard in the first release." in [[heron-building-blocks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| APP-heron | - | inkling | [[2026-10-11-first-release-boundary#^c11]] |
| APP-heron | inkling | assumption | [[2026-10-11-first-release-boundary#^c13]] |
| RUN-heron | - | assumption | [[2026-10-11-first-release-boundary#^c14]] |
| CON-001 | - | assumption | [[2026-10-11-first-release-boundary#^c15]] |
| CON-002 | - | assumption | [[2026-10-11-first-release-boundary#^c16]] |
| CON-003 | - | assumption | [[2026-10-11-first-release-boundary#^c17]] |
| CAP-001 | - | assumption | [[2026-10-11-first-release-boundary#^c18]] |
| FLO-001 | - | assumption | [[2026-10-11-first-release-boundary#^c19]] |
| UNK-020 | - | open | [[2026-10-11-first-release-boundary#^c24]] |
| R-REG-04 | - | unknown | [[2026-10-11-first-release-boundary#^c22]] |
| R-DAT-03 | open | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| R-PTN-01 | open | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| R-PTN-03 | open | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| R-REG-01 | open | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| R-REG-02 | open | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-DAT-02@APP-heron | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-PTN-02@PTY-01 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-PTN-05@PTY-01 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-PTN-05@PTY-02 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-DAT-03@CON-001 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-DAT-03@CON-002 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-DAT-03@CON-003 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-OPS-01@APP-heron | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-OPS-02@CON-001 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-OPS-02@CON-002 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-OPS-02@CON-003 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-OPS-03@CAP-001 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-PTN-04@CON-001 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-PTN-04@CON-002 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| Q-PTN-04@CON-003 | - | unknown | [[2026-10-11-first-release-boundary#^c23]] |
| R-FIN-05 | - | unknown | [[2026-10-11-first-release-boundary#^c27]] |
| R-OPS-04 | - | unknown | [[2026-10-11-first-release-boundary#^c27]] |
| R-REG-05 | - | open | [[2026-10-11-first-release-boundary#^c27]] |

## History

- **Override:** "Boundary: the direction is not `decided`" by @sim-lead on 2026-10-11: "the app boundaries won't change if text stays on the laptop or moves to the cloud, and we need to unblock the team. If the strategy flips, we recut." [[2026-10-11-first-release-boundary#^c01]]
