# Review checkpoints

A review checkpoint finds the questions the plan owes and nobody has asked. Code works out what the catalogue owes (`planner questions`). One focused reviewer per focus area, each in a fresh context, reads only the written pages and finds what code cannot. `planner findings merge` combines what they return. The lead never sees the reviewers, only one ranked digest.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner`. The skill that sends you here names the checkpoint and its focus.

## Numbering

The checkpoint number `n` is 1 plus the number of `### ` headings under `## Reviews` in this session's record, or 1 if it has no such section. Work it out from the record each time, so it stays right after a resume. A re-run of some areas is a checkpoint of its own: see "Re-running areas" below.

## 1. Write it down first

A reviewer sees only what is written. Make sure everything said so far is in the session record as captures, and commit the record and any page this mode has changed, with the message `Checkpoint <session id> <n>`, where the session id is the record's file name without `.md` and `<n>` is the number above, staged by exact path.

List the pages for this checkpoint. A reviewer reads every page it is given, and each page it reads is paid for again on each of its turns, so give only the pages the checkpoint's focus touches:

- this session's record;
- every page this session has changed: `git diff --name-only --diff-filter=d main...HEAD`, which leaves out pages it deleted, keeping the `.md` files `planner check` reads (everything under the vault root except `CLAUDE.md`, `CONVENTIONS.md`, `voice/`, `handoffs/` and any folder whose name starts with a dot);
- `01-goals.md`, `02-constraints.md`, `03-context-and-scope.md` and `sources.md`;
- `11-unknowns-and-risks.md`, to be read only above its `## Question ledger` heading. Find that heading's line with `grep -n "^## Question ledger" 11-unknowns-and-risks.md` and write it into the dispatch, as `11-unknowns-and-risks.md, lines 1 to <line - 1>`. The ledger rows a reviewer needs are already in its area's `planner questions` output.

Each area's reviewer also gets the page of each subject its pending copies name: the `subject_page` field of its `planner questions --area <AREA> --json` output (section 2). Never give a reviewer an earlier session's record, `.inbox/`, `voice/` or `handoffs/`: what earlier sessions settled is on the pages already, and their `## Reviews` sections hold earlier findings. Tell each reviewer to skip the `## Reviews` section of this session's record, for the same reason.

## 2. The owed questions

Read the area codes from the `areas:` block of `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`. Today they are `FIN`, `DAT`, `PTN`, `REG` and `OPS`, but use what the block says. For each area run `planner questions --area <AREA> --json` and keep its output for that area's reviewer. A copy in that output is pending when its `pending` field is `true`: that covers `no row`, `open`, `asked` and an invalid row.

Then decide which areas this checkpoint reviews. An area is skipped only when both hold: nothing is owed in it, because no copy and no reviewer question in its output has `pending` set to `true`; and nothing in this checkpoint's material touches what it covers, by the table "What each focus area covers" in `${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md`. The material is this session's captures and the pages it changed. When in doubt, review the area. A skipped area is never silently absent: the merge reports it as `skipped (nothing in scope)` (section 4), and you tell the lead which areas were skipped and offer to run them.

## 3. One reviewer per area

Run `git status --porcelain` and keep its output as the baseline.

Clear the folder, then make it. Each command is one Bash call, with the real session id and number written in and no variables. The folder sits in `.planner/` is gitignored, so nothing in it is ever staged. It is not under `.git/`, because Claude Code will not write there without asking.

```
rm -rf .planner/findings/<session id>/<n>
mkdir -p .planner/findings/<session id>/<n>
```

Dispatch the `planner:area-reviewer` subagent with the Agent tool, once per area this checkpoint reviews, in one message so they run side by side: all five in one message when no area is skipped. Set the Agent tool's `model` to `sonnet` on every dispatch, as the agent's own `model: sonnet` says. A focused read-only check against a short list of pages does not need the session's model, and five of them at once cost five times as much. Give each one only:

- `Focus area: <AREA> <label>`;
- `Checkpoint: <the checkpoint and its focus>`;
- the list of page paths from section 1, with that area's subject pages added, and `11-unknowns-and-risks.md` with its line range;
- `Changed: <paths>`: this session's record and every page this session has changed, from section 1, comma-separated. A page most sessions touch only in part, `11-unknowns-and-risks.md` above all, goes in with the lines this session changed, `11-unknowns-and-risks.md:40-52+88-90`: the `+<start>,<count>` of each hunk header in `git diff -U0 main...HEAD -- <page>`. A new question is about these; an owed copy may be about any page;
- that area's `planner questions --area <AREA> --json` output.

Give no conversation, no summary of what the lead said, and no other area's questions. If the Agent tool lists no `planner:area-reviewer`, dispatch a general-purpose subagent instead, with `model` set to `sonnet` as well, and give it everything in `${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md` after the frontmatter as its instructions, then the same inputs, then this: you must not change any file. If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead. Never review the pages yourself in this conversation.

Save each reply exactly as it came back, with the Write tool, to `.planner/findings/<session id>/<n>/<AREA>.json`. If a reviewer errored, or could not be dispatched, write `{"area": "<AREA>", "error": "<what happened>"}` instead. Never write an empty findings list for a reviewer that did not finish: that would read as "checked, none".

Then run `git status --porcelain` again and compare it with the baseline. If a tracked file changed that you did not change, a reviewer changed it: stop and show the user.

## 4. Merge

