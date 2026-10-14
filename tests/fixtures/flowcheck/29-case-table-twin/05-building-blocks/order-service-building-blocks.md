---
id: APP-order-service
type: app-building-blocks
title: Order service
---

# Order service

## Contracts this app provides

### CON-041 Complete the order

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| completed | order is pending | 200 | completed |  | order: completed |
| not_found | order is new | 409 | not found |  |  |
