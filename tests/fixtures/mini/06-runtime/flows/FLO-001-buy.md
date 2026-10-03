---
id: FLO-001
type: flow
title: Buy
initiative: INI-900
state: assumption
owner: "@mini-lead"
authored: authored
---

# FLO-001 Buy

```mermaid
sequenceDiagram
  participant T as Till
  participant S as Shop
  participant K as Stock
  T->>S: sell (CON-001)
  S->>K: stock level (CON-002)
  S-->>T: receipt
```
