---
id: 2026-10-08-first-release-boundary
type: session
title: "Boundary: first release boundary"
date: 2026-10-08
modes: [boundary]
status: closed
summary: "Boundary: first release cut into Coach (new) and TickerTalk (changed) with CON-001 and CON-002, all assumption; six Brightwater and TickerTalk unknowns opened; review digest deferred."
---

# 2026-10-08 Boundary: first release boundary

## Captures

- [thought] (claude) Cut A, "Coach app behind TickerTalk": Coach is new and owns lessons, paper practice and the board demo's trade ideas; TickerTalk is changed and only hosts the way in; Brightwater and Quoteline stay outside with their contracts on Coach's page; Signal is not touched in release one. Easy: the news app stays clear of regulated content, and the coach has one owner to name. Hard: a new app to run, and the board-only gate lives inside Coach. Rests on [[04-solution-strategy#First release|First release]] (decided), SRC-01 (paper accounts, section 7.2), SRC-02 (delayed quotes in Kestrel's own apps). Whether TickerTalk is a Kestrel app is open, [[11-unknowns-and-risks#UNK-017 Whose Brightwater link|UNK-017]]. → park ^c01
- [thought] (claude) Cut B, "Coach built into TickerTalk": only TickerTalk changes; lessons, paper practice and demo ideas are modules of it. Easy: no new app, and 400,000 users and sign-in already exist (the product lead, no source). Hard: lands on the mobile team, which is on the news app (the product lead, no source); a coach fault can hit the news app; the private demo and the user release share one app, so keeping customers out of the demo is harder. Rests on [[04-solution-strategy#First release|First release]] (decided) and the product lead's account of the teams. → park ^c02
- [thought] (claude) Cut C, "Coach, a separate board-demo app and Signal as idea source": Coach (new) for users, Board demo (new) for the private January showing, TickerTalk (changed), Signal (changed, serves trade ideas). Easy: no customer can reach the demo, and the demo has its own owner. Hard: two new apps; Signal's place is undecided ("Signal later", [[2026-10-08-first-instruments-signal#^c28]]); Signal covers fifty large caps (SRC-03) and where its price data came from is open, [[11-unknowns-and-risks#UNK-020 Source of Signal's price data and clause 9|UNK-020]]; the ML team is three people (the product lead, no source). Rests on [[04-solution-strategy#First release|First release]] (decided) and SRC-03. → park ^c03
- [thought] (claude) Preferred cut: A. It keeps the news app apart from content Brightwater must approve (SRC-01 section 7.2), gives the coach one place to be owned, and leaves Signal's place to its own decision instead of settling it here. B is cheaper but puts the whole coach on the mobile team. C settles Signal and a second app before either is decided. → park ^c04
- [thought] (product lead) "A." Picks Cut A, Coach app behind TickerTalk. → keep: [[05-building-blocks#Coach app behind TickerTalk|cut]] (assumption) ^c05
- [thought] (product lead) On Cut B: "B drowns mobile, they're already maxed." Rejected: the mobile team has no room (the product lead, no source). → keep: [[05-building-blocks#Coach app behind TickerTalk|cut]] (assumption) ^c06
- [thought] (product lead) On Cut C: "C's too many apps before we know what Brightwater allows." Rejected: too many apps before the Brightwater agreement is read. → keep: [[05-building-blocks#Coach app behind TickerTalk|cut]] (assumption) ^c07
- [thought] (product lead) "Reading that agreement tomorrow." The product lead reads the Brightwater agreement on 2026-10-09; it bears on [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]]. → drop: held in the Notes of UNK-027 and UNK-028 ^c08
- [thought] (product lead) Coach sheet read back: "Yes on 1a through 2f, yes on 3a through 4a, yes on 5a, 5b, 6a, 6b, and 7a through 7e." Written as the Coach app page: opening paragraphs, containers (all assumption), CON-001 and CON-002 as the contracts, and concern cells unknown on Data, Rollout, Ownership and Cost, unexamined on the rest. Added to the apps in scope. → keep: [[coach-building-blocks#Coach|APP-coach]] (assumption) ^c09
- [thought] (product lead) Runtime page for Coach from lines 6a and 6b. → keep: [[coach-runtime#On failure|RUN-coach]] (assumption) ^c10
- [thought] (product lead) Line 4a, the contract Coach provides to TickerTalk. → keep: [[coach-building-blocks#CON-001 Coach entry|CON-001]] (assumption) ^c11
- [thought] (product lead) Line 5a, the contract Coach consumes from Quoteline, with a Provider bullet. → keep: [[coach-building-blocks#CON-002 Delayed quotes|CON-002]] (assumption) ^c12
- [thought] (product lead) On the Brightwater lines: "yes, all three as unknowns, @sim-lead asking Partnerships by the sixteenth." Paper practice and Brightwater accounts. → keep: [[11-unknowns-and-risks#UNK-027 Paper practice and Brightwater accounts|UNK-027]] (open) ^c13
- [thought] (product lead) Section 7.2 approval of the lessons, as an unknown, same owner and date. → keep: [[11-unknowns-and-risks#UNK-028 Section 7.2 approval of lessons|UNK-028]] (open) ^c14
- [thought] (product lead) Source of the demo's trade ideas, as an unknown, same owner and date. The product lead named Partnerships for all three; I wrote it as given and noted the ML team may be the right answerer. → keep: [[11-unknowns-and-risks#UNK-029 Source of the demo's trade ideas|UNK-029]] (open) ^c15
- [thought] (product lead) "Change UNK-029 to the ML lead." The answer for UNK-029 comes from the ML lead, not Partnerships. → keep: [[11-unknowns-and-risks#UNK-029 Source of the demo's trade ideas|UNK-029]] (open) ^c16
- [thought] (product lead) TickerTalk sheet read back: "Yes on 1a through 7c." Written as the TickerTalk app page: opening paragraphs, the Coach entry container (assumption), no contract provided, CON-001 consumed, and concern cells unknown on Data, Rollout and Ownership, unexamined on the rest. Added to the apps in scope. → keep: [[tickertalk-building-blocks#TickerTalk|APP-tickertalk]] (assumption) ^c17
- [thought] (product lead) Runtime page for TickerTalk from lines 6a and 6b. → keep: [[tickertalk-runtime#On failure|RUN-tickertalk]] (assumption) ^c18
- [thought] (product lead) On line 3b: "mobile has those containers—ask them." Written as an unknown; the ask-by date is claude's proposal. → keep: [[11-unknowns-and-risks#UNK-030 TickerTalk existing containers|UNK-030]] (open) ^c19
- [thought] (product lead) On line 5b: "yes as unknown, same owner and date as the other Brightwater ones." → keep: [[11-unknowns-and-risks#UNK-031 TickerTalk Brightwater link in release one|UNK-031]] (open) ^c20
- [thought] (product lead) On the review digest: "Defer till tomorrow." The digest is not taken today; every line stays open. → park ^c21
- [thought] (product lead) R-REG-06, R-OPS-11, R-PTN-14: "Mobile's bandwidth and the legal entity question matter before I pitch." Mobile's room for the Coach entry (F1.48, UNK-009) and whether TickerTalk or Kestrel holds the Brightwater link and fronts customers (F1.31 and F1.38, UNK-017) are the two the product lead wants before the pitch, the CEO conversation on 2026-10-09 ([[04-solution-strategy#For the pitch|For the pitch]]). Neither is answered; their ask-by dates, 2026-10-23 and 2026-10-16, fall after it. → keep: [[11-unknowns-and-risks#Question ledger|R-REG-06]] (unknown) ^c22
- [thought] (product lead) waits on UNK-004: Q-PTN-03@PTY-01, Q-PTN-06@PTY-01, R-PTN-04; waits on UNK-028: R-PTN-10, R-REG-15; waits on UNK-024: R-PTN-03. The product lead said "Everything else hinges on the agreement." Only the lines that plainly depend on the Brightwater agreement are linked; the others stay undisposed. → keep: [[11-unknowns-and-risks#Question ledger|R-PTN-04]] (unknown) ^c23

## Reviews

### 1. after the pages are written, 2026-10-08

- **Coverage:** FIN found 8, 2 dropped; DAT found 11, 1 dropped; PTN found 14, 1 dropped; REG found 8; OPS found 15, 1 dropped
- **Dropped:** [FIN] its quote ”Brightwater holds (SRC-01)” has fewer than 4 words, too few to show where it came from: Is there any conversion between paper and real holdings? If so, who sets the rate and who approves it? If not, will the plan say there is none?; [FIN] the quote does not mention what the finding is about: What do cuts A, B and C each cost to build and run, and on what costing was A picked?; [DAT] it names R-DAT-03, which this vault does not owe and has no open reviewer question for; write new for a question of your own: What user data does TickerTalk already send to Brightwater, and what do the agreement's data-sharing and consent clauses allow for release one?; [PTN] its quote ”**Provider:** Quoteline ([[03-context-and-scope#PTY-02 Quoteline|PTY-02]])” has fewer than 4 words, too few to show where it came from: Does the Quoteline licence allow assignment or a change of control, and does it permit use in a product where users trade real money?; [OPS] the quote does not mention what the finding is about: Is anything retired or replaced by release one? If nothing, should the plan say so, and who still depends on anything it changes in TickerTalk?
- **Merged:** [DAT] into F1.7: If paper practice uses Brightwater sandbox accounts, what user data goes to Brightwater, and does the agreement allow it and cap sandbox users?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | Is any balance Coach keeps, such as a paper cash balance or progress, treated as value held for customers? If it is not, will the plan say so? | "holds no customer money, which Brightwater holds (SRC-01)" in [[coach-building-blocks]] |
| F1.2 | FIN | high | Q-FIN-02@INI-001 | Who funds the build of Coach and the TickerTalk entry, and which team's budget carries the running cost once they are live? | "[[11-unknowns-and-risks#UNK-007 CFO 2.5 million budget\|UNK-007]]: what the budget covers" in [[concern-cost]] |
| F1.3 | FIN | normal | Q-FIN-04@SV-01 | If paper balances live in Coach's ledger or in Brightwater's sandbox, how do they relate to a real Brightwater balance when real orders arrive in release two? | "Does paper practice use Brightwater's sandbox paper accounts (SRC-01 says they exist), or Coach's own simulated ledger?" in [[11-unknowns-and-risks]] |
| F1.4 | FIN | normal | Q-FIN-05@SV-01 | What happens to a user's paper positions and progress at closure or expiry, and who decides? | "It keeps each user's lesson progress and paper positions; where they are kept is not decided." in [[coach-building-blocks]] |
| F1.5 | FIN | high | R-FIN-08 | Does Coach's use of delayed quotes need a Quoteline addendum? If it does, what does it cost, and who pays? | "Whether lessons and practice count as display is open" in [[coach-building-blocks]] |
| F1.6 | FIN | high | new | Who funds and staffs the running of Coach, including out of hours, and is that cost inside the 2.5 million? | "Hard: a new app to run, and the board-only gate lives inside Coach." in [[2026-10-08-first-release-boundary]] |
| F1.7 | FIN, DAT | normal | R-DAT-06 | Does Brightwater charge for sandbox accounts or API calls for paper practice, and who pays? | "If Brightwater's, what user data goes to it, and is there a limit on sandbox users?" in [[11-unknowns-and-risks]] |
| F1.8 | FIN | high | R-FIN-11 | Does the 2.5 million budget cover only the first release or both, and has the CFO accepted the narrower first release? | "real orders are release two, and Brightwater keeps the execution (SRC-01)" in [[coach-building-blocks]] |
| F1.9 | DAT | high | Q-DAT-02@APP-coach | What customer data does Coach hold (user ID, progress, paper positions, any Brightwater account data), where is it stored, and on what lawful basis may Coach use it? | "It keeps each user's lesson progress and paper positions; where they are kept is not decided." in [[coach-building-blocks]] |
| F1.10 | DAT | high | Q-DAT-02@APP-tickertalk | What user data does TickerTalk hold, and do its terms and privacy notice allow it to pass the user ID to Coach and to Brightwater? | "it shows an entry and passes the signed-in user's ID (CON-001)." in [[tickertalk-building-blocks]] |
| F1.11 | DAT | normal | Q-DAT-03@CON-001 | Is the user ID that crosses CON-001 personal data, and were Coach and its purposes named in TickerTalk's notice when the ID was collected? | "in, the signed-in user's ID from TickerTalk and the request to open the coach; out, the lesson and practice screens." in [[coach-building-blocks]] |
| F1.12 | DAT | normal | Q-DAT-03@CON-002 | Does any customer or usage data cross to Quoteline, and does clause 9 permit showing quotes inside lessons and practice? | "Whether lessons and practice count as display is open," in [[coach-building-blocks]] |
| F1.13 | DAT | normal | Q-DAT-04@SV-01 | Which one system is the record of each customer's balance, and which system is the record of paper positions? | "**Owner:** not known yet, see [[11-unknowns-and-risks#UNK-018 Who owes customers their money\|UNK-018]]" in [[03-context-and-scope]] |
| F1.14 | DAT | normal | R-DAT-02 | Which app is the record of a user's progress, paper positions and consents, and how do they follow the user between TickerTalk, Coach and Brightwater? | "It keeps each user's lesson progress and paper positions" in [[coach-building-blocks]] |
| F1.15 | DAT | high | R-DAT-05 | What do TickerTalk's privacy notice and terms say, who holds them, and should UNK-006 block APP-coach, APP-tickertalk and CON-001? | "Who holds TickerTalk's user terms and privacy notice? The product lead did not say who holds them." in [[11-unknowns-and-risks]] |
| F1.16 | DAT | high | R-DAT-09 | Will the demo's trade ideas use any TickerTalk user data (watchlists, for example), and do the terms allow it? | "Where do the board demo's trade ideas come from? Signal's place is not decided, and nothing else is recorded as a source." in [[11-unknowns-and-risks]] |
| F1.17 | DAT | normal | new | What data does the board demo use, and how is customer data kept out of the board-only view? | "\| Board demo \| The trade-ideas view, behind a board-only gate \| CON-001 \| claude \| assumption \|" in [[coach-building-blocks]] |
| F1.18 | DAT | normal | new | Which app is the record of each kind of user data, and what is the retention and deletion rule for Coach's data? | "What each app stores, which app is the record, and what moves during the change." in [[concern-data]] |
| F1.19 | PTN | high | Q-PTN-03@PTY-01 | Has the Brightwater agreement been read in full, on which date, and who holds it? When does it end, and what does leaving or changing it cost? | "the full text is still to fetch" in [[03-context-and-scope]] |
| F1.20 | PTN | normal | Q-PTN-03@PTY-02 | Who holds the Quoteline licence, when does it end, what does it cost, and what does leaving it cost? Is Quoteline the quotes supplier, as CON-002 says, or is that still open under UNK-008? | "the full text has not been fetched" in [[03-context-and-scope]] |
| F1.21 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to the Quoteline licence need, and who must give it? | "the notice a change to the licence needs is open (Q-PTN-06@PTY-02)" in [[coach-building-blocks]] |
| F1.22 | PTN | normal | Q-PTN-06@PTY-01 | What notice does a change to the Brightwater agreement need, who gives it, and what are the terms on scope changes and termination? | "Does section 7.2 of the Brightwater agreement (SRC-01) need Brightwater's approval before Coach shows its lessons and practice, and how long does that take?" in [[11-unknowns-and-risks]] |
| F1.23 | PTN | high | R-PTN-02 | Is Quoteline the confirmed quotes supplier? Does the licence allow use where users trade real money, what does it cost, and what is its notice period? | "Source and holder of that agreement were not named." in [[11-unknowns-and-risks]] |
| F1.24 | PTN | normal | R-PTN-03 | Is Brightwater willing and contractually able to cover the regulated part under its own licence? Who would carry the liability and cost? | "Asked with UNK-014 as one ask, and settles the reviewer question R-PTN-03." in [[11-unknowns-and-risks]] |
| F1.25 | PTN | normal | R-PTN-04 | What API, sandbox, uptime and user-cap limits does the Brightwater agreement set, and do they fit a small cohort versus all 400k users? | "is there a limit on sandbox users?" in [[11-unknowns-and-risks]] |
| F1.26 | PTN | normal | R-PTN-05 | Who fetches and records the Brightwater agreement, the Quoteline licence and the TickerTalk terms, and by what date? Who briefs Partnerships before the 2026-10-16 asks? | "Mobile, ML, Partnerships and compliance are all unaware of the ask." in [[03-context-and-scope]] |
| F1.27 | PTN | normal | R-PTN-06 | How and when will Partnerships be told about the ask, given the 2026-10-09 dates and the 2026-10-16 dates on the new Brightwater unknowns? | "**Brightwater:** not yet contacted about this ask, per the product lead." in [[03-context-and-scope]] |
| F1.28 | PTN | high | R-PTN-07 | Did Signal's backtest or training use Quoteline data? If so, is Kestrel already outside the licence, and is an addendum needed before the demo's trade ideas rely on it? | "Signal's place is not decided, and nothing else is recorded as a source." in [[11-unknowns-and-risks]] |
| F1.29 | PTN | high | R-PTN-08 | Which definition of A, B and C is the plan's? Does each need Brightwater order placement and the account link, or only paper practice? | "Coach prepares or places no real order: real orders are release two, and Brightwater keeps the execution (SRC-01)." in [[coach-building-blocks]] |
| F1.30 | PTN | high | R-PTN-10 | What is the section 7.2 approval process, and can Brightwater refuse or withdraw approval? How does it fit the counsel sign-off timeline and the January demo? | "Does section 7.2 of the Brightwater agreement (SRC-01) need Brightwater's approval before Coach shows its lessons and practice" in [[11-unknowns-and-risks]] |
| F1.31 | PTN | high | new | Who is the contracting party on the Brightwater link, TickerTalk or Kestrel? Does the agreement allow Coach to use it? | "Brightwater: the product lead says TickerTalk has been on Brightwater's API since June (no source)." in [[tickertalk-building-blocks]] |
| F1.32 | PTN | normal | new | Who owns the partner relationships (Brightwater and Quoteline) for Coach? Does passing the user ID to Coach need any partner consent? | "**Change policy:** not decided; proposed (claude): Coach and TickerTalk owners agree any change to what crosses." in [[coach-building-blocks]] |
| F1.33 | REG | normal | Q-REG-01@INI-001 | Will Coach be presented to customers as a joint Kestrel and Brightwater offer, or as a Kestrel education tool only? If a part fails, who is liable to the customer? | "holds no customer money, which Brightwater holds (SRC-01)" in [[coach-building-blocks]] |
| F1.34 | REG | high | new | Does section 7.2 require Brightwater to approve Coach's lessons, practice and marketing? How long does approval take against the January demo and the March launch? Which of the session note and UNK-028 is right? | "content Brightwater must approve (SRC-01 section 7.2)" in [[2026-10-08-first-release-boundary]] |
| F1.35 | REG | high | new | Who builds and controls the board-only gate, and how is a customer kept out of the trade-ideas view? Has counsel confirmed that a private board demo of trade ideas is not a recommendation? Where do the ideas come from, and does clause 9 allow it? | "The trade-ideas view, behind a board-only gate" in [[coach-building-blocks]] |
| F1.36 | REG | high | R-REG-14 | Which counsel wrote SRC-06, and when? Who confirms that the review of marketing and shown results is done, and that paper trades taught as lessons count as education and not advice? | "counsel cleared lessons and paper" in [[04-solution-strategy]] |
| F1.37 | REG | high | R-REG-13 | Is release one now formally stocks only, so that the options course and the options-trading option are dropped or deferred? Which regulator and licence apply to the stock lessons and paper practice, and who confirms this with counsel? | "It teaches no ETFs and no options in release one" in [[coach-building-blocks]] |
| F1.38 | REG | high | R-REG-06 | Which legal entity holds the Brightwater agreement and is in front of customers when Coach opens from TickerTalk, Kestrel or TickerTalk? | "the product lead says TickerTalk has been on Brightwater's API since June (no source)" in [[tickertalk-building-blocks]] |
| F1.39 | REG | high | R-REG-02 | Under which regulatory category does the resolved reading, trade ideas that the user buys themselves, fall? Has counsel confirmed it? | "the user buys themselves" in [[coach-building-blocks]] |
| F1.40 | REG | high | R-REG-12 | Who performs the compliance read for Coach's lessons and practice, and who can hold the launch if sign-off is not done? | "when compliance signs off" in [[concern-rollout]] |
| F1.41 | OPS | high | Q-OPS-01@APP-coach | Who is on call for Coach, including out of hours, and what is the support route for a user whose lesson progress or paper positions go wrong? | "Who is on call, and the runbooks for the failures that hurt customers." in [[concern-operations]] |
| F1.42 | OPS | normal | Q-OPS-01@APP-tickertalk | Who watches and fixes the Coach entry in TickerTalk out of hours, and which team carries that duty? | "\| [[tickertalk-building-blocks\|TickerTalk]] \| unexamined \| - \|" in [[concern-operations]] |
| F1.43 | OPS | normal | Q-OPS-02@CON-001 | How does TickerTalk detect that Coach is down or slow, what counts as slow, and does the entry hide automatically or by hand? | "**Coach down:** TickerTalk hides the entry, and the news app is unaffected." in [[coach-runtime]] |
| F1.44 | OPS | normal | Q-OPS-02@CON-002 | What do the board demo and the quote display do when Quoteline is down or slow, and what availability or latency does the licence promise? | "**Quoteline down or slow:** practice pauses and lessons go on." in [[coach-runtime]] |
| F1.45 | OPS | normal | Q-OPS-04@INI-001 | Is more than one system or team doing the same job here, for example Brightwater sandbox accounts and a Coach ledger, or two sign-in and ID stores? Which one is the single source? | "Does paper practice use Brightwater's sandbox paper accounts (SRC-01 says they exist), or Coach's own simulated ledger?" in [[11-unknowns-and-risks]] |
| F1.46 | OPS | high | Q-OPS-06@INI-001 | Who is affected and not yet in the room, such as mobile, support, compliance and Partnerships, and when will each be told? | "**Who knows:** nobody has been told yet. Mobile, ML, Partnerships and compliance are all unaware of the ask." in [[03-context-and-scope]] |
| F1.47 | OPS | high | R-OPS-02 | Which named person or team owns Coach, and who has authority to settle its scope so it is not changed midway? | "the coach has one owner to name" in [[2026-10-08-first-release-boundary]] |
| F1.48 | OPS | high | new | Who builds the TickerTalk entry and CON-001 under Cut A, and has mobile confirmed it has room for even that smaller change? | "B drowns mobile, they're already maxed" in [[05-building-blocks]] |
| F1.49 | OPS | normal | R-OPS-04 | Does teach-only meet the CEO's goal, and what evidence is there that readers will use a coach that earns nothing? | "shows no trade ideas to customers (SRC-06)" in [[coach-building-blocks]] |
| F1.50 | OPS | normal | R-OPS-05 | Who confirms the Quoteline licence summary against the full text, and by when? | "the full text has not been fetched" in [[03-context-and-scope]] |
| F1.51 | OPS | normal | R-OPS-06 | Which of the three documents has arrived, who is chasing each, and is SRC-03 the full backtest? | "Whether it is the ML team's summary or the full backtest is not known; the product lead will find out, 2026-10-08." in [[11-unknowns-and-risks]] |
| F1.52 | OPS | high | R-OPS-10 | Who is the named owner and answerer for each blocking unknown (UNK-019, UNK-011, UNK-029 and the rest), and by what date? | "The ML lead has no handle recorded, so the owner stays the product lead." in [[11-unknowns-and-risks]] |
| F1.53 | OPS | high | new | Has the product lead read the full Brightwater agreement, on 2026-10-08 or not yet? If so, should UNK-027 and UNK-028 be answered or reworded? | "the product lead expects to answer this after reading the agreement on 2026-10-09" in [[11-unknowns-and-risks]] |
| F1.54 | OPS | normal | new | Where are progress and paper positions kept, who restores them after a failure, and what happens if a user ID changes or TickerTalk sign-in fails? | "where they are kept is not decided" in [[coach-building-blocks]] |
| F1.55 | OPS | normal | new | Who administers the board-only gate, who runs the January demo, and what is the fallback if it fails live? | "The trade-ideas view, behind a board-only gate" in [[coach-building-blocks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| APP-coach | - | inkling | [[2026-10-08-first-release-boundary#^c05]] |
| APP-tickertalk | - | inkling | [[2026-10-08-first-release-boundary#^c05]] |
| APP-coach | inkling | assumption | [[2026-10-08-first-release-boundary#^c09]] |
| RUN-coach | - | assumption | [[2026-10-08-first-release-boundary#^c10]] |
| CON-001 | - | assumption | [[2026-10-08-first-release-boundary#^c11]] |
| CON-002 | - | assumption | [[2026-10-08-first-release-boundary#^c12]] |
| UNK-027 | - | open | [[2026-10-08-first-release-boundary#^c13]] |
| UNK-028 | - | open | [[2026-10-08-first-release-boundary#^c14]] |
| UNK-029 | - | open | [[2026-10-08-first-release-boundary#^c15]] |
| APP-tickertalk | inkling | assumption | [[2026-10-08-first-release-boundary#^c17]] |
| RUN-tickertalk | - | assumption | [[2026-10-08-first-release-boundary#^c18]] |
| UNK-030 | - | open | [[2026-10-08-first-release-boundary#^c19]] |
| UNK-031 | - | open | [[2026-10-08-first-release-boundary#^c20]] |
| R-FIN-14 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-DAT-11 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-DAT-12 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-PTN-13 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-REG-16 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-OPS-12 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-OPS-13 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-OPS-14 | - | open | [[2026-10-08-first-release-boundary#1. after the pages are written, 2026-10-08]] |
| R-REG-15 | - | unknown | [[2026-10-08-first-release-boundary#^c23]] |
| R-OPS-11 | - | unknown | [[2026-10-08-first-release-boundary#^c22]] |
| R-PTN-14 | - | unknown | [[2026-10-08-first-release-boundary#^c22]] |
| Q-PTN-03@PTY-01 | - | unknown | [[2026-10-08-first-release-boundary#^c23]] |
| Q-PTN-06@PTY-01 | - | unknown | [[2026-10-08-first-release-boundary#^c23]] |
| R-REG-06 | open | unknown | [[2026-10-08-first-release-boundary#^c22]] |
| R-PTN-10 | open | unknown | [[2026-10-08-first-release-boundary#^c23]] |
| R-PTN-03 | open | unknown | [[2026-10-08-first-release-boundary#^c23]] |
| R-PTN-04 | open | unknown | [[2026-10-08-first-release-boundary#^c23]] |
