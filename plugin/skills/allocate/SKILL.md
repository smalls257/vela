---
name: allocate
description: Divide each functional requirement among the apps and contracts that deliver it, and write each app's share at assumption. Use after boundary and before epics.
argument-hint: "[CAP-nnn, APP-<slug>, or none for the whole initiative]"
disable-model-invocation: true
---

# Allocate

Make every requirement somebody's. A capability's requirements say what the business needs; the apps and contracts are now drawn. Allocation says, for each requirement, which app carries which part, and which contract carries the part that crosses between them, so every requirement has an owner before anyone cuts epics. Allocation never decides: each row is an `assumption` until a Grill.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The format is `vela conventions "Requirements and allocation"`.

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `allocate`. Read the Allocate row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

If `04a-capability-delta.md` has no `allocation` block, as in a vault started before it existed, add an `## Allocation` section with the empty block markers as `vela conventions "Generated blocks"` shows. Run `vela render` and read the `allocation` block on `04a-capability-delta.md`: every functional requirement against every app, and the blank rows nobody carries. The scope is the user's argument: a capability's requirements, the requirements an app's capabilities and flows touch, or every requirement. Read each requirement in scope with its criteria, the app pages and their contracts, the runtime pages and the flows. If there are no functional requirements yet, say so and offer `/vela:requirements`; if there are no app pages, offer `/vela:boundary`.

## 2. One requirement at a time

For the requirements in scope that are not fully allocated, show the allocation as a grid, requirement down and app across, the same grid the `allocation` block draws, with each cell's share in a few words, and take the lead's corrections. Read the grid in groups of about five requirements, not cell by cell. Behind each requirement is a numbered allocation sheet:

1. **Each app's share:** what that app does toward this requirement, in the domain's words, as one sentence of 40 words or fewer, such as "accepts the order, rejects fractions and shorting, records the fill". Every acceptance criterion of the requirement is covered by some share; the criteria stay on the requirement's page, where they already live, and the row never lists them.
2. **What crosses:** for each share that needs another app, the contract that carries it, and what the contract must then guarantee, such as "the Payments app answers within 3 seconds, or the Booking app shows unavailable".
3. **A missing contract:** a crossing no contract covers. Propose the contract: its provider, its consumers, what crosses, and its change.
4. **What is left:** any criterion no share covers. It is either a share for an app, or a gap the user names as an unknown.

Label every line with what it rests on: the requirement, an app page, a contract, a source, or `(claude)` for your proposal. Write a line only after the yes `START.md` defines (a yes to a group counts for the lines in it). A line the user cannot answer becomes an unknown with an owner handle, an ask-by date and `**Blocks:**` linking the requirement, written in the same checkpoint. Ask the lead first, and write who would actually know as `**Ask:**`, as `MODES.md` says under "Unknowns".

## 3. Write the confirmed rows

- **Each share** is one row per requirement in the app page's `## Requirements allocated` table, `| Requirement | Share | Through | State |`, added under that heading if the page lacks it: the requirement's link `[[CAP-nnn-<slug>#CAP-nnn.FRn <name>\|CAP-nnn.FRn]]`, with the pipe escaped because it sits in a table cell (a table vela reads keeps the ID as its label), the share as one sentence of 40 words or fewer in plain words with no ID in it (a longer cell draws W366), the contracts it goes through or `—`, and `assumption`. Do not put the criteria in the cell, not one per row and not five in a row: the table says who does what, and the requirement's page holds what a tester checks. Show the user the requirement and the contract by name; the IDs are for the table.
- **A contract's obligation** is the row on the provider's table that names the contract in Through, with the guarantee in its Share. For a contract with an outside provider, the row goes on its consumer's page.
- **A missing contract** the user confirmed is written on the provider's page as `vela conventions "Fact bullets"` says for contracts, with every required bullet, `**State:** assumption` and `**Change:** new`, then linked from each consumer. Tell the user it is a new contract that boundary did not draw, and that it needs a Grill like any other.
- Each written row and contract gets a capture marked at once, `→ keep: [[<page>#<heading>|<ID>]] (assumption)`, as Boundary does; rows have no ID of their own, so the capture links the app page's `Requirements allocated` heading and names the row as `CAP-nnn.FRn@APP-<slug>`, and so does its `## Changes` row in the session record.

Then run `vela render` and `vela check`, fix every error, and commit a checkpoint. The `allocation` block should show the requirement carried, and the trace check T7 (a code for you, not the lead) should no longer name it.

## 4. Review, then finish

Once the rows in scope are written, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the rows are written" and the app pages and contracts this session changed as its focus. Show the digest as REVIEW says and capture what the lead takes.

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a Grill on each app (`/vela:grill APP-<slug>`) decides its allocated rows with its page, which sets each confirmed row's State to decided, and `/vela:epics` takes each team's criteria from them.

## Never

- Allocate inside one app: how an app splits its share among its own parts is its team's design.
- Put a requirement's criteria into a Share cell. The cell is one sentence; the criteria stay on the requirement.
- Change a requirement to make it easier to allocate. A requirement that cannot be allocated as written is a question for `/vela:requirements` or a Grill, never a quiet rewrite.
- Write `decided`. Only a Grill decides, unless the user overrides it as `START.md` says.
