---
id: FLO-004
type: flow
title: A person withdraws
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-013, 2026-10-12-first-release-boundary]
---

# A person withdraws

The person switches the Desktop agent off, and the agent tells Consent and identity, so later consent checks answer no.

## Steps

1. The person switches the agent off.
2. [[desktop-agent-building-blocks|Desktop agent]] → [[consent-and-identity-building-blocks|Consent and identity]]: sends the person's sign-in and the withdrawal, over [[consent-and-identity-building-blocks#CON-004 Record consent|Record consent]].
3. [[consent-and-identity-building-blocks|Consent and identity]] → [[desktop-agent-building-blocks|Desktop agent]]: confirms the withdrawal was kept, over [[consent-and-identity-building-blocks#CON-004 Record consent|Record consent]].
