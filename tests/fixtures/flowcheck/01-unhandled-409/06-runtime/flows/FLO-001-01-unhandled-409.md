---
id: FLO-001
type: flow
title: A customer holds an item
state: assumption
---

# A customer holds an item

```mermaid
sequenceDiagram
participant S as Shop
participant I as Inventory
S->>I: CON-010 place a hold
alt placed
    I-->>S: 200 placed
    Note over S: END held leaves hold=held
end
```
