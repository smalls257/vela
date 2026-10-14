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

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| received | 200 |  |  |  | no | none |

### CON-091 Refund the payment

- **Provider:** Tidepay

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| refunded | 200 |  |  |  | no | none |
