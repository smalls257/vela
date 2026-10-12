---
id: 2026-10-06-one-customer-mandate
type: session
title: "Dump & Diverge: one customer mandate"
date: 2026-10-06
modes: [dump]
status: closed
summary: "Dumped the one-customer mandate: 17 open unknowns on what one customer, journey, account and next summer mean, plus the FERRYMASTER freeze; plus 21 reviewer questions open."
---

# 2026-10-06 Dump & Diverge: one customer mandate

## Captures

- [thought] (CIO, via solution lead) "one customer, one journey, one account across ferry and rail by next summer" → keep: [[01-goals#Goals|G1]] (inkling) ^c01
- [unknown] (solution lead) "Nobody has said what any of that means." What does "one customer" mean: one identity across ferry and rail, or one person de-duplicated across existing records? → keep: [[11-unknowns-and-risks#UNK-001 One customer|UNK-001]] (open) ^c02
- [unknown] (solution lead) What does "one journey" mean: one ticket for a ferry leg plus a rail leg, one booking flow, or one trip view after the fact? → keep: [[11-unknowns-and-risks#UNK-002 One journey|UNK-002]] (open) ^c03
- [unknown] (solution lead) What does "one account" mean: one login, one wallet or balance, one set of preferences, or one customer record behind several logins? → keep: [[11-unknowns-and-risks#UNK-003 One account|UNK-003]] (open) ^c04
- [unknown] (solution lead) What does "by next summer" mean: a date, a pilot on one route, or everything live? Who set it and what is it tied to? → keep: [[11-unknowns-and-risks#UNK-004 Next summer date|UNK-004]] (open) ^c05
- [unknown] (solution lead) "I don't know where to start." Who gave the mandate, and who can say what they meant? To fetch: the CIO's mandate in writing, held by the CIO's office. → keep: [[11-unknowns-and-risks#UNK-005 CIO mandate source|UNK-005]] (open) ^c06
- [idea] (claude) What if "one customer" starts as a single shared customer ID that links the existing ferry and rail accounts, with nothing merged yet? → park ^c07
- [wild] (claude) What if the customer never has an account, and the journey itself is the thing they hold, as with a boarding pass in a phone wallet? → park ^c08
- [idea] (claude) What if we start from one real traveller's day, say a commuter who takes rail to the port and then the ferry, and ask where they hit two of everything today? → park ^c09
- [idea] (claude) What if we turn the mandate around: list what the customer does twice today (two logins, two receipts, two sets of details) and call each one a candidate for "one"? → park ^c10
- [thought] (solution lead) "Ferry's SeaBook and FERRYMASTER, rail's RailCore—completely separate customer databases and logins." → keep: [[03-context-and-scope#Today|Today]] (inkling) ^c11
- [worry] (solution lead) "nobody's actually defined what the CIO means by 'one account'" → keep: [[11-unknowns-and-risks#UNK-003 One account|UNK-003]] (open) ^c12
- [worry] (solution lead) "I don't even know where to start." → keep: [[11-unknowns-and-risks#UNK-005 CIO mandate source|UNK-005]] (open) ^c13
- [unknown] (claude) What does each of SeaBook, FERRYMASTER and RailCore do, and which holds customer records, logins or payment details? Who owns each? → keep: [[11-unknowns-and-risks#UNK-016 What each system does|UNK-016]] (open) ^c14
- [unknown] (claude) Do SeaBook and FERRYMASTER both serve the ferry side for the same job, such as one for booking and one for operations, or one per route or brand? → keep: [[11-unknowns-and-risks#UNK-016 What each system does|UNK-016]] (open) ^c15
- [idea] (claude) What if the first step is a one-page "what we think the CIO means" with three readings of "one account", sent to the CIO to pick from, rather than waiting for a definition? → park ^c16
- [wild] (claude) What if we skip choosing and prototype all three readings of "one account" as paper mock-ups, then show the CIO which one they point at? → park ^c17
- [idea] (claude) What if we borrow from airline alliances: each side keeps its own system, and a shared loyalty-style ID sits on top, with no database merge? → park ^c18
- [idea] (claude) What if we ask what the customer sees today when they book ferry and then rail, and use that as the baseline before any definition of "one"? → park ^c19
- [thought] (solution lead) "Merged three months, ferry and rail ops still completely separate—Kestrel Bay and Dunmere." → keep: [[03-context-and-scope#Today|Today]] (inkling) ^c20
- [worry] (solution lead) "Ferry Operations won't let us touch FERRYMASTER until after their September season, but the CIO wants this done by next summer. Those two things don't line up at all." → keep: [[11-unknowns-and-risks#UNK-006 Freeze and next summer|UNK-006]] (open) ^c21
- [unknown] (claude) Which of Kestrel Bay and Dunmere is the ferry company and which is the rail company, and who leads each? → keep: [[11-unknowns-and-risks#UNK-017 Kestrel Bay and Dunmere|UNK-017]] (open) ^c22
- [unknown] (claude) Which September does the freeze end after, and does "next summer" fall before or after it? Who in Ferry Operations set the freeze, and is it a rule or a request? → keep: [[11-unknowns-and-risks#UNK-006 Freeze and next summer|UNK-006]] (open) ^c23
- [unknown] (claude) Does "one account" need any change inside FERRYMASTER, or could it be done from outside, by reading from it or sitting in front of it? → keep: [[11-unknowns-and-risks#UNK-007 Change inside FERRYMASTER|UNK-007]] (open) ^c24
- [idea] (claude) What if the first release touches only SeaBook and RailCore, and FERRYMASTER joins after the season? → park ^c25
- [idea] (claude) What if "next summer" is a pilot, with one rail route and one ferry route and a small group of customers, and the full rollout follows the season? → park ^c26
- [wild] (claude) What if we turn the freeze around: the September season is the best test data we will get, so we watch it read-only and build the account layer from what we see? → park ^c27
- [idea] (claude) What if we borrow from how banks join up after a merger: the front door becomes one, and the back-office systems stay separate for years? → park ^c28
- [unknown] (claude) Who else in the merged company has a stake in the date, such as finance, marketing or the CIO's sponsor, and what does the date mean to them? → keep: [[11-unknowns-and-risks#UNK-010 Date stakeholders|UNK-010]] (open) ^c29
- [thought] (Ferry Operations director, via solution lead) FERRYMASTER is off limits May through September. The lead's words: "we can't touch FERRYMASTER May through September, and the CIO wants this live by next summer. Those dates just don't fit." → keep: [[02-constraints#Constraints|CST-1]] (inkling) ^c30
- [worry] (solution lead) "honestly not sure what would persuade them." (the Ferry Operations director) → keep: [[11-unknowns-and-risks#UNK-008 Ferry Operations director stance|UNK-008]] (open) ^c31
- [unknown] (claude) Is the May to September freeze written down anywhere, such as a change policy or an agreement between ferry ops and IT? To fetch: the freeze policy, held by the Ferry Operations director. → keep: [[11-unknowns-and-risks#UNK-006 Freeze and next summer|UNK-006]] (open) ^c32
- [unknown] (claude) What does "live" mean for the CIO's date: all customers, a first group, or a demo? Does a pilot that runs only on SeaBook and RailCore count? → keep: [[11-unknowns-and-risks#UNK-004 Next summer date|UNK-004]] (open) ^c33
- [unknown] (claude) What does the Ferry Operations director fear most about a change near the season: lost bookings, boarding failures, or something else? → keep: [[11-unknowns-and-risks#UNK-008 Ferry Operations director stance|UNK-008]] (open) ^c34
- [idea] (claude) What if the director is asked what they would let us do in the freeze, such as read-only access, a copy of the data, or a test environment, instead of asking them to lift it? → park ^c35
- [idea] (claude) What if we offer the director something in return, such as a fix for a FERRYMASTER pain point, or a seat on the design? → park ^c36
- [wild] (claude) What if the only work in FERRYMASTER is done in October to April, and "next summer" ships a feature that is switched off on the ferry side until the freeze ends? → park ^c37
- [idea] (claude) What if we take the clash to the CIO as a choice between dates, scopes and risk, and let them choose, rather than solving it quietly? → park ^c38
- [thought] (solution lead) "May to September is the freeze, yes." This settles the window raised in ^c30. → keep: [[02-constraints#Constraints|CST-1]] (inkling) ^c39
- [worry] (solution lead) "'one account' still means nothing to anybody, and that's what's blocking me." → keep: [[11-unknowns-and-risks#UNK-003 One account|UNK-003]] (open) ^c40
- [worry] (solution lead) "The freeze dates never move, and we hit May still arguing about what 'one account' means." → keep: [[11-unknowns-and-risks#UNK-006 Freeze and next summer|UNK-006]] (open) ^c41
- [worry] (solution lead) "Ferry and rail both quietly build their own thing because nobody told them to stop." → keep: [[11-unknowns-and-risks#UNK-011 Parallel builds by ferry and rail|UNK-011]] (open) ^c42
- [worry] (solution lead) "CIO moves on or next summer just gets pushed to autumn, we're still running both systems in parallel." → keep: [[11-unknowns-and-risks#UNK-012 Slipping date and parallel running|UNK-012]] (open) ^c43
- [worry] (solution lead) "The CFO and Rail Product director want totally different things" → keep: [[11-unknowns-and-risks#UNK-013 CFO and Rail Product wants|UNK-013]] (open) ^c44
- [worry] (solution lead) "Ferry Operations director blocks every change" → keep: [[11-unknowns-and-risks#UNK-008 Ferry Operations director stance|UNK-008]] (open) ^c45
- [worry] (solution lead) "instead of one platform we end up with three teams all trying different things at once." → keep: [[11-unknowns-and-risks#UNK-011 Parallel builds by ferry and rail|UNK-011]] (open) ^c46
- [worry] (solution lead) "Customers end up logging in somewhere and half the features don't work." → keep: [[11-unknowns-and-risks#UNK-014 Features across logins|UNK-014]] (open) ^c47
- [worry] (solution lead) "Honestly not sure how many of them even want this merged anyway—we never asked." → keep: [[11-unknowns-and-risks#UNK-015 Customer appetite and consent|UNK-015]] (open) ^c48

## Reviews

### 1. after the pre-mortem, 2026-10-06

- **Coverage:** FIN found 7; DAT found 7; PTN found 6, 1 dropped; REG found 6; OPS found 7, 2 dropped
- **Dropped:** PTN: its quote is from a generated block on 11-unknowns-and-risks, not the written text (Q-PTN-01@INI-001 is still owed); OPS: two findings named Q-OPS-07 without its @INI-001 suffix, because the copy ID was mistyped in the reviewer's input (Q-OPS-07@INI-001 is still owed)

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | Do any of SeaBook, FERRYMASTER or RailCore hold stored value for customers (points, credits, balances, vouchers, deposits, saved payment details)? If so, who owes it to the customer, and what happens to it if accounts are linked or merged? | "one login, one wallet or balance, one set of preferences, or one customer record behind several logins?" in [[2026-10-06-one-customer-mandate]] |
| F1.2 | FIN | high | Q-FIN-02@INI-001 | Who pays to build the one-customer capability, and which budget carries the running cost of the shared layer and of both ferry and rail systems running in parallel? | "Who else in the merged company has a stake in the date, such as finance, marketing or the CIO's sponsor, and what does the date mean to them?" in [[2026-10-06-one-customer-mandate]] |
| F1.3 | FIN | normal | Q-FIN-02@INI-001 | What are the licence terms and running costs of SeaBook, FERRYMASTER and RailCore, and what would a shared ID layer add? | "Running cost, licences and shared budgets such as mainframe processing." in [[concern-cost]] |
| F1.4 | FIN | high | new | What does the CFO want from this, who holds the budget, and how does that differ from what the Rail Product director wants? | "The CFO and Rail Product director want totally different things" in [[2026-10-06-one-customer-mandate]] |
| F1.5 | FIN | normal | new | What does the parallel running cost per month, and does the case for the mandate depend on savings or on revenue? | "CIO moves on or next summer just gets pushed to autumn, we're still running both systems in parallel." in [[2026-10-06-one-customer-mandate]] |
| F1.6 | FIN | normal | new | Is any funded ferry or rail work on customer accounts already under way, and who would stop it or absorb its cost? | "Ferry and rail both quietly build their own thing because nobody told them to stop." in [[2026-10-06-one-customer-mandate]] |
| F1.7 | FIN | normal | new | What would it cost, and who would pay, to meet 'next summer' with a pilot that leaves FERRYMASTER untouched, compared with a delayed full rollout? | "FERRYMASTER is off limits May through September." in [[2026-10-06-one-customer-mandate]] |
| F1.8 | DAT | high | Q-DAT-01@INI-001 | Under the one-account mandate, will ferry customer data (SeaBook, FERRYMASTER) be used by the rail company, and rail data (RailCore) by the ferry company? Which legal entity collected each, and who may use it now? | "completely separate customer databases and logins" in [[2026-10-06-one-customer-mandate]] |
| F1.9 | DAT | high | Q-DAT-05@INI-001 | What was each system's customer data collected for, and does linking or merging accounts into one identity count as a new purpose that needs fresh consent or another lawful basis? | "What if ”one customer” starts as a single shared customer ID that links the existing ferry and rail accounts, with nothing merged yet?" in [[2026-10-06-one-customer-mandate]] |
| F1.10 | DAT | high | new | If customers are matched across ferry and rail records, what lawful basis allows it, and do customers have to opt in? | "one identity across ferry and rail, or one person de-duplicated across existing records?" in [[2026-10-06-one-customer-mandate]] |
| F1.11 | DAT | high | new | Which of SeaBook, FERRYMASTER and RailCore hold payment details, preferences and consents, and how will these follow a customer across systems? | "which holds customer records, logins or payment details? Who owns each?" in [[2026-10-06-one-customer-mandate]] |
| F1.12 | DAT | normal | new | What did ferry and rail customers agree to when they signed up, and will they be told or asked before their records are linked? | "Honestly not sure how many of them even want this merged anyway—we never asked." in [[2026-10-06-one-customer-mandate]] |
| F1.13 | DAT | normal | new | May live or copied FERRYMASTER data be used for design or test work, and under what basis and controls? | "we watch it read-only and build the account layer from what we see?" in [[2026-10-06-one-customer-mandate]] |
| F1.14 | DAT | normal | new | Who will fill in the data concern with what each app stores, which app is the record, and what moves? | "What each app stores, which app is the record, and what moves during the change." in [[concern-data]] |
| F1.15 | PTN | high | new | Is the FERRYMASTER freeze a written policy or agreement, who can waive it, and does it bind a contractor or vendor? | "Is the May to September freeze written down anywhere, such as a change policy or an agreement between ferry ops and IT?" in [[2026-10-06-one-customer-mandate]] |
| F1.16 | PTN | high | new | Who supplies and owns each of the three systems, and what do their contracts say about access, change, notice and exit? | "What does each of SeaBook, FERRYMASTER and RailCore do, and which holds customer records, logins or payment details? Who owns each?" in [[2026-10-06-one-customer-mandate]] |
| F1.17 | PTN | normal | new | Do the FERRYMASTER and SeaBook agreements allow read access or a front layer without the supplier's consent? | "Does ”one account” need any change inside FERRYMASTER, or could it be done from outside, by reading from it or sitting in front of it?" in [[2026-10-06-one-customer-mandate]] |
| F1.18 | PTN | normal | new | Which legal entity owns which system and customer relationship, and which contracts or intercompany arrangements need to change? | "Merged three months, ferry and rail ops still completely separate—Kestrel Bay and Dunmere." in [[2026-10-06-one-customer-mandate]] |
| F1.19 | PTN | normal | new | Who sponsors and funds the work, and who has authority to stop ferry and rail building their own versions? | "The CFO and Rail Product director want totally different things" in [[2026-10-06-one-customer-mandate]] |
| F1.20 | PTN | normal | new | Is 'next summer' tied to any external commitment or contract date, and where is the mandate in writing? | "To fetch: the CIO's mandate in writing, held by the CIO's office." in [[2026-10-06-one-customer-mandate]] |
| F1.21 | REG | normal | Q-REG-01@INI-001 | Under the reading of 'one journey' the CIO intends, will ferry and rail be sold or promised as one joint ticket or bundle, or only shown together? | "one ticket for a ferry leg plus a rail leg, one booking flow, or one trip view after the fact?" in [[2026-10-06-one-customer-mandate]] |
| F1.22 | REG | normal | Q-REG-02@INI-001 | Which regulators or licences cover the ferry and rail businesses, payment data and customer data, and does a shared customer ID or account touch any of them? | "which holds customer records, logins or payment details? Who owns each?" in [[2026-10-06-one-customer-mandate]] |
| F1.23 | REG | normal | Q-REG-05@INI-001 | If the ferry leg or the rail leg fails in a joint journey or account, which company is liable to the customer, and under which terms? | "Customers end up logging in somewhere and half the features don't work." in [[2026-10-06-one-customer-mandate]] |
| F1.24 | REG | high | new | Which legal entity will be the customer's counterparty for a combined account or journey, and are Kestrel Bay and Dunmere one legal entity yet? | "Merged three months, ferry and rail ops still completely separate—Kestrel Bay and Dunmere." in [[2026-10-06-one-customer-mandate]] |
| F1.25 | REG | high | new | What do the existing ferry and rail customer terms and consents allow, and does a shared customer ID that links accounts need new consent or notice? | "Honestly not sure how many of them even want this merged anyway—we never asked." in [[2026-10-06-one-customer-mandate]] |
| F1.26 | REG | normal | new | Does the freeze come from internal policy or from a safety, licence or regulatory duty, and who can lift it? | "Is the May to September freeze written down anywhere, such as a change policy or an agreement between ferry ops and IT?" in [[2026-10-06-one-customer-mandate]] |
| F1.27 | OPS | normal | Q-OPS-04@INI-001 | Do SeaBook and FERRYMASTER do the same job, and what exactly does each of the three systems hold: customer records, logins, payments? Who owns each? | "Do SeaBook and FERRYMASTER both serve the ferry side for the same job, such as one for booking and one for operations, or one per route or brand?" in [[2026-10-06-one-customer-mandate]] |
| F1.28 | OPS | normal | Q-OPS-04@INI-001 | Which of Kestrel Bay and Dunmere is ferry and which is rail, and who leads each? Which duplicate databases and logins does the plan need to name? | "Merged three months, ferry and rail ops still completely separate—Kestrel Bay and Dunmere." in [[2026-10-06-one-customer-mandate]] |
| F1.29 | OPS | normal | Q-OPS-05@INI-001 | Is anything retired, such as a login, a customer database or a system? If so, who and what still depends on it, and when does the parallel running end? | "CIO moves on or next summer just gets pushed to autumn, we're still running both systems in parallel." in [[2026-10-06-one-customer-mandate]] |
| F1.30 | OPS | high | new | Is the May to September freeze a written rule or a request? Who set it? Does 'next summer' fall inside it, and does the plan need any change inside FERRYMASTER? | "we can't touch FERRYMASTER May through September, and the CIO wants this live by next summer. Those dates just don't fit." in [[2026-10-06-one-customer-mandate]] |
| F1.31 | OPS | high | Q-OPS-06@INI-001 | Which people and teams are affected but not yet in the room: the CFO, the Rail Product director, the ferry and rail IT teams, and customers? What does each want, and who loses under each reading of 'one account'? | "The CFO and Rail Product director want totally different things" in [[2026-10-06-one-customer-mandate]] |
| F1.32 | OPS | normal | new | Who owns the initiative's work and decides between teams? Who tells ferry and rail to stop building their own versions? Who runs the new shared layer, including out of hours? | "Ferry and rail both quietly build their own thing because nobody told them to stop." in [[2026-10-06-one-customer-mandate]] |
| F1.33 | OPS | normal | new | What must follow a customer between SeaBook, FERRYMASTER and RailCore, such as identity, wallet or balance and preferences? What happens when one side is frozen or down? | "Customers end up logging in somewhere and half the features don't work." in [[2026-10-06-one-customer-mandate]] |
- [thought] (solution lead) "nothing here helps until somebody defines what the CIO means by 'one account'. Everything else flows from that." This is a belief with no source; close asks whether it is load-bearing. → keep: [[11-unknowns-and-risks#Question ledger|Q-OPS-07@INI-001]] (assumed) ^c49
- [worry] (solution lead) "Do I ask the CIO direct, or am I going to look lost?" → keep: [[11-unknowns-and-risks#UNK-005 CIO mandate source|UNK-005]] (open) ^c50
- [idea] (claude) What if you go to the CIO with a short list of readings of "one account" to pick from, such as one login, one wallet or balance, one customer record, or one view of trips, instead of asking an open question? → park ^c51
- [idea] (claude) What if the question to the CIO is "which customer problem should this fix first?", so they answer in outcomes and you derive the definition? → park ^c52
- [wild] (claude) What if you ask the CIO's office what they expect to demo next summer, and the definition falls out of the demo? → park ^c53
- [unknown] (claude) Has the CIO already said more about "one account" in a slide, memo or town hall than the one line you were given? To fetch: that material, held by the CIO's office. → keep: [[11-unknowns-and-risks#UNK-005 CIO mandate source|UNK-005]] (open) ^c54
- [idea] (solution lead) "I'll check for existing material first—it's cheaper than asking fresh." This answers ^c54. → keep: [[11-unknowns-and-risks#UNK-005 CIO mandate source|UNK-005]] (open) ^c55
- [idea] (solution lead) "If there's nothing, the 'what's on screen' question will beat any definition fight." (ask the CIO what the customer should see on screen, instead of asking for a definition) → keep: [[04-solution-strategy#The core move|core move]] (inkling) ^c56
- [thought] (solution lead) "This one thing is blocking everything else." → keep: [[11-unknowns-and-risks#Question ledger|Q-OPS-07@INI-001]] (assumed) ^c57
- [thought] (solution lead) "Tidemiles sits on ferry, Northway Plus on rail" and "not sure which system actually holds the balances or whether they're in FERRYMASTER, a separate CRM or the loyalty platform itself." Answers Q-FIN-01@INI-001: yes, loyalty balances exist; holder not known. → keep: [[11-unknowns-and-risks#UNK-018 Loyalty balance holder|UNK-018]] (open) ^c58

## Changes

| ID | From | To | Source |
|---|---|---|---|
| G1 | - | inkling | [[2026-10-06-one-customer-mandate#^c01]] |
| CST-1 | - | inkling | [[2026-10-06-one-customer-mandate#^c30]] |
| UNK-001 | - | open | [[2026-10-06-one-customer-mandate#^c02]] |
| UNK-002 | - | open | [[2026-10-06-one-customer-mandate#^c03]] |
| UNK-003 | - | open | [[2026-10-06-one-customer-mandate#^c04]] |
| UNK-004 | - | open | [[2026-10-06-one-customer-mandate#^c05]] |
| UNK-005 | - | open | [[2026-10-06-one-customer-mandate#^c06]] |
| UNK-006 | - | open | [[2026-10-06-one-customer-mandate#^c21]] |
| UNK-007 | - | open | [[2026-10-06-one-customer-mandate#^c24]] |
| UNK-008 | - | open | [[2026-10-06-one-customer-mandate#^c31]] |
| UNK-010 | - | open | [[2026-10-06-one-customer-mandate#^c29]] |
| UNK-011 | - | open | [[2026-10-06-one-customer-mandate#^c42]] |
| UNK-012 | - | open | [[2026-10-06-one-customer-mandate#^c43]] |
| UNK-013 | - | open | [[2026-10-06-one-customer-mandate#^c44]] |
| UNK-014 | - | open | [[2026-10-06-one-customer-mandate#^c47]] |
| UNK-015 | - | open | [[2026-10-06-one-customer-mandate#^c48]] |
| UNK-016 | - | open | [[2026-10-06-one-customer-mandate#^c14]] |
| UNK-017 | - | open | [[2026-10-06-one-customer-mandate#^c22]] |
| R-FIN-01 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-FIN-02 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-FIN-03 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-FIN-04 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-DAT-01 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-DAT-02 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-DAT-03 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-DAT-04 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-DAT-05 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-PTN-01 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-PTN-02 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-PTN-03 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-PTN-04 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-PTN-05 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-PTN-06 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-REG-01 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-REG-02 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-REG-03 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-OPS-01 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-OPS-02 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| R-OPS-03 | - | open | [[2026-10-06-one-customer-mandate#1. after the pre-mortem, 2026-10-06]] |
| Q-OPS-07@INI-001 | - | assumed | [[2026-10-06-one-customer-mandate#^c49]] |
| UNK-018 | - | open | [[2026-10-06-one-customer-mandate#^c58]] |
| Q-FIN-01@INI-001 | - | unknown | [[2026-10-06-one-customer-mandate#^c58]] |
