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
| none | placed | CON-403 found |
| none | canceled | CON-401 refused |
| none | canceled | CON-403 not_found |

- **Invariant:** not (order=canceled and hold=captured)
