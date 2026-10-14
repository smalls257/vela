---
id: CAP-002
type: capability
title: Show digest and prep note
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Capture
sources: [2026-10-12-first-release-boundary]
---

# Show digest and prep note

The business can have the Desktop agent show a person the 7:30 digest and the prep note ten minutes before a meeting, on that person's laptop. The Summarizer writes the notes; this capability is showing them at the right time. A digest held back by a sleeping laptop is shown at first login, marked late, and not after 12:00; the product owner has yet to say whether that meets the 7:30 commitment.

## Functional requirements

### CAP-002.FR1 Show the 7:30 digest

Each morning a person who has switched Heron on sees that day's digest on their own laptop. If the laptop was not available at 7:30, they see it the first time they are back at it that morning. A digest shown after 7:30 says that it is late.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements#^c14]]

- A person who has switched Heron on sees that day's digest on their laptop at 7:30.
- If the laptop is off or asleep at 7:30, the digest is shown the first time the person is back at the laptop that morning.
  - Trace: UNK-073
- A digest shown after 7:30 says when it was written and that it is late.
- A digest not yet seen by 12:00 is not shown, and the person is told that this morning's digest was missed.
  - Trace: UNK-073
- If the digest could not be written, the person is told there is none that morning.
  - Trace: the Summarizer runtime page
- An old digest is never shown as if it were new.
- A person who has withdrawn sees no digest.
- When a person withdraws, any digest held for them on the laptop is deleted.

### CAP-002.FR2 Show a prep note before a meeting

The person sees a prep note for a meeting on their own calendar ten minutes before it starts. If the note is ready late, they still see it until the meeting starts, marked late.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements#^c19]]

- A prep note is shown ten minutes before the meeting starts, for a meeting on the person's own calendar.
- A prep note that is ready after ten minutes before the meeting is shown as soon as it is ready, as long as the meeting has not started, and says it is late.
  - Trace: UNK-067
- A prep note not ready by the time the meeting starts is not shown.
  - Trace: UNK-067
- If the note could not be written, nothing is shown and nothing is said.
- If a meeting moves, the note follows the new time. If it is canceled, no note is shown.
- A note already shown for a meeting is not shown again.
- A person who has withdrawn sees no prep note.
- When a person withdraws, any prep note held for them on the laptop is deleted.
