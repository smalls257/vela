# tech-design-grill from an initiative vault

The user's `tech-design-grill` skill reads this file when it is given `--vault <path> --app <APP-id>`. The vault's pages for that app take the place of `docs/requirements/<slug>.md`. The skill keeps its own interview and its own output: `docs/tech-design/<slug>.md`, ADRs and `CONTEXT.md`, all in the team's repository.

## Before the first question

1. The prereq is already checked: the app's building-blocks page in the vault carries `handed_off:`. Record it in the design doc's `prereqs[]` as `path: <vault>/05-building-blocks/<app>-building-blocks.md`, `expected_status: handed_off`.
2. Record the vault commit: run `git -C <vault> rev-parse --short HEAD` and `git -C <vault> remote get-url origin`. Every link back names this commit.
3. Run `git -C <vault> status --short`. If the vault clone has changes, say so: the design would start from pages nobody reviewed.
4. Run `python3 <vault>/.claude/skills/planner/bin/planner handoff verify <APP-id> --vault <vault>`. Exit 0 means nothing the senior accepted has changed. Exit 1 lists each changed or removed item: tell the senior, and read those items again before the design rests on them. Exit 2 means the vault holds no manifest for the app; say so and go on.
5. If `slug` is not given, propose the app's name without `APP-`, for example `booking`.

## What to read, in this order

| Read | Where | It gives |
|---|---|---|
| The app's building-blocks page | `05-building-blocks/<app>-building-blocks.md` | what the app does and does not do, its containers, the contracts it provides |
| The app's runtime page | `06-runtime/apps/<app>-runtime.md` | its part in each flow, how it behaves on failure |
| Contracts it consumes | the `contracts-consumed` block on the app page; follow each link | what it calls and who tests each side |
| Its allocated requirements | the `## Requirements allocated` table on the app page; follow each row's link to the capability's requirement and its acceptance criteria | **the requirements this design answers for**: each row is this app's share of a requirement, and Through names the contracts that carry it |
| Its epics | the `epics-for-app` block on the app page; open each epic | the acceptance criteria the design must meet |
| Capabilities its epics deliver | the `delivers` list on each epic; open each `CAP-` page | functional requirements, where recorded |
| Unknowns that block it | `11-unknowns-and-risks.md`: open unknowns whose `**Blocks:**` links the app's pages | questions the design must not settle on its own |
| Its concern cells | the app's row on each `08-concerns/concern-*.md` page | what each concern asks of this app |

## Trace targets

The app's allocated rows are its requirements: they take the place of `FR-XXX` in `docs/requirements/<slug>.md`, which a vault design does not need. The trace targets are:

- each row of the app's `## Requirements allocated` table, as `CAP-nnn.FRn@APP-<slug>`;
- each contract the app provides (`CON-nnn` on its page);
- each contract it consumes;
- each acceptance criterion of its epics, as `EPC-nnn.ACn`.

Every trace target maps to at least one component. Reject the design if one has no owner, as the skill does for an FR.

## Linking back

Cite vault items by ID and commit, for example `INI-002 CON-001 @ 3f9c2a1`, or as a link to the vault repository at that commit: `<origin URL>/blob/<sha>/<path>`. Never copy vault text into the design doc. A reader follows the link.

## When the vault is wrong or silent

The design never edits the vault. A functional gap, or a vault answer the senior disputes, becomes an `OQ-XXX` in the design doc with `challenges: <vault ID>` and the scenario that shows the problem. Tell the senior to raise it in the vault with `/planner:challenge <vault ID>`. That records it as an open unknown the senior owns, and asks the solution lead in a PR. Carry on with the branches it does not touch. Never log a challenge as `D-XXX`: that type means the answer is known.
