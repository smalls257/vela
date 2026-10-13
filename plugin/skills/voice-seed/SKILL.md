---
name: voice-seed
description: Seed an initiative vault's voices with the owner's own writing. The owner pastes 2 or 3 passages per page voice type (diagnosis, decision, how-it-works), or 2 or 3 exchanges they liked for the conversation voice (conversation). The skill stores them word for word in voice/examples/ with source owner, retires the public seed examples of each type the owner filled, and opens a PR. Use when the owner wants drafts to sound like them.
argument-hint: "[diagnosis | decision | how-it-works | conversation]"
disable-model-invocation: true
---

# Voice seed

The vault's prose is drafted from `voice/examples/` and `voice/local/`. This skill puts the owner's own writing there, so drafts sound like the owner instead of the public seed. It stores the owner's words exactly as pasted. It never rewrites them.

An example's format is in `CONVENTIONS.md` under "Voice examples".

There are two voices. The page voice (`diagnosis`, `decision`, `how-it-works`) is what the tool writes; `house-voice` reads those examples. The conversation voice (`conversation`) is how sessions talk to the lead; `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` reads those. `/planner:voice-seed conversation` runs the conversation type alone. A run with no type named does the three page types, and offers conversation and `voice/VOICE.md` at the end.

## 1. Start clean

Run step 1 of `${CLAUDE_PLUGIN_ROOT}/references/START.md`: show the state of the clone, stop on any changed or untracked file, and pull `main`. Do not create a branch yet. Step 7 does that, and only if something committed changes.

## 2. Who the owner is

Get the user's handle with `gh api user -q .login`. If `gh` fails, ask the user for it. The owner is that handle, with an `@` in front. Every example this skill writes carries it as `author`.

## 3. Collect the passages, one voice type at a time

In a reader copy (no `.git`), only the local-only place is open: say so, and never offer the committed place or a branch.

First say this plainly: "`voice/examples/` is committed, pushed and opened as a PR, so anyone with access to this repository can read what goes there." Then offer two places for the run:

- committed: `voice/examples/<type>/`. The passages go through a PR.
- local only: `voice/local/<type>/`. They stay on this machine, are gitignored, and are never committed.

If the owner says their employer owns the text, or is not sure, recommend local only. A local-only run changes no committed file and makes no branch, commit or PR. Say so. A local example never retires a committed seed: that would drop every teammate's house voice below 2 examples of the type. On this machine, house-voice reads local owner examples ahead of the committed seed. Create `voice/local/<type>/` when it does not exist.

Take the voice type the user named, or the three page types in this order: diagnosis, decision, how-it-works. The `conversation` type is taken when it is named or when the owner accepts the offer at the end. For each type:

1. Say what the type is for, from the table in `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md`. Diagnosis says why something hurts now, as on the goals page. Decision says what was chosen and why, as in the strategy, the ADRs and the capability delta. How-it-works says how a system behaves, as on the context, app, runtime, flow and concern pages. Conversation is the one type that is an exchange, not a page: see "The conversation type" below.
2. Ask the owner to paste 2 or 3 passages of their own writing of that type, one at a time. Each should be one or two paragraphs, about 80 to 300 words, from something they wrote themselves.
3. For each passage, ask and wait for an explicit yes to each:
   - "Did you write this yourself?"
   - For the committed place only: "May this text be committed to the vault, where everyone with access to the repository can read it?"

   If an answer is anything but yes, do not store the passage, and say so.
4. Take everything after the frontmatter's closing `---` as the body. If the passage has a line that is exactly `---`, or contains `<!-- generated:`, tell the owner which line it is and that tools may treat it as a boundary or a generated block. Ask whether to go ahead. Store it only on an explicit yes, and never rewrite the line.
5. If a passage is under 80 or over 300 words, say so once. Store it anyway if the owner says yes.
6. Ask where it comes from, in a few words, for the `from` field: for example "design review for the 2025 payments move". Leave out anything the owner does not want recorded.

Stop asking for a type once it has 3 passages, or when the owner says they have no more.

Before storing a type, make room for it:

1. List the type's active examples in `voice/examples/` and `voice/local/`, with the passages about to be added.
2. Count only within a folder. A `public-seed` example retires when the active `owner` and `owner-edit` examples in its own folder, after this run, number at least 2. So committed owner examples retire committed seeds, and local examples retire only local ones. In a local-only run, nothing in `voice/examples/` retires. Otherwise the type keeps its seed.
3. A type holds at most 5. Count both folders together. If the list still has more than 5, retire the surplus in this order: `public-seed` first, then `owner-edit`, then `owner`. Within each, the oldest `added` goes first, then the lowest file name. In a local-only run, only local examples may retire. If the list is still over 5, store nothing new for that type and say so.
4. Show the owner each retirement the cap forces and ask. The owner may refuse. If they refuse, store nothing new for that type and say why: a type holds at most 5.

Keep the plan of retirements for step 5.

### The conversation type

The owner pastes 2 or 3 exchanges they liked, from any session or chat: a few turns of the lead and the assistant, as they were, with the speakers marked the way the paste marks them. Ask for each, one at a time, an explicit yes to "Is this an exchange you were part of, and are you happy for it to be kept?" in place of "Did you write this yourself?", and for the committed place only, "May this text be committed to the vault, where everyone with access to the repository can read it?". Anything but yes means it is not stored. Exchanges run longer than a page passage: skip the 80 to 300 word note. The `from` field says where it came from in a few words. Fields, file naming (`VX-conversation-NNN.md`), the verbatim write and compare, the cap of 5 and the committed or local-only choice are exactly as for the other types. Conversation has no public seed, so nothing retires unless the cap forces it. With fewer than 2 active conversation examples the sessions use the written rules on their own, and the owner can add more at any time.

