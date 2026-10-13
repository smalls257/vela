---
name: propose
description: Turn what you drafted in a read copy into a proposal folder for the owner, with your reasons. Use when you have changes to send and no git.
argument-hint: "[a few words naming the proposal]"
disable-model-invocation: true
allowed-tools: Read Bash(python3 *scripts/planner *)
---

# Propose your changes to the owner

A reader has no git, so a change reaches the vault as a proposal the owner reviews, never as an edited file. This skill turns what you drafted since you opened the copy into a folder holding `proposal.md` (the note the owner reads) and `changes.patch` (the changes themselves). It sends nothing: you send the folder, however you normally send files.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). Run it from the workspace folder.

## Proposing

$ARGUMENTS

## Steps

1. Run `planner role`. If it says `owner`, stop: "You work in this vault's git repo, so you decide directly. A proposal is how someone without git sends changes." Offer a normal session instead. If it says neither owner nor reader, show what it printed and stop.
2. Run `planner propose --groups --json`. If it says you have changed nothing, say so and stop. Otherwise tell the user how many things they changed, in plain words, pending decisions first. A pending decision is a decision they recorded that the owner has not yet approved; say that the owner decides it, not them.
3. For each group, one at a time, in the order the tool gave:
   - Read the page text around the change (the `path` and `hunk` say where) so you can say what changed in a sentence.
   - Ask why they changed it, and offer a draft reason in plain language that they can correct (for example, "Finance said anything else fails audit"). The reason is theirs: use their words once they accept the draft. When several groups are one change in the reader's mind, offer their reasons together, so twelve groups are not twelve questions.
   - A skipped question, "not sure", or silence is fine. Leave that group out of the reasons. The proposal will say "no reason given". Never write a reason the user did not give or accept, and never hold the proposal back for one.
4. Ask for a title of a few words, unless the user gave one. Offer a suggestion drawn from the changes.
5. Ask whether they want a folder or a single zip (a zip is easier to attach to an email).
6. Run the command with the reasons on standard input, so quotes and symbols in their words need no escaping:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner propose --title "<title>" --whys - [--zip] <<'JSON'
{"CON-001": "<their reason>", "CON-002": "<their reason>"}
JSON
```

   Keys are the group names from step 2, exactly. Leave out a group with no reason.
7. Tell the user what it printed: where the proposal is, what to send and to whom. If the check on their copy found errors, say they are listed first in the proposal and did not stop it: the owner decides what to do with them.
8. If it stopped because a line holds a private path, see "If it stops on a private path" below.
9. Tell them the owner's answer will come back as `answer.md`. When it does, the owner publishes a new copy and they open that to continue.

## If it stops on a private path

A line holds a private path (a home folder, the place the copy was opened from). Show that line and offer to reword it. If the line is in a session record and the user agrees, run again with `--rewrite-home`: the proposal then says `<home>` where the path was, and their own files are not changed. Never add that flag without their yes.

## Never

- Never send, email, upload or share the proposal. Say where it is and stop.
- Never edit the pages in the workspace, and never run `git` or `gh`.
- Never invent a reason, a title the user did not accept, or an owner's name; use what the tool printed.
