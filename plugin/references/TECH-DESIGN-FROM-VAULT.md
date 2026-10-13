# tech-design-grill from an initiative vault

The user's `tech-design-grill` skill reads this file when it is given `--vault <path> --app <APP-id>`. The vault's pages for that app take the place of `docs/requirements/<slug>.md`. The skill keeps its own interview and its own output: `docs/tech-design/<slug>.md`, ADRs and `CONTEXT.md`, all in the vault, because the senior runs the skill from the vault root: `docs/tech-design/<slug>.md`, `docs/adr/` and `CONTEXT.md` there, and `work-breakdown` writes `docs/plan/<slug>-breakdown.md` beside them. `planner explore` finds them with no flag, and `planner check` does not read `docs/`. Use `--vault .`. Write `vault: {app: <APP-id>}` in the design's frontmatter so the explorer matches it to the app.

## Before the first question

1. The prereq is already checked: the app's building-blocks page in the vault carries `handed_off:`. Record it in the design doc's `prereqs[]` as `path: <vault>/05-building-blocks/<app>-building-blocks.md`, `expected_status: handed_off`.
2. Record the vault commit: run `git -C <vault> fetch origin`, then `git -C <vault> rev-parse --short origin/main` (the commit the team can fetch, not a local one), and `git -C <vault> remote get-url origin`, and record the URL without any `user:token@` part (a token in a clone URL is a credential, and the design is committed). Every link back names this commit.
3. Run `git -C <vault> status --short`. If the vault clone has changes to planner pages, say so: the design would start from pages nobody reviewed. Changes under `docs/` and `CONTEXT.md` are the design's own files and do not count, here and at the start of any later `/planner:*` session in this vault.
4. Find the planner program the way `START.md` says under "Where the planner runs from": the installed plugin first, then `<vault>/.claude/skills/planner/scripts/planner`. A marketplace install leaves no copy in the vault, so do not assume one. Check that the file exists before you run it. If no planner can be found, stop and say: "I cannot check whether the pages changed since the senior accepted them. Run `/planner:where` and send me what it prints." A missing program is never "no manifest".
5. Run `python3 <planner> handoff verify <APP-id> --vault <vault>`. Exit 0 means nothing the senior accepted has changed. Exit 1 lists each changed or removed item: tell the senior, and read those items again before the design rests on them. Exit 2 with the message "does not exist" means the vault holds no manifest for the app; say so and go on. Any other exit 2 is a damaged manifest or a failed run: say that the check could not be made, and do not claim the pages are unchanged.
6. If `slug` is not given, propose the app's name without `APP-`, for example `booking`.

## Where the work lands

The design, its ADRs, `CONTEXT.md` and the build plan are the team's files, and they go through the team's review like any other change. Do not commit them to `main` or push to it. Work on a branch named `design/<slug>`, commit after each section, and open a pull request when the design is complete. Step 2 records the vault commit from `origin/main`, so every link back names a commit anyone can fetch. If the team has no review rule, say that you are committing to a branch, and let the senior decide.

## What to read, in this order

| Read | Where | It gives |
|---|---|---|
| The app's building-blocks page | `05-building-blocks/<app>-building-blocks.md` | what the app does and does not do, its containers, the contracts it provides |
| The app's runtime page | `06-runtime/apps/<app>-runtime.md` | its part in each flow, how it behaves on failure |
| Contracts it consumes | the `contracts-consumed` block on the app page; follow each link | what it calls and who tests each side |
| Its allocated requirements | the `## Requirements allocated` table on the app page; follow each row's link to the capability's requirement and its acceptance criteria | **the requirements this design answers for**: each row is this app's share of a requirement, and Through names the contracts that carry it |
| Its epics | the `epics-for-app` block on the app page; open each epic | the acceptance criteria the design must meet. Each criterion is written in plain words; the `- Trace:` line under it holds the requirement, contract and flow IDs it rests on |
| Capabilities its epics deliver | the `delivers` list on each epic; open each `CAP-` page | functional requirements, where recorded |
| Unknowns that block it | `11-unknowns-and-risks.md`: open unknowns whose `**Blocks:**` links the app's pages | questions the design must not settle on its own |
| Its concern cells | the app's row on each `08-concerns/concern-*.md` page | what each concern asks of this app |

## Trace targets

The app's allocated rows are its requirements: they take the place of `FR-XXX` in `docs/requirements/<slug>.md`, which a vault design does not need. The trace targets are:

- each row of the app's `## Requirements allocated` table, as `CAP-nnn.FRn@APP-<slug>`;
- each contract the app provides (`CON-nnn` on its page);
- each contract it consumes;
- each acceptance criterion of its epics, as `EPC-nnn.ACn`. In an epic written to the template, `n` is the `AC<n>` on the criterion's Trace line (the numbers may have gaps); in an older epic it is the criterion's number.

An app handed off before allocation existed has no `## Requirements allocated` table. Its requirement targets are then each `CAP-nnn.FRn` of the capabilities its epics deliver, as before; tell the senior the app has no allocation, so the split of each requirement between apps is the design's reading, not the vault's.

Epics come after handoff. If the `epics-for-app` block is empty, or its epics are still `draft`, say so before the design leans on them: the acceptance-criteria targets wait for the solution lead's epics, and the design can start from the allocated rows and the contracts.

Every trace target maps to at least one component. Reject the design if one has no owner, as the skill does for an FR.

## Running out of room

If the session is cut off or the senior stops before the design is complete, leave it at `status: in-progress` and say in one line what is written, which sections remain and roughly how many questions are left ("Components and data model are written; interfaces and the failure cases remain, about six questions"). Say that `work-breakdown` will not start until the design is `complete` or `complete-with-gaps`. On resume, say in one line where you stopped and carry on from the first unfinished section.

## Linking back

Cite vault items by ID and commit, for example `INI-002 CON-001 @ 3f9c2a1`, or as a link to the vault repository at that commit: `<origin URL>/blob/<sha>/<path>`. Never copy vault text into the design doc. A reader follows the link.

## When the vault is wrong or silent

The design never edits the vault. That means the planner pages; its own files under `docs/` and `CONTEXT.md` are the design's to write. A functional gap, or a vault answer the senior disputes, becomes an `OQ-XXX` in the design doc with `challenges: <vault ID>` and the scenario that shows the problem. Tell the senior to raise it in the vault with `/planner:challenge <vault ID>`. That records it as an open unknown the senior owns, and asks the solution lead in a PR. Carry on with the branches it does not touch. Never log a challenge as `D-XXX`: that type means the answer is known.
