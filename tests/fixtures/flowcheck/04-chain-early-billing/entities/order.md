---
id: ENT-004
type: entity
title: Order
owner: order-service
shared: false
initial: new
final: [completed, rejected]
---

# Order

| From | To | Allowed by |
|---|---|---|
| new | pending | CON-030 created |
| pending | completed | CON-041 completed |
| new | rejected | CON-030 rejected |
| pending | rejected | CON-030 rejected |
