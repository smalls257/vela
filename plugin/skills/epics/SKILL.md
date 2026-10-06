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

Run the steps in `.claude/skills/planner/references/START.md` with modes `epics`, `shape` and `grill`. The record has `modes: [epics, shape, grill]` and the title `Epics: <team>`. Read the Epics, Shape and Grill rows of `.claude/skills/planner/references/MODES.md`. If the vault has no remote or `gh` fails, START says so and the session goes on.

## 2. Read the frontier

Run `python3 .claude/skills/planner/bin/planner render`, then read the `traceability` block on `13-epics/13-epics.md`. Its rows are the work: capabilities nobody delivers (T1), new or changed contracts with no provider epic (T2), concern cells with work and no marked criterion (T4), and epics that deliver nothing (T6). Work one team at a time. A team is an `owner:` handle on app pages.

## 3. Shape the cuts

For the team's gaps, offer 2 or 3 ways to cut them into epics. Each epic has exactly one owning team. Say what each cut makes easy and what it makes hard, such as which cutover it unblocks first. Say which one you prefer. Capture the user's choice, and each rejected cut with its reason. Shape never decides, so the chosen cut stays `draft`.

## 4. Draft each epic

Write `13-epics/EPC-nnn-<slug>.md` with the next free number, at `state: draft`. Grep the vault for the existing EPC numbers, and also read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'` (`git show <branch>:sessions/<id>.md`), because another open session may already hold the next number. Add one to the highest in use. Add a `## Changes` row to the session record: `| EPC-nnn | - | draft | [[<session id>#^cNN]] |`, citing the capture of the chosen cut. A new ID with no row there is an invented ID.

