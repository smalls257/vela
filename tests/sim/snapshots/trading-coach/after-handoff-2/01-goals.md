---
id: goals
type: initiative-section
title: Goals
arc42: "§1"
state: inkling
owner: "@solution-lead"
authored: mixed
sources: [SRC-05, SRC-06, SRC-09]
---

# Goals

The one goal so far is the CEO's, as the product lead heard it in a meeting: a coach that teaches people to trade one stock or option at a time, and trades for them when they are ready, and [[sources#SRC-05|the CEO's memo of 28 September]] expects the same. No one has defined it further. The CEO has not been asked what the coach, "ready" or "trades for them" means, and the product lead reads "trades for them" most differently from the others who heard it. The board wants a demo in January and launch by March. [[sources#SRC-06|The ML team's backtest summary]] says Signal's daily long-short portfolio returned 31% a year against 11% for the index over 2015 to 2025, on the 50 largest US stocks as of September 2026, entering at each day's close and leaving out transaction costs. The stock list is fixed at the later date, and the summary does not say whether it was picked again for each year, which [[11-unknowns-and-risks#UNK-013 Signal baseline|the baseline question]] holds. The ML team wants to train on TickerTalk users' watchlists next, but the product lead says that is a wish and not a committed step. The memo also calls Signal the company's edge, which is the CEO's expectation and not something the backtest shows.

A later note from the CEO, dated 13 October, narrows the plan. [[sources#SRC-09|The note]] says release one is lessons and paper trading on a fixed list of US stocks, and that the CEO accepts that as the first release if the January board demo shows where it goes next. It says trading for customers waits for a later release, after counsel and Brightwater sign off, and that where compliance and the CEO disagree the CEO decides once counsel has ruled. These are the CEO's intentions, not agreed with compliance, and the note does not say whether the March launch still holds for release one.

## Where it stands

<!-- generated:where-it-stands sha=a336c00f: do not edit, run vela render -->
**Apps on the ladder**

| App | Stage | Blocking unknowns | Unexamined cells | Contracts decided or fact |
|---|---|---|---|---|
| [[tickertalk-building-blocks\|TickerTalk]] | target | 2 | 6 | 2 of 3 |
| [[coach-building-blocks\|Coach]] | contracts | 4 | 3 | 4 of 5 |

**Handed off:** [[coach-building-blocks|Coach]] (@coach-lead, 2026-10-09, PR pending)

**Open unknowns**

| Unknown | Owner | Ask by | Blocks |
|---|---|---|---|
| [[11-unknowns-and-risks#UNK-001 What the CEO means\|UNK-001]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-002 Who the target users are\|UNK-002]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing\|UNK-003]] | @sim-lead (product lead) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-004 No live trading and broker orders\|UNK-004]] | @sim-lead (product lead) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-005 Size and holder of budget\|UNK-005]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-007 When year one starts\|UNK-007]] | @sim-lead (product lead) | 2026-11-13 | nothing |
| [[11-unknowns-and-risks#UNK-008 Who settles CEO versus compliance\|UNK-008]] | @sim-lead (product lead) | 2026-12-04 | nothing |
| [[11-unknowns-and-risks#UNK-009 Signed broker agreement terms\|UNK-009]] | @sim-lead (product lead) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-010 Two mandates, one timeline\|UNK-010]] | @sim-lead (product lead) | 2026-12-04 | nothing |
| [[11-unknowns-and-risks#UNK-011 Who owes Brightwater balances\|UNK-011]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-012 Options coverage\|UNK-012]] | @sim-lead (product lead) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-013 Signal baseline\|UNK-013]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-014 Watchlists and Quoteline\|UNK-014]] | @sim-lead (product lead) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-015 Two clauses to read in full\|UNK-015]] | @sim-lead (product lead) | 2026-10-23 | nothing |
| [[11-unknowns-and-risks#UNK-016 Coach's user-facing copy\|UNK-016]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-017 CEO and a paper-only release\|UNK-017]] | @sim-lead (product lead) | 2026-11-13 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-018 Who writes the lessons and defines ready\|UNK-018]] | @sim-lead (product lead) | 2026-10-16 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-020 Who owns Signal after launch\|UNK-020]] | @sim-lead (product lead) | 2026-10-30 | nothing |
| [[11-unknowns-and-risks#UNK-021 Legal clearance of the stock list\|UNK-021]] | @sim-lead (product lead, finding counsel's name this week; counsel gives the ruling) | 2026-10-16 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-022 Owner and budget for the stock list\|UNK-022]] | @sim-lead (product lead) | 2026-10-12 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-023 Coverage of every stock on the list\|UNK-023]] | @partnerships-manager (partnerships manager, for Brightwater) @data-engineer (data engineer, for Quoteline) | 2026-12-31 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-025 Options lessons in release one\|UNK-025]] | @sim-lead (product lead) | 2026-10-30 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-026 Counsel and lesson content\|UNK-026]] | @sim-lead (product lead) | 2026-10-23 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-027 Brightwater as the supervisor\|UNK-027]] | @sim-lead (product lead) | 2026-10-30 | [[04-solution-strategy\|04-solution-strategy]] |
| [[11-unknowns-and-risks#UNK-028 Where a Coach service can run\|UNK-028]] | @sim-lead (product lead, asking the mobile lead) | 2026-10-16 | [[coach-building-blocks\|coach-building-blocks]] |
| [[11-unknowns-and-risks#UNK-029 Where the paper record lives\|UNK-029]] | @sim-lead (product lead) | 2026-10-16 | [[coach-building-blocks\|coach-building-blocks]] |
| [[11-unknowns-and-risks#UNK-030 What identifies a reader\|UNK-030]] | @sim-lead (product lead, asking the mobile lead) | 2026-10-16 | [[tickertalk-building-blocks\|tickertalk-building-blocks]] |
| [[11-unknowns-and-risks#UNK-031 Who at Brightwater runs the content review\|UNK-031]] | @partnerships-manager (partnerships manager, for Brightwater) | 2026-10-12 | nothing |
| [[11-unknowns-and-risks#UNK-032 Can Brightwater shorten or move the review\|UNK-032]] | @partnerships-manager (partnerships manager, for Brightwater) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-033 Does the review reach an internal board demo\|UNK-033]] | @partnerships-manager (partnerships manager, for Brightwater) | 2026-10-12 | nothing |
| [[11-unknowns-and-risks#UNK-034 Who sees the January demo\|UNK-034]] | @sim-lead (product lead, asking the CEO) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-035 What happens when Brightwater rejects a lesson\|UNK-035]] | @partnerships-manager (partnerships manager, for Brightwater) | 2026-10-16 | nothing |
| [[11-unknowns-and-risks#UNK-036 Do the mobile rendering tests fit before the 14th\|UNK-036]] | @sim-lead (product lead, asking the mobile lead) | 2026-10-14 | [[tickertalk-building-blocks\|tickertalk-building-blocks]] |
| [[11-unknowns-and-risks#UNK-037 Brightwater test side of the sandbox\|UNK-037]] | @partnerships-manager (partnerships manager, for Brightwater) | 2026-10-16 | [[coach-building-blocks#CON-003 Brightwater sandbox\|CON-003 Brightwater sandbox]] |
| [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes\|UNK-038]] | @partnerships-manager (partnerships manager, for Quoteline) | 2026-10-16 | [[coach-building-blocks#CON-004 Quoteline delayed quotes\|CON-004 Quoteline delayed quotes]] |

**Last session:** 2026-10-09

**Coverage gaps:** 1, listed on [[13-epics|Epics]]

**Delivery status:** not tracked in this vault
<!-- /generated:where-it-stands -->

## Progress by app

<!-- generated:progress-map sha=59b81017: do not edit, run vela render -->
**As of:** 2026-10-09, the last session

| App | Stage | Inkling | Assumption | Fact | Decided | Oldest open unknown | Next |
|---|---|---|---|---|---|---|---|
| [[tickertalk-building-blocks\|TickerTalk]] | target | 0 | 3 | 0 | 0 | [[11-unknowns-and-risks#UNK-030 What identifies a reader\|UNK-030]] opened 2026-10-09 | grill RUN-tickertalk |
| [[coach-building-blocks\|Coach]] | contracts | 0 | 1 | 0 | 5 (5 by override) | [[11-unknowns-and-risks#UNK-028 Where a Coach service can run\|UNK-028]] opened 2026-10-09 | grill RUN-coach |
<!-- /generated:progress-map -->

## Why now

## Goals

| ID | Goal | Measure | State |
|---|---|---|---|
| G1 | The coach teaches people to trade one stock or option at a time, and trades for them when they're ready | Not recorded | inkling |
