---
id: FLO-019
type: flow
title: A customer is told
state: assumption
---

# A customer is told

```mermaid
sequenceDiagram
participant S as Shop
participant M as Mailer
S-)M: EVT-019 order placed
alt handled
    Note over S: END told
end
```
