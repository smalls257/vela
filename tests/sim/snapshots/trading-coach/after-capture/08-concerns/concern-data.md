---
id: concern-data
type: concern
title: Data
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Data

What each app stores, which app is the record, and what moves during the change.

## Strategy

Coach is the one record of each reader's paper balance and trades, and it keeps them encrypted; the Brightwater sandbox only fills the paper orders. A reader who withdraws has their record kept for 30 days so they can undo it, and then it is deleted, even if a real Brightwater account has opened since. TickerTalk sends Coach only the opaque reader ID, and only for readers who have opted in, so the watchlist and reading history stay in TickerTalk. Two questions are still open: [[11-unknowns-and-risks#UNK-059 Whether reader data may go to Brightwater and to a new party|whether reader data may go to Brightwater and to a new party]] and [[11-unknowns-and-risks#UNK-060 Lawful basis for the data Coach holds|the lawful basis for the data Coach holds]]. The mobile lead has confirmed that the plan sends only the ID.

[[sources#SRC-19|The later answers of 9 October]] say, for the mobile lead, that a reader's ID stays the same for the life of their account, across a change of email or a new device, and is never reused for another reader. They also say mobile's plan has TickerTalk check each reader's opt-in before it sends the ID to Coach and hide the coach screens for readers who have not opted in. [[sources#SRC-26|The mobile lead has since confirmed it by phone]], and says mobile ships it by 14 October. For the privacy lead, they say that when a reader withdraws, Coach keeps their record for 30 days so they can undo it and then deletes it. The product lead has since decided that the deletion on day 30 holds even after a real account opens. They name the privacy lead who approved the opt-in wording as @privacy-lead.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | addressed | Coach is the single record of each reader's paper balance and trades and keeps them encrypted. A reader who withdraws has their record kept 30 days to undo it, then deleted on day 30, even if they have opened a real Brightwater account; without a withdrawal the record stays in Coach after a real account opens ([[11-unknowns-and-risks#UNK-029 Where the paper record lives\|where the paper record lives]]) |
| [[tickertalk-building-blocks\|TickerTalk]] | addressed | TickerTalk sends Coach only the opaque reader ID, and only for readers who have opted in. A reader's ID stays the same for the life of their account and is never reused ([[sources#SRC-19\|the later answers]]). The reader's watchlist and reading history stay in TickerTalk and nothing else crosses to Coach. For readers who have not opted in, TickerTalk sends nothing and hides the coach screens. Mobile's confirmation that this is what its plan does is [[11-unknowns-and-risks#UNK-048 Does mobile's plan cover sending the ID only for opted-in readers\|the mobile plan question]], not this cell |

## History

#### Coach
- **Decision:** [[2026-10-09-concern-cells]]
- **Options considered:** The Brightwater sandbox as the single record. Rejected: it would lock Coach to Brightwater's timeline for the live handoff.
- **Override:** GATE-5 by @sim-lead on 2026-10-09: the owner is not present and the product lead decides on their behalf
- **Decided by:** @sim-lead, on behalf of @coach-lead
- **Confirmed by:** @coach-lead on 2026-10-09

#### TickerTalk
- **Decision:** [[2026-10-09-concern-cells]]
- **Options considered:** Sending Coach the reader's watchlist or history as well, so lessons could be tailored. Rejected: it is a new purpose that needs consent the initiative does not have, and it ties Coach to TickerTalk's data when the two need to be independent.
- **Override:** GATE-5 by @sim-lead on 2026-10-09: the owner is not present and the product lead decides on their behalf
- **Decided by:** @sim-lead, on behalf of @mobile-lead
