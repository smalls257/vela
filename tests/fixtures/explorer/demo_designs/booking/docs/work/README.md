# Tickets from the work breakdown

`tickets.csv` was written by `tools/breakdown_to_tickets.py` from `booking-breakdown.md`. No model touched it: each Story row is a
`### S-NN` section and each Task row is a row of that story's task table, in the breakdown's own words. Nothing was
added, merged or reworded. 8 stories and 21 tasks, 29 rows.

## How each column is filled

| Column | From |
|---|---|
| Issue Id | `S-NN` for a story, `S-NN-Tn` for its nth task. Used only to link rows during import. |
| Summary | the story heading (`S-NN name`), or the task's name |
| Description | story: its Traces to line, acceptance criteria and Blocked by line as written. Task: its component, size, and its story's Traces to line |
| Issue Type | Story for a section, Task for a task row. The breakdown has no epic level, so there are no Epics |
| Parent | a task's Issue Id of its story. Blank for stories |
| Story Points | tasks only: S = 2, M = 5, L = 8. The work-breakdown skill gives sizes in days, not points, so this mapping is ours, and sizes are for ordering, not commitments. Stories carry no points so the total is not counted twice |
| Labels | the requirement, contract, criterion and app IDs in the story's Traces to line (`CAP-nnn.FRn@APP-slug`, `CON-nnn`, `EPC-nnn.ACn`, `FR-nnn`, `APP-slug`), one per Labels column; a task has its story's |
| Blocked by | the stories a story is blocked by, from its Blocked by line. Anything else it names (an open question, a gap, an outside party) is in the Description only |

## Import into Jira

1. Jira Cloud: Settings, System, External system import, CSV. (Team-managed or company-managed project: choose the target project first.)
2. Upload `tickets.csv`, tick the comma delimiter, and map the columns: Summary to Summary, Description to Description,
   Issue Type to Issue Type, Issue Id to Issue ID, Parent to Parent, Story Points to Story point estimate, every Labels
   column to Labels, Blocked by to the issue link "Blocks" (as "is blocked by").
3. Map the values Story and Task to your project's issue types. If your project only allows a Sub-task under a Story,
   map Task to Sub-task.
4. Import, then check one story and one of its tasks against `booking-breakdown.md`.

No problems: every line of the breakdown mapped.

## Not ticketed

The breakdown lists these under Not planned, so they have no ticket:

- GAP-1: EPC-036.AC4 has no story; Tidepay's extra-payment flow waits for Booking API v2 (D-001).
- D-001: Booking API v2 (amend with a vehicle change), designed when EPC-036 starts.
- G-002: other teams' criteria of EPC-033, EPC-034, EPC-035, EPC-037 and EPC-038; each owning team plans its own.
- G-003: EPC-039 and EPC-036.AC5 are met under Operations (on-call, dashboards, the monthly report), not by a story.
