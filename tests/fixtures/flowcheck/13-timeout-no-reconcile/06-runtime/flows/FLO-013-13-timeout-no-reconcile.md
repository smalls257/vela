---
id: FLO-013
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
    Note over S: SET charge settled
    Note over S: END paid
else declined
    Note over S: END declined
else timeout
    Note over S: END payment_failed
end
```
