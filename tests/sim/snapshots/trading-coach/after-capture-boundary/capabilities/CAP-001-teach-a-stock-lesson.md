---
id: CAP-001
type: capability
title: Teach a stock lesson
state: assumption
change: new
owner: "@sim-lead"
authored: authored
origin: proposed
domain: Learning
---

# Teach a stock lesson

A reader can learn one stock at a time through lessons in the coach, on a stock from the list. It is provided by [[coach-building-blocks|Coach]].

## Functional requirements

### CAP-001.FR1 Learn one stock at a time

A reader opens a lesson on one stock from the list and works through it. Any listed stock can be studied in any order, one at a time, and nothing has to be finished first.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c02]]

- The reader can start a lesson only on a stock that is on the list, in any order and with no earlier lesson finished first.
- The reader sees the lesson of one stock at a time.

### CAP-001.FR2 Keep the reader's place

The business remembers which lessons a reader has finished, so the reader can pick up where they left off. Only finished lessons are remembered, and a lesson left part-way starts again.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c03]]

- After leaving and coming back, the reader sees the same lessons marked finished.
- Finishing the same lesson twice counts once.
- A lesson left part-way is not marked finished, and starts again from its beginning.

### CAP-001.FR3 Label delayed prices

Any price a reader sees in a lesson is labeled as delayed by 15 minutes. When the delayed price cannot be had, the lesson still shows and the price is replaced by a plain "price unavailable", so the reader is never shown an old price under a label that says it is current.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c04]]

- Every price shown in a lesson carries a visible "delayed 15 minutes" label.
- No lesson shows a price without that label.
- When the delayed price cannot be had, the lesson still shows, with "price unavailable" in place of the price and no earlier price shown.

### CAP-001.FR4 Show only approved wording

Brightwater reviews every lesson shown to its customers as written, so a reader sees exactly the wording Brightwater approved, and no lesson reaches a reader before it has passed. A demo shown only inside Kestrel is outside this rule, per [[11-unknowns-and-risks#UNK-033 Does the review reach an internal board demo|the answer on the board demo]]. That exemption is unconfirmed until [[11-unknowns-and-risks#UNK-062 Written confirmation of the board-demo exemption|UNK-062]] writes it down.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c05]]

- The text a reader sees matches the text Brightwater reviewed, word for word.
- A lesson Brightwater has not passed is never shown to a reader.

### CAP-001.FR5 Explain trades, suggest none

Lessons explain how a trade works and use a listed stock as the example, but they never suggest a trade or judge a stock. They state facts and teach concepts, and they cover equities only.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c06]], [[sources#SRC-08|Outside Counsel's reply of 8 October]]

- No lesson says or implies that a reader should buy, sell or hold a particular stock, or that it is cheap, strong or weak.
- No lesson teaches options.

### CAP-001.FR6 Tell the reader when unavailable

When lessons cannot be served, the reader sees a plain "coach isn't available" message and no partial lesson, and their earlier progress is intact when the coach is back.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c07]]

- With lessons unavailable, the reader sees the "coach isn't available" message and no lesson.
- When lessons are available again, the reader's earlier progress is intact.
- If lessons become unavailable mid-lesson, the reader sees the same message and that lesson is not marked finished.

### CAP-001.FR7 Keep progress on dropped stocks

When a stock leaves the list, the lessons a reader already finished on it still count toward ready, and no new or part-done lesson on it can be taken, so nobody passes on half a lesson for a stock the business no longer teaches.

- **State:** assumption
- **Source:** [[2026-10-10-coach-tickertalk-requirements#^c08]]

- A reader's finished lessons on a dropped stock still count toward the ready track.
- The reader cannot start a new lesson on a dropped stock.
- A lesson not yet finished on a stock that leaves the list cannot be continued.
