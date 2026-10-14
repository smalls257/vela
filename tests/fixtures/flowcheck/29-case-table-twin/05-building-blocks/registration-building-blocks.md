---
id: APP-registration
type: app-building-blocks
title: Registration
---

# Registration

## Contracts this app provides

### CON-030 Register the customer


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| created | 201 | EVT-003 |  |  | no | none |
| rejected | 422 |  |  |  | no | none |

### EVT-003 registration created

- **Delivery:** exactly-once
- **Order:** any

| Subscriber | Retries |
|---|---|
| Billing | max 2 on refused |
