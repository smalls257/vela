---
id: EPC-033
type: epic
title: Show the 7:30 digest
state: draft
owner: "@sim-lead"
authored: mixed
apps: [APP-desktop-agent]
delivers: [CAP-001, CAP-002, CAP-003]
consumes: [CON-001, CON-002, CON-003]
flows: [FLO-002]
depends_on: [EPC-032]
---

# Show the 7:30 digest

This epic shows a person their morning digest. Once the person has agreed to calendar entries, the agent reads the day's entries and asks the Summarizer for the digest. The person sees it at 7:30, or the first time they are back at a sleeping laptop, marked late. How long a late digest should be held is still open with the product owner, and the epic is dropped if legal counsel says a digest is a client record.

**Owning team:** @sim-lead (Desk Agent team)

## Epic acceptance criteria

1. The agent reads a day's calendar entries only once the consent check says the person agreed to calendar entries, and reads only the signed-in person's own entries (title, time and attendees), with no mail and no documents.
   - Trace: CAP-001.FR2, CON-003, CON-001, FLO-002
2. The agent reads the day's calendar entries before it asks the Summarizer for the digest, sends the entries with each meeting's attendees and names no one itself, and sends the request even on a day with no meetings.
   - Trace: CAP-001.FR2, CAP-003.FR1, CAP-003.FR2, CON-002, FLO-002
3. The person sees the digest at 7:30. If the laptop was off or asleep, they see it the first time they are back at it that morning, marked late with the time it arrived.
   - Trace: CAP-002.FR1, CON-002, FLO-002, UNK-073
4. A digest not seen by 12:00 is not shown, and the person is told that this morning's digest was missed.
   - Trace: CAP-002.FR1, FLO-002, UNK-073
5. When the Summarizer returns no digest, the person is told there is none that morning, and an old digest is never shown as new.
   - Trace: CAP-002.FR1, CON-002, FLO-002

## Traces to

```traces-to
```

## Depends on

- Switch Heron on and withdraw: the digest needs the person's agreement kept and their withdrawal honored.
  - Trace: EPC-032

## Rollout notes

- Calendar entries only; transcripts join in the transcripts epic.
- Dropped if legal counsel says a digest is a client record, and the prep note kept.
  - Trace: UNK-064
- Part of the February pilot for Client Delivery London, February 2, 2027.

## Out of scope

- Writing the digest: the Summarizer's epic.
- Deleting a held digest on withdrawal: the switch-on and withdraw epic.
- What the agent does when Consent and identity is down: the runtime page holds it, and no requirement does.

## History

- **Options considered:** Four epics, by flow with transcripts separate (picked); Two epics, by capability: rejected, the showing epic would carry about 15 behaviors and need splitting anyway; Three epics, by flow: rejected, reading transcripts would be spread across the digest and prep epics and the pilot epics would carry a gated piece
