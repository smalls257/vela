---
name: epics
description: "Cut one team's handed-off work into epics with acceptance criteria, then grill each with the solution lead. Offer it when a team asks what to build from its handoff; start it only on a yes."
argument-hint: "<team handle or APP-id, or 'every team'>"
---

# Epics

Turn the app's handoff list into epics a team can build from: not decided yet, until the solution lead settles it, in this session's grill part or whenever sure. The cuts, the criteria's wording, the read-backs and the questions are yours; the commands file them.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with modes `epics`, `shape` and `grill` and the team as the topic, and read those three rows of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The epic page is `vela conventions "Epics and traceability"`.

**Say names, not IDs,** in your own sentences as well as relayed ones. Not "EPC-002 has AC1 to AC5 on CON-001; AC6 waits on UNK-026", but "The chosen-folder epic has five checks on the calendar entries; the sixth waits on whether the entry carries the organization."

## 1. Read the frontier

Run `vela epics frontier --team <@team> --for-lead` and relay it (`--json` holds the gaps). Work one team at a time. Say how many epics and criteria there are and how far you expect to get, and again at about two thirds.

## 2. Shape the cuts

Read `04b-releases.md` first, if there is one. Say which release each proposed epic serves; for a requirement dated in part, whether the epic carries all its criteria or only the first date's. A requirement on no release is cut as usual and flagged as undated. The frontier says whether the team's first epic is on the first thin path (the tracer, as Releases defines it); if it isn't, say what comes first instead: a choice, not a fault.

Offer 2 or 3 ways to cut the gaps into epics, each epic with exactly one owning team. Say what each makes easy and hard (which cutover it unblocks first) and which you prefer. Capture the choice and each rejected cut with its reason. A cut that gives an epic more than about seven criteria is one to split: offer the split, with what each half delivers; keeping it whole is an override.

## 3. Draft each epic

Write the skeleton with `vela add epic --title "<title>" --team <@team> --capture ^cNN --for-lead` (`--help` gives the rest; `--delivers` is never empty), citing the chosen cut's capture. Then add what it leaves to you:

- `depends_on`, with `## Depends on` giving one reason per dependency.
- A tracker link: ask for the item's key or link, or a skip, written as `vela conventions "Links out of the vault"` says. Never make up a key or an address; a skip writes nothing. Offer it for the Library too (`vela library add`), after a yes; `links:` stays as written.
- One-line stubs for the summary and `Still open:`; close drafts them through `house-voice`.
- `## Traces to` holding an empty `traces-to` block, `## Rollout notes` and `## Out of scope`.

**Criteria.** `## Done when` holds 4 to 7 criteria. You write the words; `vela add epic --id <EPC-id> --criterion "<heading>" --says "<sentences>" --trace <ID> --for-lead` files each (`--help` gives the rest).

- The heading is a short plain phrase ("A first call still gets a note"); under it, one or two sentences a tester could read aloud over the phone.
- Each is behavior a tester sees at a contract or flow boundary, named in words ("the calendar entries", "the prep-note flow"). IDs go in `--trace`, requirement first.
- An epic kept whole past seven puts them under group headings of about five.

Run `vela epics lint <EPC-id> --for-lead` before you propose them. For each finding, rewrite the criterion at the boundary and show it beside the original; never offer the failing version.

Draft the paragraph each filed item owes, as `START.md` says under "Draft the paragraph when the item is filed".

## 4. Behavior the plan doesn't hold

Start from the apps' `## Requirements allocated` rows: each row is the team's share of a requirement, and its criteria are that requirement's, as far as the share carries them. Write each as a sentence of its own; never copy the requirement's wording into a table. If a criterion needs behavior no requirement holds, stop on it, say which capability it belongs to, and offer `/vela:requirements` on it, then `/vela:allocate`. Never write the requirement into the epic. If the lead declines, list the criterion under `## Out of scope` as waiting on it.

A question nobody present can answer is an unknown (`MODES.md`, "Unknowns"): `vela add unknown --blocks <EPC-id> --for-lead`.

## 5. Decide the criteria (the grill part)

For each epic the lead wants decided, run `vela check --gate decide --item <EPC-id> --for-lead`. Say which are ready and which aren't, with the one thing that would make each ready, and file the agenda, one line per epic, as grill does. A reopened epic decides the same way. For a failed gate, offer "Decide it anyway (I'll note that the open question was skipped)", filed as an override with the lead's reason.

Read the criteria back in groups of about five, by their words:

- Ask whether they are right, with *Recommended: <wording>. <reason>.* for any you'd change. Wait.
- Capture the answer.
- Only a yes that names a criterion or covers its group counts; ask once more in other words otherwise. Keep your recommendation under pushback without a reason. Never answer your own question.

A group read back, to copy:

> For the calendar epic, a tester will check that a client call gets one note ten minutes before it starts, a call moved late still gets its note as soon as it can be built, a canceled call's note is withdrawn, and the people listed come from the invitation alone. *Recommended:* "within two minutes" instead of "as soon as it can be built", so a tester can time it. Does that set hold?

Set an epic to `decided` only when the solution lead confirms it in this session, after every criterion has a yes, its own or its group's; a yes to the whole epic doesn't stand in. Run `vela decide <EPC-id> --group AC1-AC5 ^cA --yes ^cM --for-lead`, one `--group` per yes (criteria, yes), plus `--why ^cK` when the lead gave a reason. If the lead says decide without the yeses, say once that each yes is what lets a tester hold the team to a criterion, then add `--override GATE-3 --reason-from ^cR`. Never confirmed, the epic stays `draft`.

## 6. Check the gate

Run `vela render` and `vela close stage --checkpoint --for-lead`, then `vela check --gate epics --app <APP-id> --for-lead` for each of the team's apps, and relay each line. Never say an app's epics are complete while one remains; passing means structurally complete, not decided, so list each epic still at `draft`. Other teams' failures are theirs.

When it says a high-priority question keeps the epics from being finished, say it in one sentence: "Nobody has answered who carries the liability for points balances. Answer it now, hand it to someone with a date, or accept the risk." Offer the three routes once, with your recommendation, record the pick and move on:

- **Answer it now:** find it with `vela questions --open --digest` and capture the answer; close writes the ledger row. Before close, the override is the only way to a clean `--gate epics`.
- **Defer it to whoever can answer:** kind `defer`, filed with `vela apply <file> --for-lead`, with the owner the lead names and a date, one yes to both. After a deferral the gate lists the question until close: say so once ("it's with the CFO; the check clears at close").
- **Override it:** kind `override` through `vela apply` on the unknowns page, rule `E805`, with the lead's reason and an end date.

"Leave it failing" with no owner and no override is not a route. Never call the epics complete past an E805 the lead has neither taken nor overridden.

## Ends when

Every chosen team's gaps are closed or listed, or the lead stops; epics at `draft` are listed by name. Close as `START.md` says under "Closing a session".
