---
id: FLO-305
type: flow
title: Close a ticket twice
state: assumption
---

# Close a ticket twice

```mermaid
sequenceDiagram
participant D as Agent desk
participant H as Helpdesk
D->>H: CON-350 close the ticket
D->>H: CON-350 close the ticket
Note over D: END closed
```
