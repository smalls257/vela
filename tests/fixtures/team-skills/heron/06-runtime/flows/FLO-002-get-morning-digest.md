---
id: FLO-002
type: flow
title: A person gets the 7:30 digest
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-013, 2026-10-12-first-release-boundary]
---

# A person gets the 7:30 digest

Each morning the Desktop agent checks the person's consent, reads their calendar entries and any existing Teams transcripts, has the Summarizer write the digest, and shows it at 7:30.

## Steps

1. [[desktop-agent-building-blocks|Desktop agent]] → [[consent-and-identity-building-blocks|Consent and identity]]: sends the person's sign-in, over [[consent-and-identity-building-blocks#CON-003 Consent check|Consent check]].
2. [[consent-and-identity-building-blocks|Consent and identity]] → [[desktop-agent-building-blocks|Desktop agent]]: replies with whether they agreed and what the agent may read, over [[consent-and-identity-building-blocks#CON-003 Consent check|Consent check]].
3. [[desktop-agent-building-blocks|Desktop agent]] → [[03-context-and-scope#PTY-01 Microsoft|Microsoft]]: asks for the person's calendar entries and existing Teams transcripts, over [[desktop-agent-building-blocks#CON-001 Calendar and Teams transcripts|Calendar and Teams transcripts]].
4. [[03-context-and-scope#PTY-01 Microsoft|Microsoft]] → [[desktop-agent-building-blocks|Desktop agent]]: returns them, where they exist and are approved, over [[desktop-agent-building-blocks#CON-001 Calendar and Teams transcripts|Calendar and Teams transcripts]].
5. [[desktop-agent-building-blocks|Desktop agent]] → [[summarizer-building-blocks|Summarizer]]: sends the day's items, over [[summarizer-building-blocks#CON-002 Note request|Note request]].
6. [[summarizer-building-blocks|Summarizer]] → [[desktop-agent-building-blocks|Desktop agent]]: returns the digest, or nothing, over [[summarizer-building-blocks#CON-002 Note request|Note request]].
7. The agent shows the digest at 7:30.
