# Starting a session

Contents: where the planner runs from; owner or reader; plain names and a page a person can hold; shell on a Mac and on Linux; the user may override any rule; steps 1 to 6 (the clone, open sessions, review comments, overdue unknowns, the record, how to talk); answer a challenge; closing a session; captures.

Every mode skill runs these steps before its own. The vault root is the current directory. The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (see "Where the planner runs from" below), and the format is `CONVENTIONS.md`. Every command in the skills is written with that prefix.

## Where the planner runs from

The skills write the planner as `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner`. The host may or may not replace that variable. Pick the program once, at the start, by the first of these that works, and use it for every `planner` command in the session:

1. `${CLAUDE_PLUGIN_ROOT}/scripts/planner`, if the variable was expanded (no literal `${` is left in the text you were given) and the file exists.
2. `${CLAUDE_SKILL_DIR}/../../scripts/planner`, on the same terms. The skill's own folder sits two levels under the plugin root.
3. `.claude/skills/planner/scripts/planner`, if it exists. That is the copy a vendored vault carries.
4. The `planner_path` recorded in `.planner/workspace.json`, in a reader copy.
5. None: stop and say "I cannot find the planner program. Run `/planner:where` and send me what it prints." Do not guess a path.

Do not say which one you picked unless you could not find one. The installed plugin wins over a vendored copy, because two versions answering one vault is how a vault gets rules its skills no longer follow. Other files the skills name as `${CLAUDE_PLUGIN_ROOT}/...` (this file, `MODES.md`, `REVIEW.md`, the catalogue) live in the same plugin root as `scripts/`. When the variable was not expanded, the root is the folder that holds the `scripts/planner` you picked, so a vendored vault's `.claude/skills/planner/`.

## Owner or reader

Run `planner role`. Access decides, never a title. An **owner** works in the vault's git work tree and can commit: follow every step below as written. A **reader** has a published copy with no `.git` (the folder holds `.planner/workspace.json`). A reader's session differs in these ways, and the steps below say so where they apply:

- **No git or `gh`, anywhere.** Never run `git switch`, `git pull`, `git fetch`, `git commit`, `git push`, `git status` or `gh`, and skip every step in any skill that stages, commits, checkpoints, pushes or opens a PR. Say so once, plainly: "This is a read copy, so I will not use git: your work stays in this folder and nothing is committed or sent."
- **Session records are still written**, in place, to `sessions/<id>.md`, and kept up to date by hand as captures arrive.
- **Decisions and overrides are pending.** A reader may record `decided`, but beside every item they decide or override, write `- **Pending approval:** @<their handle>, <today>` (where `CONVENTIONS.md` says under "Pending approval"). The handle is a short lower-case name, asked once and reused; their full name is `author` in `.planner/workspace.json`. Owner decisions never carry the marker. Tell the reader why: the owner sees it before it counts.
- **Owner-only, so not open to a reader:** handoff, publish, `planner upgrade` and `/planner:challenge`. Name the owner as the CLI does (`published.json` has `owner`): "That is <name>'s call. Send a proposal (`/planner:propose`) and they decide."
- If `planner role` says `none`, stop and show its message.

## Plain names and a page a person can hold

The people who read this vault hold about four to seven things in mind at once (Cowan 2001; Miller 1956), so what you say and what you write are sized to that. `CONVENTIONS.md` says under "Pages" what the files follow; in a session:

- **The lead reads names, never codes.** Every kind of ID and code stays out of what the lead reads: unknowns, capabilities and requirements, contracts, flows, epics, apps, parties, runs, copy and finding IDs, capture numbers, check codes, gate names and numbers, and rule names in capitals. Say the thing's name, or what the code means in the lead's words: "the pilot date is a plan, not a fact yet", not a check code; "the strategy page is ready to decide", not a gate; "the calendar entries", "the prep-note flow", not a contract or flow ID. IDs go in files, the pull request body, `- Trace:` lines and the `**Override:**` bullet, where the check reads them. If the lead asks for an ID, give it. Spell an abbreviation out the first time you use it.
- **A line is written after a yes to that line.** A yes that covers a group you read out ("yes to these five") counts for every line in it, so read sheets, criteria and rows back in groups of about five, not one by one. Silence or "ok" is not a yes: ask once more in different words, then park the line as an open question. The reason: a decided or assumed line should carry the lead's own word, and a yes to a long list is not consent to each line in it.
- **One question at a time, with your recommendation and why.** Never a list of questions, and never a question without a view.
- **Review checkpoint and digest.** Where a skill says to run the review checkpoint, run it as `REVIEW.md` says and show the digest as section 5 of that file says: once per session, at most three questions.
- **Write a line at once.** The state a mode writes is marked on its capture at once (see "Captures during the session" below); a skill names only the state it writes.
- Tool trouble you fix yourself (a failed shell command, a retry, a reviewer still running) is not news. Mention it only if you cannot get past it.
- In a page, the IDs a sentence would have carried go on a `- Trace: CAP-001.FR1, CON-001, FLO-001` line under it. Never delete a Trace line, and never turn one into prose.
- A link with a label, written inside a table cell, escapes its pipe: `[[page#Heading\|label]]`. A bare `|` splits the cell and `planner check` warns (W329). Outside a table the pipe is plain: `[[page#Heading|label]]`.
- Offer a few things at a time. A list of more than about seven items is shown in groups of about five, the ones that matter first and the rest counted. A page opens with two or three plain sentences: what it says and what is still open.
- `planner check` warns with W360 to W364 when a page drifts back. Each warning's fix line says how to write it in plain words.

