# Tech design from an initiative vault

`/vela:design --app <APP-id>` follows this file, run from the vault root. The user's own `tech-design-grill` skill, patched from `integrations/`, follows it too when given `--vault <path> --app <APP-id>`; for it, `<vault>` below is that path, and for `/vela:design` it is `.`. The vault's pages for the app take the place of `docs/requirements/<slug>.md`. The design keeps its own interview and its own output, all in the vault: `docs/tech-design/<slug>.md`, ADRs under `docs/adr/` and `CONTEXT.md`, and the build plan goes to `docs/plan/<slug>-breakdown.md` beside them. `vela explore` finds them with no flag, and `vela check` does not read `docs/`. Write `vault: {app: <APP-id>}` in the design's frontmatter so the explorer matches it to the app.

## Before the first question

1. Check the prereq: the app's building-blocks page in the vault carries `handed_off:`. If the page or the field is missing, stop and say: "<the app's name> isn't handed off yet, so its pages aren't the team's to design from. Ask the solution lead to hand it off first." Record it in the design doc's `prereqs[]` as `path: <vault>/05-building-blocks/<app>-building-blocks.md`, `expected_status: handed_off`.
2. Record the vault commit: run `git -C <vault> fetch origin`, then `git -C <vault> rev-parse --short origin/main` (the commit the team can fetch, not a local one), and `git -C <vault> remote get-url origin`, and record the URL without any `user:token@` part (a token in a clone URL is a credential, and the design is committed). Every link back names this commit.
3. Run `git -C <vault> status --short`. If the vault clone has changes to vault pages, say so: the design would start from pages nobody reviewed. Changes under `docs/` and `CONTEXT.md` are the design's own files and do not count, here and at the start of any later `/vela:*` session in this vault.
4. Find the vela program the way `START.md` says under "Where vela runs from": the installed plugin first, then `<vault>/.claude/skills/vela/scripts/vela`. A marketplace install leaves no copy in the vault, so do not assume one. Check that the file exists before you run it. If vela cannot be found, stop and say: "I cannot check whether the pages changed since the senior accepted them. Run `/vela:where` and send me what it prints." A missing program is never "no manifest".
5. Run `python3 <vela> handoff verify <APP-id> --vault <vault>`. Exit 0 means nothing the senior accepted has changed. Exit 1 lists each changed or removed item: tell the senior, and read those items again before the design rests on them. Exit 2 with the message "does not exist" means the vault holds no manifest for the app; say so and go on. Any other exit 2 is a damaged manifest or a failed run: say that the check could not be made, and do not claim the pages are unchanged.
6. If `slug` is not given, propose the app's name without `APP-`, for example `booking`.

## Where the work lands

The design, its ADRs, `CONTEXT.md` and the build plan are the team's files, and they go through the team's review like any other change. Do not commit them to `main` or push to it. Work on a branch named `design/<slug>`, commit after each section, and open a pull request when the design is complete. Step 2 records the vault commit from `origin/main`, so every link back names a commit anyone can fetch. If the team has no review rule, say that you are committing to a branch, and let the senior decide. In a reader copy there is no git: write the files and commit nothing, as `START.md` says.

## What to read, in this order

