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

Find the record with `status: open` under `sessions/`. If there is more than one, ask which. Make sure the current branch is `session/<id>`; if not, switch to it.

## 2. Mark every capture

Propose a mark for every capture at once, as a numbered list with a one-line reason each. The user changes the ones they disagree with. Defaults:

- A person's `idea` or `thought` is kept as an `inkling` on the page it belongs to.
- A person's `unknown` or `worry` is kept as an unknown with an owner handle and an ask-by date you propose, or as a concern cell.
- An `unknown` capture is kept or dropped with a reason. It is never parked.
- A `(claude)` line is parked unless the user picks it.
- Never propose `fact`. A capture becomes a fact only if the user names its source in this turn and the source has a row in `sources.md`.
- A line you will copy word for word onto a page is a lifted line. List each one and ask the user to confirm it before you copy it.

Write each mark into the line: `→ keep: [[<page>#<heading>|<ID>]] (<state>)`, `→ park` or `→ drop: <reason>`, before the `^cNN`.

## 3. Write the promoted items

Write each kept item onto its page as structured content only: fact bullets, table rows and `### <ID> <short name>` headings, per `CONVENTIONS.md`. A Grill already wrote its decided items, so leave those alone. Add one row to `## Changes` for each item whose state changed: `| ID | From | To | [[<id>#^cNN]] |`.

## 4. Prose

The house-voice skill is not installed yet, so this close drafts no paragraphs. List each paragraph the session needs, page by page, in the PR body under **Prose to draft**. A person writes them in review.

## 5. Read back decided wording

For each item that became `decided` in this session, show its final wording. If its owner is present, they confirm it. If not, list it in the PR body for them.

## 6. Render and check

Run `python3 .claude/skills/planner/bin/planner render`, then `python3 .claude/skills/planner/bin/planner check`. Fix each error with the user. If the user leaves an error in place, put it in the PR body. CI will block the merge until it is fixed.

## 7. Finish the record

Draft a one-line `summary:` and let the user accept or edit it. Set `status: closed`. Commit with the message `Close session <id>`. Run `git push -u origin session/<id>`. If the push fails, show the error, print the commands for the user to run, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the PR

Collect the reviewers:

- the `owner:` of each app page this session changed;
- the `owner:` of each consumer app of a contract this session changed.

Drop the user's own handle. A team handle `@org/team` is passed as `org/team`.

Write the PR body to a temporary file. Fill the headings of the vault's PR template:

- **What changed.** The promoted items, each with its new state. Then these lists, each with "none" when empty:
  - **Promoted on a nod:** every item whose deciding capture has origin `claude, from <name>`, with the capture quoted.
  - **Changed contracts:** each contract, and for each consumer, who was asked: present, async, in this PR, or "not consulted: <reason>".
  - **Overdue unknowns:** each `W705` line from step 6, with its owner @-mentioned.
  - **May still say the old value:** for each `decided` or `fact` value this session changed, run `grep -rn -F "<old wording>" --include='*.md' . | grep -v '^./sessions/'` and list every hit.
  - **Check:** the first line of the check output, and any error left in place.
- **Minutes.** Ask the user how long the session took.
- **Structural fixes** and **Prose edits.** Write "Filled in by the reviewer."

Then run:

```
gh pr create --base main --head session/<id> --title "<date> <mode>: <topic>" --body-file <file> --reviewer <handle> --reviewer <handle>
```

If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL. Show the URL.
