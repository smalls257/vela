---
id: building-blocks
type: index
title: Building blocks
arc42: "§5"
authored: mixed
---

# Building blocks

One page per app in scope, named `<app>-building-blocks.md`. Contracts live on the provider's page.

<!-- generated:context-map sha=6c6bc5cc: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_coach["Coach (new)"]
  n_APP_tickertalk["TickerTalk (changed)"]
  x_quoteline____03_context_and_scope_pty_02_quoteline_pty_02___["Quoteline ( 03-context-and-scope PTY-02 Quoteline PTY-02 )"]
  n_APP_coach -->|"CON-001"| n_APP_tickertalk
  x_quoteline____03_context_and_scope_pty_02_quoteline_pty_02___ -->|"CON-002"| n_APP_coach
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_tickertalk changed
  class x_quoteline____03_context_and_scope_pty_02_quoteline_pty_02___ external
  class n_APP_coach new
```
<!-- /generated:context-map -->

## Coach app behind TickerTalk

- **Apps:** [[coach-building-blocks|Coach]] (new), [[tickertalk-building-blocks|TickerTalk]] (changed). Brightwater and Quoteline stay outside; Signal is not touched in release one.
- **Options considered:** Coach app behind TickerTalk (picked); Coach built into TickerTalk: rejected, "B drowns mobile, they're already maxed" (the product lead); Coach, a separate board-demo app and Signal as idea source: rejected, "C's too many apps before we know what Brightwater allows" (the product lead)
