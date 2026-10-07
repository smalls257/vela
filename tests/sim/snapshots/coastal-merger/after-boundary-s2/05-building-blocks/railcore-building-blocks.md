---
id: APP-railcore
type: app-building-blocks
title: RailCore
state: assumption
change: integrated
owner: "@sim-lead"
authored: authored
sources: [SRC-04, 2026-10-07-login-owner-and-offer]
---

# RailCore

RailCore is the rail booking engine, hosted by its vendor (SRC-04, an assumption). It is a black box here: this initiative changes nothing inside it, and the Account link service only reads a rail account reference from it. Its vendor SLA and support hours are on [[03-context-and-scope#PTY-03 RailCore vendor|PTY-03]].

<!-- generated:app-context sha=66f1d17e: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_account_link_service["Account link service (new)"]
  n_APP_northway_id["Northway ID (changed)"]
  n_APP_railcore["RailCore (integrated)"]
  n_APP_account_link_service -->|"CON-001"| n_APP_railcore
  n_APP_railcore -->|"CON-003"| n_APP_account_link_service
  n_APP_northway_id -->|"CON-004"| n_APP_railcore
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_northway_id changed
  class n_APP_railcore focus
  class n_APP_account_link_service new
```
<!-- /generated:app-context -->

## Contracts this app provides

### CON-003 Rail account reference

- **Crosses the boundary:** out, a reference to a rail account for a person. SRC-04 does not describe this contract; it is a proposal the lead agreed to when reading back the Account link service.
- **Consumers:** [[account-link-service-building-blocks|Account link service]]
- **Change policy:** Not decided: RailCore is a vendor product, so any change is the vendor's to agree.
- **Change:** unchanged
- **State:** assumption
