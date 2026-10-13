---
name: grill
description: Grill session for an initiative vault, the only session that may set an item to decided unless the user overrides that. Checks the readiness gate per item, offers to decide anyway on an override, asks one question at a time with a recommended answer, and writes each decided item as its branch closes. Use when there is a shaped position to defend.
argument-hint: "<item IDs or page names to decide>"
disable-model-invocation: true
---

# Grill

A Grill is the only session that makes an item `decided`. It decides items that are ready, or that the user chooses to decide anyway on an override, asks one question at a time, and writes each decision the moment its branch closes.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). The format is `CONVENTIONS.md`.

In a reader copy (`planner role` says `reader`), a Grill may still decide, but beside every item it decides write `- **Pending approval:** @<handle>, <today>`, and say that the owner sees it before it counts.

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `grill`. Read the Grill row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

If the user names a challenge to answer, by its PR number or the challenged ID, START will take its "Answer a challenge" path: the record is an answer session on the challenge's own branch, and you add `grill` to its `modes`, so it reads `modes: [answer, grill]`. Read the Answer row of `MODES.md` too. The agenda holds the challenge's `UNK-nnn` and the challenged item. Resolve the unknown with the senior as its owner: set `**State:** resolved`, add `**Outcome:**` and `**Resolved in:** [[<session id>]]`, and add the row `| UNK-nnn | open | resolved | [[<session id>#^cNN]] |`. If the answer changes the item, set it back first, to `reopened` for an epic or to `assumption` for anything else, then decide it again through the gate below.

## 2. The gate, per item

For each item the user named, check all five before it goes on the agenda. Never show the lead a gate table or a gate name. Say in two or three sentences what is ready to decide and what is not, and why, in plain words: "The strategy page is ready. The three apps and their contracts aren't, because nobody knows yet when the registration request goes in and who builds consent and identity." The gate names are for the record and the override bullet, which the check reads.

| Gate | Passes when | If it fails, offer |
|---|---|---|
| GATE-1 | For an app's item, the app's `stage` is `target` or later. Initiative-level items pass. | Discover |
| GATE-2 | The item is at `assumption`, with a preferred option. An epic is at `draft` or `reopened`, with its chosen cut. A concern cell passes when the user states what the initiative does for the app under that concern, as `CONVENTIONS.md` says under "Concern cells and waivers"; one the user says is `unchanged` or `n/a` is not grilled at all, but written as they say. Where there was a real choice, the rejected options and their reasons are written down in its `**Options considered:**` bullet. | Shape |
| GATE-3 | You showed the agenda, with the open questions under each item, and the user confirmed it with an explicit yes (see Acceptance). | show it again |
| GATE-4 | No open unknown lists the item in its `**Blocks:**`. Search `11-unknowns-and-risks.md` for open unknowns whose `**Blocks:**` links the item's page or heading. An open unknown that links a page blocks every item on that page, as `planner check` does. | ask the user whether they know the answer now; the unknown's owner and ask-by date, or a research task |
| GATE-5 | The item's owner is present and says yes in person, or their async answer is quoted in a capture with them as origin, naming the channel and the date. The user deciding on the owner's behalf also passes it, recorded as below. | reschedule, collect an async answer first, or decide on the owner's behalf |

If the user names an item that is already `decided`, say so. Offer to reopen it only if the user wants that, and say that reopening records the change of mind in the Changes table.

An item that is not ready is said so in one sentence ("The Summariser can't be decided yet: nobody has said how slow is too slow, and the product owner isn't here"), with the one thing that would make it ready: the mode in the last column of the table, or deciding it anyway. If the lead wants to decide it anyway, do it and record the override under the gate's name (`GATE-n`). Do not list gates. The user may override any gate, as `START.md` says under "The user may override any rule". Never refuse, and never ask twice. An item that fails a gate stays off the agenda until the lead chooses. Before offering the choices for a GATE-4 failure, ask the user whether they know the blocking unknown's answer now, and how, as `MODES.md` says under "Unknowns". If no item passes and the user overrides none, do not start the grill: make no change to any page, say why, and offer Shape or stopping. If the user takes neither, end the session as `MODES.md` says under "Unknowns". Never draft an ask, an email or a chase for the user to send.

