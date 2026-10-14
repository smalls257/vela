---
id: ENT-022
type: entity
title: Booking
owner: booking
shared: true
initial: held
final: [confirmed, cancelled]
---

# Booking

| From | To | Allowed by |
|---|---|---|
| held | confirmed | CON-110 confirmed |
| held | cancelled | CON-111 cancelled |
