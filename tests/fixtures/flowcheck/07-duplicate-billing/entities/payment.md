---
id: ENT-008
type: entity
title: Payment
app: APP-billing
shared: false
initial: none
final: [charged]
---

# Payment

| From | To | Allowed by |
|---|---|---|
| none | charged | CON-050 charged |
| charged | charged_twice | CON-050 charged |

- **Invariant:** not payment=charged_twice
