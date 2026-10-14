---
id: APP-billing
type: app-building-blocks
title: Billing
---

# Billing

## Contracts this app provides

### CON-050 Charge the card

- **Provider:** Cardco
- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| charged |  | 200 | charged |  | payment: none→charged, charged→charged_twice |
