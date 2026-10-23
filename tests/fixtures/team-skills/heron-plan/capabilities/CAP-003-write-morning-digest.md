---
id: CAP-003
type: capability
title: Write the morning digest
state: assumption
owner: "@product-owner"
authored: authored
origin: proposed
change: new
domain: Insight
sources: [2026-10-12-first-release-boundary]
---

# Write the morning digest

The business can have the Summarizer write each person's 7:30 digest from the day's calendar entries and existing Teams transcripts that the Desktop agent hands it. The digest names only people who were in the meeting. Whether a digest counts as a client record waits on legal counsel, and whether an accepted invitee counts as being in a meeting with no transcript waits on the data protection officer.

## Functional requirements

### CAP-003.FR1 Write each person's digest

Each working morning, a person who has switched Heron on gets a digest written from their own calendar entries and any existing Teams transcripts. On a day with no meetings the digest says so.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements]] c27

- The digest draws only on that person's own calendar entries and the transcripts Heron is allowed to read.
  - Trace: CAP-001.FR1
- The digest lists the day's meetings, with the time and title of each.
- A meeting with no readable transcript is covered from its calendar entry, and the digest says so.
- On a day with no meetings, the digest says there are no meetings today.
- A person who has withdrawn gets no digest.

### CAP-003.FR2 Name only people who were there

A digest names a person only if they were in the meeting. It leaves out any remark about anyone's mood, tone or performance.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements]] c32

- A person who was only mentioned in a meeting, not in it, is not named.
  - Trace: CST-004
- When a meeting has a transcript, the digest names the people the transcript shows took part.
- When a meeting has no transcript, the digest names the accepted invitees once the data protection officer has said they count as being in the meeting. Until then it names no one.
  - Trace: UNK-074
- The digest carries no remark about anyone's mood, tone or performance.
  - Trace: CST-004
- A digest that fails any of these checks is not shown, and no digest is written in its place.
