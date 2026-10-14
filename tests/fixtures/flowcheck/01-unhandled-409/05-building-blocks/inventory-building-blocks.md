---
id: APP-inventory
type: app-building-blocks
title: Inventory
---

# Inventory

## Contracts this app provides

### CON-010 Place a hold

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| placed |  | 200 | placed |  | hold: held |
| unavailable |  | 409 | unavailable |  |  |

### CON-011 Capture the hold

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| captured |  | 200 | captured |  | hold: captured |

### CON-012 Release the hold

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| released |  | 200 | released |  | hold: released |
