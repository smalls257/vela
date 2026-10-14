---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-090 Report the payment

- **Delivery:** may-be-lost
- **Order:** any
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| received |  | 200 | received |  |  |

### CON-091 Refund the payment

- **Provider:** Tidepay
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| refunded |  | 200 | refunded |  |  |
