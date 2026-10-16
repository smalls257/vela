---
id: FLO-001
type: flow
title: A person gets a prep note before a client call
state: assumption
owner: "@sim-lead"
authored: authored
sources: [2026-10-11-first-release-boundary]
---

# A person gets a prep note before a client call

A person in the pilot team has a client call coming. They point Heron at a folder once, and ten minutes before the call Heron shows them one note on who is on the call, what was said last time and what is still open, so they walk in prepared.

## Steps

1. The person points Heron at the one folder it may read.
2. [[03-context-and-scope#PTY-01 Microsoft|Microsoft]] → [[heron-building-blocks|Heron]]: sends the person's calendar entries over [[heron-building-blocks#CON-001 Calendar entries|Calendar entries]].
3. [[heron-building-blocks|Heron]] builds the note and shows it ten minutes before the call, as [[CAP-001-prepare-a-client-for-a-call|Prepare a client for a call]].
