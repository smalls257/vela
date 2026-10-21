---
id: constraints
type: initiative-section
title: Constraints
arc42: "§2"
state: fact
sources: [SRC-007, SRC-015, SRC-016, SRC-009, SRC-010, SRC-011, SRC-013, SRC-014]
owner: "@solution-lead"
authored: authored
---

# Constraints

The constraints come from four places: the security officer's review, the data protection officer's rule on naming people, the works council, and the way IT puts software on laptops. Packaging is set for January 2027 and the pilot for February 2027. Whether the security officer's rule holds for the whole pilot depends on [[11-unknowns-and-risks#UNK-051 Text call|who settles whether meeting text may leave the laptop]], which is open.

| ID | Constraint | Where it comes from | What it forces |
|---|---|---|---|
| CST-002 | Any new app registration on the tenant needs the CISO's security review first, which takes about six weeks. | [[sources#SRC-009\|the CISO's position]] | The registration Heron needs cannot be raised until the review is requested, so the six weeks sit on the critical path. |
| CST-003 | The security review pack goes in by November 10, 2026 and the outcome is due December 4, 2026. Until it passes, no meeting text leaves a laptop. | [[sources#SRC-010\|the CISO's review booking]] | Any design that sends meeting text off the laptop cannot run before December 4, 2026. |
| CST-004 | A digest may name only people who were in the meeting, and may carry no remark about anyone's mood, tone or performance. | [[sources#SRC-011\|the DPO's answer]] | The digest must tell attendees from people merely mentioned, and must leave out remarks on mood, tone or performance. |
| CST-005 | The works council takes Heron at its December meeting and will not agree before it has read the full list of data Heron reads. | [[sources#SRC-014\|the works council note]] | The full data list has to exist before the December meeting. |
| CST-006 | Frankfurt stays out of the pilot. | [[sources#SRC-014\|the works council note]] | The pilot population must exclude Frankfurt staff. |
| CST-007 | Staff cannot install software. Everything is pushed from Intune (Windows) or Jamf (Mac). | [[sources#SRC-013\|the tenant note]] | Heron must be packaged for Intune and for Jamf, and a person can only switch it on. |
| CST-008 | Teams transcripts exist only where the organizer turned them on, and reading them needs tenant admin approval. A Graph app registration is raised through the identity team. | [[sources#SRC-013\|the tenant note]] | For most meetings Heron has the calendar entry only, unless admin approval is granted. |
| CST-009 | Packaging happens in January 2027 and the pilot starts on February 2, 2027. | [[sources#SRC-007\|the solution lead's account]] and [[sources#SRC-015\|their account of the start date]] | The security, council and impact-assessment gates have to fit before these dates. |
| CST-010 | The Desktop agent ships through Intune and Jamf in the endpoint lead's packaging slot on January 18, 2027, and he will not raise an earlier one. | [[sources#SRC-016\|the solution lead's account of the packaging slot]] | The agent's boundary and its contracts have to be settled by early January. |

## History

#### CST-009

- **Override:** "a line about the future is an assumption, whatever its source's Kind" by @solution-lead on 2026-10-12: "The pilot start is fact though—February 2, not a plan."
