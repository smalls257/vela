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

Each reader's paper balance and trades have to live in one system, either Coach or Brightwater's sandbox, and the vault does not yet say which. Coach's page keeps them on the sandbox accounts, so [[11-unknowns-and-risks#UNK-029 Where the paper record lives|where the paper record lives]] decides what Coach stores. TickerTalk's own data is not recorded either: [[11-unknowns-and-risks#UNK-030 What identifies a reader|what identifies a reader]] and whether it may go to Coach are waiting on the product lead's check with the mobile lead.

[[sources#SRC-19|The later answers of 9 October]] say, for the mobile lead, that a reader's ID stays the same for the life of their account, across a change of email or a new device, and is never reused for another reader. They also say mobile's plan has TickerTalk check each reader's opt-in before it sends the ID to Coach and hide the coach screens for readers who have not opted in. That is a plan, so it is an assumption, and it does not say that Coach receives nothing but the ID. For the privacy lead, they say that when a reader withdraws, Coach keeps their record for 30 days so they can undo it and then deletes it, which is also a plan and so an assumption. They name the privacy lead who approved the opt-in wording as @privacy-lead.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | unknown | [[11-unknowns-and-risks#UNK-029 Where the paper record lives\|Where the paper record lives]]: which system is the record of a reader's paper balance and trades |
| [[tickertalk-building-blocks\|TickerTalk]] | unknown | [[11-unknowns-and-risks#UNK-029 Where the paper record lives\|Where the paper record lives]]: which system is the record of a reader's paper balance and trades |
