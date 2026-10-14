---
id: EPC-035
type: epic
title: Read existing Teams transcripts
state: draft
owner: "@sim-lead"
authored: mixed
apps: [APP-desktop-agent]
delivers: [CAP-001]
consumes: [CON-001, CON-003]
flows: [FLO-002, FLO-003, FLO-004]
depends_on: [EPC-032, EPC-033, EPC-034]
---

# Read existing Teams transcripts

This epic lets the agent read Teams transcripts that already exist. It asks Microsoft for a transcript only where the person agreed to transcripts, the organizer turned transcripts on and the tenant administrators approved reading them, and it reads one only for a meeting the person was in. It is on no release yet, because the security review of 4 December gates it and the endpoint lead and legal counsel must first answer on transcripts, administrator approval and the lawful basis for each source.

**Owning team:** @sim-lead (Desk Agent team)

## Epic acceptance criteria

1. The agent asks Microsoft for a meeting's transcript only where the consent check says the person agreed to transcripts, and reads one only where the organizer turned transcripts on and the tenant administrators approved reading them.
   - Trace: CAP-001.FR1, CON-001, CON-003, FLO-002, FLO-003, UNK-059
2. The agent reads a transcript only for a person who was in that meeting, and none for a meeting they were not in.
   - Trace: CAP-001.FR1, CON-001, FLO-002, FLO-003
3. A person who agreed to calendar entries only never has a transcript read.
   - Trace: CAP-005.FR1, CON-003, FLO-002, FLO-003
4. A meeting with no readable transcript gives no error, and the agent works from the calendar entry.
   - Trace: CAP-001.FR1, CON-001, FLO-002, FLO-003
5. Once a person withdraws, the agent reads no more transcripts for them.
   - Trace: CAP-001.FR1, CON-003, FLO-004

## Traces to

```traces-to
```

## Depends on

- Switch Heron on and withdraw: transcripts need their own agreement from the person.
  - Trace: EPC-032
- Show the 7:30 digest and Show a prep note before a meeting: transcripts feed both, which must already work from calendar entries.
  - Trace: EPC-033, EPC-034

## Rollout notes

- On no release and no date. The CISO review of 4 December is its gate, and the endpoint lead and legal counsel must answer first, on transcripts and admin approval and on the lawful basis for each source.
  - Trace: UNK-059, UNK-071
- Moves to a later release, not the February pilot.

## Out of scope

- Saying in a note that it was written from the calendar entry only: the Summarizer's epic.
- Whether transcripts are approved at all: with the endpoint lead, as transcripts and admin approval.
  - Trace: UNK-059

## History

- **Options considered:** Four epics, by flow with transcripts separate (picked); Two epics, by capability: rejected, the showing epic would carry about 15 behaviors and need splitting anyway; Three epics, by flow: rejected, reading transcripts would be spread across the digest and prep epics and the pilot epics would carry a gated piece
