---
id: ENT-015
type: entity
title: Ticket
app: APP-ticket-service
shared: false
initial: open
final: [closed]
---

# Ticket

| From | To | Allowed by |
|---|---|---|
| open | closed | CON-081 toggled |
| closed | open | CON-081 toggled |
