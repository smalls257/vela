---
name: epics
description: Cut one team's handed-off work into epics with acceptance criteria at the boundary, then grill each with the solution lead.
argument-hint: "<team handle or APP-id, or 'every team'>"
disable-model-invocation: true
---

# Epics

Contents: 1 start; 2 read the frontier; 3 shape the cuts; 4 draft each epic; 5 behavior the plan doesn't hold; 6 grill the criteria; 7 check the gate.

Turn the app's handoff list into epics a team can build from. Only the grill part of this session (a grill as `vela terms` defines it) sets an epic to `decided`.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The epic page is in `vela conventions "Epics and traceability"`.

The commands do the mechanics: numbering, Trace lines, the boundary test, the gates, the decision writes. Relay their `--for-lead` lines and reason over `--json`. The cuts, the criteria's wording, the read-backs and the questions are yours. When a command can't express what the lead wants, say so and stop; never fall back to doing its steps by hand.

**Say names, not IDs,** in your own sentences as well as relayed ones. An ID appears only where the lead must act on it, such as a tracker key. Not "EPC-002 has AC1 to AC5 on CON-001; AC6 waits on UNK-026", but "The chosen-folder epic has five checks on the calendar entries; the sixth waits on whether the entry carries the organization."

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with modes `epics`, `shape` and `grill`. The record has `modes: [epics, shape, grill]` and the title `Epics: <team>`. Read the Epics, Shape and Grill rows of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. If the plan has no remote or `gh` fails, START says so and the session goes on.

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

For each epic the lead wants decided, run `vela check --gate grill --item <EPC-id> --for-lead`. Say which epics are ready and which aren't, with the one thing that would make each ready (never a gate table), and file the agenda, one line per epic, as grill does (`vela apply`, kind `agenda`). A reopened epic decides the same way. For a failed gate, offer "Decide it anyway (I'll note that the open question was skipped)", filed as an override with the lead's reason.

Then read the criteria back in groups of about five (an epic's usual 4 to 7 are one or two), by their words:

- Ask whether they are right, with *Recommended: <wording>. <reason>.* for any you would change. Wait.
- Capture the answer. The lead's words take their name as origin; an accepted recommendation has origin `claude, from <name>`.
- Only a yes that names a criterion or covers its group counts (`START.md` defines a yes). Silence, "ok", "next" or "sure" alone don't: ask once more in other words. Keep your recommendation under pushback without a reason. Never answer your own question.

A group read back, to copy:

> For the calendar epic, a tester will check that a client call gets one note ten minutes before it starts, a call moved late still gets its note as soon as it can be built, a canceled call's note is withdrawn, and the people listed come from the invitation alone. *Recommended:* "within two minutes" instead of "as soon as it can be built", so a tester can time it. Does that set hold?

Set an epic to `decided` only when the solution lead confirms it in this session, after every criterion has a yes, its own or its group's; a yes to the whole epic doesn't stand in. Read the final set back for one more yes, then run `vela decide <EPC-id> --group AC1-AC5 ^cA ^cB --readback ^cN --yes ^cM --for-lead`, one `--group` per read-back (criteria, read-back, yes), plus `--why ^cK` when the lead gave a reason. It writes the state, the decision lines, the `## Changes` row and the mark, and commits; while a criterion lacks a yes it files nothing and says which. Exit 3 means already decided. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet an epic already carries.

If the lead says decide without the yeses or the read-back, say once that each yes is what lets a tester hold the team to a criterion, then add `--override GATE-3 --reason-from ^cR`. Never confirmed, the epic stays `draft` and its agenda line says `status open`.

## 7. Check the gate

Run `vela render`, which rewrites blocks on other pages too. Stage every file `vela render` reported by exact path. Run `vela check --gate epics --app <APP-id> --for-lead` for each of the team's apps (`--app` leaves out other teams' gaps) and relay each line. Never say an app's epics are complete while one remains.

A line saying a high-priority question keeps the epics from being finished is an `E805`: a question the catalog owes that nobody has disposed, or that was asked and still waits for its answer. The run without `--for-lead` gives its question ID for the decision file. Say it to the lead in one sentence: "Nobody has answered who carries the liability for points balances. Answer it now, hand it to someone with a date, or accept the risk." Offer the three routes once, with your recommendation, then record the pick and move on. A route is a decision file, `.vela/decisions/<session id>/<seq>-<kind>.json` (`vela apply --schema <kind>` prints its fields), filed with `vela apply <file> --for-lead`:

- **Answer it now.** Find it with `vela questions --open --digest` and capture the answer; close writes the ledger row. Before close, the override is the only way to a clean `--gate epics`.
- **Defer it to whoever can answer**, kind `defer`: the owner the lead named ("the CFO's call") and a date, with one yes to both. It opens an unknown with someone to chase it.
- **Override it**, kind `override`, on `unknowns-and-risks`, rule `E805`, with the lead's reason and an end date. It writes `- **Override:** E805 by @<handle> on <today> until <date>: <reason>` under the `## History` section at the end of `11-unknowns-and-risks.md`, and turns E805 into W805, which still prints.

After a deferral the gate lists the question until close: say so once ("it's with the CFO; the check clears at close") and go on. "Leave it failing" with no owner and no override is not a route.

Never call the epics complete past an E805 the lead has neither taken nor overridden.

Exit 0 means structurally complete. It does not mean they are decided, so list each epic still at `draft`. The handoff doesn't wait for this. The gate without `--app` shows every team; other teams' failures are theirs.

## Ends when

Every chosen team's gaps are closed or listed, or the lead stops; epics at `draft` are listed by name. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session".

## Never

- Never name a component, table or technology in a criterion, or an ID in its sentence or heading.
- Never edit a generated block; render fills `traces-to`, `epics-for-app`, `delivered-by` and `traceability`.
