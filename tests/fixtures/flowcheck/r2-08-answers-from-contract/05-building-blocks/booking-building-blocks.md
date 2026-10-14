---
id: APP-booking
type: app-building-blocks
title: Booking
---

# Booking

## Contracts this app provides

### CON-380 Hold a seat

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| held | | 200 | the seat is held | | booking: none→held |
| sold_out | | 409 | no seat in that fare class | | |
| unavailable | | 503 | the ferry did not answer | | |

### CON-381 Reserve on the ferry

- **Provider:** Ferrymaster
- **Consumers:** [[booking-building-blocks|Booking]]
- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| reserved | | 200 | the seat is reserved | | seat: free→reserved |
| full | | 409 | the sailing is full | | |
