---
id: context-and-scope
type: initiative-section
title: Context and scope
arc42: "§3"
state: inkling
owner: "@solution-lead"
authored: mixed
sources: [SRC-03, SRC-04, SRC-07]
---

# Context and scope

TickerTalk is the foundation: an app, its readers and a mobile team. The product lead says about 400,000 people read it each month, and does not know whether the coach is for all of them or only those interested in trading. The coach is meant to take on one stock or option at a time. [[03-context-and-scope#PTY-01 Brightwater|Brightwater]], a broker-dealer TickerTalk signed with in June, holds the customers' money and executes equity orders through its API, and its agreement covers equities and not options. TickerTalk holds none of that money, and who carries the balances as owed to customers is not recorded. [[03-context-and-scope#PTY-02 Quoteline|Quoteline]] supplies the prices, under a license that lets TickerTalk's own apps display US equity quotes delayed by 15 minutes, with no options data. A budget has been allocated, but its size, holder and scope are not recorded, and the dates and the no-live-trading ban are on the constraints page.

## Today

The product lead says TickerTalk is the foundation: the app, the readers and a mobile team. They also say "users are TickerTalk readers, about 400k monthly", and that the budget is allocated. All three are the product lead's account and none has a source. The agreement and license summaries call TickerTalk "Kestrel", and [[sources#SRC-07|the product lead confirms]] they are the same company.

## After

<!-- generated:system-context sha=140bedbf: do not edit, run planner render -->
none
<!-- /generated:system-context -->

## In scope

## Out of scope

## Outside parties

### PTY-01 Brightwater

Brightwater is the broker-dealer TickerTalk signed with in June. [[sources#SRC-03|The partnerships manager's agreement summary]] says it opens accounts, runs KYC, holds customers' money and executes equity orders through its API, and that TickerTalk gets back an account ID and an order status and never holds customer money. The same summary says the agreement covers equities and not options, and that sandbox paper accounts are available for testing.

- **Relationship:** partner
- **Agreements:** the signed broker agreement, June (year not recorded), held by the partnerships manager; only [[sources#SRC-03|its summary]] is in sources, see [[11-unknowns-and-risks#UNK-009 Signed broker agreement terms|the open question on its terms]]

### PTY-02 Quoteline

Quoteline supplies the market data under a license. [[sources#SRC-04|The data engineer's license summary]] says it lets TickerTalk's own apps display US equity quotes delayed by 15 minutes, and that it includes no options data.

- **Relationship:** supplier
- **Agreements:** the Quoteline market data license, summarized by the data engineer in March 2026 ([[sources#SRC-04|the summary]]); the license itself is not in sources

## Value held for customers

### SV-01 Customer money at Brightwater

Brightwater holds the money customers put in, and TickerTalk holds none, on [[sources#SRC-01|the product lead's own account]].

- **Holder:** [[03-context-and-scope#PTY-01 Brightwater|Brightwater]]
- **Owner:** not known yet, see [[11-unknowns-and-risks#UNK-011 Who owes Brightwater balances|the question of who carries the balances]]
