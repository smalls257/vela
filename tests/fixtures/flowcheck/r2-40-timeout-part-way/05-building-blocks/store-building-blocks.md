---
id: APP-store
type: app-building-blocks
title: Store
---

# Store

## Contracts this app provides

### CON-401 Take the order

- **Consumers:** [[shop-building-blocks|Shop]]
- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| taken |  | 200 | the order is taken |  |  |
| refused |  | 402 | the card was declined |  |  |

## Contracts this app consumes

### CON-402 Charge the card

- **Provider:** Payco
- **Consumers:** [[store-building-blocks|Store]]
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| charged |  | 200 | charged |  |  |
| declined |  | 402 | declined |  |  |
