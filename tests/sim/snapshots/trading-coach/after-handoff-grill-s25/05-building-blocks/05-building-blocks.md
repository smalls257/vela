---
id: building-blocks
type: index
title: Building blocks
arc42: "§5"
authored: mixed
---

# Building blocks

One page per app: what it does, its main parts, and the contracts (agreed interfaces) it offers other apps. Each contract sits on the page of the app that provides it.

<!-- generated:context-map sha=84c35dd0: do not edit, run vela render -->
```mermaid
flowchart LR
  n_APP_coach["Coach (new)"]
  n_APP_tickertalk["TickerTalk (changed)"]
  x_quoteline__pty_02_["Quoteline (PTY-02)"]
  n_APP_coach -->|"CON-001"| n_APP_tickertalk
  x_quoteline__pty_02_ -->|"CON-002"| n_APP_coach
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_tickertalk changed
  class x_quoteline__pty_02_ external
  class n_APP_coach new
```

Key: green: new in this initiative · amber: changed by this initiative · white, dashed: outside the initiative (a party or provider) · an arrow is a contract, labeled with its ID.
<!-- /generated:context-map -->

## Coach app behind TickerTalk

- **Apps:** [[coach-building-blocks|Coach]] (new), [[tickertalk-building-blocks|TickerTalk]] (changed). Brightwater and Quoteline stay outside; Signal is not touched in release one.
- **Options considered:** Coach app behind TickerTalk (picked); Coach built into TickerTalk: rejected, "B drowns mobile, they're already maxed" (the product lead); Coach, a separate board-demo app and Signal as idea source: rejected, "C's too many apps before we know what Brightwater allows" (the product lead)
