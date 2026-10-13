---
id: APP-northway-id
type: app-building-blocks
title: Northway ID
state: assumption
change: changed
stage: target
owner: "@sim-lead"
authored: authored
sources: [SRC-04, SRC-06, 2026-10-07-login-owner-and-offer]
---

# Northway ID

Northway ID is the shared login. It signs a customer in once, proves who they are, and hands each system one person key: the decided [[04b-identity-provider#Login owner and offer|login owner and offer]]. Rail customers keep the login they have (SRC-04, an assumption). Ferry customers get one, though whether they are meant to is open: [[11-unknowns-and-risks#UNK-031 Ferry customers and Northway ID|UNK-031]]. Who owns Northway ID itself is open: [[11-unknowns-and-risks#UNK-012 Northway ID ownership|UNK-012]].

It does not hold the household, the link or the loyalty view. The link step belongs to the [[account-link-service-building-blocks|Account link service]]. It does not merge or keep customer records, because each company keeps its own (SRC-06).

- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen; Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app

<!-- generated:app-context sha=5faac5f3: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_account_link_service["Account link service (new)"]
  n_APP_ferrymaster["FERRYMASTER (changed)"]
  n_APP_northway_id["Northway ID (changed)"]
  n_APP_railcore["RailCore (integrated)"]
  n_APP_seabook["SeaBook (changed)"]
  n_APP_northway_id -->|"CON-004"| n_APP_account_link_service
  n_APP_northway_id -->|"CON-004"| n_APP_ferrymaster
  n_APP_northway_id -->|"CON-004"| n_APP_railcore
  n_APP_northway_id -->|"CON-004"| n_APP_seabook
  n_APP_northway_id -->|"CON-005"| n_APP_seabook
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  classDef unchanged fill:#eef1f5,stroke:#7a8494,color:#19212d
  class n_APP_ferrymaster,n_APP_seabook changed
  class n_APP_northway_id focus
  class n_APP_account_link_service new
  class n_APP_railcore unchanged
```

Key: dark blue: the app this page is about · green: new in this initiative · amber: changed by this initiative · grey: stays as it is · an arrow is a contract, labelled with its ID.
<!-- /generated:app-context -->

## Containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Sign-in | Where the customer proves who they are | [[#CON-004 Sign in and person key\|CON-004]] | claude | assumption |
| Person directory | Holds each customer's login, unique email and person key | [[#CON-004 Sign in and person key\|CON-004]], [[#CON-005 Enrol a ferry customer\|CON-005]] | claude | assumption |

## Contracts this app provides

### CON-004 Sign in and person key

- **Crosses the boundary:** in, the customer's credentials; out, proof of who signed in and their person key.
- **Consumers:** [[seabook-building-blocks|SeaBook]], [[ferrymaster-building-blocks|FERRYMASTER]], [[railcore-building-blocks|RailCore]], [[account-link-service-building-blocks|Account link service]]
- **Change policy:** Not decided: the owner sets it with each consumer before build.
- **Change:** new consumers
- **State:** assumption
- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen; Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app

### CON-005 Enrol a ferry customer

- **Crosses the boundary:** in, a ferry customer's details, with their agreement; out, a new Northway ID and its person key. It rests on [[11-unknowns-and-risks#UNK-037 Northway ID terms for ferry customers|UNK-037]] and UNK-031.
- **Consumers:** [[seabook-building-blocks|SeaBook]]
- **Change policy:** Not decided: the owner sets it with each consumer before build.
- **Change:** new
- **State:** assumption
- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen; Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app

## Contracts this app consumes

None from the other apps in this cut. Sign-in flows one way, into Northway ID.

<!-- generated:contracts-consumed sha=140bedbf: do not edit, run planner render -->
none
<!-- /generated:contracts-consumed -->
