---
id: APP-registration
type: app-building-blocks
title: Registration
---

# Registration

## Contracts this app provides

### CON-030 Register the customer

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| created |  | 201 | created | EVT-003 |  |
| rejected |  | 422 | rejected |  |  |

### EVT-003 registration created

- **Delivery:** exactly-once
- **Order:** any

| Subscriber | Retries |
|---|---|
| Billing | 1 after refused |
