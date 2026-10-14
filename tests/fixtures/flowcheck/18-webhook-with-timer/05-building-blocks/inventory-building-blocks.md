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
| placed | 200 |  | hold=held |  | no | none |
| unavailable | 409 |  |  |  | no | none |

### CON-011 Capture the hold


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| captured | 200 |  | hold=captured | hold=held | no | none |
| too_late | 409 |  |  | hold=expired | no | none |
