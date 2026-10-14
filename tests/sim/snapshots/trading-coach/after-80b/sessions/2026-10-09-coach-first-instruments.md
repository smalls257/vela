---
id: 2026-10-09-coach-first-instruments
type: session
title: "Shape: coach first instruments"
date: 2026-10-09
modes: [shape]
status: closed
summary: Picked a short list of about 50 big US stocks as the coach's first instruments, on condition that counsel clears it; four unknowns and eight reviewer questions recorded.
---

# 2026-10-09 Shape: coach first instruments

## Captures

- [thought] (claude) Option A, "A short list of big US stocks": the coach starts with a fixed list of about 50 large US equities that we choose, and the reader practices on paper with one at a time from it. It costs a list someone must pick and keep up, and some lessons written around those names. It rules out options, funds and any stock off the list, so a reader's own pick is turned away. → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c01
- [thought] (claude) Option B, "Any US stock the reader picks": the coach teaches on any US equity the reader chooses, with Quoteline's 15-minute delayed prices shown and simulated trades on Brightwater's sandbox. It costs lessons that must work for any stock, and thin or unusual stocks may have no sandbox or price coverage. It rules out options and funds, and gives up a curated list. → park ^c02
- [thought] (claude) Option C, "Stocks first, options as reading only": the track is Option B's equities, with a closing module that explains options in words and diagrams, with no option prices and no simulated option trades. It costs extra lesson writing and a compliance read of the options content. It rules out any priced or practiced option trade, so the CEO's "stock or option" is only half met. → park ^c03
- [thought] (Jordan Reyes, product lead) Picks Option A, "A short list of big US stocks", on one condition: "A, if counsel clears the list as non-advice—gate one." → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c04
- [thought] (Jordan Reyes, product lead) Option C rejected: "Not C—CEO acceptance is open, options read is too much in parallel." → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c05
- [thought] (Jordan Reyes, product lead) Option B is the fallback, not picked: "B if legal won't clear A." → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c06
- [thought] (Jordan Reyes, product lead) F1.33: legal must clear a house-picked list as not investment advice; it is gate one for Option A. Open, and it needs writing. → keep: [[11-unknowns-and-risks#Question ledger|R-REG-09]] (unknown) ^c07
- [thought] (Jordan Reyes, product lead) F1.29: Brightwater and Quoteline must confirm every stock on the list has sandbox and price coverage; this comes after gate one. Open, and it needs writing. → keep: [[11-unknowns-and-risks#Question ledger|R-PTN-09]] (unknown) ^c08
- [thought] (Jordan Reyes, product lead) F1.10: the list needs a named owner and a budget. Open, and it needs writing. → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-09]] (unknown) ^c09
- [thought] (Jordan Reyes, product lead) F1.16: "Data license is open—I believe it's covered, but Quoteline bars non-display use, so data engineer needs to check if teaching counts as non-display use." A belief with no source, and an open question for the data engineer; close asks whether it is load-bearing. → keep: [[11-unknowns-and-risks#Question ledger|Q-DAT-05@INI-001]] (unknown) ^c10
- [thought] (Jordan Reyes, product lead) F1.33 owner: "counsel for legal clearance (unnamed, I'll get it this week)". Counsel owns it; the product lead will find the name this week. No ask-by date for the clearance itself is given. → keep: [[11-unknowns-and-risks#UNK-021 Legal clearance of the stock list|UNK-021]] (open) ^c11
- [thought] (Jordan Reyes, product lead) F1.29 owners: "partnerships manager for Brightwater and data engineer for Quoteline by year-end." Ask-by year-end, read as 2026-12-31. → keep: [[11-unknowns-and-risks#UNK-023 Coverage of every stock on the list|UNK-023]] (open) ^c12
- [thought] (Jordan Reyes, product lead) F1.10 owner: "List owner and budget on me by next Monday." The product lead owns it, ask-by next Monday, read as 2026-10-12. → keep: [[11-unknowns-and-risks#UNK-022 Owner and budget for the stock list|UNK-022]] (open) ^c13
- [thought] (Jordan Reyes, product lead) F1.33 ask-by: "Counsel by the 16th." Read as 2026-10-16. → keep: [[11-unknowns-and-risks#UNK-021 Legal clearance of the stock list|UNK-021]] (open) ^c14
- [thought] (Jordan Reyes, product lead) F1.16: "License is load-bearing—if Quoteline says teaching is non-display use, A doesn't ship." The belief that Quoteline covers teaching use is load-bearing; signpost: the data engineer's reading of the non-display clause. → keep: [[11-unknowns-and-risks#UNK-024 Quoteline and teaching use|UNK-024]] (open) ^c15
- [thought] (Jordan Reyes, product lead) F1.16 ask-by: "Data engineer shares year-end on both checks." The data engineer's checks on F1.16 and F1.29 both fall due 2026-12-31. → keep: [[11-unknowns-and-risks#UNK-024 Quoteline and teaching use|UNK-024]] (open) ^c16
- [thought] (Jordan Reyes, product lead) F1.16 ask-by moved: "Move the data engineer's license check to mid-November—if that fails, we need to know before we're locked into B." Read as 2026-11-15; the Brightwater and Quoteline coverage check (F1.29) stays at year-end. → keep: [[11-unknowns-and-risks#UNK-024 Quoteline and teaching use|UNK-024]] (open) ^c17

## Reviews

### 1. before options, 2026-10-09

- **Coverage:** FIN found 12, 1 dropped; DAT found 6; PTN found 12; REG found 7; OPS found 9
- **Dropped:** [FIN] For options B and C, how does a reader fund the account, who handles deposits and withdrawals, and what happens to the balance on closure or withdrawal? (the quote does not mention what the finding is about)
- **Merged:** [PTN] into F1.12: What service levels, stock coverage and volume limits does the Brightwater agreement give the sandbox, and does Quoteline cover every US stock a reader could pick?; [REG] into F1.28: Who in compliance and in Brightwater must approve Option C's options explainer before release? Does section 7.2 of the Brightwater agreement cover educational content on products it excludes?; [OPS] into F1.10: Who picks and keeps up Option A's list of about 50 stocks, who writes the lessons around it, and what happens when a stock is delisted or stops being suitable?; [OPS] into F1.11: Who in compliance will read Option C's options content and rule in writing, and by what date, given the January demo?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-03@SV-01 | Who carries the balances Brightwater holds as owed to customers, and does that apply to the sandbox accounts in Options B and C? | "who carries the balances as owed to customers is not recorded" in [[03-context-and-scope]] |
| F1.2 | FIN | normal | Q-FIN-04@SV-01 | Is a sandbox balance ever linked to or converted into a real Brightwater balance, and if so how? | "simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.3 | FIN | normal | Q-FIN-05@SV-01 | What happens to a reader's balance at account closure, expiry or withdrawal of the coach? | "Brightwater holds the money customers put in, and TickerTalk holds none" in [[03-context-and-scope]] |
| F1.4 | FIN | normal | Q-FIN-06@SV-01 | If any balance converts, who sets the rate and who approves it? | "Owner:** not known yet" in [[03-context-and-scope]] |
| F1.5 | FIN | high | R-FIN-02 | Who carries the financial liability if readers lose money following the coach, and is any legal, registration or insurance cost provided for? | "Readers may lose money following the coach's recommendations, and TickerTalk could be sued." in [[11-unknowns-and-risks]] |
| F1.6 | FIN | normal | R-FIN-03 | What would registration or licensing cost, and is it inside the allocated budget? | "which would need registration and turn the product into a year of legal work" in [[11-unknowns-and-risks]] |
| F1.7 | FIN | normal | R-FIN-04 | Does the allocated budget assume live trading through a broker, and who pays broker integration and fees if it does? | "its amount, its holder and what it covers are not recorded" in [[11-unknowns-and-risks]] |
| F1.8 | FIN | normal | R-FIN-05 | Which price feed would the coach trade on, does the license cover it, and who pays if not? | "with Quoteline's 15-minute delayed prices shown" in [[2026-10-09-coach-first-instruments]] |
| F1.9 | FIN | normal | R-FIN-08 | What is Signal's return after transaction costs, and who bears the costs if the gross figure is used? | "leaving out transaction costs" in [[01-goals]] |
| F1.10 | FIN, OPS | normal | new | Who picks and maintains Option A's list and writes its lessons, and what does that cost and out of which budget? | "It costs a list someone must pick and keep up, and some lessons written around those names." in [[2026-10-09-coach-first-instruments]] |
| F1.11 | FIN, OPS | high | R-OPS-02 | Who pays for Option C's extra lesson writing and compliance read, and is it inside the allocated budget? | "It costs extra lesson writing and a compliance read of the options content." in [[2026-10-09-coach-first-instruments]] |
| F1.12 | FIN, PTN | normal | R-PTN-02 | Do wider sandbox or price coverage cost extra under the Brightwater or Quoteline terms, and who pays? | "thin or unusual stocks may have no sandbox or price coverage" in [[2026-10-09-coach-first-instruments]] |
| F1.13 | DAT | high | R-DAT-02 | May the coach use Quoteline prices only to display quotes, or also in lessons, simulated trade pricing and recommendations? Is the separate addendum needed for Options A, B and C? | "with Quoteline's 15-minute delayed prices shown and simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.14 | DAT | high | Q-DAT-01@INI-001 | Will any reader data (identity, picks, simulated trades) go to Brightwater or Quoteline under Option B or C, and do the consent and data terms of the signed agreement allow it? | "simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.15 | DAT | high | Q-DAT-05@INI-001 | Will reader picks and paper trades under Option B or C be used for anything beyond teaching, such as Signal training, and what consent covers that? | "the coach teaches on any US equity the reader chooses" in [[2026-10-09-coach-first-instruments]] |
| F1.16 | DAT | normal | Q-DAT-05@INI-001 | What source is the 50-stock list drawn from, and is that data licensed for curating a teaching list and writing lessons around it? | "a fixed list of about 50 large US equities that we choose" in [[2026-10-09-coach-first-instruments]] |
| F1.17 | DAT | normal | Q-DAT-04@SV-01 | Which one system is the record of each reader's simulated balance and positions (the coach app or the Brightwater sandbox)? Does it carry to a live account later? | "Brightwater holds the money customers put in, and TickerTalk holds none" in [[03-context-and-scope]] |
| F1.18 | DAT | normal | new | What happens to a reader's pick, progress and any data kept when the stock has no sandbox or Quoteline coverage, and is the pick still stored? | "thin or unusual stocks may have no sandbox or price coverage" in [[2026-10-09-coach-first-instruments]] |
| F1.19 | PTN | high | Q-PTN-02@PTY-01 | Does the signed Brightwater agreement allow sandbox accounts in a consumer app, and let TickerTalk share reader data with Brightwater for them? Who reads it before Option B or C is picked? | "simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.20 | PTN | high | Q-PTN-02@PTY-02 | Does the Quoteline license let quote data be shared with, or used by, anyone other than TickerTalk's own display, such as the sandbox or the coaching logic? | "lets TickerTalk's own apps display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.21 | PTN | normal | Q-PTN-03@PTY-01 | When does the Brightwater agreement end, who holds it, and what does it cost to leave or change it if the coach's use changes? | "held by the partnerships manager; only [[sources#SRC-03\|its summary]] is in sources" in [[03-context-and-scope]] |
| F1.22 | PTN | normal | Q-PTN-03@PTY-02 | Who holds the Quoteline license, when does it end, and what does leaving or changing it cost? | "the license itself is not in sources" in [[03-context-and-scope]] |
| F1.23 | PTN | high | Q-PTN-05@PTY-02 | Does the Quoteline license allow assignment or a change of control, and does that matter to any option? | "summarized by the data engineer in March 2026" in [[03-context-and-scope]] |
| F1.24 | PTN | normal | Q-PTN-06@PTY-01 | What notice, and from whom, does Brightwater need before the coach uses its sandbox at reader scale? | "including consent, data, notice, exit and any limit on live trading" in [[11-unknowns-and-risks]] |
| F1.25 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to the Quoteline license need, and who gives it? | "it includes no options data" in [[03-context-and-scope]] |
| F1.26 | PTN | normal | R-PTN-04 | Which existing agreements, such as reader terms or content or data licenses, limit what the coach can say or show about named stocks and options? List them in sources. | "some lessons written around those names" in [[2026-10-09-coach-first-instruments]] |
| F1.27 | PTN | high | R-PTN-05 | Does the Quoteline license allow its delayed quotes to drive simulated trades or coaching, and is 15-minute delay acceptable for the lessons? | "with Quoteline's 15-minute delayed prices shown and simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.28 | PTN, REG | high | new | Does the Brightwater agreement (section 7.2) require Brightwater to approve options-explainer content, and does Quoteline's no-options license limit showing options examples or diagrams? | "a compliance read of the options content" in [[2026-10-09-coach-first-instruments]] |
| F1.29 | PTN | normal | new | Who picks and maintains Option A's list, and have Brightwater and Quoteline confirmed that every stock on it has sandbox and price coverage? | "a list someone must pick and keep up" in [[2026-10-09-coach-first-instruments]] |
| F1.30 | REG | normal | Q-REG-01@INI-001 | Does Option B, or any option, count as a product sold or promised across parties (Quoteline prices plus Brightwater sandbox)? If so, which party's terms govern what the customer is told? | "with Quoteline's 15-minute delayed prices shown and simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.31 | REG | normal | Q-REG-05@INI-001 | If Quoteline prices or the Brightwater sandbox fail or are wrong for a stock, who is liable to the reader, and what must the reader be told? | "thin or unusual stocks may have no sandbox or price coverage" in [[2026-10-09-coach-first-instruments]] |
| F1.32 | REG | normal | R-REG-02 | From what date does compliance's year one run, and when does the ban end? Does that leave room for any live step after the March paper launch? | "What date does ”year one” start from, and when does the ban end?" in [[11-unknowns-and-risks]] |
| F1.33 | REG | high | R-REG-06 | Will legal rule in writing, before Option A is chosen, whether a curated list of 50 stocks chosen by TickerTalk is investment advice? Who in legal will rule, and by when? | "a fixed list of about 50 large US equities that we choose" in [[2026-10-09-coach-first-instruments]] |
| F1.34 | REG | high | new | Does the signed Brightwater agreement allow sandbox accounts in a consumer product, and will compliance confirm in writing that simulated trades sit outside the live-trading ban, before Option B or C is relied on? | "simulated trades on Brightwater's sandbox" in [[2026-10-09-coach-first-instruments]] |
| F1.35 | REG | high | new | Will the CEO accept equities-only (Option A or B) or equities plus options explained in words (Option C)? Is the signed agreement confirmed to exclude options? | "so the CEO's ”stock or option” is only half met" in [[2026-10-09-coach-first-instruments]] |
| F1.36 | OPS | high | R-OPS-03 | Who builds and runs Option B's any-stock lessons and sandbox use? Has anyone checked sandbox and Quoteline coverage and limits, and what does the reader see when a stock has none? | "It costs lessons that must work for any stock, and thin or unusual stocks may have no sandbox or price coverage." in [[2026-10-09-coach-first-instruments]] |
| F1.37 | OPS | high | R-OPS-04 | Who decides between the CEO and compliance if the CEO rejects a stocks-only or options-as-reading release, and by what date? Does the year-one ban cover March? | "so the CEO's ”stock or option” is only half met." in [[2026-10-09-coach-first-instruments]] |
| F1.38 | OPS | normal | Q-OPS-06@INI-001 | Which readers and teams are affected by each option but not yet consulted, and who wants something different (readers wanting their own picks, options or funds, the CEO, compliance, the mobile team, Brightwater)? | "It rules out options, funds and any stock off the list, so a reader's own pick is turned away." in [[2026-10-09-coach-first-instruments]] |
| F1.39 | OPS | normal | Q-OPS-05@INI-001 | Does any option replace or retire something readers or teams use today, and who depends on it? | "It rules out any priced or practiced option trade" in [[2026-10-09-coach-first-instruments]] |
| F1.40 | OPS | normal | Q-OPS-04@INI-001 | Is any other list, system or team already choosing or covering instruments, for example Signal's 50-stock universe, and should Option A reuse it or keep it separate? | "the coach starts with a fixed list of about 50 large US equities that we choose" in [[2026-10-09-coach-first-instruments]] |
| F1.41 | OPS | high | R-OPS-03 | Which named teams and people build and run each option, and can the mobile team deliver Option B or C by March alongside TickerTalk itself? | "The mobile lead, who is not named, has to confirm that the mobile team has capacity for the first release by March." in [[11-unknowns-and-risks]] |
| F1.42 | OPS | normal | R-OPS-06 | Is training on users' watchlists, or on stocks readers pick under Option B, planned or only wished for, and who would approve and run it? | "The ML team wants to train on TickerTalk users' watchlists next, but the product lead says that is a wish and not a committed step." in [[01-goals]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| UNK-021 | - | open | [[2026-10-09-coach-first-instruments#^c07]] |
| UNK-022 | - | open | [[2026-10-09-coach-first-instruments#^c09]] |
| UNK-023 | - | open | [[2026-10-09-coach-first-instruments#^c08]] |
| UNK-024 | - | open | [[2026-10-09-coach-first-instruments#^c10]] |
| R-REG-09 | - | unknown | [[2026-10-09-coach-first-instruments#^c07]] |
| R-FIN-09 | - | unknown | [[2026-10-09-coach-first-instruments#^c09]] |
| R-PTN-09 | - | unknown | [[2026-10-09-coach-first-instruments#^c08]] |
| Q-DAT-05@INI-001 | - | unknown | [[2026-10-09-coach-first-instruments#^c10]] |
| R-DAT-04 | - | open | [[2026-10-09-coach-first-instruments#1. before options, 2026-10-09]] |
| R-PTN-08 | - | open | [[2026-10-09-coach-first-instruments#1. before options, 2026-10-09]] |
| R-REG-10 | - | open | [[2026-10-09-coach-first-instruments#1. before options, 2026-10-09]] |
| R-REG-11 | - | open | [[2026-10-09-coach-first-instruments#1. before options, 2026-10-09]] |
