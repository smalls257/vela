# Starting a session

Every mode skill runs these steps before its own. The vault root is the current directory. The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (see "Where the planner runs from" below), and the format is `CONVENTIONS.md`. Every command in the skills is written with that prefix.

## Where the planner runs from

The skills write the planner as `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner`. The host may or may not replace that variable. Pick the program once, at the start, by the first of these that works, and use it for every `planner` command in the session:

1. `${CLAUDE_PLUGIN_ROOT}/scripts/planner`, if the variable was expanded (no literal `${` is left in the text you were given) and the file exists.
2. `${CLAUDE_SKILL_DIR}/../../scripts/planner`, on the same terms. The skill's own folder sits two levels under the plugin root.
3. `.claude/skills/planner/scripts/planner`, if it exists. That is the copy a vendored vault carries.
4. The `planner_path` recorded in `.planner/workspace.json`, in a reader copy.
5. None: stop and say "I cannot find the planner program. Run `/planner:where` and send me what it prints." Do not guess a path.

Say which one you picked in a sentence the first time. The installed plugin wins over a vendored copy, because two versions answering one vault is how a vault gets rules its skills no longer follow. Other files the skills name as `${CLAUDE_PLUGIN_ROOT}/...` (this file, `MODES.md`, `REVIEW.md`, the catalogue) live in the same plugin root as `scripts/`. When the variable was not expanded, the root is the folder that holds the `scripts/planner` you picked, so a vendored vault's `.claude/skills/planner/`.

## Owner or reader

Run `planner role`. Access decides, never a title. An **owner** works in the vault's git work tree and can commit: follow every step below as written. A **reader** has a published copy with no `.git` (the folder holds `.planner/workspace.json`). A reader's session differs in these ways, and the steps below say so where they apply:

- **No git or `gh`, anywhere.** Never run `git switch`, `git pull`, `git fetch`, `git commit`, `git push`, `git status` or `gh`, and skip every step in any skill that stages, commits, checkpoints, pushes or opens a PR. Say so once, plainly: "This is a read copy, so I will not use git: your work stays in this folder and nothing is committed or sent."
- **Session records are still written**, in place, to `sessions/<id>.md`, and kept up to date by hand as captures arrive.
- **Decisions and overrides are pending.** A reader may record `decided`, but beside every item they decide or override, write `- **Pending approval:** @<their handle>, <today>` (where `CONVENTIONS.md` says under "Pending approval"). The handle is a short lower-case name, asked once and reused; their full name is `author` in `.planner/workspace.json`. Owner decisions never carry the marker. Tell the reader why: the owner sees it before it counts.
- **Owner-only, so not open to a reader:** handoff, publish, `planner upgrade` and `/planner:challenge`. Name the owner as the CLI does (`published.json` has `owner`): "That is <name>'s call. Send a proposal (`/planner:propose`) and they decide."
- If `planner role` says `none`, stop and show its message.

## The user may override any rule

