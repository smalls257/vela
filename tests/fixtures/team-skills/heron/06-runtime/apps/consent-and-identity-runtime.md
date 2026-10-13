---
id: RUN-consent-and-identity
type: app-runtime
title: Consent and identity runtime
state: assumption
owner: "@product-owner"
authored: authored
sources: [SRC-013, 2026-10-12-first-release-boundary]
---

# Consent and identity runtime

Consent and identity runs as a shared service that Marlowe's people operate. The Desktop agent calls it before every read and whenever a person switches Heron on or off. It consumes only Microsoft sign-in. If the security review does not pass by mid-December, the registration request cannot go in and the 18 January slot slips.

## On failure

- If it is down, or the sign-in fails, it answers no, and the Desktop agent reads nothing.
- If the security review has not passed by mid-December, the registration request cannot go in and the 18 January slot slips.

## Flows

- [[FLO-001-switch-heron-on|A person switches Heron on]]
- [[FLO-002-get-morning-digest|A person gets the 7:30 digest]]
- [[FLO-003-get-prep-note|A person gets a prep note]]
- [[FLO-004-withdraw-consent|A person withdraws]]
- [[FLO-005-get-tenant-registration|Heron gets its tenant registration]]

## History

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarising inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January
