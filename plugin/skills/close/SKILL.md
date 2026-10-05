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

- In a session whose `modes` include `shape`, the picked option is kept as an `assumption`, never an `inkling`. See section 3.
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

For a session whose `modes` include `epics`, the epic pages already exist, so write no `assumption` item for a picked cut, and skip the `shape` paragraph that follows. Still add the `## Changes` rows for every epic whose state changed, `| EPC-nnn | - | draft | [[<id>#^cNN]] |` and `| EPC-nnn | draft | decided | ... |`, if the session has not already. For any other session whose `modes` include `shape`, write the picked option as an `assumption` item with an `**Options considered:**` bullet, at page level or under the item's heading: `- **Options considered:** <picked option> (picked); <option>: rejected, <reason>; ...`. `planner next` reads it: an `assumption` without it still needs a Shape, and one with it is ready for a Grill. If a capture says "that's decided", add a "grill to confirm" note to the item. The item must pass grill's GATE-2 afterwards: at `assumption`, with a preferred option and the rejected options with their reasons. New items get the next free ID of their kind: grep the vault for the existing IDs of that kind, and also read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'` (`git show <branch>:sessions/<id>.md`), because another open session may already hold the next ID. Add one to the highest in use. Add one row to `## Changes` for each item whose state changed: `| ID | From | To | [[<id>#^cNN]] |`.

## 4. Draft the prose

Read `.claude/skills/planner/skills/house-voice/SKILL.md` and follow it for every paragraph this session needs. For a session whose `modes` include `epics`, each epic it drafted owes a description paragraph, so list those epics under "Prose drafted" in the PR body. The epics session already wrote each `**Owning team:**` line; close leaves it as written. Prose is drafted here and nowhere else. Commit the drafts on their own with the message `draft: prose for <id>`, so the reviewer's edits show as a diff.

### Voice review

A fresh reader checks the drafts, because the drafter cannot judge its own voice. Skip this part if the session drafted no paragraph, and go on to the part "Harvest the owner's edits".

1. List every paragraph in the `draft: prose for <id>` commit: a number, the page path, its voice type from house-voice's table, and the paragraph's text. Run `git status --porcelain` and keep the output.
2. Dispatch the `planner:voice-reviewer` subagent with the Agent tool, and give it the list. If the Agent tool lists no `planner:voice-reviewer`, dispatch a general-purpose subagent instead, and give it everything in `.claude/skills/planner/agents/voice-reviewer.md` after the frontmatter as its instructions, then the list, then this: you must not change any file, and you must report any file you changed. Never review the drafts yourself in this conversation. If no subagent can be dispatched, write "**Voice review:** not run: <the reason>" in the PR body and go on to the part "Harvest the owner's edits". The harvest does not depend on the review.
3. Run `git status --porcelain` again. If the output differs from step 1 of this part, the reviewer changed a file: stop and show the user. If the reviewer errored, or returned anything but the table, treat the review as not run, write "**Voice review:** not run: <the reason>" in the PR body, and go on to the part "Harvest the owner's edits". If it flagged no paragraph, skip steps 4 and 5 of this part: there is nothing to rewrite and no commit, so go on to the part "Harvest the owner's edits".
4. Rewrite each paragraph the reviewer flags once, in the working tree, from what it says differs. Do not send the rewrite back for review. A paragraph it did not flag stays as drafted. Note the pages you rewrote. Touch no other file. Before you rewrite a page, check it holds no uncommitted edit from sections 2 and 3, because a restore would discard that edit. For each `<page>`:

   ```
   git diff --quiet HEAD -- <page> || { git add -- <page> && git commit -qm "Checkpoint <id>" -- <page>; }
   ```

   This commits that page alone, with the message `Checkpoint <id>`, when it differs from HEAD. Then rewrite it, so `git restore -- <page>` returns the page to a state that already holds those edits.
