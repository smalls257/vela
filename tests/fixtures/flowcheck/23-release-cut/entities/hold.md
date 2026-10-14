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
| held | paid | CON-011 captured |
| paid | captured | CON-011 captured |
| held | released | CON-012 released |
