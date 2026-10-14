---
id: EPC-032
type: epic
title: Switch Heron on and withdraw
state: draft
owner: "@sim-lead"
authored: mixed
apps: [APP-desktop-agent]
delivers: [CAP-005]
consumes: [CON-003, CON-004]
flows: [FLO-001, FLO-004]
depends_on: []
---

# Switch Heron on and withdraw

This epic is how a person turns Heron on and off. At switch-on the person chooses separately whether Heron may read their calendar entries and whether it may read their Teams transcripts, and a choice counts only once Consent and identity confirms it. A person who withdraws sees nothing more and loses anything Heron held for them. The date still waits on the data protection officer's answer about the lawful basis for each source.

**Owning team:** @sim-lead (Desk Agent team)

## Epic acceptance criteria

1. When a person switches Heron on, they are offered calendar entries and Teams transcripts as two separate choices, and cannot choose transcripts without calendar entries.
   - Trace: CAP-005.FR1, FLO-001
2. Each choice is sent to Consent and identity with the person's sign-in over the record-consent contract, and Heron treats it as kept only when Consent and identity confirms it. What is sent holds the person's sign-in, the source and the date, and no meeting text.
   - Trace: CAP-005.FR1, CON-004, FLO-001
3. When a choice is not confirmed as kept, Heron reads nothing for that person and tells them.
   - Trace: CAP-005.FR1, CON-004, FLO-001
4. For a person who has not switched Heron on, Heron records no agreement and reads nothing.
   - Trace: CAP-005.FR1, CON-004, CON-003, FLO-001
5. When a person switches Heron off, the withdrawal is sent to Consent and identity over the record-consent contract, and later consent checks answer no, so nothing more is read for them.
   - Trace: CAP-001.FR2, CAP-005.FR1, CAP-005.FR2, CON-004, CON-003, FLO-004
6. After a person withdraws, no digest or prep note is shown to them, and any digest or prep note held for them on the laptop is deleted.
   - Trace: CAP-002.FR1, CAP-002.FR2, FLO-004

## Traces to

```traces-to
```

## Depends on

Nothing in this team.

## Rollout notes

- The date still waits on the lawful basis for each source, asked of the DPO by 10 November.
  - Trace: UNK-071
- Part of the February pilot for Client Delivery London, 2 February 2027.

## Out of scope

- Keeping the record of who agreed to what: Consent and identity's epic, not this team's.
- Reading transcripts after a person agrees to them: the transcripts epic.

## History

- **Options considered:** Four epics, by flow with transcripts separate (picked); Two epics, by capability: rejected, the showing epic would carry about 15 behaviors and need splitting anyway; Three epics, by flow: rejected, reading transcripts would be spread across the digest and prep epics and the pilot epics would carry a gated piece
