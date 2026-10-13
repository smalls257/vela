---
id: CAP-005
type: capability
title: Record a person's consent
state: assumption
owner: "@product-owner"
authored: authored
origin: proposed
change: new
domain: Trust
sources: [2026-10-12-first-release-boundary]
---

# Record a person's consent

The business can have Consent and identity keep a record of who agreed to what, and who withdrew, in a shared service that the works council can audit. The Desktop agent tells it when a person switches Heron on or off. A person agrees to calendar entries and to Teams transcripts separately, and agreeing to transcripts needs the calendar entries too.

## Functional requirements

### CAP-005.FR1 Agree to each source separately

When a person switches Heron on, they choose separately whether Heron may read their calendar entries and whether it may read their Teams transcripts. Each choice is kept.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements#^c39]]

- A person chooses separately for calendar entries and for Teams transcripts.
- A person cannot agree to transcripts without agreeing to calendar entries.
- Each choice is recorded with the person, the source and the date.
- Heron reads a source for a person only if they have agreed to that source.
- A person who has agreed to calendar entries only never has a transcript read.
- If a choice could not be recorded, Heron reads nothing for the person and tells them.
- A person who has not switched Heron on is never recorded as having agreed.

### CAP-005.FR2 Stop reading when a withdrawal is not confirmed

When a person switches Heron off and Consent and identity does not confirm the withdrawal, Heron stops reading for that person at once, so a person never believes they have withdrawn while Heron still reads.

- **State:** assumption
- **Source:** [[2026-10-12-desk-agent-epics#^c06]]

- Heron stops reading for the person at once, without waiting for Consent and identity to confirm.
- Heron deletes what it holds for the person.
- Heron tells the person that the withdrawal is not yet recorded and that it is still trying to send it.
- Heron keeps trying to send the withdrawal until Consent and identity confirms it.
