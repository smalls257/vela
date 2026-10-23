---
id: CAP-001
type: capability
title: Read calendar and Teams transcripts
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Capture
sources: [2026-10-12-first-release-boundary]
---

# Read calendar and Teams transcripts

The business can have the Desktop agent read a person's own calendar entries and any Teams transcripts that already exist, on that person's laptop. It reads no mail and no documents in the first release. A transcript exists only where the organizer turned it on and needs tenant admin approval, so for most meetings the agent has the calendar entry and nothing more, and the note says it was written from the calendar entry only. Whether transcripts may be read at all still waits on legal counsel and the data protection officer.

## Functional requirements

### CAP-001.FR1 Read existing Teams transcripts

Where a meeting has a Teams transcript that Heron is allowed to read, Heron reads it for a person who was in that meeting. Where there is none, Heron has the calendar entry only, and the person is told when a note is thin for that reason.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements]] c03

- Heron reads a transcript only if the organizer turned transcripts on and the tenant administrators have approved reading them.
  - Trace: CST-008, UNK-059
- Heron reads a transcript only for a person who was in that meeting and has switched Heron on, and stops reading once they withdraw.
- A meeting with no readable transcript gives no error. Heron works from the calendar entry.
- A note for a meeting with no readable transcript says that it was written from the calendar entry only.
- Heron reads no transcript of a meeting the person was not in.

### CAP-001.FR2 Read the person's own calendar entries

Heron reads the signed-in person's own calendar entries for the day, and for each meeting the title, time and attendees that the entry holds.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements]] c05

- Heron reads only the signed-in person's own calendar.
- Heron reads each entry's title, time and attendees.
- Heron reads no mail and no documents in the first release.
- Heron reads nothing until the person has switched Heron on, and nothing after they withdraw.
- Heron reads a day's calendar entries before the 7:30 digest is written.
