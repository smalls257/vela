---
id: concern-security
type: concern
title: Security
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Security

Who can call what, and what data each boundary carries.

## Strategy

Nobody has examined security for Coach yet, and [[sources#SRC-19|the mobile lead says]] TickerTalk's existing practice holds. Who may call Coach, and how a reader's identity is protected on its way from TickerTalk, is not recorded.

The platform engineer's security review, relayed in [[sources#SRC-16|the answers the product lead gathered by 9 October]], found no payment data and no real orders in Coach, says reader IDs are opaque, and says Coach stores practice records encrypted at rest.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | unchanged | the product lead says the existing security practice holds ([[2026-10-09-concern-cells#^c07]])
| [[tickertalk-building-blocks\|TickerTalk]] | unchanged | the mobile lead says TickerTalk's existing security practice holds ([[sources#SRC-19|the later answers]]) |
