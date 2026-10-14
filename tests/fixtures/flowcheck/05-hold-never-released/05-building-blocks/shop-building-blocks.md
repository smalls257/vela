---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-020 Take the payment

- **Provider:** Tidepay
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| paid |  | 200 | paid |  |  |
| declined |  | 402 | declined |  |  |
