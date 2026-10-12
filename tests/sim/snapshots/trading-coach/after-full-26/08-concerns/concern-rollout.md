---
id: concern-rollout
type: concern
title: Rollout
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Rollout

The order apps cut over, and how each one rolls back.

## Strategy

Coach holds a release switch, and TickerTalk hides the coach when it is off, so the coach can ship dark. The switch waits on the [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|compliance ruling in writing]]. How a release rolls back, and in what order readers get the coach, is not recorded.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | unknown | [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing\|Compliance ruling in writing]]: the compliance ruling the release switch waits on |
| [[tickertalk-building-blocks\|TickerTalk]] | unknown | [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing\|Compliance ruling in writing]]: the compliance ruling the release switch waits on |
