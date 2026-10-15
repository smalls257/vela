---
name: proposals
description: Review a reader's proposal as the owner, walking each change to accept, reject or edit it, and write the answer. Use when a reader sends a proposal folder or zip.
argument-hint: "review <proposal folder, .zip or changes.patch>"
disable-model-invocation: true
allowed-tools: Read Edit Bash(python3 *scripts/vela *)
---

# Review a reader's proposal

A reader worked in a published copy and sent changes. You are the owner, so you decide each one. The changes go on their own branch in a git worktree beside your checkout, so nothing you are working on moves.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). When a command can't express what the owner wants, say so and stop.

Before your first question, read how to talk, as `START.md` step 0 says: `voice/VOICE.md` first when the plan has one (the owner's own rules win), then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` and the examples it names. Don't tell the owner you read them.

## Reviewing

$ARGUMENTS

## 1. Start

Run `vela role`. Only an owner reviews: in a reader copy, say "Reviewing a proposal is the owner's job, and it needs the plan's git repo" and stop. Ask for the proposal if none was given. Do not search the disk for one.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela proposals review "<proposal>"` from the plan's folder (`--slug <name>` or `--worktree <folder>` only if the owner asks). It applies and commits the changes on a new branch and worktree. Relay what it printed in plain words:
- A stop (a base commit this clone lacks, uncommitted files, a branch that exists, a damaged patch): why, in one sentence, and what to do. Fix the cause or ask; never work around it by hand.
- The plan moved since the reader's copy: by how many commits. A warning, not a stop.
- **Conflicts:** before anything else, walk each conflicted file: show both sides, ask which text wins or what the merged text says, edit the worktree file, stage it by exact path (`git -C <worktree> add -- <file>`), then `git -C <worktree> commit -m "Resolve proposal conflicts"`.
- **Check:** compare its counts with the proposal's claim, showing errors from the reader's copy first. The owner, not the errors, decides the review.

## 2. Walk the changes

Read `proposal.md` (for a zip, the review output). Walk the groups in the order the tool listed: pending decisions first, then the rest. Say each by the item's name, in your own sentences too; the group key goes into commands, never into what the owner hears: "First change: the Record consent contract. Priya's reason: finance said anything else fails audit."

For each group:

1. Say what it is and the reader's why, before the change. "No reason given" is said as it stands.
2. Show the text now on the branch and what it replaced (`git -C <worktree> show HEAD`, or the hunk `proposal.md` names), in plain words, not diff syntax.
3. Ask: accept, reject, or edit? The owner always decides. Never recommend an outcome on a pending decision, and never decide for them.
   - **Accept.** A pending decision: with the owner's handle, run `vela proposals accept --vault <worktree> --item <ID> --by @<owner>`. It removes the marker, records the owner's decision, credits the reader in History, and commits. An ordinary change is already on the branch.
   - **Reject.** Ask why, in the owner's own words (the reader reads it). Never write the reason yourself. Run `vela proposals reject "<proposal>" --vault <worktree> --group <key> --reason "<their words>"`. If the pages moved and it can't take the change out, say so and edit the file with the owner.
   - **Edit.** Edit the worktree file with the owner, commit it (`git -C <worktree> commit -am "Edit <key> from the proposal"`), then for a pending decision run `vela proposals accept`. Ask for a one-line note of what they changed, for the reader.
4. Note the outcome and the owner's reason.

## 3. Check and answer

Run `vela render` then `vela check` in the worktree, commit what render changed, and say the final counts.

Write the answer from the notes, on standard input so the owner's words need no escaping. Every group needs an entry; `rejected` and `edited` need a reason:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela proposals answer "<proposal>" --vault <worktree> --decisions - <<'JSON'
[{"group": "CON-001", "outcome": "accepted"},
 {"group": "CON-002", "outcome": "rejected", "reason": "<the owner's words>"}]
JSON
```

It writes `answer.md` beside the proposal, and stops on a group with no decision, a rejection with no reason, or a line holding a private path. Tell the owner where it is. They send it; the tool doesn't send anything.

## 4. The branch

The work is on `proposal/<slug>`. Print the owner's normal git steps, for example `git switch main && git merge proposal/<slug>`, or `git push -u origin proposal/<slug>` and a PR as `/vela:close` opens one. Run a local merge only if they say so. **Never push, and never open a PR yourself.** Once it is merged, `git worktree remove <worktree>` tidies up, and the reader continues from a new published copy.

## Special cases

If the owner wants to accept something a rule forbids, such as a check error or a decision made without a grill, they may: record it as an `**Override:**` on the item, as `vela conventions "Overrides"` says, with their handle, today's date and their reason. Never block it, never hide it.

If a reader reworded an already decided item (not one they decided) and the owner won't settle it now, don't leave it quietly decided: record a blocking open question as `/vela:challenge` section 4 does, the reader as its owner and `**Blocks:**` the item, committed on the branch. `vela check` then shows E316 until an answer session (`modes: [answer, grill]`, `START.md` "Answer a challenge") settles it.

## Never

- Never accept, reject or edit a change the owner did not decide in this session.
- Never write the owner's reason for them.
- Never hand-edit the proposal folder's `changes.patch` or `proposal.md`.
