---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-020 Take the payment

- **Provider:** Tidepay
- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| paid |  | 200 | paid |  | charge: taken |
| declined |  | 402 | declined |  |  |

### CON-023 Look up the payment

- **Provider:** Tidepay
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| found | charge is taken | 200 | found |  |  |
| not_found | charge is none | 404 | not found |  |  |
