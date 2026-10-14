---
id: APP-inventory
type: app-building-blocks
title: Inventory
---

# Inventory

## Contracts this app provides

### CON-020 Check the stock


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| in_stock | 200 |  |  | stock=one | no | none |
| out_of_stock | 409 |  |  | stock=zero or minus_one | no | none |

### CON-021 Reserve the item


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| reserved | 200 |  | stock=one->zero zero->minus_one |  | no | none |
