---
id: APP-booking
type: app-building-blocks
title: Booking
---

# Booking

## Contracts this app provides

### CON-110 Confirm the booking


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| confirmed | 200 |  | booking=held->confirmed |  | no | none |

### CON-111 Cancel the booking


| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| cancelled | 200 |  | booking=held->cancelled |  | no | none |
