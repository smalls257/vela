---
name: breakdown
description: Break a finished app design into stories and tasks a team can build in order, from the vault the team works in. Every story quotes its acceptance criteria word for word from the vault, names the design components that deliver it, and says whether it fits before the next release date. The first story is the team's piece of the initiative's tracer flow. Use after the app's design is complete or complete-with-gaps, when someone says "break down the work", "stories and tasks" or "plan the build". Writes docs/plan/<slug>-breakdown.md.
argument-hint: "<app slug or APP-id>"
disable-model-invocation: true
---

# Breakdown

Turn a finished design into stories and tasks, and show that nothing was left out. The plan is the team's file: the explorer's Build plan draws it, and `/planner:tickets` turns it into tickets, so the format in `${CLAUDE_PLUGIN_ROOT}/skills/breakdown/PLAN-FORMAT.md` is exact and read by code. Read that file before the first story.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). The vault is the folder this runs in. The design, the plan and the tickets sit in its `docs/` folder, beside the pages they trace to.

## 1. Start

Read `${CLAUDE_PLUGIN_ROOT}/references/START.md` for "Plain names and a page a person can hold" and "The user may override any rule", then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, and `voice/VOICE.md` in the vault when it exists (the person's own rules sit above the defaults). The plan's prose follows `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md`, which is read by path because it is not invoked as a command. Acceptance criteria are never restyled.

A team session writes no session record. Work on the branch `design/<slug>` (create it if it does not exist), commit after each agreed story, and say so. The plan is reviewed like the design. If the team has no review rule, say you are committing to a branch and let the person decide.

Check the prerequisites:

1. `docs/tech-design/<slug>.md` exists with `status: complete` or `complete-with-gaps`. If not, say in one sentence what is missing and offer `/planner:design`; stop there. A plan on an unfinished design is a plan for work that will change.
2. `docs/plan/<slug>-breakdown.md` may already exist. Read back its summary table, ask whether to continue it or start again, and say what you did not re-check. Stories already agreed stay as they are.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner handoff verify <APP-id>` as `${CLAUDE_PLUGIN_ROOT}/references/TECH-DESIGN-FROM-VAULT.md` says. If the vault changed since the design, name what changed before the plan leans on it.

## 2. Read what the plan stands on

Read in this order, and when a fact is missing look in this order before asking the person: this conversation, then the docs, then the code.

- The design (`gaps` and `deferred` in its frontmatter, its Trace table, components, open questions) and its ADRs.
- The app's page in the vault: its `## Requirements allocated` rows, the contracts it provides and consumes, and each epic that lists the app, with every acceptance criterion.
- `slices/`: one page per slice, the unit of done. SLC-001 is the tracer; each names its flows, what it comes after and the joins it crosses. `planner handoff` lists the slices this app takes part in.
- `04b-releases.md`: the release dates and what each delivers, and the slices each points at. In a vault with no slice pages, its first release section may name the initiative's tracer flow (`- **Tracer:**`).
- `CONTEXT.md`, and the codebase if it exists, so tasks name real modules.

Build the coverage table before proposing a cut: every allocated requirement, contract, epic criterion and design component, with the stories that will cover it. An empty cell is work left out.

Plan only around people the design or the vault names. The design says who owns the spike, how many engineers there are; a person who appears for the first time in the conversation is asked about ("You mentioned someone for the Mac build. Who is that, and are they on this team?") before any task is assigned to them or any capacity counts them.

## 3. Find the tracer

The first release is a thin flow end to end through every app. This team's first story is its piece of that flow, with the other teams' sides stubbed, so the first thing built is something the whole initiative can see working. Later stories are vertical slices: each one delivers behaviour someone can watch.

Read the tracer from its slice page, the one slice with no `**After:**` (usually `slices/SLC-001-*.md`): its `**Flows:**` and its `## Not in this slice`. A vault with no slice pages names it in the first release section of `04b-releases.md`: a `- **Tracer:**` bullet linking one or more flows, then optionally the thin version in plain words, and an optional `- **Not in the tracer:**` bullet saying what is left out and why.

Group the work by slice: the tracer's stories first, then each later slice this app takes part in, in the order the slices come. Each story names its slice on its `Slice:` line after its shape, `Slice: vertical, SLC-002 The digest reaches a pilot user`; a story that serves no slice says nothing more. The word before the ID is the story's shape, not a kind of slice: a slice is always a page in `slices/`. A story naming SLC-001 is a tracer story. Mark this team's tracer story with the fact bullet `- **Tracer:** yes` under its `### S-nn` heading. If the vault names no tracer, ask one question with your recommendation: "Release one has seven flows. I'd take the one that proves the most with the least: switching on and then one digest. Does that match what the release is meant to show?" Record the answer as the plan's tracer. The person may say a piece isn't ready; carry on, and put it in the plan under what the tracer leaves out, with their reason. No override is needed.

A story that is a layer (a gate, a schema, a screen with nothing behind it) is flagged with `Slice: layer` and folded into the slice that needs it. If the person keeps it apart, the plan says why in their words.

## 4. Propose the cut, then walk it

Group the work into stories. Read the list back as a short list in words: each story's name, one sentence on what a person can see when it is done, and what it waits on. No IDs, no trace lines; those are in the file. About four stories at a time. For a low-risk story, "I'll take these four as proposed unless you want to look at one" saves the person a turn.

Then, for each agreed story, one question at a time with your recommendation and a one-line reason. Settle:

- **Acceptance criteria.** Quote them word for word from the epic criterion or requirement the story traces to, one bullet each, and put every ID on the `Traces to:` line. A criterion that comes from the design or the team (a target, a failure rule) is written as the design states it. Quoting keeps the plan testable without a trip to the vault; the vault commit in the design's frontmatter shows when the words were taken, and `/planner:tickets` checks them again. A criterion the vault does not hold is never made up: it goes to the design as a question.
- **Done when**: one plain sentence a tester could say aloud.
- **Tasks**, each sized `S` (up to about 2 days), `M` (3 to 5 days) or `L` (1 to 2 weeks) for one engineer. A task over `L` is split. Sizes are for ordering.
- **What it waits on**: another story, a design question or deferral, an outside party. `Blocked by:` starts with `none` when nothing blocks it; any note after that is kept.
- **Whether it fits before the next release date** in `04b-releases.md`: do the rough sum only from capacity the design or the person states, say it is rough and from their numbers, and write "cannot tell" with the missing number when one is missing.

When a story's tasks come out vague, probe with a concrete edge case rather than the happy path: "A customer cancels an order with three line items, one already shipped. Which task handles the shipped line, which the refund, and which the order's status?" If no task owns an answer, the story is missing one. If the person answers in generalities, restate the scenario more concretely until the answer is unambiguous.

Write the story into the plan as soon as it is agreed, and commit. Stories deferred, held or split keep every field a built story has; a deferred one carries `Status: deferred` and a reason, a split one is `S-07a` and `S-07b` with their own traces, criteria, tasks and blockers. A story merged into another keeps its ID with `Status: merged into S-nn`; IDs are never renumbered or reused.

Never split, merge, drop or reorder agreed stories without reading the change back and getting a yes. Being allowed to edit the plan is not leave to change what was agreed.

## 5. Order

Order puts the tracer stories first, in the order the flow needs them, then the vertical slices by what unblocks the most and what waits on outside answers last or behind a switch. Say in one line why each story sits where it does. Confirm the order with the person. A tracer story that waits on another team's piece names the wait and its stub.

Keep "Ticket waves": which tickets to create now and which to hold because the work may move.

## 6. Close the plan

Check, and fix before saying done:

- Every allocated requirement, contract, epic criterion and component has a story, or a gap entry `PG-nnn` (plan gaps are `PG-`, never the design's `G-`) with who accepted it and why. Every `gaps[]` and `deferred[]` entry of the design is a story or sits under `## Not planned` with its ID.
- Every story has tasks with sizes, a `Blocked by:` line and a `Release fit:` line; every story in the summary table is in the build order, and the reverse. The summary row's size total is a count ("3 M, 2 S").
- Run `planner explore --breakdown APP-x=docs/plan/<slug>-breakdown.md` (or `planner tickets check`) and fix every line it could not read.
- Run the audit in `${CLAUDE_PLUGIN_ROOT}/references/NEG-AUDIT.md` against the plan. In particular Paper Tiger (do the stories add up to what the requirements need, not only to the components?) and Distributed Monolith (can each story ship without waiting on all the others? A tracer story waits for another team's piece by design; its waits are named and stubbed). Tell the person the findings in plain words ("Reading the calendar shows nothing a person can see; I'd merge it into the digest story") and keep the table in `docs/plan/<slug>-audit.md`. The plan carries one line: "Audited on <date> against `NEG-AUDIT.md`; the result is in `docs/plan/<slug>-audit.md`."

Set `status: complete`, or `complete-with-gaps` with a `PG-nnn` entry for each target the person chose to leave uncovered or each audit finding they accepted. Then say the next step: `/planner:tickets`, and open the pull request if the team's rule asks for one.

## What stays out of this session

The plan never edits the design, the requirements or the vault pages. A gap goes back as an open question written "what we know / what would unblock / affects", with the vault ID it challenges, and the person raises it with `/planner:challenge`. Dates and people are the team's: the plan gives sizes, a rough fit from stated capacity, and names only people the design or vault names.
