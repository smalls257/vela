---
id: ENT-009
type: entity
title: Order
app: APP-shop
shared: false
initial: new
final: [invoiced, expired]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | waiting | FLO-008 |
| waiting | invoiced | EVT-009 received |
| waiting | expired | timer |
