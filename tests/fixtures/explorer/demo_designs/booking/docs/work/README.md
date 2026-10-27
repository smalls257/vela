# Tickets from the work breakdown

`tickets.csv` was written by `tools/breakdown_to_tickets.py` from `booking-breakdown.md`. Each Story row is a `### S-NN` section of the plan and each Task row a row of its task table. A story's summary and its grouped acceptance criteria were written into the plan in the house voice, and vela checked that every one of the plan's criteria is still covered; the plan keeps its criteria word for word. What a story relies on (contracts and requirements) and what it still waits on (open questions) are copied by code from the vault and the design. 8 stories and 21 tasks, 29 rows. This file was written without the vault, so each ticket names what it relies on by ID only.

## How each column is filled

| Column | From |
|---|---|
| Issue Id | `S-NN` for a story, `S-NN-Tn` for its nth task. Used only to link rows during import. |
| Summary | the story's name, or the task's name |
| Description | story: its summary, its acceptance criteria (grouped, each line tagged with the plan criteria it covers, or the plan's own list when the story has no grouped criteria yet), Done when, What this story relies on, Still open, then Components, Slice, Size, Blocked by (stories by name), anything else it waits on, Release fit, and any "Open for the design" and "Conflicts" notes. Task: its component, size and its story's name |
| Issue Type | Story for a section, Task for a task row. The breakdown has no epic level, so there are no Epics |
| Parent | a task's Issue Id of its story. Blank for stories |
| Story Points | tasks only: S = 2, M = 5, L = 8. The work-breakdown skill gives sizes in days, not points, so this mapping is ours, and sizes are for ordering, not commitments. Stories carry no points so the total is not counted twice |
| Labels | the requirement and contract IDs on the story's Traces to line, each epic a criterion belongs to (`EPC-nnn`) and any app ID; then its slice shape (tracer, vertical, layer) and vault slice; `needs-design` for an "Open for ..." note and `conflict` for a "Conflict with ..." note. A task has its story's IDs only |
| Blocked by | the stories a story is blocked by, from its Blocked by line. Anything else it names (an open question, a gap, an outside party) is in the Description only |

## Import into Jira

1. Jira Cloud: Settings, System, External system import, CSV. (Team-managed or company-managed project: choose the target project first.)
2. Upload `tickets.csv`, tick the comma delimiter, and map the columns: Summary to Summary, Description to Description,
   Issue Type to Issue Type, Issue Id to Issue ID, Parent to Parent, Story Points to Story point estimate, every Labels
   column to Labels, Blocked by to the issue link "Blocks" (as "is blocked by").
3. Map the values Story and Task to your project's issue types. If your project only allows a Sub-task under a Story,
   map Task to Sub-task.
4. Import, then check one story and one of its tasks against `booking-breakdown.md`.

## Problems

These lines could not be mapped cleanly. Fix the breakdown (or the ticket by hand), then run again.

- S-01: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-02: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-03: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-04: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-05: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-06: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-07: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list
- S-08: has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the plan's criteria as a flat list

## Not ticketed

The breakdown lists these as deferred, merged or not planned, so they have no ticket:

- GAP-1: EPC-036.AC4 has no story; Tidepay's extra-payment flow waits for Booking API v2 (D-001).
- D-001: Booking API v2 (amend with a vehicle change), designed when EPC-036 starts.
- G-002: other teams' criteria of EPC-033, EPC-034, EPC-035, EPC-037 and EPC-038; each owning team plans its own.
- G-003: EPC-039 and EPC-036.AC5 are met under Operations (on-call, dashboards, the monthly report), not by a story.