## Shell that runs on a Mac and on Linux

Owners work on macOS (BSD tools) as often as on Linux (GNU tools). Edit a file with the Edit tool, or with a `planner` command when one exists. Never edit in place from the shell: no `sed -i`, which takes a different argument on each, and no `\n`, `\+` or `\|` in a `sed` replacement. To read a line range, `sed -n '<first>,<last>p' <file>` works on both. Anything longer is `python3 -c` or a script, not a `sed` chain. If a shell edit fails, check the file before you retry, because part of it may have been written.

## The user may override any rule

The user may override any rule in these skills. Say once, in one plain sentence and without the rule's code, what the rule protects. Then do what they asked, and record an `**Override:**` bullet (or the session's Changes row note) naming the rule and their reason. Never refuse, and never ask twice.

This holds in every skill, whichever steps of this file it runs, and it covers the grill gates, "only a Grill decides", an open unknown that blocks an item, an absent owner, and every "never" and "must not" in the skills and in `MODES.md`. The lead may decide on others' behalf.

- History bullets (Override, Decision, Decided by, Confirmed by, Options considered, Dissent) go under the page's `## History`, as `CONVENTIONS.md` says under "Pages": page level directly under it, an item's under `#### <ID>`. Add the section at the end of the page if it is missing.
- Write the bullet in the grammar of `CONVENTIONS.md` under "Overrides": `- **Override:** <rule> by @<user's handle> on <today>: <their reason, in their words>`, under the item's heading or at page level. Name the rule as the skills do: `GATE-1` to `GATE-5`, `grill`, a check code such as `E316`, or the rule's own words in double quotes (the file needs the name; the lead does not hear it). If no rule was set aside, write no `**Override:**` bullet: something the lead wishes, such as who may reopen an item, is a Notes line. The handle comes from `gh api user -q .login`; if `gh` fails, read it from the first line of `.planner/handle`, and if that is missing ask once and write it there (`.planner/` is not committed). In a reader copy, do not run `gh`: read or ask for a short handle the same way, once, and never again in any skill.
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

