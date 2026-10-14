---
id: FLO-403
type: flow
title: A customer orders, and the shop looks it up after a timeout
state: assumption
---

# A customer orders, and the shop looks it up after a timeout

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
    Note over S: SET order placed
    Note over S: END ordered
else refused
    Note over S: SET order canceled
    Note over S: END canceled
else timeout
    S->>T: CON-403 look up the order
    alt found
        Note over S: SET order placed
        Note over S: END ordered
    else not_found
        Note over S: SET order canceled
        Note over S: END canceled
    end
end
```
