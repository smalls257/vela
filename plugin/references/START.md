# Starting a session

Every mode skill runs these steps before its own. The vault root is the current directory. The planner is `python3 .claude/skills/planner/bin/planner`, and the format is `CONVENTIONS.md`.

## 1. Show the state of the clone

Run `git status --short --branch` and show the output. If any file is changed or untracked, stop and ask: commit it, stash it, or carry it into this session. Do nothing else until the user answers.

Then run `git fetch origin` and `git switch main` and `git pull --ff-only`. If any of them fails, show the error and say the session would start from an old `main`. Ask whether to go on. Never start from an old `main` without saying so.

## 2. Find open sessions

An open record lives on its own `session/<id>` branch until its PR merges, so `main` alone cannot show it. Run all three: `grep -l '^status: open' sessions/*.md`, `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`. Treat every `session/*` branch as a possibly open session, and read its record with `git show <branch>:sessions/<id>.md`. For each open record or branch:

- Say its id, its date and how many captures it has.
- If its date is more than 14 days ago, say so.
- Offer three choices: resume it, close it now with `/planner:close`, or leave it open and start a new one.

To resume, run `git switch session/<id>`, read the record, and carry on from the last capture. For a Grill, carry on from the `## Agenda` section of the record: take the first item whose status is `open`. Never close a session for the user.

## 3. Bring in review comments

Find the date of the last closed session: the highest `date:` among records with `status: closed`. If there is none yet, skip the merged-PR search and say so. Otherwise run:

```
gh pr list --state merged --search "merged:>=<that date>" --json number,title,url
```

For each PR, run `gh pr view <number> --comments`, `gh api repos/{owner}/{repo}/pulls/<number>/comments` and `gh api repos/{owner}/{repo}/pulls/<number>/reviews`, so review bodies are read as well as line comments. Offer each review comment as a capture, one at a time, with the commenter's handle as the origin and the comment quoted word for word. The user keeps or skips each one.

If `gh` fails, say: "gh could not list merged PRs (<the error>), so review comments were not checked." Then go on.

## 4. Offer the overdue unknowns

Run `python3 .claude/skills/planner/bin/planner check` and read its first line, which says which date it used. For each `W705` line, name the unknown, its owner and its ask-by date. Offer two things: draft a short ask the user can send to the owner, or turn the question into a research task Claude does now with a source. A research answer becomes a capture with the source named. It never becomes a `fact` without a row in `sources.md`.

## 5. Open the record and the branch

Ask for a topic of two to four words. The id is today's date plus the topic as a lower-case slug, for example `2026-10-05-mainframe-breaks-booking`. If `sessions/<id>.md` exists, or a `session/<id>` branch exists locally or on `origin`, add `-2`, then `-3`, and so on until both are free.

Run `git switch -c session/<id>`. Write `sessions/<id>.md`:

```
---
id: <id>
type: session
title: "<Mode name>: <topic>"
date: <today>
modes: [<mode>]
status: open
summary: In progress.
---

# <today> <Mode name>: <topic>

## Captures

## Changes

| ID | From | To | Source |
|---|---|---|---|
```

`<Mode name>` is the display name in `MODES.md`: Dump & Diverge, Discover, Shape, Grill, Requirements, Epics or Challenge. Commit it with the message `Open session <id>`.

A session that runs a second mode adds that mode to `modes`. It never opens a second record.

## Captures during the session

Write each point as a capture line in `## Captures`, in the form `CONVENTIONS.md` gives. Leave the mark off until close. The first exception is a Grill, which marks the deciding capture `→ keep: [[<page>#<heading>|<ID>]] (decided)` as soon as it writes the item `decided`. The second is a Discover, which marks the capture of each fact it writes `→ keep: [[<page>#<heading>|<ID>]] (fact)` at once.

- A person's words are quoted verbatim, with their name, role or handle as the origin.
- Claude's own idea has origin `claude`.
- Any origin that starts with `claude` is Claude-originated, and close parks its line by default.
- When Claude restates what someone said, or the user accepts Claude's recommended answer, the origin is `claude, from <name>`. Close lists those lines under "promoted on a nod".
- Number block IDs `^c01`, `^c02` and so on, in order, never reused.

Commit after about every ten captures, with the message `Checkpoint <id>`. Stage the session record and the pages you changed by exact path, never `git add -A`. The session record is the resume point if the conversation stops.
