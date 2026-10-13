---
id: 2026-10-12-desk-helper-start
type: session
title: "Dump & Diverge: desk helper start"
date: 2026-10-12
modes: [dump]
status: closed
summary: "Dump: the CIO's desk-helper ask met conflicting positions. Recorded 8 constraints, 10 unknowns, 3 risks and the question ledger; the lock is who settles whether meeting text may leave the laptop."
---

# 2026-10-12 Dump & Diverge: desk helper start

## Captures

- [idea] (CIO, as relayed by the solution lead) "a desk helper for Mac and Windows that sets up in two minutes, quietly watches your meetings, email and documents, and tells you what matters each morning" → keep: [[01-goals#Goals|G1]] (inkling) ^c01
- [worry] (solution lead) "it's a blank page. I don't know where to start." → drop: this session answered the blank-page worry ^c02
- [idea] (claude) What if it only did the morning part at first, with no watching: you hand it yesterday's meetings, mail and documents, and it hands back the morning note? → park ^c03
- [idea] (claude) What if the morning note worked like a shift handover in a hospital: yesterday-you tells today-you what is open, what changed and what is waiting on someone else? → park ^c04
- [wild] (claude) What if "sets up in two minutes" meant nothing is installed at all, and the helper lives where the mail and calendar already are, so Mac and Windows stop mattering? → park ^c05
- [wild] (claude) What if the note also said what you can safely ignore today, not only what matters? → park ^c06
- [idea] (claude) What if it turned around: each evening it lists what it could not make sense of and asks you, so the morning note gets better by being corrected? → park ^c07
- [thought] (CISO, position of 2026-10-06) "Nothing leaves the laptop. No meeting, mail or document text goes to a cloud service, a vendor or a language model API, with or without redaction." → park ^c08
- [thought] (CISO, position of 2026-10-06) "Any new app registration on the tenant needs my security review first, which takes about six weeks. I will not review a pack that sends text off the device." → keep: [[02-constraints#Constraints|CST-002]] (fact) ^c09
- [thought] (CISO, 6 October) "Security review booked for the week of 16 November, outcome due 4 December. Submit the pack by 10 November. Until it passes, no meeting text leaves a laptop." → keep: [[02-constraints#Constraints|CST-003]] (fact) ^c10
- [thought] (DPO, 7 October) "A digest may name only people who were in the meeting. It may not name people who were merely mentioned, and it may carry no remark about anyone's mood, tone or performance." → keep: [[02-constraints#Constraints|CST-004]] (fact) ^c11
- [unknown] (DPO, 7 October) "The rest of my view waits for the impact assessment." to fetch: the impact assessment, held by the DPO; who starts it, and when? → keep: [[11-unknowns-and-risks#UNK-060 Impact assessment|UNK-060]] (open) ^c12
- [thought] (works council rep, 5 October) "The council will take Heron at its December meeting. We will not agree before we have read the full list of data Heron reads." → keep: [[02-constraints#Constraints|CST-005]] (fact) ^c13
- [thought] (works council rep, 5 October) "Frankfurt stays out of the pilot." → keep: [[02-constraints#Constraints|CST-006]] (fact) ^c14
- [thought] (IT endpoint lead, tenant note of 2026-10-02) One tenant, about 4,200 users: 3,100 Windows managed by Intune, 1,100 Macs managed by Jamf. "Staff cannot install software. Everything is pushed from Intune or Jamf." → keep: [[02-constraints#Constraints|CST-007]] (fact) ^c15
- [thought] (IT endpoint lead, tenant note of 2026-10-02) Teams transcripts exist only where the organiser turned them on, in the organiser's OneDrive. Calendar and mail can be read with each user's own consent; "Reading transcripts needs tenant admin approval." A Graph app registration is raised through the identity team. → keep: [[02-constraints#Constraints|CST-008]] (fact) ^c16
- [thought] (product owner, one-pager of 2026-10-05) Heron reads Teams, Zoom, Outlook and documents, writes a 7:30 digest and a prep note ten minutes before each meeting. "a cloud service writes the summaries with a hosted language model, because the on-device model is poor". A team dashboard shows adoption by team. Pilot starts 2 February 2027 with Client Delivery. → keep: [[04-solution-strategy#The core move|solution strategy]] (inkling) ^c17
- [thought] (CIO, brief of 2026-09-30) "It runs on the PC, so the data never leaves the machine and there is nothing for privacy or the works councils to worry about. Staff choose to install it, so consent is covered. It needs only each person's own Microsoft 365 sign-in. Pilot in January, firm-wide by the summer. Everyone is on Windows, so we start there." → park ^c18
- [unknown] (claude) The CIO brief says staff install it themselves in two minutes; the tenant note says staff cannot install software and everything is pushed from Intune or Jamf. Which one holds, and who owns the answer: the CIO or the IT endpoint lead? → keep: [[11-unknowns-and-risks#UNK-053 Install or push|UNK-053]] (open) ^c19
- [unknown] (claude) The CIO brief and the CISO say the data stays on the machine; the product owner's one-pager has a cloud service and a hosted language model writing the summaries. Which design is meant, and who settles it? → keep: [[11-unknowns-and-risks#UNK-051 Text call|UNK-051]] (open) ^c20
- [unknown] (claude) The CIO brief says everyone is on Windows and the first ask says Mac and Windows; the tenant note counts 1,100 Macs. Is the Mac in the first release or later? → keep: [[11-unknowns-and-risks#UNK-054 Mac in the first release|UNK-054]] (open) ^c21
- [unknown] (claude) Pilot dates differ: January (CIO), 2 February 2027 with Client Delivery (product owner). The CISO outcome is due 4 December and the works council meets in December. Which date is real, and does Client Delivery include anyone in Frankfurt? → keep: [[11-unknowns-and-risks#UNK-055 Frankfurt in Client Delivery|UNK-055]] (open) ^c22
- [unknown] (claude) The product owner calls the on-device model poor, and the CISO allows only on-device. Has anyone tried a model on a managed laptop against the digest, and who would know? → keep: [[11-unknowns-and-risks#UNK-056 On-device model quality|UNK-056]] (open) ^c23
- [unknown] (claude) Does the works council's "full list of data Heron reads" include the team adoption dashboard, and is there a list yet? to fetch: the full list of data Heron reads, held by nobody recorded; who writes it? → keep: [[11-unknowns-and-risks#UNK-057 Full list of data Heron reads|UNK-057]] (open) ^c24
- [unknown] (claude) to fetch: the security review pack the CISO wants by 10 November, held by the CISO; who writes it, and is a six-week app-registration review part of that or on top of it? → keep: [[11-unknowns-and-risks#UNK-058 Security review pack|UNK-058]] (open) ^c25
- [unknown] (claude) Transcripts exist only where the organiser turned them on and need tenant admin approval. For most meetings, does "watches your meetings" mean the calendar entry only? Who decides on admin approval? → keep: [[11-unknowns-and-risks#UNK-059 Transcripts and admin approval|UNK-059]] (open) ^c26
- [idea] (claude) What if the first version read only the user's calendar and mail headers, on the laptop, with no transcripts and no documents: the shortest possible list to put in front of the council and the CISO? → park ^c27
- [wild] (claude) What if the digest were built only from what the person wrote themselves (their own notes and sent mail), so no one else's words are read and nobody can be named by mistake? → park ^c28
- [wild] (claude) What if the works council and the DPO wrote the list of what Heron may read, and the product could not read anything off that list? → park ^c29
- [thought] (solution lead) "I was wrong about consent—opt-in clicks don't cover it." → keep: [[04-solution-strategy#The core move|solution strategy]] (inkling) ^c30
- [thought] (solution lead) "Most of this is news—CISO won't review anything that sends text off the laptop, product owner wants cloud, install doesn't work with Intune/Jamf." → drop: restates the CISO position, the tenant note and the one-pager, which are kept on their own lines ^c31
- [worry] (solution lead) "I don't think the CIO knows the CISO's hard line yet" → keep: [[11-unknowns-and-risks#UNK-052 CISO line reaching the CIO|UNK-052]] (open) ^c32
- [thought] (solution lead) "commit the quotes as-is—I'll need them for the conversation." Consent given in this session to commit the quotes from `.inbox/` in this record; the `.inbox/` files themselves stay uncommitted. → drop: records consent to commit the quotes, not content for the plan ^c33
- [unknown] (claude) Who tells the CIO about the CISO's line, and by when? Owner and ask-by are for the solution lead to set at close. → keep: [[11-unknowns-and-risks#UNK-052 CISO line reaching the CIO|UNK-052]] (open) ^c34
- [idea] (claude) What if consent did not rest on a click at all, but on the council's agreement to a published list of what is read, and each person could see on screen what was read about them today? → park ^c35
- [idea] (claude) What if "two minutes" were the first-run sign-in and not the install: Intune and Jamf push Heron to every laptop, and the person only switches it on? → park ^c36
- [idea] (claude) What if the product owner and the CISO judged the on-device digest together, blind, on a dozen real mornings, before either side's position was argued? → keep: [[04-solution-strategy#The core move|solution strategy]] (inkling) ^c37
- [wild] (claude) What if the "follows the person across devices" need were met by a one-page note the person carries, such as a file they move themselves, so nothing is stored anywhere but the laptop? → park ^c38
- [thought] (solution lead) "The blind judging stops them arguing, which is worth testing." Taken up on a nod from `^c37`. → keep: [[04-solution-strategy#The core move|solution strategy]] (inkling) ^c39
- [thought] (solution lead) "the timeline's real—January packaging, February pilot" → keep: [[02-constraints#Constraints|CST-009]] (fact) ^c40
- [worry] (solution lead) "the CISO and product owner are at opposite ends." → keep: [[11-unknowns-and-risks#UNK-051 Text call|UNK-051]] (open) ^c41
- [worry] (solution lead, pre-mortem) "The CISO and product owner are at opposite ends and nobody's making them pick. We get to January still arguing, packaging doesn't happen, and February slips." → keep: [[11-unknowns-and-risks#R-01 Two ends, nobody picks|R-01]] (open) ^c42
- [worry] (solution lead, pre-mortem) "The digest fails the first morning—someone mentioned but not on the call, a deadline way in the future. Sam sees more than a couple like that and she stops reading by Wednesday." → keep: [[11-unknowns-and-risks#R-02 Digest fails the first morning|R-02]] (open) ^c43
- [worry] (solution lead, pre-mortem) "The on-device model we're forced to use turns out not to be good enough. Same result." → keep: [[11-unknowns-and-risks#UNK-056 On-device model quality|UNK-056]] (open) ^c44
- [worry] (solution lead, pre-mortem) "The desk agent team gets handed Heron with no boundary between what they own and what the product owner owns. They design all of February instead of building. Nothing ships for April." → keep: [[11-unknowns-and-risks#R-03 No boundary with the desk agent team|R-03]] (open) ^c45
- [thought] (solution lead) "CISO and product owner are at opposite ends—someone's got to call it, and that decides everything else. That's the lock." → keep: [[11-unknowns-and-risks#UNK-051 Text call|UNK-051]] (open) ^c46
- [unknown] (solution lead) "Who settles it?" Between the CISO's "Nothing leaves the laptop" and the product owner's cloud service writing the summaries, who has the authority to call it? No paper in the vault says. Owner and ask-by to be set at close. → keep: [[11-unknowns-and-risks#UNK-051 Text call|UNK-051]] (open) ^c47
- [idea] (claude) What if the call were put to whoever settles it as one yes-or-no question, "may meeting text leave the laptop in the pilot?", so the CISO's line and the product owner's design are not argued as whole designs? → park ^c48
- [thought] (solution lead) Q-FIN-01@INI-001, F1.1: "Value for customers is no." → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-01@INI-001]] (not-applicable) ^c49
- [thought] (solution lead) A belief, no source named: "Everything locks on the text call—CIO's the budget holder, they settle it." → keep: [[11-unknowns-and-risks#UNK-051 Text call|UNK-051]] (open) ^c50
- [thought] (solution lead) waits on the text call in [[2026-10-12-desk-helper-start#^c47]] (close gives it its unknown number): Q-DAT-01@INI-001, Q-DAT-05@INI-001, Q-PTN-01@INI-001, F1.4, F1.5, F1.6, F1.12, F1.13, F1.18 → keep: [[11-unknowns-and-risks#Question ledger|Q-DAT-01@INI-001]] (unknown) ^c51
- [unknown] (solution lead) "Haven't heard if the CISO's position has reached them yet." Has the CISO's position reached the CIO, who settles the text call? The solution lead holds this to find out. → keep: [[11-unknowns-and-risks#UNK-052 CISO line reaching the CIO|UNK-052]] (open) ^c52
- [thought] (solution lead) Ask-by for the text call in [[2026-10-12-desk-helper-start#^c47]] and for `^c52`: "Early November at the latest—before the 10 November deadline." → drop: used as the ask-by date on the two unknowns it names ^c53
- [worry] (solution lead) "I haven't called the CIO yet, honestly not sure what they'll say." → keep: [[11-unknowns-and-risks#UNK-052 CISO line reaching the CIO|UNK-052]] (open) ^c54
- [thought] (solution lead) "Council meeting and data list are running their own track." Not waiting on the text call: F1.9, F1.14 → drop: only says which findings do not wait, and both are open rows in the ledger ^c55
- [thought] (solution lead) "Everything else rides on the text call." Waits on the text call in [[2026-10-12-desk-helper-start#^c47]]: Q-FIN-02@INI-001, Q-REG-01@INI-001, Q-REG-02@INI-001, Q-REG-05@INI-001, Q-OPS-04@INI-001, Q-OPS-06@INI-001, Q-OPS-07@INI-001, F1.3, F1.7, F1.8, F1.10, F1.11, F1.19, F1.23, F1.24, F1.25 → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-02@INI-001]] (unknown) ^c56

## Reviews

### 1. after the pre-mortem, 2026-10-12

- **Coverage:** FIN found 3, 1 dropped; DAT found 8, 1 dropped; PTN found 4; REG found 6; OPS found 6, 1 dropped
- **Dropped:** [FIN] the quote does not mention what the finding is about: if the cloud design were chosen, who would pay the vendor and carry the liability. [DAT] the quote does not mention what the finding is about: what lawful basis Heron rests on, given that opt-in clicks do not cover it. [OPS] its quote "## Today" has fewer than 4 words: does Heron replace anything, and who still depends on it.
- **Merged:** [PTN] into F1.10: Who in the identity team and tenant admin group owns the Graph app registration and the transcript approval, and what turnaround have they agreed to? [REG] into F1.7: How will the digest enforce the DPO's rule on who may be named, and is this recorded as a constraint?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | Does Heron or any partner it uses hold anything of value for staff or customers (credits, balances, vouchers, deposits, stored per-person data that carries weight)? If not, record that as decided. | "What if the ”follows the person across devices” need were met by a one-page note the person carries" in [[2026-10-12-desk-helper-start]] |
| F1.2 | FIN | normal | Q-FIN-02@INI-001 | Who funds the build (the desk agent team, the product owner, the CIO) and who carries the running cost afterwards, including any hosted-model or per-user licence fees? | "a cloud service writes the summaries with a hosted language model, because the on-device model is poor" in [[2026-10-12-desk-helper-start]] |
| F1.3 | FIN | normal | new | Who funds and staffs the security review pack, the app-registration review, the impact assessment and the Intune and Jamf packaging, and is that budget agreed before January? | "Submit the pack by 10 November. Until it passes, no meeting text leaves a laptop." in [[2026-10-12-desk-helper-start]] |
| F1.4 | DAT | high | Q-DAT-01@INI-001 | Will meeting, mail and document text go to any party other than the user's own laptop (a cloud service, a hosted model vendor)? Who settles this between the CISO and the product owner, and is the answer recorded as decided? | "a cloud service writes the summaries with a hosted language model, because the on-device model is poor" in [[2026-10-12-desk-helper-start]] |
| F1.5 | DAT | high | Q-DAT-05@INI-001 | Is using people's meetings, mail, documents and transcripts for digests and prep notes a different purpose from the one they were collected for? Who starts the impact assessment, and when? | "The rest of my view waits for the impact assessment." in [[2026-10-12-desk-helper-start]] |
| F1.6 | DAT | high | Q-DAT-05@INI-001 | Is the team adoption dashboard in scope? If so, what data does it use, and does the DPO or works council need to approve it as a separate purpose? | "A team dashboard shows adoption by team." in [[2026-10-12-desk-helper-start]] |
| F1.7 | DAT, REG | high | new | How will the digest be stopped from naming people who were only mentioned? Should the DPO's limit be written into 02-constraints.md? | "A digest may name only people who were in the meeting. It may not name people who were merely mentioned" in [[2026-10-12-desk-helper-start]] |
| F1.8 | DAT | normal | new | Does Client Delivery include anyone in Frankfurt, and how will their data be kept out of the pilot? | "Frankfurt stays out of the pilot." in [[2026-10-12-desk-helper-start]] |
| F1.9 | DAT | high | new | Who writes the full list of data Heron reads, and by when, so the council can read it before its December meeting? | "We will not agree before we have read the full list of data Heron reads." in [[2026-10-12-desk-helper-start]] |
| F1.10 | DAT, PTN | normal | new | Do the other attendees of a transcribed meeting have a say in Heron reading it, and who decides whether to request tenant admin approval? | "Reading transcripts needs tenant admin approval." in [[2026-10-12-desk-helper-start]] |
| F1.11 | DAT | normal | new | What needs to follow a person between their devices, and where may it be stored under the CISO's rule? | "What if the ”follows the person across devices” need were met by a one-page note the person carries" in [[2026-10-12-desk-helper-start]] |
| F1.12 | PTN | high | Q-PTN-01@INI-001 | Does ownership, operation or payment change for any system, agreement, team or service? In particular, who owns Heron, who runs the Intune and Jamf packaging, and who pays for it? | "The desk agent team gets handed Heron with no boundary between what they own and what the product owner owns." in [[2026-10-12-desk-helper-start]] |
| F1.13 | PTN | high | new | Is there or would there be a contract with a cloud or language-model vendor? Who would sign it, on what terms, and would it be allowed given the CISO's line? | "a cloud service writes the summaries with a hosted language model, because the on-device model is poor" in [[2026-10-12-desk-helper-start]] |
| F1.14 | PTN | high | new | What agreement with the works council does the pilot need, who holds it, and how does a December meeting fit a January packaging date and a 2 February pilot? | "We will not agree before we have read the full list of data Heron reads." in [[2026-10-12-desk-helper-start]] |
| F1.15 | REG | normal | Q-REG-01@INI-001 | Is Heron sold or promised across parties, such as with a cloud or model vendor, or is it an internal tool only? | "”a cloud service writes the summaries with a hosted language model, because the on-device model is poor”" in [[2026-10-12-desk-helper-start]] |
| F1.16 | REG | high | Q-REG-02@INI-001 | Which regulations, approvals or licences apply (data protection impact assessment, works council agreement, security review)? Who starts the impact assessment, and when? | "”The rest of my view waits for the impact assessment.”" in [[2026-10-12-desk-helper-start]] |
| F1.17 | REG | normal | Q-REG-05@INI-001 | If the digest is wrong, or the cloud or model part fails, who is liable to the staff who rely on it? | "The digest fails the first morning—someone mentioned but not on the call, a deadline way in the future." in [[2026-10-12-desk-helper-start]] |
| F1.18 | REG | high | new | What is the lawful basis for reading staff mail, meetings and documents, if opt-in consent does not hold? Who owns that answer: the DPO or the works council? | "Staff choose to install it, so consent is covered." in [[2026-10-12-desk-helper-start]] |
| F1.19 | REG | normal | new | Does Client Delivery include anyone in Frankfurt, and what is the gate sequence (CISO outcome, works council, DPO impact assessment) before 2 February 2027? | "”Frankfurt stays out of the pilot.”" in [[2026-10-12-desk-helper-start]] |
| F1.20 | OPS | normal | Q-OPS-04@INI-001 | Which teams or systems do overlapping jobs here (desk agent team, product owner, identity team, Intune and Jamf teams)? Who owns what, and who draws the boundary? | "The desk agent team gets handed Heron with no boundary between what they own and what the product owner owns." in [[2026-10-12-desk-helper-start]] |
| F1.21 | OPS | high | Q-OPS-06@INI-001 | Who is affected but not yet consulted (Mac users, Frankfurt, identity team, IT endpoint team, people mentioned in meetings, the desk agent team), and who wants something different? Who tells the CIO about the CISO's line, and by when? | "I don't think the CIO knows the CISO's hard line yet" in [[2026-10-12-desk-helper-start]] |
| F1.22 | OPS | high | Q-OPS-07@INI-001 | Which unsupported beliefs does the plan rest on (on-device model quality, the pilot date, the Windows-only assumption, the CIO's no-privacy-concern view)? Which one would change the plan most if wrong, and who will test it? | "Has anyone tried a model on a managed laptop against the digest, and who would know?" in [[2026-10-12-desk-helper-start]] |
| F1.23 | OPS | high | new | Can packaging in January happen before the CISO outcome of 4 December and the council's December view? Who owns the pilot date and the order of the gates? | "the timeline's real—January packaging, February pilot" in [[2026-10-12-desk-helper-start]] |
| F1.24 | OPS | high | new | Who writes the data list, the impact assessment and the security review pack, and by when, given the 10 November submission? | "to fetch: the full list of data Heron reads, held by nobody recorded; who writes it?" in [[2026-10-12-desk-helper-start]] |
| F1.25 | OPS | normal | new | Who runs and supports Heron day to day (packaging, Intune and Jamf pushes, failed digests), and who handles problems early in the pilot? | "writes a 7:30 digest and a prep note ten minutes before each meeting" in [[2026-10-12-desk-helper-start]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| G1 | - | inkling | [[2026-10-12-desk-helper-start#^c01]] |
| CST-002 | - | fact | [[2026-10-12-desk-helper-start#^c09]] |
| CST-003 | - | fact | [[2026-10-12-desk-helper-start#^c10]] |
| CST-004 | - | fact | [[2026-10-12-desk-helper-start#^c11]] |
| CST-005 | - | fact | [[2026-10-12-desk-helper-start#^c13]] |
| CST-006 | - | fact | [[2026-10-12-desk-helper-start#^c14]] |
| CST-007 | - | fact | [[2026-10-12-desk-helper-start#^c15]] |
| CST-008 | - | fact | [[2026-10-12-desk-helper-start#^c16]] |
| CST-009 | - | fact | [[2026-10-12-desk-helper-start#^c40]] |
| UNK-051 | - | open | [[2026-10-12-desk-helper-start#^c47]] |
| UNK-052 | - | open | [[2026-10-12-desk-helper-start#^c52]] |
| UNK-053 | - | open | [[2026-10-12-desk-helper-start#^c19]] |
| UNK-054 | - | open | [[2026-10-12-desk-helper-start#^c21]] |
| UNK-055 | - | open | [[2026-10-12-desk-helper-start#^c22]] |
| UNK-056 | - | open | [[2026-10-12-desk-helper-start#^c23]] |
| UNK-057 | - | open | [[2026-10-12-desk-helper-start#^c24]] |
| UNK-058 | - | open | [[2026-10-12-desk-helper-start#^c25]] |
| UNK-059 | - | open | [[2026-10-12-desk-helper-start#^c26]] |
| UNK-060 | - | open | [[2026-10-12-desk-helper-start#^c12]] |
| R-01 | - | open | [[2026-10-12-desk-helper-start#^c42]] |
| R-02 | - | open | [[2026-10-12-desk-helper-start#^c43]] |
| R-03 | - | open | [[2026-10-12-desk-helper-start#^c45]] |
| Q-FIN-01@INI-001 | - | not-applicable | [[2026-10-12-desk-helper-start#^c49]] |
| Q-DAT-01@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c51]] |
| Q-DAT-05@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c51]] |
| Q-PTN-01@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c51]] |
| Q-FIN-02@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| Q-REG-01@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| Q-REG-02@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| Q-REG-05@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| Q-OPS-04@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| Q-OPS-06@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| Q-OPS-07@INI-001 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-FIN-01 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-DAT-01 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-DAT-02 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-DAT-03 | - | open | [[2026-10-12-desk-helper-start#1. after the pre-mortem, 2026-10-12]] |
| R-DAT-04 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-DAT-05 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-PTN-01 | - | unknown | [[2026-10-12-desk-helper-start#^c51]] |
| R-PTN-02 | - | open | [[2026-10-12-desk-helper-start#1. after the pre-mortem, 2026-10-12]] |
| R-REG-01 | - | unknown | [[2026-10-12-desk-helper-start#^c51]] |
| R-REG-02 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-OPS-01 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-OPS-02 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
| R-OPS-03 | - | unknown | [[2026-10-12-desk-helper-start#^c56]] |
