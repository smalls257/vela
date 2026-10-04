---
name: close
description: Close an initiative-vault session. Marks every capture keep, park or drop, writes the promoted items into the pages, drafts prose in the house voice, renders and checks the vault, then commits, pushes and opens the PR with reviewers. Use at the end of any planner session.
argument-hint: "[session id, if more than one is open]"
disable-model-invocation: true
---

# Close a session

Close turns a session record into a reviewed PR. Run every step in order. Never skip a step to save time, and never report a step as done when it failed.

The planner is `python3 .claude/skills/planner/bin/planner`. The format is `CONVENTIONS.md`.

## 1. Find the session

Open records live on `session/<id>` branches, so first run `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`, and read each record with `git show <branch>:sessions/<id>.md`. Find the one with `status: open`. If there is more than one, ask which. Find that record's branch and switch to it with `git switch session/<id>` before anything else.

## 2. Mark every capture

Propose a mark for every capture that has none yet, at once, as a numbered list with a one-line reason each. The user changes the ones they disagree with. Defaults:

- In a session whose `modes` include `shape`, the picked option is kept as an `assumption`, never an `inkling`. See step 3.
- A person's `idea` or `thought` is kept as an `inkling` on the page it belongs to.
- A person's `unknown` or `worry` is kept as an unknown with an owner handle and an ask-by date you propose, or as a concern cell.
- An `unknown` capture is kept or dropped with a reason. It is never parked. For a `claude`-origin `unknown`, the user must choose: kept as an UNK with an owner and an ask-by date, or dropped with a reason. Claude never decides it alone. This rule wins over the park default for `claude` lines.
- A person's `wild` line is parked, never dropped.
- A `(claude)` line is parked unless the user picks it. This covers every origin that starts with `claude`, including `(claude, from <name>)`.
- Never propose `fact`. A capture becomes a fact only if the user names its source in this turn and the source has a row in `sources.md`.
- A line you will copy word for word onto a page is a lifted line. List each one and ask the user to confirm it before you copy it.

A line a Grill already marked `(decided)`, or a Discover already marked `(fact)`, keeps its mark. Leave it alone. It still appears under "Promoted on a nod" when its origin starts with `claude`.

Write each mark into the line: `→ keep: [[<page>#<heading>|<ID>]] (<state>)`, `→ park` or `→ drop: <reason>`, before the `^cNN`.

## 3. Write the promoted items

Write each kept item onto its page as structured content only: fact bullets, table rows and `### <ID> <short name>` headings, per `CONVENTIONS.md`. A Grill already wrote its decided items, and Discover already wrote its facts, so leave those alone.

For a session whose `modes` include `epics`, the epic pages already exist, so write no `assumption` item for a picked cut, and skip the `shape` paragraph that follows. Still add the `## Changes` rows for every epic whose state changed, `| EPC-nnn | - | draft | [[<id>#^cNN]] |` and `| EPC-nnn | draft | decided | ... |`, if the session has not already. For any other session whose `modes` include `shape`, write the picked option as an `assumption` item with an `Options considered` list: each option, and for each rejected one, why it was rejected. If a capture says "that's decided", add a "grill to confirm" note to the item. The item must pass grill's GATE-2 afterwards: at `assumption`, with a preferred option and the rejected options with their reasons. New items get the next free ID of their kind: grep the vault for the existing IDs of that kind, and also read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'` (`git show <branch>:sessions/<id>.md`), because another open session may already hold the next ID. Add one to the highest in use. Add one row to `## Changes` for each item whose state changed: `| ID | From | To | [[<id>#^cNN]] |`.

## 4. Draft the prose

Read `.claude/skills/planner/skills/house-voice/SKILL.md` and follow it for every paragraph this session needs. For a session whose `modes` include `epics`, each epic it drafted owes a description paragraph, so list those epics under "Prose drafted" in the PR body. The epics session already wrote each `**Owning team:**` line; close leaves it as written. Prose is drafted here and nowhere else. Commit the drafts on their own with the message `draft: prose for <id>`, so the reviewer's edits show as a diff.

### Voice review

A fresh reader checks the drafts, because the drafter cannot judge its own voice. Skip this if the session drafted no paragraph.

