---
id: 2026-10-06-decode-cio-mandate
type: session
title: "Dump & Diverge: decode CIO mandate"
date: 2026-10-06
modes: [dump]
status: closed
summary: Decoded the CIO mandate into 20 open unknowns, one inkling goal (G1) and 18 reviewer questions; nothing decided.
---

# 2026-10-06 Dump & Diverge: decode CIO mandate

## Captures

- [thought] (CIO) "one customer, one journey, one account across ferry and rail by next summer" → keep: [[01-goals#Goals|G1]] (inkling) ^c01
- [worry] (solution lead) "Nobody has said what any of that means." → keep: [[11-unknowns-and-risks#UNK-001 Meaning of the mandate|UNK-001]] (open) ^c02
- [worry] (solution lead) "I don't know where to start." → drop: not an item, the session itself answered where to start ^c03
- [unknown] (claude) "One customer": is that one identity across ferry and rail, or one customer record that merges two existing ones? → keep: [[11-unknowns-and-risks#UNK-001 Meaning of the mandate|UNK-001]] (open) ^c04
- [unknown] (claude) "One journey": one ticket, one booking, or one trip the customer plans and sees as a whole? → keep: [[11-unknowns-and-risks#UNK-001 Meaning of the mandate|UNK-001]] (open) ^c05
- [unknown] (claude) "One account": a login, a wallet, a loyalty balance, or all three? → keep: [[11-unknowns-and-risks#UNK-001 Meaning of the mandate|UNK-001]] (open) ^c06
- [unknown] (claude) "Next summer": which date, and is it a launch for customers or a first release for staff? → keep: [[11-unknowns-and-risks#UNK-002 Meaning of next summer|UNK-002]] (open) ^c07
- [unknown] (claude) Who in the CIO's office can say what the mandate means, and has anyone asked? → keep: [[11-unknowns-and-risks#UNK-003 Who speaks for CIO|UNK-003]] (open) ^c08
- [idea] (claude) What if "one account" meant the customer never logs in at all, and a phone number or a card is the account? → park ^c09
- [wild] (claude) What if the first release is one real journey for one real customer, done by hand behind the scenes, before any system changes? → park ^c10
- [thought] (solution lead) "The CIO's unreachable" → keep: [[11-unknowns-and-risks#UNK-003 Who speaks for CIO|UNK-003]] (open) ^c11
- [thought] (solution lead) "CFO wants one platform" → keep: [[11-unknowns-and-risks#UNK-005 CFO platform versus account|UNK-005]] (open) ^c12
- [thought] (solution lead) "Rail Product wants it rail-first" → keep: [[11-unknowns-and-risks#UNK-006 Meaning of rail-first|UNK-006]] (open) ^c13
- [thought] (solution lead) "Ferry Ops won't touch anything before May" → keep: [[11-unknowns-and-risks#UNK-007 May freeze scope and end|UNK-007]] (open) ^c14
- [thought] (solution lead) "SeaBook and RailCore are on completely separate stacks with completely separate customer data." → keep: [[11-unknowns-and-risks#UNK-011 How ferry systems relate|UNK-011]] (open) ^c15
- [unknown] (solution lead) "Honestly not sure what "one account" even means — do we link the records or merge them?" → keep: [[11-unknowns-and-risks#UNK-001 Meaning of the mandate|UNK-001]] (open) ^c16
- [unknown] (claude) Is the CFO's "one platform" the same thing as the CIO's "one account", or a second goal? Ask: the CFO. → keep: [[11-unknowns-and-risks#UNK-005 CFO platform versus account|UNK-005]] (open) ^c17
- [unknown] (claude) What does "rail-first" mean to Rail Product: first to launch, first to be served, or first to be rebuilt? Ask: Rail Product. → keep: [[11-unknowns-and-risks#UNK-006 Meaning of rail-first|UNK-006]] (open) ^c18
- [unknown] (claude) Is "before May" a freeze on any change to SeaBook, on any change to ferry operations, or on any ask of the team? Ask: Ferry Ops. → keep: [[11-unknowns-and-risks#UNK-007 May freeze scope and end|UNK-007]] (open) ^c19
- [unknown] (claude) What customer data do SeaBook and RailCore each hold, and what do their customers agreed to? Ask: the owner of each system. → keep: [[11-unknowns-and-risks#UNK-008 Customer data and consents|UNK-008]] (open) ^c20
- [unknown] (claude) Who else is affected by this and not yet in the room? → keep: [[11-unknowns-and-risks#UNK-020 Others affected not in room|UNK-020]] (open) ^c21
- [idea] (claude) What if "link" is the first release and "merge" is a later one, so Ferry Ops has nothing to touch before May? → park ^c22
- [idea] (claude) What if the link sat in a small third service that holds only a customer's two IDs, so neither stack changes? → park ^c23
- [idea] (claude) What if the CFO's "one platform" and Rail Product's "rail-first" were one plan: RailCore becomes the base and ferry joins it after May? → park ^c24
- [wild] (claude) What if the customer did the linking, by entering one booking reference from each side, and no one matched records behind the scenes? → park ^c25
- [wild] (claude) What if "one account" were only a shared sign-in, and each system kept its own customer record forever? → park ^c26
- [thought] (solution lead) "Ferry customer DB and Northway ID are completely different on email — families share one email on ferry but every rail account needs unique." → keep: [[11-unknowns-and-risks#UNK-009 Family email clash|UNK-009]] (open) ^c27
- [worry] (solution lead) "Honestly not sure how we link those without asking a million customers to change." → keep: [[11-unknowns-and-risks#UNK-009 Family email clash|UNK-009]] (open) ^c28
- [thought] (solution lead) "there's the mainframe thing: FERRYMASTER's got two people who understand it, both probably on their way out." → keep: [[11-unknowns-and-risks#UNK-014 FERRYMASTER people and docs|UNK-014]] (open) ^c29
- [worry] (solution lead) "If we're touching customer data at all, we've got a real problem on the ferry side." → keep: [[11-unknowns-and-risks#UNK-010 Data Protection Officer|UNK-010]] (open) ^c30
- [unknown] (claude) How do SeaBook, the ferry customer DB and FERRYMASTER relate: one system, three, or layers of one? Ask: Ferry Ops. → keep: [[11-unknowns-and-risks#UNK-011 How ferry systems relate|UNK-011]] (open) ^c31
- [unknown] (claude) Is Northway ID the rail login in RailCore or a separate identity service, and who owns it? Ask: Rail Product. → keep: [[11-unknowns-and-risks#UNK-012 Northway ID ownership|UNK-012]] (open) ^c32
- [unknown] (claude) How many ferry customers share an email with another customer, and how many rail accounts exist? to fetch: the customer counts from each system, held by the owner of SeaBook and the owner of RailCore. → keep: [[11-unknowns-and-risks#UNK-013 Customer counts per system|UNK-013]] (open) ^c33
- [unknown] (claude) Who are the two FERRYMASTER people, are they leaving, and when? Ask: Ferry Ops. → keep: [[11-unknowns-and-risks#UNK-014 FERRYMASTER people and docs|UNK-014]] (open) ^c34
- [unknown] (claude) Is any FERRYMASTER knowledge written down, such as a runbook or a data layout? to fetch: any FERRYMASTER documentation, held by the two people who know it. → keep: [[11-unknowns-and-risks#UNK-014 FERRYMASTER people and docs|UNK-014]] (open) ^c35
- [unknown] (claude) Does anything in the customer link need to read from or write to FERRYMASTER, or can it stay outside it? Ask: Ferry Ops. → keep: [[11-unknowns-and-risks#UNK-015 Link and FERRYMASTER access|UNK-015]] (open) ^c36
- [idea] (claude) What if a family were one household account on both sides, with each member a person under it, so a shared email stops being a clash? → park ^c37
- [idea] (claude) What if the rail side accepted a shared email for linked ferry customers and kept its unique rule for everyone else? → park ^c38
- [idea] (claude) What if the link were made at the next booking, when the customer is already typing details, and not by a mailout? → park ^c39
- [idea] (claude) What if the two FERRYMASTER people were asked, before they go, to record what they know, with a leaving date as the deadline? → park ^c40
- [wild] (claude) What if the customer's booking reference, not their email, were the key that joins the two sides? → park ^c41
- [wild] (claude) What if FERRYMASTER were never touched, and a nightly copy of customer data were read out of it and the copy became the thing we link to? → park ^c42
- [thought] (solution lead) "Ferry's got a customer service team in Kestrel Bay, and someone in Finance probably owns the revenue side." → keep: [[11-unknowns-and-risks#UNK-017 Revenue owners in Finance|UNK-017]] (open) ^c43
- [unknown] (solution lead) "Honestly not sure about the port teams or who owns the customer database after the reorganization." → keep: [[11-unknowns-and-risks#UNK-016 Ferry customer DB owner|UNK-016]] (open) ^c44
- [thought] (solution lead) "Nothing like this has been attempted — the two businesses have pretty much been left to operate separately since the merger three months ago." → park: no source for the merger date ^c45
- [unknown] (solution lead) "First week I need to know: is the CIO actually reachable, or are we making decisions against an empty chair?" → keep: [[11-unknowns-and-risks#UNK-003 Who speaks for CIO|UNK-003]] (open) ^c46
- [unknown] (claude) Who in Ferry Finance owns the revenue side, and does anyone in Rail Finance own the same thing? Ask: the CFO. → keep: [[11-unknowns-and-risks#UNK-017 Revenue owners in Finance|UNK-017]] (open) ^c47
- [unknown] (claude) What will the Kestrel Bay customer service team need to do differently if a ferry customer has a linked account? Ask: the Kestrel Bay team lead. → keep: [[11-unknowns-and-risks#UNK-018 Kestrel Bay team change|UNK-018]] (open) ^c48
- [unknown] (claude) Which port teams touch customer data or check customers in, and who speaks for them? Ask: Ferry Ops. → keep: [[11-unknowns-and-risks#UNK-019 Port teams and customer data|UNK-019]] (open) ^c49
- [unknown] (claude) Who owned the ferry customer database before the reorganization, and who owns it now? Ask: the CFO. → keep: [[11-unknowns-and-risks#UNK-016 Ferry customer DB owner|UNK-016]] (open) ^c50
- [unknown] (claude) If the CIO stays unreachable, who can decide in their place, and who can say that for them? Ask: the CFO. → keep: [[11-unknowns-and-risks#UNK-003 Who speaks for CIO|UNK-003]] (open) ^c51
- [idea] (claude) What if the first week produced a one-page "what I think the mandate means" that goes to the CIO's office, so silence counts as a recorded answer? → park ^c52
- [idea] (claude) What if Kestrel Bay customer service, who talk to customers daily, were asked what customers already say about ferry and rail being separate? → park ^c53
- [idea] (claude) What if the merger three months ago is an advantage: nothing is set in stone yet, and the new structure could be asked to name the customer database owner? → park ^c54
- [wild] (claude) What if the empty chair were filled by a named stand-in for the CIO, even for one decision, and the stand-in's name went on the record? → park ^c55
- [wild] (claude) What if the first move were a joint walk-through of one real family's ferry and rail trip, with someone from each business watching? → park ^c56
- [worry] (solution lead) "The FERRYMASTER people leave before we've got anyone else who can read that code. That's a three-month window and we've already lost time." → keep: [[11-unknowns-and-risks#UNK-014 FERRYMASTER people and docs|UNK-014]] (open) ^c57
- [worry] (solution lead) "The CIO stays silent and we end up building the wrong thing for Rail Product and the CFO, and then we have to rip it out." → keep: [[11-unknowns-and-risks#UNK-003 Who speaks for CIO|UNK-003]] (open) ^c58
- [worry] (solution lead) "Ferry Ops says no during the freeze — May through September is five months we can't touch anything, and that's half our timeline." → keep: [[11-unknowns-and-risks#UNK-007 May freeze scope and end|UNK-007]] (open) ^c59
- [worry] (solution lead) "We've built something that works for the ferry-rail customer but the Data Protection Officer won't let us go live because we can't prove the family email thing is legal." → keep: [[11-unknowns-and-risks#UNK-010 Data Protection Officer|UNK-010]] (open) ^c60
- [worry] (solution lead) "the customer sees nothing different, so by next summer they don't know we've done anything at all." → keep: [[11-unknowns-and-risks#UNK-002 Meaning of next summer|UNK-002]] (open) ^c61
- [thought] (solution lead) F1.26: "I meant the May freeze is when they won't touch anything, not that it runs through September." → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-01]] (unknown) ^c62
- [thought] (solution lead) F1.3, F1.28: "I can't move until someone tells me whether "one account" means a login or a full merge, because Rail Product and the CFO are going to want different things and I need the CIO to pick." → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-01]] (unknown), [[11-unknowns-and-risks#Question ledger|R-OPS-03]] (unknown) ^c63
- [thought] (solution lead) F1.11: "Finance probably owns it" (a belief, no source). → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-04]] (unknown) ^c64
- [unknown] (solution lead) F1.11: "I'm not even sure who to ask after the reorganization." → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-04]] (unknown) ^c65
- [unknown] (solution lead) "If I get those answers this week, what else should I nail down before the CIO meeting?" → drop: a question to Claude, answered in session ^c66
- [unknown] (claude) F1.26: Does the May freeze start in May and end on a date, or does it end in May? What is the date, and what does it cover? Ask: Ferry Ops. → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-01]] (unknown) ^c67
- [unknown] (claude) Is a CIO meeting booked, and if so with whom, when and who set it up, given the CIO is unreachable (c11, c46)? Ask: the solution lead. → keep: [[11-unknowns-and-risks#UNK-004 CIO meeting booked|UNK-004]] (open) ^c68
- [idea] (claude) What if the question to the CIO were one line with two answers, "login or full merge", and a default the CIO can accept by saying nothing? → park ^c69
- [idea] (claude) What if the same one-line question went to the CFO and Rail Product first, so the CIO is picking between two stated positions and not starting from nothing? → park ^c70
- [thought] (solution lead) F1.26, F1.11: "Honestly not sure on either yet — need to get Ferry Ops and Finance to pick up." → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-01]] (unknown), [[11-unknowns-and-risks#Question ledger|R-DAT-04]] (unknown) ^c71
- [worry] (solution lead) "the CIO is still the blocker." → keep: [[11-unknowns-and-risks#UNK-003 Who speaks for CIO|UNK-003]] (open) ^c72
- [unknown] (solution lead) "Is that meeting booked? If it's not, we're just wasting time." → keep: [[11-unknowns-and-risks#UNK-004 CIO meeting booked|UNK-004]] (open) ^c73
- [thought] (solution lead) c68: "Draft it, I'll send it this afternoon." → drop: the lead's own to-do, recorded in the UNK ask-by dates ^c74
- [worry] (solution lead) "if the CIO doesn't slot me in this week we're already behind." → keep: [[11-unknowns-and-risks#UNK-004 CIO meeting booked|UNK-004]] (open) ^c75
- [thought] (solution lead) "Ferry Ops and Finance need nudging anyway" → drop: the lead's own to-do, recorded in the UNK ask-by dates ^c76
- [thought] (solution lead) c67, c71: "Yes, both drafts would help — I'll send them this afternoon along with the CIO one." → drop: the lead's own to-do, recorded in the UNK ask-by dates ^c77
- [worry] (solution lead) F1.26: "Ferry Ops is going to dodge the freeze-end question if I'm not careful, and if they say "we'll decide in May" we've already lost half the timeline." → keep: [[11-unknowns-and-risks#UNK-007 May freeze scope and end|UNK-007]] (open) ^c78
- [unknown] (solution lead) "Should I call Ferry Ops before I send the email, or will the written ask land better?" → drop: a question to Claude, answered in session ^c79
- [idea] (claude) What if you called Ferry Ops first, then sent the written ask as a "confirming what we said" note, so their answer is on the record in their own words? → park ^c80
- [idea] (claude) What if the question to Ferry Ops were "what is the latest date you could decide, and who decides it?", so "we'll decide in May" has to name a person and a day? → park ^c81
- [wild] (claude) What if the question were not "when does the freeze end?" but "what could we do inside it?", such as design work or reading data, so the freeze stops being the whole of the constraint? → park ^c82
- [thought] (solution lead) c67: "I'll call Ferry Ops before they pile up with meetings, send all three this afternoon." → drop: the lead's own to-do, recorded in the UNK ask-by dates ^c83
- [thought] (solution lead) F1.11, c50: "Finance should know who owns the database." (a belief, no source) → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-04]] (unknown) ^c84
- [worry] (solution lead) c68: "Honestly not sure the CIO's office will move this week — that's what's actually going to stop us." → keep: [[11-unknowns-and-risks#UNK-004 CIO meeting booked|UNK-004]] (open) ^c85
- [idea] (claude) What if the CIO note named a day, and the CFO were told the same day that the CFO would be asked next if the CIO's office had not replied (c51, c55)? → park ^c86

## Reviews

### 1. After the pre-mortem, 2026-10-06

- **Coverage:** FIN found 5, 1 dropped; DAT found 6; PTN found 6; REG found 7; OPS found 6, 2 dropped
- **Dropped:** [FIN] What is the cost exposure of rework and of the May-to-September freeze, who carries it, and should it be recorded as a risk with an owner? (the quote does not mention what the finding is about); [OPS] Is anything retired, such as SeaBook, FERRYMASTER or the Northway ID login? If so, who still depends on it, and does the customer link need to read from or write to it? (the quote does not mention what the finding is about); [OPS] Which beliefs have no source: the meaning of the mandate, the May freeze, the FERRYMASTER departures and the family-email rule? Which of them would change the plan most if wrong, and who can confirm it? (its quote "”The CIO's unreachable”" has fewer than 4 words, too few to show where it came from)
- **Merged:** [REG] into F1.11: Who is the accountable owner of the ferry customer database now, and who answers regulator or customer data requests?; [OPS] into F1.14: Who are the two FERRYMASTER people, when do they leave, and who will run or support it afterwards? Is any of it written down?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | Do SeaBook, RailCore or Northway ID hold any value for customers (loyalty points, wallet balances, credits, vouchers, deposits)? If so, who owes it, and how would it follow a customer across the link? | "”One account”: a login, a wallet, a loyalty balance, or all three?" in [[2026-10-06-decode-cio-mandate]] |
| F1.2 | FIN | high | Q-FIN-02@INI-001 | Which budget pays for the build, and which team carries the running cost of the link or platform after launch (Ferry, Rail or central IT)? | "”Ferry's got a customer service team in Kestrel Bay, and someone in Finance probably owns the revenue side.”" in [[2026-10-06-decode-cio-mandate]] |
| F1.3 | FIN | high | new | Is the funded scope a link of customer identities or a single rebuilt platform, and what budget and savings case does the CFO attach to each? | "Is the CFO's ”one platform” the same thing as the CIO's ”one account”, or a second goal? Ask: the CFO." in [[2026-10-06-decode-cio-mandate]] |
| F1.4 | FIN | normal | new | Who owns revenue and the customer database in each business after the merger, and who signs off financial commitments? | "Who in Ferry Finance owns the revenue side, and does anyone in Rail Finance own the same thing? Ask: the CFO." in [[2026-10-06-decode-cio-mandate]] |
| F1.5 | FIN | normal | new | Who funds retention or documentation for the FERRYMASTER staff, and what is the cost if they leave before the link is built? | "FERRYMASTER's got two people who understand it, both probably on their way out." in [[2026-10-06-decode-cio-mandate]] |
| F1.6 | DAT | high | Q-DAT-01@INI-001 | Will ferry customer data go to rail staff or systems (or the reverse), and who is the controller for each side after the merger? | "What customer data do SeaBook and RailCore each hold, and what do their customers agreed to? Ask: the owner of each system." in [[2026-10-06-decode-cio-mandate]] |
| F1.7 | DAT | high | Q-DAT-05@INI-001 | What was each dataset collected for, and does linking or merging accounts count as a new purpose that needs a fresh lawful basis or customer consent? | "If we're touching customer data at all, we've got a real problem on the ferry side." in [[2026-10-06-decode-cio-mandate]] |
| F1.8 | DAT | high | new | Who is the Data Protection Officer, have they been asked, and what do they need to see to approve the family-email handling? | "the Data Protection Officer won't let us go live because we can't prove the family email thing is legal." in [[2026-10-06-decode-cio-mandate]] |
| F1.9 | DAT | high | new | How will the link match the right person when emails are shared, and how will consent and preferences follow each person across systems? | "families share one email on ferry but every rail account needs unique." in [[2026-10-06-decode-cio-mandate]] |
| F1.10 | DAT | normal | new | If a copy or a third linking service is used, who holds it, under what basis, and for how long? | "What if FERRYMASTER were never touched, and a nightly copy of customer data were read out of it and the copy became the thing we link to? ^c42" in [[2026-10-06-decode-cio-mandate]] |
| F1.11 | DAT, REG | high | new | Who is the data owner or controller of the ferry customer database now, and who can approve a change in its use? | "Honestly not sure about the port teams or who owns the customer database after the reorganization." in [[2026-10-06-decode-cio-mandate]] |
| F1.12 | PTN | high | Q-PTN-01@INI-001 | Does ownership, operation or payment change for SeaBook, RailCore, FERRYMASTER, the ferry customer DB or Northway ID? Who owns the ferry customer database now? | "Honestly not sure about the port teams or who owns the customer database after the reorganization." in [[2026-10-06-decode-cio-mandate]] |
| F1.13 | PTN | high | new | Are SeaBook, RailCore, Northway ID and FERRYMASTER run under vendor or license contracts? What do those contracts say on change of control, assignment, notice, and use of data for a new purpose? | "Is Northway ID the rail login in RailCore or a separate identity service, and who owns it? Ask: Rail Product." in [[2026-10-06-decode-cio-mandate]] |
| F1.14 | PTN, OPS | high | new | What is the employment or contract status of the two FERRYMASTER people? Is there any support contract or notice period that governs their leaving or handover? | "FERRYMASTER's got two people who understand it, both probably on their way out." in [[2026-10-06-decode-cio-mandate]] |
| F1.15 | PTN | normal | new | Where does the Ferry Ops freeze come from (contract, operations or policy)? Who can lift it? Which date is next summer? | "Ferry Ops won't touch anything before May" in [[2026-10-06-decode-cio-mandate]] |
| F1.16 | PTN | high | new | What do the ferry and rail customer terms and consents allow? Can data cross between the two entities, and who is the contracting party on each side? | "What customer data do SeaBook and RailCore each hold, and what do their customers agreed to? Ask: the owner of each system." in [[2026-10-06-decode-cio-mandate]] |
| F1.17 | PTN | normal | new | Who has authority to approve changes to ownership, operation, payment or agreements while the CIO is unreachable? | "If the CIO stays unreachable, who can decide in their place, and who can say that for them? Ask: the CFO." in [[2026-10-06-decode-cio-mandate]] |
| F1.18 | REG | normal | Q-REG-01@INI-001 | Will the customer buy or be promised anything that spans ferry and rail, such as a single ticket, a joint booking or a bundle, or is this only an account link? | "”One journey”: one ticket, one booking, or one trip the customer plans and sees as a whole?" in [[2026-10-06-decode-cio-mandate]] |
| F1.19 | REG | high | Q-REG-02@INI-001 | What is regulated or licensed here, for example customer personal data, ferry or rail operating licenses, or payment data? Who is the regulator or approver for each, and has the Data Protection Officer been engaged? | "the Data Protection Officer won't let us go live because we can't prove the family email thing is legal." in [[2026-10-06-decode-cio-mandate]] |
| F1.20 | REG | normal | Q-REG-05@INI-001 | If a combined ferry and rail journey fails on one leg, who is liable to the customer, and under which terms? Are the ferry and rail terms of carriage different? | "What this initiative cannot change." in [[02-constraints]] |
| F1.21 | REG | high | new | What consent or lawful basis covers each system's customer data, and does it allow linking or merging across the two businesses? | "What customer data do SeaBook and RailCore each hold, and what do their customers agreed to?" in [[2026-10-06-decode-cio-mandate]] |
| F1.22 | REG | high | new | Are ferry and rail now one legal entity or separate ones, and which one is the controller for each customer data set? | "the two businesses have pretty much been left to operate separately since the merger three months ago." in [[2026-10-06-decode-cio-mandate]] |
| F1.23 | REG | normal | new | Does the Data Protection Officer need to review each linking option before one is chosen? | "What if the rail side accepted a shared email for linked ferry customers and kept its unique rule for everyone else?" in [[2026-10-06-decode-cio-mandate]] |
| F1.24 | OPS | high | Q-OPS-04@INI-001 | Which systems, identity schemes and teams do the same job (SeaBook, the ferry customer DB, FERRYMASTER, RailCore, Northway ID)? How do they relate, and which is the base? | "SeaBook and RailCore are on completely separate stacks with completely separate customer data." in [[2026-10-06-decode-cio-mandate]] |
| F1.25 | OPS | high | Q-OPS-06@INI-001 | Who speaks for the Kestrel Bay team, the port teams, Ferry Finance and Rail Finance, and the ferry customer database owner? When will each be brought in? | "Honestly not sure about the port teams or who owns the customer database after the reorganization." in [[2026-10-06-decode-cio-mandate]] |
| F1.26 | OPS | high | new | Is the Ferry Ops freeze before May or from May through September? What does it cover? How does it fit the 'next summer' date? | "May through September is five months we can't touch anything, and that's half our timeline." in [[2026-10-06-decode-cio-mandate]] |
| F1.27 | OPS | high | new | How will a customer's identity and consent follow them across ferry and rail when the email rules conflict? Who owns the Data Protection Officer sign-off? | "families share one email on ferry but every rail account needs unique." in [[2026-10-06-decode-cio-mandate]] |
| F1.28 | OPS | high | new | Are the CIO, CFO and Rail Product asking for one goal or three? Who gains and who loses under each reading, and who decides between them? | "CFO wants one platform" in [[2026-10-06-decode-cio-mandate]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| G1 | - | inkling | [[2026-10-06-decode-cio-mandate#^c01]] |
| UNK-001 | - | open | [[2026-10-06-decode-cio-mandate#^c02]] |
| UNK-002 | - | open | [[2026-10-06-decode-cio-mandate#^c07]] |
| UNK-003 | - | open | [[2026-10-06-decode-cio-mandate#^c08]] |
| UNK-004 | - | open | [[2026-10-06-decode-cio-mandate#^c68]] |
| UNK-005 | - | open | [[2026-10-06-decode-cio-mandate#^c12]] |
| UNK-006 | - | open | [[2026-10-06-decode-cio-mandate#^c13]] |
| UNK-007 | - | open | [[2026-10-06-decode-cio-mandate#^c14]] |
| UNK-008 | - | open | [[2026-10-06-decode-cio-mandate#^c20]] |
| UNK-009 | - | open | [[2026-10-06-decode-cio-mandate#^c27]] |
| UNK-010 | - | open | [[2026-10-06-decode-cio-mandate#^c30]] |
| UNK-011 | - | open | [[2026-10-06-decode-cio-mandate#^c15]] |
| UNK-012 | - | open | [[2026-10-06-decode-cio-mandate#^c32]] |
| UNK-013 | - | open | [[2026-10-06-decode-cio-mandate#^c33]] |
| UNK-014 | - | open | [[2026-10-06-decode-cio-mandate#^c29]] |
| UNK-015 | - | open | [[2026-10-06-decode-cio-mandate#^c36]] |
| UNK-016 | - | open | [[2026-10-06-decode-cio-mandate#^c44]] |
| UNK-017 | - | open | [[2026-10-06-decode-cio-mandate#^c43]] |
| UNK-018 | - | open | [[2026-10-06-decode-cio-mandate#^c48]] |
| UNK-019 | - | open | [[2026-10-06-decode-cio-mandate#^c49]] |
| UNK-020 | - | open | [[2026-10-06-decode-cio-mandate#^c21]] |
| R-FIN-01 | - | unknown | [[2026-10-06-decode-cio-mandate#^c63]] |
| R-FIN-02 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-FIN-03 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-DAT-01 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-DAT-02 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-DAT-03 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-DAT-04 | - | unknown | [[2026-10-06-decode-cio-mandate#^c64]] |
| R-PTN-01 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-PTN-02 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-PTN-03 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-PTN-04 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-PTN-05 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-REG-01 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-REG-02 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-REG-03 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-OPS-01 | - | unknown | [[2026-10-06-decode-cio-mandate#^c67]] |
| R-OPS-02 | - | open | [[2026-10-06-decode-cio-mandate#1. After the pre-mortem, 2026-10-06]] |
| R-OPS-03 | - | unknown | [[2026-10-06-decode-cio-mandate#^c63]] |
