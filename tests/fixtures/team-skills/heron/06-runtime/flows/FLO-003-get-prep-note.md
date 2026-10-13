---
id: FLO-003
type: flow
title: A person gets a prep note
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-013, 2026-10-12-first-release-boundary]
---

# A person gets a prep note

Ten minutes before a meeting the Desktop agent checks consent, reads that meeting's calendar entry and any existing transcript, has the Summariser write a prep note, and shows it.

## Steps

1. [[desktop-agent-building-blocks|Desktop agent]] → [[consent-and-identity-building-blocks|Consent and identity]]: sends the person's sign-in, over [[consent-and-identity-building-blocks#CON-003 Consent check|Consent check]].
2. [[consent-and-identity-building-blocks|Consent and identity]] → [[desktop-agent-building-blocks|Desktop agent]]: replies with whether they agreed and what the agent may read, over [[consent-and-identity-building-blocks#CON-003 Consent check|Consent check]].
3. [[desktop-agent-building-blocks|Desktop agent]] → [[03-context-and-scope#PTY-01 Microsoft|Microsoft]]: asks for that meeting's calendar entry and any existing Teams transcript, over [[desktop-agent-building-blocks#CON-001 Calendar and Teams transcripts|Calendar and Teams transcripts]].
4. [[03-context-and-scope#PTY-01 Microsoft|Microsoft]] → [[desktop-agent-building-blocks|Desktop agent]]: returns them, where they exist and are approved, over [[desktop-agent-building-blocks#CON-001 Calendar and Teams transcripts|Calendar and Teams transcripts]].
5. [[desktop-agent-building-blocks|Desktop agent]] → [[summariser-building-blocks|Summariser]]: sends that meeting's items, over [[summariser-building-blocks#CON-002 Note request|Note request]].
6. [[summariser-building-blocks|Summariser]] → [[desktop-agent-building-blocks|Desktop agent]]: returns the prep note, or nothing, over [[summariser-building-blocks#CON-002 Note request|Note request]].
7. The agent shows the prep note ten minutes before the meeting.
