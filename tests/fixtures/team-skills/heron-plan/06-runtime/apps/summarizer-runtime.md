---
id: RUN-summarizer
type: app-runtime
title: Summarizer runtime
state: assumption
owner: "@product-owner"
authored: authored
sources: [2026-10-12-first-release-boundary]
---

# Summarizer runtime

The Summarizer answers one request at a time from the Desktop agent and returns a note or nothing. It consumes nothing from another app in the first release. How long counts as slow is not yet defined ([[11-unknowns-and-risks#UNK-067 How slow is too slow|how slow is too slow]]).

## On failure

- If the model fails or returns something unusable, the Summarizer returns no note rather than a partial one.
- If the Summarizer is down or slow, the Desktop agent shows nothing that morning and says so. It never shows an old note as new.

## Flows

- [[FLO-002-get-morning-digest|A person gets the 7:30 digest]]
- [[FLO-003-get-prep-note|A person gets a prep note]]

## History

- **Options considered:** Three apps (picked); Two apps: rejected, it keeps the summarizing inside the agent, so a cloud answer to the text call would pull it out after the agent's contracts are fixed in early January
