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

Heron reads the [[heron-building-blocks#CON-001 Calendar entries|calendar entries]] and builds one note for each client call, shown ten minutes before the call starts. If the entry moves the note moves with it, and if the entry is cancelled the note is withdrawn.

Still open: how a call is marked as a client call, and whether the entry carries each person's organisation.

- **Owning team:** @agent-lead

## Who this is for and what changes

The people who take client calls in the London pilot team are the readers. Today they open the calendar and the last call's notes by hand before each call. With this epic the note is built for them from the calendar entry, so they read one page instead of two.

## Done when

### Timing of the note

#### One note ten minutes before a client call

For each call that counts as a client call in the person's calendar entries, the person sees one note ten minutes before the call starts. No note appears for a call that does not count.

- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC1  ·  [testing]

#### A late booking still gets its note

A client call booked, or moved to start, inside ten minutes of the change reaching Heron gets its note as soon as it can be built.

- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC2

#### A move moves the note

When the calendar sends a move, the note is shown ten minutes before the call's new time and not the old one.

- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC3

#### A cancellation withdraws it

When the calendar sends a cancellation, no note is shown for that call and a note already built for it is withdrawn.

- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC4

### Who is on the call

#### The list comes from the entry

The people listed on a client call come from that call's calendar entry and nowhere else. Everyone invited appears except those who have declined, and someone who joins without being invited does not appear.

- Trace: CAP-001.FR2, CON-001, FLO-001  ·  AC5  ·  [data]

#### Name and organisation only

Each person on the list is shown by name and organisation only. Whether the entry carries the organisation is still open.

- Trace: CAP-001.FR2, CON-001, FLO-001, UNK-026  ·  AC6

#### Past entries come over too

Past calendar entries come over with their attendees, as coming ones do, so the most recent earlier call with the same client can be found.

- Trace: CAP-001.FR3, CON-001, FLO-001  ·  AC7

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
