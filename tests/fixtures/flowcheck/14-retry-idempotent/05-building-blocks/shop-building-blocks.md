---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-020 Take the payment

- **Provider:** Tidepay
- **Idempotent:** yes

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| paid | 200 |  | charge=none->taken taken->taken_twice |  | yes | max 2 on timeout |
| declined | 402 |  |  |  | yes | max 2 on timeout |
