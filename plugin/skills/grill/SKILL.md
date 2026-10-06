---
name: grill
description: Grill session for an initiative vault, the only session that may set an item to decided unless the user overrides that. Checks the readiness gate per item, offers to decide anyway on an override, asks one question at a time with a recommended answer, and writes each decided item as its branch closes. Use when there is a shaped position to defend.
argument-hint: "<item IDs or page names to decide>"
disable-model-invocation: true
---

# Grill

A Grill is the only session that makes an item `decided`. It decides items that are ready, or that the user chooses to decide anyway on an override, asks one question at a time, and writes each decision the moment its branch closes.

The planner is `python3 .claude/skills/planner/bin/planner`. The format is `CONVENTIONS.md`.

## 1. Start

Run the steps in `.claude/skills/planner/references/START.md` with mode `grill`. Read the Grill row of `.claude/skills/planner/references/MODES.md`.

If the user names a challenge to answer, by its PR number or the challenged ID, START will take its "Answer a challenge" path: the record is an answer session on the challenge's own branch, and you add `grill` to its `modes`, so it reads `modes: [answer, grill]`. Read the Answer row of `MODES.md` too. The agenda holds the challenge's `UNK-nnn` and the challenged item. Resolve the unknown with the senior as its owner: set `**State:** resolved`, add `**Outcome:**` and `**Resolved in:** [[<session id>]]`, and add the row `| UNK-nnn | open | resolved | [[<session id>#^cNN]] |`. If the answer changes the item, set it back first, to `reopened` for an epic or to `assumption` for anything else, then decide it again through the gate below.

## 2. The gate, per item

For each item the user named, check all five before it goes on the agenda. Show the result as a table: item, then GATE-1 to GATE-5, each pass or fail with one line of evidence.

| Gate | Passes when | If it fails, offer |
|---|---|---|
| GATE-1 | For an app's item, the app's `stage` is `target` or later. Initiative-level items pass. | Discover |
| GATE-2 | The item is at `assumption`, with a preferred option. An epic is at `draft` or `reopened`, with its chosen cut. Where there was a real choice, the rejected options and their reasons are written down in its `**Options considered:**` bullet. | Shape |
| GATE-3 | You showed the agenda, with the open questions under each item, and the user confirmed it with an explicit yes (see Acceptance). | show it again |
| GATE-4 | No open unknown lists the item in its `**Blocks:**`. Search `11-unknowns-and-risks.md` for open unknowns whose `**Blocks:**` links the item's page or heading. An open unknown that links a page blocks every item on that page, as `planner check` does. | an ask to the unknown's owner, or a research task |
| GATE-5 | The item's owner is present and says yes in person, or their async answer is quoted in a capture with them as origin, naming the channel and the date. The user deciding on the owner's behalf also passes it, recorded as below. | reschedule, collect an async answer first, or decide on the owner's behalf |

If the user names an item that is already `decided`, say so. Offer to reopen it only if the user wants that, and say that reopening records the change of mind in the Changes table.

An item that fails a gate stays off the agenda until the user chooses. Say which gate failed, say in one sentence what that gate protects, and offer the choices: the mode in the last column, or "decide anyway (override GATE-n)". The user may override any gate, as `START.md` says under "The user may override any rule". Never refuse, and never ask twice. If no item passes and the user overrides none, do not start the grill: make no change to any page, say why, and offer Shape or an ask instead.

When the user picks "decide anyway (override GATE-n)", the item goes on the agenda and the rest of the Grill runs as normal: the agenda and its explicit yes (GATE-3), one question at a time, the read-back and the explicit yes before `decided`. When the item is written `decided` in section 4, also write, under its heading or at page level:

- `- **Override:** GATE-n by @<user's handle> on <today>: <their reason>`, one rule per failed gate, several in one bullet as `GATE-4, GATE-5`. Overriding GATE-3 itself means the user waives the agenda's explicit yes.
- When the owner is not the user and is not present: `- **Decided by:** @<user's handle>, on behalf of @<owner>`, with `GATE-5` in the Override. This is how GATE-5 passes with the owner away. Tell the user the owner confirms later with `- **Confirmed by:** @<owner> on <date>`, or raises `/planner:challenge` if they disagree, and that `planner check` warns with W324 until then.
- A `GATE-4` override keeps the open unknown open. `planner check` reports W316 instead of E316 for the item, quoting the override, until the unknown is resolved.

