---
name: voice-seed
description: Seed an initiative vault's house voice with the owner's own writing. The owner pastes 2 or 3 passages per voice type (diagnosis, decision, how-it-works). The skill stores them word for word in voice/examples/ with source owner, retires the public seed examples of each type the owner filled, and opens a PR. Use when the owner wants drafts to sound like them.
argument-hint: "[diagnosis | decision | how-it-works]"
disable-model-invocation: true
---

# Voice seed

The vault's prose is drafted from `voice/examples/` and `voice/local/`. This skill puts the owner's own writing there, so drafts sound like the owner instead of the public seed. It stores the owner's words exactly as pasted. It never rewrites them.

An example's format is in `CONVENTIONS.md` under "Voice examples".

## 1. Start clean

Run step 1 of `.claude/skills/planner/references/START.md`: show the state of the clone, stop on any changed or untracked file, and pull `main`. Do not create a branch yet. Step 7 does that, and only if something committed changes.

## 2. Who the owner is

Get the user's handle with `gh api user -q .login`. If `gh` fails, ask the user for it. The owner is that handle, with an `@` in front. Every example this skill writes carries it as `author`.

## 3. Collect the passages, one voice type at a time

First say this plainly: "`voice/examples/` is committed, pushed and opened as a PR, so anyone with access to this repository can read what goes there." Then offer two places for the run:

- committed: `voice/examples/<type>/`. The passages go through a PR.
- local only: `voice/local/<type>/`. They stay on this machine, are gitignored, and are never committed.

If the owner says their employer owns the text, or is not sure, recommend local only. A local-only seed has no branch, commit or PR. Say so. Create `voice/local/<type>/` when it does not exist.

Take the voice type the user named, or all three in this order: diagnosis, decision, how-it-works. For each type:

1. Say what the type is for, from the table in `.claude/skills/planner/skills/house-voice/SKILL.md`. Diagnosis says why something hurts now, as on the goals page. Decision says what was chosen and why, as in the strategy, the ADRs and the capability delta. How-it-works says how a system behaves, as on the context, app, runtime, flow and concern pages.
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
2. The owner has 2 examples of a type when the count of active `owner` and `owner-edit` examples, across both folders, after this run, is at least 2. When that is true, every active `public-seed` example of the type retires. When it is not, the type keeps its seed.
3. A type holds at most 5. If the list still has more than 5, retire the surplus in this order: `public-seed` first, then `owner-edit`, then `owner`. Within each, the oldest `added` goes first, then the lowest file name.
4. Show the owner each retirement the cap forces and ask. The owner may refuse. If they refuse, store nothing new for that type and say why: a type holds at most 5.

Keep the plan of retirements for step 5.

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

Third, compare the stored body with the pasted text. Run `cat -A <file>` and read the body line by line against the paste. Look for a difference in line endings (`^M`), trailing whitespace (spaces before the `$`), quotes (curly turned straight or the reverse), and the final newline. On any difference, stop. Tell the owner what differs and do not repair it. Store an accepted passage as it was pasted.

Then re-read the frontmatter and confirm it parses as YAML and that `from` is the text the owner gave.

## 5. Retire examples

Apply the plan from step 3. Set `state: retired` on each example in it. Change only the `state:` line. Never delete a seed example: its licence and attribution stay in the file. Retiring a committed example changes a committed file, so it goes through the PR in step 7. Retiring a local example needs no PR.

A type with fewer than 2 owner passages keeps its seed. Say: "<type> has one owner passage, so house-voice still reads the public seed. Add another to replace it."

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

Otherwise run `git switch -c voice/seed-<today>`. If that branch exists locally or on `origin`, add `-2`, then `-3`, until it is free. Stage each committed example you wrote or retired, by exact path. Never use `git add -A`. Commit with the message `voice: owner examples for <types>`. Run `git push -u origin voice/seed-<today>`. If the push fails, show the error, print the commands for the user to run, and stop.

Write the PR body to a temporary file: each committed example added, with its type and `from`; each example retired; and each type that kept its seed. Name local examples only as a count. Never put their text or their `from` in the PR. Run `gh pr create --base main --head voice/seed-<today> --title "Voice: owner examples" --body-file <file>`. If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL.

## Never

- Never rewrite, shorten, correct or paraphrase the owner's words.
- Never store a passage the owner did not write. Never commit one they did not clear for the repository.
- Never write under `voice/corpus/`. It is gitignored reading material, not examples.
- Never edit a file outside `voice/examples/` and `voice/local/`.
