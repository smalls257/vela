---
id: ENT-020
type: entity
title: Seat
app: APP-booking
shared: false
initial: free
final: [free, reserved]
---

# Seat

| From | To | Allowed by |
|---|---|---|
| free | reserved | CON-101 reserved |

- **Invariant:** booking=held implies seat=reserved
