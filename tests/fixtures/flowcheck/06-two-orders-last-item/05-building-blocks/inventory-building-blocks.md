---
id: APP-inventory
type: app-building-blocks
title: Inventory
---

# Inventory

## Contracts this app provides

### CON-020 Check the stock

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| in_stock | stock is one | 200 | in stock |  |  |
| out_of_stock | stock in [zero, minus_one] | 409 | out of stock |  |  |

### CON-021 Reserve the item

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| reserved |  | 200 | reserved |  | stock: one→zero, zero→minus_one |
