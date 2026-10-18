---
id: constraints
type: initiative-section
title: Constraints
arc42: "§2"
state: fact
sources: [SRC-01, SRC-03, SRC-05, SRC-06, SRC-07, SRC-08]
owner: "@solution-lead"
authored: authored
---

# Constraints

The security pack must reach the CISO's review by 10 November 2026, and the CISO, the DPO, the works council and IT's device management each fix something about what Heron may do and how it can arrive. None of these has been designed around yet.

| ID | Constraint | Where it comes from | What it forces |
|---|---|---|---|
| CST-1 | The security pack goes to the CISO's review by 10 November 2026 | [[2026-10-11-desk-helper-kickoff#^c18\|The solution lead says there are 30 days]] to put the pack together | The pack cannot be written until [[11-unknowns-and-risks#UNK-007 CISO security pack requirements\|the CISO's requirements]] and [[11-unknowns-and-risks#UNK-006 What data Heron reads\|what data Heron reads]] are known |
| CST-2 | Staff cannot install software; everything reaches a PC through Intune on Windows or Jamf on Mac | [[sources#SRC-03\|The IT endpoint lead's tenant note]] says so | Heron has to be pushed by IT, so [[11-unknowns-and-risks#UNK-011 IT packaging\|whether IT will package it]] decides whether anyone can run it |
| CST-3 | No meeting, mail or document text goes to a cloud service, a vendor or a language model API, with or without redaction, and none leaves a laptop until the review passes | [[sources#SRC-06\|The CISO's position]] and [[sources#SRC-07\|the review booking]] | The CISO will not review a pack that sends text off the device |
| CST-4 | Any new app registration on the tenant needs the CISO's security review first, which takes about six weeks | [[sources#SRC-06\|The CISO's position]] | Heron's Graph registration cannot be raised until that review is done |
| CST-5 | The security review is booked for the week of 16 November 2026, with the outcome due 4 December | [[sources#SRC-07\|The CISO's review booking]] | The pack goes in by 10 November, and nothing the review gates can start before 4 December |
| CST-6 | A digest may name only people who were in the meeting, and may carry no remark about anyone's mood, tone or performance | [[sources#SRC-08\|The DPO's answer]] | The rest of the DPO's view waits for the impact assessment |
| CST-7 | The works council takes Heron at its December meeting and will not agree before it has read the full list of data Heron reads | [[sources#SRC-05\|The works council representative's note]] | [[11-unknowns-and-risks#UNK-006 What data Heron reads\|What data Heron reads]] has to be written down before December |
| CST-8 | Frankfurt stays out of the pilot | [[sources#SRC-05\|The works council representative's note]] | The pilot can only include London |
