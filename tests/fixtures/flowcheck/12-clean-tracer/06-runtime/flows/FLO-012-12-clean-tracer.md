---
id: FLO-012
type: flow
title: A customer buys an item
state: assumption
---

# A customer buys an item

```mermaid
sequenceDiagram
participant S as Shop
participant I as Inventory
participant P as Payments
participant C as Cardco
S->>I: CON-010 place a hold
alt placed
    I-->>S: 200 placed
    S->>P: CON-022 take the payment
    P->>C: CON-070 charge the card
    alt charged
        C-->>P: 200 charged
        P-)I: EVT-020 payment taken
        par Inventory handles payment taken
            Note over I: SET hold captured
            Note over I: END handled
        end
        P-->>S: 200 paid
    else declined
        C-->>P: 402 declined
        P-->>S: 402 refused
    else timeout
        P-->>S: 503 unavailable
    end
    alt paid
        Note over S: END paid
    else refused, unavailable
        S->>I: CON-012 release the hold
        Note over S: END not_paid
    end
else unavailable
    I-->>S: 409 unavailable
    Note over S: END unavailable
end
```
