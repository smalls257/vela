---
id: APP-helpdesk
type: app-building-blocks
title: Helpdesk
---

# Helpdesk

## Contracts this app provides

### CON-350 Close the ticket

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| closed | | 200 | the ticket is closed | | ticket: open→closed |
