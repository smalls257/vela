---
id: 2026-10-09-broker-data-coach-limits
type: session
title: "Discover: broker data coach limits"
date: 2026-10-09
modes: [discover, dump]
status: closed
summary: "Discover on broker, data and coach limits: Brightwater (equities only) and Quoteline (delayed display, no options) typed, five new unknowns and a no-demo risk recorded, and the compliance and options questions marked as gates."
---

# 2026-10-09 Discover: broker data coach limits

## Captures

- [thought] (product lead) "1, 2, 5 are solid." Brightwater opens accounts, runs KYC and holds the money; TickerTalk gets an account ID and order status and holds no money; sandbox paper accounts exist. → keep: [[03-context-and-scope#PTY-01 Brightwater|PTY-01]] (subject) ^c01
- [thought] (product lead) "6, 7 match the mandate." Line 6 is the coach that teaches one stock or option at a time and trades for people when ready. → keep: [[01-goals#Goals|G1]] (inkling) ^c02
- [thought] (product lead) "6, 7 match the mandate." Line 7 is the January demo and the March launch. → keep: [[02-constraints|CST-1]] (inkling) ^c03
- [thought] (product lead) "11, 12 track." Quoteline's license is delayed US equity quotes for display, with no options data. → keep: [[03-context-and-scope#PTY-02 Quoteline|PTY-02]] (subject) ^c04
- [thought] (product lead) "Kestrel = TickerTalk, that's right." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c05
- [unknown] (product lead) "3 stops me—I thought Brightwater covered options, so if the agreement doesn't, I've got bad info. We need that nailed before the demo." → keep: [[11-unknowns-and-risks#UNK-012 Options coverage|UNK-012]] (open) ^c06
- [unknown] (product lead) "Options gap is real." The CEO wants options; the Brightwater summary and the Quoteline summary cover none. → keep: [[11-unknowns-and-risks#UNK-012 Options coverage|UNK-012]] (open) ^c07
- [thought] (product lead) "The CEO framing on 8, 9, honestly haven't heard it put that way." Lines 8 and 9 are not confirmed and are not written. → drop: the lead has not heard this framing and does not confirm it, and it is on no page ^c08
- [unknown] (product lead) "10, Signal's 31% is real but I wouldn't tell the board "beats the market" without nailing the baseline first." → keep: [[11-unknowns-and-risks#UNK-013 Signal baseline|UNK-013]] (open) ^c09
- [unknown] (product lead) "14 methodology mostly yes, but confirm the stock-list time gap you flagged." → keep: [[11-unknowns-and-risks#UNK-013 Signal baseline|UNK-013]] (open) ^c10
- [unknown] (product lead) "4, 13, the specific sections I'd need to read myself." → keep: [[11-unknowns-and-risks#UNK-015 Two clauses to read in full|UNK-015]] (open) ^c11
- [thought] (product lead) "15, that's what ML wants to do, not a committed next step." → drop: same statement as c14 ^c12
- [unknown] (product lead) "Watchlists and Quoteline still unclear." → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c13
- [thought] (product lead) "Line 15 yes, line 14 with caveat yes, line 3 yes." Line 15 is the ML team's wish to train on watchlists, not a committed step. → keep: [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline|UNK-014]] (open) ^c14
- [thought] (product lead) "Line 15 yes, line 14 with caveat yes, line 3 yes." Line 14 is the backtest result with the stock-list caveat. → keep: [[11-unknowns-and-risks#UNK-013 Signal baseline|UNK-013]] (open) ^c15
- [thought] (product lead) "Line 15 yes, line 14 with caveat yes, line 3 yes." Line 3 is that the Brightwater agreement covers equities and not options. → keep: [[03-context-and-scope#PTY-01 Brightwater|PTY-01]] (subject) ^c16
- [thought] (product lead) "Line 4 and 13 no—unread clauses. Lines 8 and 9 no—CEO framing not confirmed." Not written. → drop: repeats c08 and c11, and nothing new is written ^c17
- [thought] (product lead) "if Brightwater doesn't cover options and compliance bans live orders, there's no demo and no March." A belief, not sourced; close asks whether it is load-bearing. → keep: [[11-unknowns-and-risks#R-09 No demo and no March|R-09]] (open) ^c18
- [thought] (product lead) R-PTN-01 and F1.22: "Lines 7 and 10 from your high-severity list are everything though." → keep: [[11-unknowns-and-risks#Question ledger|R-REG-04]] (unknown) ^c19
- [thought] (product lead) "Yes, move it up—if compliance bans partner orders, there's nothing." Ask-by date of the question whether the ban covers partner-broker orders moved up to 2026-10-23, the date of the compliance ruling. → keep: [[11-unknowns-and-risks#UNK-004 No live trading and broker orders|UNK-004]] (open) ^c20
- [thought] (product lead) "Honestly not sure on the names." Neither the partnerships manager nor the compliance holder can be named yet. → keep: [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|UNK-003]] (open) ^c21
- [unknown] (product lead) "What's not in any document: the user-facing copy. When the coach suggests a trade, what does it say, who signs off on it, does Signal explain why?" → keep: [[11-unknowns-and-risks#UNK-016 Coach's user-facing copy|UNK-016]] (open) ^c22
- [thought] (product lead) "That's where investment advice either does or does not live. Can't move till that's settled." A belief about what blocks the work; close asks whether it is load-bearing. → keep: [[11-unknowns-and-risks#UNK-016 Coach's user-facing copy|UNK-016]] (open) ^c23
- [thought] (product lead) "Both dates work—copy by end of month, compliance ruling by the 23rd. Those are critical." Confirms ask-by 2026-10-30 for the coach's copy and 2026-10-23 for the compliance questions. → keep: [[11-unknowns-and-risks#UNK-016 Coach's user-facing copy|UNK-016]] (open) ^c24

## Reviews

### 1. After the read-back, 2026-10-09

- **Coverage:** FIN found 4, 7 dropped; DAT found 2, 4 dropped; PTN found 13, 1 dropped; REG found 3, 6 dropped; OPS found 0, 8 dropped
- **Dropped:** [FIN] copy Q-FIN-03 is not one this vault owes under that id: Who carries the balances Brightwater holds as money owed to customers? Which clause of the signed agreement says so?; [FIN] copy Q-FIN-04 is not one this vault owes under that id: Does any balance move between TickerTalk, Brightwater or another scheme and need converting? If not, can this be recorded as not applicable?; [FIN] copy Q-FIN-05 is not one this vault owes under that id: What does the signed Brightwater agreement say happens to customer balances on account closure or on exit?; [FIN] copy Q-FIN-06 is not one this vault owes under that id: Is there any rate or conversion between balances? If there is, who sets and approves it?; [FIN] the quote does not mention what the finding is about: Does the allocated budget assume live trading through Brightwater? If it does, who pays for integration and fees?; [FIN] a new question about a page this session did not change: If options stay in scope, who pays for options execution at Brightwater and for an options data license, and is that inside the budget?; [FIN] a new question about a page this session did not change: What would the Quoteline non-display addendum cost, and which budget would carry it if the ML team trains on watchlists?; [DAT] copy Q-DAT-01 is not one this vault owes under that id: What customer data goes from TickerTalk to Brightwater, and from Brightwater to TickerTalk, and may Brightwater use it for its own purposes?; [DAT] copy Q-DAT-05 is not one this vault owes under that id: What were watchlists collected for, did readers consent to model training, and is training on them a new purpose that needs fresh consent or a license addendum?; [DAT] copy Q-DAT-04 is not one this vault owes under that id: Which system is the single record of each customer's balance, and how does TickerTalk see it?; [DAT] a new question about a page this session did not change: What do the signed Brightwater agreement and the Quoteline license say on data use and consent, and when will the product lead read them in full?; [PTN] a new question about a page this session did not change: Does Brightwater have to approve the coach's customer-facing content under section 7.2, how long does approval take, and does it fit before the January demo?; [REG] copy Q-REG-01 is not one this vault owes under that id: Will the coach be sold or promised to customers jointly with Brightwater or Quoteline, for example as a bundle, a co-branded offer or a trading service presented under TickerTalk's name?; [REG] copy Q-REG-05 is not one this vault owes under that id: If a Brightwater order, a Quoteline quote or the coach's recommendation fails and a customer loses money, who is liable to the customer, and what do the Brightwater agreement and Quoteline license say about it?; [REG] copy R-REG-01 is not one this vault owes under that id: Who has authority to settle a CEO versus compliance conflict, and can a date before the January demo be fixed for putting both in the same room?; [REG] a new question about a page this session did not change: What licenses, broker permissions or approvals would the coach need to teach or place options trades, and will the January demo include options?; [REG] a new question about a page this session did not change: What does section 7.2 require for approval of customer-facing trading content, who at Brightwater approves it, and how long does approval take against the January demo?; [REG] a new question about a page this session did not change: Who in legal will give a written view on whether the coach is investment advice, and before what date, given the January demo?; [OPS] copy Q-OPS-07 is not one this vault owes under that id: Who owns the decision to train on watchlists, and does any plan rest on Quoteline data being usable beyond display?; [OPS] copy Q-OPS-07 is not one this vault owes under that id: If options are not covered by Brightwater or Quoteline, does the coach and the January demo drop options, and who decides that?; [OPS] copy Q-OPS-06 is not one this vault owes under that id: Who else heard the CEO differently, and which groups (compliance, legal, the ML team, the mobile team, readers) want something different from the coach?; [OPS] copy Q-OPS-06 is not one this vault owes under that id: Who will build and run the coach, the broker integration and the data feed, including out of hours, and does the mobile team have capacity?; [OPS] copy Q-OPS-07 is not one this vault owes under that id: Which of the foundation claims (400k readers, mobile team, allocated budget) can be sourced, and which would change the plan most if wrong?; [OPS] copy Q-OPS-06 is not one this vault owes under that id: Who is the partnerships manager, and who at TickerTalk operates the Brightwater and Quoteline relationships day to day?; [OPS] copy Q-OPS-05 is not one this vault owes under that id: Does the coach replace or retire anything, such as an existing TickerTalk feature, watchlist or data feed, and who still depends on it?; [OPS] copy Q-OPS-04 is not one this vault owes under that id: Is there more than one system or team doing the same job (quotes, watchlists, Signal), and which ones?
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | R-FIN-01 | Is mobile team time inside the allocated budget? What TickerTalk work gives way, and who carries that cost? | "The mobile team may be swamped building the coach while TickerTalk itself deteriorates." in [[11-unknowns-and-risks]] |
| F1.2 | FIN | high | R-FIN-02 | Who carries the financial liability if readers lose money following the coach? Is any legal, registration or insurance cost budgeted? | "Readers may lose money following the coach's recommendations, and TickerTalk could be sued." in [[11-unknowns-and-risks]] |
| F1.3 | FIN | normal | R-FIN-03 | What would registration or licensing cost, and is it inside the allocated budget? | "which would need registration and turn the product into a year of legal work" in [[11-unknowns-and-risks]] |
| F1.4 | FIN | normal | new | Which price feed would the coach trade on, and does the existing delayed display license cover it? If not, who pays for a feed that does? | "display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.5 | DAT | normal | R-DAT-01 | What data would paper accounts, the opt-in and the audit trail hold, and may they carry over to a live Brightwater account without fresh consent? | "The same summary says sandbox paper accounts are available for testing." in [[03-context-and-scope]] |
| F1.6 | DAT | high | new | May the coach use Quoteline data to generate lessons or recommendations, or only to display quotes, and is any addendum needed? | "it lets TickerTalk's own apps display US equity quotes delayed by 15 minutes, and that it includes no options data." in [[03-context-and-scope]] |
| F1.7 | PTN | high | Q-PTN-02@PTY-01 | Does the signed Brightwater agreement let TickerTalk share customer or reader data with a new owner or user of it? Who will read the full document and record the answer? | "the vault holds only summaries" in [[11-unknowns-and-risks]] |
| F1.8 | PTN | high | Q-PTN-02@PTY-02 | Does the Quoteline license let data be shared with, or used by, a new party or for a new purpose such as models? Is the addendum needed, and what would it cost? | "bars non-display use of its data, including models and derived data, without a separate addendum" in [[11-unknowns-and-risks]] |
| F1.9 | PTN | normal | Q-PTN-03@PTY-01 | Who holds the Brightwater agreement, when does it end, and what does leaving or changing it cost? | "the signed broker agreement, June (year not recorded), held by the partnerships manager" in [[03-context-and-scope]] |
| F1.10 | PTN | normal | Q-PTN-03@PTY-02 | Who holds the Quoteline license, when does it end, and what does leaving or changing it cost? | "the license itself is not in sources" in [[03-context-and-scope]] |
| F1.11 | PTN | high | Q-PTN-05@PTY-01 | Does the Brightwater agreement allow assignment, and what happens if control of TickerTalk or Brightwater changes? | "including consent, data, notice, exit and any limit on live trading" in [[11-unknowns-and-risks]] |
| F1.12 | PTN | high | Q-PTN-05@PTY-02 | Can the Quoteline license be assigned, or survive a change of control, and does it cover a new coach app or entity? | "lets TickerTalk's own apps display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.13 | PTN | normal | Q-PTN-06@PTY-01 | What notice does a change to the Brightwater agreement need, and who must give it? | "The terms of the broker agreement signed with Brightwater in June are not recorded" in [[11-unknowns-and-risks]] |
| F1.14 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to the Quoteline license, such as adding the addendum, need, and who gives it? | "does not say whether watchlists count as Quoteline data" in [[11-unknowns-and-risks]] |
| F1.15 | PTN | high | R-PTN-01 | If Brightwater does not cover options, which broker would, what terms would that agreement need (consent, data sharing, change of control, notice, exit cost), and can it be in place for the January demo or March launch? | "the plan and both summaries disagree" in [[11-unknowns-and-risks]] |
| F1.16 | PTN | normal | R-PTN-02 | What uptime, rate or volume limits does the Brightwater agreement give, and how do they compare with what the coach needs? | "The broker's API may not scale to the coach's volume." in [[11-unknowns-and-risks]] |
| F1.17 | PTN | normal | R-PTN-03 | Does the budget cover partner fees, the Quoteline addendum, broker integration or legal costs, and who pays if not? | "The budget is said to be allocated, but its amount, its holder and what it covers are not recorded." in [[11-unknowns-and-risks]] |
| F1.18 | PTN | normal | R-PTN-04 | Do any other agreements, such as the TickerTalk readers' terms or content licenses, limit the coach? If so, list them in sources with their limits. | "the Brightwater agreement's rule on approving customer-facing trading content" in [[11-unknowns-and-risks]] |
| F1.19 | PTN | high | new | Is 15-minute-delayed display data acceptable for a coach that places orders through Brightwater, and does the Quoteline license allow its quotes to drive coaching or order decisions? | "delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.20 | REG | normal | R-REG-02 | What date does compliance's year one start from, and on what date does the ban on live trading end? | "It is not recorded whether compliance's year one runs from March, from today or from another date." in [[11-unknowns-and-risks]] |
| F1.21 | REG | normal | R-REG-03 | Does compliance agree in writing that a coach working only on Brightwater sandbox paper accounts falls outside the live-trading ban and outside any licensing requirement? | "The same summary says sandbox paper accounts are available for testing." in [[03-context-and-scope]] |
| F1.22 | REG | high | new | Can the coach trade for people at all by March given compliance's ban, and who will get the written ruling on whether orders through Brightwater are covered? | "Rules out TickerTalk placing live orders in year one; whether orders through a partner broker are covered is open" in [[02-constraints]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| PTY-01 | - | subject | [[2026-10-09-broker-data-coach-limits#^c01]] |
| G1 | inkling | inkling | [[2026-10-09-broker-data-coach-limits#^c02]] |
| CST-1 | inkling | inkling | [[2026-10-09-broker-data-coach-limits#^c03]] |
| PTY-02 | - | subject | [[2026-10-09-broker-data-coach-limits#^c04]] |
| SRC-07 | - | fact | [[2026-10-09-broker-data-coach-limits#^c05]] |
| UNK-012 | - | open | [[2026-10-09-broker-data-coach-limits#^c06]] |
| UNK-013 | - | open | [[2026-10-09-broker-data-coach-limits#^c09]] |
| UNK-014 | - | open | [[2026-10-09-broker-data-coach-limits#^c13]] |
| UNK-015 | - | open | [[2026-10-09-broker-data-coach-limits#^c11]] |
| UNK-013 | open | open | [[2026-10-09-broker-data-coach-limits#^c15]] |
| UNK-014 | open | open | [[2026-10-09-broker-data-coach-limits#^c14]] |
| UNK-004 | open | open | [[2026-10-09-broker-data-coach-limits#^c20]] |
| UNK-016 | - | open | [[2026-10-09-broker-data-coach-limits#^c22]] |
| R-09 | - | open | [[2026-10-09-broker-data-coach-limits#^c18]] |
| Q-OPS-07@INI-001 | - | assumed | [[2026-10-09-broker-data-coach-limits#^c18]] |
| R-PTN-01 | open | unknown | [[2026-10-09-broker-data-coach-limits#^c19]] |
| R-REG-04 | - | unknown | [[2026-10-09-broker-data-coach-limits#^c19]] |
| R-FIN-05 | - | open | [[2026-10-09-broker-data-coach-limits#1. After the read-back, 2026-10-09]] |
| R-DAT-02 | - | open | [[2026-10-09-broker-data-coach-limits#1. After the read-back, 2026-10-09]] |
| R-PTN-05 | - | open | [[2026-10-09-broker-data-coach-limits#1. After the read-back, 2026-10-09]] |
