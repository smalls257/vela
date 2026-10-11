---
name: ask
description: Answer a question about this initiative from the vault alone, citing item IDs and the sections they come from, flagging anything not yet decided, and saying "Not recorded" or "Not decided" with who to ask when the vault is silent. Use for questions about goals, apps, containers, contracts, decisions, unknowns, risks, concerns, flows or epics.
argument-hint: "<question>"
allowed-tools: Read Grep Glob Bash(git log *) Bash(git rev-list *) Bash(date *) Bash(cat *) Bash(python3 .claude/skills/planner/scripts/planner query *)
disallowed-tools: Write Edit NotebookEdit
---

# Ask the vault

## Rules for this vault, written by a person

!`cat "${CLAUDE_PROJECT_DIR}/CLAUDE.md" 2>/dev/null || echo "NO CLAUDE.md: say that this vault has no answering rules yet, then answer by the steps below."`

## How fresh this clone is

!`git log -1 --format='HEAD is %h, committed %cs.' 2>&1; echo "Behind origin/main by $(git rev-list --count HEAD..origin/main 2>/dev/null || echo 'an unknown number of') commits, as of the last fetch on $(date -r .git/FETCH_HEAD +%F 2>/dev/null || echo 'no recorded date')."`

## Question

$ARGUMENTS

## Steps

1. Start the answer with the two lines under "How fresh this clone is", word for word.
2. Find the pages. Start with `python3 .claude/skills/planner/scripts/planner query search <the asker's words> --json`, which ranks pages and sections by the words and lists the flows that cross each, then `planner query find <words> --json` for exact titles and headings, then use Grep and Glob over the vault's `.md` files. Never search `voice/`. Search `sessions/` only if the question asks about a session or what was said.
   Never Read a file under `voice/` or `.inbox/`. Read `sessions/` only if the user asks. Try at least two sets of words before you decide no page covers it: the asker's words, and the vault's own words from `12-glossary.md`.
3. Open every section you will cite with Read, and read it. Cite nothing you did not open in this answer. Assert nothing you did not open and read. A Grep snippet alone does not count.
4. Before you cite any ID, run `python3 .claude/skills/planner/scripts/planner query get <ID> --json`. Cite the ID by the `link` it returns, and take its state, `dissent`, `blocked_by`, `override` and `decided_by` for the flags below. If the answer is `not_found`, never cite that ID, and never write it as if it existed: say `Not recorded: <ID> is not in this vault.` To find every page that mentions an item, run `python3 .claude/skills/planner/scripts/planner query refs <ID> --json`. If `planner query` exits 2, it could not read the vault: show its message, say the IDs in this answer were not checked, and never treat that as `not_found` or "Not recorded".
5. Split the question into its parts. Each part is answered, in conflict, or unanswered.
6. Write the answer in the shape below. Never create, edit or delete a file.
7. Every claim is followed by its ID or labelled `Not from the vault:`. There is no third choice.

## Bash is read-only here

Use Bash only to read. `planner query` only reads. Never redirect output (`>`, `>>`). Never use `tee`, `sed -i`, `git commit`, `git checkout`, `git log --output`, `planner render`, or anything else that writes a file or changes git state.

## Flags

Put a flag next to any claim that rests on something not settled:

- the state word, for an item at `inkling`, `assumption`, `proposed` or `open`;
- "unexamined: nobody has looked at <concern> for <app>", for an `unexamined` cell or an app with no cell;
- "assumed: not confirmed by the <app> senior", for a container at `assumption`;
- "contested: see UNK-nnn", for an item an open unknown lists in `**Blocks:**`, which `planner query get` returns as `blocked_by`;
- "dissent: <name>", for an item with a `**Dissent:**` bullet.
- "decided by override: <rule>, by @x", for each entry in `override`, with its rules joined by commas, its `by` and its reason. An entry marked `malformed` overrides nothing: say "override not readable: <problem>".
- "on behalf of @owner, not yet confirmed", when `decided_by` is set and its `confirmed` is false. When it is true, say "decided by @x on behalf of @owner, confirmed by @y" from `confirmed_by`.

When two pages disagree, show both, cite both, and say which page owns the value.

## Unanswered parts

Each unanswered part gets its own line, and each line names who to ask:

- `Not recorded:` no page covers it. Name the owner of the nearest page.
- `Not recorded:` an open unknown covers it. Give its ID, owner and ask-by date.
- `Not recorded:` a page lists it as out of scope. Say where.
- `Not recorded:` it sits below the vault's level, such as components or stories. Name the team whose tech design owns it.
- `Not decided:` the question asks "should we" and no `decided` item answers it. Name the area and suggest a Shape or a Grill.

If the only match is a capture in `sessions/`, say: "Not recorded in the plan. An unpromoted capture in session <id> mentions it."

Never fill a gap from general knowledge. If the asker insists, add it after the `Sources:` list under the heading `Not from the vault:`.

## Answer shape

```
<the two freshness lines>

<the answer, pitched at the asker; each claim followed by its ID, or labelled `Not from the vault:`>
<one line per flag>
<one line per unanswered part>

Sources:
- <ID> · <path>#<full heading> · <state>, each as `planner query get` returned it
```
