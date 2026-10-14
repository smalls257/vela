---
id: APP-inventory
type: app-building-blocks
title: Inventory
---

# Inventory

## Contracts this app provides

### CON-501 Place a hold

Shop asks Inventory to hold the item while the customer pays.

- **Consumers:** [[shop-building-blocks|Shop]]
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| placed |  | 200 | held |  | hold: held |
| unavailable |  | 409 | none left |  |  |

### CON-502 Release the hold

- **Consumers:** [[shop-building-blocks|Shop]]
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| released |  | 200 | released |  | hold: held→released |

### CON-504 Check the stock

- **Consumers:** [[shop-building-blocks|Shop]]
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| in_stock |  | 200 | in stock |  |  |
| out_of_stock |  | 409 | out of stock |  |  |
