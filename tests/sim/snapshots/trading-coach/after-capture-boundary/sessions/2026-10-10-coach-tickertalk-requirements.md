---
id: 2026-10-10-coach-tickertalk-requirements
type: session
title: "Requirements: coach tickertalk requirements"
date: 2026-10-10
modes: [requirements, releases, boundary]
status: open
summary: In progress.
---

# 2026-10-10 Requirements: coach tickertalk requirements

## Captures

- "Yes to CAP-005 separate, and the session topic works." — @sim-lead, to the proposal of a fifth capability, Opt in to the coach, provided by TickerTalk → keep: [[CAP-005-opt-in-to-the-coach#Opt in to the coach|CAP-005]] (assumption) ^c01
- "Yes, all of it works. Any order, one at a time, no gating—that's the right call for release one." — @sim-lead, to CAP-001.FR1 and its two criteria, with Claude's recommended answer of any order and no gating (claude, from @sim-lead) → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR1 Learn one stock at a time|CAP-001.FR1]] (assumption) ^c02
- "Finished only, keeps it simple. Mid-lesson resume sounds like scope creep when we're racing March anyway." — @sim-lead, to CAP-001.FR2, taking Claude's recommended answer of finished lessons only (claude, from @sim-lead) → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR2 Keep the reader's place|CAP-001.FR2]] (assumption) ^c03
- "(a) makes sense—don't show stale data with a label that says fresh. Keeps us honest and the lesson still teaches without a number. Ship it." — @sim-lead, to CAP-001.FR3, taking Claude's recommended answer of "price unavailable" and no stale price (claude, from @sim-lead) → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR3 Label delayed prices|CAP-001.FR3]] (assumption) ^c04
- "Yes to requirement 4. K44 clears the board demo—it's inside Kestrel and exempt. No unknown to track." — @sim-lead, to CAP-001.FR4 worded for readers only, and declining a new unknown for the demo; the exemption is already recorded in UNK-033, and its written confirmation is already UNK-062 → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR4 Show only approved wording|CAP-001.FR4]] (assumption) ^c05
- "Yes, that wording works. Facts and concepts, no judgment on any stock. Counsel already cleared that we explain trades, never suggest." — @sim-lead, to CAP-001.FR5 with Claude's recommended wording (claude, from @sim-lead); the claim that counsel cleared it is the lead's own and not yet in the vault, whose compliance ruling is UNK-003 → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR5 Explain trades, suggest none|CAP-001.FR5]] (assumption) ^c06
- "October 8 counsel ruling—education vs. recommendations. That's the distinction. Yes on FR6's third criterion." — @sim-lead, naming Outside Counsel's reply of 8 October ([[sources#SRC-08]]) as the basis for CAP-001.FR5, and agreeing to CAP-001.FR6 with Claude's third criterion (claude, from @sim-lead) → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR6 Tell the reader when unavailable|CAP-001.FR6]] (assumption) ^c07
- "Yes, that's clean. Finished counts, can't start new, can't continue old. Makes sense—we're not going to let someone graduate on half a lesson for a stock we dropped." — @sim-lead, to CAP-001.FR7 with Claude's third criterion (claude, from @sim-lead) → keep: [[CAP-001-teach-a-stock-lesson#CAP-001.FR7 Keep progress on dropped stocks|CAP-001.FR7]] (assumption) ^c08
- "Yes to both. Mark FR4 unconfirmed until UNK-062 writes it. FR2's retention rule to privacy lead, Oct 30 ask-by—without it in writing, we're stuck on reader data." — @sim-lead, taking review findings F1.18 and F1.13: FR4 marked unconfirmed until UNK-062, and a new unknown on FR2's retention rule asked of @privacy-lead by 2026-10-30 → keep: [[11-unknowns-and-risks#UNK-076 How long Coach keeps a reader's finished-lesson record|UNK-076]] (assumption) ^c09

- "Yes to all five. The list and the gating are already locked by counsel, so nothing changes here." — @sim-lead, to the FR1 allocation sheet, Coach's share through CON-001; the claim that counsel locked the list and the gating is the lead's own and not yet in the vault → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR1@APP-coach]] (assumption) ^c10
- "Yes to all five." — @sim-lead, to the FR1 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR1@APP-tickertalk]] (assumption) ^c11