**Owner:** run `git status --short --branch` and read it; do not paste it to the lead. If a page of the vault is changed or untracked, carry it into the session unstaged and say so in one clause ("your edit to the strategy page comes with us, unstaged"). Ask only when two reasonable choices would lose work, for example when the pull cannot run over the change. The one exception is untracked output the planner itself writes under `.planner/` (`findings/`, `owed/`, `pr-body*.md`, `handle`): leave it unstaged and go on, and never stage it. `.planner/explorer-pins.json` is different: it is the shared map layout, committed, so stage it by exact path when it changed. Files under `docs/` and `CONTEXT.md` are a team's design files and are not a reason to stop either. A changed `dashboard.html` is the exception to the exception: it is the rebuilt explorer page and it is tracked, so it is not a reason to stop (close commits it). 

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner freshness` and tell the user only if the clone is behind, or origin could not be reached and this is the local state. Say nothing when it is in step. It fetches with a short timeout and never pulls or changes anything; if it says origin is unreachable, say so and never describe the clone as up to date. If it fails, show its message.

If the user names a challenge to answer, by its PR number or the challenged ID, take the path "Answer a challenge" below instead of the rest of this step. Otherwise run `git switch main` and `git pull --ff-only`. If any of them fails, show the error and say the session would start from an old `main`. Ask whether to go on. Never start from an old `main` without saying so.

## 2. Find open sessions

**Reader copy:** run only `grep -l '^status: open' sessions/*.md` (there are no branches) and offer to resume or close it, or leave it open and start a new one. Skip the branch commands below.

An open record lives on its own `session/<id>` branch until its PR merges, so `main` alone cannot show it. Run all three: `grep -l '^status: open' sessions/*.md`, `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`. Treat every `session/*` branch as a possibly open session, and read its record with `git show <branch>:sessions/<id>.md`. A branch can hold more than one record, because an answer session shares its challenge's branch, so also run `git grep -l '^status: open' <branch> -- sessions/` for each branch and read every record it lists. For each open record or branch:

- Say its id, its date and how many captures it has.
- If its date is more than 14 days ago, say so.
- Offer three choices: resume it, close it now with `/planner:close`, or leave it open and start a new one.
- A branch whose only record is a closed `Challenge:` record is not an open session: it waits for the solution lead. Name it as "challenge waiting for an answer" and offer the "Answer a challenge" path instead of the three choices.

To resume, run `git switch session/<id>`, read the record, and carry on from the last capture. For a Grill, carry on from the `## Agenda` section of the record: take the first item whose status is `open`. Never close a session the user has not asked to close; "Closing a session" below says what asking looks like.

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

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner next` and show its line. If the user has not said what this session is for, offer that app and mode first. It is a suggestion from the rules in `CONVENTIONS.md` under "Progress and next step", never a decision.

## 5. Open the record and the branch

Take the topic from the user's first message, in two to four words, and tell them the id in half a sentence ("calling this one `desk-helper-start`"). Change it only if they object; ask for a topic only when they have said nothing about what the session is for. The id is today's date plus the topic as a lower-case slug, for example `2026-10-05-mainframe-breaks-booking`. If `sessions/<id>.md` exists, or a `session/<id>` branch exists locally or on `origin`, add `-2`, then `-3`, and so on until both are free.

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

`<Mode name>` is the display name in `MODES.md`: Dump & Diverge, Discover, Shape, Boundary, Allocate, Releases, Grill, Requirements, Epics, Challenge or Answer. Commit it with the message `Open session <id>`. (A reader copy writes the file and stops there.)

A session that runs a second mode adds that mode to `modes`. It never opens a second record.

Then say in one sentence how much there is and how far you expect to get: "Six capabilities, two or three requirements each; we'll do two or three today." When you have done about two thirds of what you said, say so, and ask whether to push on or stop and close. If the conversation is cut off, the record holds the resume point; on resume, say in one line where you stopped.

**Name the initiative, once.** The template ships `title: New initiative` in `.planner.yaml`, and that title heads the dashboard and every copy a reader gets. If the title is still that (`planner check` says W718), ask the lead before the first question of the session: "What short name should this initiative go by? A few words, as you would say it to a colleague." Write their answer as `title:` in `.planner.yaml`, commit it with the message `Name the initiative`, and never ask again; a title that is already something else is theirs, so leave it alone. If they decline, say once that the dashboard will read "New initiative" until they give one, and go on. **Reader copy:** do not edit the file; say the owner names the initiative.

## 6. Read how to talk

Before the session's first question, read `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`. If the vault has `voice/VOICE.md`, read that first: it holds the owner's own rules and sits above the defaults. The conversation file says which examples to read and how. Every mode skill reaches this step through START, so no skill repeats it. Do not tell the lead you read it.

## Answer a challenge

The solution lead answers a challenge on the challenge's own branch, so the red check and its answer land in the same PR. When the user names a challenge to answer, read `${CLAUDE_PLUGIN_ROOT}/references/ANSWER-A-CHALLENGE.md` and follow it instead of the rest of step 1; it finds the challenge PR, switches to its branch and opens the answer record on it.

## Closing a session

Close is a skill you may start, and only on the lead's word. That word is any plain way of saying they are done: "close", "close it", "we're done", "that's enough", "let's wrap up", or a request to move to another mode ("now do requirements for the third capability"), because the open session has to be closed before another opens.

- **They said close, or something equal to it.** That is the yes. Say in one line what will happen ("I'll file your notes, write the pages and send the branch for review"), and run the `close` skill in this conversation.
- **They only sounded finished** ("I think that's it", a long pause after the last answer). Ask once, "Shall I close this out now?", and wait. Do not start it on a guess.
- **Never start close** because the work looks complete, a turn limit is near, or a gate stopped you. The lead decides when the session ends.
- **One confirmation stays, before anything leaves the machine.** Close pushes the branch and opens a pull request. Before it does, close says what will be sent and waits for a yes, unless the lead typed `/planner:close` themselves or said "push" or "open the PR" in so many words. A "close" alone is not consent to push company material; it is consent to file.
- **A switch.** After closing for a switch, say the one line the lead types to start the next mode ("Type `/planner:requirements CAP-005`"). Modes start on the lead's word and are not started by you.
- **If close cannot be started from where you are,** say only: "Type `/planner:close` and I'll take it from there." Say nothing about why, and give no lecture.

## Captures during the session

Write each point as a capture line in `## Captures`, in the form `CONVENTIONS.md` gives. Leave the mark off until close, except in a mode whose skill says its captures are marked at once. Those are a Grill, which marks the deciding capture `→ keep: [[<page>#<heading>|<ID>]] (decided)` as soon as it writes the item `decided`; a Discover, which marks the capture of each fact it writes `→ keep: [[<page>#<heading>|<ID>]] (fact)`; and Boundary, Requirements, Allocate and Releases, which mark the capture of each line they write `→ keep: [[<page>#<heading>|<ID>]] (assumption)`. Close leaves a mark already written alone.

- A person's words are quoted verbatim, with their name, role or handle as the origin.
- Claude's own idea has origin `claude`.
- Any origin that starts with `claude` is Claude-originated, and close parks its line by default.
- When Claude restates what someone said, or the user accepts Claude's recommended answer, the origin is `claude, from <name>`. Close lists those lines under "promoted on a nod".
- Number block IDs `^c01`, `^c02` and so on, in order, never reused.

A reader copy does not commit: the file on disk is the resume point. Otherwise, commit after about every ten captures, with the message `Checkpoint <id>`. Stage the session record and the pages you changed by exact path, never `git add -A`. The session record is the resume point if the conversation stops.
