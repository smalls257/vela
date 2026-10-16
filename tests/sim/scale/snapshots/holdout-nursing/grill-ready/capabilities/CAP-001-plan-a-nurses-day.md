---
id: CAP-001
type: capability
title: Plan a nurse's day
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Community nursing
sources: [2026-10-12-day-plan-requirements]
---

# Plan a nurse's day

A district nurse starts the day knowing which patients to visit, in what order and why, and the coordinators can see every nurse's day and move visits when something changes. Today the day is built by hand in paper diaries and a shared spreadsheet.

## Functional requirements

### CAP-001.FR1 See the day's visits

A nurse sees the day's visits as a list in the order they are planned.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c01]]
- **Options considered:** A list in visit order (picked); A map: rejected, nurses read the day top to bottom and a map is no use in a car.

- Each visit shows the patient's name, the address, the planned time and what the visit is for.
- A visit at a fixed time is marked as one.

### CAP-001.FR2 Mark a visit done

A nurse marks a visit done with one tap, which records the time.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c02]]
- **Options considered:** Tap done, which records the time (picked); Done when the phone leaves the address: rejected, the nurse decides when a visit is over, not the phone.

- A visit marked done by mistake can be undone the same day.
- The coordinator sees the visit as done within a minute.

### CAP-001.FR3 Reorder the day

A nurse can change the order of the day's visits, except visits at a fixed time.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c03]]
- **Options considered:** Yes, except visits at a fixed time (picked); No, the plan is the plan: rejected, traffic and a long visit happen every day.

- A visit at a fixed time cannot be moved by the nurse.
- The coordinator sees the new order.

### CAP-001.FR4 Tell the patient

A patient gets a text about 30 minutes before the nurse is due.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c04]]
- **Options considered:** A text 30 minutes before (picked); A text on the morning of the day: rejected, a morning text is wrong by lunchtime.

- The text gives the nurse's first name and the expected time, and nothing about the patient's care.
- A visit moved after the text is sent sends a second text.

### CAP-001.FR5 A visit that can't be made

When a visit can't be made, the nurse records why, and the coordinator is told at once.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c05]]
- **Options considered:** The nurse records why and the coordinator is told (picked); It moves to tomorrow on its own: rejected, a missed visit needs a person to judge it.

- The reasons are a short list, with "other" and a note.
- A missed visit at a fixed time is shown to the coordinator first.

### CAP-001.FR6 Visit notes

A nurse writes visit notes on a short template, the same for every visit of a kind.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c06]]
- **Options considered:** A short template (picked); Free text: rejected, notes typed in a car need to be quick and the same every time.

- Every template has a free-text box at the end.
- A visit can't be marked done until its notes are saved.

### CAP-001.FR7 The coordinator's view

A coordinator sees every nurse's day on one screen and can move a visit from one nurse to another.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c07]]
- **Options considered:** Every nurse's day on one screen (picked); One team at a time: rejected, coordinators move visits across teams every morning.

- A moved visit appears on the new nurse's list straight away and leaves the old one's.
- The coordinator sees which visits are at a fixed time.

### CAP-001.FR8 A nurse off sick

When a nurse is off sick, the coordinator reassigns their visits in the app.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c08]]
- **Options considered:** The coordinator reassigns them in the app (picked); By phone, as today: rejected, phoning round takes the first hour of every bad morning.

- Visits at a fixed time are reassigned first.
- Each nurse who takes a visit sees it on their list with a note that it was reassigned.

### CAP-001.FR9 Check in at a visit

A nurse checks in at each visit in Tidewell, so the lone-worker service knows where they are.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c09]]
- **Options considered:** In Tidewell (picked); In the lone-worker service, as today: rejected, one app on the doorstep, not two.

- A check-in records the time and the visit.
- Whether the lone-worker service can take check-ins from Tidewell is open as [[11-unknowns-and-risks#UNK-001 Check-ins and the lone-worker service|check-ins and the lone-worker service]].

### CAP-001.FR10 Notes reach the patient record

Visit notes reach the patient record as each visit ends.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c10]]
- **Options considered:** Straight into the record as each visit ends (picked); In a weekly export: rejected, the record has to be right the same day.

- A note that can't be sent is kept and sent again, and the nurse sees that it is waiting.
- Whether the record system takes notes from Tidewell directly is open as [[11-unknowns-and-risks#UNK-002 Notes into the record system|notes into the record system]].

### CAP-001.FR11 Joint visits with social care

A joint visit with the council's social care team is planned on one plan both teams see.

- **State:** assumption
- **Source:** [[2026-10-12-day-plan-requirements#^c11]]
- **Options considered:** Both teams see the same plan in Tidewell (picked); Joint visits stay on paper: rejected, joint visits are the ones that go wrong most.

- A joint visit can't be moved by one team without the other seeing it.
- Whether the council's staff can be given access is open as [[11-unknowns-and-risks#UNK-003 Council access to the plan|council access to the plan]].
