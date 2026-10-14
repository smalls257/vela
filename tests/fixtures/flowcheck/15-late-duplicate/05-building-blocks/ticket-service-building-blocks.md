---
id: APP-ticket-service
type: app-building-blocks
title: Ticket service
---

# Ticket service

## Contracts this app provides

### CON-081 Toggle the ticket

- **Provider:** Helpdesk
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| toggled |  | 200 | toggled |  | ticket: open→closed, closed→open |
