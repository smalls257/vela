---
id: APP-payments
type: app-building-blocks
title: Payments
---

# Payments

## Contracts this app provides

### CON-300 Take the payment

- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| paid | | 200 | the payment is taken | EVT-301 | |
| declined | | 402 | refused by the card issuer | | |

### EVT-301 payment taken

- **Delivery:** exactly-once
- **Order:** any

| Subscriber | Retries |
|---|---|
| Warehouse | none |
