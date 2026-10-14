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
| captured | hold is held | 200 | captured |  | hold: captured |
| too_late | hold is expired | 409 | too late |  |  |

### CON-012 Expire the hold

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| expired | hold is held | 200 | the hold is let go | | hold: held→expired |
| already_settled | hold is not held | 409 | the hold was captured or let go already | | |
