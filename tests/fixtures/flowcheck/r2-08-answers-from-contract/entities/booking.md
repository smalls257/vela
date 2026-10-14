---
id: ENT-308
type: entity
title: Booking
app: APP-booking
shared: false
initial: none
final: [none, held]
---

# Booking

| From | To | Allowed by |
|---|---|---|
| none | held | CON-380 held |

- **Invariant:** booking=held implies seat=reserved
