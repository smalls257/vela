---
id: APP-ticket-service
type: app-building-blocks
title: Ticket service
---

# Ticket service

## Contracts this app provides

### CON-081 Toggle the ticket

- **Provider:** Helpdesk

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| toggled | 200 |  | ticket=open->closed closed->open |  | no | none |