| Read | Where | It gives |
|---|---|---|
| The app's building-blocks page | `05-building-blocks/<app>-building-blocks.md` | what the app does and does not do, its containers, the contracts it provides |
| The app's runtime page | `06-runtime/apps/<app>-runtime.md` | its part in each flow, how it behaves on failure |
| Contracts it consumes | the `contracts-consumed` block on the app page; follow each link | what it calls and who tests each side |
| Its allocated requirements | the `## Requirements allocated` table on the app page; follow each row's link to the capability's requirement and its acceptance criteria | **the requirements this design answers for**: each row is this app's share of a requirement, and Through names the contracts that carry it |
| Its epics | the `epics-for-app` block on the app page; open each epic | the acceptance criteria the design must meet. Each criterion is written in plain words; the `- Trace:` line under it holds the requirement, contract and flow IDs it rests on |
| Capabilities its epics deliver | the `delivers` list on each epic; open each `CAP-` page | functional requirements, where recorded |
| The tracer and the other slices | `slices/SLC-nnn-*.md`, the tracer (the one slice with no After) first: each slice's `**Flows:**`, `**Done when:**` and `## Not in this slice`, for the slices `vela handoff` lists for the app; open each flow it links, whose steps name the contracts the slice crosses | the thin end-to-end flows the walking skeleton and the later stories serve, what they leave out, and the order they come in |
| Release one, in a vault with no slice pages | the first release section of `04b-releases.md`: its `- **Tracer:**` bullet (flow links, then the thin version in plain words, or `none, <reason>`) and its `- **Not in the tracer:**` bullet; open each flow it links | the thin end-to-end flow the walking skeleton serves, what it leaves out, and its date. No `**Tracer:**` bullet: ask which flow release one should prove end to end |
| Unknowns that block it | `11-unknowns-and-risks.md`: open unknowns whose `**Blocks:**` links the app's pages | questions the design must not settle on its own |
| Its concern cells | the app's row on each `08-concerns/concern-*.md` page | what each concern asks of this app |
| The glossary | `12-glossary.md` | the initiative's terms, which the design uses as they are |
| The voices | `voice/VOICE.md`, when present, and `voice/examples/` | the vault owner's own rules and examples for the conversation and the pages |

## Trace targets

The app's allocated rows are its requirements: they take the place of `FR-XXX` in `docs/requirements/<slug>.md`, which a vault design does not need. The trace targets are:

- each row of the app's `## Requirements allocated` table, as `CAP-nnn.FRn@APP-<slug>`;
- each contract the app provides (`CON-nnn` on its page);
- each contract it consumes;
- each acceptance criterion of its epics, as `EPC-nnn.ACn`. In an epic written to the template, `n` is the `AC<n>` on the criterion's Trace line (the numbers may have gaps); in an older epic it is the criterion's number.

An app handed off before allocation existed has no `## Requirements allocated` table. Its requirement targets are then each `CAP-nnn.FRn` of the capabilities its epics deliver, as before; tell the senior the app has no allocation, so the split of each requirement between apps is the design's reading, not the vault's.

Epics come after handoff. If the `epics-for-app` block is empty, or its epics are still `draft`, say so before the design leans on them: the acceptance-criteria targets wait for the solution lead's epics, and the design can start from the allocated rows and the contracts.

Every trace target maps to at least one component. Reject the design if one has no owner, as the skill does for an FR. The walking skeleton decides which targets are designed first, never which are left out.

## Running out of room

If the session is cut off or the senior stops before the design is complete, leave it at `status: in-progress` and say in one line what is written, which sections remain and roughly how many questions are left ("Components and data model are written; interfaces and the failure cases remain, about six questions"). Say that the build plan (`/vela:breakdown`, or the user's work-breakdown skill) will not start until the design is `complete` or `complete-with-gaps`. On resume, say in one line where you stopped and carry on from the first unfinished section.

## Linking back

Cite vault items by ID and commit, for example `INI-002 CON-001 @ 3f9c2a1`, or as a link to the vault repository at that commit: `<origin URL>/blob/<sha>/<path>`. Never copy vault text into the design doc. A reader follows the link. Where the design's reasoning rests on the vault's exact words, as an open question's scenario often does, quote the few words in quotation marks beside their ID, unchanged.

## When the vault is wrong or silent

The design never edits the vault. That means vault pages; its own files under `docs/` and `CONTEXT.md` are the design's to write. A functional gap, or a vault answer the senior disputes, becomes an `OQ-XXX` in the design doc with `challenges: <vault ID>` (written `**Challenges:**` in the doc) and the scenario that shows the problem. Tell the senior to raise it in the vault with `/vela:challenge <vault ID>`. That records it as an open unknown the senior owns, and asks the solution lead in a PR. Carry on with the branches it does not touch. Never log a challenge as `D-XXX`: that type means the answer is known.
