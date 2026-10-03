---
name: epics
description: Epics session for an initiative vault at stage 6. Works team by team from the traceability gaps, shapes 2 or 3 epic cuts, drafts boundary acceptance criteria with concern markers, grills the solution lead one criterion at a time, and runs check --gate epics before calling an app's epics complete.
argument-hint: "<team handle or APP-id, or 'every team'>"
disable-model-invocation: true
---

# Epics

Turn a handed-off slice into epics a team can build from. The check finds the gaps, so the frontier is never guessed. Only the Grill part of this session sets an epic to `decided`.

The planner is `python3 .claude/skills/planner/bin/planner`. The format, including the epic page and the trace rules, is in `CONVENTIONS.md` under "Epics and traceability".

## 1. Start

Run the steps in `.claude/skills/planner/references/START.md` with modes `shape` and `grill`. Read the Shape and Grill rows of `.claude/skills/planner/references/MODES.md`. If the vault has no remote or `gh` fails, START says so and the session goes on.

## 2. Read the frontier

Run `python3 .claude/skills/planner/bin/planner render`, then read the `traceability` block on `13-epics/13-epics.md`. Its rows are the work: capabilities nobody delivers (T1), new or changed contracts with no provider epic (T2), concern cells with work and no marked criterion (T4), and epics that deliver nothing (T6). Work one team at a time. A team is an `owner:` handle on app pages.

## 3. Shape the cuts

For the team's gaps, offer 2 or 3 ways to cut them into epics. Each epic has exactly one owning team. Say what each cut makes easy and what it makes hard, such as which cutover it unblocks first. Say which one you prefer. Capture the user's choice, and each rejected cut with its reason. Shape never decides, so the chosen cut stays `draft`.

## 4. Draft each epic

Write `13-epics/EPC-nnn-<slug>.md` with the next free number, at `state: draft`. Grep the vault for the existing EPC numbers and add one to the highest. Add a `## Changes` row to the session record: `| EPC-nnn | - | draft | [[<session id>#^cNN]] |`, citing the capture of the chosen cut. A new ID with no row there is an invented ID.

- Frontmatter: `id`, `type: epic`, `title`, `state: draft`, `owner`, `authored: mixed`, `apps`, `delivers`, `consumes`, `flows` and `depends_on`, per `CONVENTIONS.md`. Lists hold IDs.
- `**Owning team:**` in the description.
- `## Epic acceptance criteria`: 4 to 7 numbered criteria. Each describes behaviour a tester can see at a contract or a flow boundary. Name the contract or flow by ID. Never name a component, a table, a technology or a container's internals. Every criterion sits at the boundary.
- End each criterion that does a concern cell's work with the concern's marker, such as `[testing]` or `[security] [data]`. Every `addressed` cell for the epic's apps needs one marked criterion on an epic whose `apps` lists the app, or a waiver in the cell. Markers go on numbered criteria. A bulleted criterion carries none.
- `## Traces to` holding an empty `traces-to` block, `## Depends on` with one reason per dependency, `## Rollout notes` and `## Out of scope`.

Write no description paragraph yet. Prose is drafted at close, through `house-voice`. Until then the page holds the bullets, the criteria and the sections above.

## 5. Behaviour the vault does not hold

If a criterion needs behaviour no page records, stop on that criterion. Say which capability it belongs to, and offer to run requirements-grill on that `CAP-NNN`. Add `requirements` to the session's `modes` if the user says yes. The requirement is written once, on the capability, at most `assumption`, and the criterion cites it. Never write the requirement into the epic. If the user declines, leave the criterion out and list it under the epic's `## Out of scope` as waiting on that `CAP-NNN`.

## 6. Grill the criteria

For each epic the user wants decided, run the gate in `.claude/skills/planner/skills/grill/SKILL.md` section 2. For an epic, GATE-1 reads each of the epic's apps, GATE-2 reads `draft` with the chosen cut and the rejected cuts written down, and GATE-5 asks for the solution lead. Show the table, and write the `## Agenda` section into the session record, one line per epic, as grill does. START's resume rule reads it.

Then take each criterion in turn:

- Show the criterion and ask whether it is right. Give your recommended wording and a one-line reason, in the form *Recommended: <wording>. <reason>.* Wait.
- Capture the answer. The lead's own words take their name as origin. An accepted recommendation has origin `claude, from <name>`.
- Silence, "ok", "next" or "sure" with nothing else do not count. Ask for an explicit yes or for another wording. Keep your recommendation under pushback without a reason.
- Never answer your own question.

Set an epic to `decided` only when the solution lead confirms the epic as a whole in this session. Read the final criteria back, and get an explicit yes to that read-back. Then, as grill does:

- set `state: decided`;
- add `- **Decision:** [[<session id>]]` and a `## Changes` row `| EPC-nnn | draft | decided | [[<session id>#^cNN]] |`;
- mark the deciding capture `→ keep: [[<page>#<heading>|EPC-nnn]] (decided)`;
- commit with the message `grill: EPC-nnn decided`, staging the session record and the epic by exact path.

If the lead never confirms, the epic stays `draft`, and its agenda line says `status open`.

## 7. Check the gate

Run `python3 .claude/skills/planner/bin/planner render`, then `python3 .claude/skills/planner/bin/planner check --gate epics`. Read every `E50x` line for the team's apps. Never say an app's epics are complete while one remains. Show the remaining lines and say what each needs.

## Ends when

Every chosen team's gaps are closed or listed, or the user stops. Tell the user: "Run `/planner:close` to finish the session and open the PR."

## Never

- Never set `decided` without the lead's confirmation in this session.
- Never put one epic under two owning teams.
- Never name a component, table or technology in a criterion.
- Never edit a generated block. Render fills `traces-to`, `epics-for-app`, `delivered-by` and `traceability`.
