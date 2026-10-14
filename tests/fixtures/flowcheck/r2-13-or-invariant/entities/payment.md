---
id: ENT-314
type: entity
title: Payment
app: APP-shop
shared: false
initial: none
final: [none, taken, refunded]
---

# Payment

| From | To | Allowed by |
|---|---|---|
| none | taken | FLO-313 |
| taken | refunded | FLO-313 |

