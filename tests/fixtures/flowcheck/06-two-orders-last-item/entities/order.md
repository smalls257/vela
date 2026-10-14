---
id: ENT-007
type: entity
title: Order
app: APP-shop
shared: false
initial: new
final: [reserved, sold_out]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | reserved | CON-021 reserved |
| new | sold_out | CON-020 out_of_stock |
