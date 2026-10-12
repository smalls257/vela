---
id: 2026-10-11-first-release-surface
type: session
title: "Shape: first release surface"
date: 2026-10-11
modes: [shape]
status: closed
summary: Picked the pre-call prep note as the first release, as an assumption waiting on Sam, with three new unknowns and eight ledger rows.
---

# 2026-10-11 Shape: first release surface

## Captures

- [thought] (claude) Option A, the morning note: the pilot gets one 7:30 digest from the person's calendar, mail and documents, written entirely on their own Mac or Windows laptop and pushed there by IT. It costs a text-summarising model that runs on the laptop and IT's packaging work, and it needs the full list of data read ready for the works council. It rules out the prep note, any cloud summary, and anything beyond the digest in the first release. → park ^c01
- [thought] (claude) Option B, the pre-call prep note: the pilot gets one note about ten minutes before each client call (who is on it, what was said last time, what is open), built on the laptop from the calendar and one folder the person points Heron at. It costs the least data (no mailbox, no general document search) and so the shortest list for the CISO and the works council, but it depends on knowing which call tools the team uses and what each leaves behind. It rules out the morning digest and any "what matters today" view in the first release. → keep: [[04-solution-strategy#The core move|solution strategy]] (assumption) ^c02
- [thought] (claude) Option C, hand-in: Heron reads nothing by itself; the person drops or forwards what matters into one local Heron folder, and Heron writes the morning note from that, on the laptop. It costs the person a daily habit and loses the "quietly watches" promise, but it needs no sign-in to Microsoft 365, no app registration and no consent question, and the data list is only what people choose to hand over. It rules out any automatic reading of meetings, mail or documents in the first release. → park ^c03
- [thought] (solution lead) "A's blocked by the data list." Reaction to option A. → park ^c04
- [thought] (solution lead) "C loses the whole point." Reaction to option C. → park ^c05
- [thought] (solution lead) "B is tightest, but it rests on the 70 percent—I need Sam to confirm the call tools and actual time breakdown before the next step." Reaction to option B. → park ^c06
- [thought] (claude, from solution lead) Pick option B, the pre-call prep note: "Yes on B." → keep: [[04-solution-strategy#The core move|solution strategy]] (assumption) ^c07
- [thought] (claude, from solution lead) Option A rejected: "A's blocked by the data list." → park ^c08
- [thought] (claude, from solution lead) Option C rejected: "C loses the whole point." → park ^c09
- [thought] (solution lead) F1.31: the 70 percent share of the pilot team's work that comes from client calls is a belief, and option B rests on it ("it rests on the 70 percent"): load-bearing. It is checked with Sam on the actual time breakdown, UNK-009. → keep: [[11-unknowns-and-risks#Question ledger|Q-OPS-07@INI-001]] (unknown) ^c10
- [thought] (solution lead) waits on UNK-008: F1.2, F1.6, F1.19, F1.28. "I need Sam to confirm the call tools" before the next step. → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-02@INI-001]] (unknown); [[11-unknowns-and-risks#Question ledger|R-FIN-04]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-PTN-02@PTY-02]] (unknown); [[11-unknowns-and-risks#Question ledger|Q-REG-01@INI-001]] (unknown) ^c11
- [thought] (solution lead) F1.8, F1.9: "Teams covers F1.8/9 (W3, the recording banner)". For Teams calls, notice rests on the recording banner. W3 is not a row in `sources.md`, so this is the lead's word and not yet a fact; Discover would need to read it. → keep: [[11-unknowns-and-risks#UNK-017 Client Zoom transcripts and engagement letters|UNK-017]] (open) ^c12
- [unknown] (solution lead) F1.8, F1.9, F1.19: "client Zoom is blind—I don't know what transcripts are kept or what the engagement letters say. That's on Legal and Sam." Open question: what transcripts of client-hosted Zoom calls are kept, and what the engagement letters allow. Ask: Legal and Sam (@pilot-lead). → keep: [[11-unknowns-and-risks#UNK-017 Client Zoom transcripts and engagement letters|UNK-017]] (open) ^c13
- [unknown] (solution lead) F1.11: "open, CISO and DPO on the filtering". Open question: how Frankfurt staff's data is filtered out of London people's calendars and calls. Ask: the CISO and the DPO. → keep: [[11-unknowns-and-risks#UNK-018 Filtering Frankfurt staff's data|UNK-018]] (open) ^c14
- [thought] (solution lead) F1.18: "18 January slot is booked but I haven't heard @endpoint-lead say yes. Need to ask him directly." A belief with no source: IT's packaging slot of 18 January is booked, but @endpoint-lead has not said yes. Stays under UNK-011; the lead asks him. → keep: [[11-unknowns-and-risks#UNK-011 IT packaging|UNK-011]] (open) ^c15
- [thought] (solution lead) waits on the pack: F1.25. "Works council and CISO both due around 4 December—can't know they'll accept until they've read the short list. Waiting on the pack." → keep: [[11-unknowns-and-risks#Question ledger|R-REG-03]] (unknown) ^c16
- [thought] (solution lead) F1.32: "Sam's team lives on calls but will they hand in a folder every day? That's adoption risk and could kill B." A belief the plan rests on: pilot users will keep pointing Heron at a folder every day. Load-bearing; no source. → keep: [[11-unknowns-and-risks#UNK-019 Daily folder habit|UNK-019]] (open) ^c17
- [thought] (solution lead) F1.38: "Product owner wanted digest plus prep—B is prep only. CIO wanted adoption dashboard—B gives nothing on that. Both miss and I should tell them now rather than surprise them." The product owner's wish is in the one-pager (SRC-04); the CIO's wish for an adoption dashboard is the lead's word and is in no source. The lead will tell both; owner of that: the solution lead. → keep: [[11-unknowns-and-risks#UNK-004 Stakeholders|UNK-004]] (open) ^c18
- [thought] (solution lead) "Sam's @pilot-lead, yes." Sam Hadley is `@pilot-lead`. → park ^c19
- [unknown] (solution lead) F1.8, F1.9, F1.19: "Legal needs the Zoom and engagement-letter question by 1 November—that's the blocker if client calls are even allowed." Ask by 2026-11-01. Ask: Legal and @pilot-lead. Blocks option B. → keep: [[11-unknowns-and-risks#UNK-017 Client Zoom transcripts and engagement letters|UNK-017]] (open) ^c20
- [unknown] (solution lead) F1.11: "Frankfurt filtering to CISO and DPO by the same date, so it goes in the pack." Ask by 2026-11-01. Ask: the CISO and the DPO. The pack is due 10 November (CST-1). → keep: [[11-unknowns-and-risks#UNK-018 Filtering Frankfurt staff's data|UNK-018]] (open) ^c21

## Reviews

### 1. Before options, 2026-10-11

- **Coverage:** FIN found 6, 2 dropped; DAT found 9, 2 dropped; PTN found 6, 2 dropped; REG found 7, 4 dropped; OPS found 10, 3 dropped
- **Dropped:** [FIN] it names R-FIN-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own; [FIN] it names R-FIN-03, which this vault does not owe and has no open reviewer question for; write new for a question of your own; [DAT] the quote does not mention what the finding is about; [DAT] it names R-DAT-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own; [PTN] the quote does not mention what the finding is about; [PTN] it names R-PTN-02, which this vault does not owe and has no open reviewer question for; write new for a question of your own; [REG] the quote does not mention what the finding is about; [REG] the quote does not mention what the finding is about; [REG] the quote does not mention what the finding is about; [REG] the quote does not mention what the finding is about; [OPS] the quote does not mention what the finding is about; [OPS] it names R-OPS-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own; [OPS] the quote does not mention what the finding is about
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-02@INI-001 | For option A, who pays for the on-laptop model and the packaging, and who carries the running cost after the pilot? | "It costs a text-summarising model that runs on the laptop and IT's packaging work" in [[2026-10-11-first-release-surface]] |
| F1.2 | FIN | normal | Q-FIN-02@INI-001 | For option B, who pays to build and run the per-call-tool integrations, and who carries that cost after the pilot? | "it depends on knowing which call tools the team uses and what each leaves behind" in [[2026-10-11-first-release-surface]] |
| F1.3 | FIN | normal | Q-FIN-02@INI-001 | For option C, who accepts the time cost to pilot staff, and who funds building and running the hand-in folder and note writer? | "It costs the person a daily habit and loses the ”quietly watches” promise" in [[2026-10-11-first-release-surface]] |
| F1.4 | FIN | normal | R-FIN-02 | For option A, where is the model processed and kept, who pays for it and who carries the hosting and compute risk? Does the laptop fleet have the capacity? | "written entirely on their own Mac or Windows laptop and pushed there by IT" in [[2026-10-11-first-release-surface]] |
| F1.5 | FIN | normal | R-FIN-02 | For options B and C, where do the notes and the hand-in folder live, and who pays for and carries the risk of that storage and compute? | "built on the laptop from the calendar and one folder the person points Heron at" in [[2026-10-11-first-release-surface]] |
| F1.6 | FIN | normal | new | For option B, which call tools does the pilot team use, and does reading what each leaves behind carry any licence, agreement or cost, and who holds it? | "it depends on knowing which call tools the team uses and what each leaves behind" in [[2026-10-11-first-release-surface]] |
| F1.7 | DAT | high | Q-DAT-05@INI-001 | For Option A, what was the mail, calendar and document data collected for, and is writing a personal digest from it a compatible purpose? Who confirms that, the DPO? | "the pilot gets one 7:30 digest from the person's calendar, mail and documents, written entirely on their own Mac or Windows laptop" in [[2026-10-11-first-release-surface]] |
| F1.8 | DAT | high | Q-DAT-05@INI-001 | For Option B, is a prep note built from earlier call content a purpose the data was collected for? What were clients and attendees told? | "built on the laptop from the calendar and one folder the person points Heron at" in [[2026-10-11-first-release-surface]] |
| F1.9 | DAT | high | R-DAT-02 | For Option B, what consent or notice do clients and other attendees need before Heron uses what was said on a call? Does the transcript source depend on who organised the meeting? | "what was said last time, what is open" in [[2026-10-11-first-release-surface]] |
| F1.10 | DAT | high | R-DAT-03 | For Option A, who writes the data list and the data protection impact assessment, and by when? Does it come before the 10 November pack and the December council? | "it needs the full list of data read ready for the works council" in [[2026-10-11-first-release-surface]] |
| F1.11 | DAT | high | R-DAT-04 | For Options A and B, how is Frankfurt staff's data excluded or handled when London users read meetings and mail that include them? Does the works council need to see that in the data list? | "Frankfurt stays out of the pilot" in [[02-constraints]] |
| F1.12 | DAT | high | Q-DAT-01@INI-001 | For Option A, who supplies the on-laptop summarising model, and does any new party get access to the data, such as the model supplier or IT packaging? | "It costs a text-summarising model that runs on the laptop and IT's packaging work" in [[2026-10-11-first-release-surface]] |
| F1.13 | DAT | high | R-DAT-02 | For Option C, do clients and colleagues named in handed-over material need notice or consent, and does the DPO's rule on who a digest may name still apply? | "it needs no sign-in to Microsoft 365, no app registration and no consent question" in [[2026-10-11-first-release-surface]] |
| F1.14 | DAT | normal | R-DAT-04 | For Option C, what rules say what may be handed over, and does the works council accept a list of data types instead of fixed sources? | "the data list is only what people choose to hand over" in [[2026-10-11-first-release-surface]] |
| F1.15 | DAT | high | Q-DAT-05@INI-001 | For all options, what is the lawful basis for processing staff and client data, and does anything other than the person's own choice to install cover it? | "It expects that staff choosing to install covers consent" in [[03-context-and-scope]] |
| F1.16 | PTN | high | Q-PTN-02@PTY-01 | Do the firm's Microsoft agreement and platform terms allow Heron to read calendar, mail and documents and summarise them on the laptop, and who holds that agreement? | "the pilot gets one 7:30 digest from the person's calendar, mail and documents" in [[2026-10-11-first-release-surface]] |
| F1.17 | PTN | high | R-PTN-03 | Who supplies the on-laptop summarising model, under what licence, and should it be recorded as an outside party? Is the hosted-model vendor from the one-pager dropped for good? | "It costs a text-summarising model that runs on the laptop" in [[2026-10-11-first-release-surface]] |
| F1.18 | PTN | normal | Q-PTN-06@PTY-01 | Has IT agreed to package and push Heron, who owns and pays for it, and what notice does IT or Microsoft need for any change? | "pushed there by IT" in [[2026-10-11-first-release-surface]] |
| F1.19 | PTN | high | Q-PTN-02@PTY-02 | Which call tools does the pilot team use, and do Zoom's terms (and Teams' terms where the client hosts) allow Heron to use what those tools leave behind? | "it depends on knowing which call tools the team uses and what each leaves behind" in [[2026-10-11-first-release-surface]] |
| F1.20 | PTN | high | Q-PTN-05@PTY-01 | Does anything in the Microsoft or client agreements restrict forwarding or dropping mail, meeting content or documents into a local Heron folder, and does that action change who may use the data? | "it needs no sign-in to Microsoft 365, no app registration and no consent question" in [[2026-10-11-first-release-surface]] |
| F1.21 | PTN | normal | Q-PTN-03@PTY-02 | Who holds each partner agreement (Microsoft, Zoom), when does it end, and what would changing or leaving it cost under Options A, B and C? | "It costs a text-summarising model that runs on the laptop and IT's packaging work" in [[2026-10-11-first-release-surface]] |
| F1.22 | REG | high | R-REG-01 | May staff put client emails, call notes or documents into a Heron folder under client contracts, and who checks that? | "the person drops or forwards what matters into one local Heron folder" in [[2026-10-11-first-release-surface]] |
| F1.23 | REG | high | R-REG-02 | What employee-monitoring, consultation or notice duties apply to Option A's reading of London staff's calendar, mail and documents, and who owns that check? | "from the person's calendar, mail and documents" in [[2026-10-11-first-release-surface]] |
| F1.24 | REG | high | R-REG-03 | Is there a London consultation process, when must it finish, and do the council's December meeting, the CISO's 4 December outcome and any registration review fit a 2 February 2027 start? Does the Frankfurt exclusion cover a firm-wide rollout? | "it needs the full list of data read ready for the works council" in [[2026-10-11-first-release-surface]] |
| F1.25 | REG | normal | R-REG-03 | Would the works council and the CISO accept Option B's list in time for the pilot, and has either said so? | "so the shortest list for the CISO and the works council" in [[2026-10-11-first-release-surface]] |
| F1.26 | REG | high | R-REG-03 | Which of Options A and B need an app registration, and does that review run after the 4 December outcome and push back the 2 February 2027 start? | "no sign-in to Microsoft 365, no app registration and no consent question" in [[2026-10-11-first-release-surface]] |
| F1.27 | REG | normal | Q-REG-05@INI-001 | Who supplies the summarising model, under what licence, and who is liable to staff or clients when a summary is wrong or exposes something? | "It costs a text-summarising model that runs on the laptop" in [[2026-10-11-first-release-surface]] |
| F1.28 | REG | normal | Q-REG-01@INI-001 | Do the call tools' or Microsoft's terms restrict what Heron may read or keep, and is any option a joint offer or a regulated activity or data set? | "it depends on knowing which call tools the team uses and what each leaves behind" in [[2026-10-11-first-release-surface]] |
| F1.29 | OPS | normal | Q-OPS-07@INI-001 | Is there evidence that an on-laptop summarising model works on the pilot team's actual laptops, and does the product owner accept that Heron cannot use a cloud summary? | "It costs a text-summarising model that runs on the laptop and IT's packaging work" in [[2026-10-11-first-release-surface]] |
| F1.30 | OPS | normal | Q-OPS-05@INI-001 | Whose expectations (the product owner's and the CIO's) does ruling out the prep note and the cloud summary break, and have they been told? | "It rules out the prep note, any cloud summary, and anything beyond the digest in the first release." in [[2026-10-11-first-release-surface]] |
| F1.31 | OPS | high | Q-OPS-07@INI-001 | What is the basis of the 70 percent calls figure, and would Option B still be worth it if it were wrong? | "the pilot gets one note about ten minutes before each client call" in [[2026-10-11-first-release-surface]] |
| F1.32 | OPS | normal | Q-OPS-06@INI-001 | Have the pilot users been asked whether they will set a folder, and who holds each person's folder content when someone leaves or changes teams? | "built on the laptop from the calendar and one folder the person points Heron at" in [[2026-10-11-first-release-surface]] |
| F1.33 | OPS | high | Q-OPS-06@INI-001 | Will the CIO accept a first release that loses the quietly-watches promise, and will the pilot team do a daily hand-in? | "It costs the person a daily habit and loses the ”quietly watches” promise" in [[2026-10-11-first-release-surface]] |
| F1.34 | OPS | normal | Q-OPS-07@INI-001 | Do the works council, the DPO and the CISO accept a user-chosen data list, which in practice is open-ended, as the full list they asked for? | "the data list is only what people choose to hand over" in [[2026-10-11-first-release-surface]] |
| F1.35 | OPS | high | Q-OPS-06@INI-001 | Who writes the data list for the works council and CISO, by when, and does the December works council date still allow the 2 February 2027 pilot? | "it needs the full list of data read ready for the works council" in [[2026-10-11-first-release-surface]] |
| F1.36 | OPS | normal | R-OPS-03 | What is the plan for Frankfurt and other council sites after the London pilot under each option, and who tells the CIO that firm-wide by summer does not follow? | "Frankfurt stays out of the pilot" in [[02-constraints]] |
| F1.37 | OPS | high | R-OPS-02 | Who sets the 10 November deadline, who owns and runs Heron, and who writes and signs the pack for whichever option is chosen? | "The security pack goes to the CISO's review by 10 November 2026" in [[02-constraints]] |
| F1.38 | OPS | normal | Q-OPS-06@INI-001 | Who are the stakeholders for each option, including IT packaging staff, and who wants something different from the CIO's sentence? | "Nobody has listed the stakeholders for the desk helper" in [[11-unknowns-and-risks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| 04-solution-strategy | inkling | assumption | [[2026-10-11-first-release-surface#^c07]] |
| UNK-017 | - | open | [[2026-10-11-first-release-surface#^c13]] |
| UNK-018 | - | open | [[2026-10-11-first-release-surface#^c14]] |
| UNK-019 | - | open | [[2026-10-11-first-release-surface#^c17]] |
| Q-OPS-07@INI-001 | - | unknown | [[2026-10-11-first-release-surface#^c10]] |
| Q-FIN-02@INI-001 | - | unknown | [[2026-10-11-first-release-surface#^c11]] |
| Q-REG-01@INI-001 | - | unknown | [[2026-10-11-first-release-surface#^c11]] |
| Q-PTN-02@PTY-02 | - | unknown | [[2026-10-11-first-release-surface#^c11]] |
| R-FIN-04 | - | unknown | [[2026-10-11-first-release-surface#^c11]] |
| Q-DAT-05@INI-001 | - | unknown | [[2026-10-11-first-release-surface#^c13]] |
| R-DAT-02 | open | unknown | [[2026-10-11-first-release-surface#^c13]] |
| R-DAT-04 | open | unknown | [[2026-10-11-first-release-surface#^c14]] |
| Q-PTN-06@PTY-01 | - | unknown | [[2026-10-11-first-release-surface#^c15]] |
| R-REG-03 | open | unknown | [[2026-10-11-first-release-surface#^c16]] |
| Q-OPS-06@INI-001 | - | unknown | [[2026-10-11-first-release-surface#^c18]] |
