---
id: APP-booking
type: app-building-blocks
title: Booking
---

# Booking

## Contracts this app provides

### CON-100 Hold a seat


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| held | 200 |  |  |  | no | none |
| sold_out | 409 |  |  |  | no | none |
| unavailable | 503 |  |  |  | no | none |

### CON-101 Reserve on the ferry

- **Provider:** Ferrymaster

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| reserved | 200 |  | seat=reserved |  | yes | none |
| full | 409 |  |  |  | yes | none |
