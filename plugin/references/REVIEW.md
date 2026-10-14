# Review checkpoints

Contents: reader copy; numbering; 1 write it down; 2 the owed questions; 3 one reviewer per area; 4 merge; re-running areas; 5 the digest; 6 record what the lead does.

A review checkpoint finds the questions the plan owes and nobody has asked. Code works out what the catalog owes (`vela questions`). One focused reviewer per focus area, each in a fresh context, reads only the written pages and finds what code cannot. `vela findings merge` combines what they return. The lead never sees the reviewers, only one ranked digest.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela`. The skill that sends you here names the checkpoint and its focus.

## Reader copy

A reader copy has no git (`START.md`, "Owner or reader"). Skip the commit in section 1, and build the `Changed:` list from the session record's `## Changes` table and its captures instead of `git diff`. In section 3, replace the `git status --porcelain` comparison with a hash of each page and the record taken before and after the reviewers run (`shasum <path>`); a page whose hash moved was changed by a reviewer, so stop and show the lead. Everything else is as written.

## Numbering

The checkpoint number `n` is 1 plus the number of `### ` headings under `## Reviews` in this session's record, or 1 if it has no such section. Work it out from the record each time, so it stays right after a resume. A re-run of some areas is a checkpoint of its own: see "Re-running areas" below.

## 1. Write it down first

A reviewer sees only what is written. Make sure everything said so far is in the session record as captures, and commit the record and any page this mode has changed, with the message `Checkpoint <session id> <n>`, where the session id is the record's file name without `.md` and `<n>` is the number above, staged by exact path.

List the pages for this checkpoint. A reviewer reads every page it is given, and each page it reads is paid for again on each of its turns, so give only the pages the checkpoint's focus touches:

- this session's record;
- every page this session has changed: `git diff --name-only --diff-filter=d main...HEAD`, which leaves out pages it deleted, keeping the `.md` files `vela check` reads (everything under the vault root except `CLAUDE.md`, `CONVENTIONS.md`, `voice/`, `handoffs/` and any folder whose name starts with a dot);
- `01-goals.md`, `02-constraints.md`, `03-context-and-scope.md` and `sources.md`;
- `11-unknowns-and-risks.md`, to be read only above its `## Question ledger` heading. Find that heading's line with `grep -n "^## Question ledger" 11-unknowns-and-risks.md` and write it into the dispatch, as `11-unknowns-and-risks.md, lines 1 to <line - 1>`. The ledger rows a reviewer needs are already in its area's `vela questions` output.

Each area's reviewer also gets the page of each subject its pending copies name: the `subject_page` field of its `vela questions --area <AREA> --json` output (section 2). Never give a reviewer an earlier session's record, `.inbox/`, `voice/` or `handoffs/`: what earlier sessions settled is on the pages already, and their `## Reviews` sections hold earlier findings. Tell each reviewer to skip the `## Reviews` section of this session's record, for the same reason.

## 2. The owed questions

Read the area codes from the `areas:` block of `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`. Today they are `FIN`, `DAT`, `PTN`, `REG` and `OPS`, but use what the block says. For each area run `vela questions --area <AREA> --json`. Section 3 saves each area's output to a file for that area's reviewer. A copy in that output is pending when its `pending` field is `true`: that covers `no row`, `open`, `asked` and an invalid row.

Then decide which areas this checkpoint reviews. An area is skipped only when both hold: nothing is owed in it, because no copy and no reviewer question in its output has `pending` set to `true`; and nothing in this checkpoint's material touches what it covers, by the table "What each focus area covers" in `${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md`. The material is this session's captures and the pages it changed. When in doubt, review the area. A skipped area is never silently absent: the merge reports it as `skipped (nothing in scope)` (section 4), and you tell the lead which areas were skipped and offer to run them.

## 3. One reviewer per area

Run `git status --porcelain` and keep its output as the baseline.

Clear the folder, then make it. Each command is one Bash call, with the real session id and number written in and no variables. The folder sits in `.vela/` is gitignored, so nothing in it is ever staged. It is not under `.git/`, because Claude Code will not write there without asking.

