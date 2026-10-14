---
id: ENT-022
type: entity
title: Booking
app: APP-booking
shared: true
initial: held
final: [confirmed, canceled]
---

# Booking

| From | To | Allowed by |
|---|---|---|
| held | confirmed | CON-110 confirmed |
| held | canceled | CON-111 canceled |
