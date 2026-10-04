---
name: voice-seed
description: Seed an initiative vault's house voice with the owner's own writing. The owner pastes 2 or 3 passages per voice type (diagnosis, decision, how-it-works). The skill stores them word for word in voice/examples/ with source owner, retires the public seed examples of each type the owner filled, and opens a PR. Use when the owner wants drafts to sound like them.
argument-hint: "[diagnosis | decision | how-it-works]"
disable-model-invocation: true
---

# Voice seed

The vault's prose is drafted from `voice/examples/`. This skill puts the owner's own writing there, so drafts sound like the owner instead of the public seed. It stores the owner's words exactly as pasted. It never rewrites them.

An example's format is in `CONVENTIONS.md` under "Voice examples".

## 1. Start clean

Run step 1 of `.claude/skills/planner/references/START.md`: show the state of the clone, stop on any changed or untracked file, and pull `main`. Then run `git switch -c voice/seed-<today>`. If that branch exists locally or on `origin`, add `-2`, then `-3`, until it is free.

## 2. Who the owner is

Get the user's handle with `gh api user -q .login`. If `gh` fails, ask the user for it. The owner is that handle, with an `@` in front. Every example this skill writes carries it as `author`.

## 3. Collect the passages, one voice type at a time

Take the voice type the user named, or all three in this order: diagnosis, decision, how-it-works. For each type:

1. Say what the type is for, from the table in `.claude/skills/planner/skills/house-voice/SKILL.md`. Diagnosis says why something hurts now, as on the goals page. Decision says what was chosen and why, as in the strategy, the ADRs and the capability delta. How-it-works says how a system behaves, as on the context, app, runtime, flow and concern pages.
2. Ask the owner to paste 2 or 3 passages of their own writing of that type, one at a time. Each should be one or two paragraphs, about 80 to 300 words, from something they wrote themselves.
3. For each passage, ask two questions and wait for an explicit yes to each:
   - "Did you write this yourself?"
   - "May this text be committed to the vault, where everyone with access to the repository can read it?"
   If either answer is anything but yes, do not store the passage, and say so.
4. Store an accepted passage as it was pasted. Do not fix its spelling, punctuation or grammar, do not shorten it, and do not tidy its line breaks. If it is under 80 or over 300 words, say so once, and store it anyway if the owner says yes.
5. Ask where it comes from, in a few words, for the `from` field: for example "design review for the 2025 payments move". Leave out anything the owner does not want recorded.

Stop asking for a type once it has 3 passages, or when the owner says they have no more.

## 4. Write the examples

Write each passage to `voice/examples/<type>/VX-<type>-NNN.md`. NNN is one higher than the highest number in that folder, retired files included, in three digits.

```
---
id: VX-<type>-NNN
voice_type: <type>
source: owner
author: "@<handle>"
from: "<where it comes from>"
state: active
added: <today>
---

<the passage, exactly as pasted>
```

## 5. Retire the public seed of each type the owner filled

A type the owner gave at least 2 passages now has the owner's own examples. Set `state: retired` on every `source: public-seed` example of that type, so house-voice stops reading them and the owner's examples take precedence. Change only the `state:` line. Never delete a seed example: its licence and attribution stay in the file.

A type with fewer than 2 owner passages keeps its seed. Say: "<type> has one owner passage, so house-voice still reads the public seed. Add another to replace it."

Then count the active examples of each type. A type holds at most 5. If it has more, retire the oldest by `added` and then by file name, `public-seed` examples first, until 5 remain.

## 6. Commit and open the PR

Stage each example you wrote or retired, by exact path. Never use `git add -A`. Commit with the message `voice: owner examples for <types>`. Run `git push -u origin voice/seed-<today>`. If the push fails, show the error, print the commands for the user to run, and stop.

Write the PR body to a temporary file: each example added, with its type and `from`; each example retired; and each type that kept its seed. Run `gh pr create --base main --head voice/seed-<today> --title "Voice: owner examples" --body-file <file>`. If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL.

## Never

- Never rewrite, shorten, correct or paraphrase the owner's words.
- Never store a passage the owner did not write, or one they did not clear for the repository.
- Never write under `voice/corpus/`. It is gitignored reading material, not examples.
- Never edit a file outside `voice/examples/`.
