---
# The model may start close, on purpose: "we're done" or "switch to requirements" must be able to start it
# without the lead typing /planner:close. The description's "Never start it on your own" is the guard.
name: close
description: Close an initiative-vault session. Marks every capture keep, park or drop by default and asks only what is unsettled, writes the promoted items into the pages, drafts prose in the house voice, renders and checks the vault, then commits, pushes and opens the PR with reviewers. Use when the lead says they are done ("close", "we're done", "switch to ...") or types /planner:close. Never start it on your own.
argument-hint: "[session id, if more than one is open]"
---

# Close a session

Close turns a session record into a reviewed PR. Run every step in order, because a skipped step leaves the pull request describing work nobody checked, and never report a step as done when it failed.

The path, in order: find the session (1), mark every capture (2), write the promoted items, the ledger and the marks (3), draft the prose, review its voice and harvest the owner's edits (4), read back decided wording (5), render and check (6), finish the record and push (7), open the PR (8), rebuild the explorer (9). The longer parts live in files beside this one, each read at the step that needs it: `READER.md`, `LEDGER.md`, `VOICE-REVIEW.md`, `HARVEST.md`, `PR-BODY.md`.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). The format is `CONVENTIONS.md`.

## Starting a close

Close is started by the lead's word, never by yours, as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session": typing `/planner:close`, or saying "close", "we're done" or "switch to requirements", is the yes to filing. Say in one line what will happen ("I'll file your notes, write the pages and send the branch for review") and go on.

One confirmation stays, because the push and the pull request are the only steps that leave the machine and a hard stop forbids sending company material without consent. Before section 7 pushes, say what is about to be sent ("I'll push `session/<id>` and open a pull request for <reviewers>") and wait for a yes. Skip that wait only when the lead has said "push" or "open the PR" in so many words in this conversation. A bare "close" is consent to file, not to send.

Close talks in the session's voice. If this conversation has not read `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` yet (a close typed in a fresh conversation), read it now, as step 6 of `${CLAUDE_PLUGIN_ROOT}/references/START.md` says. What the lead reads while close runs is short, in plain words and without codes (START defines them); those go in the files and the pull request body. A command that fails and that you fix is not news. When a `planner close` command can't do what the lead wants, say so plainly and stop; never fall back to doing its steps by hand.

## Reader copy: no git, no PR

Run `planner role` first. If it says `reader` (a published copy: `.planner/workspace.json`, no `.git`), say once, plainly: "This is a read copy, so close writes your session record and stops. Nothing is committed, pushed or sent." Then read `${CLAUDE_PLUGIN_ROOT}/skills/close/READER.md`: it lists the few changes to the sections below, and there are no others. Never say a PR exists in a reader copy.

## 1. Find the session

Run `planner session open --switch`. With one open session it switches to that session's branch (an answer session's is its challenge's) and prints which; go on. If it exits 3, several are open: ask the lead which one, by topic and date, then run `planner session open --switch --id <the one they picked>`. If it exits 1, none is open: say so in one line, change nothing in the vault's pages, and go straight to section 9, which has its own path for a close with no session.

## 2. Mark every capture

Mark every capture that has none yet by the defaults below, without asking. Filing is the tool's work, not the lead's. Keep the full list of marks, each with its one-line reason, for the pull request body; never show it to the lead as a numbered list to approve. A new item gets its ID in section 3, and the marks are written into the lines at the end of it, once every ID exists.

Then show the lead only what the defaults could not settle: at most three items, each one plain sentence with your recommended answer, asked in one message. These are the kinds of thing that qualify, and nothing else does:

- a `claude`-origin line the lead might want kept, or an `unknown` of yours that needs a keep or a drop;
- an unknown with nobody who could answer it;
- a line you would copy word for word that the lead did not say themselves;
- a belief the plan seems to rest on, when you cannot tell whether it is load-bearing.

For example: "I'd write the 18 January slot down as a constraint, from your account. Right?" and "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and chase it on 6 November. Is that the right person?" If more than three are unsettled, ask the three that matter most and take your recommended answer for the rest, listing them in the pull request body. When the lead answers, write it, and say in two or three sentences what you filed, by group and in their words ("I kept the 8 hard limits as constraints, parked the 12 what-ifs and dropped 5 that repeat other lines"). Never show a capture number. Do not ask "anything to change?" a second time.

