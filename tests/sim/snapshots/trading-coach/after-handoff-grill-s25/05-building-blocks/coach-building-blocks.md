---
id: APP-coach
type: app-building-blocks
title: Coach
state: decided
change: new
stage: target
owner: "@sim-lead"
authored: authored
sources: [SRC-01, SRC-02, SRC-06, 2026-10-08-first-instruments-signal, 2026-10-08-first-release-boundary]
---

# Coach

- **Decision:** [[2026-10-08-coach-contracts-grill]]
- **Override:** E316 by @sim-lead on 2026-10-08: CEO wants the January demo, counsel cleared lessons and paper, open questions to the build team as named risks with owners
- **Options considered:** Coach app behind TickerTalk (picked); Coach built into TickerTalk: rejected, "B drowns mobile, they're already maxed" (the product lead); Coach, a separate board-demo app and Signal as idea source: rejected, "C's too many apps before we know what Brightwater allows" (the product lead)

Coach teaches individual US-listed stocks through lessons and paper practice on quotes delayed by 15 minutes (SRC-02; [[04-solution-strategy#First instruments|First instruments]], decided). It also holds the private January board demo of trade ideas: no customer can open it, it places no live order, and the user buys themselves ([[04-solution-strategy#First release|First release]], decided). It keeps each user's lesson progress and paper positions; where they are kept is not decided.

Coach prepares or places no real order: real orders are release two, and Brightwater keeps the execution (SRC-01). It teaches no ETFs and no options in release one, shows no trade ideas to customers (SRC-06) and holds no customer money, which Brightwater holds (SRC-01). Sign-in and the news stay with [[tickertalk-building-blocks|TickerTalk]]. Coach does not run Signal, whose place is not decided.

<!-- generated:app-context sha=46363da4: do not edit, run vela render -->
```mermaid
flowchart LR
  n_APP_coach["Coach (new)"]
  n_APP_tickertalk["TickerTalk (changed)"]
  x_quoteline__pty_02_["Quoteline (PTY-02)"]
  n_APP_coach -->|"CON-001"| n_APP_tickertalk
  x_quoteline__pty_02_ -->|"CON-002"| n_APP_coach
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef external fill:#ffffff,stroke:#7a8494,color:#19212d,stroke-dasharray:2 2
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  class n_APP_tickertalk changed
  class x_quoteline__pty_02_ external
  class n_APP_coach focus
```

Key: dark blue: the app this page is about · amber: changed by this initiative · white, dashed: outside the initiative (a party or provider) · an arrow is a contract, labeled with its ID.
<!-- /generated:app-context -->

## Containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Lessons | The teaching content and each user's progress | CON-001 | claude | assumption |
| Paper practice | Practice trades and positions | CON-001, CON-002 | claude | assumption |
| Quote display | Shows the delayed quotes | CON-002 | claude | assumption |
| Board demo | The trade-ideas view, opened only for a named list of board members kept by the board owner (the CEO until it is known who manages it); the CON-001 entry never offers it to anyone else | CON-001 | claude | assumption |

## Contracts this app provides

### CON-001 Coach entry

- **Crosses the boundary:** in, the signed-in user's ID from TickerTalk and the request to open the coach; out, the lesson and practice screens.
- **Consumers:** [[tickertalk-building-blocks|TickerTalk]]
- **Change policy:** the Coach and TickerTalk owners agree any change to what crosses; the Coach owner approves before any change to the user ID ships.
- **Change:** new
- **State:** decided
- **Decision:** [[2026-10-08-coach-contracts-grill]]
- **Tested by:** TickerTalk side, the mobile lead; Coach side, the coach lead; neither is named yet, no handles
- **Override:** E316 by @sim-lead on 2026-10-08: CEO wants the January demo, counsel cleared lessons and paper, open questions to the build team as named risks with owners
- **Options considered:** Coach app behind TickerTalk (picked); Coach built into TickerTalk: rejected, "B drowns mobile, they're already maxed" (the product lead); Coach, a separate board-demo app and Signal as idea source: rejected, "C's too many apps before we know what Brightwater allows" (the product lead)

## Contracts this app consumes

### CON-002 Delayed quotes

- **Provider:** Quoteline ([[03-context-and-scope#PTY-02 Quoteline|PTY-02]])
- **Crosses the boundary:** out, US equity quotes delayed by 15 minutes, for display in Kestrel's own apps (SRC-02). Practice trades fill at the delayed quote shown on screen; Coach stores only the user's own practice record and builds no quote history or model from it. Whether lessons and practice count as display under clause 9 is the lead's reading, not settled, and stays open, [[11-unknowns-and-risks#UNK-021 Clause 9 and the coach's lessons and practice|UNK-021]].
- **Consumers:** [[coach-building-blocks|Coach]]
- **Change policy:** not recorded; the notice a change to the license needs is open (Q-PTN-06@PTY-02).
- **Change:** new consumers
- **State:** decided
- **Decision:** [[2026-10-08-coach-contracts-grill]]
- **Tested by:** Coach side, the coach lead (not named yet, no handle); Quoteline side, not consulted
- **Override:** E316 by @sim-lead on 2026-10-08: CEO wants the January demo, counsel cleared lessons and paper, open questions to the build team as named risks with owners
- **Options considered:** Coach app behind TickerTalk (picked); Coach built into TickerTalk: rejected, "B drowns mobile, they're already maxed" (the product lead); Coach, a separate board-demo app and Signal as idea source: rejected, "C's too many apps before we know what Brightwater allows" (the product lead)

<!-- generated:contracts-consumed sha=5c308f02: do not edit, run vela render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[coach-building-blocks#CON-002 Delayed quotes\|CON-002 Delayed quotes]] | Quoteline ([[03-context-and-scope#PTY-02 Quoteline\|PTY-02]]) | not recorded; the notice a change to the license needs is open (Q-PTN-06@PTY-02). | decided |
<!-- /generated:contracts-consumed -->
