---
id: EPC-004
type: epic
title: Note or reason
state: draft
owner: "@agent-lead"
authored: mixed
apps: [APP-heron]
delivers: [CAP-001]
consumes: []
flows: [FLO-001]
depends_on: [EPC-001, EPC-002, EPC-003]
---

# Note or reason

This epic holds the whole journey of [[FLO-001-prep-note-before-a-client-call|a person getting a prep note before a client call]] together. Every client call ends in a note or a plain reason for none, a note that is late is shown and marked as late, and the list of who is on the call is never lost.

- **Owning team:** @agent-lead

## Epic acceptance criteria

1. Every client call in FLO-001 gets either a note or a short message saying why there is none, so the person is never left with silence. From CAP-001.FR5.
2. A first call with a client gets a note that says there is no earlier call and still lists who is on the call (FLO-001, CON-001). From CAP-001.FR5.
3. When what the call tool left behind cannot be read (CON-003), the message says so (FLO-001). From CAP-001.FR5.
4. A note not ready by ten minutes before the call is shown as soon as it is ready, clearly marked as late, and is not dropped (FLO-001). From CAP-001.FR5. Whether the pilot laptops can build the note in time is open as UNK-027.
5. A message never takes the place of the list of who is on the call, when the entry over CON-001 makes that known (FLO-001). From CAP-001.FR5.

## Traces to

<!-- generated:traces-to sha=6571f4c2: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[heron-building-blocks\|Heron]] |
| Delivers | [[CAP-001-prepare-a-client-for-a-call\|CAP-001 Prepare a client for a call]] |
| Consumes | none |
| Flows | [[FLO-001-prep-note-before-a-client-call\|FLO-001 A person gets a prep note before a client call]] |
| Depends on | [[EPC-001-calendar\|EPC-001 Calendar]], [[EPC-002-chosen-folder\|EPC-002 Chosen folder]], [[EPC-003-call-tool-records\|EPC-003 Call tool records]] |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-001-calendar|Calendar]]: the list of who is on the call and the times come from the calendar entries.
- [[EPC-002-chosen-folder|Chosen folder]]: the messages for a folder that is not set, missing or empty are part of the folder behavior.
- [[EPC-003-call-tool-records|Call tool records]]: the message for unreadable call tool records and the first-call case rest on the account of the last call.

## Rollout notes

- Part of Release one, the London pilot on 2027-02-02 ([[04b-releases#Release one: London pilot|Release one]]), which is an assumption.

## Out of scope

- A message when the calendar entries themselves cannot be read is not held by any requirement. The runtime page says Heron then shows no note and says why, but no CAP-001 requirement states it, so no criterion is written until one does (`/planner:requirements` on CAP-001, then `/planner:allocate`).

## History

- **Options considered:** Cut C, four epics by what Heron reads (picked): "The constraints already split the work that way—calendar and folder run while Legal's on the call tools."; Cut A, one epic for the whole prep note: rejected, four engineers share one epic with no seam, five requirements fit 4 to 7 criteria only by being coarse, and the epic waits on all fourteen blocking unknowns; Cut B, three epics by what the person sees: rejected, two epics would touch the same call tool records and the same folder, and each is gated by unknowns from all three contracts. Both reasons are Claude's, as the lead gave none.
