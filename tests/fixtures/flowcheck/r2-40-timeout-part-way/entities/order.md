---
id: ENT-402
type: entity
title: Order
app: APP-shop
shared: false
initial: none
final: [placed, canceled]
---

# Order

| From | To | Allowed by |
|---|---|---|
| none | placed | CON-401 taken |
| none | canceled | CON-401 |

- **Invariant:** not (order=canceled and hold=captured)
