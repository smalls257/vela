---
id: 2026-10-08-trading-coach
type: session
title: "Dump & Diverge: trading-coach"
date: 2026-10-08
modes: [dump]
status: closed
summary: "Dumped the CEO's trading-coach ask as one goal, 13 unknowns, 3 ledger rows and 15 open reviewer questions."
---

# 2026-10-08 Dump & Diverge: trading-coach

## Captures

- [idea] (product lead) CEO's ask, in his words: "an AI coach that teaches people to trade one stock or option at a time, and trades for them when they're ready", live by March. → keep: [[01-goals#Goals|G1]] (inkling) ^c01
- [thought] (product lead) The product lead runs product for the news app and has been told to make it happen, with no idea where to start. → drop: describes the lead's role, not the initiative ^c02
- [unknown] (product lead) "The CEO's one-liner doesn't say what 'trades for them' means—is it placing orders the model picked, or just coaching through it, or something else?" → keep: [[11-unknowns-and-risks#UNK-001 Meaning of trades for them|UNK-001]] (open) ^c03
- [unknown] (product lead) "I don't know if he means by March this year or next." → keep: [[11-unknowns-and-risks#UNK-002 Which March|UNK-002]] (open) ^c04
- [thought] (product lead) We have TickerTalk at 400k monthly users. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c05
- [thought] (product lead) We have a broker called Brightwater, on API since June. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c06
- [thought] (product lead) We have an ML model called Signal that guesses next-day moves on fifty large-cap stocks. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c07
- [thought] (product lead) We have a compliance person two days a week. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c08
- [worry] (product lead) "We're now a fintech in four months with zero trading product, zero real-money experience, and March is not far off." → keep: [[11-unknowns-and-risks#UNK-012 Team trading experience|UNK-012]] (open) ^c09
- [idea] (claude) What if "trades for them" is a ladder rather than one switch: watch, then paper-trade, then confirm each order by hand, then trade within a limit the user sets? "Ready" would then be a step the user climbs, not a date the product flips. → park ^c10
- [idea] (claude) What if the coach in March only teaches, on paper trades or a simulator, and the real-money step is a later release? Borrowed from flight simulators: nobody flies the aircraft before hours in the sim. → park ^c11
- [wild] (claude) What if the coach never held a position of its own, and "trades for them" meant the coach prepares the order and Brightwater's own app or screen takes the final confirm? → park ^c12
- [idea] (claude) What if Signal were switched around: instead of telling users what to buy, the coach shows users where Signal was wrong, as a teaching tool ("here is a guess that failed, and why")? → park ^c13
- [wild] (claude) What if the first lesson were run on stocks TickerTalk readers already read about that day, so the news article is the lesson and the trade is the homework? → park ^c14
- [idea] (claude) What if the 400k readers were not the launch audience, but a waitlist of 500 people, so the first real-money weeks run on a small group? → park ^c15
- [wild] (claude) What if the coach taught only options first, or only one stock for the first month, because "one at a time" could mean the product holds one position per user at a time? → park ^c16
- [idea] (claude) What if the compliance person's two days a week were spent on a one-page rulebook of what the coach may and may not say, before any build starts, so every lesson is checked against it? → park ^c17
- [unknown] (claude) Is the "four months" the product lead's own count to March, which would make March next year, or is it a different deadline? → keep: [[11-unknowns-and-risks#UNK-002 Which March|UNK-002]] (open) ^c18
- [unknown] (product lead) Who knows where the CEO's idea came from: "CEO didn't say where it came from, just handed it down." → keep: [[11-unknowns-and-risks#UNK-003 Origin of the CEO idea|UNK-003]] (open) ^c19
- [unknown] (product lead) to fetch: the Brightwater API agreement, held by Partnerships (product lead: "ask Partnerships for Brightwater's agreement"). → keep: [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]] (open) ^c20
- [unknown] (product lead) to fetch: Signal's backtest, held by the ML team (product lead: "ML for Signal's backtest"). → keep: [[11-unknowns-and-risks#UNK-005 Signal backtest|UNK-005]] (open) ^c21
- [unknown] (claude) to fetch: TickerTalk's user terms and privacy notice, holder not named; the product lead did not say who holds them. → keep: [[11-unknowns-and-risks#UNK-006 TickerTalk terms and privacy notice|UNK-006]] (open) ^c22
- [thought] (product lead) Belief with no source: "if we call this education not advice we don't need registration, but I could be wrong". → keep: [[04-solution-strategy#The core move|04 core move]] (inkling) ^c23
- [worry] (product lead) "One consultant two days a week is all I have to bet that on." → keep: [[11-unknowns-and-risks#UNK-010 Education line and counsel|UNK-010]] (open) ^c24
- [idea] (claude) What if the education-or-advice line were drawn by what the product does, for example whether it ever names a stock for a user to buy, rather than by what the product is called? The coach could then be built so it can show the test on any screen. → park ^c25
- [wild] (claude) What if Brightwater's own license covered the regulated part, and the coach lived inside their permissions instead of TickerTalk holding its own? → park ^c26
- [wild] (claude) What if the claim were turned around, and the product were built as registered advice from day one, with a registered adviser on contract, so nothing rests on the education label? → park ^c27
- [idea] (claude) What if the two consultant days were used as a gate: no lesson, screen or push notice ships until it is on a list the consultant has read? → park ^c28
- [thought] (product lead) "No, haven't talked to counsel or Brightwater yet." → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c29
- [worry] (product lead) "The real blocker is figuring out who builds this: mobile's on the news app, the ML team is three people, and I don't know if we're adding a new team or pulling from somewhere." → keep: [[11-unknowns-and-risks#UNK-009 Build team new or pulled|UNK-009]] (open) ^c30
- [unknown] (product lead) Whether the build is a new team or people pulled from existing teams: "I don't know if we're adding a new team or pulling from somewhere." → keep: [[11-unknowns-and-risks#UNK-009 Build team new or pulled|UNK-009]] (open) ^c31
- [thought] (product lead) The mobile team is on the news app, and the ML team is three people. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c32
- [idea] (claude) What if the first build team were the coach's smallest slice, say one product person, one mobile engineer and one ML engineer borrowed for a fixed number of weeks, with a date when the loan is reviewed? → park ^c33
- [wild] (claude) What if Brightwater's team built the order screen, since they already run the broker side, and TickerTalk built only the teaching? → park ^c34
- [idea] (claude) What if the coach were a web view inside the news app, so the mobile team ships one container once and the lessons change without app-store releases? → park ^c35
- [wild] (claude) What if the first lessons were written by hand by TickerTalk's editors, and the AI part came in only where the hand-written ones ran out? → park ^c36
- [thought] (product lead) "CEO decides, but I'd be the one to pitch it." The CEO decides whether to move people; the product lead pitches it. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c37
- [thought] (product lead) "Nobody's been told yet." Mobile, ML, Partnerships and compliance have not been told of the ask. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c38
- [idea] (claude) What if the pitch to the CEO carried the ladder (c10) as a menu of three scopes with a team size and a date for each, so the CEO picks the scope and not just the date? → park ^c39
- [worry] (product lead) "Compliance sign-off takes until February and we ship anyway because the demo date is sacred." → keep: [[11-unknowns-and-risks#UNK-011 Compliance sign-off against launch date|UNK-011]] (open) ^c40
- [worry] (product lead) "Signal's backtest was too good—it overfits and loses money on real money and we're liable." → keep: [[11-unknowns-and-risks#UNK-005 Signal backtest|UNK-005]] (open) ^c41
- [worry] (product lead) "The mobile team burns out because I'm pulling people and TickerTalk breaks and the CEO blames me." → keep: [[11-unknowns-and-risks#UNK-009 Build team new or pulled|UNK-009]] (open) ^c42
- [worry] (product lead) "We build for all 400k users instead of a small cohort and the broker's sandbox can't handle it or the API falls over when real orders start flowing." → keep: [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]] (open) ^c43
- [worry] (product lead) "Nobody on the team has actually placed a trade so we miss something huge about how orders actually work and users lose money in the first week." → keep: [[11-unknowns-and-risks#UNK-012 Team trading experience|UNK-012]] (open) ^c44
- [worry] (product lead) "The CEO changes his mind about what 'trades for them' means halfway through and we rebrand twice." → keep: [[11-unknowns-and-risks#UNK-001 Meaning of trades for them|UNK-001]] (open) ^c45
- [worry] (product lead) "Brightwater says no at the last minute to something we've already shipped—the quotes, or the account link, or the auto-trading piece." → keep: [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]] (open) ^c46
- [worry] (product lead) "We run out of money before March because building a fintech is way more expensive than a news app and the CFO's 2.5 million disappears into infra and lawyers." → keep: [[11-unknowns-and-risks#UNK-007 CFO 2.5 million budget|UNK-007]] (open) ^c47
- [worry] (product lead) "The consultant says we need to register as advisers and suddenly the whole thing stops." → keep: [[11-unknowns-and-risks#UNK-010 Education line and counsel|UNK-010]] (open) ^c48
- [unknown] (product lead) to fetch: the CFO's 2.5 million budget, the document or approval behind it, held by the CFO (the product lead named the CFO; the document itself was not named). → keep: [[11-unknowns-and-risks#UNK-007 CFO 2.5 million budget|UNK-007]] (open) ^c49
- [unknown] (claude, from product lead) Where the quotes in the product would come from and on what terms, since the product lead names "the quotes" as something Brightwater could refuse. Source and holder of that license or agreement were not named. → keep: [[11-unknowns-and-risks#UNK-008 Source and terms of quotes|UNK-008]] (open) ^c50
- [unknown] (claude, from product lead) Whether the "account link" and "auto-trading piece" are things the Brightwater agreement allows, since the product lead fears Brightwater saying no to them. → keep: [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]] (open) ^c51
- [thought] (product lead) Q-PTN-01@INI-001, Q-REG-02@INI-001, Q-OPS-07@INI-001, F1.27, F1.28: "Can't move without the Brightwater agreement and counsel confirming the education-not-advice thing—both load-bearing." Belief, no source: the Brightwater agreement and counsel's confirmation are each load-bearing for the plan. → keep: [[11-unknowns-and-risks#Question ledger|Q-PTN-01@INI-001]] (unknown) ^c52
- [worry] (product lead) "If I call them before pitching the CEO, he'll know something's up." → drop: squared by the lead's own plan in c59 to c63 ^c53
- [unknown] (product lead) "How do I square that?" How to get the Brightwater agreement and counsel's view before the pitch without the CEO learning of it early. → drop: answered by the lead's plan in c63 ^c54
- [idea] (claude) What if the agreement needed no call to Brightwater at all? It is held by Partnerships (c20), so reading it is an internal step, and what it allows can be known before anyone outside the company hears of the ask. → park ^c55
- [idea] (claude) What if the question to counsel and to the consultant were put in general form, such as "what separates education from advice for a retail trading product", with no TickerTalk name or date on it? → park ^c56
- [idea] (claude) What if the "he'll know something's up" worry were turned around, and the pitch to the CEO itself named the two checks as its first gate, with a date for each? → park ^c57
- [wild] (claude) What if the pitch asked for a two-week "can we?" phase before the "will we?", so the CEO funds the two answers and not the product? → park ^c58
- [thought] (product lead) "Partnerships manager can get the agreement, no problem—it's part of my job to read it." The Brightwater agreement (c20) is reachable through the Partnerships manager, with no stated need to explain why. → keep: [[03-context-and-scope#Today|03 Today]] (inkling) ^c59
- [unknown] (product lead) Q-REG-02@INI-001, F1.18: "Counsel's a question mark, honestly not sure if we have anyone beyond the consultant." Whether the company has counsel beyond the consultant. → keep: [[11-unknowns-and-risks#Question ledger|Q-REG-02@INI-001]] (unknown) ^c60
- [thought] (product lead) "I'll ask the consultant in general form first, then pitch once I have answers." The order is: the consultant first, in general form, then the CEO pitch. → keep: [[04-solution-strategy#The core move|04 core move]] (inkling) ^c61
- [thought] (product lead) "Pitch once I have answers." Belief, no source: the pitch to the CEO waits for the Brightwater agreement (c59) and the consultant's answer (c61). → keep: [[04-solution-strategy#The core move|04 core move]] (inkling) ^c62
- [thought] (product lead) "I'll read the agreement this week, ask the consultant Monday, and take it to the CEO once I have answers on both." The plan: read the Brightwater agreement this week, ask the consultant on Monday, then go to the CEO with both answers. → keep: [[04-solution-strategy#The core move|04 core move]] (inkling) ^c63
- [unknown] (product lead) "Do we know users will actually want this? We're a news app—how does options trading fit the product?" → keep: [[11-unknowns-and-risks#UNK-013 Reader demand for coach|UNK-013]] (open) ^c64

## Reviews

### 1. After the pre-mortem, 2026-10-08

- **Coverage:** FIN found 6; DAT found 5; PTN found 6; REG found 6; OPS found 7, 1 dropped
- **Dropped:** [OPS] the quote does not mention what the finding is about: Is there more than one scheme or owner for the same job: who places orders (the coach or Brightwater's app), and who owns the education line (the consultant, counsel or Brightwater's license)? Which date applies?
- **Merged:** [OPS] into F1.21: Who has authority to hold a launch if compliance has not signed off, and how will two days a week cover review of every lesson, screen and push notice?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | Would TickerTalk ever hold customer cash, positions, credits or deposits, or would Brightwater hold all of them? What does 'trades for them' mean for custody of customer funds? | "the product holds one position per user at a time" in [[2026-10-08-trading-coach]] |
| F1.2 | FIN | high | Q-FIN-02@INI-001 | Is the 2.5 million approved, what does it cover (build, run, legal, Brightwater fees, compliance), and which budget carries the running cost after launch? | "the CFO's 2.5 million disappears into infra and lawyers" in [[2026-10-08-trading-coach]] |
| F1.3 | FIN | normal | Q-FIN-02@INI-001 | Which cost center pays for the build team, and does the news app lose capacity or revenue when people are pulled from it? | "I don't know if we're adding a new team or pulling from somewhere." in [[2026-10-08-trading-coach]] |
| F1.4 | FIN | high | new | If users lose money following Signal or the coach, who bears the loss and legal cost (TickerTalk, Brightwater or the user)? Are there Brightwater fees or revenue terms that change the cost of the plan? | "it overfits and loses money on real money and we're liable" in [[2026-10-08-trading-coach]] |
| F1.5 | FIN | normal | new | How is the coach meant to earn money, and what return is expected against the 2.5 million? | "We run out of money before March because building a fintech is way more expensive than a news app" in [[2026-10-08-trading-coach]] |
| F1.6 | FIN | normal | new | What would registration or a contracted registered adviser cost, and is it inside the 2.5 million? | "The consultant says we need to register as advisers and suddenly the whole thing stops." in [[2026-10-08-trading-coach]] |
| F1.7 | DAT | high | Q-DAT-01@INI-001 | What user data will be shared with Brightwater (identity, account link, order data, reading history), and does the Brightwater agreement and the TickerTalk privacy notice allow it? | "Whether the ”account link” and ”auto-trading piece” are things the Brightwater agreement allows" in [[2026-10-08-trading-coach]] |
| F1.8 | DAT | high | Q-DAT-05@INI-001 | Do TickerTalk's privacy notice and user terms allow readers' data to be used for a trading coach, and who holds those documents? | "to fetch: TickerTalk's user terms and privacy notice, holder not named" in [[2026-10-08-trading-coach]] |
| F1.9 | DAT | normal | Q-DAT-05@INI-001 | What data does TickerTalk hold on its 400k users, and on what consent was it collected? | "We have TickerTalk at 400k monthly users." in [[2026-10-08-trading-coach]] |
| F1.10 | DAT | high | new | Who supplies the quotes and market data, and do the license terms allow showing them to users in the coach? | "Where the quotes in the product would come from and on what terms" in [[2026-10-08-trading-coach]] |
| F1.11 | DAT | normal | new | Who will hold users' trade, position and limit data, and how will a user's step on the ladder and their consents follow them between TickerTalk and Brightwater? | "trade within a limit the user sets" in [[2026-10-08-trading-coach]] |
| F1.12 | PTN | high | Q-PTN-01@INI-001 | Does the Brightwater agreement allow retail order placement, account linking and auto-trading? Who pays and who operates each of these, and does any ownership, operation or payment change for them? | "to fetch: the Brightwater API agreement, held by Partnerships" in [[2026-10-08-trading-coach]] |
| F1.13 | PTN | high | new | What do Brightwater's terms say on scope changes, termination notice and exclusivity? What would it cost to leave or to be refused, and who will contact Brightwater and when? | "Brightwater says no at the last minute to something we've already shipped—the quotes, or the account link, or the auto-trading piece." in [[2026-10-08-trading-coach]] |
| F1.14 | PTN | high | new | Who supplies the quotes, under what agreement, and does it permit use in a product where users trade real money? What does it cost, and what is its notice period? | "Source and holder of that license or agreement were not named." in [[2026-10-08-trading-coach]] |
| F1.15 | PTN | normal | new | Is Brightwater willing and contractually able to build the order screen, or to cover the regulated part under its own license? Who would carry the liability and cost if it did? | "What if Brightwater's team built the order screen, since they already run the broker side, and TickerTalk built only the teaching?" in [[2026-10-08-trading-coach]] |
| F1.16 | PTN | normal | new | What API rate limits, sandbox limits, uptime commitments and user caps does Brightwater's agreement set, and do they fit a launch to a small cohort versus all 400k users? | "the broker's sandbox can't handle it or the API falls over when real orders start flowing" in [[2026-10-08-trading-coach]] |
| F1.17 | PTN | normal | new | Who will fetch and record the Brightwater agreement, the quotes license and the TickerTalk terms in sources, and by what date? Who will brief Partnerships, which has not been told? | "No, haven't talked to counsel or Brightwater yet." in [[2026-10-08-trading-coach]] |
| F1.18 | REG | high | Q-REG-02@INI-001 | Is placing or recommending trades regulated or licensed (adviser or broker registration, for example)? Who will confirm this in writing, counsel or the regulator, before design commits? | "if we call this education not advice we don't need registration, but I could be wrong" in [[2026-10-08-trading-coach]] |
| F1.19 | REG | high | Q-REG-01@INI-001 | Will the coach be offered on its own, or as a joint or bundled offer with Brightwater? Whose license would cover which part? | "What if Brightwater's own license covered the regulated part, and the coach lived inside their permissions instead of TickerTalk holding its own?" in [[2026-10-08-trading-coach]] |
| F1.20 | REG | high | Q-REG-05@INI-001 | If Signal's picks lose money, or Brightwater's API or the coach fails, who is liable to the customer: TickerTalk, Brightwater or both? What does the Brightwater agreement say? | "Signal's backtest was too good—it overfits and loses money on real money and we're liable." in [[2026-10-08-trading-coach]] |
| F1.21 | REG, OPS | high | new | Who has authority to stop a launch if compliance sign-off is not done, and is sign-off a recorded constraint on the March date? | "Compliance sign-off takes until February and we ship anyway because the demo date is sacred." in [[2026-10-08-trading-coach]] |
| F1.22 | REG | high | new | Which reading of 'trades for them' does the CEO intend, and which regulatory category does each reading fall under? | "The CEO's one-liner doesn't say what 'trades for them' means—is it placing orders the model picked, or just coaching through it, or something else?" in [[2026-10-08-trading-coach]] |
| F1.23 | REG | normal | new | Who holds TickerTalk's user terms and privacy notice, and do they allow reuse of user data for a trading product or sharing with Brightwater? Is options coaching planned when Signal covers stocks only? | "to fetch: TickerTalk's user terms and privacy notice, holder not named; the product lead did not say who holds them." in [[2026-10-08-trading-coach]] |
| F1.24 | OPS | high | new | Who builds, runs and supports the coach after launch, including out of hours when real orders flow? Is it a new team or people pulled from existing teams? | "I don't know if we're adding a new team or pulling from somewhere." in [[2026-10-08-trading-coach]] |
| F1.25 | OPS | high | Q-OPS-05@INI-001 | If mobile and ML people are pulled onto the coach, what do they stop doing, and who still depends on that work (the news app, Signal)? | "The mobile team burns out because I'm pulling people and TickerTalk breaks and the CEO blames me." in [[2026-10-08-trading-coach]] |
| F1.26 | OPS | high | Q-OPS-06@INI-001 | Who is affected and not yet in the room (mobile, ML, Partnerships, compliance, counsel, Brightwater, the CFO, editors, support, readers), and who tells each of them and when? | "”Nobody's been told yet.” Mobile, ML, Partnerships and compliance have not been told of the ask." in [[2026-10-08-trading-coach]] |
| F1.27 | OPS | high | Q-OPS-07@INI-001 | If the education-not-advice belief is wrong, what happens to the plan? Who can confirm it before the pitch, and what would the plan do if registration is required? | "Belief with no source: ”if we call this education not advice we don't need registration, but I could be wrong”." in [[2026-10-08-trading-coach]] |
| F1.28 | OPS | high | Q-OPS-07@INI-001 | Which unsupported belief (Signal's backtest, Brightwater limits and permissions, the education-not-advice line, the budget) would change the plan most if wrong, and who holds the evidence? | "Signal's backtest was too good—it overfits and loses money on real money and we're liable." in [[2026-10-08-trading-coach]] |
| F1.29 | OPS | normal | new | Who owns the coach after the pitch, and who can settle what 'trades for them' means so the CEO does not change it midway? | "”CEO decides, but I'd be the one to pitch it.”" in [[2026-10-08-trading-coach]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| G1 | - | inkling | [[2026-10-08-trading-coach#^c01]] |
| UNK-001 | - | open | [[2026-10-08-trading-coach#^c03]] |
| UNK-002 | - | open | [[2026-10-08-trading-coach#^c04]] |
| UNK-003 | - | open | [[2026-10-08-trading-coach#^c19]] |
| UNK-004 | - | open | [[2026-10-08-trading-coach#^c20]] |
| UNK-005 | - | open | [[2026-10-08-trading-coach#^c21]] |
| UNK-006 | - | open | [[2026-10-08-trading-coach#^c22]] |
| UNK-007 | - | open | [[2026-10-08-trading-coach#^c49]] |
| UNK-008 | - | open | [[2026-10-08-trading-coach#^c50]] |
| UNK-009 | - | open | [[2026-10-08-trading-coach#^c30]] |
| UNK-010 | - | open | [[2026-10-08-trading-coach#^c24]] |
| UNK-011 | - | open | [[2026-10-08-trading-coach#^c40]] |
| UNK-012 | - | open | [[2026-10-08-trading-coach#^c44]] |
| UNK-013 | - | open | [[2026-10-08-trading-coach#^c64]] |
| Q-PTN-01@INI-001 | - | unknown | [[2026-10-08-trading-coach#^c52]] |
| Q-REG-02@INI-001 | - | unknown | [[2026-10-08-trading-coach#^c52]] |
| Q-OPS-07@INI-001 | - | assumed | [[2026-10-08-trading-coach#^c52]] |
| R-FIN-01 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-FIN-02 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-FIN-03 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-DAT-01 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-DAT-02 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-PTN-01 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-PTN-02 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-PTN-03 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-PTN-04 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-PTN-05 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-REG-01 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-REG-02 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-REG-03 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-OPS-01 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
| R-OPS-02 | - | open | [[2026-10-08-trading-coach#1. After the pre-mortem, 2026-10-08]] |
