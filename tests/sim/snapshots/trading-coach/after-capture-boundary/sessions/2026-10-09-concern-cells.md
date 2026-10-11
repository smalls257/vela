---
id: 2026-10-09-concern-cells
type: session
title: "Grill: concern cells"
date: 2026-10-09
modes: [grill]
status: closed
summary: "Four concern cells decided (Coach data, operations, ownership; TickerTalk data), seven marked unchanged, UNK-022 resolved, UNK-067 and UNK-068 opened."
---

# 2026-10-09 Grill: concern cells

## Captures

- [thought] (Jordan Reyes, product lead) "I own the stock list and lessons, CFO has the 2.5 million" UNK-022: the product lead owns the stock list and the lessons, and the CFO holds the 2.5 million dollar budget (SRC-24; the budget is already recorded from SRC-16 and SRC-19). → keep: [[11-unknowns-and-risks#UNK-022 Owner and budget for the stock list|UNK-022]] (resolved) ^c01
- [thought] (Jordan Reyes, product lead) "Sarah Chen ruled October 2nd—no conflict, means no live trading until March 2028." UNK-003: the person who ruled is Sarah Chen, on 2 October, and "live orders until March" means no live trading until March 2028, so it agrees with UNK-004 (SRC-25). Whether the ruling is in writing is not stated. → keep: [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|UNK-003]] (open) ^c02
- [thought] (Jordan Reyes, product lead) "Coach data: encrypts paper records" The product lead's statement of what the initiative does for Coach under Data: Coach encrypts the paper records it holds. → keep: [[concern-data#Per app|Coach data]] (decided) ^c03
- [thought] (Jordan Reyes, product lead) "Coach ops: Kestrel AWS, team-owned" The product lead's statement for Coach under Operations: Coach runs on Kestrel's AWS account and the Coach team owns running it. → keep: [[concern-operations#Per app|Coach operations]] (decided) ^c04
- [thought] (Jordan Reyes, product lead) "Coach ownership: @coach-lead owns Coach, I own lessons" The product lead's statement for Coach under Ownership: @coach-lead owns Coach, and the product lead owns the lessons. → keep: [[concern-ownership#Per app|Coach ownership]] (decided) ^c05
- [thought] (Jordan Reyes, product lead) "TickerTalk data: sends opaque IDs" The product lead's statement for TickerTalk under Data: TickerTalk sends Coach opaque reader IDs. → keep: [[concern-data#Per app|TickerTalk data]] (decided) ^c06
- [decision] (Jordan Reyes, product lead) "Mark other seven unchanged and move." Seven cells are `unchanged`: Coach observability, security and testing; TickerTalk ownership and testing; and rollout for both apps. Written on the product lead's yes. → keep: [[concern-security#Per app|Coach and TickerTalk concern cells]] (unchanged) ^c07
- [decision] (Jordan Reyes, product lead) "All four cells yes." The agenda of four concern cells is confirmed (GATE-3): Coach data, Coach operations, Coach ownership and TickerTalk data. → drop: agenda confirmation, recorded under Agenda ^c08
- [thought] (Jordan Reyes, product lead) "honestly not sure we sort that until Sarah Chen's written ruling is locked in. That's the gate. Once I have it in writing, I can assign them." No owner is named for any of the four cells (GATE-5), and the product lead ties naming them to the written ruling (UNK-003). → drop: superseded by c10, which names the owners ^c09
- [decision] (Jordan Reyes, product lead) "Coach cells to @coach-lead, I own the lessons, TickerTalk data to @mobile-lead. Decide on their behalf." Owners: @coach-lead for Coach data, operations and ownership (the product lead owns the lessons); @mobile-lead for TickerTalk data. The product lead overrides GATE-5 and decides on their behalf. → drop: owners and the GATE-5 override are recorded as Override and Decided by bullets on the cell pages ^c10
- [thought] (Jordan Reyes, product lead) "Yeah, withdrawal wins—delete on day 30. On what we rejected, sandbox as the single record would've locked us to Brightwater's timeline on the live handoff, so Coach holds it encrypted." A withdrawn reader's paper record is deleted on day 30 even after a real account opens; the rejected option is the sandbox as the single record. → keep: [[concern-data#Per app|Coach data]] (decided) ^c11
- [decision] (Jordan Reyes, product lead) "Yes, that's right. Let's move to the next one." The read-back of Coach data is confirmed. → keep: [[concern-data#Per app|Coach data]] (decided) ^c12
- [unknown] (Jordan Reyes, product lead) "Write for March and open January. The demo risk is real—I'll get the platform engineer committed for that week, ask-by end of month." UNK-067 written: owner @sim-lead, ask-by 2026-10-31, blocking nothing yet. The Coach × Operations cell is written for March onward. → keep: [[11-unknowns-and-risks#UNK-067 Who covers Coach on demo week|UNK-067]] (open) ^c13
- [thought] (Jordan Reyes, product lead) "Yes, reason's right. News app stays a news app, Coach can move to live orders later without dragging TickerTalk along." The rejected option for Coach operations, the coach inside TickerTalk, is rejected so the news app stays a news app and Coach can move to live orders later without TickerTalk. → keep: [[concern-operations#Per app|Coach operations]] (decided) ^c14
- [decision] (Jordan Reyes, product lead) "The wording's good—commit it." The read-back of Coach operations is confirmed. → keep: [[concern-operations#Per app|Coach operations]] (decided) ^c15
- [unknown] (Jordan Reyes, product lead) "Yeah, that's right—Fieldnote rewrites, I own the Brightwater conversation. Clock restart in mid-February is the risk: if the rewrite bounces again, we hit escalation and miss the 15th. Honestly not sure if partnerships owns that escalation talk or if it lands on me." Fieldnote rewrites a rejected lesson and the product lead answers Brightwater; who owns the escalation after two rounds is not known. UNK-068 written (owner @partnerships-manager, ask-by 2026-10-30, blocking nothing yet), agreed with "Yes, all four work." → keep: [[11-unknowns-and-risks#UNK-068 Who owns escalation after two rejected rounds|UNK-068]] (open) ^c16
- [thought] (Jordan Reyes, product lead) "Right, that's the reason—@coach-lead runs the team and the service, that's where the ownership lives." The rejected option for Coach ownership, the product lead owning Coach too, is rejected because @coach-lead runs the team and the service. → keep: [[concern-ownership#Per app|Coach ownership]] (decided) ^c17
- [decision] (Jordan Reyes, product lead) "Rest of the wording's good, commit it." The read-back of Coach ownership is confirmed. → keep: [[concern-ownership#Per app|Coach ownership]] (decided) ^c18
- [thought] (Jordan Reyes, product lead) "Yes, only the ID for opted-ins. Watchlist and history stay with TickerTalk, nothing else crosses." TickerTalk sends Coach only the opaque reader ID, and only for opted-in readers; the watchlist and reading history stay in TickerTalk. → keep: [[concern-data#Per app|TickerTalk data]] (decided) ^c19
- [thought] (Jordan Reyes, product lead) "Yes, reason's right. It's new purpose, needs consent we don't have, and it ties Coach to TickerTalk's data when we need them independent." The rejected option for TickerTalk data, sending the watchlist or history too, is rejected as a new purpose without consent that also ties Coach to TickerTalk's data. → keep: [[concern-data#Per app|TickerTalk data]] (decided) ^c20
- [decision] (Jordan Reyes, product lead) "Wording's good—commit it." The read-back of TickerTalk data is confirmed. → keep: [[concern-data#Per app|TickerTalk data]] (decided) ^c21

## Agenda

- Coach data: GATE-3 confirmed yes, status decided, override: GATE-5
- Coach operations: GATE-3 confirmed yes, status decided, override: GATE-5
- Coach ownership: GATE-3 confirmed yes, status decided, override: GATE-5
- TickerTalk data: GATE-3 confirmed yes, status decided, override: GATE-5

## Reviews

### 1. On the agenda (concern cells), 2026-10-09

- **Coverage:** FIN found 5; DAT found 6; PTN found 2, 3 dropped; REG found 6; OPS found 8
- **Dropped:** [PTN] Q-PTN-02, Q-PTN-03, Q-PTN-06 for PTY-03: the quote "**Agreements:** none known" has fewer than 4 words
- **Merged:** [OPS] into F1.19: Is the Coach team, led by @coach-lead, now the recorded owner and operator of Coach? Should the Coach x Ownership cell stop being 'unknown'?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-04@SV-01 | If a reader moves from paper practice to a real Brightwater account, does the paper balance convert, carry over or reset to nothing? If it converts, how? | "paper balances are not money" in [[03-context-and-scope]] |
| F1.2 | FIN | normal | Q-FIN-05@SV-01 | What happens to a reader's paper balance at expiry, withdrawal or account closure? And what happens to customer money if Brightwater's account is closed or the agreement ends on 90 days' notice? | "when a reader withdraws, Coach keeps their record for 30 days so they can undo it and then deletes it" in [[concern-data]] |
| F1.3 | FIN | normal | Q-FIN-06@SV-01 | Is any conversion rate planned between paper and real balances? If so, who sets it and who approves it? | "which carries the balances as money owed to its own customers" in [[03-context-and-scope]] |
| F1.4 | FIN | normal | new | What part of the 2.5 million pays for the stock list, the Fieldnote lessons, the Coach team's running costs and the platform engineer's help? Which cost centre carries Coach's AWS cost? | "the CFO holds the 2.5 million dollar budget" in [[11-unknowns-and-risks]] |
| F1.5 | FIN | normal | new | Which team and which budget carry Coach's running cost after launch? Does the roughly 180,000 dollar year-one figure include the Coach team's staff time and the platform engineer's help? | "Coach's page names the product lead as owner for now, and no team is recorded to run it." in [[concern-ownership]] |
| F1.6 | DAT | high | Q-DAT-02@APP-tickertalk | What customer data does TickerTalk hold or receive today (account, email, watchlists, reading history), who collected it and for what, and on what lawful basis may TickerTalk use it, including for the opt-in and coach screens? Who asks the privacy lead, and by when? | "What TickerTalk holds today, and the lawful basis it holds it on, is not recorded" in [[tickertalk-building-blocks]] |
| F1.7 | DAT | high | new | Is the product lead's statement that TickerTalk sends opaque IDs a decision that only the ID crosses to Coach? If so, will the Data cell for TickerTalk be recorded with that limit, with mobile's written confirmation (UNK-048) as the condition? | "TickerTalk data: sends opaque IDs" in [[2026-10-09-concern-cells]] |
| F1.8 | DAT | normal | new | Where does the paper record live (UNK-029), and does encryption of it settle anything about the lawful basis and the Brightwater crossing (UNK-059, UNK-060)? Or are those still open? | "Coach data: encrypts paper records" in [[2026-10-09-concern-cells]] |
| F1.9 | DAT | high | new | What stops reader data, such as watchlists and practice trades, from being used to train Signal without fresh opt-in consent? Who confirms in writing that release one uses it for nothing beyond the coach? | "release one trains nothing on reader data, the second part being an assumption" in [[01-goals]] |
| F1.10 | DAT | normal | new | Does hosting on Kestrel's AWS account settle where reader data is stored (region and processor terms)? If so, will UNK-028 and the Operations cell be updated to say so? | "Coach ops: Kestrel AWS, team-owned" in [[2026-10-09-concern-cells]] |
| F1.11 | DAT | normal | new | Who owns TickerTalk's reader consent records and the decision to send the ID to Coach? Does the 'unchanged' ownership practice cover that responsibility? | "the product lead says the existing ownership practice holds" in [[concern-ownership]] |
| F1.12 | PTN | high | Q-PTN-05@PTY-03 | Does any agreement with Outside Counsel allow assignment, or a change of who controls it? | "Outside Counsel is the legal adviser whose written reply on the first release is in sources." in [[03-context-and-scope]] |
| F1.13 | PTN | normal | new | Is Fieldnote Learning the named owner of lesson writing, so the Ownership page and UNK-018 can be updated? Is the contract locked in or ended on 30 days' notice, and who gives that notice? | "Nobody is named yet for [[11-unknowns-and-risks#UNK-018 Who writes the lessons and defines ready\|writing the lessons and defining ready]]." in [[concern-ownership]] |
| F1.14 | REG | normal | Q-REG-01@INI-001 | Will the coach, Brightwater and Quoteline be sold or promised as one offer, a bundle or joint offer? If not, which page records that decision? | "Whether the coach, Brightwater and Quoteline together make a product sold or promised across parties, and who is liable to the customer when one part fails, are still open" in [[11-unknowns-and-risks]] |
| F1.15 | REG | normal | Q-REG-05@INI-001 | Who is liable to the reader when one part fails: Kestrel, Brightwater or Quoteline? What do counsel and compliance say, and by when? | "who is liable to the customer when one part fails, are still open" in [[11-unknowns-and-risks]] |
| F1.16 | REG | high | new | Is Sarah Chen's 2 October ruling in writing? Does the ban run to March 2028 or for 'year one'? Should CST-2 on the constraints page be updated, and who has the ruling? | "Whether the ruling is in writing is not stated." in [[2026-10-09-concern-cells]] |
| F1.17 | REG | high | new | Does a rejected lesson restart the ten-business-day clock and push the 15 February clearance date past the March beta? Do paper-only beta readers count as Brightwater customers for the content review? Is 'unchanged' right for rollout while the compliance ruling is still open? | "the figure does not mention the clock restarting on a rejection or the limit of ten sandbox test accounts." in [[concern-rollout]] |
| F1.18 | REG | high | new | Does Coach receive anything besides the reader ID? Has the privacy lead confirmed the lawful basis for Coach holding that data, and does the ID cross to Brightwater or to any new party? | "TickerTalk sends Coach opaque reader IDs" in [[2026-10-09-concern-cells]] |
| F1.19 | REG, OPS | high | new | Who is the named owner of Coach and of lesson content for compliance and Brightwater review purposes? Should the ownership page and the Coach page be reconciled with @coach-lead? | "Coach's page names the product lead as owner for now, and no team is recorded to run it." in [[concern-ownership]] |
| F1.20 | OPS | normal | Q-OPS-03@CAP-003 | Which team owns CAP-003 once the teams form? Should the page be updated now that the product lead has defined 'ready' as three graded paper trades plus the lessons? | "What ”ready” means is not yet defined." in [[CAP-003-pass-the-ready-track]] |
| F1.21 | OPS | high | Q-OPS-04@INI-001 | Which system is the one record of a reader's paper balance and trades, Coach or the Brightwater sandbox? Is that settled by the Coach lead's statement, and does the data concern page need correcting? | "Each reader's paper balance and trades have to live in one system, either Coach or Brightwater's sandbox, and the vault does not yet say which." in [[concern-data]] |
| F1.22 | OPS | normal | Q-OPS-05@INI-001 | Is anything retired or replaced by this initiative, for example an existing watchlist or news flow? If so, who still depends on it? | "[[tickertalk-building-blocks\|TickerTalk]], the news app, changed to add the coach screens and to send Coach the reader ID" in [[03-context-and-scope]] |
| F1.23 | OPS | normal | new | Who owns the lessons, the stock list and the ready track after the change: the product lead, the Coach team or Fieldnote Learning? Who accepts the work? | "@coach-lead owns Coach, and the product lead owns the lessons." in [[2026-10-09-concern-cells]] |
| F1.24 | OPS | normal | new | Which team owns the TickerTalk and mobile changes, and has the mobile lead confirmed capacity in writing? Is 'unchanged' right while that is unconfirmed? | "TickerTalk's ownership has not been examined." in [[concern-ownership]] |
| F1.25 | OPS | normal | new | Who covers Coach out of hours from the first run until the rota starts on 1 March, and who covers it once the platform engineer's first month ends? | "with the platform engineer's help for the first month, according to the CTO" in [[concern-ownership]] |
| F1.26 | OPS | normal | new | Is 'unchanged' right for Coach observability, security and testing when Coach is a new service? Who monitors it, and who handles alerts out of hours? | "Seven cells are `unchanged`: Coach observability, security and testing" in [[2026-10-09-concern-cells]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| UNK-022 | open | resolved | [[2026-10-09-concern-cells#^c01]] |
| Coach data cell | unknown | addressed | [[2026-10-09-concern-cells#^c12]] |
| Coach operations cell | unknown | addressed | [[2026-10-09-concern-cells#^c15]] |
| Coach ownership cell | unknown | addressed | [[2026-10-09-concern-cells#^c18]] |
| TickerTalk data cell | unknown | addressed | [[2026-10-09-concern-cells#^c21]] |
| R-FIN-26 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-FIN-27 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-DAT-19 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-DAT-20 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-DAT-21 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-DAT-22 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-DAT-23 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-PTN-25 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-REG-27 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-REG-28 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-REG-29 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-REG-30 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-OPS-26 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-OPS-27 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-OPS-28 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
| R-OPS-29 | - | open | [[2026-10-09-concern-cells#1. On the agenda (concern cells), 2026-10-09]] |
