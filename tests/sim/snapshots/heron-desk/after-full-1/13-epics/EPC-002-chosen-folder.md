---
id: EPC-002
type: epic
title: Chosen folder
state: draft
owner: "@agent-lead"
authored: mixed
apps: [APP-heron]
delivers: [CAP-001]
consumes: [CON-002]
flows: [FLO-001]
depends_on: []
---

# Chosen folder

This epic covers the one folder Heron may read, set through the [[heron-building-blocks#CON-002 Chosen folder|chosen folder]] contract. The person names the folder and can change it later. When it is not set, missing or empty, the person sees a plain message saying so.

- **Owning team:** @agent-lead

## Epic acceptance criteria

1. The person can name one folder and change it later (CON-002, FLO-001); after a change the next note uses the new folder. From CAP-001.FR4.
2. Heron reads nothing of the person's apart from the chosen folder (CON-002), the calendar entries (CON-001) and the call tools' records (CON-003): no mailbox and no general document search (FLO-001). From CAP-001.FR4.
3. Until a folder is chosen, the note for a client call says that no folder is set (CON-002, FLO-001). From CAP-001.FR4.
4. When the chosen folder is missing or empty, the note says so and names the problem (CON-002, FLO-001). From CAP-001.FR4.
5. From a folder that holds files for several clients, the note uses only the files that relate to the call's client, matched as for CAP-001.FR3 (CON-002, FLO-001). From CAP-001.FR4. How a call is matched to its client is open as UNK-022.
6. The files in the chosen folder can be read and nothing is written back to it (CON-002). From CAP-001.FR3, obligation of CON-002.

## Traces to

<!-- generated:traces-to sha=73670621: do not edit, run planner render -->
| Traces to | Items |
|---|---|
| Apps | [[heron-building-blocks\|Heron]] |
| Delivers | [[CAP-001-prepare-a-client-for-a-call\|CAP-001 Prepare a client for a call]] |
| Consumes | [[heron-building-blocks#CON-002 Chosen folder\|CON-002 Chosen folder]] |
| Flows | [[FLO-001-prep-note-before-a-client-call\|FLO-001 A person gets a prep note before a client call]] |
| Depends on | none |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

None. This epic can start without waiting on another epic.

## Rollout notes

- Part of Release one, the London pilot on 2027-02-02 ([[04b-releases#Release one: London pilot|Release one]]), which is an assumption.

## Out of scope

- Using the folder's files for the account of the last call: [[EPC-003-call-tool-records|Call tool records]].
- Whether the pilot team keeps pointing Heron at a folder every day is open as UNK-019.

## History

- **Options considered:** Cut C, four epics by what Heron reads (picked): "The constraints already split the work that way—calendar and folder run while Legal's on the call tools."; Cut A, one epic for the whole prep note: rejected, four engineers share one epic with no seam, five requirements fit 4 to 7 criteria only by being coarse, and the epic waits on all fourteen blocking unknowns; Cut B, three epics by what the person sees: rejected, two epics would touch the same call tool records and the same folder, and each is gated by unknowns from all three contracts. Both reasons are Claude's, as the lead gave none.
