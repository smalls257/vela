---
id: ENT-501
type: entity
title: Hold
app: APP-inventory
shared: false
initial: none
final: [none, released, captured]
---

# Hold

| From | To | Allowed by |
|---|---|---|
| none | held | CON-501 placed |
| held | released | CON-502 released |
| held | captured | CON-503 paid |
