---
id: ENT-009
type: entity
title: Order
owner: shop
shared: false
initial: new
final: [invoiced, expired]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | waiting | FLO-027 |
| waiting | invoiced | EVT-009 received |
| waiting | expired | timer |
