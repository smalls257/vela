---
id: 2026-10-09-signal-model-backtest
type: session
title: "Discover: signal model backtest"
date: 2026-10-09
modes: [discover, dump]
status: closed
summary: "Signal's backtest, the Quoteline clause 9 question and who feeds Signal, folded into UNK-014 for the ML team and due 2026-10-23"
---

# 2026-10-09 Discover: signal model backtest

## Captures

- [thought] (product lead) "Nothing new on my end—check with the ML team." No new document has arrived; the ML team is the one to ask. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c01
- [thought] (product lead) "Yes through 10." Lines 1 to 10 on Signal's backtest, the Quoteline licence and the CEO memo are confirmed; each is already written from earlier sessions, so nothing new is written. → drop: already on 01-goals, 03-context-and-scope and UNK-013 and UNK-014 ^c02
- [thought] (product lead) "Line 11's right." The CEO memo calls Signal the company's edge. → keep: [[01-goals#Goals|G1]] (inkling) ^c03
- [unknown] (claude, from product lead) No source says what data feeds Signal, so clause 9 may reach Signal itself. "Fold inputs into the watchlist question—one ask to the ML team on what feeds Signal and what the licensing means for it." to fetch: what feeds Signal and the licensing view, held by the ML team. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c04
- [thought] (product lead) F1.24: "Clause 9 is the load-bearing question." A belief, not sourced; close asks whether it is load-bearing. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c05
- [unknown] (product lead) F1.14, F1.24: "Is Signal already in breach with what feeds it today, or only if we train on watchlists? Because I need to know if I'm walking into the CEO with a dead backtest or not. Who reads the full license and when does that answer land?" to fetch: what feeds Signal, held by the ML team, and the full Quoteline licence, held by the data engineer who summarised it. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c06
- [thought] (product lead) F1.24, F1.33: "Move UNK-014 to 10-23, same as the licence read." Ask-by of UNK-014 moves from 2026-11-13 to 2026-10-23. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c07
- [thought] (product lead) "I'll grab the documents from the data engineer this week and get the ML team's answer on what feeds Signal by then." A plan of the lead's own, not a fact; the data engineer as holder of the full licence is the lead's statement. → keep: [[11-unknowns-and-risks#UNK-015 Two clauses to read in full|UNK-015]] (open) ^c08
- [thought] (product lead) "Can't walk into the CEO without knowing if the model already broke the contract." A belief about what blocks the CEO conversation; close asks whether it is load-bearing. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c09
- [thought] (product lead) "All of that's in there. Done." Taken as: the six gaps Claude listed are what the documents do not say, and the lead adds nothing more. → drop: the lead added no gap of their own; the gaps below are Claude's ^c10
- [unknown] (claude, from product lead) The backtest does not say what Signal is, what it reads or how it picks; no source says who owns, maintains or retrains it. The lead keeps it: nobody knows who owns Signal after launch, which matters for handoff. → keep: [[11-unknowns-and-risks#UNK-020 Who owns Signal after launch|UNK-020]] (open) ^c11
- [unknown] (claude, from product lead) The backtest does not say whether data was held out of sample, what the 11% index is measured against, or what daily long-short trading would cost once transaction costs are counted. → drop: Claude's own; the baseline part is already UNK-013 ^c12
- [unknown] (claude, from product lead) No source gives a live or paper track record for Signal. → drop: Claude's own; the worry that backtests mislead is already R-04 ^c13
- [unknown] (claude, from product lead) The memo does not say whether customers would see Signal's 31% figure, or who signs off on such a claim. → drop: Claude's own; same ground as F1.31 on the digest ^c14
- [thought] (product lead) F1.25: "date moved but we still don't know if options data in Quoteline's a blocker." The question of who reads the licence stays open after the ask-by move. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c15

## Reviews

### 1. After the read-back, 2026-10-09

- **Coverage:** FIN found 9, 2 dropped; DAT found 6, 1 dropped; PTN found 11, 1 dropped; REG found 7; OPS found 6, 2 dropped
- **Dropped:** FIN: Q-FIN-06@SV-01, its quote has fewer than 4 words ("If a balance converts, who sets the rate and who approves it?"); FIN: R-FIN-07, the quote does not mention what the finding is about; DAT: a new question about the Brightwater data terms, on a page this session did not change; PTN: Q-PTN-05@PTY-02, the quote does not mention what the finding is about; OPS: Q-OPS-04@INI-001, the quote does not mention what the finding is about; OPS: Q-OPS-05@INI-001, the quote does not mention what the finding is about
- **Merged:** [DAT] into F1.8: Does the Quoteline licence let the coach or Signal use its data for anything beyond display, and is an addendum needed? Who reads clause 9 in full, and by when?; [REG] into F1.24: If clause 9 reaches Signal's current inputs, is Signal already in breach of the Quoteline licence? Is the addendum needed before any model use, and not only before the watchlist step?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-03@SV-01 | Who carries the balances Brightwater holds as money owed to customers: Brightwater, TickerTalk or another party? Who will get this from the signed agreement? | "who carries the balances as owed to customers is not recorded" in [[03-context-and-scope]] |
| F1.2 | FIN | normal | Q-FIN-04@SV-01 | If a reader moves between the sandbox paper account and a real Brightwater account, or between options, does any balance convert, and who handles it? | "Brightwater holds the money customers put in, and TickerTalk holds none" in [[03-context-and-scope]] |
| F1.3 | FIN | normal | Q-FIN-05@SV-01 | What happens to a reader's balance at Brightwater if the account closes or expires, or if the coach is withdrawn? | "**Owner:** not known yet" in [[03-context-and-scope]] |
| F1.4 | FIN | high | R-FIN-02 | Who carries the financial liability if readers lose money following the coach, and is any legal, registration or insurance cost budgeted? | "Readers may lose money following the coach's recommendations, and TickerTalk could be sued." in [[11-unknowns-and-risks]] |
| F1.5 | FIN | normal | R-FIN-03 | What would registration or licensing cost, and does the allocated budget cover it? | "which would need registration and turn the product into a year of legal work" in [[11-unknowns-and-risks]] |
| F1.6 | FIN | normal | R-FIN-04 | Does the budget assume orders through a broker, and who pays broker integration and fees if so? | "its amount, its holder and what it covers are not recorded" in [[11-unknowns-and-risks]] |
| F1.7 | FIN | normal | R-FIN-05 | Which price feed would the coach and Signal use, does the delayed display licence cover it, and who pays if not? | "No source says what data feeds Signal today, so it is also unknown whether Signal's own inputs fall under that clause." in [[11-unknowns-and-risks]] |
| F1.8 | FIN, DAT | high | R-DAT-02 | If Signal or watchlist training needs the Quoteline non-display addendum, what does it cost, who pays, and is it inside the budget? | "bars non-display use of its data, including models and derived data, without a separate addendum" in [[11-unknowns-and-risks]] |
| F1.9 | FIN | normal | new | What is Signal's return after transaction costs, and who bears trading or running costs if the gross figure is used for the goal? | "entering at each day's close and leaving out transaction costs" in [[01-goals]] |
| F1.10 | DAT | high | Q-DAT-01@INI-001 | Will any data, including watchlists or Signal's inputs, go to a new party? If so, who is that party and on what basis? | "The ML team wants to train on TickerTalk users' watchlists next, but the product lead says that is a wish and not a committed step." in [[01-goals]] |
| F1.11 | DAT | high | Q-DAT-05@INI-001 | What were users told when their watchlists were collected, and does that cover training Signal? Is a new consent or another lawful basis needed? | "names training on TickerTalk users' watchlists as the ML team's next step" in [[11-unknowns-and-risks]] |
| F1.12 | DAT | normal | R-DAT-02 | Does the licence's definition of TickerTalk's own apps cover the coach, and does it allow showing quotes inside simulated trading? | "lets TickerTalk's own apps display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.13 | DAT | normal | Q-DAT-04@SV-01 | Which one system is the record of each customer's balance, and where does a paper balance live, in Brightwater's sandbox or in TickerTalk? | "Brightwater holds the money customers put in, and TickerTalk holds none" in [[03-context-and-scope]] |
| F1.14 | DAT | high | new | What data trains and feeds Signal today, who collected it, and is it licensed for that use? Can this be answered before the January demo, not after 13 November? | "No source says what data feeds Signal, so clause 9 may reach Signal itself." in [[2026-10-09-signal-model-backtest]] |
| F1.15 | PTN | high | Q-PTN-02@PTY-01 | What does the signed Brightwater agreement say about sharing data with a new owner or user? Who will read it and report? | "are not recorded, including consent, data, notice, exit and any limit on live trading" in [[11-unknowns-and-risks]] |
| F1.16 | PTN | high | Q-PTN-02@PTY-02 | Does the Quoteline licence let TickerTalk share its data, or data derived from it, with a new owner or user? Does that need the separate addendum? | "bars non-display use of its data, including models and derived data, without a separate addendum" in [[11-unknowns-and-risks]] |
| F1.17 | PTN | normal | Q-PTN-03@PTY-01 | When does the Brightwater agreement end, who holds it by name, and what does leaving or changing it cost? | "the signed broker agreement, June (year not recorded), held by the partnerships manager" in [[03-context-and-scope]] |
| F1.18 | PTN | normal | Q-PTN-03@PTY-02 | Who holds the Quoteline licence, when does it end, and what does leaving or changing it cost? | "the Quoteline market data licence, summarised by the data engineer in March 2026" in [[03-context-and-scope]] |
| F1.19 | PTN | normal | Q-PTN-06@PTY-01 | What notice does a change to the Brightwater agreement need, and who must give it? | "are not recorded, including consent, data, notice, exit and any limit on live trading" in [[11-unknowns-and-risks]] |
| F1.20 | PTN | normal | Q-PTN-06@PTY-02 | What notice or process does a change to the Quoteline licence need, and who must give it? | "without a separate addendum" in [[11-unknowns-and-risks]] |
| F1.21 | PTN | normal | R-PTN-02 | What service levels and volume limits does the Brightwater API agreement give, and do they fit the coach's expected volume? | "The broker's API may not scale to the coach's volume." in [[11-unknowns-and-risks]] |
| F1.22 | PTN | normal | R-PTN-04 | Do the TickerTalk readers' terms or any other licence limit training a model on users' watchlists? If so, add it to sources. | "The ML team wants to train on TickerTalk users' watchlists next" in [[01-goals]] |
| F1.23 | PTN | high | R-PTN-05 | Is 15-minute-delayed display data acceptable for a coach that places orders, and does the licence allow its quotes to drive coaching or order decisions? | "a licence that lets TickerTalk's own apps display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.24 | PTN, REG | high | new | What data feeds Signal today, and does Quoteline clause 9 reach Signal? Who will read the full licence, and is an addendum needed before the January demo or March launch? | "No source says what data feeds Signal today, so it is also unknown whether Signal's own inputs fall under that clause." in [[11-unknowns-and-risks]] |
| F1.25 | PTN | normal | new | Who reads the full Quoteline licence and gives the licensing view: the ML team, the data engineer, or counsel? Should the 2026-11-13 ask date move earlier than the 2026-10-23 clause reading? | "The ML team holds what feeds Signal, and the product lead puts that and the licensing question to them as one ask." in [[11-unknowns-and-risks]] |
| F1.26 | REG | normal | Q-REG-01@INI-001 | Will the coach be sold or promised to customers as one offer that combines TickerTalk, Brightwater's brokerage and Quoteline data, or as separate things? | "a coach that teaches people to trade one stock or option at a time, and trades for them when they are ready" in [[01-goals]] |
| F1.27 | REG | high | Q-REG-05@INI-001 | If the coach's suggestion, the Brightwater order or the Quoteline price fails or misleads, who is liable to the customer: TickerTalk, Brightwater or Quoteline? What do the agreements say? | "Readers may lose money following the coach's recommendations, and TickerTalk could be sued." in [[11-unknowns-and-risks]] |
| F1.28 | REG | normal | R-REG-02 | What date does compliance's year one start from, and when does the ban end? | "It is not recorded whether compliance's year one runs from March, from today or from another date." in [[11-unknowns-and-risks]] |
| F1.29 | REG | high | R-REG-06 | Who in legal will rule in writing whether suggested or automatic trades are investment advice, and can that ruling arrive before the January demo? | "Whether a coach's lessons or recommendations count as investment advice is known only from what people said in meetings, and the owner in legal is not known." in [[11-unknowns-and-risks]] |
| F1.30 | REG | high | R-REG-07 | Is TickerTalk or Brightwater licensed to place orders on a customer's behalf without a tap, and what must the opt-in and audit trail satisfy? | "The product lead adds that nothing regulated goes live before counsel and Brightwater sign off." in [[02-constraints]] |
| F1.31 | REG | normal | new | Who must approve any customer-facing or board-facing statement of Signal's performance, and does compliance or legal require hypothetical-performance disclosures for a backtest like this? | "The memo also calls Signal the company's edge, which is the CEO's expectation and not something the backtest shows." in [[01-goals]] |
| F1.32 | OPS | normal | Q-OPS-06@INI-001 | Who is affected but not in the room, such as the ML team contact and TickerTalk readers whose watchlists would be used, and who wants something different from the coach? | "names training on TickerTalk users' watchlists as the ML team's next step" in [[11-unknowns-and-risks]] |
| F1.33 | OPS | normal | new | Who on the ML team will answer UNK-013 and UNK-014, and should the two asks share one date, given that UNK-013 is due 2026-10-30 and UNK-014 2026-11-13? | "The ML team holds what feeds Signal, and the product lead puts that and the licensing question to them as one ask." in [[11-unknowns-and-risks]] |
| F1.34 | OPS | normal | new | Is training on users' watchlists planned or only wished for, and who would approve and run it? | "The ML team wants to train on TickerTalk users' watchlists next, but the product lead says that is a wish and not a committed step." in [[01-goals]] |
| F1.35 | OPS | high | R-OPS-02 | Who in compliance will rule in writing on partner-broker orders, and by when, given the January demo? | "the product lead cannot yet name the compliance person who holds it" in [[11-unknowns-and-risks]] |
| F1.36 | OPS | high | R-OPS-03 | Which teams and named people build and run the order path, opt-in and audit trail, and does the mobile team have capacity next to TickerTalk itself? | "The mobile lead, who is not named, has to confirm that the mobile team has capacity" in [[11-unknowns-and-risks]] |
| F1.37 | OPS | high | R-OPS-04 | Who decides between the CEO and compliance, and by when? Does the year-one ban cover the March launch? | "Nobody has been named to decide when the CEO and compliance disagree." in [[11-unknowns-and-risks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| UNK-014 | open | open | [[2026-10-09-signal-model-backtest#^c04]] |
| UNK-014 | open | open | [[2026-10-09-signal-model-backtest#^c07]] |
| UNK-020 | - | open | [[2026-10-09-signal-model-backtest#^c11]] |
| R-DAT-03 | - | unknown | [[2026-10-09-signal-model-backtest#^c06]] |
| R-PTN-06 | - | unknown | [[2026-10-09-signal-model-backtest#^c07]] |
| R-OPS-05 | - | unknown | [[2026-10-09-signal-model-backtest#^c07]] |
| R-PTN-07 | - | unknown | [[2026-10-09-signal-model-backtest#^c15]] |
| R-FIN-08 | - | open | [[2026-10-09-signal-model-backtest#1. After the read-back, 2026-10-09]] |
| R-REG-08 | - | open | [[2026-10-09-signal-model-backtest#1. After the read-back, 2026-10-09]] |
| R-OPS-06 | - | open | [[2026-10-09-signal-model-backtest#1. After the read-back, 2026-10-09]] |
