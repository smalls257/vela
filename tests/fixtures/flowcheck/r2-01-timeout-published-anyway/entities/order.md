---
id: ENT-301
type: entity
title: Order
app: APP-shop
shared: false
initial: new
final: [paid, canceled]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | paid | CON-300 paid |
| new | canceled | CON-300 |

- **Invariant:** not (order=canceled and parcel=shipped)
