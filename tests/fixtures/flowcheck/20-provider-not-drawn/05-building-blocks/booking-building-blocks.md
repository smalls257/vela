---
id: APP-booking
type: app-building-blocks
title: Booking
---

# Booking

## Contracts this app provides

### CON-100 Hold a seat

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| held |  | 200 | held |  |  |
| sold_out |  | 409 | sold out |  |  |
| unavailable |  | 503 | unavailable |  |  |

### CON-101 Reserve on the ferry

- **Provider:** Ferrymaster
- **Consumers:** [[booking-building-blocks|Booking]]
- **Can time out:** yes
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| reserved |  | 200 | reserved |  | seat: reserved |
| full |  | 409 | full |  |  |
