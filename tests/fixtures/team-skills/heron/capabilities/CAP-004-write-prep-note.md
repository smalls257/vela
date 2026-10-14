---
id: CAP-004
type: capability
title: Write a prep note
state: assumption
owner: "@product-owner"
authored: authored
origin: proposed
change: new
domain: Insight
sources: [2026-10-12-first-release-boundary]
---

# Write a prep note

The business can have the Summarizer write a short prep note for one meeting from that meeting's calendar entry alone, ready ten minutes before it starts. It uses no transcript and no earlier meeting for now; the previous meeting is added once the product owner says the model keeps up with ten minutes.

## Functional requirements

### CAP-004.FR1 Write a prep note for one meeting

For a meeting on their own calendar, a person who has switched Heron on gets a short prep note written from that meeting's calendar entry, ready ten minutes before it starts.

- **State:** assumption
- **Source:** [[2026-10-12-heron-capability-requirements#^c35]]

- The prep note draws only on that meeting's calendar entry.
  - Trace: UNK-067
- The prep note covers one meeting only.
- The prep note says it was written from the calendar entry only.
- A prep note is ready ten minutes before the meeting starts.
  - Trace: UNK-067
- A person who has withdrawn gets no prep note.