5. Check only the pages you rewrote, one at a time, because the working tree also holds the work of sections 2 and 3 that is not committed. For each rewritten `<page>`:

   ```
   tmp=$(mktemp)
   git show HEAD:<page> > "$tmp"
   python3 .claude/skills/planner/bin/planner voicecheck "$tmp" <page>; code=$?; rm -f "$tmp"; (exit $code)
   ```

   voicecheck fails if a rewrite lost, added or moved a wikilink, code span, date, ID, number (with its units or currency), table cell, version, frontmatter line or negation.
   - Exit 0: keep the rewrite.
   - Exit 1: run `git restore -- <page>`. That discards every rewrite on that page and keeps its earlier draft whole. Run it for no other file.
   - Exit 2: show the error, then run `git restore -- <page>` so the unchecked rewrite stays out of the work that section 7 stages. Never commit a rewrite voicecheck could not check.

   Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`, staging each page by exact path.

### Harvest the owner's edits

Only the vault's owner harvests, and only their own edits. The owner is the `author` of the `source: owner` examples in `voice/examples/` and `voice/local/`. If there are none, say "No owner examples yet, so nothing to harvest. `/planner:voice-seed` adds them." and go on to section 5, Read back decided wording. Harvest does not depend on the voice review: run it even when the review did not run.

Each command runs in its own shell call, and no shell variable survives from one call to the next. So each paragraph's text is kept in a file with a fixed path every later step names: `.git/planner-harvest/<pr>-<n>.txt`, where `<pr>` is the PR number and `<n>` is the paragraph's order in this harvest, from 1. It sits inside `.git`, so it never shows in `git status` and is never staged. When harvest ends, by any route, run `rm -rf .git/planner-harvest`.

Every `gh` or `git` call below can fail. When one does, say which call failed and what it left unchecked. Never read a failure as "no edits found". Say "no edits found" only when every merged PR was checked.

1. Get the user's handle with `gh api user -q .login`. If `gh` fails, say "gh could not read your handle, so nothing was harvested." and go on to section 5, Read back decided wording. If the handle is not the owner's handle without the `@`, say "Harvest is owner-only." and go on to section 5, Read back decided wording.
2. List the user's merged session PRs: `gh pr list --state merged --search "head:session/" --author @me --json number,headRefName --limit 10`. If `gh` fails, say "gh could not list merged PRs, so nothing was harvested." and go on to section 5, Read back decided wording. If it returns 10 PRs, say "10 merged PRs came back, so older PRs were not checked."
3. Take one PR at a time, because `FETCH_HEAD` holds only the last fetch. Run `gh pr view <number> --json commits`, which lists each commit's `oid`, `messageHeadline` and `messageBody`, and `git fetch origin pull/<number>/head`. If `gh` fails, say "gh could not read the commits of PR <number>, so its edits were not checked." and go to the next PR. If the fetch fails, say "git could not fetch PR <number>, so it was not checked." and go to the next PR. Then:
   - Keep the commits whose `messageHeadline` starts `draft: `, both `draft: prose for` and `draft: voice rewrite for`. Skip the PR if there are none.
   - For each, list its pages with `git diff-tree --no-commit-id --name-only -r <oid>`. For each page, the baseline is the last draft commit in the PR's list that touched it.
4. For each page of the PR:
   - Run `git log --format=%H <baseline>..FETCH_HEAD -- <page>` and keep the commits that are in the PR's list. Drop each one whose `messageHeadline` starts with `draft: `, `Checkpoint ` or `Close session `, and each one whose `messageBody` carries a `Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer. Those are the skill's own commits. Drop a merge commit too. If none remain, the owner did not edit the page, so skip it.
   - For each remaining commit, run `git diff -U0 <oid>^ <oid> -- <page>`. Never compare the baseline with the tip, because the tip also holds section 3's content. The added lines are the owner's edit. Find the paragraph of `git show FETCH_HEAD:<page>` that holds them. If a later commit removed them, skip. The draft paragraph is the one in its place in `git show <oid>^:<page>`. Read the merged text from `FETCH_HEAD`, never from `origin/main`.
   - Extract the merged paragraph into its file, and hash it, in one call:

     ```
     mkdir -p .git/planner-harvest
     git show FETCH_HEAD:<page> | sed -n '<first>,<last>p' > .git/planner-harvest/<pr>-<n>.txt
     shasum < .git/planner-harvest/<pr>-<n>.txt | cut -c1-12
     ```

   - Skip a paragraph that is already saved or declined, and run `rm -f .git/planner-harvest/<pr>-<n>.txt`. It is saved when an example in either folder has the same `page`, a `harvested_from` equal to the baseline's full hash, and a body equal to the merged paragraph. It is declined when `grep -rh '^Harvest declined: ' sessions/` has its line: `Harvest declined: PR <number> <page> <hash>`.
