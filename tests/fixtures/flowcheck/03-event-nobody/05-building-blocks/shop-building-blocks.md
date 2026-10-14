---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-020 Take the payment

- **Provider:** Tidepay

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| paid | 200 | EVT-020 |  |  | no | none |
| declined | 402 |  |  |  | no | none |

### EVT-020 payment taken

- **Delivery:** exactly-once
- **Order:** any