- "Yes to the shares." — @sim-lead, to the FR2 allocation sheet, Coach's share through CON-001 and CON-005 → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR2@APP-coach]] (assumption) ^c12
- "Yes to the unknown, and yes, @coach-lead is the right one—they own the Coach service. Honestly not sure what the exact signal is, but if it blocks FR2 then we need to ask." — @sim-lead, to the unknown on how Coach learns a lesson is finished, with @coach-lead as who would know → keep: [[11-unknowns-and-risks#UNK-077 How Coach learns a lesson is finished|UNK-077]] (assumption) ^c13
- "Yes to the shares." — @sim-lead, to the FR2 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR2@APP-tickertalk]] (assumption) ^c14

- "Yes to all three. K23's in writing on display in lessons, so we're covered." — @sim-lead, to the FR3 allocation sheet, Coach's share through CON-001 and CON-004; the Quoteline reply on display use is already [[sources#SRC-10]], and the lead's reference to K23 is not a row in the vault → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR3@APP-coach]] (assumption) ^c15
- "Yes to all three." — @sim-lead, to the FR3 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR3@APP-tickertalk]] (assumption) ^c16

- "Yes to both. FR4 stays conditional on UNK-062 like we said; just mark it and move to FR5?" — @sim-lead, to the FR4 allocation sheet, Coach's share through CON-001, with both rows marked conditional on UNK-062 → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR4@APP-coach]] (assumption) ^c17
- "Yes to both." — @sim-lead, to the FR4 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR4@APP-tickertalk]] (assumption) ^c18
- "Partnerships manager has the Brightwater channel—they'd know how a lesson gets to Brightwater and back." — @sim-lead, to the unknown on how a lesson reaches Brightwater and how Coach learns it passed, with @partnerships-manager as who would know → keep: [[11-unknowns-and-risks#UNK-078 How a lesson gets to Brightwater and how Coach learns it passed|UNK-078]] (assumption) ^c19

- "Yes to all three. UNK-003 is the blocker to close before launch, but lessons and education are counsel-cleared." — @sim-lead, to the FR5 allocation sheet, Coach's share through CON-001; the claim that counsel cleared lessons is the lead's own, and the compliance ruling in the vault is UNK-003, still open → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR5@APP-coach]] (assumption) ^c20
- "Yes to all three." — @sim-lead, to the FR5 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR5@APP-tickertalk]] (assumption) ^c21

- "Yes to all three. The 3-second assumption is solid. Leave the wording for the Grill on the runtime page, yeah." — @sim-lead, to the FR6 allocation sheet, Coach's share through CON-001, leaving the "isn't available" versus "is not available" wording to a Grill on the runtime page, and the third criterion's dependence on UNK-077 noted there → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR6@APP-coach]] (assumption) ^c22
- "Yes to all three." — @sim-lead, to the FR6 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR6@APP-tickertalk]] (assumption) ^c23

- "Yes to all three. Stock list is CAP-004's problem—keeps it clean." — @sim-lead, to the FR7 allocation sheet, Coach's share through CON-001, leaving who drops a stock and who tells readers to CAP-004 → keep: [[coach-building-blocks#Requirements allocated|CAP-001.FR7@APP-coach]] (assumption) ^c24
- "Yes to all three." — @sim-lead, to the FR7 allocation sheet, TickerTalk's share through CON-001 → keep: [[tickertalk-building-blocks#Requirements allocated|CAP-001.FR7@APP-tickertalk]] (assumption) ^c25

- "January 15, 2027 to the board and CEO—but that's inside Kestrel, so not outside the team yet. Release one ships to actual users in March." — @sim-lead, giving the first release's date and audience, and naming the March launch as release one; Claude proposed keeping the demo as its own earlier release called January board demo ^c26
- "Yes. Just need Coach to confirm the full demo—lessons and a live paper order flow—fits in their January timeline." — @sim-lead, agreeing to the January board demo release at 2027-01-15, with the demo ahead of Release one: March launch, and naming a dependency on Coach confirming the full demo fits January (for the step 4 unknown) ^c27

