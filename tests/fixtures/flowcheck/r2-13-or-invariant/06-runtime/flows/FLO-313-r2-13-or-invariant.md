---
id: FLO-313
type: flow
title: Ship an order
state: assumption
---

# Ship an order

```mermaid
sequenceDiagram
participant S as Shop
participant W as Warehouse
S->>W: CON-330 ship the order
Note over S: END shipped
```
