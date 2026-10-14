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
| paid | 200 |  | charge=taken |  | yes | none |
| declined | 402 |  |  |  | yes | none |

### CON-023 Look up the payment

- **Provider:** Tidepay

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| found | 200 |  |  | charge=taken | no | none |
| not_found | 404 |  |  | charge=none | no | none |
