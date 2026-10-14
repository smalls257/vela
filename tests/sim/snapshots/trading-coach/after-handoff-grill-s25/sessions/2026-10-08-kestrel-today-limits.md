---
id: 2026-10-08-kestrel-today-limits
type: session
title: "Discover: kestrel today limits"
date: 2026-10-08
modes: [discover]
status: closed
summary: "Discover: Brightwater and Signal facts from the summary and backtest; five new unknowns; everything waits on the agreement read."
---

# 2026-10-08 Discover: kestrel today limits

- **Override:** "Dump & Diverge segment" by @sim-lead on 2026-10-08: "everything waits on what I find in the agreement tomorrow"

## Captures

- [thought] (claude, from partnerships manager) Brightwater opens accounts, does the identity checks, holds customer money and executes equity orders through its API (SRC-01). → keep: [[03-context-and-scope#Today|03 today]] (fact) ^c65
- [thought] (claude, from partnerships manager) Kestrel gets an account ID and order status from Brightwater, and never holds customer money (SRC-01). → keep: [[03-context-and-scope#Today|03 today]] (fact) ^c66
- [thought] (claude, from partnerships manager) Brightwater offers sandbox paper accounts for testing (SRC-01). → keep: [[03-context-and-scope#Today|03 today]] (fact) ^c67
- [thought] (claude, from ML team) The Signal backtest used the 50 largest US stocks by market value as of September 2026, over 2015 to 2025 (SRC-03). → keep: [[03-context-and-scope#Today|03 today]] (fact) ^c68
- [thought] (claude, from ML team) In that backtest Signal's daily long-short portfolio returned 31% a year against 11% for the index (SRC-03). → keep: [[03-context-and-scope#Today|03 today]] (fact) ^c69
- [thought] (claude, from CEO) The coach teaches people to trade one stock or option at a time, and trades for them when they are ready (SRC-04, a plan). → keep: [[01-goals#Goals|G1]] (assumption) ^c70
- [thought] (claude, from CEO) The coach is to go live by March, with a board demo in January (SRC-04, a plan). → park ^c71
- [thought] (claude, from CEO) TickerTalk's 400,000 users are the launch audience (SRC-04, a plan). → keep: [[03-context-and-scope#Today|03 today]] (assumption) ^c72
- [thought] (claude, from CEO) Brightwater handles the brokerage side (SRC-04, a plan). → keep: [[03-context-and-scope#Today|03 today]] (assumption) ^c73
- [thought] (product lead) "I know we can do options." Later: "I believe we can do them, the agreement should back it up." A belief with no source. → keep: [[11-unknowns-and-risks#UNK-014 Options under the Brightwater agreement|UNK-014]] (open) ^c74
- [worry] (product lead) "Options is the blocker though... If it doesn't, the CEO's whole mandate dies." → keep: [[11-unknowns-and-risks#UNK-014 Options under the Brightwater agreement|UNK-014]] (open) ^c75
- [unknown] (claude, from product lead) Do options fall under the Brightwater agreement: the summary (SRC-01) says no, the CEO's memo (SRC-04) says yes, and the product lead believes yes but has not read the agreement. → keep: [[11-unknowns-and-risks#UNK-014 Options under the Brightwater agreement|UNK-014]] (open) ^c76
- [unknown] (claude) How big is Signal's edge: the CEO's memo (SRC-04) says it beats the market by 31% a year, the backtest (SRC-03) says 31% against 11% for the index. → keep: [[11-unknowns-and-risks#UNK-015 Size of Signal's edge|UNK-015]] (open) ^c77
- [unknown] (claude) Does the Brightwater agreement allow auto-trading and the account link, and does an approval rule reach the coach's content? The summary (SRC-01) is silent. → keep: [[11-unknowns-and-risks#UNK-016 Auto-trading and account link under Brightwater|UNK-016]] (open) ^c78
- [unknown] (claude) Is the Brightwater link Kestrel's or TickerTalk's: the Context page says TickerTalk, the summary (SRC-01) says Kestrel. → keep: [[11-unknowns-and-risks#UNK-017 Whose Brightwater link|UNK-017]] (open) ^c79
- [unknown] (claude) Who carries the customer money Brightwater holds as money owed to customers. → keep: [[11-unknowns-and-risks#UNK-018 Who owes customers their money|UNK-018]] (open) ^c80
- [thought] (product lead) Rules none of the review lines out: "they all tie back to either the agreement or other unknowns. Tomorrow's read is what tells us which actually matter." Asked who can pull the TickerTalk terms and privacy notice; no holder named. → keep: [[11-unknowns-and-risks#UNK-006 TickerTalk terms and privacy notice|UNK-006]] (open) ^c81
- [thought] (product lead) "Mobile probably hold them." A belief about who holds TickerTalk's user terms and privacy notice, no source. → keep: [[11-unknowns-and-risks#UNK-006 TickerTalk terms and privacy notice|UNK-006]] (open) ^c82
- [thought] (product lead) waits on UNK-004: R-PTN-01, Q-PTN-05@PTY-01, Q-PTN-02@PTY-01, R-FIN-01, Q-FIN-03@SV-01, F1.1, F1.4, F1.7, F1.9, F1.10, F1.17, F1.18, F1.26 → keep: [[11-unknowns-and-risks#Question ledger|R-PTN-01]] (unknown) ^c83
- [thought] (product lead) waits on UNK-006: Q-DAT-01@INI-001, Q-DAT-05@INI-001, R-REG-03, F1.22 → keep: [[11-unknowns-and-risks#Question ledger|Q-DAT-01@INI-001]] (unknown) ^c84
- [thought] (product lead) waits on UNK-005: F1.3, F1.8, F1.21 → keep: [[11-unknowns-and-risks#Question ledger|R-FIN-04]] (unknown) ^c85
- [thought] (product lead) "Done for now though—everything waits on what I find in the agreement tomorrow. That's the real work." Ends the session before the "What do these documents not say?" segment. → drop: recorded as the session's Override bullet; no item to keep ^c86

## Reviews

### 1. After the read-back, 2026-10-08

- **Coverage:** FIN found 4, 7 dropped; DAT found 4, 3 dropped; PTN found 6, 7 dropped; REG found 8, 3 dropped; OPS found 6, 1 dropped
- **Dropped:** 21 findings: FIN Q-FIN-03 (named without its subject); FIN Q-FIN-01 (named without its subject); FIN Q-FIN-02 (named without its subject); FIN Q-FIN-04 (named without its subject); FIN Q-FIN-05 (named without its subject); FIN Q-FIN-06 (named without its subject); FIN "How is the coach meant to earn revenue (commissions, subscri..." (quote does not mention what it is about); DAT Q-DAT-01 (named without its subject); DAT Q-DAT-05 (named without its subject); DAT Q-DAT-04 (named without its subject); PTN Q-PTN-02 (named without its subject); PTN Q-PTN-03 (named without its subject); PTN Q-PTN-05 (named without its subject); PTN Q-PTN-06 (named without its subject); PTN Q-PTN-03 (named without its subject); PTN "Who will fetch and record the Brightwater agreement, the quo..." (quote does not mention what it is about); PTN Q-PTN-01 (named without its subject); REG Q-REG-01 (named without its subject); REG Q-REG-05 (named without its subject); REG Q-REG-02 (named without its subject); OPS R-OPS-01 finding (its quote is not in 03-context-and-scope).
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | R-FIN-01 | If users lose money following Signal or the coach, who bears the loss and legal cost? Does the Brightwater agreement set fees, indemnities or revenue shares? | "does it overfit and lose money on real money, leaving TickerTalk liable?" in [[11-unknowns-and-risks]] |
| F1.2 | FIN | normal | R-FIN-03 | What would registration or a contracted registered adviser cost, and is that inside the 2.5 million? | "The product lead fears the consultant says registration as advisers is needed." in [[11-unknowns-and-risks]] |
| F1.3 | FIN | high | new | Which Signal return figure may any financial case or user-facing claim use, and was the backtest stock list chosen with hindsight? | "which is a 20-point gap, on the 50 largest stocks over 2015 to 2025" in [[11-unknowns-and-risks]] |
| F1.4 | FIN | high | new | If options are not covered, what would adding them cost with Brightwater, who pays, and is it inside the 2.5 million? | "The summary of the agreement (SRC-01) says options are not covered" in [[11-unknowns-and-risks]] |
| F1.5 | DAT | high | R-DAT-01 | Is Quoteline the quote source for the coach? Does its license summary (SRC-02) allow showing quotes to users and to a new product, and who holds the agreement? | "Quoteline market data license summary" in [[sources]] |
| F1.6 | DAT | high | R-DAT-02 | Which entity holds the Brightwater link and each user's account, and where are users' trade, limit and consent records kept so they follow the user across TickerTalk, Kestrel and Brightwater? | "Is the Brightwater API link Kestrel's or TickerTalk's?" in [[11-unknowns-and-risks]] |
| F1.7 | DAT | high | new | What do the Brightwater agreement's clauses on data sharing, user consent and use of account data say about linking accounts and trading for users? | "Does the Brightwater agreement allow the coach to place orders for a user and to link a user's account" in [[11-unknowns-and-risks]] |
| F1.8 | DAT | normal | new | Where did the backtest's historical price data come from, does its license allow this use, and was the stock universe picked with hindsight? | "the 50 largest US stocks by market value as of September 2026, over 2015 to 2025." in [[03-context-and-scope]] |
| F1.9 | PTN | high | R-PTN-01 | What do Brightwater's terms say on options, scope changes, termination notice and exclusivity, and will Brightwater agree to a scope change? | "The summary of the agreement (SRC-01) says options are not covered" in [[11-unknowns-and-risks]] |
| F1.10 | PTN | high | R-PTN-01 | Does the agreement permit order placement on a user's behalf and account linking? Does any approval rule reach the coach's content? | "The summary (SRC-01) is silent on these" in [[11-unknowns-and-risks]] |
| F1.11 | PTN | high | R-PTN-02 | Is Quoteline the quotes supplier? What does its license summary (SRC-02) allow for display or use in a real-money trading product? | "Source and holder of that agreement were not named." in [[11-unknowns-and-risks]] |
| F1.12 | PTN | normal | R-PTN-03 | Will Brightwater build the order screen or cover the regulated part, and under which clause? | "the CEO's memo says Brightwater handles the brokerage side." in [[03-context-and-scope]] |
| F1.13 | PTN | normal | R-PTN-04 | What API rate limits, sandbox limits, uptime commitments and user caps does the agreement set, and do they fit a launch to 400,000 users? | "it offers sandbox paper accounts." in [[03-context-and-scope]] |
| F1.14 | PTN | normal | new | How and when will Partnerships be told about the ask, given that the agreement is needed by 2026-10-09 and Brightwater has not been contacted? | "Mobile, ML, Partnerships and compliance are all unaware of the ask." in [[03-context-and-scope]] |
| F1.15 | REG | high | R-REG-01 | Who has authority to stop a launch if compliance sign-off is not done, and does that cover the January board demo as well as the March go-live? | "Compliance sign-off may take until February. Does the product ship anyway because the demo date is fixed? Who can hold a launch?" in [[11-unknowns-and-risks]] |
| F1.16 | REG | high | R-REG-02 | Which reading of 'trades for them' does the CEO intend, and which regulatory category does each reading fall under? | "trades for them when they're ready (the CEO's ask)" in [[01-goals]] |
| F1.17 | REG | high | new | Does the Brightwater agreement cover options? If not, will the launch be stocks only, and does options trading carry extra regulatory requirements? | "The summary of the agreement (SRC-01) says options are not covered, and the CEO's memo (SRC-04) says the coach teaches ”one stock or option at a time”." in [[11-unknowns-and-risks]] |
| F1.18 | REG | high | new | Does the Brightwater agreement require Brightwater to approve the coach's content or marketing, and how long would that take against the January demo and March launch? | "does any approval rule in it reach what the coach shows users?" in [[11-unknowns-and-risks]] |
| F1.19 | REG | high | new | Which legal entity holds the Brightwater agreement and will be in front of customers, Kestrel or TickerTalk? | "It is not recorded whether TickerTalk is a Kestrel app." in [[11-unknowns-and-risks]] |
| F1.20 | REG | normal | new | Who owes customers the money held at Brightwater, and what protection do customers have if Brightwater fails? | "- **Owner:** not known yet, see [[11-unknowns-and-risks#UNK-018 Who owes customers their money\|UNK-018]]" in [[03-context-and-scope]] |
| F1.21 | REG | high | new | Will performance figures from Signal be shown to users, who reviews those claims, and has the survivorship-bias problem in the backtest been addressed? | "the 50 largest US stocks by market value as of September 2026, over 2015 to 2025." in [[03-context-and-scope]] |
| F1.22 | REG | normal | R-REG-03 | Who holds TickerTalk's user terms and privacy notice, and is options coaching planned when Signal covers stocks only? | "an ML model that guesses next-day moves on fifty large-cap stocks" in [[03-context-and-scope]] |
| F1.23 | OPS | high | Q-OPS-06@INI-001 | Who in mobile, ML, Partnerships and compliance will be affected, and when will each be told and asked what they would stop doing? | "Mobile, ML, Partnerships and compliance are all unaware of the ask." in [[03-context-and-scope]] |
| F1.24 | OPS | normal | Q-OPS-04@INI-001 | Is TickerTalk a Kestrel app, and which team owns and runs the existing Brightwater API link? | "a broker TickerTalk has been on API with since June, per the product lead." in [[03-context-and-scope]] |
| F1.25 | OPS | normal | R-OPS-02 | Who owns the coach after the pitch, and who can settle what 'trades for them' means? | "the CEO decides whether to move people, and the product lead pitches it." in [[03-context-and-scope]] |
| F1.26 | OPS | high | Q-OPS-07@INI-001 | If the agreement excludes options, what is the fallback for G1 and who decides whether the coach ships as stocks only? | "The product lead believes options can be done and expects the full agreement to back it up." in [[11-unknowns-and-risks]] |
| F1.27 | OPS | normal | Q-OPS-07@INI-001 | What supports the 400,000 user figure, and who handles support for that audience at launch? | "400,000 monthly users, per the product lead. No source yet." in [[03-context-and-scope]] |
| F1.28 | OPS | normal | new | Who answers customers and handles disputes when money or an order at Brightwater goes wrong? | "Owner:** not known yet" in [[03-context-and-scope]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| 03 today (Brightwater, 3 lines) | - | fact | [[2026-10-08-kestrel-today-limits#^c65]] |
| PTY-01 | - | subject | [[2026-10-08-kestrel-today-limits#^c65]] |
| SV-01 | - | subject | [[2026-10-08-kestrel-today-limits#^c66]] |
| 03 today (Signal, 2 lines) | - | fact | [[2026-10-08-kestrel-today-limits#^c69]] |
| G1 | - | assumption | [[2026-10-08-kestrel-today-limits#^c70]] |
| UNK-014 | - | open | [[2026-10-08-kestrel-today-limits#^c76]] |
| UNK-015 | - | open | [[2026-10-08-kestrel-today-limits#^c77]] |
| UNK-016 | - | open | [[2026-10-08-kestrel-today-limits#^c78]] |
| UNK-017 | - | open | [[2026-10-08-kestrel-today-limits#^c79]] |
| UNK-018 | - | open | [[2026-10-08-kestrel-today-limits#^c80]] |
| R-FIN-04 | - | unknown | [[2026-10-08-kestrel-today-limits#^c85]] |
| R-FIN-05 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| R-DAT-03 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| R-DAT-04 | - | unknown | [[2026-10-08-kestrel-today-limits#^c85]] |
| R-PTN-06 | - | open | [[2026-10-08-kestrel-today-limits#1. After the read-back, 2026-10-08]] |
| R-REG-04 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| R-REG-05 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| R-REG-06 | - | open | [[2026-10-08-kestrel-today-limits#1. After the read-back, 2026-10-08]] |
| R-REG-07 | - | open | [[2026-10-08-kestrel-today-limits#1. After the read-back, 2026-10-08]] |
| R-REG-08 | - | unknown | [[2026-10-08-kestrel-today-limits#^c85]] |
| R-OPS-03 | - | open | [[2026-10-08-kestrel-today-limits#1. After the read-back, 2026-10-08]] |
| Q-PTN-05@PTY-01 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| Q-PTN-02@PTY-01 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| Q-FIN-03@SV-01 | - | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| Q-DAT-01@INI-001 | - | unknown | [[2026-10-08-kestrel-today-limits#^c84]] |
| Q-DAT-05@INI-001 | - | unknown | [[2026-10-08-kestrel-today-limits#^c84]] |
| R-FIN-01 | open | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| R-PTN-01 | open | unknown | [[2026-10-08-kestrel-today-limits#^c83]] |
| R-REG-03 | open | unknown | [[2026-10-08-kestrel-today-limits#^c84]] |
