---
name: breakdown
description: "Break a finished app design into stories and tasks, tracer first, written to docs/plan/. Offer it when someone asks how to build an app or what to build first; start it only on a yes."
argument-hint: "<app slug or APP-id>"
---

# Breakdown

Turn a finished design into stories and tasks, and show that nothing was left out. The dashboard and `/vela:tickets` read the plan by code, so write it exactly as `${CLAUDE_PLUGIN_ROOT}/skills/breakdown/PLAN-FORMAT.md` says; read that file before the first story. Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from"). The vault is the folder this runs in, and the plan sits in its `docs/` folder.

## 1. Start

Before your first question, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`; write the plan's prose through `house-voice` (`${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md`, read as a file: only a person can start it). Acceptance criteria are never restyled. From `${CLAUDE_PLUGIN_ROOT}/references/START.md` follow "Plain names and a page a person can hold", "Relaying a command" and "The user may override any rule". When the terms slice or tracer first come up, define each once from `vela terms <word>`.

Then run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela freshness --for-lead`. If it exits 3, this copy is behind the shared plan, and every check below would read old pages: say what it printed in your words and offer to bring it up to date (`git switch main`, then `git pull --ff-only`) before you go on. If it fails, say in one plain sentence that you couldn't check, then go on.

A team session writes no session. Work on the branch `design/<slug>` (create it if it doesn't exist), commit after each agreed story with `vela team commit --about "<the story>"`, and say so. The plan is reviewed like the design. If the team has no review rule, say you are committing to a branch and let the team lead decide.

Check the prerequisites:

1. `docs/tech-design/<slug>.md` exists with `status: complete` or `complete-with-gaps`. If not, say in one sentence what is missing and offer `/vela:design`; stop there. A plan on an unfinished design is a plan for work that will change.
2. `docs/plan/<slug>-breakdown.md` may already exist. Read back its summary in words, ask whether to continue it or start again, and say what you didn't re-check. Stories already agreed stay as they are.
3. Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela handoff verify <APP-id> --for-lead` as `${CLAUDE_PLUGIN_ROOT}/references/TECH-DESIGN-FROM-VAULT.md` says. If the vault changed since the design, name what changed, by name, before the plan leans on it.
4. Read your app's slices' flow check from the handoff rather than running it again: `handoffs/<APP-id>.md`, under `## Flow checks when written`. If the handoff record has no `## Flow checks when written` section, run `vela check-slice <slice> --for-lead` once. If a slice is 'not fully checked' or has open findings, tell the team lead before you design against it.

## 2. Read what the plan stands on

Read the design (`gaps` and `deferred` in its frontmatter, its Trace table, components, open questions) and its ADRs; then the app's vault pages, in the order `TECH-DESIGN-FROM-VAULT.md` gives under "What to read" (allocated rows, contracts, epic criteria, slices, `04b-releases.md`); then `CONTEXT.md` and the codebase, so tasks name real modules. When a fact is missing, look in this order before asking: this conversation, then the docs, then the code.

Build the coverage table before proposing a cut: every allocated requirement, contract, epic criterion and design component, with the stories that will cover it. An empty cell is work left out.

Plan only around people the design or the vault names. A person who appears for the first time in the conversation is asked about ("You mentioned someone for the Mac build. Who is that, and are they on this team?") before any task is assigned to them or any capacity counts them.

## 3. Find the tracer

The tracer runs end to end through every app. This team's first story is its piece of that flow, with the other teams' sides stubbed, so the first thing built is something the whole initiative can see working. Later stories are vertical slices: each one delivers behavior someone can watch.

Read it from its slice page, the one with no `**After:**` (usually `slices/SLC-001-*.md`): its `**Flows:**` and `## Not in this slice`. A vault with no slice pages names it on release one in `04b-releases.md`, as a `- **Tracer:**` bullet linking its flows, with an optional `- **Not in the tracer:**`.

Group the work by slice, the tracer's stories first, then each later slice in order. Each story names its slice on its `Slice:` line after its shape, `Slice: vertical, SLC-002 The digest reaches a pilot user`. Mark this team's tracer story with the fact bullet `- **Tracer:** yes` under its `### S-nn` heading. If the vault names no tracer, ask one question with your recommendation: "Release one has seven flows. I'd take the one that proves the most with the least: switching on and then one digest. Does that match what the release is meant to show?" Record the answer as the plan's tracer. If the team lead says a piece isn't ready, carry on and put it under what the tracer leaves out, with their reason. No override is needed.

A story that is a layer (a gate, a schema, a screen with nothing behind it) is flagged with `Slice: layer` and folded into the slice that needs it. If the team lead keeps it apart, the plan says why in their words.

## 4. Propose the cut, then walk it

Read the proposed stories back in words, about four at a time: each one's name, what a person can see when it's done, and what it waits on. No IDs, no trace lines; those are in the file. For low-risk stories, "I'll take these four as proposed unless you want to look at one" saves a turn.

Then, for each agreed story, one question at a time with your recommendation and a one-line reason. Settle:

- **Acceptance criteria.** Quote them word for word from the epic criterion or requirement the story traces to, one bullet each, and put every ID on the `Traces to:` line. A criterion from the design or the team (a target, a failure rule) is written as the design states it. `vela tickets check` checks the quotes again. A criterion the vault doesn't hold is never made up: it goes to the design as a question.
- **Done when**: one plain sentence a tester could say aloud.
- **Tasks**, each sized `S` (up to about 2 days), `M` (3 to 5 days) or `L` (1 to 2 weeks) for one engineer. A task over `L` is split. Sizes are for ordering.
- **What it waits on**: another story, a design question or deferral, an outside party. `Blocked by:` starts with `none` when nothing blocks it.
- **Whether it fits before the next release date** in `04b-releases.md`: do the rough sum only from capacity the design or the team lead states, say it's rough and from their numbers, and write "cannot tell" with the missing number when one is missing.

When a story's tasks come out vague, probe with a concrete edge case rather than the happy path: "A customer cancels an order with three line items, one already shipped. Which task handles the shipped line, which the refund, and which the order's status?" If no task owns an answer, the story is missing one. If the answer comes back general, restate the scenario more concretely until it isn't.

Write each story into the plan as soon as it's agreed, and commit it with `vela team commit`. Stories deferred, held or split keep every field a built story has (`PLAN-FORMAT.md` gives their `Status:` lines); IDs are never renumbered or reused.

Never split, merge, drop or reorder agreed stories without reading the change back and getting a yes. Being allowed to edit the plan is not leave to change what was agreed.

## 5. Order

Put the tracer stories first, in the order the flow needs them, then the vertical slices by what unblocks the most, and what waits on outside answers last or behind a switch. Say in one line why each sits where it does, and confirm the order.

Keep "Ticket waves": which tickets to create now and which to hold because the work may move.

## 6. Close the plan

1. Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela tickets check --vault .`. It finds a target no story covers, a missing field, a story the build order leaves out, and every line it couldn't read. Fix each with the team lead, or record it as a plan gap (`PG-nnn`, never the design's `G-`) with who accepted it and why. Every `gaps[]` and `deferred[]` entry of the design is a story or sits under `## Not planned`.
2. Start a subagent with `${CLAUDE_PLUGIN_ROOT}/references/NEG-AUDIT.md` and the plan, and have it run that self-check against the plan. Two questions matter most: do the stories add up to what the requirements need, not only to the components? Can each story ship without waiting on all the others? A tracer story waits for another team's piece by design; its waits are named and stubbed.
3. Tell the team lead the findings in plain words ("Reading the calendar shows nothing a person can see; I'd merge it into the digest story"), about four at a time, each with what you'd do. Write the result in `docs/plan/<slug>-audit.md` as plain checks, "Every requirement has a story: passes, except transcripts (deferred).", with the checklist's own names kept to the checklist. The plan carries one line: "Checked against the design self-check on October 12; see the audit file beside this plan."

Set `status: complete`, or `complete-with-gaps` with a `PG-nnn` entry for each target the team lead chose to leave uncovered or each audit finding they accepted. Then say the next step: `/vela:tickets`, and open the pull request if the team's rule asks for one.

When a command can't do what the team lead wants, say so and stop.

## What stays out of this session

The plan never edits the design, the requirements or the vault pages. A gap goes back as an open question written "what we know / what would unblock / affects", with the vault ID it challenges, and the team lead raises it with `/vela:challenge`.
