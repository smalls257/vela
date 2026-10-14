---
id: APP-inventory
type: app-building-blocks
title: Inventory
---

# Inventory

## Contracts this app provides

### CON-010 Place a hold

- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| placed |  | 200 | placed |  |  |
| unavailable |  | 409 | unavailable |  |  |
| blocked |  | 423 | blocked |  |  |
