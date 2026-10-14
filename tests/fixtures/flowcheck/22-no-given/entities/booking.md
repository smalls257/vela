---
id: ENT-023
type: entity
title: Booking
app: APP-booking
shared: false
initial: new
final: [confirmed, amended]
---

# Booking

| From | To | Allowed by |
|---|---|---|
| new | confirmed | CON-130 confirmed |
| confirmed | amended | CON-120 amended |
