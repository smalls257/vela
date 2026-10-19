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

Nobody has examined security for either app yet. Who may call Coach, and how a reader's identity is protected on its way from TickerTalk, is not recorded.

The platform engineer's security review, relayed in [[sources#SRC-16|the answers the product lead gathered by 9 October]], found no payment data and no real orders in Coach, says reader IDs are opaque, and says Coach stores practice records encrypted at rest.

## Per app

| App | State | Why |
|---|---|---|

Not looked at yet: [[coach-building-blocks\|Coach]], [[tickertalk-building-blocks\|TickerTalk]].
