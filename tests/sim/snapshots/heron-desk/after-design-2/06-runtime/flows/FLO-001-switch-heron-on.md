---
id: FLO-001
type: flow
title: A person switches Heron on
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-013, 2026-10-12-first-release-boundary]
---

# A person switches Heron on

The person switches the Desktop agent on, and the agent has their agreement kept in Consent and identity, so the record of who agreed to what is not in the agent.

## Steps

1. The person switches the agent on.
2. [[desktop-agent-building-blocks|Desktop agent]] → [[consent-and-identity-building-blocks|Consent and identity]]: sends the person's sign-in and that they agreed, over [[consent-and-identity-building-blocks#CON-004 Record consent|Record consent]].
3. [[consent-and-identity-building-blocks|Consent and identity]] → [[desktop-agent-building-blocks|Desktop agent]]: confirms the agreement was kept, over [[consent-and-identity-building-blocks#CON-004 Record consent|Record consent]].