### The owner's own rules

After the types, offer once: "Do you want to start `voice/VOICE.md`, your own rules for how pages read or how sessions talk, in your words?" It is optional. If yes, ask which facet (pages, conversation or both) and take the rules the owner states, one at a time. Write each rule as the owner said it, never reworded and never invented by you; if you think of a rule they might want, you may offer it as a question and write it only when they say yes in their own words. Put the pages rules and the conversation rules under two headings, `## Pages` and `## Conversation`. Create the file if it does not exist, append to it if it does, and never delete or rewrite a line already there. `voice/VOICE.md` is committed, so say the same plain words about who can read it and ask for the same yes before it goes in the PR.

## 4. Write the examples

Write each passage to `<folder>/<type>/VX-<type>-NNN.md`, where the folder is `voice/examples` or `voice/local`. NNN is one higher than the highest number for that type in both folders, retired files included, in three digits. Write a file in three moves.

First, write the frontmatter with the Write tool. End it with the closing `---` and one blank line. Write `from` in single-quoted YAML, and double any `'` inside it:

````
---
id: VX-<type>-NNN
voice_type: <type>
source: owner
author: "@<handle>"
from: '<where it comes from>'
state: active
added: <today>
---

````

Second, append the pasted text exactly as given, with a quoted heredoc so nothing expands:

```
cat >> <file> <<'PLANNER_EOF'
<the passage, exactly as pasted>
PLANNER_EOF
```

If the passage contains a line `PLANNER_EOF`, pick another delimiter and use it in both places.

Third, compare the stored body with the pasted text, with a tool. Write the pasted text to a temp file with a second quoted heredoc. Extract the stored body, which is everything after the closing frontmatter `---` line and its one blank line. Compare the two with `cmp`:

```
tmp=$(mktemp)
cat > "$tmp" <<'PLANNER_EOF'
<the passage, exactly as pasted>
PLANNER_EOF
awk 'body { if (first && $0 == "") { first = 0; next } first = 0; print; next } $0 == "---" && ++n == 2 { body = 1; first = 1 }' <file> | cmp - "$tmp"; code=$?; rm -f "$tmp"; (exit $code)
```

Run the whole block in one call: the shell keeps no variable between calls, so `$tmp` exists only inside it. If `cmp` reports a difference, stop. Tell the owner and do not repair the file. A heredoc always ends its text with a newline, so a paste that had no final newline gains one in both files, and `cmp` will not show it. When the paste had none, tell the owner. The check proves the file holds what the heredoc received. It does not prove the chat text reached the heredoc unchanged. Store an accepted passage as it was pasted.

Then re-read the frontmatter and confirm it parses as YAML and that `from` is the text the owner gave.

## 5. Retire examples

Apply the plan from step 3. Set `state: retired` on each example in it. Change only the `state:` line. Never delete a seed example: its licence and attribution stay in the file. Retiring a committed example changes a committed file, so it goes through the PR in step 7. Retiring a local example needs no PR.

A type with fewer than 2 owner passages keeps its seed. A local-only run always leaves the committed seed in place. Say: "<type> has one owner passage, so house-voice still reads the public seed. Add another to replace it."

## 6. Final check

Re-read every file you wrote or changed. Confirm each frontmatter parses, then run this from the vault root. It prints a count per type and exits 1 if a type has more than 5 active examples or a file does not parse:

```
python3 - <<'PLANNER_EOF'
import glob, sys, yaml
active, bad = {}, []
for path in glob.glob("voice/examples/*/*.md") + glob.glob("voice/local/*/*.md"):
    try:
        meta = yaml.safe_load(open(path, encoding="utf-8").read().split("---\n", 2)[1])
        if meta["state"] == "active":
            active[meta["voice_type"]] = active.get(meta["voice_type"], 0) + 1
    except Exception as err:
        bad.append(f"{path}: {err}")
print(active, bad)
sys.exit(1 if bad or any(n > 5 for n in active.values()) else 0)
PLANNER_EOF
```

If it fails, say what failed and stop.

## 7. Commit and open the PR

If nothing committed changed, say: "Local only: no branch, commit or PR." Stop here.

Otherwise run `git switch -c voice/seed-<today>`. If that branch exists locally or on `origin`, add `-2`, then `-3`, until it is free. Stage each committed example you wrote or retired, and `voice/VOICE.md` if you changed it, by exact path. Never use `git add -A`. Commit with the message `voice: owner examples for <types>`. Run `git push -u origin voice/seed-<today>`. If the push fails, show the error, print the commands for the user to run, and stop.

Write the PR body to a temporary file: each committed example added, with its type and `from`; each example retired; and each type that kept its seed. Name local examples only as a count. Never put their text or their `from` in the PR. Run `gh pr create --base main --head voice/seed-<today> --title "Voice: owner examples" --body-file <file>`. If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL.

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded. Its hard stops still hold.

- Never rewrite, shorten, correct or paraphrase the owner's words.
- Never store a passage the owner did not write. Never commit one they did not clear for the repository.
- Never write under `voice/corpus/`. It is gitignored reading material, not examples.
- Never edit a file outside `voice/examples/`, `voice/local/` and `voice/VOICE.md`.
- Never invent a rule for `voice/VOICE.md`. Its lines are the owner's words.
