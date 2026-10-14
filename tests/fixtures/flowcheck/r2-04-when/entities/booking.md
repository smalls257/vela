---
id: ENT-304
type: entity
title: Booking
app: APP-booking
shared: false
initial: new
final: [confirmed, expired]
---

# Booking

| From | To | Allowed by |
|---|---|---|
| new | held | FLO-304 |
| held | confirmed | CON-340 confirmed |
| paid | confirmed | CON-340 confirmed |
| held | expired | FLO-304 |

