---
id: FLO-010
type: flow
title: A customer is told
state: assumption
---

# A customer is told

```mermaid
sequenceDiagram
participant S as Shop
participant M as Mailer
loop every morning
S-)M: EVT-010 order confirmed
par Mailer handles order confirmed
    Note over M: END handled
end
Note over S: END told
```
