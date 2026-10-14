---
id: APP-inventory
type: app-building-blocks
title: Inventory
---

# Inventory

## Contracts this app provides

### CON-010 Place a hold


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| placed | 200 |  |  |  | yes | none |
| unavailable | 409 |  |  |  | yes | none |
| blocked | 423 |  |  |  | yes | none |
