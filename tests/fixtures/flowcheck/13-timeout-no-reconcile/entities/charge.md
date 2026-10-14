---
id: ENT-013
type: entity
title: Charge
app: APP-shop
shared: false
initial: none
final: [settled]
---

# Charge

| From | To | Allowed by |
|---|---|---|
| none | taken | CON-020 paid |
| taken | settled | CON-020 paid |
| taken | settled | CON-023 found |
