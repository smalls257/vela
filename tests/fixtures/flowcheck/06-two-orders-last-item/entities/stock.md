---
id: ENT-006
type: entity
title: Stock
app: APP-inventory
shared: true
initial: one
final: [one, zero]
---

# Stock

| From | To | Allowed by |
|---|---|---|
| one | zero | CON-021 reserved |
| zero | minus_one | CON-021 reserved |

- **Invariant:** not stock=minus_one