5. Offer each remaining paragraph, one at a time. Show the draft paragraph, the file `.git/planner-harvest/<pr>-<n>.txt` and the voice type from house-voice's table, so the text is never retyped. Harvest offers and never saves by itself. Ask "Did you write this change?" The owner's answer is the check that the edit is theirs. If the answer is unclear, ask once more. If it is no, or still unclear, record a decline, run `rm -f .git/planner-harvest/<pr>-<n>.txt`, and do not ask the save question. Otherwise ask "Save the merged paragraph as a <type> example?" Save it only on an explicit yes. On any other answer, record a decline and run `rm -f .git/planner-harvest/<pr>-<n>.txt`. To record a decline, insert one bare line `Harvest declined: PR <number> <page> <hash>` directly under `## Captures` in the session record. It is never a bullet.
6. Ask where it goes, and say plainly that a committed example is pushed in this PR, where everyone with access to the repository can read it:
   - committed: `voice/examples/<type>/`. Ask "May this text be committed to the vault?" and wait for an explicit yes.
   - local only: `voice/local/<type>/`. It stays on this machine and no step below stages it.

   If the owner's employer owns the text, or the owner is not sure, recommend local only. If the answer is not an explicit choice, do not save, and run `rm -f .git/planner-harvest/<pr>-<n>.txt`.
7. Plan the room before you save, and change no example yet. A type keeps at most 5 active examples. Count both folders together, with the new one. If that makes 6, plan to retire one: the oldest `public-seed` example first, then the oldest `owner-edit`, then the oldest `owner`, by `added` and then file name. A local example never retires a committed seed, and in a local-only save only local examples may retire. If the cap blocks a local-only save, store nothing, run `rm -f .git/planner-harvest/<pr>-<n>.txt`, and say "The cap blocks a local save: <type> holds 5 active examples and none in voice/local/ may retire." Show the owner each planned retirement and ask. If they refuse, store nothing for that type, and run `rm -f .git/planner-harvest/<pr>-<n>.txt`.
8. Save the merged paragraph word for word as `<folder>/<type>/VX-<type>-NNN.md`, NNN one higher than the highest in that type in both folders, retired files included. First write the frontmatter with the Write tool, quoting every free value, ending with the closing `---` and one blank line:

   ```
   ---
   id: VX-<type>-NNN
   voice_type: <type>
   source: owner-edit
   author: "@<handle>"
   page: '<page path>'
   harvested_from: '<full hash of the baseline draft commit>'
   state: active
   added: <today>
   ---

   ```

   Then append the paragraph's file and compare it with the stored body, with a tool, in one call. The block removes the file whatever `cmp` finds:

   ```
   cat .git/planner-harvest/<pr>-<n>.txt >> <file>
   awk 'body { if (first && $0 == "") { first = 0; next } first = 0; print; next } $0 == "---" && ++n == 2 { body = 1; first = 1 }' <file> | cmp - .git/planner-harvest/<pr>-<n>.txt; code=$?; rm -f .git/planner-harvest/<pr>-<n>.txt; (exit $code)
   ```

   If `cmp` reports a difference, stop, tell the owner, and do not repair the file. Then re-read the frontmatter and confirm it parses as YAML and that `page` and `harvested_from` hold the text you gave. Only now apply the retirements you planned in step 7, changing only each `state:` line. If the save made a folder's active `owner` and `owner-edit` examples of the type 2 or more, retire that folder's active `public-seed` examples of the type the same way, as `/planner:voice-seed` does. A local save retires only local seeds. Retire by editing `state:` and never delete an example.

