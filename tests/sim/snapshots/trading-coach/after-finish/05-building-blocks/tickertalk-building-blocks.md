---
id: APP-tickertalk
type: app-building-blocks
title: TickerTalk
state: decided
change: changed
stage: target
owner: "@sim-lead"
authored: authored
sources: [SRC-12, 2026-10-09-first-instruments, 2026-10-09-first-release-apps]
---

# TickerTalk

TickerTalk is the news app readers already use, and it stays the news app. For the first release it gains the coach screens: lessons, the stock list, progress, paper trades and delayed prices, all drawn from what [[coach-building-blocks|Coach]] sends. It tells Coach who the reader is, hides the coach when the release switch is off, and shows the coach's user-facing copy exactly as Coach sends it, because Brightwater reviews that copy as written. Coach owns the copy, and [[11-unknowns-and-risks#UNK-016 Coach's user-facing copy|who writes it]] is still open. The product lead recalls, on [[sources#SRC-12|their own account]], that the mobile lead confirmed capacity for the first release, but is unsure of the date and has nothing in writing, so [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|the capacity question]] is open.

TickerTalk keeps no lessons, stock list or paper record, places no order, and does not talk to Brightwater or Quoteline for the coach. It changes no news feature and shows no options. It identifies a signed-in reader by an opaque reader ID, [[sources#SRC-16|per the mobile lead]], and sends Coach that ID and nothing else, only for a reader who has opted in. The rest of its data stays in TickerTalk. What TickerTalk holds today, and the lawful basis it holds it on, is not recorded, and [[11-unknowns-and-risks#UNK-049 Who covers TickerTalk out of hours|who covers it out of hours]] is open. The containers table lists only what this release adds.

<!-- generated:app-context sha=8f5872f3: do not edit, run vela render -->
```mermaid
flowchart LR
  n_APP_coach["Coach (new)"]
  n_APP_tickertalk["TickerTalk (changed)"]
  n_APP_coach -->|"CON-001"| n_APP_tickertalk
  n_APP_coach -->|"CON-002"| n_APP_tickertalk
  n_APP_tickertalk -->|"CON-005"| n_APP_coach
  classDef focus fill:#2448b8,stroke:#19212d,color:#ffffff
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  class n_APP_tickertalk focus
  class n_APP_coach new
```

Key: dark blue: the app this page is about · green: new in this initiative · an arrow is a contract, labeled with its ID.
<!-- /generated:app-context -->

## Containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Coach screens | The mobile screens for lessons and paper trades | [[coach-building-blocks#CON-001 Lessons and track\|Lessons and track]], [[coach-building-blocks#CON-002 Paper trades\|Paper trades]] | claude | confirmed |

## Contracts this app provides

### CON-005 Reader identity

Tells Coach who the reader is, so lessons, progress and paper trades attach to the right person. What crosses is the opaque reader ID of a reader who has opted in, and nothing else of TickerTalk's data. Coach signs off any change to it. The contract assumes that the ID [[11-unknowns-and-risks#UNK-047 Is the reader ID stable across email and device changes|stays the same for the life of the account]] and is never reused, that [[11-unknowns-and-risks#UNK-048 Does mobile's plan cover sending the ID only for opted-in readers|TickerTalk checks the opt-in before it sends the ID]], and that Coach creates a reader's record the first time it sees an ID, with no registration call.

- **Crosses the boundary:** out, the opaque reader ID of a signed-in reader with a current opt-in, and nothing else
- **Consumers:** [[coach-building-blocks|Coach]]
- **Change policy:** TickerTalk only adds to the contract; changing, renaming or reissuing the ID needs Coach's agreement, and TickerTalk keeps sending the old ID until Coach says it has moved; Coach signs off changes
- **Tested by:** TickerTalk (mobile), a provider test that only an opted-in reader's opaque ID is sent and that the ID is unchanged across an email change and a new device; Coach, a consumer test that a first-seen ID creates a record and that no other detail is needed, both run in each pipeline per the Coach lead in [[sources#SRC-16|the answers the product lead gathered]]
- **Change:** new
- **State:** decided

## Contracts consumed

<!-- generated:contracts-consumed sha=7202fbd7: do not edit, run vela render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[coach-building-blocks#CON-001 Lessons and track\|CON-001 Lessons and track]] | [[coach-building-blocks\|Coach]] | Coach only adds to the contract; removing or renaming anything needs TickerTalk's agreement, and Coach keeps serving the old shape until mobile says the last app version that uses it is retired | decided |
| [[coach-building-blocks#CON-002 Paper trades\|CON-002 Paper trades]] | [[coach-building-blocks\|Coach]] | Coach only adds to the contract; removing or renaming anything, including an order status, needs TickerTalk's agreement, and Coach keeps serving the old shape until mobile says the last app version that uses it is retired | decided |
<!-- /generated:contracts-consumed -->

## Capabilities

Readers reach these through TickerTalk's screens. [[coach-building-blocks|Coach]] provides them.

- [[CAP-001-teach-a-stock-lesson|Teach a stock lesson]]
- [[CAP-002-paper-trade-a-stock|Paper-trade a stock]]
- [[CAP-003-pass-the-ready-track|Pass the ready track]]

## History

- **Decision:** [[2026-10-09-tickertalk-reader-identity#^c21]]; decided with Q-DAT-02@APP-tickertalk and Q-OPS-01@APP-tickertalk open (W807)
- **Override:** E316 by @sim-lead on 2026-10-09: mobile answers on out-of-hours cover by 14 October; the product lead decides the page now so the Coach screens can be built
- **Options considered:** Coach service behind TickerTalk (picked); Coach inside TickerTalk: rejected, the product lead says "news app stays news"; Coach plus a paper-trading gateway: rejected, two new services for a January demo and a seam that only pays off once real orders exist

#### CON-005 Reader identity

- **Options considered:** Opaque reader ID (picked); email as the identifier: rejected, the mobile lead says TickerTalk identifies readers by an opaque ID, not the email, and an email changes, which would orphan a reader's record
- **Decision:** [[2026-10-09-tickertalk-reader-identity#^c11]]; provider TickerTalk: present (@sim-lead); consumer Coach: not consulted, the Coach lead has not been asked; decided with Q-DAT-01@INI-001, Q-DAT-02@APP-tickertalk, Q-DAT-03@CON-005 and Q-OPS-02@CON-005 open (W807)
- **Override:** GATE-2, E316 by @sim-lead on 2026-10-09: mobile confirms stability and the opt-in check by 14 October; the product lead decides now so Coach can build against the contract