When the user decides an item anyway, the item goes on the agenda and the rest of the Grill runs as normal: the agenda and its explicit yes (GATE-3), one question at a time, the read-back and the explicit yes before `decided`. When the item is written `decided` in section 4, also write, under its heading or at page level:

- `- **Override:** GATE-n by @<user's handle> on <today>: <their reason>`, one rule per failed gate, several in one bullet as `GATE-4, GATE-5`. Overriding GATE-3 itself means the user waives the agenda's explicit yes.
- When the owner is not the user and is not present: `- **Decided by:** @<user's handle>, on behalf of @<owner>`, with `GATE-5` in the Override. This is how GATE-5 passes with the owner away. Tell the user the owner confirms later with `- **Confirmed by:** @<owner> on <date>`, or raises `/planner:challenge` if they disagree, and that `planner check` warns with W324 until then.
- A `GATE-4` override keeps the open unknown open. `planner check` reports W316 instead of E316 for the item, quoting the override, until the unknown is resolved.

Before you show the agenda for GATE-3, find the open questions under each item, in two ways:

- Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check --gate grill --item <ID>`. Repeat `--item` once per item on the agenda. An ID that is not in the vault exits 2. Each W807 is an owed question, still open, asked or with no ledger row, that blocks that item. W807 can be stale for an answer captured this session, because close writes its row later: skip a W807 the session record already answers.
- Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "on the agenda" and the agenda items as its focus.

Route both lists through the digest in REVIEW section 5: at most three questions, as plain sentences with a recommended answer each, the ones that block the agenda's items first. The Grill asks the ones the lead takes before the item is decided. An owed question that blocks an item is a question to ask, not a gate. The user may decide the item with it still open. Then capture "decided with <copy IDs> open (W807)" with the user as origin, and add a note to that item's `## Changes` row. W807 prints only under `--gate grill --item`, so a plain check and CI never show it again: the capture is the record that the question was open when the item was decided.

After the gate check, write the agenda into the session record as an `## Agenda` section, one line per item: `- <ID>: GATE-3 confirmed yes|no, status open|decided|off-agenda: UNK-xxx|off-agenda: GATE-n`. An item that fails a gate other than GATE-4 carries `off-agenda: GATE-n` with the gate's number. An item the user chose to decide anyway carries `override: GATE-n` and a status, for example `- CON-003: GATE-3 confirmed yes, status open, override: GATE-5`. Update the line as the item changes. START's resume rule reads this section.

GATE-4 is also a check rule: `planner check` fails an item that is `decided` while an open unknown blocks it, with E316, unless an `**Override:**` on the item names `GATE-4`.

## 3. The questions

- Ask one question at a time. Wait for the answer.
- Name each item by its plain name when you ask; the ID goes in the file, not the sentence. An agenda of more than about seven items is shown in groups, and the user may take it in two sessions.
- Give your recommended answer with each question, in the form: question, then *Recommended: <answer>. <one-line reason>.*
- Prefer looking things up in the vault over asking.
- Use a concrete scenario at the edge of the item to force a precise answer. Pick an edge case, not the happy path.
- Check each answer against what the vault already holds and what the user said earlier. Say so when they disagree.
- Keep your recommendation when the user pushes back without a reason. Change it only for a reason, and say what the reason was.
- Never answer your own question.

## Acceptance

Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance. Before you close a branch, ask for an explicit yes or for an alternative. Before you write `decided`, read the final wording back and get a yes.

Capture each answer. The user's own words take their name as origin. When the user accepts your recommendation as it stands, the origin is `claude, from <name>`.

## Handing an app over

