---
name: proposals
description: Review a reader's proposal as the owner, walking each change to accept, reject or edit it, and write the answer. Use when a reader sends a proposal folder or zip.
argument-hint: "review <proposal folder, .zip or changes.patch>"
disable-model-invocation: true
allowed-tools: Read Edit Bash(python3 *scripts/planner *)
---

# Review a reader's proposal

A reader worked in a published copy and sent changes. You are the owner, so you decide each one. The reader's changes are applied on their own branch in a git worktree beside your checkout, so nothing you are working on moves.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). The format is in `CONVENTIONS.md`; read the section a step names with `planner conventions "<section>"` (`--list` names them all), never the whole file.

## Reviewing

$ARGUMENTS

## 1. Start

Run `planner role`. Only an owner reviews: in a reader copy, say "Reviewing is the owner's job and needs the vault's git repo" and stop. Ask for the proposal if none was given. Do not search the disk for one.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner proposals review "<proposal>"` from the vault. Add `--slug <name>` or `--worktree <folder>` only if the user asks. It checks that the commit the reader worked from exists in this clone, stops on a checkout with uncommitted files and says which, makes the worktree and branch, applies the changes with `git apply --3way`, and commits them as `Proposal: <title> (from <author>)`.

Tell the user in plain words what it printed:
- If it stopped (a base commit this clone lacks, a dirty checkout, a branch that exists, a damaged patch), say why in one sentence and what to do. Do not work around a stop by hand; fix its cause or ask the owner.
- If the vault moved since the reader's copy, say by how many commits. It is a warning, not a stop.
- **Conflicts:** the files hold conflict markers in the worktree. Walk the user through each conflicted file: show both sides, ask which text wins or what the merged text says, edit the worktree file, then stage each conflicted file by exact path (`git -C <worktree> add -- <file>`) and commit with `git -C <worktree> commit -m "Resolve proposal conflicts"`. Do this before anything else.
- **Check:** compare its counts with the proposal's claim. If the reader's copy had errors, show them first. They do not decide the review; the owner does.

## 2. Walk the changes

Read `proposal.md` in the proposal folder (for a zip, the tool read it; show the reader's text from the review output and the worktree). Walk the groups in the order the tool listed: pending decisions first, then the rest. For each group:

1. Say what it is, and read out the reader's why before the diff. "No reason given" is said as it stands.
2. Show the change: the text now on the branch, and what it replaced (`git -C <worktree> show HEAD` or the hunk named in `proposal.md`). Plain words, not diff syntax.
3. Ask: accept, reject, or edit? The owner always decides. Never recommend an outcome on a pending decision, and never decide for them.
   - **Accept.** A pending decision: ask for the owner's handle if you do not have it, then run `planner proposals accept --vault <worktree> --item <ID> --by @<owner>`. It removes the marker, records `**Decided by:** @<owner>` as the owner's decision, adds a `**Credit:**` line for the reader to History, and commits. An ordinary change is already on the branch; there is nothing to run.
   - **Reject.** Ask why, in the owner's own words (the reader will read it). Never write the reason yourself. Run `planner proposals reject "<proposal>" --vault <worktree> --group <key> --reason "<their words>"`. If it cannot take the change out because the pages moved, say so, and edit the file with the owner instead.
   - **Edit.** The owner says what the text should be; edit the worktree file with them, commit it (`git -C <worktree> commit -am "Edit <key> from the proposal"`), and for a pending decision run `planner proposals accept` afterwards so the marker goes and the reader is credited. Ask for a one-line note of what they changed; the reader reads it.
4. Keep a note of the outcome and the owner's reason for each group.

Two rarer cases are under "Special cases" at the end.

## 3. Check and answer

Run `planner render` then `planner check` in the worktree. If render changed files, commit them. Show the final counts.

Write the answer from the notes. Pass them on standard input so the owner's words need no escaping. Every group needs an entry; `rejected` and `edited` need a reason:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner proposals answer "<proposal>" --vault <worktree> --decisions - <<'JSON'
[{"group": "CON-001", "outcome": "accepted"},
 {"group": "CON-002", "outcome": "rejected", "reason": "<the owner's words>"}]
JSON
```

It writes `answer.md` into the proposal folder (beside a zip, or beside a bare patch). It stops on a group with no decision, a rejection with no reason, and any line that holds a private path. Tell the owner where it is. They send it to the reader; the tool sends nothing.

## 4. The branch

The work is on `proposal/<slug>`. Offer the owner their normal git steps and print the commands, for example `git switch main && git merge proposal/<slug>`, or `git push -u origin proposal/<slug>` and a PR as `/planner:close` opens one. Run a local merge only if they say so. **Never push, and never open a PR yourself.** Remind them that `git worktree remove <worktree>` tidies up once the branch is merged, and that a new published copy is how the reader continues.

## Special cases

If the owner wants to accept something a rule forbids, such as a check error or a decision made without a Grill, they may: record it as an `**Override:**` on the item, as `planner conventions "Overrides"` says, with their handle, today's date and their reason. Never block it, never hide it.

If a reader changed the words of an item that was already `decided` (not one they decided themselves), and the owner does not want to settle it now, do not leave it quietly decided. Record a blocking unknown as `/planner:challenge` section 4 does, with the reader as its owner and `**Blocks:**` the item, and commit it on the branch. `planner check` then shows E316 until an answer session (`modes: [answer, grill]`, `START.md` "Answer a challenge") settles it.

## Never

- Never accept, reject or edit a change the owner did not decide in this session.
- Never write the owner's reason for them.
- Never push, merge or open a PR for them.
- Never hand-edit the proposal folder's `changes.patch` or `proposal.md`.
