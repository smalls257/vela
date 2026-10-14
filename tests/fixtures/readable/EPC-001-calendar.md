---
id: EPC-001
type: epic
title: Calendar
state: draft
owner: "@agent-lead"
authored: mixed
apps: [APP-heron]
delivers: [CAP-001]
consumes: [CON-001]
flows: [FLO-001]
depends_on: []
---

# Calendar

Heron reads the [[heron-building-blocks#CON-001 Calendar entries|calendar entries]] and builds one note for each client call, shown ten minutes before the call starts. If the entry moves the note moves with it, and if the entry is canceled the note is withdrawn. Still open: how a call is marked as a client call, and whether the entry carries each person's organization.

- **Owning team:** @agent-lead

## Epic acceptance criteria

### Timing of the note

1. For each call that counts as a client call in the person's calendar entries, the person sees one note ten minutes before the call starts; no note appears for a call that does not count.
   - Trace: CAP-001.FR1, CON-001, FLO-001
2. A client call booked, or moved to start, inside ten minutes of the change reaching Heron gets its note as soon as it can be built.
   - Trace: CAP-001.FR1, CON-001, FLO-001
3. When the calendar sends a move, the note is shown ten minutes before the call's new time and not the old one.
   - Trace: CAP-001.FR1, CON-001, FLO-001
4. When the calendar sends a cancellation, no note is shown for that call and a note already built for it is withdrawn.
   - Trace: CAP-001.FR1, CON-001, FLO-001

### Who is on the call

5. The people listed on a client call come from that call's calendar entry and nowhere else: everyone invited appears except those who have declined, someone who joins without being invited does not appear, and a list in the invitation is expanded only when the entry names its members.
   - Trace: CAP-001.FR2, CON-001, FLO-001
6. Each person on the list is shown by name and organization only. Whether the entry carries the organization is still open ([[11-unknowns-and-risks#UNK-026 Whether the calendar entry carries an attendee's organization|the organization question]]).
   - Trace: CAP-001.FR2, CON-001, FLO-001, UNK-026
7. Past calendar entries come over with their attendees, as coming ones do, so the most recent earlier call with the same client can be found.
   - Trace: CAP-001.FR3, CON-001, FLO-001

## Traces to

<!-- generated:traces-to sha=a45fdd5b: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[heron-building-blocks\|Heron]] |
| Delivers | [[CAP-001-prepare-a-client-for-a-call\|CAP-001 Prepare a client for a call]] |
| Consumes | [[heron-building-blocks#CON-001 Calendar entries\|CON-001 Calendar entries]] |
| Flows | [[FLO-001-prep-note-before-a-client-call\|FLO-001 A person gets a prep note before a client call]] |
| Depends on | none |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

None. This epic can start without waiting on another epic.

## Rollout notes

- Part of Release one, the London pilot on 2027-02-02 ([[04b-releases#Release one: London pilot|Release one]]), which is an assumption.

## Out of scope

- The account of the last call and its open points: [[EPC-003-call-tool-records|Call tool records]].
- The message shown when there is no note: [[EPC-004-note-or-reason|Note or reason]].
- Neither [[11-unknowns-and-risks#UNK-021 How a client call is marked|how a call is marked as a client call]] nor [[11-unknowns-and-risks#UNK-023 Invitees and the DPO rule|the data protection officer's rule on listing invitees]] is decided here.

## History

- **Options considered:** Cut C, four epics by what Heron reads (picked): "The constraints already split the work that way—calendar and folder run while Legal's on the call tools."; Cut A, one epic for the whole prep note: rejected, four engineers share one epic with no seam, five requirements fit 4 to 7 criteria only by being coarse, and the epic waits on all fourteen blocking unknowns; Cut B, three epics by what the person sees: rejected, two epics would touch the same call tool records and the same folder, and each is gated by unknowns from all three contracts. Both reasons are Claude's, as the lead gave none.
