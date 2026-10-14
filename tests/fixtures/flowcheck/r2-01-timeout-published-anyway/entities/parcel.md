---
id: ENT-302
type: entity
title: Parcel
app: APP-warehouse
shared: false
initial: waiting
final: [waiting, shipped]
---

# Parcel

| From | To | Allowed by |
|---|---|---|
| waiting | shipped | EVT-301 handled |

