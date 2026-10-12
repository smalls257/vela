---
id: 2026-10-09-first-release
type: session
title: "Shape: first release"
date: 2026-10-09
modes: [shape]
status: closed
summary: "Shape: first release is Teach on paper (Option A), a paper-trading coach with equities only and no real orders. It waits on compliance's written confirmation and Brightwater's sandbox terms."
---

# 2026-10-09 Shape: first release

## Captures

- [thought] (claude) Option A, "Teach on paper": the first release is a coach that teaches one stock at a time, with lessons and simulated trades on Brightwater's sandbox paper accounts, and "ready" is a track the reader passes. It costs the least, because it places no real order and so stays clear of the no-live-trading ban, but the CEO's "trades for them" is not in it and the coach teaches only equities, since the agreement and the licence cover no options. It rules out real orders and options in the first release. → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c01
- [thought] (claude) Option B, "Recommend, reader taps": the first release is a coach that suggests a trade on an equity the reader picked, with its reasoning and the risk beside it, and the reader taps to place the order through Brightwater. It costs a live order path, wording that carries the advice risk, and quotes delayed 15 minutes feeding order decisions. It rules out automatic ordering and options, and it holds only if compliance's ban does not cover orders the reader places through a partner broker. → park ^c02
- [thought] (claude) Option C, "Automatic for the ready": the first release is the CEO's version, where the coach teaches and then places equity orders itself for readers who opted in and passed "ready". It costs the most: a live order path, an opt-in and audit trail, the compliance ruling and the legal view on advice, all by March. It rules out nothing technically, but it runs straight into the reported ban on live trading and cannot ship by March unless compliance rules that orders through a partner broker are allowed. → park ^c03
- [thought] (Jordan Reyes, product lead) Going with A: "nothing regulated goes live before counsel and Brightwater sign off, and that's non-negotiable." → keep: [[02-constraints|CST-3]] (inkling) ^c04
- [thought] (Jordan Reyes, product lead) Option B rejected: "B and C both need a compliance ruling nobody's written." → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c05
- [thought] (Jordan Reyes, product lead) Option C rejected, for the same reason as B: it needs a compliance ruling nobody has written. → keep: [[04-solution-strategy#The core move|solution-strategy]] (assumption) ^c06
- [worry] (Jordan Reyes, product lead) A means "no trades by March, and the CEO asked for trades, so someone's got to own that conversation and I'm honestly not sure she accepts it." → [[11-unknowns-and-risks#UNK-017 CEO and a paper-only release|UNK-017]] (open) ^c07
- [thought] (Jordan Reyes, product lead) F1.22: "CEO conversation is mine. I'll take it to her once Brightwater and compliance sign off. She asked for trades, we're delivering paper trading, no options, no real orders. That's the tradeoff, and I'll own it." Open: whether the CEO accepts an equities-only paper release; the product lead owns it. That the agreement and licence cover no options rests on the summaries only, see UNK-012. → [[11-unknowns-and-risks#Question ledger|R-REG-05]] (unknown) ^c08
- [thought] (Jordan Reyes, product lead) F1.21: "I believe paper trading stays clear of the ban, but compliance has to confirm in writing." A belief with no source, and a gate that blocks Option A. Compliance owes the written confirmation, and the compliance person is not yet named. → [[11-unknowns-and-risks#Question ledger|R-REG-03]] (assumed) ^c09
- [thought] (Jordan Reyes, product lead) F1.12: "Brightwater's agreement has to let the sandbox work in a consumer product." Open, and a gate that blocks Option A. The partnerships manager holds the agreement, and their name is not recorded (UNK-009, UNK-015). → [[11-unknowns-and-risks#Question ledger|Q-PTN-05@PTY-01]] (unknown) ^c10
- [thought] (Jordan Reyes, product lead) F1.6: "also open, it's in the agreement." Whether the sandbox costs anything and the agreement allows a paper-trading product is an open question the signed agreement answers. → [[11-unknowns-and-risks#Question ledger|R-FIN-06]] (unknown) ^c11
- [thought] (Jordan Reyes, product lead) F1.9: "honestly not sure. Legal owns that, whether data can carry to a live account without fresh consent." Open, for legal. The legal owner is not named (UNK-006). → [[11-unknowns-and-risks#Question ledger|R-DAT-01]] (unknown) ^c12
- [thought] (Jordan Reyes, product lead) F1.25: "5 is open. Someone writes the lessons and defines 'ready'." Open, no owner named. → [[11-unknowns-and-risks#Question ledger|R-OPS-01]] (unknown) ^c13
- [thought] (Jordan Reyes, product lead) F1.7: "mobile lead needs to confirm they have March capacity." Open, for the mobile lead, who is not named. → [[11-unknowns-and-risks#Question ledger|R-FIN-01]] (unknown) ^c14
- [thought] (Jordan Reyes, product lead) F1.18: "CFO holds the budget. I don't know the numbers." Open, for the CFO, who is not named (UNK-005). → [[11-unknowns-and-risks#Question ledger|R-PTN-03]] (unknown) ^c15

## Reviews

### 1. before options, 2026-10-09

- **Coverage:** FIN found 8, 1 dropped; DAT found 3, 5 dropped; PTN found 9, 2 dropped; REG found 7, 4 dropped; OPS found 5, 5 dropped
- **Dropped:** 17 findings, all for form. 15 named a copy ID the vault does not owe in that form (Q-FIN-03, Q-DAT-01 twice, Q-DAT-04, Q-DAT-05 twice, Q-REG-01 twice, Q-REG-05 twice, Q-OPS-04, Q-OPS-05, Q-OPS-06 three times); 1 named R-PTN-01, which has no open reviewer question; 1 [PTN] quote did not mention what the finding is about. Their questions: who carries the balances Brightwater holds (FIN); what reader data crosses to Brightwater and whether suggestions or automatic trading are a new purpose for reader data (DAT); whether the coach plus Brightwater is a joint offer and who is liable to the reader when it fails (REG); whether the CEO will accept no real orders and no options, and who tells her (OPS); who owns a price source and out-of-hours cover for the order path (OPS); who holds the Brightwater agreement and what leaving it costs (PTN); which broker would cover options (PTN). Re-running the areas would raise them again in the right form.
- **Merged:** [PTN] into F1.11: For option C, who keeps the consent and audit record, does the Brightwater agreement require it to be shared, and how does a reader's opt-in carry across the two systems?; [REG] into F1.6: Does the Brightwater agreement allow its sandbox to be used in a consumer-facing product, and what does section 7.2 require before the content ships?; [REG] into F1.5: Does the Quoteline licence allow delayed quotes to drive trade suggestions or orders, and is a stale-price disclosure needed?; [OPS] into F1.18: What do the three options cost against the allocated budget, and who holds that budget?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | R-FIN-04 | Does the allocated budget assume live trading through a broker? Who pays for the order path, the audit trail, the legal work and any broker fees if it does? | "It costs the most: a live order path, an opt-in and audit trail, the compliance ruling and the legal view on advice, all by March." in [[2026-10-09-first-release]] |
| F1.2 | FIN | normal | R-FIN-04 | Who pays Brightwater integration and any per-order fees for option B, and are they inside the allocated budget (UNK-005)? | "It costs a live order path, wording that carries the advice risk" in [[2026-10-09-first-release]] |
| F1.3 | FIN | high | R-FIN-02 | If readers lose money following option B's suggestions, who carries the liability, and is any budget set aside for legal review, registration or insurance? | "Readers may lose money following the coach's recommendations, and TickerTalk could be sued." in [[11-unknowns-and-risks]] |
| F1.4 | FIN | high | R-FIN-03 | What would registration or licensing cost for options B and C, and is it inside the allocated budget and the March date? | "which would need registration and turn the product into a year of legal work" in [[11-unknowns-and-risks]] |
| F1.5 | FIN, REG | high | R-FIN-05 | Does the Quoteline licence allow delayed quotes to feed order decisions? If not, who pays for a real-time feed, and who bears losses from trades made on delayed prices? | "quotes delayed 15 minutes feeding order decisions" in [[2026-10-09-first-release]] |
| F1.6 | FIN, REG | normal | new | Does the signed Brightwater agreement charge anything for sandbox use, and does it allow a paper-trading product at all (UNK-009)? | "simulated trades on Brightwater's sandbox paper accounts" in [[2026-10-09-first-release]] |
| F1.7 | FIN | normal | R-FIN-01 | How much mobile team capacity does each of options A, B and C take, is it inside the allocated budget, and what TickerTalk work is displaced? | "It costs the least" in [[2026-10-09-first-release]] |
| F1.8 | FIN | high | new | For options B and C, how does a reader fund the Brightwater account, who handles deposits and withdrawals, and what happens to the balance if the reader closes the account or the coach is withdrawn? | "places equity orders itself for readers who opted in and passed ”ready”" in [[2026-10-09-first-release]] |
| F1.9 | DAT | normal | R-DAT-01 | What data do the simulated account and the reader's progress hold, who holds it, and may it carry over to a live broker account without fresh consent? | "lessons and simulated trades on Brightwater's sandbox paper accounts" in [[2026-10-09-first-release]] |
| F1.10 | DAT | high | R-DAT-02 | May the coach use Quoteline data to generate suggestions, or only to display quotes, and is an addendum needed before Option B? | "quotes delayed 15 minutes feeding order decisions" in [[2026-10-09-first-release]] |
| F1.11 | DAT, PTN | high | R-DAT-01 | What does the opt-in cover and what does the audit trail hold, who keeps them, and can they carry over to the broker account without fresh consent? | "an opt-in and audit trail" in [[2026-10-09-first-release]] |
| F1.12 | PTN | high | Q-PTN-05@PTY-01 | For option A, does the signed Brightwater agreement allow the sandbox to be used in a reader-facing product, and can the agreement be assigned or its control changed? | "simulated trades on Brightwater's sandbox paper accounts" in [[2026-10-09-first-release]] |
| F1.13 | PTN | high | Q-PTN-02@PTY-01 | For option B, what do the Brightwater agreement's terms say about data sharing, consent and use of order and account data by TickerTalk and by any new owner? | "the reader taps to place the order through Brightwater" in [[2026-10-09-first-release]] |
| F1.14 | PTN | high | Q-PTN-06@PTY-01 | For option B, does Brightwater have to approve the coach's suggestion wording (section 7.2), what notice or change process applies, and who gives it? | "wording that carries the advice risk" in [[2026-10-09-first-release]] |
| F1.15 | PTN | high | R-PTN-05 | Does the Quoteline licence allow its delayed quotes to drive coaching and order decisions, and is 15-minute-delayed data acceptable for orders placed through Brightwater? | "quotes delayed 15 minutes feeding order decisions" in [[2026-10-09-first-release]] |
| F1.16 | PTN | high | Q-PTN-02@PTY-01 | For option C, does the signed Brightwater agreement allow automatic orders on a reader's behalf, what consent does it require, and does it limit live trading? | "places equity orders itself for readers who opted in and passed ”ready”" in [[2026-10-09-first-release]] |
| F1.17 | PTN | normal | R-PTN-02 | For options B and C, what service levels, rate limits and volume limits does the Brightwater agreement give the order API, and can it carry the coach's expected volume by March? | "a live order path, an opt-in and audit trail, the compliance ruling and the legal view on advice, all by March" in [[2026-10-09-first-release]] |
| F1.18 | PTN, OPS | normal | R-PTN-03 | Does the allocated budget cover Brightwater and Quoteline fees, broker integration and legal costs for each option, and who pays if it does not? | "It costs the least, because it places no real order" in [[2026-10-09-first-release]] |
| F1.19 | PTN | normal | R-PTN-04 | Which existing agreements (full Brightwater agreement, full Quoteline licence, readers' terms, content licences) do the options rely on, and what limits do they put on the coach? | "since the agreement and the licence cover no options" in [[2026-10-09-first-release]] |
| F1.20 | REG | high | R-REG-02 | What date does compliance's year one start from, and does the ban end before or after the March launch? | "it runs straight into the reported ban on live trading" in [[2026-10-09-first-release]] |
| F1.21 | REG | high | R-REG-03 | Will compliance confirm in writing that simulated trades on Brightwater's sandbox accounts are outside the live-trading ban and outside licensing? | "places no real order and so stays clear of the no-live-trading ban" in [[2026-10-09-first-release]] |
| F1.22 | REG | high | new | Does the signed Brightwater agreement exclude options, and has the CEO accepted an equities-only first release? | "the coach teaches only equities, since the agreement and the licence cover no options" in [[2026-10-09-first-release]] |
| F1.23 | REG | high | new | Who in legal will rule in writing whether suggested or automatic trades are investment advice, and by when, given the March date? | "the compliance ruling and the legal view on advice, all by March" in [[2026-10-09-first-release]] |
| F1.24 | REG | high | new | Is TickerTalk or Brightwater licensed to place orders on a customer's behalf without a tap, and what must the opt-in and audit trail satisfy? | "an opt-in and audit trail" in [[2026-10-09-first-release]] |
| F1.25 | OPS | normal | new | Who writes the lessons and the 'ready' track and who operates the Brightwater sandbox accounts? What does 'ready' mean? | "”ready” is a track the reader passes" in [[2026-10-09-first-release]] |
| F1.26 | OPS | high | new | Who in compliance will rule in writing on partner-broker orders, and by what date, given the January demo? | "it holds only if compliance's ban does not cover orders the reader places through a partner broker" in [[2026-10-09-first-release]] |
| F1.27 | OPS | high | new | Which teams and named people build and run the order path, opt-in and audit trail, and does the mobile team have capacity alongside TickerTalk itself? | "a live order path, an opt-in and audit trail, the compliance ruling and the legal view on advice, all by March" in [[2026-10-09-first-release]] |
| F1.28 | OPS | high | new | Who decides between the CEO and compliance, and by what date? Does the year-one ban cover March? | "cannot ship by March unless compliance rules that orders through a partner broker are allowed" in [[2026-10-09-first-release]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| solution-strategy | inkling | assumption | [[2026-10-09-first-release#^c01]] |
| CST-3 | - | inkling | [[2026-10-09-first-release#^c04]] |
| UNK-017 | - | open | [[2026-10-09-first-release#^c07]] |
| UNK-018 | - | open | [[2026-10-09-first-release#^c13]] |
| UNK-019 | - | open | [[2026-10-09-first-release#^c14]] |
| R-REG-05 | - | unknown | [[2026-10-09-first-release#^c08]] |
| R-REG-03 | open | assumed | [[2026-10-09-first-release#^c09]] |
| Q-PTN-05@PTY-01 | - | unknown | [[2026-10-09-first-release#^c10]] |
| R-FIN-06 | - | unknown | [[2026-10-09-first-release#^c11]] |
| R-DAT-01 | open | unknown | [[2026-10-09-first-release#^c12]] |
| R-OPS-01 | - | unknown | [[2026-10-09-first-release#^c13]] |
| R-FIN-01 | open | unknown | [[2026-10-09-first-release#^c14]] |
| R-PTN-03 | open | unknown | [[2026-10-09-first-release#^c15]] |
| R-FIN-07 | - | open | [[2026-10-09-first-release#1. before options, 2026-10-09]] |
| R-REG-06 | - | open | [[2026-10-09-first-release#1. before options, 2026-10-09]] |
| R-REG-07 | - | open | [[2026-10-09-first-release#1. before options, 2026-10-09]] |
| R-OPS-02 | - | open | [[2026-10-09-first-release#1. before options, 2026-10-09]] |
| R-OPS-03 | - | open | [[2026-10-09-first-release#1. before options, 2026-10-09]] |
| R-OPS-04 | - | open | [[2026-10-09-first-release#1. before options, 2026-10-09]] |
