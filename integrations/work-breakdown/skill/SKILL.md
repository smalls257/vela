---
name: work-breakdown
description: Use when a technical design is settled and the work needs breaking into stories and tasks a team can build in order. Every story traces to a requirement (in vault mode, an allocated requirement row or epic criterion) and to the design components that deliver it; every task is sized S, M or L; the plan ends with what blocks what and the order to build in. Requires a design doc at status complete or complete-with-gaps. Triggers include "break down the work", "work breakdown", "stories and tasks", "plan the build".
---

<what-to-do>

Turn a settled design into stories and tasks, and prove nothing was left out. Read the design and its inputs, propose the stories, then walk them with the user one at a time, with your recommended answer for each question.

Pure *plan*. Assumes the *what* and the *how* are settled: `docs/tech-design/<slug>.md` at `status: complete` or `complete-with-gaps`. Refuse to start otherwise and tell the user to finish `tech-design-grill`.

Every story traces to at least one requirement and at least one design component. Every requirement and every component is covered by at least one story. Reject the plan while either is not true.

Do not reopen design or requirement questions. A gap becomes an open question in the plan and a note for the user to take back to `tech-design-grill` (or, in vault mode, `/planner:challenge`).

Write the plan to `docs/plan/<slug>-breakdown.md` as stories are agreed. Do not batch.

</what-to-do>

<supporting-info>

## Inputs

- **Required:** `docs/tech-design/<slug>.md` with `status: complete` or `complete-with-gaps`. Read its `gaps[]` and `deferred[]`: each acknowledged gap and deferral either gets a story, or is listed under "Not planned" with its ID.
- **Requirements:** `docs/requirements/<slug>.md` (`FR-XXX`), or in vault mode (`--vault <path> --app <APP-id>`) the app page's `## Requirements allocated` rows, the contracts it provides and consumes, and the acceptance criteria of the epics that list the app. Read them as `TECH-DESIGN-FROM-VAULT.md` in the vault says; never edit the vault.
- **Also scan:** `CONTEXT.md`, `docs/adr/*.md`, and the codebase if brownfield, so tasks name real modules.

## Trace targets

- Requirements: each `FR-XXX`, or in vault mode each allocated row as `CAP-nnn.FRn@APP-<slug>`, each contract `CON-nnn`, and each epic criterion `EPC-nnn.ACn`.
- Components: every component named in the design's component section.

Build the coverage table before proposing stories, and keep it current as stories change.

## Session

1. **Propose the cut.** Group the work into stories a team can demo: each delivers behaviour someone can see, not a layer. Read back the proposed list, numbered, each with the targets it traces to. Ask the user to confirm or reshape it.
2. **One story at a time.** For each agreed story, propose and confirm: its acceptance criteria (from the requirement or epic criterion it traces to, never invented), the design sections it rests on, and its tasks.
3. **Size each task** `S` (up to about 2 days), `M` (3 to 5 days) or `L` (1 to 2 weeks), for one engineer. A task larger than `L` is split. Sizes are for ordering, not commitments; say so in the plan.
4. **Dependencies.** For each story, what it is blocked by: another story, an open question, a deferred item, a gap, or an outside party. Name the ID.
5. **Order.** Propose the build order: what unblocks most comes first, what waits on outside answers comes last or behind a switch. Confirm it with the user.

## Output: `docs/plan/<slug>-breakdown.md`

Frontmatter as `FRONTMATTER-FORMAT.md` in `tech-design-grill`, with `prereqs[]` naming the design doc. Then:

- An opening paragraph: what the plan covers, its inputs with their status, and what the sizes mean.
- A summary table: story, what it traces to, size total, blocked by.
- One section per story: `### S-NN <name>`, the line "Traces to: ..." (IDs only, comma-separated, each one of the trace targets above, nothing in prose), one plain sentence a developer can test ("Done when a person who refuses transcripts never has one read."), its acceptance criteria as bullets, a task table (`| Task | Size | Component |`), and "Blocked by: ...". Never copy vault text: link the requirement and write the sentence yourself.
- A story the plan holds back, defers or splits keeps the same fields. A lettered split (`S-07a`, `S-07b`) has its own traces, sentence, criteria, tasks and blockers, and is in the summary table and the build order like any story. A story the plan will not build is not in the table: it is under `## Not planned` with its ID and why.
- `## Build order`: the stories in order, with one line on why each sits where it does.
- `## Coverage`: every trace target and every component with the stories that cover it. An empty cell fails the plan.
- `## Not planned`: each gap, deferral or open question the plan does not cover, with its ID and why.

## Completion gate

- Every trace target and every component has a story. Every story has tasks, every task a size, every story its blockers.
- Every `gaps[]` and `deferred[]` entry of the design is a story or is under "Not planned".
- Run `NEG-AUDIT.md` from `tech-design-grill` against the plan itself. In particular **Paper Tiger** (do the stories add up to what the requirements need, not just to the components?) and **Distributed Monolith** (can each story ship without waiting on all the others?).

- Every story in the summary table is in the build order, and the reverse.

Record the audit's result in the session notes, not in the plan: the plan says "Audited on <date> against `NEG-AUDIT.md`; the result is in the session notes." The audit's own vocabulary (the violation names) is the author's checklist, not something a developer reads.

Set `status: complete` only if all of that holds. If the user goes ahead with an uncovered target or an acknowledged violation, set `complete-with-gaps` with a `gaps[]` entry for each.

## Hard rules

- Never invent acceptance criteria. A criterion comes from a requirement, an epic, a contract or the design.
- Never edit the design, the requirements or the vault. Gaps go back upstream as open questions.
- Never estimate in dates or people. Sizes only; the team plans the calendar.
- Never split, merge, drop or reorder stories without reading the change back and getting the user's yes. Being allowed to edit the plan is not leave to change what was agreed.

</supporting-info>
