---
id: APP-billing
type: app-building-blocks
title: Billing
---

# Billing

## Contracts this app provides

### CON-503 Take the payment

- **Consumers:** [[shop-building-blocks|Shop]]
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| paid |  | 200 | paid |  |  |
| declined |  | 402 | declined |  |  |