When the user grills an app's handoff, or `planner ladder` shows an app's pages reach `handoff`: in a reader copy, stop here and say "Handing an app to a senior is the owner's call: it stamps their commit. Name the owner from `.planner/published.json` and send a proposal." Otherwise:

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner ladder` and read the list under "Handoff" in `CONVENTIONS.md`. The epics are not on it: epics come after handoff, so neither the epics nor the epics gate holds a handoff back, and another app's gaps never do. Say once what is not met, as one list in plain words, and offer to hand over anyway; that is an override named `"handoff checklist"`, as `START.md` says. Do not ask about each line.
2. The senior who takes the app is named, with a handle. They are present and say yes, or their answer is quoted with the channel and the date, or the user decides on their behalf, recorded as GATE-5 says. If nobody is named, ask the user first, as `MODES.md` says under "Unknowns"; if they cannot name one, write the unknown and end the session.
3. Read back what the senior takes: the app, its runtime page, the contracts it provides and consumes, its epics, and every open unknown that blocks any of them. Also read back the links recorded for the app and each of its epics, and say which have none: "The team will look for the code, the wiki and the tracker items here. Anything to add before you hand over?" Record only what the user gives, and let them skip. Get an explicit yes.
4. On the app page, write `handed_off: "<senior>, <today>, PR pending"` and set `stage` to the stage `planner ladder` says the pages reach. If an open unknown asks who the senior is, resolve it with the name. Commit. Tell the senior that their tech design and build plan go in this vault, under `docs/`, when they run the skills from the vault root, and that the explorer then shows them with no setup. Do not run `planner handoff` here: close commits everything first, then writes the manifest, so it records a clean commit, and then the PR number.

## 4. Write each decision as its branch closes

When an item's branch closes, write it at once, before the next question:

- Set its state to `decided`: the page's `state:` field, or the contract's `**State:**` bullet. A Grill on an app page also takes its `## Requirements allocated` rows: read each row back as part of the app's agenda, as `CAP-nnn.FRn@APP-<slug>`, and set each row the user confirms to `decided` in its State cell. The page's `**Decision:**` answers for them, as it does for goal rows.
- Add `- **Decision:** [[<session id>]]` under the page's `## History`: directly under it for the page, under `#### <ID>` for a contract.
- For a contract, record where the provider stands as well as each consumer, as a capture: present, async with channel and date, asked in the PR, or "not consulted: <reason>".
- If anyone disagrees, add `- **Dissent:** <name>, <date>: <reason>`. The item can still be decided.
- If the user overrode a gate for it, add the `**Override:**` bullet, and `**Decided by:**` when the owner is not the user, as section 2 says.
- Add a row to `## Changes`: `| <ID> | <old state> | decided | [[<session id>#^cNN]] |`, citing the capture that settled it. For an epic the old state is `draft` or `reopened`: `| EPC-nnn | draft | decided | ... |` or `| EPC-nnn | reopened | decided | ... |`.
- Mark the deciding capture line now: `→ keep: [[<page>#<heading>|<ID>]] (decided)`. This is the one exception to leaving marks off until close.
- Commit with the message `grill: <ID> decided`. Stage the session record and the changed pages, by exact path.

A functional requirement is a `### CAP-nnn.FRn <what the capability does>` heading on the capability page, and it is decided the same way. Its `**State:**` bullet moves to `decided`, `- **Decision:** [[<session id>]]` goes under `#### <its ID>` in the capability page's `## History`, and the `## Changes` row cites its ID. A `fact` FR needs a `**Source:**` bullet. An open unknown that blocks the FR fails GATE-4 for it. A requirements session may write an FR at `assumption` only. Only a Grill makes it `decided`.

A release is a `## <name>` section on `04b-releases.md`, with no ID. A Grill decides it by setting that section's `**State:**` to `decided` and adding `- **Decision:** [[<session id>]]` directly under the page's `## History`. Without that Decision, check reports E303 on the release's heading.

Write fact bullets and table cells only. Prose waits for close. Any `- Trace:` line on an item or a criterion is the planner's: leave it exactly as it is.

## 5. A new unknown mid-grill

If a question turns up that nobody present can answer, write it as an unknown with owner, ask-by and `**Blocks:**` naming the item. Commit the new unknown at once. Take that item off the agenda (`off-agenda: UNK-xxx`), unless the user chooses to decide it anyway (override GATE-4), re-run GATE-4 for every other agenda item it blocks, and go on with the rest.

If it blocks an item already written `decided`, tell the user, and leave a `**Dissent:**` or follow-up note on that item. It will fail `check` with E316 until the unknown is resolved, or warn with W316 if the user overrides GATE-4 for it.

## Ends when

The agenda is empty or the user stops. Commit. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session".

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded.

- Never set `decided` on an item that failed a gate, unless the user overrode that gate and the `**Override:**` bullet is written.
- Never write `fact` from what someone said in the grill without a source row, unless the user overrides `E304`.
- Never batch decisions to the end.