```
rm -rf .vela/findings/<session id>/<n> .vela/findings/<session id>/<n>-questions
mkdir -p .vela/findings/<session id>/<n> .vela/findings/<session id>/<n>-questions
```

Then save each reviewed area's owed questions, one Bash call per area, with the real session id, number and area code written in: `vela questions --area <AREA> --json > .vela/findings/<session id>/<n>-questions/<AREA>.json`. They sit beside the findings folder, not in it, so the merge does not list them as ignored files.

Dispatch the `vela:area-reviewer` subagent with the Agent tool, once per area this checkpoint reviews, in one message so they run side by side: all five in one message when no area is skipped. Set the Agent tool's `model` to `sonnet` on every dispatch, as the agent's own `model: sonnet` says. A focused read-only check against a short list of pages does not need the session's model, and five of them at once cost five times as much. Give each one only:

- `Focus area: <AREA> <label>`;
- `Checkpoint: <the checkpoint and its focus>`;
- the list of page paths from section 1, with that area's subject pages added, and `11-unknowns-and-risks.md` with its line range;
- `Changed: <paths>`: this session's record and every page this session has changed, from section 1, comma-separated. A page most sessions touch only in part, `11-unknowns-and-risks.md` above all, goes in with the lines this session changed, `11-unknowns-and-risks.md:40-52+88-90`: the `+<start>,<count>` of each hunk header in `git diff -U0 main...HEAD -- <page>`. A new question is about these; an owed copy may be about any page;
- `Questions file: .vela/findings/<session id>/<n>-questions/<AREA>.json`, written out in full with the real session id, number and area code. It is the file you just saved for that area, so check that it exists before you dispatch. Never send a placeholder, a `<...>` template or the output pasted in place of the path.

While the reviewers run, say one line ("Checking this against five angles, about a minute.") and nothing more until the digest is ready. Do not report each reviewer returning, a failed command, a retry or a commit.

Give no conversation, no summary of what the lead said, and no other area's questions. If the Agent tool lists no `vela:area-reviewer`, dispatch a general-purpose subagent instead, with `model` set to `sonnet` as well, and give it everything in `${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md` after the frontmatter as its instructions, then the same inputs, then this: you must not change any file. If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead. Never review the pages yourself in this conversation.

Save each reply exactly as it came back, with the Write tool, to `.vela/findings/<session id>/<n>/<AREA>.json`. If a reviewer errored, or could not be dispatched, write `{"area": "<AREA>", "error": "<what happened>"}` instead. Never write an empty findings list for a reviewer that did not finish: that would read as "checked, none".

Then run `git status --porcelain` again and compare it with the baseline. If a tracked file changed that you did not change, a reviewer changed it: stop and show the user.

## 4. Merge

Run `vela findings merge .vela/findings/<session id>/<n> --changed <paths>`, with the same `Changed:` list the reviewers got, comma-separated. A finding with copy `new` that quotes a page outside that list is dropped as "a new question about a page this session did not change": it was owed when that page was written, and raising it again every session is what makes a digest grow faster than a lead can answer it. When the checkpoint skipped any area, name the areas that ran and the areas skipped: `vela findings merge .vela/findings/<session id>/<n> --changed <paths> --areas FIN,DAT,REG --skipped PTN,OPS`. Its coverage line then reads `PTN skipped (nothing in scope)` for each skipped area, so none is missing from the record. It keeps the union, removes duplicates, and folds the same question raised by several areas into one finding that lists every area: near-identical wording, or the same quote on the same page with a looser match, decided by code. It drops every finding whose quote is not on the page it cites, and every finding whose quote shares no content word with its question or its subject's name ("the quote does not mention what the finding is about"). It never votes. A finding may address an owed copy, an open reviewer question by its `R-` id, or `new`. Exit 1 means an area did not run or a finding was dropped, and the output says which. Exit 2 means the tool failed: show the error, and record the checkpoint with every area as `did not run (merge failed: <error>)` and no table rows.

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

Once the table is written, run `rm -rf .vela/findings/<session id>/<n>` again, with the real values written in, so no stale file is left to be read as fresh.

