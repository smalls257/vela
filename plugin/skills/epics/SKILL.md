---
name: epics
description: Work team by team from the traceability gaps, cut epics, draft boundary acceptance criteria and grill the solution lead on each. Use at stage 6, before calling an app's epics complete.
argument-hint: "<team handle or APP-id, or 'every team'>"
disable-model-invocation: true
---

# Epics

Contents: 1 start; 2 read the frontier; 3 shape the cuts; 4 draft each epic; 5 behavior the vault does not hold; 6 grill the criteria; 7 check the gate.

Turn a handed-off app into epics a team can build from. The check finds the gaps, so the frontier is never guessed. Only the Grill part of this session sets an epic to `decided`.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The format, including the epic page and the trace rules, is in `vela conventions "Epics and traceability"`.

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with modes `epics`, `shape` and `grill`. The record has `modes: [epics, shape, grill]` and the title `Epics: <team>`. Read the Epics, Shape and Grill rows of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. If the vault has no remote or `gh` fails, START says so and the session goes on.

## 2. Read the frontier

Run `vela epics frontier --team <@team> --for-lead` (a team is an `owner:` handle on app pages) and relay it; `--json` holds the gaps (requirements nobody delivers, contracts with no provider epic, concerns with no marked criterion, epics that deliver nothing). Work one team at a time. Say how many epics and criteria there are and how far you expect to get, and say it again at about two thirds.

## 3. Shape the cuts

Read `04b-releases.md` first, if the plan has one. Say which release each proposed epic serves; when a requirement is dated in part, say whether the epic carries all its criteria or only the first date's. A requirement on no release is cut as usual and flagged as undated. The frontier says whether the team's first epic is on the first thin path (the tracer, as `vela conventions "Releases"` defines it); if it isn't, say what comes first instead. That is a choice, not a fault.

Offer 2 or 3 ways to cut the gaps into epics, each epic with exactly one owning team. Say what each cut makes easy and hard (which cutover it unblocks first) and which you prefer. Capture the choice, and each rejected cut with its reason; the chosen cut stays `draft`. A cut giving an epic more than about seven criteria is a cut to split: offer the split as an option, with what each half delivers. If the lead keeps it whole, record that as an override, as `START.md` says.

## 4. Draft each epic

Write the skeleton with `vela add epic --title "<title>" --team <@team> --apps <APP-id> --delivers <ID> --consumes <CON-id> --flows <FLO-id> --capture ^cNN --for-lead`, repeating a list flag per ID, with the chosen cut's capture. It numbers the epic and writes the frontmatter, the owning team, the template's headings and the `## Changes` row. `delivers` is never empty. Then add what it leaves to you:

- `depends_on`, as `vela conventions "Frontmatter"` says, and `## Depends on` with one reason per dependency.
- A tracker link: ask for the item's key or link, or a skip. With a `link_templates` entry for `Tracker` in `.vela.yaml`, write the key, `links: {Tracker: BOOK-12}`; otherwise the URL given. Never make up a key or an address; a skip writes no `links:` line.
- One-line stubs for the summary and `Still open:`. Close drafts them, and `## Who this is for and what changes`, through `house-voice`.
- `## Traces to` holding an empty `traces-to` block, `## Rollout notes` and `## Out of scope`.

**Criteria.** `## Done when` holds 4 to 7 criteria. You write the words; `vela add epic --id <EPC-id> --criterion "<heading>" --says "<sentences>" --trace <CAP-id.FRn> --trace <CON-id> --concerns testing --capture ^cNN --for-lead` writes the number and the Trace line.

- The heading is a short plain phrase ("A first call still gets a note"); under it, one or two sentences a tester could read aloud over the phone.
- Each is behavior a tester sees at a contract or flow boundary, named in words ("the calendar entries", "the prep-note flow"). IDs go in `--trace`, requirement first.
- `--concerns` marks the Trace line, such as `[testing]`. Every `addressed` concern cell for the epic's apps needs one marked criterion, or a waiver in the cell.
- More than 7 means the epic should be split (section 3). Kept whole, its criteria go under `###` group headings of about five, each criterion at `####`.

Run `vela epics lint <EPC-id> --for-lead` before you propose them. For each finding, rewrite the criterion at the boundary and show it beside the original; never offer the failing version. An epic in the first shape (numbered criteria under `## Epic acceptance criteria`) gets `vela epics lint --fix-shape <EPC-id>` when this session touches it, which keeps each number.

## 5. Behavior the plan doesn't hold

Start from the apps' `## Requirements allocated` rows: each row is the team's share of a requirement, and its criteria are that requirement's, as far as the share carries them. Write each as a sentence of its own; never copy the requirement's wording into a table. If a criterion needs behavior no requirement holds, stop on it, say which capability it belongs to, and offer `/vela:requirements` on that `CAP-nnn`, then `/vela:allocate`. The requirement is written once, on the capability, not decided yet, until a grill decides it. Never write the requirement into the epic. If the lead declines, list the criterion under `## Out of scope` as waiting on it.

A question nobody present can answer is an unknown (`MODES.md`, "Unknowns"): `vela add unknown --name "<name>" --capture ^cNN --owner <@handle> --ask "<who would know>" --blocks <EPC-id> --for-lead`.

## 6. Grill the criteria

