---
id: FLO-402
type: flow
title: A customer orders, the hold made in one step
state: assumption
---

# A customer orders, the hold made in one step

```mermaid
sequenceDiagram
participant S as Shop
participant T as Store
participant P as Payco
S->>T: CON-401 take the order
T->>P: CON-402 charge the card
alt charged
    P-->>T: 200 charged
    Note over T: SET hold captured
    T-->>S: 200 taken
else declined
    P-->>T: 402 declined
    T-->>S: 402 refused
end
alt taken
    Note over S: END ordered
else refused, timeout
    Note over S: END not_ordered
end
```
