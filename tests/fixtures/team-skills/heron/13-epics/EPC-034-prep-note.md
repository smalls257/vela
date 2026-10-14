---
id: EPC-034
type: epic
title: Show a prep note before a meeting
state: draft
owner: "@sim-lead"
authored: mixed
apps: [APP-desktop-agent]
delivers: [CAP-002, CAP-004]
consumes: [CON-001, CON-002, CON-003]
flows: [FLO-003]
depends_on: [EPC-032]
---

# Show a prep note before a meeting

This epic shows a person a short prep note ten minutes before a meeting on their own calendar. The agent reads only that meeting's calendar entry, sends it to the Summarizer, and shows the note when it comes back, marked late if it is late and not at all if none comes. How early the agent must ask is still open with the product owner.

**Owning team:** @sim-lead (Desk Agent team)

## Epic acceptance criteria

1. Before a meeting on the person's own calendar, the agent checks the consent check, reads that meeting's calendar entry, and asks the Summarizer for a note, sending only that meeting's entry, with no transcript and no earlier meeting.
   - Trace: CAP-004.FR1, CON-003, CON-001, CON-002, FLO-003
2. The agent asks early enough for the note to be ready, and shows it ten minutes before the meeting starts.
   - Trace: CAP-002.FR2, CAP-004.FR1, CON-002, FLO-003, UNK-067
3. A note that is ready after that time is shown as soon as it is ready, marked late, until the meeting starts, and not after.
   - Trace: CAP-002.FR2, FLO-003, UNK-067
4. If a meeting moves, the note follows the new time. If it is canceled, no note is shown. A note already shown is not shown again.
   - Trace: CAP-002.FR2, CON-001, FLO-003
5. When no note comes, nothing is shown and nothing is said.
   - Trace: CAP-002.FR2, CON-002, FLO-003

## Traces to

```traces-to
```

## Depends on

- Switch Heron on and withdraw: the prep note needs the person's agreement kept and their withdrawal honored.
  - Trace: EPC-032

## Rollout notes

- How early the agent must ask is open with the product owner, as how slow is too slow.
  - Trace: UNK-067
- Part of the February pilot for Client Delivery London, 2 February 2027.

## Out of scope

- Writing the prep note: the Summarizer's epic.
- Deleting a held note on withdrawal: the switch-on and withdraw epic.
- Transcripts in a prep note: the transcripts epic.

## History

- **Options considered:** Four epics, by flow with transcripts separate (picked); Two epics, by capability: rejected, the showing epic would carry about 15 behaviors and need splitting anyway; Three epics, by flow: rejected, reading transcripts would be spread across the digest and prep epics and the pilot epics would carry a gated piece
