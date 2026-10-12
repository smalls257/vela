---
id: 2026-10-11-privacy-m365-device-line
type: session
title: "Grill: privacy, M365 access and the device line"
date: 2026-10-11
modes: [grill]
status: closed
summary: "Grilled APP-heron: no text leaves the device in release one, plainer note instead of a hosted fallback; Data and Security cells wait on UNK-020"
---

# 2026-10-11 Grill: privacy, M365 access and the device line

## Agenda

- APP-heron: GATE-3 confirmed yes, status decided
- CONCERN-DATA-heron: GATE-3 confirmed yes, status off-agenda: UNK-020
- CONCERN-SECURITY-heron: GATE-3 confirmed yes, status off-agenda: UNK-020
- CON-001: GATE-3 confirmed no, status off-agenda: UNK-020

## Captures

- The CISO has not answered UNK-020 yet; CON-001 comes off the agenda. — Sim Lead ^c01
  → park
- [decision] Yes to the agenda: APP-heron, Heron's Data cell and Heron's Security cell. — Sim Lead ^c02
  → drop: agenda confirmation; the outcomes are on c04 and c05
- [thought] I'll ring the CISO this afternoon; I need that calendar answer (UNK-020) before we lock these cells down. — Sim Lead ^c03
  → drop: a to-do, superseded by c07
- [decision] (Q1, APP-heron) Option 2: that's the CISO's line in release one, nothing off the device. The plainer note holds the pack, and we offer the product owner the hosted route for release two once the DPO clears it, which keeps them a path to better summaries later. — Sim Lead ^c04
  → keep: [[heron-building-blocks#Heron|APP-heron]] (decided)
- [decision] Park the Data and Security cells until the CISO answers UNK-020. I'll ring the CISO today. — Sim Lead ^c05
  → keep: [[11-unknowns-and-risks#UNK-020 Calendar read and the device line|UNK-020]] (open)
- [decision] Yes, add the Data and Security concerns to UNK-020's Blocks. I'm calling the CISO now. — Sim Lead ^c06
  → keep: [[11-unknowns-and-risks#UNK-020 Calendar read and the device line|UNK-020]] (open)
- [fact-candidate] Rang the CISO and got voicemail. The calendar question (UNK-020) is on the message. He will call back this afternoon or Monday. No answer yet. — Sim Lead ^c07
  → park

## Reviews

### 1. On the agenda, 2026-10-11

- **Coverage:** FIN found 2; DAT found 2; PTN found 3; REG found 3, 1 dropped; OPS found 4, 2 dropped
- **Dropped:** [REG] quote under 4 words (liability if a part fails); [OPS] quote does not mention what the finding is about (what Heron retires); [OPS] a new question about a page this session did not change (whether UNK-012 is closed)
- **Merged:** [DAT] into F1.2: can the on-device and privacy cells be settled without the UNK-020 answer; [REG] into F1.2: who gets the CISO's answer and what is the fallback for the pack; [OPS] into F1.2: who chases the CISO's office and what is the fallback

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| APP-heron | assumption | decided | [[2026-10-11-privacy-m365-device-line#^c04]] |
| F1.1 | FIN | normal | R-FIN-02 | Where will Heron process and keep data, and who pays for and carries the risk of any hosting or compute? | "Does Heron process meeting, mail and document text only on the laptop" in [[11-unknowns-and-risks]] |
| F1.2 | FIN, DAT, REG, OPS | high | new | If the CISO rules the calendar read counts as text leaving the device, who pays for the redesign or the delay to the 10 November pack, and who decides meanwhile? | "The CISO has not answered UNK-020 yet; CON-001 comes off the agenda." in [[2026-10-11-privacy-m365-device-line]] |
| F1.3 | DAT | normal | R-DAT-05 | Can Heron read only transcripts of meetings the pilot user organised, or all they attended, and who gives the tenant admin approval? | "It says Teams transcripts exist only where the meeting's organiser turned them on, and that they sit in the organiser's OneDrive." in [[03-context-and-scope]] |
| F1.4 | PTN | normal | Q-PTN-03@PTY-02 | Is Zoom in use at the firm, and who holds the agreement? | "Whether Zoom is in use at the firm is not recorded." in [[03-context-and-scope]] |
| F1.5 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to the Zoom agreement need, and who must give it? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.6 | PTN | high | new | Which Microsoft agreement covers the calendar read in CON-001, and does Heron's use stay inside it? | "The CISO has not answered UNK-020 yet; CON-001 comes off the agenda." in [[2026-10-11-privacy-m365-device-line]] |
| F1.7 | REG | normal | Q-REG-02@INI-001 | Is anything Heron touches regulated or licensed, and has the DPO's impact assessment started? | "The rest of the DPO's view waits for the impact assessment" in [[02-constraints]] |
| F1.8 | REG | high | R-REG-05 | Does the DPO's content rule cover the pre-call prep note, and has the DPO been asked about it? | "A digest may name only people who were in the meeting, and may carry no remark about anyone's mood, tone or performance" in [[02-constraints]] |
| F1.9 | OPS | normal | Q-OPS-04@INI-001 | Does any other tool, team or process already do pre-call prep? | "Today they piece it together themselves." in [[CAP-001-prepare-a-client-for-a-call]] |
| F1.10 | OPS | normal | R-OPS-02 | Who runs and supports Heron on pilot laptops, and who set the 30-day pack deadline? | "The solution lead says IT's packaging slot of 18 January is booked but has not heard @endpoint-lead say yes, and will ask directly." in [[11-unknowns-and-risks]] |
| F1.11 | OPS | normal | R-OPS-03 | What happens to Frankfurt and the other sites between the London pilot and the CIO's summer target? | "Frankfurt stays out of the pilot" in [[02-constraints]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| APP-heron | assumption | decided | [[2026-10-11-privacy-m365-device-line#^c04]] |
| R-FIN-06 | - | unknown | [[2026-10-11-privacy-m365-device-line#1. On the agenda, 2026-10-11]] |
| R-PTN-04 | - | unknown | [[2026-10-11-privacy-m365-device-line#1. On the agenda, 2026-10-11]] |