## 5. Read back decided wording

For each item that became `decided` in this session, show its final wording. If its owner is present, they confirm it. If not, list it in the PR body for them.

## 6. Render and check

Run `python3 .claude/skills/planner/bin/planner render`, then `python3 .claude/skills/planner/bin/planner check`. Fix each error with the user. If the user leaves an error in place, put it in the PR body. CI will block the merge until it is fixed.

## 7. Finish the record

If this session set `handed_off:` on an app page, run `python3 .claude/skills/planner/bin/planner handoff <APP-id>` now. It writes `handoffs/<APP-id>.md`, the record of what the senior accepts. If the manifest already exists, the senior is accepting changes: run it with `--replace` only once they say so in this session.

Stage every file `planner render` reported, any manifest `planner handoff` wrote, every example harvested or retired in `voice/examples/`, plus the session record and the changed pages, by exact path. Never stage anything in `voice/local/`. Never use `git add -A`. Before pushing, `git status --short` must show nothing modified. A rewritten block left out of the commit fails CI's render check. Draft a one-line `summary:` and let the user accept or edit it. Set `status: closed`, then stage. Commit with the message `Close session <id>`. Run `git push -u origin session/<id>`. If the push fails, show the error, print the commands for the user to run, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the PR

Collect the reviewers:

- the `owner:` of each app page this session changed;
- the `owner:` of each consumer app of a contract this session changed.

Get the user's own handle with `gh api user -q .login`. Strip the leading `@` from each individual handle. A team handle `@org/team` is passed as `org/team`. Drop the user's own handle. If nobody remains, leave out `--reviewer`.

Write the PR body to a temporary file. Fill the headings of the vault's PR template:

- **What changed.** The promoted items, each with its new state. Then these lists, each with "none" when empty:
  - **Prose drafted:** each paragraph in the `draft: prose for <id>` commit, page by page.
  - **Voice review:** each paragraph the reviewer flagged, what it said, and whether it was rewritten or kept because voicecheck named a changed token; or "not run: <reason>".
  - **Voice examples:** each example harvested or retired. Name a local example only as a count, never by its text. Add each PR harvest could not check, and why, and say when the PR limit hid older PRs.
  - **Decided wording not yet read back:** each `decided` item whose owner was not present in section 5.
  - **Promoted on a nod:** every item kept or promoted from a capture whose origin starts with `claude`, not only the deciding capture, with the capture quoted.
  - **Changed contracts:** each contract, and for each consumer, who was asked: present, async, in this PR, or "not consulted: <reason>".
  - **Overdue unknowns:** each `W705` line from section 6, with its owner @-mentioned.
  - **May still say the old value:** for each `decided` or `fact` value this session changed, run `grep -rn -F "<old wording>" --include='*.md' . | grep -v '^./sessions/'` and list every hit.
  - **Check:** the first line of the check output, and any error left in place.
- **Minutes.** Ask the user how long the session took.
- **Structural fixes** and **Prose edits.** Write "Filled in by the reviewer."

Then run the command below, with one `--reviewer` per remaining reviewer (none, if nobody remains). `<Mode name>` is the display name in `MODES.md`.

```
gh pr create --base main --head session/<id> --title "<date> <Mode name>: <topic>" --body-file <file> --reviewer <handle> --reviewer <org/team>
```

If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL. Show the URL.
