---
id: ENT-027
type: entity
title: Parcel
app: APP-packing
shared: false
initial: new
final: [labeled]
---

# Parcel

| From | To | Allowed by |
|---|---|---|
| new | picked | EVT-027 handled |
| picked | packed | EVT-027 handled |
| packed | labeled | EVT-027 handled |