For each epic the user wants decided, run the gate in `${CLAUDE_PLUGIN_ROOT}/skills/grill/SKILL.md` section 2. For an epic, GATE-1 reads each of the epic's apps, GATE-2 reads `draft` or `reopened` with the chosen cut and the rejected cuts written down, and GATE-5 asks for the solution lead. Say in plain words which epics are ready to decide and which are not (never a gate table), and write the `## Agenda` section into the session record, one line per epic, as grill does. START's resume rule reads it. A failed gate gets grill's choice too: "decide anyway (override GATE-n)", with the `**Override:**` and `**Decided by:**` bullets grill writes.

Then take the criteria in groups of about five (an epic's usual 4 to 7 are one or two groups), and read each group back:

- Show the criteria and ask whether they are right. Give your recommended wording and a one-line reason for any you would change, in the form *Recommended: <wording>. <reason>.* Wait.
- Capture the answer. The lead's own words take their name as origin. An accepted recommendation has origin `claude, from <name>`.
- Write a criterion only on a yes that names it or covers its group (`START.md` defines a yes). Silence, "ok", "next" or "sure" with nothing else do not count: ask once more in different words, or for another wording. Keep your recommendation under pushback without a reason.
- Never answer your own question.

Set an epic to `decided` only when the solution lead confirms it in this session, and only after every criterion has a yes, its own or its group's. A yes to the epic as a whole does not stand in for them. When every group has its yes, read the final set back and get a yes to that read-back. A criterion with no yes keeps the epic at `draft`. Then, as grill does:

- set `state: decided`;
- add `- **Decision:** [[<session id>]]` and a `## Changes` row `| EPC-nnn | draft | decided | [[<session id>#^cNN]] |`, or `| EPC-nnn | reopened | decided | [[<session id>#^cNN]] |` for an epic a challenge's answer reopened;
- mark the deciding capture `→ keep: [[<page>#<heading>|EPC-nnn]] (decided)`;
- commit with the message `grill: EPC-nnn decided`, staging the session record and the epic by exact path.

Render (steps 2 and 7) rewrites generated blocks on other pages too. Stage every file `vela render` reported by exact path in the next commit, so no rewritten block is left out of the PR.

If the lead never confirms, the epic stays `draft`, and its agenda line says `status open`.

If the user tells you to decide an epic without a yes on its criteria, or without the read-back, say once that each yes is what makes a criterion something a tester can hold the team to. Then do it, and write `- **Override:** GATE-3 by @<handle> on <today>: <reason>` under the epic page's `## History`, with its `**Decision:**` line. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet an epic already carries when you edit it.

## 7. Check the gate

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela render` and stage every file it reports, by exact path. Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela check --gate epics --app <APP-id>` for each of the team's apps. The `--app` run leaves out other teams' gaps, so its exit code is this app's alone. Read every `E50x` line it prints. Never say an app's epics are complete while one remains. Say what each needs in plain words ("nobody is planned to build the sale API yet"), never its code. Read every `E805` line too: each is a high-severity question the catalog owes that nobody has disposed, or that was asked and still waits for its answer, such as the lawful basis for data, a partner's clauses or a stored-value liability. Put each to the lead as one plain sentence. Dispose of each one in this session, while the lead is here, with one of three routes (answer it, defer it to an owner, or override to accept the risk) as `vela conventions "Questions and the ledger"` says. Offer them once, with your recommendation, and do not loop: once the lead picks one, record it and move on.

- Answer it now. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela questions --open --digest`, take the line, and capture the answer. The gate clears once close writes its row. Before close, the override is the only way to a clean `--gate epics`.
- Override it. Write `- **Override:** E805 by @<handle> on <today>: <reason>` under the `## History` section at the end of `11-unknowns-and-risks.md`, at page level, as `vela conventions "Pages"` says. It turns E805 into W805, which still prints.
- Defer it to whoever can answer. Take the owner from what the lead has said, such as "the CFO's call", and propose the unknown yourself instead of asking again: a new `UNK-nnn` from `vela next-id UNK` on `11-unknowns-and-risks.md`, with `**Owner:**` that handle, `**Ask by:**` a date and `**Blocks:**` the question's ID, and capture it `→ keep` as an unknown. Close writes the ledger row `unknown`, which disposes of the question and gives it someone who chases it. Ask for one yes to the owner and the date.

A gate that still shows E805 after you record a deferral is expected until close writes the row. Say so once and go on; do not re-run it, re-offer the routes, or hold the session open for it. "Leave it failing" with no unknown and no override is not a route: it leaves a high-severity question nobody is chasing, as the heron run showed.

Never call the epics complete past an E805 the user has neither taken nor overridden.

Exit 0 means the app's epics are structurally complete. It does not mean they are decided, so list each epic still at `draft` before you finish. Handoff does not wait for this: epics follow it. To see every team at once, run the gate without `--app`; its failures on other teams' apps are those teams' work, not this team's gap.

## Ends when

Every chosen team's gaps are closed or listed, or the user stops. Epics left at `draft` are listed. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session".

## Never

- Never set `decided` without the lead's confirmation in this session, or while any criterion lacks a yes (its own or its group's), unless the user overrides `GATE-3` and the bullet is written.
- Never read exit 0 from the gate as `decided`.
- Never put one epic under two owning teams.
- Never name a component, table or technology in a criterion, and never write an ID in its sentence or its heading: the name goes in the sentence and the ID on the `- Trace:` line.
- Never edit a generated block. Render fills `traces-to`, `epics-for-app`, `delivered-by` and `traceability`.
