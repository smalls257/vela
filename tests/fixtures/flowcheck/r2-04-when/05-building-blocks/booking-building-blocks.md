---
id: APP-booking
type: app-building-blocks
title: Booking
---

# Booking

## Contracts this app provides

### CON-340 Confirm the booking

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| confirmed | booking in [held, paid] | 200 | the booking is confirmed | | booking: confirmed |
| already_gone | booking is not held and booking is not paid | 409 | the booking has expired or was canceled | | |
