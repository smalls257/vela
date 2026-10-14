---
id: RUN-desktop-agent
type: app-runtime
title: Desktop agent runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-013, 2026-10-12-first-release-boundary]
---

# Desktop agent runtime

The Desktop agent runs on each laptop and depends on three things: Consent and identity for proof of consent, the Summarizer for the note, and Microsoft 365 for calendar entries and transcripts. When any of them is down, it shows nothing rather than something wrong.

## On failure

- If Consent and identity is down, the agent reads nothing and shows no note, because it has no proof of consent.
- If the Summarizer is down or slow, the agent shows nothing that morning and says so. It never shows an old note as new.
- If Microsoft 365 is down, there is no note that morning.

## Flows

- [[FLO-001-switch-heron-on|A person switches Heron on]]
- [[FLO-002-get-morning-digest|A person gets the 7:30 digest]]
- [[FLO-003-get-prep-note|A person gets a prep note]]
- [[FLO-004-withdraw-consent|A person withdraws]]

## History

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarizing inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January
