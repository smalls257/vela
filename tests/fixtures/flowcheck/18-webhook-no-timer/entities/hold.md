---
id: ENT-018
type: entity
title: Hold
app: APP-inventory
shared: false
initial: none
final: [captured, expired]
---

# Hold

| From | To | Allowed by |
|---|---|---|
| none | held | CON-010 placed |
| held | captured | CON-011 captured |
| held | expired | timer |
