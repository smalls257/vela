---
id: ENT-310
type: entity
title: Hold
app: APP-shop
shared: false
initial: none
final: [captured, released]
---

# Hold

| From | To | Allowed by |
|---|---|---|
| none | held | FLO-310 |
| held | captured | EVT-311 received |
| held | released | timer pay_window |

