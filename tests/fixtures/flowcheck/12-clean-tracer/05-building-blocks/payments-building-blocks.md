---
id: APP-payments
type: app-building-blocks
title: Payments
---

# Payments

## Contracts this app provides

### CON-022 Take the payment

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| paid |  | 200 | paid |  |  |
| refused |  | 402 | refused |  |  |
| unavailable |  | 503 | unavailable |  |  |

### CON-070 Charge the card

- **Provider:** Cardco
- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| charged |  | 200 | charged |  |  |
| declined |  | 402 | declined |  |  |

### EVT-020 payment taken

- **Delivery:** exactly-once
- **Order:** any

| Subscriber | Retries |
|---|---|
| Inventory | none |
