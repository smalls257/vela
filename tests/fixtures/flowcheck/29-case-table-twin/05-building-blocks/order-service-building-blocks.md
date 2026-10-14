---
id: APP-order-service
type: app-building-blocks
title: Order service
---

# Order service

## Contracts this app provides

### CON-041 Complete the order


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| completed | 200 |  | order=completed | order=pending | no | none |
| not_found | 409 |  |  | order=new | no | none |
