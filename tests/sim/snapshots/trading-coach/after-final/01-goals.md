---
id: goals
type: initiative-section
title: Goals
arc42: "§1"
state: inkling
owner: "@solution-lead"
authored: mixed
sources: [SRC-05, SRC-06, SRC-09, SRC-16]
---

# Goals

The one goal so far is the CEO's, as the product lead heard it in a meeting: a coach that teaches people to trade one stock or option at a time, and trades for them when they are ready, and [[sources#SRC-05|the CEO's memo of 28 September]] expects the same. No one has defined it further. The CEO has not been asked what the coach, "ready" or "trades for them" means, and the product lead reads "trades for them" most differently from the others who heard it. The board wants a demo in January and launch by March. [[sources#SRC-06|The ML team's backtest summary]] says Signal's daily long-short portfolio returned 31% a year against 11% for the index over 2015 to 2025, on the 50 largest US stocks as of September 2026, entering at each day's close and leaving out transaction costs. The stock list is fixed at the later date, and the summary does not say whether it was picked again for each year, which [[11-unknowns-and-risks#UNK-013 Signal baseline|the baseline question]] holds. The ML team wants to train on TickerTalk users' watchlists next, but the product lead says that is a wish and not a committed step. The memo also calls Signal the company's edge, which is the CEO's expectation and not something the backtest shows.

[[sources#SRC-16|The answers the product lead gathered by 9 October]] change the Signal picture. The ML lead re-ran Signal against the S&P 500 total return with the stock list as it stood each year, and the edge falls from 31% to about 2% a year before costs, so the 31% is the earlier backtest's figure and the re-run is the later one. Why the two differ is not recorded, and [[11-unknowns-and-risks#UNK-013 Signal baseline|the baseline question]] holds both. The ML lead says Signal stays out of release one and owns it, which is a plan and so an assumption. The privacy lead's review of 7 October says training Signal on readers' watchlists or practice trades is a new purpose and needs fresh opt-in consent, and that release one trains nothing on reader data, the second part being an assumption.

A later note from the CEO, dated 6 October, narrows the plan. [[sources#SRC-09|The note]] says release one is lessons and paper trading on a fixed list of US stocks, and that the CEO accepts that as the first release if the January board demo shows where it goes next. It says trading for customers waits for a later release, after counsel and Brightwater sign off, and that where compliance and the CEO disagree the CEO decides once counsel has ruled. These are the CEO's intentions, not agreed with compliance, and the note does not say whether the March launch still holds for release one.

## Where it stands

<!-- generated:where-it-stands sha=3843c93f: do not edit, run vela render -->
**Apps on the ladder**

| App | Stage | Blocking unknowns | Unexamined cells | Contracts decided or fact |
|---|---|---|---|---|
| [[tickertalk-building-blocks\|TickerTalk]] | target | 0 | 0 | 3 of 3 |
| [[coach-building-blocks\|Coach]] | contracts | 1 | 0 | 4 of 5 |

**Handed off:** [[coach-building-blocks|Coach]] (@coach-lead, 2026-10-09, PR pending)

**Open unknowns**

| Unknown | Owner | Ask by | Blocks |
|---|---|---|---|
| [[11-unknowns-and-risks#UNK-001 What the CEO means\|UNK-001]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-002 Who the target users are\|UNK-002]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing\|UNK-003]] | @sim-lead (product lead) | 2026-10-13 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-007 When year one starts\|UNK-007]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-008 Who settles CEO versus compliance\|UNK-008]] | @sim-lead (product lead) | 2026-12-04 | nothing |
| [[11-unknowns-and-risks#UNK-009 Signed broker agreement terms\|UNK-009]] | @partnerships-manager (partnerships manager, holder of the agreement; the product lead does the asking) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-010 Two mandates, one timeline\|UNK-010]] | @sim-lead (product lead) | 2026-12-04 | nothing |
| [[11-unknowns-and-risks#UNK-012 Options coverage\|UNK-012]] | @partnerships-manager (partnerships manager, holder of the agreement; the product lead does the asking) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-013 Signal baseline\|UNK-013]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline\|UNK-014]] | @sim-lead (product lead) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-017 CEO and a paper-only release\|UNK-017]] | @sim-lead (product lead) | 2026-10-10 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-019 Mobile capacity for March\|UNK-019]] | @mobile-lead (mobile lead) | 2026-10-14 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-021 Legal clearance of the stock list\|UNK-021]] | @sim-lead (product lead, finding counsel's name this week; counsel gives the ruling) | 2026-10-16 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-023 Coverage of every stock on the list\|UNK-023]] | @partnerships-manager (partnerships manager, for Brightwater) @data-engineer (data engineer, for Quoteline) | 2026-12-31 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes\|UNK-038]] | @partnerships-manager (partnerships manager, for Quoteline) | 2026-10-16 | [[coach-building-blocks#CON-004 Quoteline delayed quotes\|CON-004 Quoteline delayed quotes]] |
| [[11-unknowns-and-risks#UNK-040 Does the March beta fit the review timeline\|UNK-040]] | @sim-lead (product lead, asking partnerships and compliance) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-046 Coach lead's names for the containers\|UNK-046]] | @sim-lead (product lead, asking the Coach lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-055 Date of Brightwater's written reply\|UNK-055]] | @partnerships-manager (partnerships manager, for Brightwater) | 2026-10-13 | nothing |
| [[11-unknowns-and-risks#UNK-056 Full texts of the three partner documents\|UNK-056]] | @sim-lead (product lead, asking the partners) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-057 Which team owns each capability after the change\|UNK-057]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-058 March launch gate and who decides a slip\|UNK-058]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-059 Whether reader data may go to Brightwater and to a new party\|UNK-059]] | @partnerships-manager (partnerships manager, holder of the agreement; the product lead does the asking) | 2026-10-16 | [[EPC-002-coach-paper-trading\|EPC-002-coach-paper-trading]] |
| [[11-unknowns-and-risks#UNK-060 Lawful basis for the data Coach holds\|UNK-060]] | @sim-lead (product lead, asking @privacy-lead) | 2026-10-16 | [[EPC-002-coach-paper-trading\|EPC-002-coach-paper-trading]] |
| [[11-unknowns-and-risks#UNK-061 Fieldnote Learning: locked in, or 30 days' notice\|UNK-061]] | @sim-lead (product lead, holder of the contract) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-062 Written confirmation of the board-demo exemption\|UNK-062]] | @partnerships-manager (partnerships manager, holder of the agreement; the product lead does the asking) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-063 What data the January demo runs on\|UNK-063]] | @sim-lead (product lead, who defines the demo; the Coach lead runs Coach) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-064 What the CEO's decision after the January demo changes\|UNK-064]] | @sim-lead (product lead, asking the CEO) | 2027-02-15 | nothing |
| [[11-unknowns-and-risks#UNK-065 Who the compliance consultant is\|UNK-065]] | @sim-lead (product lead) | 2026-10-12 | [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing\|the compliance ruling in writing]] |
| [[11-unknowns-and-risks#UNK-066 Brightwater's position on live trading and its date\|UNK-066]] | @partnerships-manager (partnerships manager, for Brightwater; the product lead does the asking) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-067 Who covers Coach on demo week\|UNK-067]] | @sim-lead (product lead, who asks the platform engineer) | 2026-10-31 | nothing |
| [[11-unknowns-and-risks#UNK-068 Who owns escalation after two rejected rounds\|UNK-068]] | @partnerships-manager (partnerships manager, who read the agreement in full; the product lead does the asking) | 2026-10-30 | nothing |

**Last session:** 2026-10-09

**Coverage gaps:** 3, listed on [[13-epics|Epics]]

**Delivery status:** not tracked in this vault
<!-- /generated:where-it-stands -->

## Progress by app

<!-- generated:progress-map sha=d1cd42b0: do not edit, run vela render -->
**As of:** 2026-10-09, the last session

| App | Stage | Inkling | Assumption | Fact | Decided | Oldest open unknown | Next |
|---|---|---|---|---|---|---|---|
| [[tickertalk-building-blocks\|TickerTalk]] | target | 0 | 0 | 0 | 3 (1 by override) | none | epics EPC-003 |
| [[coach-building-blocks\|Coach]] | contracts | 0 | 1 | 0 | 5 (1 by override) | [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes\|UNK-038]] opened 2026-10-09 | probe UNK-038 |
<!-- /generated:progress-map -->

## Why now

## Goals

| ID | Goal | Measure | State |
|---|---|---|---|
| G1 | The coach teaches people to trade one stock or option at a time, and trades for them when they're ready | Not recorded | inkling |
