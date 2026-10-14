---
id: APP-billing
type: app-building-blocks
title: Billing
---

# Billing

## Contracts this app provides

### CON-050 Charge the card

- **Provider:** Cardco

| Case | Status | Emits | Sets | When | Timeout | Retries |
|---|---|---|---|---|---|---|
| charged | 200 |  | payment=none->charged charged->charged_twice |  | no | none |
