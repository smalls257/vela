---
id: building-blocks
type: index
title: Building blocks
arc42: "§5"
authored: mixed
---

# Building blocks

One page per app in scope, named `<app>-building-blocks.md`. Contracts live on the provider's page.

<!-- generated:context-map sha=d1158534: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_consent_and_identity["Consent and identity (new)"]
  n_APP_desktop_agent["Desktop agent (new)"]
  n_APP_summariser["Summariser (new)"]
  x_microsoft["Microsoft"]
  x_microsoft -->|"CON-001"| n_APP_desktop_agent
  n_APP_summariser -->|"CON-002"| n_APP_desktop_agent
  n_APP_consent_and_identity -->|"CON-003"| n_APP_desktop_agent
  n_APP_consent_and_identity -->|"CON-004"| n_APP_desktop_agent
  x_microsoft -->|"CON-005"| n_APP_consent_and_identity
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class x_microsoft external
  class n_APP_consent_and_identity,n_APP_desktop_agent,n_APP_summariser new
```

Key: green: new in this initiative · white, dashed: outside the initiative (a party or provider) · an arrow is a contract, labelled with its ID.
<!-- /generated:context-map -->

## Three apps

The first release is cut into three apps, so the text call can move where the summarising runs without changing the agent's or the consent app's contracts. All three are `assumption`. The [[desktop-agent-building-blocks|Desktop agent]] reads the person's own calendar entries and existing Teams transcripts on the laptop and shows the digest and prep note, and ships through Intune and Jamf in the endpoint lead's 18 January slot. The [[summariser-building-blocks|Summariser]] writes the digest and the prep note behind its own contract, on the laptop in the agent's package or in a shared service, as [[11-unknowns-and-risks#UNK-051 Text call|the text call]] settles. [[consent-and-identity-building-blocks|Consent and identity]] keeps who agreed to what, who signed in, and what access the tenant registration grants, so rebuilding the agent loses none of it.

Intune and Jamf packaging stays the endpoint team's existing pipeline, per [[sources#SRC-013|the tenant note]], and Microsoft 365 is an outside party, [[03-context-and-scope#PTY-01 Microsoft|Microsoft]]. Neither is an app.

## History

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarising inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January