- Frontmatter: `id`, `type: epic`, `title`, `state: draft`, `owner` (the owning team's handle), `authored: mixed`, `apps`, `delivers`, `consumes`, `flows` and `depends_on`, per `CONVENTIONS.md`. Lists hold IDs. `delivers` is never empty: an epic that delivers nothing fails T6.
- `**Owning team:**` in the description, written now, in this session. Close does not write it.
- `## Epic acceptance criteria`: 4 to 7 numbered criteria. Each describes behaviour a tester can see at a contract or a flow boundary. Name the contract or flow by ID. Never name a component, a table, a technology or a container's internals. Every criterion sits at the boundary.
- End each criterion that does a concern cell's work with the concern's marker, such as `[testing]` or `[security] [data]`. Every `addressed` cell for the epic's apps needs one marked criterion on an epic whose `apps` lists the app, or a waiver in the cell. Markers go on numbered criteria. A bulleted criterion carries none.
- `## Traces to` holding an empty `traces-to` block, `## Depends on` with one reason per dependency, `## Rollout notes` and `## Out of scope`.

Before you propose a criterion, run the boundary test on it:

1. It cites at least one contract (`CON-`) or flow (`FLO-`) ID.
2. It names none of the app's containers, components or data stores from its building-blocks page.
3. It names no technology or product from the tech or ADR pages, and none of the generic words database, table, queue, Redis or Kafka.

If it fails, rewrite it at the boundary and show the rewrite beside the original. Do not offer the failing version.

Write no description paragraph yet. Prose is drafted at close, through `house-voice`. Until then the page holds the bullets, the criteria and the sections above.

## 5. Behaviour the vault does not hold

If a criterion needs behaviour no page records, stop on that criterion. Say which capability it belongs to, and offer to run requirements-grill on that `CAP-NNN`. Add `requirements` to the session's `modes` if the user says yes. The requirement is written once, on the capability, at most `assumption`, and the criterion cites it. Never write the requirement into the epic. If the user declines, leave the criterion out and list it under the epic's `## Out of scope` as waiting on that `CAP-NNN`.

## 6. Grill the criteria

For each epic the user wants decided, run the gate in `.claude/skills/planner/skills/grill/SKILL.md` section 2. For an epic, GATE-1 reads each of the epic's apps, GATE-2 reads `draft` or `reopened` with the chosen cut and the rejected cuts written down, and GATE-5 asks for the solution lead. Show the table, and write the `## Agenda` section into the session record, one line per epic, as grill does. START's resume rule reads it. A failed gate gets grill's choice too: "decide anyway (override GATE-n)", with the `**Override:**` and `**Decided by:**` bullets grill writes.

Then take each criterion in turn. Every criterion needs its own explicit yes before the epic can be confirmed:

- Show the criterion and ask whether it is right. Give your recommended wording and a one-line reason, in the form *Recommended: <wording>. <reason>.* Wait.
- Capture the answer. The lead's own words take their name as origin. An accepted recommendation has origin `claude, from <name>`.
- Silence, "ok", "next" or "sure" with nothing else do not count. Ask for an explicit yes or for another wording. Keep your recommendation under pushback without a reason.
- Never answer your own question.

Set an epic to `decided` only when the solution lead confirms it in this session, and only after the lead has given an explicit yes to each criterion on its own. A yes to the epic as a whole does not stand in for them. When every criterion has its yes, read the final set back and get an explicit yes to that read-back. A criterion with no yes of its own keeps the epic at `draft`. Then, as grill does:

- set `state: decided`;
- add `- **Decision:** [[<session id>]]` and a `## Changes` row `| EPC-nnn | draft | decided | [[<session id>#^cNN]] |`, or `| EPC-nnn | reopened | decided | [[<session id>#^cNN]] |` for an epic a challenge's answer reopened;
- mark the deciding capture `→ keep: [[<page>#<heading>|EPC-nnn]] (decided)`;
- commit with the message `grill: EPC-nnn decided`, staging the session record and the epic by exact path.

Render (steps 2 and 7) rewrites generated blocks on other pages too. Stage every file `planner render` reported by exact path in the next commit, so no rewritten block is left out of the PR.

If the lead never confirms, the epic stays `draft`, and its agenda line says `status open`.

If the user tells you to decide an epic without a yes per criterion, or without the read-back, say once that each yes is what makes a criterion something a tester can hold the team to. Then do it, and write `- **Override:** GATE-3 by @<handle> on <today>: <reason>` at page level, beside the `**Decision:**` line. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet an epic already carries when you edit it.

## 7. Check the gate

Run `python3 .claude/skills/planner/bin/planner render` and stage every file it reports, by exact path. Then run `python3 .claude/skills/planner/bin/planner check --gate epics`. Read every `E50x` line for the team's apps. Never say an app's epics are complete while one remains. Show the remaining lines and say what each needs. Read every `E805` line too: each is a high-severity question the catalogue owes that nobody has disposed, or that was asked and still waits for its answer, such as the lawful basis for data, a partner's clauses or a stored-value liability. E805 covers the whole vault, not one team. Offer the user three choices for each:

- Answer it now. Run `python3 .claude/skills/planner/bin/planner questions --open --digest`, take the line, and capture the answer. The gate clears once close writes its row. Before close, the override is the only way to a clean `--gate epics`.
- Override it. Write `- **Override:** E805 by @<handle> on <today>: <reason>` at page level under `## Question ledger` on `11-unknowns-and-risks.md`. It turns E805 into W805, which still prints.
- Leave the gate failing.

Never call the epics complete past an E805 the user has neither taken nor overridden.

Exit 0 means the epics are structurally complete. It does not mean they are decided. Handoff needs every epic `decided` and a clean gate, so list each epic still at `draft` before you finish. The gate checks the whole vault, so `E50x` lines on other teams' apps also fail the exit code. Report those separately as other teams' work, and do not treat them as this team's gap.

## Ends when

Every chosen team's gaps are closed or listed, or the user stops. Epics left at `draft` are listed. Tell the user: "Run `/planner:close` to finish the session and open the PR."

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded.

- Never set `decided` without the lead's confirmation in this session, or while any criterion lacks its own explicit yes, unless the user overrides `GATE-3` and the bullet is written.
- Never read exit 0 from the gate as `decided`.
- Never put one epic under two owning teams.
- Never name a component, table or technology in a criterion.
- Never edit a generated block. Render fills `traces-to`, `epics-for-app`, `delivered-by` and `traceability`.
