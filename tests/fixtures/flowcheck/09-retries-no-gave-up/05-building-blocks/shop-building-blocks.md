---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-060 Take the payment

- **Provider:** Tidepay

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| paid | 200 |  |  |  | yes | max 3 on timeout |
| declined | 402 |  |  |  | yes | max 3 on timeout |