Never ask the lead for bookkeeping the record already holds or the tool can work out: not a handle (`START.md` says where it is kept), not the session's minutes (section 8), not whether a source document gets a row in `sources.md` (write the row for each document the lead brought in, and say so in the summary), not whether another gap turned up. Defaults:

- In a session whose `modes` include `shape`, the picked option is kept as an `assumption`, never an `inkling`. See section 3.
- A capture that names something the initiative cannot change, such as a date, a budget, a law, a contract term or a system it must keep, is kept as a constraint: a row on `02-constraints.md`, `| CST-n | <the constraint> | <where it comes from, as a link on the words> | <what it forces> |`. The link's label pipe is written `\|` there, because the link sits in a table cell.
- A person's `idea` or `thought` is kept as an `inkling` on the page it belongs to.
- A capture that says `type at close: PTY` or `type at close: SV` names a subject the lead said exists. It gets one mark, to the subject, `→ keep: [[03-context-and-scope#<heading>|<ID>]] (subject)`, because a party or stored value carries no state. That holds when its words also start with the existence question's copy ID: section 3 writes that copy's row, and the row's `## Changes` line cites the capture, so the capture needs no second mark. If section 3 leaves the subject untyped, mark it as a keep to the unknown section 3 writes instead, `→ keep: [[11-unknowns-and-risks#<heading>|UNK-nnn]] (open)`, so no mark links a heading that does not exist.
- Any other capture whose words start with a copy ID or a finding ID is kept as its ledger row, `→ keep: [[11-unknowns-and-risks#Question ledger|<copy>]] (<state>)`, with the state of the row. A finding the lead did not take has no capture, so it gets no mark. Section 3 says which of those still get a row.
- A capture that says how a concern touches an app, as `unchanged`, `n/a` with why, or `unknown` with its unknown, is kept as that concern cell, as `CONVENTIONS.md` says under "Concern cells and waivers". Only a grill writes `addressed`.
- A capture that answers an open unknown, the lead's first-hand word or a source the session read, is kept as that unknown resolved, as `MODES.md` says under "Unknowns": `→ keep: [[11-unknowns-and-risks#<heading>|<ID>]] (resolved)`. A first-hand answer needs its own row in `sources.md` first.
- A person's `unknown` or `worry` is kept as an unknown, or as a concern cell. Its `**Owner:**` is the handle of the lead who is chasing it, and the person who would know goes on the `**Ask:**` line as the role the lead named ("CISO", "outside counsel"); never stop to ask for a handle. Its ask-by date is the date the lead gave, else the nearest hard date the vault holds (a constraint or a release target), else two weeks from today. Say the date you chose in the summary.
- An `unknown` capture is kept or dropped with a reason. It is never parked. For a `claude`-origin `unknown`, the user must choose, so it is one of the few items you ask about: kept as an UNK with an owner and an ask-by date, or dropped with a reason. Number each new UNK with `planner next-id UNK`, run again after each one is written, so the number is never guessed or reused from an open session branch. Claude never decides it alone. This rule wins over the park default for `claude` lines.
- A capture, or a sentence you are about to write on a page, that says something is left for a grill, or is decided later, is never kept as prose. It becomes an open unknown, `### UNK-nnn <short name>`: the question in the lead's words, an `**Owner:**` (the lead who will take it to the grill), an `**Ask by:**` date by the rule above, and `**Blocks:**` linking the item that is waiting. The sentence on the page then links that unknown, so the record says who will answer and by when. Say in the summary which deferrals you turned into questions. The check warns (W389) on page prose that leaves a matter for a grill and links no open question.
- A person's `wild` line is parked, never dropped.
- A `(claude)` line is parked unless the user picks it. This covers every origin that starts with `claude`, including `(claude, from <name>)`.
- Never propose `fact`. A capture becomes a fact only if the user names its source in this turn and the source has a row in `sources.md`.
- A line you will copy word for word onto a page is a lifted line. When the lead said it themselves, copy it and list it in the pull request body. When anyone else said it, or it is `claude`'s, it is one of the few items you confirm before you copy it.

