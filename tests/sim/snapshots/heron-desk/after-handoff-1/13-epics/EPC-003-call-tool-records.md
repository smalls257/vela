---
id: EPC-003
type: epic
title: Call tool records
state: draft
owner: "@agent-lead"
authored: mixed
apps: [APP-heron]
delivers: [CAP-001]
consumes: [CON-003]
flows: [FLO-001]
depends_on: [EPC-001, EPC-002]
---

# Call tool records

This epic turns what the call tools leave behind, read through the [[heron-building-blocks#CON-003 Call tool records|call tool records]] contract, into a short account of the last call with the same client and the points still open from it. It waits on Legal and on which call tools are in use.

- **Owning team:** @agent-lead

## Epic acceptance criteria

1. For a client call with an earlier call with the same client, the note gives a short account of the most recent earlier call, drawn only from what the call tool left behind about that call (CON-003) and from files in the chosen folder (CON-002) (FLO-001). From CAP-001.FR3.
2. An open point appears in the note only when a record over CON-003 or a file in the chosen folder (CON-002) states it as open, and the note says which; the note adds no open point of its own (FLO-001). From CAP-001.FR3.
3. When the most recent earlier call left nothing readable over CON-003, the note says so and does not reach back to an older call (FLO-001). From CAP-001.FR3.
4. For each call, the call tool leaves a readable record that can be tied to that call (CON-003); where it leaves none, Heron says so (FLO-001). From CAP-001.FR3, obligation of CON-003. Which tools leave a readable record is open as UNK-008.
5. The note carries no remark about anyone's mood, tone or performance, whatever the records over CON-003 contain (FLO-001). From CAP-001.FR3.

## Traces to

<!-- generated:traces-to sha=04776c27: do not edit, run vela render -->
| Traces to | Items |
|---|---|
| Apps | [[heron-building-blocks\|Heron]] |
| Delivers | [[CAP-001-prepare-a-client-for-a-call\|CAP-001 Prepare a client for a call]] |
| Consumes | [[heron-building-blocks#CON-003 Call tool records\|CON-003 Call tool records]] |
| Flows | [[FLO-001-prep-note-before-a-client-call\|FLO-001 A person gets a prep note before a client call]] |
| Depends on | [[EPC-001-calendar\|EPC-001 Calendar]], [[EPC-002-chosen-folder\|EPC-002 Chosen folder]] |
| Concerns | none |
<!-- /generated:traces-to -->

## Depends on

- [[EPC-001-calendar|Calendar]]: the most recent earlier call with the same client is found from the past calendar entries EPC-001 reads.
- [[EPC-002-chosen-folder|Chosen folder]]: the account draws on files in the chosen folder, which EPC-002 makes readable.

## Rollout notes

- Part of Release one, the London pilot on 2027-02-02 ([[04b-releases#Release one: London pilot|Release one]]), which is an assumption.

## Out of scope

- Whether Legal allows the call records to be reused, and client attendees named, is open as UNK-025 and gates this epic. No criterion here assumes the answer.
- Whether the DPO's name rule covers the whole note is open as UNK-024.
- Which call tools the pilot team and its clients use is open as UNK-008, and client video calls as UNK-017.

## History

- **Options considered:** Cut C, four epics by what Heron reads (picked): "The constraints already split the work that way—calendar and folder run while Legal's on the call tools."; Cut A, one epic for the whole prep note: rejected, four engineers share one epic with no seam, five requirements fit 4 to 7 criteria only by being coarse, and the epic waits on all fourteen blocking unknowns; Cut B, three epics by what the person sees: rejected, two epics would touch the same call tool records and the same folder, and each is gated by unknowns from all three contracts. Both reasons are Claude's, as the lead gave none.
