---
id: APP-customer-identity-runtime
type: app-runtime
title: Customer identity runtime
initiative: INI-002
arc42: "§6"
state: decided
owner: Platform team
authored: authored
last_verified: 2026-11-20
sources: ["Customer identity read API documentation"]
---

[[README|Harbourline]] / [[06-flows|06 Flows]] / [[customer-identity-building-blocks|Customer identity]] / Runtime

# Customer identity runtime

Customer identity is unchanged. In [[FLO-001-hold-pay-confirm|FLO-001]] it answers Booking's lookup before a hold. It has no part in FLO-002 or FLO-003.

```mermaid
sequenceDiagram
  participant API as Booking API
  participant CI as Customer identity
  API->>CI: look up customer (CON-005)
  CI-->>API: customer record
```

If Customer identity is down, Booking refuses the hold and tells the channel why.
