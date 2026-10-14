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
| captured | 200 |  | hold=captured |  | no | none |

### CON-012 Release the hold


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| released | 200 |  | hold=released |  | no | none |
