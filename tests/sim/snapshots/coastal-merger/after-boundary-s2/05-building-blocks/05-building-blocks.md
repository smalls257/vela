---
id: building-blocks
type: index
title: Building blocks
arc42: "§5"
authored: mixed
---

# Building blocks

One page per app in scope, named `<app>-building-blocks.md`. Contracts live on the provider's page.

<!-- generated:context-map sha=c9cea270: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_account_link_service["Account link service (new)"]
  n_APP_ferrymaster["FERRYMASTER (changed)"]
  n_APP_northway_id["Northway ID (changed)"]
  n_APP_railcore["RailCore (integrated)"]
  n_APP_seabook["SeaBook (changed)"]
  n_APP_account_link_service -->|"CON-001"| n_APP_railcore
  n_APP_account_link_service -->|"CON-001"| n_APP_seabook
  n_APP_account_link_service -->|"CON-002"| n_APP_ferrymaster
  n_APP_account_link_service -->|"CON-002"| n_APP_seabook
  n_APP_railcore -->|"CON-003"| n_APP_account_link_service
  n_APP_northway_id -->|"CON-004"| n_APP_account_link_service
  n_APP_northway_id -->|"CON-004"| n_APP_ferrymaster
  n_APP_northway_id -->|"CON-004"| n_APP_railcore
  n_APP_northway_id -->|"CON-004"| n_APP_seabook
  n_APP_northway_id -->|"CON-005"| n_APP_seabook
  n_APP_seabook -->|"CON-006"| n_APP_account_link_service
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  classDef unchanged fill:#eef1f5,stroke:#7a8494,color:#19212d
  class n_APP_ferrymaster,n_APP_northway_id,n_APP_seabook changed
  class n_APP_account_link_service new
  class n_APP_railcore unchanged
```
<!-- /generated:context-map -->

## Login with a link service

The cut of the decided [[04b-identity-provider#Login owner and offer|login owner and offer]] into apps. It is an assumption until a Grill. The Northway Platform team owning the link step is the lead's pick and rests on the CIO's reply (SRC-06, an assumption); the team's commitment is open: [[11-unknowns-and-risks#UNK-050 Platform team commitment to link service|UNK-050]]. The household and the loyalty view have no owning app in this cut.

| App | Change |
|---|---|
| [[northway-id-building-blocks\|Northway ID]] | changed |
| [[seabook-building-blocks\|SeaBook]] | changed |
| [[ferrymaster-building-blocks\|FERRYMASTER]] | changed |
| RailCore | integrated |
| [[account-link-service-building-blocks\|Account link service]] | new |

- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen (claude's reading, the lead gave no separate reason); Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app (claude's reading, the lead gave no separate reason)
