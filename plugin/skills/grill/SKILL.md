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
| GATE-2 | The item is at `assumption`, with a preferred option. Where there was a real choice, the rejected options and their reasons are written down in its `**Options considered:**` bullet. | Shape |
| GATE-3 | You showed the agenda, with the open questions under each item, and the user confirmed it with an explicit yes (see Acceptance). | show it again |
| GATE-4 | No open unknown lists the item in its `**Blocks:**`. Search `11-unknowns-and-risks.md` for open unknowns whose `**Blocks:**` links the item's page or heading. An open unknown that links a page blocks every item on that page, as `planner check` does. | an ask to the unknown's owner, or a research task |
| GATE-5 | The item's owner is present and says yes in person, or their async answer is quoted in a capture with them as origin, naming the channel and the date. | reschedule, or collect an async answer first |

If the user names an item that is already `decided`, say so. Offer to reopen it only if the user wants that, and say that reopening records the change of mind in the Changes table.

An item that fails any gate stays off the agenda. Say which gate failed and offer the mode in the last column. If no item passes, do not start the grill: make no change to any page, say why, and offer Shape or an ask instead.

After the table, write the agenda into the session record as an `## Agenda` section, one line per item: `- <ID>: GATE-3 confirmed yes|no, status open|decided|off-agenda: UNK-xxx|off-agenda: GATE-n`. An item that fails a gate other than GATE-4 carries `off-agenda: GATE-n` with the gate's number. Update the line as the item changes. START's resume rule reads this section.

GATE-4 is also a check rule: `planner check` fails an item that is `decided` while an open unknown blocks it.

## 3. The questions

- Ask one question at a time. Wait for the answer.
- Give your recommended answer with each question, in the form: question, then *Recommended: <answer>. <one-line reason>.*
- Prefer looking things up in the vault over asking.
- Use a concrete scenario at the edge of the item to force a precise answer. Pick an edge case, not the happy path.
- Check each answer against what the vault already holds and what the user said earlier. Say so when they disagree.
- Keep your recommendation when the user pushes back without a reason. Change it only for a reason, and say what the reason was.
- Never answer your own question.

## Acceptance

Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance. Before you close a branch, ask for an explicit yes or for an alternative. Before you write `decided`, read the final wording back and get a yes.

Capture each answer. The user's own words take their name as origin. When the user accepts your recommendation as it stands, the origin is `claude, from <name>`.

## 4. Write each decision as its branch closes

When an item's branch closes, write it at once, before the next question:

- Set its state to `decided`: the page's `state:` field, or the contract's `**State:**` bullet.
- Add `- **Decision:** [[<session id>]]` at page level, or under the contract's heading.
- For a contract, record where the provider stands as well as each consumer, as a capture: present, async with channel and date, asked in the PR, or "not consulted: <reason>".
- If anyone disagrees, add `- **Dissent:** <name>, <date>: <reason>`. The item can still be decided.
- Add a row to `## Changes`: `| <ID> | <old state> | decided | [[<session id>#^cNN]] |`, citing the capture that settled it.
- Mark the deciding capture line now: `→ keep: [[<page>#<heading>|<ID>]] (decided)`. This is the one exception to leaving marks off until close.
- Commit with the message `grill: <ID> decided`. Stage the session record and the changed pages, by exact path.

A functional requirement is a `### CAP-nnn.FRn <what the capability does>` heading on the capability page, and it is decided the same way. Its `**State:**` bullet moves to `decided`, `- **Decision:** [[<session id>]]` goes under its heading, and the `## Changes` row cites its ID. A `fact` FR needs a `**Source:**` bullet. An open unknown that blocks the FR fails GATE-4 for it. A requirements session may write an FR at `assumption` only. Only a Grill makes it `decided`.

Write fact bullets and table cells only. Prose waits for close.

## 5. A new unknown mid-grill

If a question turns up that nobody present can answer, write it as an unknown with owner, ask-by and `**Blocks:**` naming the item. Commit the new unknown at once. Take that item off the agenda (`off-agenda: UNK-xxx`), re-run GATE-4 for every other agenda item it blocks, and go on with the rest.

If it blocks an item already written `decided`, tell the user, and leave a `**Dissent:**` or follow-up note on that item. It will fail `check` with E316 until the unknown is resolved.

## Ends when

The agenda is empty or the user stops. Commit, then tell the user: "Run `/planner:close` to finish the session and open the PR."

## Never

- Never set `decided` on an item that failed a gate.
- Never write `fact` from what someone said in the grill without a source row.
- Never batch decisions to the end.
