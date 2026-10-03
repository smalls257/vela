---
name: grill
description: Grill session for an initiative vault, the only session that may set an item to decided. Checks the readiness gate per item, asks one question at a time with a recommended answer, and writes each decided item as its branch closes. Use when there is a shaped position to defend.
argument-hint: "<item IDs or page names to decide>"
disable-model-invocation: true
---

# Grill

A Grill is the only session that makes an item `decided`. It decides only items that are ready, asks one question at a time, and writes each decision the moment its branch closes.

The planner is `python3 .claude/skills/planner/bin/planner`. The format is `CONVENTIONS.md`.

## 1. Start

Run the steps in `.claude/skills/planner/references/START.md` with mode `grill`. Read the Grill row of `.claude/skills/planner/references/MODES.md`.

## 2. The gate, per item

For each item the user named, check all five before it goes on the agenda. Show the result as a table: item, then GATE-1 to GATE-5, each pass or fail with one line of evidence.

| Gate | Passes when | If it fails, offer |
|---|---|---|
| GATE-1 | For an app's item, the app's `stage` is `target` or later. Initiative-level items pass. | Discover |
| GATE-2 | The item is at `assumption`, with a preferred option. Where there was a real choice, the rejected options and their reasons are written down. | Shape |
| GATE-3 | You showed the agenda, with the open questions under each item, and the user confirmed it. | show it again |
| GATE-4 | No open unknown lists the item in its `**Blocks:**`. Search `11-unknowns-and-risks.md` for open unknowns whose `**Blocks:**` links the item's page or heading. | an ask to the unknown's owner, or a research task |
| GATE-5 | The item's owner is present, or their answer is already a capture with them as origin, naming the channel and the date. | reschedule, or collect an async answer first |

An item that fails any gate stays off the agenda. Say which gate failed and offer the mode in the last column. If no item passes, do not start the grill: make no change to any page, say why, and offer Shape or an ask instead.

GATE-4 is also a check rule: `planner check` fails an item that is `decided` while an open unknown blocks it.

## 3. The questions

- Ask one question at a time. Wait for the answer.
- Give your recommended answer with each question, in the form: question, then *Recommended: <answer>. <one-line reason>.*
- Prefer looking things up in the vault over asking.
- Use a concrete scenario at the edge of the item to force a precise answer. Pick an edge case, not the happy path.
- Check each answer against what the vault already holds and what the user said earlier. Say so when they disagree.
- Keep your recommendation when the user pushes back without a reason. Change it only for a reason, and say what the reason was.
- Never answer your own question.

Capture each answer. The user's own words take their name as origin. When the user accepts your recommendation as it stands, the origin is `claude, from <name>`.

## 4. Write each decision as its branch closes

When an item's branch closes, write it at once, before the next question:

- Set its state to `decided`: the page's `state:` field, or the contract's `**State:**` bullet.
- Add `- **Decision:** [[<session id>]]` at page level, or under the contract's heading.
- For a contract, record where each consumer stands as a capture: present, async with channel and date, asked in the PR, or "not consulted: <reason>".
- If anyone disagrees, add `- **Dissent:** <name>, <date>: <reason>`. The item can still be decided.
- Add a row to `## Changes`: `| <ID> | <old state> | decided | [[<session id>#^cNN]] |`, citing the capture that settled it.
- Commit with the message `grill: <ID> decided`.

Write fact bullets and table cells only. Prose waits for close.

## 5. A new unknown mid-grill

If a question turns up that nobody present can answer, write it as an unknown with owner, ask-by and `**Blocks:**` naming the item. Take that item off the agenda and go on with the rest.

## Ends when

The agenda is empty or the user stops. Commit, then tell the user: "Run `/planner:close` to finish the session and open the PR."

## Never

- Never set `decided` on an item that failed a gate.
- Never write `fact` from what someone said in the grill without a source row.
- Never batch decisions to the end.
