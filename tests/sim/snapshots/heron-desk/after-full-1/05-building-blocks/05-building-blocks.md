---
id: building-blocks
type: index
title: Building blocks
arc42: "§5"
authored: mixed
---

# Building blocks

One page per app in scope, named `<app>-building-blocks.md`. Contracts live on the provider's page.

<!-- generated:context-map sha=46c029ce: do not edit, run vela render -->
```mermaid
flowchart LR
  n_APP_heron["Heron (new)"]
  x_microsoft["Microsoft"]
  x_the_call_tools_the_pilot_team_and_its_clients_use__not_yet_known["the call tools the pilot team and its clients use, not yet known"]
  x_the_pilot_user__on_their_own_laptop["the pilot user, on their own laptop"]
  x_microsoft -->|"CON-001"| n_APP_heron
  x_the_pilot_user__on_their_own_laptop -->|"CON-002"| n_APP_heron
  x_the_call_tools_the_pilot_team_and_its_clients_use__not_yet_known -->|"CON-003"| n_APP_heron
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class x_microsoft,x_the_call_tools_the_pilot_team_and_its_clients_use__not_yet_known,x_the_pilot_user__on_their_own_laptop external
  class n_APP_heron new
```

Key: green: new in this initiative · white, dashed: outside the initiative (a party or provider) · an arrow is a contract, labeled with its ID.
<!-- /generated:context-map -->

## One laptop app

One app carries the first release: [[heron-building-blocks|Heron]], new, in the Capture area. It reads the calendar and the chosen folder on the laptop, builds the pre-call prep note (the Insight work) and shows it, as one unit to ship, so no text leaves the device. Microsoft stays an outside party.

## History

- **Options considered:** One laptop app (picked); Collector and note builder: rejected, "I don't own anyone yet, and two apps means two ownership questions when I can't answer one."; Laptop agent and cloud summarizer: rejected, "No text off the device in release one, that's the line we hold for the pack."
