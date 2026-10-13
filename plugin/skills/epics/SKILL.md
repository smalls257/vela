---
name: epics
description: Epics session for an initiative vault at stage 6. Works team by team from the traceability gaps, shapes 2 or 3 epic cuts, drafts boundary acceptance criteria with concern markers, grills the solution lead one criterion at a time, and runs check --gate epics --app before calling an app's epics complete.
argument-hint: "<team handle or APP-id, or 'every team'>"
disable-model-invocation: true
---

# Epics

Turn a handed-off slice into epics a team can build from. The check finds the gaps, so the frontier is never guessed. Only the Grill part of this session sets an epic to `decided`.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). The format, including the epic page and the trace rules, is in `CONVENTIONS.md` under "Epics and traceability".

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with modes `epics`, `shape` and `grill`. The record has `modes: [epics, shape, grill]` and the title `Epics: <team>`. Read the Epics, Shape and Grill rows of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. If the vault has no remote or `gh` fails, START says so and the session goes on.

## 2. Read the frontier

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner render`, then read the `traceability` block on `13-epics/13-epics.md`. Its rows are the work: capabilities nobody delivers (T1), new or changed contracts with no provider epic (T2), concern cells with work and no marked criterion (T4), and epics that deliver nothing (T6). Work one team at a time. A team is an `owner:` handle on app pages.

## 3. Shape the cuts

Read `04b-releases.md` first, if the vault has one. The team's epics are cut against the releases: say which release each proposed epic serves, and when a requirement is dated in part ("AC1 and AC2 in January, AC3 later"), say whether the epic carries all of its criteria or only those on the first date. A requirement on no release is cut as usual and flagged as undated. Say too whether the team's first epic is on the tracer, a thin path through every app that release one builds first: its `flows:` lists a tracer flow from release one's `**Tracer:**` bullet. If it is not, say what comes first instead; it is not a fault.

For the team's gaps, offer 2 or 3 ways to cut them into epics. Each epic has exactly one owning team. Say what each cut makes easy and what it makes hard, such as which cutover it unblocks first. Say which one you prefer. Capture the user's choice, and each rejected cut with its reason. Shape never decides, so the chosen cut stays `draft`. People hold about four to seven things at once, so a cut that would give an epic more than about seven acceptance criteria is a cut to split: propose the split as one of the options, with what each half delivers. The user may keep it whole; record that as an override, as `START.md` says.

## 4. Draft each epic

Write `13-epics/EPC-nnn-<slug>.md` with the number `planner next-id EPC` prints, at `state: draft`. If the command is unavailable, grep the vault for the existing EPC numbers, and also read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'` (`git show <branch>:sessions/<id>.md`), because another open session may already hold the next number. Add one to the highest in use. Add a `## Changes` row to the session record: `| EPC-nnn | - | draft | [[<session id>#^cNN]] |`, citing the capture of the chosen cut. A new ID with no row there is an invented ID.

