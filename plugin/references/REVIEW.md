# Review checkpoints

A review checkpoint finds the questions the plan owes and nobody has asked. Code works out what the catalogue owes (`planner questions`). One focused reviewer per focus area, each in a fresh context, reads only the written pages and finds what code cannot. `planner findings merge` combines what they return. The lead never sees the reviewers, only one ranked digest.

The planner is `python3 .claude/skills/planner/bin/planner`. The skill that sends you here names the checkpoint and its focus. Number the checkpoints of a session from 1.

## 1. Write it down first

A reviewer sees only what is written. Make sure everything said so far is in the session record as captures, and commit the record and any page this mode has changed, with the message `Checkpoint <id>`, staged by exact path.

List the pages to give the reviewers: every `.md` file `planner check` reads, which is everything under the vault root except `CLAUDE.md`, `CONVENTIONS.md`, `voice/`, `handoffs/` and any folder whose name starts with a dot, plus this session's record. Never give a reviewer `.inbox/`.

## 2. The owed questions

Run `planner questions --json` and read the area codes in the catalogue: `FIN`, `DAT`, `PTN`, `REG` and `OPS`. For each area run `planner questions --area <AREA> --json` and keep its output for that area's reviewer.

## 3. One reviewer per area

Run `mkdir -p .git/planner-findings/<session id>-<n>`, where `<n>` is this checkpoint's number. It sits inside `.git`, so it is never staged.

Dispatch the `planner:area-reviewer` subagent with the Agent tool, once per area, all five in one message so they run side by side. Give each one only:

- `Focus area: <AREA> <label>`;
- `Checkpoint: <the checkpoint and its focus>`;
- the list of page paths;
- that area's `planner questions --area <AREA> --json` output.

Give no conversation, no summary of what the lead said, and no other area's questions. If the Agent tool lists no `planner:area-reviewer`, dispatch a general-purpose subagent instead, and give it everything in `.claude/skills/planner/agents/area-reviewer.md` after the frontmatter as its instructions, then the same inputs, then this: you must not change any file, and you must report any file you changed. Never review the pages yourself in this conversation.

Save each reply exactly as it came back, with the Write tool, to `.git/planner-findings/<session id>-<n>/<AREA>.json`. If a reviewer errored, or could not be dispatched, write `{"area": "<AREA>", "error": "<what happened>"}` instead. Never write an empty findings list for a reviewer that did not finish: that would read as "checked, none".

Then run `git status --porcelain`. If a tracked file changed that you did not change, a reviewer changed it: stop and show the user.

## 4. Merge

Run `planner findings merge .git/planner-findings/<session id>-<n>`. It keeps the union, removes duplicates, drops every finding whose quote is not on the page it cites, and never votes. Exit 1 means an area did not run or a finding was dropped, and the output says which. Exit 2 means the tool failed: show the error.

Write the result into the session record, under `## Reviews` after `## Captures`. Add the heading if the record has none.

```
### <n>. <checkpoint>, <today>

- **Coverage:** <the merge's coverage line, after "coverage: ", word for word>
- **Dropped:** <each dropped finding, its area and the reason, or none>

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F<n>.1 | FIN | high | Q-FIN-03@SV-01 | <the question> | "<the quote>" in [[<page basename>]] |
```

Number the kept findings `F<n>.1`, `F<n>.2` and so on, in the merge's order. Escape a `|` inside a cell as `\|`. In the quote cell, replace each inner straight `"` with `”`, as the merge does when it checks the quote, so the quote stays valid on the ledger side.

Tell the lead the coverage in plain words: which areas found something, which ran and found nothing, and which did not run and why. An area that did not run is never reported as clean. Offer to run it again.

## 5. The digest

Run `planner questions --open --digest`. Fold in the kept findings: one about an owed copy joins that copy's line, and one with copy `new` is a line of its own, ranked the same way, high severity first. Show every line in that order, each with its focus area in brackets, its copy IDs or finding ID, what it blocks, and "one answer for all?" when it groups several copies. There is no cap. If the list is long, show the first lines whole and say how many follow, then go on when the lead says so. Never drop a line to keep it short. Then ask: "Which do you want to take now? Any you can rule out?"

## 6. Record what the lead does

The lead sets the pace. What they take, capture as `START.md` says, starting the words with the copy ID or the finding ID, for example `- [thought] (Head of Finance) Q-FIN-03@SV-01: finance carries the balance today ^c14`. A ruling-out is a capture with its reason. A belief the lead states without a source is a capture tagged `thought` that says it is a belief, and close asks whether it is load-bearing.

Write nothing to a page because of a finding, beyond what the mode itself writes. Close writes the ledger rows from these captures and from the `## Reviews` tables, so every copy taken and every finding ends in a row. Whatever the lead does not take stays open and visible, in the ledger's `undisposed-questions` block and in `planner questions`.
