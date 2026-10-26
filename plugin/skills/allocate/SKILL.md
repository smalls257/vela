---
name: allocate
description: "Divide each requirement among the apps and contracts that deliver it, saved as not decided yet. Offer it when someone asks who builds what or how requirements split across apps; start it only on a yes."
argument-hint: "[CAP-nnn, APP-<slug>, or none for the whole initiative]"
---

# Allocate

Make every requirement somebody's. Allocation says, for each requirement, which app carries which part, and which contract carries the part that crosses between them, before anyone cuts epics. Each row is `assumption` (to the lead, "not decided yet") until the lead settles it.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The format is `vela conventions "Requirements and allocation"`. When a command can't express what the lead wants, say so and stop.

## 1. Start

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `allocate`. Read the Allocate row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The first time you say grill to the lead, say what it is in the words `vela terms grill` gives.

If `04a-capability-delta.md` has no `allocation` block add an `## Allocation` section with the empty block markers as `vela conventions "Generated blocks"` shows. Run `vela render` and read the `allocation` block on `04a-capability-delta.md`: every functional requirement against every app, and the blank rows nobody carries. The scope is the lead's argument: a capability's requirements, the requirements an app's capabilities and flows touch, or every requirement. Read each requirement in scope with its criteria, the app pages with their contracts, and the flows. If there are no functional requirements yet, say so and offer `/vela:requirements`; if there are no app pages, offer `/vela:boundary`.

## 2. One requirement at a time

For the requirements in scope that are not fully allocated, show the allocation as a grid, requirement down and app across, with each cell's share in a few words, and take the lead's corrections. Read the grid in groups of about five requirements, not cell by cell, and say each requirement and app by its name. Behind each requirement is a numbered allocation sheet:

1. **What each app does:** what that app does toward this requirement, in the domain's words, as one sentence of 40 words or fewer, such as "accepts the order, rejects fractions and shorting, records the fill". Every acceptance criterion is covered by some share; the criteria stay on the requirement's page.
2. **What passes between apps, and the contract that carries it:** for each share that needs another app, the contract that carries it, and what the contract must then guarantee, such as "the Payments app answers within 3 seconds, or the Booking app shows unavailable".
3. **A handover no contract covers yet:** propose the contract: its provider, its consumers, what crosses, and its change.
4. **What nobody does yet:** any criterion no share covers. It is either a share for an app, or a gap the lead names as an unknown.

Label every line with what it rests on: the requirement, an app page, a contract, a source, or `(claude)` for your proposal. Write a line only after the yes `START.md` defines (a yes to a group counts for the lines in it). A line the lead can't answer becomes `vela add unknown --name "<name>" --capture ^cNN --blocks CAP-nnn.FRn`, written in the same checkpoint. Ask the lead first, and pass who would actually know as `--ask`, as `MODES.md` says under "Unknowns".

## 3. Write the confirmed rows

- **Each share** is one row per requirement in the app page's `## Requirements allocated` table, `| Requirement | Share | Through | State |`, added under that heading if the page lacks it: the requirement's link `[[CAP-nnn-<slug>#CAP-nnn.FRn <name>\|CAP-nnn.FRn]]`, with the pipe escaped because it sits in a table cell, the share as one sentence of 40 words or fewer in plain words with no ID in it (a longer cell draws W366), the contracts it goes through or `—`, and `assumption`.
- **A contract's obligation** is the row on the provider's table that names the contract in Through, with the guarantee in its Share. For a contract with an outside provider, the row goes on its consumer's page.
- **A handover no contract covers** that the lead confirmed is `vela add contract --provider APP-<slug> --consumers APP-<slug> --change new --capture ^cNN`, with `--name`, `--crosses` and `--change-policy` in the lead's words. It writes the required bullets on the provider's page and links each consumer. Tell the lead: "This is a new contract between apps that nobody planned when the apps were split. It still needs deciding like the others."
- Each written row gets a capture marked at once, `→ keep: [[<page>#<heading>|<ID>]] (assumption)`; rows have no ID of their own, so the capture links the app page's `Requirements allocated` heading and names the row as `CAP-nnn.FRn@APP-<slug>`, and so does its `## Changes` row in the session's notes. That label is for the files; to the lead, say the requirement and the app by name.

Then run `vela render` and `vela check`, fix every error, and commit a checkpoint with `vela close stage --checkpoint --for-lead`. The `allocation` block should show the requirement carried, and the trace check T7 (a code for you, not the lead) should no longer name it.

Draft the paragraph each filed item owes now, as `START.md` says under "Draft the paragraph when the item is filed", and show it with the filed line.

## 4. Review, then finish

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the rows are written" and the app pages and contracts this session changed as its focus. Show the digest as REVIEW says and capture what the lead takes.

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then each app's rows are settled with its page, in a grill or whenever the lead is sure, and `/vela:epics` takes each team's criteria from them. Say the one line the lead types by the app's name, such as "/vela:grill Desktop agent".

## Never

- Allocate inside one app: how an app splits its share among its own parts is its team's design.
- Put a requirement's criteria into a share cell. The cell is one sentence; the criteria stay on the requirement.
- Change a requirement to make it easier to allocate. A requirement that can't be allocated as written is a question for `/vela:requirements` or a grill, never a quiet rewrite.
