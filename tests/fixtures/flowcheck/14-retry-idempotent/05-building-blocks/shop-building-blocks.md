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
- **Can time out:** yes
- **Retries:** 1 after timeout

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| paid |  | 200 | paid |  | charge: none→taken, taken→taken_twice |
| declined |  | 402 | declined |  |  |