- Frontmatter: `id`, `type: epic`, `title`, `state: draft`, `owner` (the owning team's handle), `authored: mixed`, `apps`, `delivers`, `consumes`, `flows` and `depends_on`, per `CONVENTIONS.md`. Lists hold IDs. `delivers` is never empty: an epic that delivers nothing fails T6.
- `**Owning team:**` in the description, written now, in this session. Close does not write it.
- Where the work is tracked: ask "Is there a tracker item for this epic? Give me its key or link, or say skip." If `.planner.yaml` has a `link_templates` entry for `Tracker`, write the key, `links: {Tracker: BOOK-12}`; otherwise write the URL the user gave. Never make up a key or an address, and write no `links:` line when they skip.
- The page follows the epic template in `CONVENTIONS.md` under "Epics and traceability", in this order: a two or three sentence summary and a `Still open:` line; `**Owning team:**`; `## Who this is for and what changes`; `## Done when`; then the sections below. The summary is the page's opening, so write it in the house voice at close, as section 4 of `close` says; until then leave a one-line stub.
- `## Done when`: 4 to 7 criteria, each a `###` heading in a short plain phrase ("A first call still gets a note") with one or two sentences under it that a tester could read aloud over the phone, and a Trace line. Each describes behaviour a tester can see at a contract or a flow boundary. Name the contract or flow by its name ("the calendar entries", "the prep-note flow"), never by its ID, and write no "From CAP-001.FR1" in the sentence. The Trace line is the last line under the criterion: `- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC3  ·  [testing]`, which is the IDs it traces to (requirement first), then its stable id `AC<n>`, then its concern markers. Take the next `AC` number nobody has used on this epic: the number is written, never counted, so a later insert or strike renumbers nothing and `EPC-nnn.AC3` always means the same criterion. Never name a component, a table, a technology or a container's internals. Every criterion sits at the boundary. More than 7 means the epic should be split (section 3); if an epic holds more than 7 and the user keeps it whole, group the criteria under `###` group headings of about five and drop each criterion to `####`.
- Put a criterion's concern marker on its Trace line, after the AC id, such as `[testing]` or `[security] [data]`. Every `addressed` cell for the epic's apps needs one marked criterion on an epic whose `apps` lists the app, or a waiver in the cell. An epic written in the first shape (numbered criteria under `## Epic acceptance criteria`, markers ending the sentence) still checks; when this session touches it, rewrite it to the template and keep each criterion's number as its `AC` id.
- `## Traces to` holding an empty `traces-to` block, `## Depends on` with one reason per dependency, `## Rollout notes` and `## Out of scope`.

Before you propose a criterion, run the boundary test on it:

1. Its `- Trace:` line holds at least one contract (`CON-`) or flow (`FLO-`) ID, and its sentences name that contract or flow in plain words.
2. It names none of the app's containers, components or data stores from its building-blocks page.
3. It names no technology or product from the tech or ADR pages, and none of the generic words database, table, queue, Redis or Kafka.

If it fails, rewrite it at the boundary and show the rewrite beside the original. Do not offer the failing version.

Write no summary yet beyond a stub. Prose is drafted at close, through `house-voice`: the summary, the `Still open:` line and `## Who this is for and what changes`. Until then the page holds the headings, the criteria and the sections above.

## 5. Behaviour the vault does not hold

Start each team's criteria from its apps' `## Requirements allocated` rows: each row is a share of a requirement the team owns, and its criteria are the acceptance criteria of that requirement, which stay on the requirement's page, as far as that share carries them. Write each as a read-aloud sentence of its own; never copy the requirement's wording into a table. Put the requirement's ID on the criterion's `- Trace:` line. If a criterion needs behaviour no requirement holds, stop on that criterion. Say which capability it belongs to, and offer `/planner:requirements` on that `CAP-nnn`, then `/planner:allocate`. The requirement is written once, on the capability, at most `assumption`, and the criterion cites it. Never write the requirement into the epic. If the user declines, leave the criterion out and list it under the epic's `## Out of scope` as waiting on that `CAP-nnn`.

A question nobody present can answer becomes an unknown, as `MODES.md` says under "Unknowns". When the owner is not the person who would actually know, ask once: "Who would actually know this? If that is not the owner, give me a name or a role, like outside counsel." Write the answer as `**Ask:** @handle` or `**Ask:** outside counsel`, and leave the line out when the owner holds the answer.

## 6. Grill the criteria

For each epic the user wants decided, run the gate in `${CLAUDE_PLUGIN_ROOT}/skills/grill/SKILL.md` section 2. For an epic, GATE-1 reads each of the epic's apps, GATE-2 reads `draft` or `reopened` with the chosen cut and the rejected cuts written down, and GATE-5 asks for the solution lead. Say in plain words which epics are ready to decide and which are not (never a gate table), and write the `## Agenda` section into the session record, one line per epic, as grill does. START's resume rule reads it. A failed gate gets grill's choice too: "decide anyway (override GATE-n)", with the `**Override:**` and `**Decided by:**` bullets grill writes.

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

If the user tells you to decide an epic without a yes per criterion, or without the read-back, say once that each yes is what makes a criterion something a tester can hold the team to. Then do it, and write `- **Override:** GATE-3 by @<handle> on <today>: <reason>` under the epic page's `## History`, with its `**Decision:**` line. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet an epic already carries when you edit it.

## 7. Check the gate

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner render` and stage every file it reports, by exact path. Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check --gate epics --app <APP-id>` for each of the team's apps. The `--app` run leaves out other teams' gaps, so its exit code is this app's alone. Read every `E50x` line it prints. Never say an app's epics are complete while one remains. Say what each needs in plain words ("nobody is planned to build the sale API yet"), never its code. Read every `E805` line too: each is a high-severity question the catalogue owes that nobody has disposed, or that was asked and still waits for its answer, such as the lawful basis for data, a partner's clauses or a stored-value liability. Put each to the lead as one plain sentence. Dispose of each one in this session, while the lead is here, with one of three routes (answer it, defer it to an owner, or override to accept the risk) as `CONVENTIONS.md` says under "The ledger". Offer them once, with your recommendation, and do not loop: once the lead picks one, record it and move on.

- Answer it now. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --open --digest`, take the line, and capture the answer. The gate clears once close writes its row. Before close, the override is the only way to a clean `--gate epics`.
- Override it. Write `- **Override:** E805 by @<handle> on <today>: <reason>` under the `## History` section at the end of `11-unknowns-and-risks.md`, at page level, as `CONVENTIONS.md` says under "Pages". It turns E805 into W805, which still prints.
- Defer it to whoever can answer. Take the owner from what the lead has said, such as "the CFO's call", and propose the unknown yourself instead of asking again: a new `UNK-nnn` from `planner next-id UNK` on `11-unknowns-and-risks.md`, with `**Owner:**` that handle, `**Ask by:**` a date and `**Blocks:**` the question's ID, and capture it `→ keep` as an unknown. Close writes the ledger row `unknown`, which disposes of the question and gives it someone who chases it. Ask for one yes to the owner and the date.

A gate that still shows E805 after you record a deferral is expected until close writes the row. Say so once and go on; do not re-run it, re-offer the routes, or hold the session open for it. "Leave it failing" with no unknown and no override is not a route: it leaves a high-severity question nobody is chasing, as the heron run showed.

Never call the epics complete past an E805 the user has neither taken nor overridden.

Exit 0 means the app's epics are structurally complete. It does not mean they are decided, so list each epic still at `draft` before you finish. Handoff does not wait for this: epics follow it. To see every team at once, run the gate without `--app`; its failures on other teams' apps are those teams' work, not this team's gap.

## Ends when

Every chosen team's gaps are closed or listed, or the user stops. Epics left at `draft` are listed. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session".

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded.

- Never set `decided` without the lead's confirmation in this session, or while any criterion lacks its own explicit yes, unless the user overrides `GATE-3` and the bullet is written.
- Never read exit 0 from the gate as `decided`.
- Never put one epic under two owning teams.
- Never name a component, table or technology in a criterion, and never write an ID in its sentence or its heading: the name goes in the sentence and the ID on the `- Trace:` line.
- Never edit a generated block. Render fills `traces-to`, `epics-for-app`, `delivered-by` and `traceability`.
