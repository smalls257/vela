---
id: APP-call-centre-runtime
type: app-runtime
title: Call centre desktop runtime
initiative: INI-002
arc42: "§6"
state: decided
owner: Contact Centre Systems team
authored: authored
last_verified: 2026-11-20
sources: ["Contact Centre Systems senior container review"]
---

[[README|Harbourline]] / [[06-flows|06 Flows]] / [[call-centre-building-blocks|Call centre desktop]] / Runtime

# Call centre desktop runtime

| Flow | Desktop's part |
|---|---|
| [[FLO-001-hold-pay-confirm\|FLO-001]] | The agent finds a crossing, the desktop asks Booking for a hold, the agent takes payment through Tidepay, and the desktop asks Booking to confirm. |
| [[FLO-002-amend-or-cancel\|FLO-002]] | The agent finds the booking by reference. Booking says whether the change is allowed and re-quotes an amendment. The desktop shows the result. |

The desktop has no part in [[FLO-003-notify-on-change|FLO-003]]. Customers get the same email or SMS whichever channel made the change.

```mermaid
sequenceDiagram
  participant A as Agent
  participant D as Desktop client
  participant API as Booking API
  A->>D: find booking
  D->>API: get (CON-001)
  API-->>D: booking state
  A->>D: amend
  D->>API: amend, preview
  API-->>D: change allowed, new fare
  A->>D: accept
  D->>API: amend, accept
  API-->>D: confirming
  D->>API: get, until amended
  API-->>D: amended
```

The diagram shows FLO-002 because the amend and cancel screens are the new part. FLO-001 follows the same calls as the website, with Tidepay taking payment as it does today.

## When a dependency is slow or down

- **Ledger write slow.** The desktop shows "confirming" and the agent can end the call. The customer's notification follows when Booking completes the write. There is no manual fix queue to fall back to.
- **Booking down.** The desktop says booking is unavailable and the agent cannot hold or amend. It does not switch to the terminal adapter on its own. During the 4 weeks after cutover, a person can flip the switch back.
