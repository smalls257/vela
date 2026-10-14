---
id: ENT-313
type: entity
title: Order
app: APP-shop
shared: false
initial: new
final: [shipped]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | shipped | CON-330 shipped |

- **Invariant:** not (order=shipped and (payment=none or payment=refunded))
