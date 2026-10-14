---
id: APP-payments
type: app-building-blocks
title: Payments
---

# Payments

## Contracts this app provides

### CON-022 Take the payment


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| paid | 200 |  |  |  | no | none |
| refused | 402 |  |  |  | no | none |
| unavailable | 503 |  |  |  | no | none |

### CON-070 Charge the card

- **Provider:** Cardco

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| charged | 200 |  |  |  | yes | none |
| declined | 402 |  |  |  | yes | none |

### EVT-020 payment taken

- **Delivery:** exactly-once
- **Order:** any

| Subscriber | Retries |
|---|---|
| Inventory | none |