1. List every paragraph in the `draft: prose for <id>` commit: a number, the page path, its voice type from house-voice's table, and the paragraph's text. Run `git status --porcelain` and keep the output.
2. Dispatch the `planner:voice-reviewer` subagent with the Agent tool, and give it the list. If the Agent tool lists no `planner:voice-reviewer`, dispatch a general-purpose subagent instead, and give it everything in `.claude/skills/planner/agents/voice-reviewer.md` after the frontmatter as its instructions, then the list, then this: you must not change any file, and you must report any file you changed. Never review the drafts yourself in this conversation. If no subagent can be dispatched, write "**Voice review:** not run: <the reason>" in the PR body and go on to step 5.
3. Run `git status --porcelain` again. If the output differs from step 1, the reviewer changed a file: stop and show the user. If the reviewer errored, or returned anything but the table, treat the review as not run, write "**Voice review:** not run: <the reason>" in the PR body, and go on to step 5. If it flagged no paragraph, skip steps 4 and 5 of this part: there is nothing to rewrite and no commit.
4. Rewrite each paragraph the reviewer flags once, in the working tree, from what it says differs. Do not send the rewrite back for review. A paragraph it did not flag stays as drafted. Note the pages you rewrote. Touch no other file. Before you rewrite a page, check it holds no uncommitted edit from step 2 or 3, because a restore would discard that edit. For each `<page>`:

   ```
   git diff --quiet HEAD -- <page> || { git add -- <page> && git commit -qm "Checkpoint <id>" -- <page>; }
   ```

   This commits that page alone, with the message `Checkpoint <id>`, when it differs from HEAD. Then rewrite it, so `git restore -- <page>` returns the page to a state that already holds those edits.
5. Check only the pages you rewrote, one at a time, because the working tree also holds step 2 and 3 work that is not committed. For each rewritten `<page>`:

   ```
   tmp=$(mktemp)
   git show HEAD:<page> > "$tmp"
   python3 .claude/skills/planner/bin/planner voicecheck "$tmp" <page>; code=$?; rm -f "$tmp"; (exit $code)
   ```

   voicecheck fails if a rewrite lost, added or moved a wikilink, code span, date, ID, number (with its units or currency), table cell, version, frontmatter line or negation.
   - Exit 0: keep the rewrite.
   - Exit 1: run `git restore -- <page>`. That discards every rewrite on that page and keeps its earlier draft whole. Run it for no other file.
   - Exit 2: show the error, then run `git restore -- <page>` so the unchecked rewrite stays out of the work that step 7 stages. Never commit a rewrite voicecheck could not check.

   Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`, staging each page by exact path.

## 5. Read back decided wording

For each item that became `decided` in this session, show its final wording. If its owner is present, they confirm it. If not, list it in the PR body for them.

## 6. Render and check

Run `python3 .claude/skills/planner/bin/planner render`, then `python3 .claude/skills/planner/bin/planner check`. Fix each error with the user. If the user leaves an error in place, put it in the PR body. CI will block the merge until it is fixed.

## 7. Finish the record

Stage every file `planner render` reported, plus the session record and the changed pages, by exact path. Never use `git add -A`. Before pushing, `git status --short` must show nothing modified. A rewritten block left out of the commit fails CI's render check. Draft a one-line `summary:` and let the user accept or edit it. Set `status: closed`, then stage. Commit with the message `Close session <id>`. Run `git push -u origin session/<id>`. If the push fails, show the error, print the commands for the user to run, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the PR

Collect the reviewers:

- the `owner:` of each app page this session changed;
- the `owner:` of each consumer app of a contract this session changed.

Get the user's own handle with `gh api user -q .login`. Strip the leading `@` from each individual handle. A team handle `@org/team` is passed as `org/team`. Drop the user's own handle. If nobody remains, leave out `--reviewer`.

Write the PR body to a temporary file. Fill the headings of the vault's PR template:

- **What changed.** The promoted items, each with its new state. Then these lists, each with "none" when empty:
  - **Prose drafted:** each paragraph in the `draft: prose for <id>` commit, page by page.
  - **Voice review:** each paragraph the reviewer flagged, what it said, and whether it was rewritten or kept because voicecheck named a changed token; or "not run: <reason>".
  - **Decided wording not yet read back:** each `decided` item whose owner was not present in step 5.
  - **Promoted on a nod:** every item kept or promoted from a capture whose origin starts with `claude`, not only the deciding capture, with the capture quoted.
  - **Changed contracts:** each contract, and for each consumer, who was asked: present, async, in this PR, or "not consulted: <reason>".
  - **Overdue unknowns:** each `W705` line from step 6, with its owner @-mentioned.
  - **May still say the old value:** for each `decided` or `fact` value this session changed, run `grep -rn -F "<old wording>" --include='*.md' . | grep -v '^./sessions/'` and list every hit.
  - **Check:** the first line of the check output, and any error left in place.
- **Minutes.** Ask the user how long the session took.
- **Structural fixes** and **Prose edits.** Write "Filled in by the reviewer."

Then run the command below, with one `--reviewer` per remaining reviewer (none, if nobody remains). `<Mode name>` is the display name in `MODES.md`.

```
gh pr create --base main --head session/<id> --title "<date> <Mode name>: <topic>" --body-file <file> --reviewer <handle> --reviewer <org/team>
```

If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL. Show the URL.