A line a grill already marked `(decided)`, a Discover already marked `(fact)`, or a Boundary, Requirements, Allocate or Releases session already marked `(assumption)`, keeps its mark. Leave it alone. It still appears under "Promoted on a nod" when its origin starts with `claude`.

## 3. Write the promoted items

Write each kept item onto its page as structured content only: fact bullets, table rows and `### <ID> <short name>` headings, per `CONVENTIONS.md`. A grill already wrote its decided items, Discover already wrote its facts, Boundary already wrote its app, contract and runtime pages, Requirements already wrote its functional requirements, Allocate already wrote its allocation rows and any contract it proposed, and Releases already wrote `04b-releases.md`, so leave those alone. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written, and never move, merge or reword one. If the user overrode a rule during the session and no bullet records it yet, write it now, in the grammar of `CONVENTIONS.md` under "Overrides", with the handle, date and reason from the capture. If no rule was set aside, write no `**Override:**` bullet: something the lead wishes (who may reopen an item, and when) is a Notes line, not an override, and an `**Override:**` never names a rule that exists nowhere in the skills.

For a session whose `modes` include `epics`, the epic pages already exist, so write no `assumption` item for a picked cut, and skip the `shape` paragraph that follows. Still add the `## Changes` rows for every epic whose state changed, `| EPC-nnn | - | draft | [[<id>#^cNN]] |` and `| EPC-nnn | draft | decided | ... |`, or `| EPC-nnn | reopened | decided | ... |` for a reopened epic, if the session has not already. For any other session whose `modes` include `shape`, write the picked option as an `assumption` item with an `**Options considered:**` bullet, at page level or under the item's heading: `- **Options considered:** <picked option> (picked); <option>: rejected, <reason>; ...`. `planner next` reads it: an `assumption` without it still needs a Shape, and one with it is ready for a grill. If a capture says "that's decided", add a "grill to confirm" note to the item. The item must pass grill's GATE-2 afterwards: at `assumption`, with a preferred option and the rejected options with their reasons. Number each new item with `planner next-id <its prefix>` (`planner next-id CST`, `planner next-id UNK`), run again after each one is written: it counts this tree, `main` and every session branch, so another open session's number is never reused. Add one row to `## Changes` for each item whose state changed: `| ID | From | To | [[<id>#^cNN]] |`.

### Subjects, the question ledger and catalog gaps