The user may override any rule in these skills. Say once, in one sentence, what the rule protects. Then do what they asked, and record an `**Override:**` bullet (or the session's Changes row note) naming the rule and their reason. Never refuse, and never ask twice.

This holds in every skill, whichever steps of this file it runs, and it covers the grill gates, "only a Grill decides", an open unknown that blocks an item, an absent owner, and every "never" and "must not" in the skills and in `MODES.md`. The lead may decide on others' behalf.

- History bullets (Override, Decision, Decided by, Confirmed by, Options considered, Dissent) go under the page's `## History`, as `CONVENTIONS.md` says under "Pages": page level directly under it, an item's under `#### <ID>`. Add the section at the end of the page if it is missing.
- Write the bullet in the grammar of `CONVENTIONS.md` under "Overrides": `- **Override:** <rule> by @<user's handle> on <today>: <their reason, in their words>`, under the item's heading or at page level. Name the rule as the skills do: `GATE-1` to `GATE-5`, `grill`, a check code such as `E316`, or the rule's own words in double quotes. The handle comes from `gh api user -q .login`; if `gh` fails, ask for it once. In a reader copy, do not run `gh`: ask once for a short handle.
- The "session's note" is that same bullet at page level in the session record, for a rule that belongs to no item, such as batching writes. Also capture the user's instruction verbatim, with them as origin, so the record holds what they said.
- When the user decides for an owner who is not there, add `- **Decided by:** @<user>, on behalf of @<owner>`. The owner later adds `- **Confirmed by:** @<owner> on <date>`, or raises `/planner:challenge` if they disagree. Until then `planner check` warns with W324.
- If they give no reason, ask for one once. If they still give none, write `reason not given`.

Hard stops are not process rules, and no override reaches them. Say which one applies and offer what you can do instead:

- Never edit anything under `~/.claude`.
- Never commit or push company material, or anything from `.inbox/`, `voice/local/` or `voice/corpus/`, without the owner's explicit consent in this session.
- Never say a PR, comment, push or commit exists unless the tool printed it, and never report a failed step as done.
- Never invent what a person said, a source, or an ID the vault does not hold.

## 1. Show the state of the clone

**Reader copy:** skip every git command in steps 1 to 3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner freshness` and tell the user what it prints in its own words: whether a newer copy was published, or that the folder they opened this from is out of reach. It reports and never updates. There is nothing to pull. Then go to step 2.

**Owner:** run `git status --short --branch` and show the output. If any file is changed or untracked, stop and ask: commit it, stash it, or carry it into this session. The one exception is untracked output the planner itself writes under `.planner/` (`explorer-pins.json`, `explorer.html`, `findings/`, `owed/`, `pr-body*.md`): say once that you are leaving it unstaged and go on, and never stage it. Do nothing else until the user answers.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner freshness` and tell the user what it prints, in its own plain words: how far behind or ahead the clone is, how many files are uncommitted, or that origin could not be reached and this is the local state. It fetches with a short timeout and never pulls or changes anything; if it says origin is unreachable, say so and do not describe the clone as up to date. If it fails, show its message.

If the user names a challenge to answer, by its PR number or the challenged ID, take the path "Answer a challenge" below instead of the rest of this step. Otherwise run `git switch main` and `git pull --ff-only`. If any of them fails, show the error and say the session would start from an old `main`. Ask whether to go on. Never start from an old `main` without saying so.

## 2. Find open sessions

**Reader copy:** run only `grep -l '^status: open' sessions/*.md` (there are no branches) and offer to resume or close it, or leave it open and start a new one. Skip the branch commands below.

An open record lives on its own `session/<id>` branch until its PR merges, so `main` alone cannot show it. Run all three: `grep -l '^status: open' sessions/*.md`, `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`. Treat every `session/*` branch as a possibly open session, and read its record with `git show <branch>:sessions/<id>.md`. A branch can hold more than one record, because an answer session shares its challenge's branch, so also run `git grep -l '^status: open' <branch> -- sessions/` for each branch and read every record it lists. For each open record or branch:

- Say its id, its date and how many captures it has.
- If its date is more than 14 days ago, say so.
- Offer three choices: resume it, close it now with `/planner:close`, or leave it open and start a new one.
- A branch whose only record is a closed `Challenge:` record is not an open session: it waits for the solution lead. Name it as "challenge waiting for an answer" and offer the "Answer a challenge" path instead of the three choices.

To resume, run `git switch session/<id>`, read the record, and carry on from the last capture. For a Grill, carry on from the `## Agenda` section of the record: take the first item whose status is `open`. Never close a session for the user.

## 3. Bring in review comments

**Reader copy:** skip this step; there is no `gh`. Say "review comments are not checked in a read copy".

Find the date of the last closed session: the highest `date:` among records with `status: closed`. If there is none yet, skip the merged-PR search and say so. Otherwise run:

```
gh pr list --state merged --search "merged:>=<that date>" --json number,title,url
```

For each PR, run `gh pr view <number> --comments`, `gh api repos/{owner}/{repo}/pulls/<number>/comments` and `gh api repos/{owner}/{repo}/pulls/<number>/reviews`, so review bodies are read as well as line comments. Offer each review comment as a capture, one at a time, with the commenter's handle as the origin and the comment quoted word for word. The user keeps or skips each one.

If `gh` fails, say: "gh could not list merged PRs (<the error>), so review comments were not checked." Then go on.

## 4. Offer the overdue unknowns and the next step

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check` and read its first line, which says which date it used. For each `W705` line, name the unknown, its owner and its ask-by date. Ask the user whether they know the answer now, and how, as `MODES.md` says under "Unknowns". If they do not, offer to turn the question into a research task Claude does now with a source. Never draft an ask for the user to send, and never offer to. A research answer becomes a capture with the source named. It never becomes a `fact` without a row in `sources.md`.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner next` and show its line. If the user has not said what this session is for, offer that app and mode first. It is a suggestion from the rules in `CONVENTIONS.md` under "Progress and next step", never a decision. When `planner next` suggests `probe`, it means the question to the user and the research offer above. There is no Probe skill.

## 5. Open the record and the branch

Ask for a topic of two to four words. The id is today's date plus the topic as a lower-case slug, for example `2026-10-05-mainframe-breaks-booking`. If `sessions/<id>.md` exists, or a `session/<id>` branch exists locally or on `origin`, add `-2`, then `-3`, and so on until both are free.

**Reader copy:** do not run `git switch -c`, and do not commit; write the record on the folder as it is.

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

`<Mode name>` is the display name in `MODES.md`: Dump & Diverge, Discover, Shape, Requirements, Boundary, Allocate, Grill, Epics, Challenge or Answer. Commit it with the message `Open session <id>`. (A reader copy writes the file and stops there.)

A session that runs a second mode adds that mode to `modes`. It never opens a second record.

## Answer a challenge

The solution lead answers a challenge on the challenge's own branch, so the red E316 check and its answer land in the same PR.

1. Find the open challenge PR: `gh pr list --search "Challenge: <ID>" --state open --json number,headRefName,title`, then keep only the PRs whose title ends with exactly `Challenge: <ID>`, because the search also matches longer IDs such as `CON-0010` for `CON-001`. If the user gave a PR number, run `gh pr view <number> --json number,headRefName,title,state` and confirm its title starts with the date and `Challenge:` and its state is `OPEN`. If none is open, or more than one, stop and show what `gh` returned. If `gh` fails, show the error and stop: an answer never starts on a guessed branch.
2. Check out that `session/...` branch instead of `git switch main`: `git switch <headRefName>`, then `git pull --ff-only`. If either fails, show the error and stop.
3. Run steps 2 to 4 as usual. Step 4's check shows the E316 the challenge left; that is the work.
4. Open the record as step 5 says, with two changes. Do not run `git switch -c`: the record goes on the branch you are on. The id is `<date>-answer-<id-lowercased>`, for example `2026-11-24-answer-con-001`, with `-2` and so on if that file exists. Write `modes: [answer]` and the title `Answer: <ID>`. Commit it with the message `Open session <id>`.

In the answer session, a Grill works on that branch and adds `grill` to `modes`. It resolves `UNK-nnn` with the senior, or decides the item again. Or the lead sets the item back, a contract to `assumption` or an epic to `reopened`, with a `## Changes` row such as `| CON-nnn | decided | assumption | [[<id>#^cNN]] |`. `/planner:close` then pushes to the same branch and comments on the challenge PR.

## Captures during the session

Write each point as a capture line in `## Captures`, in the form `CONVENTIONS.md` gives. Leave the mark off until close. The first exception is a Grill, which marks the deciding capture `→ keep: [[<page>#<heading>|<ID>]] (decided)` as soon as it writes the item `decided`. The second is a Discover, which marks the capture of each fact it writes `→ keep: [[<page>#<heading>|<ID>]] (fact)` at once. The third is a Boundary, which marks the capture of each line it writes `→ keep: [[<page>#<heading>|<ID>]] (assumption)` at once.

- A person's words are quoted verbatim, with their name, role or handle as the origin.
- Claude's own idea has origin `claude`.
- Any origin that starts with `claude` is Claude-originated, and close parks its line by default.
- When Claude restates what someone said, or the user accepts Claude's recommended answer, the origin is `claude, from <name>`. Close lists those lines under "promoted on a nod".
- Number block IDs `^c01`, `^c02` and so on, in order, never reused.

A reader copy does not commit: the file on disk is the resume point. Otherwise, commit after about every ten captures, with the message `Checkpoint <id>`. Stage the session record and the pages you changed by exact path, never `git add -A`. The session record is the resume point if the conversation stops.