Before you show the agenda for GATE-3, find the open questions under each item, in two ways:

- Run `python3 .claude/skills/planner/bin/planner check --gate grill --item <ID>`. Repeat `--item` once per item on the agenda. An ID that is not in the vault exits 2. Each W807 is an owed question, still open, asked or with no ledger row, that blocks that item. W807 can be stale for an answer captured this session, because close writes its row later: skip a W807 the session record already answers.
- Run the review checkpoint in `.claude/skills/planner/references/REVIEW.md`, with the checkpoint "on the agenda" and the agenda items as its focus.

Route both lists through the digest in REVIEW section 5, grouped under their item, each with its copy or finding ID. Show the high and blocking lines in full and the rest counted by area, as the digest prints them, and run the command a count names when the lead asks for it. Ask: "Which do you want to take now?" The Grill asks the ones taken before the item is decided. An owed question that blocks an item is a question to ask, not a gate. The user may decide the item with it still open. Then capture "decided with <copy IDs> open (W807)" with the user as origin, and add a note to that item's `## Changes` row. W807 prints only under `--gate grill --item`, so a plain check and CI never show it again: the capture is the record that the question was open when the item was decided.

After the table, write the agenda into the session record as an `## Agenda` section, one line per item: `- <ID>: GATE-3 confirmed yes|no, status open|decided|off-agenda: UNK-xxx|off-agenda: GATE-n`. An item that fails a gate other than GATE-4 carries `off-agenda: GATE-n` with the gate's number. An item the user chose to decide anyway carries `override: GATE-n` and a status, for example `- CON-003: GATE-3 confirmed yes, status open, override: GATE-5`. Update the line as the item changes. START's resume rule reads this section.

GATE-4 is also a check rule: `planner check` fails an item that is `decided` while an open unknown blocks it, with E316, unless an `**Override:**` on the item names `GATE-4`.

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
- If the user overrode a gate for it, add the `**Override:**` bullet, and `**Decided by:**` when the owner is not the user, as section 2 says.
- Add a row to `## Changes`: `| <ID> | <old state> | decided | [[<session id>#^cNN]] |`, citing the capture that settled it. For an epic the old state is `draft` or `reopened`: `| EPC-nnn | draft | decided | ... |` or `| EPC-nnn | reopened | decided | ... |`.
- Mark the deciding capture line now: `→ keep: [[<page>#<heading>|<ID>]] (decided)`. This is the one exception to leaving marks off until close.
- Commit with the message `grill: <ID> decided`. Stage the session record and the changed pages, by exact path.

A functional requirement is a `### CAP-nnn.FRn <what the capability does>` heading on the capability page, and it is decided the same way. Its `**State:**` bullet moves to `decided`, `- **Decision:** [[<session id>]]` goes under its heading, and the `## Changes` row cites its ID. A `fact` FR needs a `**Source:**` bullet. An open unknown that blocks the FR fails GATE-4 for it. A requirements session may write an FR at `assumption` only. Only a Grill makes it `decided`.

Write fact bullets and table cells only. Prose waits for close.

## 5. A new unknown mid-grill

If a question turns up that nobody present can answer, write it as an unknown with owner, ask-by and `**Blocks:**` naming the item. Commit the new unknown at once. Take that item off the agenda (`off-agenda: UNK-xxx`), unless the user chooses to decide it anyway (override GATE-4), re-run GATE-4 for every other agenda item it blocks, and go on with the rest.

If it blocks an item already written `decided`, tell the user, and leave a `**Dissent:**` or follow-up note on that item. It will fail `check` with E316 until the unknown is resolved, or warn with W316 if the user overrides GATE-4 for it.

## Ends when

The agenda is empty or the user stops. Commit, then tell the user: "Run `/planner:close` to finish the session and open the PR."

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded.

- Never set `decided` on an item that failed a gate, unless the user overrode that gate and the `**Override:**` bullet is written.
- Never write `fact` from what someone said in the grill without a source row, unless the user overrides `E304`.
- Never batch decisions to the end.
