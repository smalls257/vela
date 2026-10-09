---
id: FLO-001
type: flow
title: A reader starts learning
state: decided
owner: "@sim-lead"
authored: authored
sources: [SRC-16, 2026-10-09-coach-tickertalk-journeys]
---

# A reader starts learning

A signed-in TickerTalk reader opts in to the coach and begins a lesson on one stock. [[tickertalk-building-blocks|TickerTalk]] holds the reader's consent and shows the screens, and [[coach-building-blocks|Coach]] creates the reader's record and serves the lessons. TickerTalk sends Coach only the opaque reader ID, and only once the reader has opted in. Coach creates the record the first time it sees that ID, before it serves the first lesson. The privacy lead signed off the opt-in wording, as [[11-unknowns-and-risks#UNK-042 Opt-in language for Coach's reader records|the opt-in language for Coach's reader records]] records: "Coach keeps your lessons, practice trades and progress, under your reader ID, so you can pick up where you left off. Nothing is used to train any model."

If the reader ID does not reach Coach, or Coach is down at step 3 or 4, the opt-in stands. The reader sees the same "coach isn't available" message as when Coach is down at any other time, and no lesson. TickerTalk sends the ID again the next time the reader opens the coach, and Coach creates the record then, so the reader never opts in twice. A reader who withdraws consent is outside this flow. TickerTalk stops sending the ID and hides the coach, and [[11-unknowns-and-risks#UNK-054 What Coach does with a reader's record after withdrawal|what Coach does with the record it already holds]] is not decided.

## Steps

1. TickerTalk shows the coach entry only when the release switch is on and the reader is signed in. Uses [[CAP-001-teach-a-stock-lesson|Teach a stock lesson]].
2. The reader opts in on TickerTalk, which holds the consent.
3. TickerTalk sends Coach the opaque reader ID of the opted-in reader, and nothing else, over [[tickertalk-building-blocks#CON-005 Reader identity|Reader identity]].
4. Coach creates the reader's record the first time it sees the ID, with no registration call, over [[tickertalk-building-blocks#CON-005 Reader identity|Reader identity]].
5. TickerTalk asks Coach for the lessons, the stock list and the reader's progress over [[coach-building-blocks#CON-001 Lessons and track|Lessons and track]], and draws the screens from them.
6. The reader works through a lesson on one stock. TickerTalk shows Coach's copy exactly as sent, with delayed prices labelled as delayed, using [[CAP-001-teach-a-stock-lesson|Teach a stock lesson]].

## History

- **Decision:** [[2026-10-09-grill-journeys]]
