---
id: APP-booking
type: app-building-blocks
title: Booking
---

# Booking

## Contracts this app provides

### CON-110 Confirm the booking

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| confirmed |  | 200 | confirmed |  | booking: held→confirmed |

### CON-111 Cancel the booking

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| cancelled |  | 200 | cancelled |  | booking: held→cancelled |
