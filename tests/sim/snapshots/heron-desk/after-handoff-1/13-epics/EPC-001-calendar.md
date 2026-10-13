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

This epic turns the [[heron-building-blocks#CON-001 Calendar entries|calendar entries]] Heron reads into the right note at the right time. A note is built for each client call and shown ten minutes before the call starts. When the entry moves, the note follows the new time, and when the entry is cancelled, the note is withdrawn. The people on the call are taken from the entry alone, and the past entries are read the same way so the last call with the same client can be found.

- **Owning team:** @agent-lead

## Epic acceptance criteria

1. For each call that counts as a client call in the person's calendar entries (CON-001), the person sees one note ten minutes before the call starts (FLO-001); no note appears for a call that does not count as a client call. From CAP-001.FR1.
2. A client call booked, or moved to start, inside ten minutes of the change reaching Heron over CON-001 gets its note as soon as it can be built (FLO-001). From CAP-001.FR1.
3. When CON-001 sends a move, the note is shown ten minutes before the call's new time and not the old one (FLO-001). From CAP-001.FR1.
4. When CON-001 sends a cancellation, no note is shown for that call and a note already built for it is withdrawn (FLO-001). From CAP-001.FR1.
5. The people listed on a client call come from that call's entry over CON-001 and nowhere else: everyone invited appears except those who have declined, someone who joins without being invited does not appear, and a list in the invitation is expanded only when the entry names its members (FLO-001). From CAP-001.FR2.
6. Each person on the list is shown by name and organisation only (CON-001, FLO-001). From CAP-001.FR2. Whether the entry carries the organisation is open as UNK-026.
7. Past calendar entries come over CON-001 with their attendees, as coming ones do, so the most recent earlier call with the same client can be found (FLO-001). From CAP-001.FR3.

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
- How a call is marked as a client call is open as UNK-021, and the DPO's rule on listing invitees as UNK-023. Neither is decided here.

## History

- **Options considered:** Cut C, four epics by what Heron reads (picked): "The constraints already split the work that way—calendar and folder run while Legal's on the call tools."; Cut A, one epic for the whole prep note: rejected, four engineers share one epic with no seam, five requirements fit 4 to 7 criteria only by being coarse, and the epic waits on all fourteen blocking unknowns; Cut B, three epics by what the person sees: rejected, two epics would touch the same call tool records and the same folder, and each is gated by unknowns from all three contracts. Both reasons are Claude's, as the lead gave none.
