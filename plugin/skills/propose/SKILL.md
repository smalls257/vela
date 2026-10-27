---
name: propose
description: "Turn what you drafted in a read copy into a proposal folder for the owner, with your reasons. Offer it when someone has changes to send and no git; start it only on a yes."
argument-hint: "[a few words naming the proposal]"
allowed-tools: Read Bash(sh *scripts/run-vela *)
---

# Propose your changes to the owner

A reader has no git, so a change reaches the plan as a proposal the owner reviews. This skill turns what you drafted since opening the copy into a folder: `proposal.md` (the note the owner reads) and `changes.patch`. It doesn't send anything; you send the folder however you normally send files.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). Run it from the workspace folder. When a command can't express what the user wants, say so and stop.

Before your first question, read how to talk, as `START.md` step 0 says: `voice/VOICE.md` first when the copy has one (the owner's own rules win), then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` and the examples it names. Don't tell the user you read them.

## Proposing

$ARGUMENTS

## Steps

1. Run `vela role`. If it says `owner`, stop: "You work in this plan's git repo, so you decide directly. A proposal is how someone without git sends changes." Offer a normal session instead. If it says neither owner nor reader, say in one plain sentence that this folder isn't a plan or a reader copy, and stop.
2. Run `vela propose --groups --json`. If nothing changed, say so and stop. Otherwise say how many things they changed, in plain words, pending decisions first: a decision they recorded that the owner decides, not them.
3. For each group, one at a time, in the tool's order, by the item's name (the group key goes only into the command):
   - Read the page around the change (`path` and `hunk`) to say what changed in a sentence, and ask why, offering a draft reason they can correct: "You changed the Record consent contract to record consent before the first message. Is the reason that finance said anything else fails audit?" Once they accept it, use their words. Groups that are one change in their mind get one question, so twelve groups are not twelve questions.
   - A skipped question, "not sure", or silence is fine: leave that group out, and the proposal says "no reason given". Never write a reason the user did not give or accept, and never hold the proposal back for one.
4. Ask for a title of a few words, unless they gave one, offering one drawn from the changes.
5. Make a folder, unless they asked for a zip (`--zip`).
6. If they had a session of their own in this copy, ask: "Do you want to send your session notes along? They're your own words from the conversation, and by default they stay on this computer." Only a plain yes attaches them, and then you add `--with-record <session id>`. A no, or no answer, sends the changes without them.
7. Run it with the reasons on standard input (no escaping needed), keyed by the group keys from step 2 exactly, a group with no reason left out:

```
sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela propose --title "<title>" --whys - [--zip] [--with-record <session id>] <<'JSON'
{"CON-001": "<their reason>", "CON-002": "<their reason>"}
JSON
```

8. Say what it printed in your own words: where the proposal is, what to send and to whom. Errors from their copy's check are listed first in the proposal and didn't stop it; the owner decides about them. The owner's answer comes back as `answer.md`, with a new published copy to open and continue from.
9. If it stopped on a private path (a home folder, the place the copy was opened from), show that line. If it is in a session's notes, run again with `--rewrite-home` and say so: the proposal says `<home>` there, and their own files don't change.

## Never

- Never attach the session notes without a yes in this conversation.
- Never send, email, upload or share the proposal. Say where it is and stop.
- Never edit the pages in the workspace, and never run `git` or `gh`.
- Never invent a reason, a title the user did not accept, or an owner's name; use what the tool printed.
