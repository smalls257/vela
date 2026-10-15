---
name: voice-seed
description: Store the owner's own writing as the voice samples that drafts and sessions are written from. Use when the owner wants drafts and conversations to sound like them.
argument-hint: "[diagnosis | decision | how-it-works | conversation]"
disable-model-invocation: true
---

# Voice seed

This skill stores the owner's own writing in `voice/examples/` or `voice/local/`, so drafts sound like the owner instead of the built-in samples. It never rewrites them. Vela does the files: relay its plain lines and ask the owner what it hands you. When a command can't do what the owner wants, say so plainly and stop; never write, retire or count the files by hand.

The argument values are the type names the commands take. Say them in words: `diagnosis` is why something hurts now (the goals page), `decision` is what we chose and why (the strategy, decision records, the capability delta), `how-it-works` is how a system behaves (the context, app, runtime, flow and concern pages), and `conversation` is how sessions talk to the lead. A run with no type named does the first three in that order, then offers conversation and `voice/VOICE.md`.

## 1. Start

Run steps 0 and 1 of `${CLAUDE_PLUGIN_ROOT}/references/START.md` (how to talk: `voice/VOICE.md` when it exists, then `CONVERSATION-VOICE.md`; then the state of the clone). Run `vela whoami --json`: its handle, with an `@` in front, is the owner and every sample's author. On exit 3, ask its question once and run `vela whoami --set <handle>`.

Vela saves a passage only against the owner's yeses written in an open session record. Run `vela session open --switch --for-lead`. With several open, ask which and run it again with `--id <id>`. With none, say: "Saving a sample needs an open session to write your yeses into, and none is open. Start the session you were going to run next, then type `/vela:voice-seed` in it." Stop there.

## 2. Where the samples go

In a reader copy (no `.git`), only the local-only place is open: say so, and never offer the committed place or a branch.

Otherwise say plainly: "`voice/examples/` is committed, pushed and opened as a PR, so anyone with access to this repository can read what goes there." Then offer:

- committed: `voice/examples/<type>/`, for everyone, through a PR.
- local only: `voice/local/<type>/`: this machine only, gitignored, never committed. On this machine drafts read these first.

If the owner says their employer owns the text, or is not sure, recommend local only. A local-only run changes no committed file and makes no branch, commit or PR. Say so. A local example never retires a committed seed, so teammates keep their samples.

## 3. Collect the passages, one type at a time

1. Say what the type is for, in the words above.
2. Ask for 2 or 3 passages of the owner's own writing of that type, one at a time, each one or two paragraphs.
3. For each passage, ask and wait for an explicit yes to each, as its own question:
   - "Did you write this yourself?"
   - committed only: "May this text be committed to the plan, where everyone with access to the repository can read it?"

   Capture each answer in the owner's words: `vela record add '"<their words>"' --origin @<handle> --tag instruction --mark "drop: consent to store"` (`"drop: consent to commit"` for the second). Keep the number it prints. Anything but yes: do not store the passage, and say so.
4. Ask where it comes from, in a few words ("design review for the 2025 payments move"), leaving out anything the owner does not want recorded.

Stop at 3 passages, or when the owner has no more.

### The conversation type

`/vela:voice-seed conversation` runs it alone. The owner pastes 2 or 3 exchanges they liked, a few turns as they were, speakers marked as the paste marks them. The first question becomes "Is this an exchange you were part of, and are you happy for it to be kept?"; the commit question is the same. Vela names the files `VX-conversation-NNN.md` and skips the length note. With fewer than 2 conversation samples, sessions use the written rules alone.

### The owner's own rules

Offer once: "Do you want to start `voice/VOICE.md`, your own rules for how pages read or how sessions talk, in your words?" It is optional; the defaults already spell in American English, and the owner can change that here. Take each rule as the owner states it, one at a time, never reworded and never invented by you; you may offer a rule as a question and write it only when they say yes in their own words. Put them under `## Pages` and `## Conversation`. Append; never delete or rewrite a line already there. It is committed: same plain words, same yes.

## 4. Save each one

Write the passage to a file exactly as pasted, with a quoted heredoc so nothing expands:

```
cat > .vela/voice-passage.md <<'VELA_EOF'
<the passage, exactly as pasted>
VELA_EOF
```

If the passage contains a line `VELA_EOF`, pick another delimiter and use it in both places. A heredoc always ends its text with a newline, so a paste that had no final newline gains one. When the paste had none, tell the owner. Vela's compare proves the file holds what the heredoc received. It does not prove the chat text reached the heredoc unchanged. Store an accepted passage as it was pasted.

Before the yeses, run `vela voice plan --type decision --place committed --from .vela/voice-passage.md --for-lead`, with this run's type and place, and handle what it says, one question at a time:

- a line that is exactly `---` or a generated-block marker: say which line and that tools may read it as a boundary, and ask. Store it only on an explicit yes, and never rewrite the line.
- short or long: say it once; store it anyway if the owner says yes.
- exit 3, a retirement the cap forces: a type holds at most 5. Say which sample would retire and ask. The owner may refuse. If they refuse, store nothing new for that type and say why. Capture a yes like the others, marked `"drop: consent to retire"`.
- exit 1: the type is full and nothing may retire. Say so and go on.

Then run `vela voice save --from .vela/voice-passage.md --type decision --place committed --consent ^c<N> --commit-consent ^c<M> --author @<handle> --where '<from>' --for-lead`, again with this run's type and place, with `--retire-consent ^c<K>` for a forced retirement, and with no `--commit-consent` for `--place local`. Relay its lines. If it stops for a missing yes, ask for it; never pass another capture in its place. Exit 2 means the stored file differs from the passage: tell the owner and never repair it. Then run `rm -f .vela/voice-passage.md`.

The owner's second sample of a type retires the built-in ones in that folder. A type with fewer than 2 owner passages keeps its seed; say it in words: "I have only one sample of how you explain how things work, so drafts still follow the built-in samples. Add one more to switch to yours."

## 5. Commit and open the PR

If nothing committed changed, say: "Local only: no branch, commit or PR." Stop here.

Otherwise the samples ride the open session's branch: run `vela close stage --checkpoint --for-lead`, which stages `voice/examples/` and `voice/VOICE.md` by exact path with the session record, leaves `voice/local/` out, and commits. Never stage or commit by hand. The push and the pull request go with that session's close, which says what it will send and waits for the owner's yes; tell the owner so. For its PR body, name each committed sample added with its type and `from`, each retired, and each type that kept its seed. Name local examples only as a count, never their text or `from`. Never say a PR exists unless `gh` printed its URL.

## Never

- Never rewrite, shorten, correct or paraphrase the owner's words.
- Never store a passage the owner did not write. Never commit one they did not clear for the repository.
- Never write under `voice/corpus/`. It is gitignored reading material, not examples.
- Never edit a file outside `voice/examples/`, `voice/local/`, `voice/VOICE.md` and the session record.
- Never invent a rule for `voice/VOICE.md`. Its lines are the owner's words.
