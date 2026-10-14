---
id: FLO-232
type: flow
title: A paid hold is captured
state: assumption
---

# A paid hold is captured

```mermaid
sequenceDiagram
participant S as Shop
participant I as Inventory
Note over S: GIVEN hold paid
S->>I: CON-011 capture the hold
Note over S: END captured
```
