---
id: APP-consent-and-identity
type: app-building-blocks
title: Consent and identity
state: assumption
change: new
stage: target
domain: Trust
owner: "@product-owner"
authored: authored
sources: [SRC-009, SRC-013, 2026-10-12-first-release-boundary]
---

# Consent and identity

Consent and identity keeps who agreed to what, who signed in, and what access was granted, in a shared service that Marlowe's people operate, not on the laptop. It answers the Desktop agent's question whether a person has agreed, takes the agent's word when a person switches Heron on or off, and owns asking for the tenant registration. The solution lead says the works council audits the record, and that rebuilding the agent must not lose it. Its part in each requirement is under Requirements allocated, all still assumptions. The Record consent contract says only that a person switched Heron on or off, not a choice per source, and its wording is left for the Grill on this app.

It does not read calendar entries or transcripts, write notes, or push anything to laptops. It does not approve its own registration: the identity team raises it and [[sources#SRC-009|the CISO's review]] has to clear it first. It does not write the data list the works council reads, which is [[11-unknowns-and-risks#UNK-057 Full list of data Heron reads|a separate open question]]. Still open: which team builds it ([[11-unknowns-and-risks#UNK-068 Who builds Consent and identity|who builds Consent and identity]]) and whether the registration review fits before the 18 January slot ([[11-unknowns-and-risks#UNK-058 Security review pack|the security review pack]], [[11-unknowns-and-risks#UNK-069 When the registration request goes in|when the request goes in]]). The tenant note says [[sources#SRC-013|a registration is raised through the identity team]].

## Containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Consent record | Keeps who agreed to what, and when, and who withdrew. | Consent check; Record consent | claude | assumption |
| Sign-in link | Ties a person's Microsoft 365 sign-in to their record. | Microsoft sign-in; Consent check | claude | assumption |
| Registration | Holds the tenant app registration and what it grants. | none | claude | assumption |

## Contracts this app provides

### CON-003 Consent check

The Desktop agent asks Consent and identity whether a person has agreed, before it reads anything, and gets back what it may read.

- **Crosses the boundary:** In: the person's sign-in. Out: whether they have agreed, and which sources the agent may read (calendar entries, transcripts).
- **Consumers:** [[desktop-agent-building-blocks|Desktop agent]]
- **Change policy:** A change is agreed by the product owner and the agent's team before the January package.
- **Change:** new
- **State:** assumption

### CON-004 Record consent

The Desktop agent tells Consent and identity when a person switches Heron on or off, so the record of who agreed to what is kept outside the agent.

- **Crosses the boundary:** In: the person's sign-in and whether they switched on or off. Out: confirmation that it was kept.
- **Consumers:** [[desktop-agent-building-blocks|Desktop agent]]
- **Change policy:** A change is agreed by the product owner and the agent's team before the January package.
- **Change:** new
- **State:** assumption

## Contracts this app consumes

### CON-005 Microsoft sign-in

Consent and identity asks Microsoft 365 who signed in, so each record belongs to a real person.

- **Provider:** [[03-context-and-scope#PTY-01 Microsoft|Microsoft]]
- **Crosses the boundary:** In: a sign-in request. Out: who signed in.
- **Consumers:** [[consent-and-identity-building-blocks|Consent and identity]]
- **Change policy:** Not recorded. Microsoft runs the interface, and no agreement with Microsoft is registered.
- **Change:** new
- **State:** assumption

## Requirements allocated

| Requirement | Share | Through | State |
|---|---|---|---|
| [[CAP-001-read-calendar-and-transcripts#CAP-001.FR1 Read existing Teams transcripts\|Read existing Teams transcripts]] | answers before anything is read whether the person has agreed to transcripts, and answers no once they have withdrawn or when it is down | CON-003 | assumption |
| [[CAP-001-read-calendar-and-transcripts#CAP-001.FR2 Read the person's own calendar entries\|Read the person's own calendar entries]] | answers before anything is read whether the person has agreed to calendar entries, separately from transcripts, and answers no before they switch on, after they withdraw, or when it is down | CON-003 | assumption |
| [[CAP-002-show-digest-and-prep-note#CAP-002.FR1 Show the 7:30 digest\|Show the 7:30 digest]] | answers no to the consent check once the person has withdrawn, so the agent shows no digest | CON-003 | assumption |
| [[CAP-002-show-digest-and-prep-note#CAP-002.FR2 Show a prep note before a meeting\|Show a prep note before a meeting]] | answers no to the consent check once the person has withdrawn, so the agent shows no prep note | CON-003 | assumption |
| [[CAP-003-write-morning-digest#CAP-003.FR1 Write each person's digest\|Write each person's digest]] | answers no to the consent check once the person has withdrawn, so the agent sends the Summariser nothing | CON-003 | assumption |
| [[CAP-004-write-prep-note#CAP-004.FR1 Write a prep note for one meeting\|Write a prep note for one meeting]] | answers no to the consent check once the person has withdrawn, so the agent sends the Summariser nothing | CON-003 | assumption |
| [[CAP-005-record-persons-consent#CAP-005.FR1 Agree to each source separately\|Agree to each source separately]] | keeps each source choice with the person, the source and the date; also refuses transcripts without calendar entries; confirms to the agent only once the choice is kept; answers the consent check per source, and no for a person who has not switched on | CON-004, CON-003 | assumption |

## Capabilities

- [[CAP-005-record-persons-consent|Record a person's consent]]
- [[CAP-006-answer-consent-check|Answer whether a person has agreed]]

## Where it fits

<!-- generated:app-context sha=6b4f9cdc: do not edit, run planner render -->
```mermaid
flowchart LR
  n_APP_consent_and_identity["Consent and identity (new)"]
  n_APP_desktop_agent["Desktop agent (new)"]
  x_microsoft["Microsoft"]
  n_APP_consent_and_identity -->|"CON-003"| n_APP_desktop_agent
  n_APP_consent_and_identity -->|"CON-004"| n_APP_desktop_agent
  x_microsoft -->|"CON-005"| n_APP_consent_and_identity
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class x_microsoft external
  class n_APP_consent_and_identity focus
  class n_APP_desktop_agent new
```
<!-- /generated:app-context -->

<!-- generated:contracts-consumed sha=a859dfe7: do not edit, run planner render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[consent-and-identity-building-blocks#CON-005 Microsoft sign-in\|CON-005 Microsoft sign-in]] | [[03-context-and-scope#PTY-01 Microsoft\|Microsoft]] | Not recorded. Microsoft runs the interface, and no agreement with Microsoft is registered. | assumption |
<!-- /generated:contracts-consumed -->

## History

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarising inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January

#### CON-003

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarising inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January

#### CON-004

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarising inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January

#### CON-005

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarising inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January
