---
id: ENT-001
type: entity
title: Hold
app: APP-inventory
shared: false
initial: none
final: [released, captured]
---

# Hold

| From | To | Allowed by |
|---|---|---|
| none | held | CON-010 placed |
| held | released | CON-012 released |
| held | captured | CON-011 captured |
| held | captured | EVT-020 handled |
