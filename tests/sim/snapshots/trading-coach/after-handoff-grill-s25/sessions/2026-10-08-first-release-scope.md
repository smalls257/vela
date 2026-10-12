---
id: 2026-10-08-first-release-scope
type: session
title: "Shape: first release scope"
date: 2026-10-08
modes: [shape]
status: closed
summary: "Shape: first release scope. Picked Option B (stocks with a hand confirm) as an assumption, with A as the fallback and C rejected. Added UNK-019 on who runs the order path."
---

# 2026-10-08 Shape: first release scope

## Captures

- [thought] (claude) Option A, teach on paper: the first release only teaches, with lessons on stocks and practice trades in Brightwater's sandbox paper accounts (SRC-01). No real money moves and Signal's guesses are not shown as picks. Costs the smallest build and compliance read, and earns nothing. Rules out "trades for them", real-money trading and options on real money for the first release. → park ^c01
- [thought] (claude) Option B, stocks with a hand confirm: the first release teaches, and when a user is ready the coach prepares a stock order that the user confirms by hand, placed through Brightwater's API. Costs the account link, order placement and a compliance sign-off, which may run to February (UNK-011). Rules out options and any order placed without the user's tap. → park ^c02
- [thought] (claude) Option C, the CEO's ask as written: the first release teaches one stock or option at a time and trades for users within a limit they set, for all 400,000 TickerTalk users (SRC-04, a plan). Costs the most: options cover (UNK-014), auto-trading and account link terms (UNK-016), registration or counsel (UNK-010), and a build team nobody has yet (UNK-009). Rules out nothing, but every open unknown on the page sits under it. → park ^c03
- [thought] (product lead) On A: "A's what I picked, but it doesn't solve the problem." Reaction to Option A: it is the safe one, and it falls short of the ask. → keep: [[04-solution-strategy|first release scope]] (assumption) ^c04
- [thought] (product lead) On C: "C is dead—no team, no path to March." Reaction to Option C. → keep: [[04-solution-strategy|first release scope]] (assumption) ^c05
- [thought] (product lead) "I'm going with B." Picks Option B, stocks with a hand confirm, over A and C. "B gets us there if the agreement allows it." → keep: [[04-solution-strategy|first release scope]] (assumption) ^c06
- [thought] (product lead) Rejects A as the first release, with this reason: it does not solve the problem. A stays as the fallback: "If Brightwater says no, we fall back to A and the CEO's frustrated at the demo." → keep: [[04-solution-strategy|first release scope]] (assumption) ^c07
- [thought] (product lead) Rejects C, with this reason: no team and no path to March. → keep: [[04-solution-strategy|first release scope]] (assumption) ^c08
- [thought] (product lead) F1.14: "Everything's on tomorrow's read." Whether Brightwater allows the account link and coach-prepared orders is an open question for Partnerships, answered by reading the agreement; it waits on UNK-016 and UNK-004. → keep: [[11-unknowns-and-risks#Question ledger|R-PTN-03]] (unknown) ^c09
- [worry] (product lead) If the agreement says no, the fallback is A and the CEO is frustrated at the January demo. → drop: already held by UNK-004 and UNK-016, and A is the recorded fallback ^c10
- [thought] (product lead) F1.23: "F1.23 is tomorrow's read—Brightwater's agreement says who owes what, or we're stuck." Who owes customers the money at Brightwater is an open question for Partnerships, answered by reading the agreement; it waits on UNK-004 and UNK-018. → keep: [[11-unknowns-and-risks#Question ledger|R-REG-07]] (unknown) ^c11
- [thought] (product lead) F1.25: "F1.25 is what I believe (W1), but the consultant hasn't confirmed it and we're betting the whole approach on it." A belief with no source: a coach-prepared order the user confirms is not regulated advice. The plan rests on it (load-bearing); the signpost is the consultant's answer, UNK-010. → keep: [[11-unknowns-and-risks#Question ledger|R-REG-10]] (assumed) ^c12
- [worry] (product lead) F1.28: "mobile can't come off the news app, and ML is three people who need to stay on Signal. Honestly not sure how we staff the order path without pulling someone else in or hiring, and nobody's been asked yet." Who runs the order path is an open question; no team is named and nobody has been asked. → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-01]] (unknown) ^c13
- [unknown] (claude, from product lead) Who runs the order path once real stock orders flow, including out of hours, when mobile cannot leave the news app and ML must stay on Signal? Owner: @sim-lead (product lead), answer from the CEO. Ask by: 2026-10-09. Blocks: Option B, stocks with a hand confirm. F1.28 waits on it. The product lead: "New unknown—CEO owns it, ask by tomorrow's read." → keep: [[11-unknowns-and-risks#UNK-019 Who runs the order path|UNK-019]] (open) ^c14

## Reviews

### 1. Before options, 2026-10-08

- **Coverage:** FIN found 5, 3 dropped; DAT found 5, 2 dropped; PTN found 7, 2 dropped; REG found 9, 5 dropped; OPS found 11
- **Dropped:** 12 findings: FIN R-FIN-01 (named an R- id with no open reviewer question); FIN R-FIN-05 (named an R- id with no open reviewer question); FIN R-FIN-04 (named an R- id with no open reviewer question); DAT R-DAT-03 (named an R- id with no open reviewer question); DAT R-DAT-04 (named an R- id with no open reviewer question); PTN new question (a page this session did not change); PTN new question (the quote does not mention what the finding is about); REG R-REG-04 (named an R- id with no open reviewer question); REG R-REG-05 (named an R- id with no open reviewer question); REG R-REG-08 (named an R- id with no open reviewer question); REG R-REG-03 (named an R- id with no open reviewer question); REG new question (a page this session did not change).
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | For Options B and C, who holds and who owes the customer money once the coach places orders through Brightwater? Does Option A really involve no balances, deposits or credits, including the sandbox paper accounts? | "No real money moves and Signal's guesses are not shown as picks." in [[2026-10-08-first-release-scope]] |
| F1.2 | FIN | normal | Q-FIN-02@INI-001 | Who funds Option A and its running cost, and does it fit inside the CFO's 2.5 million? Is a first release that earns nothing acceptable to the CEO? | "Costs the smallest build and compliance read, and earns nothing." in [[2026-10-08-first-release-scope]] |
| F1.3 | FIN | normal | R-FIN-02 | How would the coach earn money under Option B, and what return is expected against the 2.5 million? Who pays for the account link and order placement? | "Costs the account link, order placement and a compliance sign-off, which may run to February (UNK-011)." in [[2026-10-08-first-release-scope]] |
| F1.4 | FIN | normal | R-FIN-03 | What would registration or a contracted registered adviser cost under Options B and C, and is it inside the 2.5 million? | "registration or counsel (UNK-010)" in [[2026-10-08-first-release-scope]] |
| F1.5 | FIN | normal | Q-FIN-02@INI-001 | Who pays for the Option C build team and its running cost, and is it inside the budget? Are there cost estimates for A, B and C to compare against it? | "a build team nobody has yet (UNK-009)" in [[2026-10-08-first-release-scope]] |
| F1.6 | DAT | normal | Q-DAT-04@SV-01 | Which system is the record of each user's balance for the practice (paper) accounts in A and the real accounts in B and C? Who owes real balances to the user (UNK-018)? | "**Holder:** [[03-context-and-scope#PTY-01 Brightwater]] (fact, SRC-01)" in [[03-context-and-scope]] |
| F1.7 | DAT | high | R-DAT-01 | Is Quoteline (SRC-02) the quote source? Does its licence allow displaying quotes to users in the coach, and at what user count? Does Option A need quotes at all? | "Source and holder of that agreement were not named." in [[11-unknowns-and-risks]] |
| F1.8 | DAT | normal | R-DAT-02 | Under Option B or C, who holds each user's orders, positions and limits (Kestrel, TickerTalk or Brightwater)? How do the user's consent and progress carry between TickerTalk and Brightwater? Is the link Kestrel's or TickerTalk's? | "Costs the account link, order placement and a compliance sign-off, which may run to February (UNK-011)." in [[2026-10-08-first-release-scope]] |
| F1.9 | DAT | high | new | What did TickerTalk's privacy notice and terms tell its 400,000 users? Do they allow sharing user data with Brightwater and using it for trading? Is new, separate consent needed for B and C? | "for all 400,000 TickerTalk users (SRC-04, a plan)" in [[2026-10-08-first-release-scope]] |
| F1.10 | DAT | normal | new | What user data goes to Brightwater for sandbox paper accounts under Option A? Does the agreement allow that, and is there a limit on sandbox users? | "practice trades in Brightwater's sandbox paper accounts (SRC-01)" in [[2026-10-08-first-release-scope]] |
| F1.11 | PTN | high | Q-PTN-03@PTY-01 | Option A ("practice trades in Brightwater's sandbox paper accounts (SRC-01)"): who holds the Brightwater agreement, when does it end, and what would leaving or changing it cost? Which clause permits paper accounts for TickerTalk users? | "the full text is still to fetch" in [[03-context-and-scope]] |
| F1.12 | PTN | normal | Q-PTN-06@PTY-01 | For options B and C, what notice does a change to the Brightwater agreement need, who gives it, and what happens to a live release if Brightwater refuses? | "can Brightwater refuse something already shipped?" in [[11-unknowns-and-risks]] |
| F1.13 | PTN | high | R-PTN-02 | Option B ("the coach prepares a stock order that the user confirms by hand") and Option C: is Quoteline (SRC-02) the quotes source? Does its licence allow use where users trade real money, and what are its cost and notice period? Does Option A need quotes at all? | "Where would the quotes in the product come from, and on what terms? Source and holder of that agreement were not named." in [[11-unknowns-and-risks]] |
| F1.14 | PTN | high | R-PTN-03 | Option B ("Costs the account link, order placement and a compliance sign-off"): will Brightwater allow the account link and coach-prepared orders, and under whose licence? Who carries the liability if it fails? | "Does the Brightwater agreement allow the coach to place orders for a user and to link a user's account, and does any approval rule in it reach what the coach shows users?" in [[11-unknowns-and-risks]] |
| F1.15 | PTN | high | R-PTN-04 | Option C ("for all 400,000 TickerTalk users"): what API, sandbox, uptime and user-cap limits does Brightwater set? Would a small cohort be needed for options A or B? Does the agreement cover options at all, given that the summary says it does not? | "What are its limits (sandbox, API, cohort size)" in [[11-unknowns-and-risks]] |
| F1.16 | PTN | normal | R-PTN-05 | Who will fetch and record the full Brightwater agreement, the Quoteline licence and TickerTalk's terms in sources, and by what date? Who will brief Partnerships? | "\| SRC-01 \| Brightwater Securities agreement summary \| Partnerships manager \| 2026-06-20 \| exists \| local only \|" in [[sources]] |
| F1.17 | PTN | normal | R-PTN-06 | How and when will Partnerships be told, given the 2026-10-09 ask-by date and no contact with Brightwater yet? What reason can be given for needing the agreement? | "**Who knows:** nobody has been told yet. Mobile, ML, Partnerships and compliance are all unaware of the ask." in [[03-context-and-scope]] |
| F1.18 | REG | normal | Q-REG-01@INI-001 | In options B and C, is the coach's order flow presented to customers as a joint Kestrel and Brightwater offer or as separate services, and which agreement terms govern that? | "the coach prepares a stock order that the user confirms by hand, placed through Brightwater's API" in [[2026-10-08-first-release-scope]] |
| F1.19 | REG | high | Q-REG-05@INI-001 | If a coach-prepared or auto-placed order loses money because of the coach, Signal or Brightwater, who is liable to the customer under options B and C, and what does the Brightwater agreement say about it? | "does it overfit and lose money on real money, leaving TickerTalk liable?" in [[11-unknowns-and-risks]] |
| F1.20 | REG | high | R-REG-01 | Who has authority to hold a launch if compliance sign-off is not done, and should sign-off be recorded as a constraint on the March date for options B and C? | "a compliance sign-off, which may run to February (UNK-011)" in [[2026-10-08-first-release-scope]] |
| F1.21 | REG | high | R-REG-02 | Which reading of 'trades for them' does each option implement, and which regulatory category (education, advice, order handling, discretionary trading) does each reading fall under? | "trades for users within a limit they set" in [[2026-10-08-first-release-scope]] |
| F1.22 | REG | high | R-REG-06 | Which legal entity, Kestrel or TickerTalk, holds the Brightwater agreement and is in front of customers in options A, B and C? | "It is not recorded whether TickerTalk is a Kestrel app." in [[11-unknowns-and-risks]] |
| F1.23 | REG | normal | R-REG-07 | For options B and C, who owes customers the money held at Brightwater, and what protection do customers have if Brightwater fails? | "but not who owes it to the customer." in [[11-unknowns-and-risks]] |
| F1.24 | REG | high | new | What evidence supports that option A needs only a small compliance read, and has the consultant or counsel confirmed that teaching with paper trades is education and not advice? | "Costs the smallest build and compliance read, and earns nothing." in [[2026-10-08-first-release-scope]] |
| F1.25 | REG | high | new | Does a coach-prepared order that the user confirms count as regulated advice or recommendation, and what must Kestrel do (registration, suitability, disclosures) before doing it? | "the coach prepares a stock order that the user confirms by hand" in [[2026-10-08-first-release-scope]] |
| F1.26 | REG | high | new | Which regulator and which registration or licence apply to options A, B and C, and who will confirm this with counsel before options are shown? | "registration or counsel (UNK-010)" in [[2026-10-08-first-release-scope]] |
| F1.27 | OPS | high | R-OPS-01 | For Option C, who builds, runs and supports the coach after launch, including out of hours while orders are live? Is it a new team or people pulled from mobile and ML, and who agrees to that? | "a build team nobody has yet (UNK-009)" in [[2026-10-08-first-release-scope]] |
| F1.28 | OPS | high | R-OPS-01 | For Option B, which team runs the order path and handles failures and out-of-hours incidents once real stock orders flow? | "the coach prepares a stock order that the user confirms by hand, placed through Brightwater's API" in [[2026-10-08-first-release-scope]] |
| F1.29 | OPS | normal | R-OPS-01 | For Option A, who writes the lessons and keeps the sandbox practice trades running, and from which team's time? | "lessons on stocks and practice trades in Brightwater's sandbox paper accounts (SRC-01)" in [[2026-10-08-first-release-scope]] |
| F1.30 | OPS | normal | R-OPS-02 | Who owns the coach after the pitch? Who can settle what 'trades for them' means, and will the CEO accept Option A or B as the first release? | "trades for users within a limit they set" in [[2026-10-08-first-release-scope]] |
| F1.31 | OPS | high | R-OPS-03 | If an order or money at Brightwater goes wrong, who answers the customer and handles the dispute: TickerTalk support, Kestrel, or Brightwater? Is that written down for Options B and C? | "Kestrel never holds customer money." in [[03-context-and-scope]] |
| F1.32 | OPS | high | Q-OPS-06@INI-001 | Who must be told and brought into the room before options are shown? That covers mobile, ML, Partnerships, compliance, TickerTalk support, and the users who would see the coach. | "Mobile, ML, Partnerships and compliance are all unaware of the ask." in [[03-context-and-scope]] |
| F1.33 | OPS | normal | Q-OPS-06@INI-001 | Who carries the load of a launch to all 400,000 users, and should a smaller cohort be offered as an option? Who confirms the 400,000 figure? | "for all 400,000 TickerTalk users (SRC-04, a plan)" in [[2026-10-08-first-release-scope]] |
| F1.34 | OPS | normal | Q-OPS-04@INI-001 | Are Kestrel and TickerTalk the same party, or two apps or teams with separate Brightwater links? Which one would each option run under? | "the summary (SRC-01) speaks of Kestrel. It is not recorded whether TickerTalk is a Kestrel app." in [[11-unknowns-and-risks]] |
| F1.35 | OPS | normal | Q-OPS-05@INI-001 | Does any option retire or pause something, such as news app work if mobile is pulled? Who relies on it? If nothing is retired, say so. | "the mobile team is on the news app" in [[03-context-and-scope]] |
| F1.36 | OPS | high | Q-OPS-07@INI-001 | Can one consultant two days a week clear Option B by February or Option C at all? Which March is meant, and who can hold a launch if sign-off is late? | "which may run to February (UNK-011)" in [[2026-10-08-first-release-scope]] |
| F1.37 | OPS | normal | new | Does a teach-only first release meet the CEO's goal, and who has evidence that readers would use a coach that earns nothing? | "Costs the smallest build and compliance read, and earns nothing." in [[2026-10-08-first-release-scope]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| 04-solution-strategy (first release scope) | inkling | assumption | [[2026-10-08-first-release-scope#^c06]] |
| UNK-019 | - | open | [[2026-10-08-first-release-scope#^c14]] |
| UNK-004 (blocks) | open | open | [[2026-10-08-first-release-scope#^c14]] |
| UNK-016 (blocks) | open | open | [[2026-10-08-first-release-scope#^c14]] |
| R-PTN-03 | open | unknown | [[2026-10-08-first-release-scope#^c09]] |
| R-REG-07 | open | unknown | [[2026-10-08-first-release-scope#^c11]] |
| R-REG-10 | - | assumed | [[2026-10-08-first-release-scope#^c12]] |
| R-OPS-01 | open | unknown | [[2026-10-08-first-release-scope#^c13]] |
| R-DAT-05 | - | open | [[2026-10-08-first-release-scope#1. Before options, 2026-10-08]] |
| R-DAT-06 | - | open | [[2026-10-08-first-release-scope#1. Before options, 2026-10-08]] |
| R-REG-09 | - | open | [[2026-10-08-first-release-scope#1. Before options, 2026-10-08]] |
| R-REG-11 | - | open | [[2026-10-08-first-release-scope#1. Before options, 2026-10-08]] |
| R-OPS-04 | - | open | [[2026-10-08-first-release-scope#1. Before options, 2026-10-08]] |