Read `${CLAUDE_PLUGIN_ROOT}/skills/close/LEDGER.md` and follow it. It types the subjects Dump named (`type at close: PTY` or `SV` captures), writes a ledger row for every copy or finding the lead took (and for every row of the record's `## Reviews` tables), runs `planner check` on the ledger, and lists catalog gaps in the pull request body. Skip it only when the record holds no such capture and no `## Reviews` table.

### Write the marks

Every new item, subject, unknown and reviewer question now has its ID. Write each mark into the line: `→ keep: [[<page>#<heading>|<ID>]] (<state>)`, `→ park` or `→ drop: <reason>`, before the `^cNN`.

## 4. Draft the prose

Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it for every paragraph this session needs. Those are:

- the opening prose of every page this session changed (`git diff --name-only --diff-filter=d main...HEAD`, leaving out `sessions/` and `sources.md`), rewritten to say what is true now, as `CONVENTIONS.md` says under "Pages". Keep the owner's own wording wherever the facts it states have not changed, because a later close harvests those edits; rewrite only what the session made untrue or left out. Never add a paragraph about what changed: that is the page's `## History`. A page has one opening: the one you rewrite replaces the old one, and you never write a new opening beside it. Two or more separate opening paragraphs above the first `##` heading, running past 150 words together, draw W371; keep one and fold what the others add under a heading. The opening is two or three plain sentences, at most about 80 words and three links: what is true now and the one thing that holds it up. It names threads, not items, and sends the reader to the block or table below for the items; a state is said once, in one sentence, and never added to each clause (`house-voice` rules 1, 3 and 7). A page of more than about 900 words with no such opening draws W363, an opening over 90 words or 3 links draws W365, and an opening that is still a line the template wrote draws W368. Run `planner check` for W363, W365, W368 and W371 on every page whose opening you wrote, and rewrite until none remains; do not list the warning in the pull request instead. An opening is never a changelog ("Five more unknowns came from the desks session..."). On a page that is mostly a list (unknowns and risks, concerns, decisions, sources), the opening counts and points and never enumerates the list, as `house-voice` says under "Pages that are mostly a list": "28 questions are open. Five hold up the first release; the most urgent is who owns Heron, due 23 October." The items go below it, grouped by what they hold up;
- the sentences on other pages that mention an item whose state this session changed. For each unknown this session resolved and each item it decided, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner query refs <ID>`, open each page it lists, and rewrite the sentence that links the item so it says what is true now: "the account opens at the first practice trade", not "when the account opens is still open". Leave `## History` alone. `planner check` reports W334 for a sentence still calling an answered question open;
- the `## Strategy` paragraph of each concern page whose cells this session changed;
- on a page that lists more than about seven unknowns, concerns or other items, the few that matter first, and the rest under `## Also open (n)` at the end of the list's section, which the viewer and the explorer fold. Group any other list of more than about seven under subheadings of about five, each line reading the plain name, who to ask and by when, and what it holds up;
- the opening sentence of each `### <ID>` item this session wrote or changed, before its fact bullets;
- a decision record for each page this session made `decided` whose decision shapes the whole design: the solution strategy or another initiative section, an app page, or a flow. Write it as `09-decisions/ADR-nnnn-<slug>.md`, with `id`, `type: decision`, `title`, `state: decided`, `owner`, `authored: authored` and `sources`, and these sections: `## Context` (what forced the choice), `## Decision` (what was chosen, linking the decided page), `## Alternatives considered` (a table, `| Alternative | Why rejected |`, from its `**Options considered:**`) and `## Consequences` (what it commits people to). Put its `**Decision:**` bullet, linking the grill, under `## History`, and link the record from `09-decisions/09-decisions.md`. Contracts and unknowns get no record of their own;
- a glossary entry for each term the session used that a newcomer to the initiative would not know, such as a product name or a word like "paper trading": one paragraph on `12-glossary.md`, the term in bold, then what it means here;
- the paragraphs below.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner style <each changed page>` and fix every line it prints: move a history bullet under `## History`; write a labeled bullet nothing reads as a sentence in its section, merged with any prose that already says it; open an item that has only bullets with a sentence; say a bracketed aside in the sentence; label a link with the thing's name; and give a page with no opening prose one. An ID in a sentence or a list item is moved to a `- Trace:` line under it and the sentence names the thing in plain words. Fix only what it names, and run it again until it prints nothing. It also lists each word of the lint list (`${CLAUDE_PLUGIN_ROOT}/references/lint-words.txt`) the page uses, with its count: say what the thing does in plain words. Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check` and fix each W365 to W369 line on the pages you changed the same way: split a long paragraph at its second topic or move its pointers to a table, cut a table cell to a clause, say a repeated state once and put the rest on a Trace line or in the table, replace a template opening with what is true now, and spell an abbreviation out at its first use. Never delete an `**Ask:**`, `**Target:**` or `**Owning team:**` line, or a `- Trace:` line, to quiet it: the planner reads them, and a line it still flags is a planner bug to report in the PR body. For a session whose `modes` include `epics`, each epic it drafted owes its summary, its `Still open:` line and its `## Who this is for and what changes` section, in the epic template's order, so list those epics under "Prose drafted" in the PR body. The epics session already wrote each `**Owning team:**` line; close leaves it as written. Prose is drafted here and nowhere else. When a merged paragraph is wrong as a whole, `house-voice` says to rewrite it: first copy the old paragraph word for word under `## Replaced prose` in the session record (page, date, then the paragraph), so no edit of the owner's is lost. Commit each drafted page, by exact path, with the message `draft: prose for <id>`. That commit holds each drafted page whole, including its structured section-3 edits, because a page cannot be committed in halves. The reviewer's later edits then show as a diff against it.

### Voice review

A fresh reader checks the drafts, because the drafter cannot judge its own voice. Skip this part if the session drafted no paragraph. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/close/VOICE-REVIEW.md` and follow it (the optional voicescore reading, the reviewer subagent, one rewrite per flagged paragraph, and the voicecheck that decides whether a rewrite stays), then go on to the harvest.

### Harvest the owner's edits

Only the vault's owner harvests, and only their own edits. The owner is the `author` of the `source: owner` examples in `voice/examples/` and `voice/local/`. If there are none, say "No owner examples yet, so nothing to harvest. `/planner:voice-seed` adds them." and go on to section 5, Read back decided wording. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/close/HARVEST.md` and follow it; it offers the owner's merged edits as voice examples, one at a time. Harvest does not depend on the voice review: run it even when the review did not run.

## 5. Read back decided wording

For each item that became `decided` in this session, show its final wording. If its owner is present, they confirm it. If not, list it in the PR body for them.

## 6. Render and check

First bring in `main`, so render and check see what will merge: run `planner close sync-main`.

- Exit 0: main is in (or nothing moved). Go on.
- Exit 3 because of uncommitted edits: run `planner close stage --checkpoint`, then `planner close sync-main` again.
- Exit 3 because the shared copy couldn't be reached: tell the lead what it prints and ask whether to go on without it. On a yes, run `planner close sync-main --accept-not-compared`; otherwise try again later.
- Exit 1: main changed lines this session changed too, so it stopped the merge and lists them. Show the lead both sides in plain words and let them choose; make their choice, commit with `planner close stage --checkpoint`, and run `planner close sync-main` again.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner render`, then `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check`. Fix each W326 at once: set the page's `state` as the warning says, because a page whose rows have moved on but whose own state has not reads as unsettled to everyone. For a session whose `modes` include `shape`, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check --gate shape` as well: each W806 is a question still `assumed`, so list it under **Questions** in the PR body. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --open --digest` and keep its first line, the coverage, for the PR body.

Two warnings point at questions the ledger cannot see, so tell the lead about each one in plain words (never the code), and not only in the PR body. These count among the few items section 2 allows you to ask about:

- W809 is possibly an untyped subject: a fact names points, a clause, a license or another word an existence question lists, and the page holds or links no subject of that kind. For each one, offer to type the subject, as "Type the subjects Dump named" says, with the facts the user gives, or to answer the existence question in the ledger.
- W804 is a ledger row that is orphaned (its subject is gone), no longer owed (its subject no longer matches the trigger), or a wildcard that covers nothing because other rows shadow it or no copy matches. For each one, offer to fix the row, such as renaming its copy to the subject's new ID, or to leave it as a record. Never delete it without the user's yes.

Carry each one into the PR body's **Questions** line with what the user chose. Fix each error with the user. An E321 or E322 is an override the check cannot read: fix its grammar, never delete it. A W303, W304, W316, W317, W318 or W324 is an override doing its job: list it under **Overrides**, and do not remove the bullet to quiet it. Never delete a ledger row to quiet the check: fix its grammar or change its state with the user. If the user leaves an error in place, put it in the PR body. CI will block the merge until it is fixed.

## 7. Finish the record

Run `planner check-slice --changed` and give the lead one line per slice it checked, as it prints them, then say how many are unchanged since their last check.

Run `planner close gate --for-lead`. If it lists anything, sort each one out with the lead, in its words, and run it again until it says the session is ready. A decision it says has no yes on record needs the lead's own words: read the item back, capture their answer with them as origin, and cite that capture in the item's `## Changes` row; if they want it kept without one, that is an override with their reason (`START.md`, "The user may override any rule").

Write a one-line `summary:` yourself, in plain words, and mention it in your closing message. Set `status: closed`, then run `planner close stage --close --session <id>`. It stages by exact path from an allow-list (what render rewrote, the changed pages, the session record, harvested voice examples, the explorer's pin file) and commits `Close session <id>`; it never stages the inbox, `voice/local/` or `voice/corpus/`, which hold material only the owner may send. If it names a file it left out, tell the lead in one plain line and ask whether that file belongs in this session.

If this session set `handed_off:` on an app page, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner handoff <APP-id>` only now, after that commit, so the handoff record names a clean commit and not "with uncommitted changes". It writes `handoffs/<APP-id>.md`, the record of what the app's team accepts. If the record already exists, the team is accepting changes: run it with `--replace` only once they say so in this session. The command prints what is not settled at handoff and writes the same list into the record; say that list to the lead in plain words before you commit, so nobody hands an app over without knowing. Then commit the handoff record alone, by exact path, with the message `Handoff manifest for <APP-id>`.

Before you push, ask the one confirmation the section "Starting a close" describes, unless the lead has already said "push" or "open the PR". Run `git push -u origin session/<id>`. For a session whose `modes` include `answer`, push to the challenge's branch instead: `git push origin <branch>`. If the push fails, say in a sentence what failed, give the branch name and the one command that would retry it, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the PR

For a session whose `modes` include `answer`, do not open a new PR: the answer belongs in the challenge's PR. Find it with `gh pr list --head <branch> --state open --json number,url`. Write the body below to a temporary file, and in its **Check:** line add "E316 for <ID> should now be gone." If check still reports E316 for that item, say so in its place. Run `gh pr comment <number> --body-file <file>`, and skip the rest of this section. If `gh` fails, say so, print the exact command, and stop. Never say the comment exists unless `gh` printed its URL.

Collect the reviewers:

- the `owner:` of each app page this session changed;
- the `owner:` of each consumer app of a contract this session changed.

Get the user's own handle with `gh api user -q .login`. Strip the leading `@` from each individual handle. A team handle `@org/team` is passed as `org/team`. Drop the user's own handle. If nobody remains, leave out `--reviewer`.

Write the PR body to a temporary file, as `${CLAUDE_PLUGIN_ROOT}/skills/close/PR-BODY.md` says: it lists the headings, the lists that appear only when they have something to say, the minutes from the commit log, and the two lines left for the reviewer. Paste what `planner close gate --consent-block` prints into it, under the summary: it quotes the lead's words behind each decision.

Then run the command below, with one `--reviewer` per remaining reviewer (none, if nobody remains). `<Mode name>` is the display name in `MODES.md`.

```
gh pr create --base main --head session/<id> --title "<date> <Mode name>: <topic>" --body-file <file> --reviewer <handle> --reviewer <org/team>
```

If `gh` fails, write the body to `.planner/pr-body.md` (it is not committed) and say one sentence: "The branch is pushed; I couldn't open the pull request from here. The text is in `.planner/pr-body.md`." Never say a PR exists unless `gh` printed its URL. Show the URL. If this session wrote `handed_off: "<senior>, <date>, PR pending"`, replace `pending` with `#<the PR's number>`, commit it as `Handoff PR number for <APP-id>`, and push. If `gh` failed, leave `pending`: W325 says so until someone writes the number.

## What you tell the lead at the end

Three to six plain sentences: what was filed, by group and in the lead's words; what is waiting on someone, with the date; and the pull request link, or why there is none. No capture number, copy ID, finding ID or check code, and no list of what a tool did or did not install. The pull request body is the reviewer's record; the lead does not need to read it. For a switch, end with the one line that starts the next mode.

## 9. Rebuild the explorer

This is the last step of every close. Run it even when section 8 stopped because `gh` or the push failed, since the explorer needs neither. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner explore` from the vault root, without `--serve`, as a command of its own: never pipe it, because a pipe hides its exit status. Read the exit status before you say anything about the result. It rewrites `dashboard.html` at the vault root, the page colleagues open from git or OneDrive, and takes about a second. A reader's copy has no git: nothing is committed, and the rebuilt page shows the reader's drafts.

In an owner's vault, when `git status --short -- dashboard.html` shows it changed:

- **With a session branch** (section 7 ran), commit only that file by exact path with the message `Rebuild dashboard`, and push the branch if section 7 pushed it.
- **With no session** (section 1 found none, so you are on `main`), do not commit to `main` and do not push. Say: "The dashboard is rebuilt in your folder but not committed, because no session is open. It goes in with the next close, or I can put it on its own branch for a pull request." On a yes, create `dashboard/<today>`, commit only `dashboard.html` by exact path, push it after the same confirmation section 7 asks, and open the pull request as section 8 does.

- If it exits 0, say one plain line: "The dashboard is up to date: dashboard.html — open it, or run /planner:explore to ask Claude from it". Then add one line for each `warning:` and each `no design doc found` it printed, in its own words, such as a `team_repos:` folder that does not exist. Do not read the rest of its output back.
- If it fails, say so plainly with its message: "The explorer could not be built: <message>. The close itself is done." A failed build never undoes or blocks the close, and you never say the dashboard is up to date unless the command exited 0.
