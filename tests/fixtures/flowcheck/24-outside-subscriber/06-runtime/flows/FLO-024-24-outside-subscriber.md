---
id: FLO-024
type: flow
title: A customer pays
state: assumption
---

# A customer pays

```mermaid
sequenceDiagram
participant S as Shop
participant T as Tidepay
S->>T: CON-020 take the payment
alt paid
    Note over S: END paid
else declined
    Note over S: END declined
end
```