Give the coverage in one sentence ("All five angles found something", or "Four angles ran; the regulation angle did not run, because its reviewer failed"). An area that did not run is never reported as clean. It is named in that sentence. A skipped area is never reported as checked. The per-area detail goes in the record and the pull request body, not the conversation. Offer to run an area that did not.

## Re-running areas

A re-run of one or more areas, or running an area a checkpoint skipped, is a new checkpoint `n+1`. Read `${CLAUDE_PLUGIN_ROOT}/references/REVIEW-RERUN.md` for how it is headed, dispatched and merged.

## 5. The digest

Run `vela questions --open --digest`. It prints the consequential lines in full first: those of high severity, and those that block something, ranked high and blocking first. Then it counts the rest by area, one line each, such as `FIN: 6 more (normal). List them: vela questions --open --digest --all --area FIN`, and ends with the command that prints every line in full, `vela questions --open --digest --all`. Nothing is hidden: every line stays in `vela questions --open`, in `--json` and in the ledger's `undisposed-questions` block.

Fold in the kept findings: one about an owed copy joins that copy's line, and one with copy `new` is a line of its own, ranked the same way. All of it stays in the ledger and in `vela questions --open`, whatever the lead is shown: no question is dropped, only held back from the conversation.

What the lead is shown is small, so they can answer it.

- **Once per session, at a pause.** A mode may run its checkpoint more than once; each result goes in `## Reviews`. But the lead sees one digest per session, at the natural pause after a topic or at the end, never in the middle of their own line of thought. If they are still talking, carry on and show it last. Shape is the exception: its checkpoint comes before the options, and its findings go with the options as "what must be true" (the Shape skill says how); what is left goes in the one digest.
- **At most three questions.** Take the high and blocking lines first, and only those a reviewer tied to a page this session changed. Say each as one plain sentence with one question mark, as a colleague would across a desk, naming the thing and the person who would know, and give your recommended answer with it. No copy ID, finding ID, area code or severity in the sentence; those go in the record.
- **Never twice, never ruled out.** A question shown once this session is not shown again. Before you show a line, check the record's captures: a question the lead has ruled out, or answered, is not asked.
- **The rest, in one line.** "Eleven more are written down; say 'more' if you want the next three now." On "more", show the next three the same way.

For example, instead of "Q-PTN-02@PTY-01 and @PTY-03: does the agreement permit transfer of data to a new owner or user? One answer for all?", say:

> Legal hasn't been asked whether a digest of a client call counts as a client record. My suggestion is to write it down as a question for legal, due 6 November, unless you already know. Fine?
>
> Eleven more are written down; say "more" if you want the next three now.

A turn of 50 questions is a dump, not an interview, and the lead answers none of it well. Never paste a reviewer's reply, or the findings JSON, into the conversation: the digest is the only thing the lead reads. When the lead asks for an area, or for everything, run the command the digest names (`vela questions --open --digest --all --area FIN`) and show those lines three at a time.

## 6. Record what the lead does

The lead sets the pace. What they take, capture as `START.md` says, starting the words with the copy ID or the finding ID, for example `- [thought] (Head of Finance) Q-FIN-03@SV-01: finance carries the balance today ^c14`. A yes to an existence question, one whose entry `creates` a party or stored value, also ends with the subject note, `type at close: PTY` or `type at close: SV`, as `dump/SKILL.md` shows, so close types the subject and writes the row in one go. A ruling-out is a capture with its reason. When the lead says a group of lines all wait on one open unknown, such as "all of these wait on the Platform team, UNK-050", capture it once, naming every ID: `- [thought] (<name>) waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4 ^c21`. Close writes one `unknown` row per ID linking that unknown, so the whole group leaves the digest and comes back when the unknown is resolved. If the group waits on something no unknown asks yet, write that unknown first, with an owner and an ask-by date. A belief the lead states without a source is a capture tagged `thought` that says it is a belief, and close asks whether it is load-bearing.

Write nothing to a page because of a finding, beyond what the mode itself writes. Close writes the ledger rows from these captures and from the `## Reviews` tables, so every copy taken and every finding ends in a row. Whatever the lead does not take stays open and visible, in the ledger's `undisposed-questions` block and in `vela questions`.
