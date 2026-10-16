---
id: CAP-001
type: capability
title: Prepare a client for a call
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Capture
sources: [2026-10-11-first-release-boundary]
---

# Prepare a client for a call

A person in the pilot team can see, ten minutes before a client call, who is on the call, what was said last time and what is still open. Today they piece it together themselves. [[heron-building-blocks|Heron]] delivers it.

## Functional requirements

### CAP-001.FR1 Note before a client call

A pilot team member gets one note about ten minutes before each client call. The note is built as soon as the call is known and shown at ten minutes before the start.

- **State:** assumption
- **Source:** [[2026-10-11-prep-note-requirements#^c04]]

- On a day with a client call, the person sees one note ten minutes before the call starts.
- A call booked or moved to start inside ten minutes gets its note as soon as it can be built.
- A call that is canceled gets no note, and a note already built for it is withdrawn.
- A call moved to a new time is shown ten minutes before the new time, not the old one.
- The note appears only for calls that count as client calls. How a call is marked as one is open as [[11-unknowns-and-risks#UNK-021 How a client call is marked|how a call is marked]].

### CAP-001.FR2 Who is on the call

The note lists the people on the call, taken from the person's calendar entry for it and nowhere else. It shows each one's name and organization, and no one who was not in the meeting.

- **State:** assumption
- **Source:** [[2026-10-11-prep-note-requirements#^c05]]

- Everyone invited on the calendar entry appears, except those who have declined. Whether the DPO's rule allows an invitee who may not join is open as [[11-unknowns-and-risks#UNK-023 Invitees and the DPO rule|the invitees question]], and the lawful basis for naming client attendees as [[11-unknowns-and-risks#UNK-025 Reusing call records and client names|reusing call records]].
- A person who has declined does not appear.
- A person who joins the call without being invited does not appear.
- A list in the invitation is expanded only when the calendar entry names its members; otherwise it is not expanded.
- Each person is shown by name and organization only.

### CAP-001.FR3 Last time and what is open

The note gives a short account of the last call with the same client, and the points still open from it. It draws only on what the call tool left behind and on the one folder the person chose.

- **State:** assumption
- **Source:** [[2026-10-11-prep-note-requirements#^c06]]

- "Last time" is the most recent earlier call with the same client. How a call is matched to the client is open as [[11-unknowns-and-risks#UNK-022 How an earlier call is matched to the same client|how an earlier call is matched]].
- The account uses only what the call tool left behind about that call and the files in the chosen folder. Whether the DPO's name rule covers it is open as [[11-unknowns-and-risks#UNK-024 DPO rule across the whole note|the reach of the DPO rule]], and the basis for reusing call records as [[11-unknowns-and-risks#UNK-025 Reusing call records and client names|reusing call records]].
- An open point appears only when a record the call tool left or a file in the chosen folder states it as open, and the note says which one.
- The note adds no open point of its own.
- When the most recent earlier call left nothing readable, the note says so and does not reach back to an older call. Which call tools leave a readable record is open as [[11-unknowns-and-risks#UNK-008 Call tools in use|which call tools are in use]].
- The note carries no remark about anyone's mood, tone or performance.

### CAP-001.FR4 The person chooses the folder

The person names the one folder the note may draw on, and can change it. The note draws on nothing else of the person's, apart from their calendar and what the call tools left behind.

- **State:** assumption
- **Source:** [[2026-10-11-prep-note-requirements#^c08]]

- The person can name one folder and change it later.
- Nothing outside that folder, the calendar and the call tools' records is read: no mailbox and no general document search.
- After a change of folder, the next note uses the new folder.
- Until a folder is chosen, the note says that no folder is set.
- When the chosen folder is missing or empty, the note says so, naming the problem.
- From a folder that holds files for several clients, the note uses only the files that relate to the call's client, matched as for CAP-001.FR3.

### CAP-001.FR5 A note, or the reason for none

Every client call gets either a note or a short message saying why there is no note, so the person is never left with silence.

- **State:** assumption
- **Source:** [[2026-10-11-prep-note-requirements#^c09]]

- A first call with a client gets a note that says there is no earlier call, and still lists who is on the call.
- When what the call tool left behind cannot be read, the message says so.
- A note that is not ready by ten minutes before the call is shown as soon as it is ready, clearly marked as late, and is not dropped.
- A message never takes the place of the list of who is on the call, when that is known.

## History

#### CAP-001.FR2

- **Options considered:** everyone invited who has not declined (picked); only the people who accepted: rejected, most client invitees never reply, so the list would be empty for most calls; no list of people before the call: rejected, it is the first thing the pilot team asked for

#### CAP-001.FR4

- **Options considered:** one folder the person names and can change (picked); the whole OneDrive: rejected, it reads far more than the note needs and is the part most likely to read as monitoring; a folder IT sets for each team: rejected, people keep client files in different places

#### CAP-001.FR5

- **Options considered:** a note, or a short message saying why there is none (picked); silence when there is nothing to show: rejected, the person cannot tell a quiet day from a broken helper; a note with blank sections: rejected, it reads as if the call had no history