- "Yes, both checks. That's foundational—you can't have the lesson without it." — @sim-lead, placing CAP-001.FR1 on the January board demo with both criteria (claude, from @sim-lead) → keep: [[04b-releases#January board demo|January board demo]] (assumption) ^c28

- "Can wait. Demo's one sitting, so persistence doesn't matter." — @sim-lead, to CAP-001.FR2 on the January board demo, with Claude's recommended answer that it can wait for release one (claude, from @sim-lead); it goes on Release one: March launch once that release has a date ^c29

- "Must have AC1 and AC2—the label's non-negotiable for compliance when we show prices in the trade screen. AC3 is edge case, leave it for March." — @sim-lead, placing CAP-001.FR3 on the January board demo with AC1 and AC2, and AC3 for release one, taking Claude's recommended split (claude, from @sim-lead); the lead's compliance reason is theirs and not a vault source → keep: [[04b-releases#January board demo|January board demo]] (assumption) ^c30

- "Demo's inside Kestrel—Brightwater exempts it from the review clock. FR4 can wait for release one." — @sim-lead, to CAP-001.FR4 on the January board demo, taking Claude's recommended answer that it can wait for release one (claude, from @sim-lead); the exemption is the lead's statement and stays unconfirmed in [[11-unknowns-and-risks#UNK-062 Written confirmation of the board-demo exemption|UNK-062]]; it goes on Release one: March launch once that release has a date ^c31

- "Yes, both checks. AC1's the real teeth—can't hint at any stock to the board. AC2's academic since options come in March, not the demo." — @sim-lead, placing CAP-001.FR5 on the January board demo with both criteria, taking Claude's recommended answer (claude, from @sim-lead); the lead's remark that options come in March is theirs, and the vault says release one teaches no options (CAP-001.FR5 AC2, [[01-goals]]) → keep: [[04b-releases#January board demo|January board demo]] (assumption) ^c32

- "Yes, AC1 only. Demo runs once; we don't need the whole persistence story right there." — @sim-lead, placing CAP-001.FR6 on the January board demo with AC1, and AC2 and AC3 for release one, taking Claude's recommended split (claude, from @sim-lead) → keep: [[04b-releases#January board demo|January board demo]] (assumption) ^c33

- "Can wait. Fixed list for the demo, so no dropped-stock edge cases to handle." — @sim-lead, to CAP-001.FR7 on the January board demo, taking Claude's recommended answer that it can wait for release one (claude, from @sim-lead); it goes on Release one: March launch once that release has a date ^c34

- "TickerTalk is Reader accounts. Coach spans Learning (lessons) and Trading (paper trades), not just one." — @sim-lead, naming the domains → keep: [[tickertalk-building-blocks|APP-tickertalk]] domain Reader accounts; [[CAP-001-teach-a-stock-lesson|CAP-001]] domain Learning; [[CAP-002-paper-trade-a-stock|CAP-002]] domain Trading (assumption) ^c35
- "FLO-001: yes, yes, yes." — @sim-lead, to FLO-001 steps 3 (TickerTalk → Coach), 4 (no pair) and 5 (Coach → TickerTalk) → keep: [[FLO-001-reader-starts-learning#Steps|FLO-001]] (decided, unchanged) ^c36
- "FLO-002: yes through step 4. Step 5, yes—Quoteline sends to Coach, our licence is display-use only." — @sim-lead, to FLO-002 steps 1 to 5 → keep: [[FLO-002-reader-practises-a-trade#Steps|FLO-002]] (assumption) ^c37
- "honestly not sure how Coach learns a lesson is finished. TickerTalk → Coach makes sense—flag it as unknown and move on." — @sim-lead, to FLO-003 step 1; the open question is already UNK-077, whose Blocks now also names FLO-003; step 3 (Coach → TickerTalk) was not answered, so it is left unpaired pending a yes → keep: [[11-unknowns-and-risks#UNK-077 How Coach learns a lesson is finished|UNK-077]] (open) ^c38

- "Coach's domain is Learning, per how we carve up the business. CAP-003 and CAP-004 go Learning, CAP-005 goes Reader accounts." — @sim-lead, naming Coach's domain and three capability domains → keep: [[coach-building-blocks|APP-coach]] domain Learning; CAP-003, CAP-004 Learning; [[CAP-005-opt-in-to-the-coach|CAP-005]] Reader accounts (assumption) ^c39
- "Yes to FLO-003 step 3, Coach sends the ready mark." — @sim-lead, to FLO-003 step 3, Coach → TickerTalk → keep: [[FLO-003-reader-passes-the-ready-track#Steps|FLO-003]] (assumption) ^c40

## Reviews

### 1. after the requirements are written (CAP-001), 2026-10-10

- **Coverage:** FIN found 10, 2 dropped; DAT found 7, 2 dropped; PTN found 1; REG found 10, 1 dropped; OPS found 7, 1 dropped
- **Dropped:** [FIN] its quote was not in the written text of 03-context-and-scope (what happens to a balance at closure or withdrawal); [FIN] the quote did not mention what the finding was about (who carries liability if a reader loses money); [DAT] the quote did not mention what the finding was about (training Signal on reader data); [DAT] the quote did not mention what the finding was about (whether the January demo uses real reader data); [REG] it named R-REG-09, which the vault does not owe (legal ruling on the curated list); [OPS] it named R-OPS-25, which the vault does not owe (who submits lessons to Brightwater)
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-04@SV-01 | If a reader moves from paper trading to a real Brightwater account, does any paper balance or result carry over or convert, or is the paper record simply kept and never turned into money? | "expects that record to stay in Coach if a reader later opens a real account, which is an assumption" in [[03-context-and-scope]] |
| F1.2 | FIN | normal | Q-FIN-06@SV-01 | Is there any conversion rate in release one? If not, record that none applies. If one is ever needed, who sets it and who approves it? | "paper balances are not money" in [[03-context-and-scope]] |
| F1.3 | FIN | high | R-FIN-12 | Where is counsel's written clearance of the lesson approach and the 50-stock list, and who owns and pays for the list? | "Counsel already cleared that we explain trades, never suggest." in [[2026-10-10-coach-tickertalk-requirements]] |
| F1.4 | FIN | normal | R-FIN-15 | Does Brightwater's content review carry any fee, and who pays for the cost and delay of re-review when a lesson is rejected? | "Brightwater reviews every lesson shown to its customers as written" in [[CAP-001-teach-a-stock-lesson]] |
| F1.5 | FIN | high | R-FIN-16 | Which price source do lessons use, Quoteline or Brightwater? Is it licensed for display to non-customers, and does it add any fee beyond the Quoteline licence? | "Any price a reader sees in a lesson is labelled as delayed by 15 minutes." in [[CAP-001-teach-a-stock-lesson]] |
| F1.6 | FIN | high | R-FIN-25 | What is Fieldnote Learning paid, out of which budget, and what would exit or replacing the writer cost? | "either side may end it on 30 days' notice" in [[03-context-and-scope]] |
| F1.7 | FIN | normal | R-FIN-27 | Which team and budget carry Coach's running cost after launch, and does the 180,000 dollars include staff time, the platform engineer and Quoteline fees? | "the CFO puts Coach's running cost in year one at about 180,000 dollars, inside the 2.5 million" in [[03-context-and-scope]] |
| F1.8 | FIN | high | R-FIN-31 | On what dates does the budget's first year start and end, and does it cover the period to March 2028? | "the product lead says it is for the coach's first year" in [[03-context-and-scope]] |
| F1.9 | FIN | normal | R-FIN-21 | Who pays to build the TickerTalk side of opt-in and the reader ID to Coach, and out of which budget? | "which holds the consent, and it is what lets [[coach-building-blocks\|Coach]] hold anything about the reader" in [[CAP-005-opt-in-to-the-coach]] |
| F1.10 | FIN | normal | R-FIN-18 | What reader volume and release scope does the 180,000 dollar estimate assume, and does the cost change if every opted-in reader can use the coach? | "rollout is an opt-in beta for 2,000 watchlist readers in March, then everyone who opts in from April" in [[03-context-and-scope]] |
| F1.11 | DAT | normal | R-DAT-12 | What exactly does a reader opt in to, where is that opt-in stored, and does it cover the data Coach holds and the sandbox use? | "it is what lets [[coach-building-blocks\|Coach]] hold anything about the reader" in [[CAP-005-opt-in-to-the-coach]] |
| F1.12 | DAT | high | R-DAT-15 | When a reader withdraws the opt-in, is Coach's data on them deleted, frozen or kept, and what does the flow do on the next request? | "can withdraw that choice" in [[CAP-005-opt-in-to-the-coach]] |
| F1.13 | DAT | high | new | On what lawful basis and for how long does Coach keep each reader's finished-lesson record, including after withdrawal of the opt-in and for dropped stocks? | "The business remembers which lessons a reader has finished, so the reader can pick up where they left off." in [[CAP-001-teach-a-stock-lesson]] |
| F1.14 | DAT | normal | Q-DAT-03@CON-001 | Does reader data cross CON-001, and were Coach and its uses named when TickerTalk collected the data? | "in, the reader's identity and the lesson they are on" in [[coach-building-blocks]] |
| F1.15 | DAT | normal | Q-DAT-03@CON-002 | Does reader data cross CON-002, and were its consumers named when the data was collected? | "in, a stock pick and a paper order" in [[coach-building-blocks]] |
| F1.16 | DAT | normal | Q-DAT-03@CON-003 | Does reader data cross to Brightwater at CON-003, and were Brightwater and its use named when the data was collected? | "in, a paper account request and paper orders; out, the account ID and order status" in [[coach-building-blocks]] |
| F1.17 | DAT | high | R-DAT-18 | Does clause 9 of the Quoteline licence allow Coach to show quotes inside generated lessons, and who reads the full text before this requirement is relied on? | "Any price a reader sees in a lesson is labelled as delayed by 15 minutes." in [[CAP-001-teach-a-stock-lesson]] |
| F1.18 | PTN | high | new | Will Brightwater or the signed agreement confirm in writing that an inside-Kestrel board demo is exempt from the ten-business-day review? Until then, should FR4 say the exemption is unconfirmed? | "A demo shown only inside Kestrel is outside this rule" in [[CAP-001-teach-a-stock-lesson]] |
| F1.19 | REG | normal | Q-REG-01@INI-001 | Are lessons sold or promised jointly with Brightwater, and do paper-only readers count as Brightwater customers for the content review? | "Brightwater reviews every lesson shown to its customers as written" in [[CAP-001-teach-a-stock-lesson]] |
| F1.20 | REG | normal | Q-REG-05@INI-001 | If an approved lesson misleads a reader or the coach part fails, who is liable to the reader: TickerTalk, Coach's owner or Brightwater? | "so a reader sees exactly the wording Brightwater approved" in [[CAP-001-teach-a-stock-lesson]] |
| F1.21 | REG | high | R-REG-17 | Is counsel's statement that lessons are education held in writing, and who does the marketing and compliance review of lesson wording and shown results? | "Counsel already cleared that we explain trades, never suggest." in [[2026-10-10-coach-tickertalk-requirements]] |
| F1.22 | REG | high | R-REG-18 | Will the partnerships manager confirm in writing, before January, that an internal board demo is exempt from Brightwater's review? Who owns the review and counsel check for the demo content? | "K44 clears the board demo—it's inside Kestrel and exempt. No unknown to track." in [[2026-10-10-coach-tickertalk-requirements]] |
| F1.23 | REG | high | R-REG-28 | Can the lessons clear Brightwater's ten-day review, including a restart after a rejection, before the March beta? Does the review apply to paper-only readers and to every lesson update? | "no lesson reaches a reader before it has passed" in [[CAP-001-teach-a-stock-lesson]] |
| F1.24 | REG | high | R-REG-24 | Who enforces and checks that lessons never become customer-specific trade ideas, given Brightwater has declined the recommender role? | "they never suggest a trade or judge a stock" in [[CAP-001-teach-a-stock-lesson]] |
| F1.25 | REG | normal | R-REG-32 | Does the Quoteline licence cover the Coach service serving delayed prices in lessons, and has Quoteline said so? | "Any price a reader sees in a lesson is labelled as delayed by 15 minutes." in [[CAP-001-teach-a-stock-lesson]] |
| F1.26 | REG | normal | R-REG-14 | Who in legal or compliance approves what 'ready' means and how it is worded, and could it be read as advice or suitability? | "still count toward ready" in [[CAP-001-teach-a-stock-lesson]] |
| F1.27 | REG | high | R-REG-29 | What must the opt-in and its audit trail satisfy, what happens to Coach's records on withdrawal, and has the privacy lead confirmed the lawful basis for Coach holding the reader ID? | "it is what lets [[coach-building-blocks\|Coach]] hold anything about the reader" in [[CAP-005-opt-in-to-the-coach]] |
| F1.28 | REG | normal | R-REG-21 | Which regulatory answers must be in hand before the first release is switched on, and who owns each? | "sees the coach only while the first release is switched on" in [[CAP-005-opt-in-to-the-coach]] |
| F1.29 | OPS | normal | Q-OPS-03@CAP-003 | Which named team will own and run the ready track (and who defines and accepts 'ready') once the teams form, and can that be settled before the January demo rather than 2026-11-13? | "What ”ready” means is not yet defined." in [[CAP-003-pass-the-ready-track]] |
| F1.30 | OPS | normal | Q-OPS-04@INI-001 | Which system is the record for a reader's paper trades when Coach and the Brightwater sandbox differ, and which team reconciles them? | "The Coach lead says Coach keeps each reader's paper balance and trades while the Brightwater sandbox only fills the paper orders" in [[03-context-and-scope]] |
| F1.31 | OPS | normal | Q-OPS-05@INI-001 | Does the coach retire or replace anything, such as an existing tool, a spreadsheet or a manual process? If so, who still depends on it? | "a new service for the lessons, the stock list and the paper record" in [[03-context-and-scope]] |
| F1.32 | OPS | normal | R-OPS-28 | Who watches the coach, who responds when readers see 'coach isn't available' out of hours, and who covers the gap before the rota starts on 1 March? | "their earlier progress is intact when the coach is back." in [[CAP-001-teach-a-stock-lesson]] |
| F1.33 | OPS | normal | new | Who decides when a stock is dropped from the list, and who tells readers and Fieldnote when that happens? | "When a stock leaves the list, the lessons a reader already finished on it still count toward ready" in [[CAP-001-teach-a-stock-lesson]] |
| F1.34 | OPS | high | new | Which team builds and runs opt-in and withdrawal, who counts opt-ins for the 40,000 target, and what happens to a reader's Coach data when they withdraw? | "can withdraw that choice, and sees the coach only while the first release is switched on" in [[CAP-005-opt-in-to-the-coach]] |
| F1.35 | OPS | normal | R-OPS-16 | Who operates the release switch, and who can roll the beta back? | "sees the coach only while the first release is switched on" in [[CAP-005-opt-in-to-the-coach]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| CAP-005 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c01]] |
| CAP-001.FR1 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c02]] |
| CAP-001.FR2 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c03]] |
| CAP-001.FR3 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c04]] |
| CAP-001.FR4 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c05]] |
| CAP-001.FR5 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c06]] |
| CAP-001.FR6 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c07]] |
| CAP-001.FR7 | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c08]] |
| UNK-076 | none | open | [[2026-10-10-coach-tickertalk-requirements#^c09]] |
| CAP-001.FR4 | assumption | assumption (exemption marked unconfirmed) | [[2026-10-10-coach-tickertalk-requirements#^c09]] |
| CAP-001.FR1@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c10]] |
| CAP-001.FR1@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c11]] |
| CAP-001.FR2@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c12]] |
| UNK-077 | none | open | [[2026-10-10-coach-tickertalk-requirements#^c13]] |
| CAP-001.FR2@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c14]] |
| CAP-001.FR3@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c15]] |
| CAP-001.FR3@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c16]] |
| CAP-001.FR4@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c17]] |
| CAP-001.FR4@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c18]] |
| UNK-078 | none | open | [[2026-10-10-coach-tickertalk-requirements#^c19]] |
| CAP-001.FR5@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c20]] |
| CAP-001.FR5@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c21]] |
| CAP-001.FR6@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c22]] |
| CAP-001.FR6@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c23]] |
| CAP-001.FR7@APP-coach | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c24]] |
| CAP-001.FR7@APP-tickertalk | none | assumption | [[2026-10-10-coach-tickertalk-requirements#^c25]] |
| releases | - | assumption | [[2026-10-10-coach-tickertalk-requirements#^c28]] |
