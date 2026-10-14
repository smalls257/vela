---
id: ENT-301
type: entity
title: Order
app: APP-shop
shared: false
initial: new
final: [paid, cancelled]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | paid | CON-300 paid |
| new | cancelled | CON-300 |

- **Invariant:** not (order=cancelled and parcel=shipped)
