---
id: ENT-401
type: entity
title: Hold
app: APP-store
shared: false
initial: none
final: [none, captured, released]
---

# Hold

| From | To | Allowed by |
|---|---|---|
| none | held | CON-401 |
| held | captured | CON-402 charged |
| held | released | CON-402 declined |
