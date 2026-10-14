---
id: ENT-014
type: entity
title: Charge
owner: shop
shared: false
initial: none
final: [taken]
---

# Charge

| From | To | Allowed by |
|---|---|---|
| none | taken | CON-020 paid |
| taken | taken_twice | CON-020 paid |

- **Invariant:** not charge=taken_twice