Run `planner findings merge .planner/findings/<session id>/<n> --changed <paths>`, with the same `Changed:` list the reviewers got, comma-separated. A finding with copy `new` that quotes a page outside that list is dropped as "a new question about a page this session did not change": it was owed when that page was written, and raising it again every session is what makes a digest grow faster than a lead can answer it. When the checkpoint skipped any area, name the areas that ran and the areas skipped: `planner findings merge .planner/findings/<session id>/<n> --changed <paths> --areas FIN,DAT,REG --skipped PTN,OPS`. Its coverage line then reads `PTN skipped (nothing in scope)` for each skipped area, so none is missing from the record. It keeps the union, removes duplicates, and folds the same question raised by several areas into one finding that lists every area: near-identical wording, or the same quote on the same page with a looser match, decided by code. It drops every finding whose quote is not on the page it cites, and every finding whose quote shares no content word with its question or its subject's name ("the quote does not mention what the finding is about"). It never votes. A finding may address an owed copy, an open reviewer question by its `R-` id, or `new`. Exit 1 means an area did not run or a finding was dropped, and the output says which. Exit 2 means the tool failed: show the error, and record the checkpoint with every area as `did not run (merge failed: <error>)` and no table rows.

Write the result into the session record, under `## Reviews` after `## Captures`. Add the heading if the record has none.

```
### <n>. <checkpoint>, <today>

- **Coverage:** <the merge's coverage line, after "coverage: ", word for word>
- **Dropped:** <each dropped finding, its area and the reason, or none>
- **Merged:** <each finding the merge folded into another, as `[<area>] into F<n>.<m>: <its question>`, or none>

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F<n>.1 | FIN | high | Q-FIN-03@SV-01 | <the question> | "<the quote>" in [[<page file name without .md>]] |
| F<n>.2 | DAT, PTN, REG | high | new | <the question> | "<the quote>" in [[<page file name without .md>]] |
```

Number the kept findings `F<n>.1`, `F<n>.2` and so on, in the merge's order. The Area cell lists every area the merge gives the finding, first one first. The **Merged** line takes each entry under `duplicates:` in the merge's output whose question differs from the finding it joined, so every area's own words stay on the record. Escape a `|` inside a cell as `\|`. In the quote cell, replace each inner straight `"` with `”`, as the merge does when it checks the quote, so the quote stays valid on the ledger side.

Once the table is written, run `rm -rf .planner/findings/<session id>/<n>` again, with the real values written in, so no stale file is left to be read as fresh.

Tell the lead the coverage in plain words: which areas found something, which ran and found nothing, which were skipped because nothing in them was in scope, and which did not run and why. An area that did not run is never reported as clean. A skipped area is never reported as checked. Offer to run either.

## Re-running areas

A re-run of one or more areas is a new checkpoint, `n+1`, headed `### <n+1>. Re-run of checkpoint <n>: <areas>, <today>`. Running an area a checkpoint skipped is a re-run too. Dispatch only those areas into the new folder, and merge with `planner findings merge .planner/findings/<session id>/<n+1> --changed <paths> --areas FIN,REG`, naming them, with the same `Changed:` list. Areas not listed are neither read nor reported as did not run, and a file for one is ignored and listed under `ignored:`. The new findings get ids `F<n+1>.1` and on, so the ids of earlier checkpoints never change.

## 5. The digest

Run `planner questions --open --digest`. It prints the consequential lines in full first: those of high severity, and those that block something, ranked high and blocking first. Then it counts the rest by area, one line each, such as `FIN: 6 more (normal). List them: planner questions --open --digest --all --area FIN`, and ends with the command that prints every line in full, `planner questions --open --digest --all`. Nothing is hidden: every line stays in `planner questions --open`, in `--json` and in the ledger's `undisposed-questions` block.

Fold in the kept findings: one about an owed copy joins that copy's line, and one with copy `new` is a line of its own, ranked the same way: in full when it is high severity, else in its area's count. Show the full lines in that order, each with its focus area in brackets (every area, for a finding several areas raised), its copy IDs or finding ID, what it blocks, and "one answer for all?" when it groups several copies. Then show each area's count line and its command as the digest prints them, adding the normal findings to their area's count. There is no cap. When the lead asks for an area, or for everything, run the command the digest names and show those lines in full. Never drop a line to keep it short. Then ask: "Which do you want to take now? Any you can rule out?"

## 6. Record what the lead does

The lead sets the pace. What they take, capture as `START.md` says, starting the words with the copy ID or the finding ID, for example `- [thought] (Head of Finance) Q-FIN-03@SV-01: finance carries the balance today ^c14`. A yes to an existence question, one whose entry `creates` a party or stored value, also ends with the subject note, `type at close: PTY` or `type at close: SV`, as `dump/SKILL.md` shows, so close types the subject and writes the row in one go. A ruling-out is a capture with its reason. When the lead says a group of lines all wait on one open unknown, such as "all of these wait on the Platform team, UNK-050", capture it once, naming every ID: `- [thought] (<name>) waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4 ^c21`. Close writes one `unknown` row per ID linking that unknown, so the whole group leaves the digest and comes back when the unknown is resolved. If the group waits on something no unknown asks yet, write that unknown first, with an owner and an ask-by date. A belief the lead states without a source is a capture tagged `thought` that says it is a belief, and close asks whether it is load-bearing.

Write nothing to a page because of a finding, beyond what the mode itself writes. Close writes the ledger rows from these captures and from the `## Reviews` tables, so every copy taken and every finding ends in a row. Whatever the lead does not take stays open and visible, in the ledger's `undisposed-questions` block and in `planner questions`.
